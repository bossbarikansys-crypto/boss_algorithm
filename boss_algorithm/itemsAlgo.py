"""
Items Performance Algorithm

This module analyzes sales data from MongoDB to calculate item performance metrics.
It provides functions to analyze daily, weekly, and monthly sales data for each menu item.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
import os


def get_mongodb_connection():
    """
    Establish connection to MongoDB database.
    Returns the database connection object.
    """
    try:
        from pymongo import MongoClient
        
        # Get MongoDB URI from environment variable or use default
        mongodb_uri = os.environ.get(
            'MONGODB_URI',
            'mongodb+srv://dbUser:bossbarikan@barikandb.rsrkuro.mongodb.net/Sales'
        )
        
        client = MongoClient(mongodb_uri)
        db = client['Sales']
        return db
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        raise


def get_date_range(period: str, week_number: Optional[int] = None, day_number: Optional[int] = None, month_number: Optional[int] = None) -> Dict[str, datetime]:
    """
    Calculate the start and end dates based on the specified period.
    
    Args:
        period: 'daily', 'weekly', or 'monthly'
        week_number: For weekly period, specify which week of the month (1-5)
        day_number: For daily period, specify which day of the month (1-31)
        month_number: For monthly period, specify which month (1-12)
    
    Returns:
        Dictionary with 'start' and 'end' datetime objects
    """
    today = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    print(f"get_date_range called - period: {period}, week_number: {week_number}, day_number: {day_number}, month_number: {month_number}")
    
    if period == 'daily':
        if day_number is not None:
            # Specific day of current month (or specified month)
            current_date = datetime.now()
            year = current_date.year
            month = month_number if month_number is not None else current_date.month
            start_date = datetime(year, month, day_number, 0, 0, 0, 0)
            end_date = datetime(year, month, day_number, 23, 59, 59, 999999)
            print(f"Specific day {day_number} of month {month}: {start_date} to {end_date}")
        else:
            # Default to today
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = today
    elif period == 'weekly':
        if week_number is not None:
            # Calculate specific week of the current month (or specified month)
            current_date = datetime.now()
            year = current_date.year
            month = month_number if month_number is not None else current_date.month
            
            print(f"Calculating week {week_number} for {year}-{month}")
            
            # Calculate the start day of the requested week
            week_start_day = ((week_number - 1) * 7) + 1
            
            # Calculate last day of month
            if month < 12:
                last_day_datetime = datetime(year, month + 1, 1) - timedelta(days=1)
            else:
                last_day_datetime = datetime(year + 1, 1, 1) - timedelta(days=1)
            
            last_day_of_month = last_day_datetime.day
            
            # Week end day is the minimum of (week_number * 7) and last day of month
            week_end_day = min(week_number * 7, last_day_of_month)
            
            start_date = datetime(year, month, week_start_day, 0, 0, 0, 0)
            end_date = datetime(year, month, week_end_day, 23, 59, 59, 999999)
            
            print(f"Week {week_number}: days {week_start_day} to {week_end_day}")
            print(f"Date range: {start_date} to {end_date}")
        else:
            # Last 7 days (default)
            start_date = (datetime.now() - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = today
            print(f"Default last 7 days: {start_date} to {end_date}")
    elif period == 'monthly':
        if month_number is not None:
            # Specific month of current year
            current_date = datetime.now()
            year = current_date.year
            # First day of the month
            start_date = datetime(year, month_number, 1, 0, 0, 0, 0)
            # Last day of the month
            if month_number < 12:
                last_day_datetime = datetime(year, month_number + 1, 1) - timedelta(days=1)
            else:
                last_day_datetime = datetime(year + 1, 1, 1) - timedelta(days=1)
            end_date = last_day_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)
            print(f"Specific month {month_number}: {start_date} to {end_date}")
        else:
            # Default to current month
            current_date = datetime.now()
            year = current_date.year
            month = current_date.month
            start_date = datetime(year, month, 1, 0, 0, 0, 0)
            end_date = today
    else:
        # Default to daily
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today
    
    return {'start': start_date, 'end': end_date}


def get_all_menu_items(db) -> List[Dict[str, Any]]:
    """
    Fetch all menu items from the menu collection.
    
    Args:
        db: MongoDB database connection
    
    Returns:
        List of menu items with their details
    """
    try:
        menu_collection = db['menu']
        menu_items = list(menu_collection.find({}, {
            '_id': 0,
            'productName': 1,
            'category': 1,
            'price': 1
        }))
        return menu_items
    except Exception as e:
        print(f"Error fetching menu items: {str(e)}")
        return []


def analyze_sales_data(period: str = 'daily', show_sold_only: bool = False, week_number: Optional[int] = None, day_number: Optional[int] = None, month_number: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Analyze sales data for item performance based on the specified period.
    Revenue is calculated from actual sold prices in orders, then adjusted for discounts
    and collection shortfalls to match actual cash collected (Sales Performance).
    
    Args:
        period: 'daily', 'weekly', or 'monthly'
        show_sold_only: If True, only return items that have been sold
        week_number: For weekly period, specify which week of the month (1-5)
        day_number: For daily period, specify which day of the month (1-31)
        month_number: For monthly period, specify which month (1-12)
    
    Returns:
        List of items with their performance metrics
    """
    try:
        db = get_mongodb_connection()
        
        # Get date range based on period
        date_range = get_date_range(period, week_number=week_number, day_number=day_number, month_number=month_number)
        
        # Fetch sales reports within the date range
        sales_collection = db['salesReport']
        sales_reports = list(sales_collection.find({
            'date': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            }
        }))
        
        # Get all menu items
        all_menu_items = get_all_menu_items(db)
        
        # Create a dictionary to aggregate item performance
        item_performance = defaultdict(lambda: {
            'productName': '',
            'category': '',
            'price': 0,
            'totalQuantitySold': 0,
            'totalRevenue': 0,
            'orderCount': 0,
            'averageQuantityPerOrder': 0
        })
        
        # Track unique orders per product (to count how many orders contained each product)
        product_orders = defaultdict(set)
        
        # Process sales reports - iterate through individual orders to get actual sold prices
        for report in sales_reports:
            report_id = str(report.get('_id', ''))
            orders = report.get('orders', [])
            
            for order in orders:
                order_number = order.get('orderNumber', 0)
                order_items = order.get('items', [])
                
                for item in order_items:
                    product_name = item.get('productName', '')
                    if not product_name:
                        continue
                    
                    quantity = item.get('quantitySold', 0)
                    price = item.get('price', 0)  # Actual sold price from this specific order
                    category = item.get('category', '')
                    
                    # Update item performance metrics
                    if product_name not in item_performance:
                        item_performance[product_name]['productName'] = product_name
                        item_performance[product_name]['category'] = category
                        # Use the first price encountered (they may vary, so this is just a reference)
                        item_performance[product_name]['price'] = price
                    
                    item_performance[product_name]['totalQuantitySold'] += quantity
                    # Calculate revenue using the actual sold price from this order
                    item_performance[product_name]['totalRevenue'] += (quantity * price) if price else 0
                    
                    # Track unique orders that contain this product
                    product_orders[product_name].add(f"{report_id}-{order_number}")
        
        # Calculate order count and average quantity per order for items that have been sold
        for product_name, data in item_performance.items():
            # Set the order count from the tracked unique orders
            order_count = len(product_orders.get(product_name, set()))
            data['orderCount'] = order_count
            
            if order_count > 0:
                data['averageQuantityPerOrder'] = round(
                    data['totalQuantitySold'] / order_count, 2
                )
        
        # If not showing sold only, add menu items that haven't been sold
        if not show_sold_only:
            for menu_item in all_menu_items:
                product_name = menu_item.get('productName', '')
                if product_name not in item_performance:
                    item_performance[product_name] = {
                        'productName': product_name,
                        'category': menu_item.get('category', ''),
                        'price': menu_item.get('price', 0) if menu_item.get('price') is not None else 0,
                        'totalQuantitySold': 0,
                        'totalRevenue': 0,
                        'orderCount': 0,
                        'averageQuantityPerOrder': 0
                    }
        
        # Convert to list and sort by total quantity sold (descending)
        result = sorted(
            item_performance.values(),
            key=lambda x: x['totalQuantitySold'],
            reverse=True
        )
        
        return result
        
    except Exception as e:
        print(f"Error analyzing sales data: {str(e)}")
        return []


def get_item_performance_summary(period: str = 'daily', week_number: Optional[int] = None, day_number: Optional[int] = None, month_number: Optional[int] = None) -> Dict[str, Any]:
    """
    Get a summary of item performance including top performers and insights.
    
    Args:
        period: 'daily', 'weekly', or 'monthly'
        week_number: For weekly period, specify which week of the month (1-5)
        day_number: For daily period, specify which day of the month (1-31)
        month_number: For monthly period, specify which month (1-12)
    
    Returns:
        Dictionary containing performance summary
    """
    try:
        db = get_mongodb_connection()
        
        # Get date range based on period
        date_range = get_date_range(period, week_number=week_number, day_number=day_number, month_number=month_number)
        
        # Fetch sales reports to get discounts
        sales_collection = db['salesReport']
        sales_reports = list(sales_collection.find({
            'date': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            }
        }))
        
        # Calculate total discounts
        total_discounts = 0.0
        for report in sales_reports:
            discounts = report.get('discounts', [])
            if isinstance(discounts, list):
                for discount in discounts:
                    if isinstance(discount, dict):
                        total_discounts += discount.get('amount', 0)
                    else:
                        total_discounts += discount
            elif isinstance(discounts, (int, float)):
                total_discounts += discounts
        
        items_data = analyze_sales_data(
            period=period, 
            show_sold_only=True,
            week_number=week_number,
            day_number=day_number,
            month_number=month_number
        )
        
        # Calculate summary statistics
        total_items_sold = sum(item['totalQuantitySold'] for item in items_data)
        total_revenue = sum(item['totalRevenue'] for item in items_data)
        items_with_sales = len(items_data)
        
        # Get top 5 performers
        top_performers = items_data[:5] if len(items_data) >= 5 else items_data
        
        summary = {
            'period': period,
            'totalItemsSold': total_items_sold,
            'totalRevenue': round(total_revenue, 2),
            'totalDiscounts': round(total_discounts, 2),
            'netRevenue': round(total_revenue - total_discounts, 2),
            'itemsWithSales': items_with_sales,
            'topPerformers': top_performers,
            'dateRange': date_range
        }
        
        return summary
        
    except Exception as e:
        print(f"Error generating performance summary: {str(e)}")
        return {
            'period': period,
            'totalItemsSold': 0,
            'totalRevenue': 0,
            'itemsWithSales': 0,
            'topPerformers': [],
            'error': str(e)
        }


def get_category_performance(period: str = 'daily') -> List[Dict[str, Any]]:
    """
    Analyze performance by category.
    
    Args:
        period: 'daily', 'weekly', or 'monthly'
    
    Returns:
        List of categories with their performance metrics
    """
    try:
        items_data = analyze_sales_data(period=period, show_sold_only=True)
        
        # Aggregate by category
        category_performance = defaultdict(lambda: {
            'category': '',
            'totalQuantitySold': 0,
            'totalRevenue': 0,
            'itemsSold': 0
        })
        
        for item in items_data:
            category = item.get('category', 'Uncategorized')
            if not category:
                category = 'Uncategorized'
            
            category_performance[category]['category'] = category
            category_performance[category]['totalQuantitySold'] += item['totalQuantitySold']
            category_performance[category]['totalRevenue'] += item['totalRevenue']
            category_performance[category]['itemsSold'] += 1
        
        # Convert to list and sort by revenue
        result = sorted(
            category_performance.values(),
            key=lambda x: x['totalRevenue'],
            reverse=True
        )
        
        return result
        
    except Exception as e:
        print(f"Error analyzing category performance: {str(e)}")
        return []


def get_individual_item_performance(product_name: str, period: str = 'monthly', year: Optional[int] = None, month: Optional[int] = None) -> Dict[str, Any]:
    """
    Get detailed performance data for a specific item including order history and time series data.
    
    Args:
        product_name: Name of the product to analyze
        period: 'daily', 'weekly', or 'monthly' (determines the granularity of the chart data)
        year: Year to analyze (defaults to current year)
        month: Month to analyze for daily/weekly views (defaults to current month)
    
    Returns:
        Dictionary containing:
        - itemInfo: Basic item information
        - orderHistory: List of all orders containing this item
        - chartData: Time series data for graphing (daily, weekly, or monthly)
        - summary: Overall performance metrics
    """
    try:
        db = get_mongodb_connection()
        sales_collection = db['salesReport']
        
        # Set default year and month
        if year is None:
            year = datetime.now().year
        if month is None:
            month = datetime.now().month
        
        print(f"Analyzing item: {product_name}, period: {period}, year: {year}, month: {month}")
        
        # Define date range based on period
        if period == 'daily':
            # Show entire month, grouped by day
            start_date = datetime(year, month, 1, 0, 0, 0, 0)
            if month < 12:
                end_date = datetime(year, month + 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
            else:
                end_date = datetime(year + 1, 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
        elif period == 'weekly':
            # Show entire month, grouped by week
            start_date = datetime(year, month, 1, 0, 0, 0, 0)
            if month < 12:
                end_date = datetime(year, month + 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
            else:
                end_date = datetime(year + 1, 1, 1, 0, 0, 0, 0) - timedelta(microseconds=1)
        else:  # monthly
            # Show entire year, grouped by month
            start_date = datetime(year, 1, 1, 0, 0, 0, 0)
            end_date = datetime(year, 12, 31, 23, 59, 59, 999999)
        
        # Fetch all sales reports in the date range
        sales_reports = list(sales_collection.find({
            'date': {
                '$gte': start_date,
                '$lte': end_date
            }
        }).sort('date', 1))
        
        # Get item info from menu
        menu_collection = db['menu']
        menu_item = menu_collection.find_one({'productName': product_name})
        
        item_info = {
            'productName': product_name,
            'category': menu_item.get('category', 'N/A') if menu_item else 'N/A',
            'price': menu_item.get('price', 0) if menu_item else 0
        }
        
        # Process order history and aggregate data
        order_history = []
        total_quantity = 0
        total_revenue = 0
        order_count = 0
        
        # For chart data aggregation
        time_series_data = defaultdict(lambda: {'date': '', 'quantity': 0, 'revenue': 0, 'orders': 0})
        
        # Count unique orders that contain this item per time period
        orders_per_period = defaultdict(set)
        
        for report in sales_reports:
            report_date = report.get('date')
            orders = report.get('orders', [])
            report_id = str(report.get('_id', ''))
            
            # Iterate through individual orders
            for order in orders:
                order_number = order.get('orderNumber', 0)
                order_items = order.get('items', [])
                
                # Check if this order contains the product we're looking for
                for item in order_items:
                    if item.get('productName') == product_name:
                        quantity = item.get('quantitySold', 0)
                        price = item.get('price', 0)
                        revenue = quantity * price
                        
                        # Add to order history
                        order_history.append({
                            'date': report_date.isoformat(),
                            'reportId': report_id,
                            'orderNumber': order_number,
                            'quantity': quantity,
                            'price': price,
                            'revenue': revenue
                        })
                        
                        # Update totals
                        total_quantity += quantity
                        total_revenue += revenue
                        order_count += 1
                        
                        # Aggregate for chart data
                        if period == 'daily':
                            # Group by day
                            date_key = report_date.strftime('%Y-%m-%d')
                            display_key = report_date.strftime('%b %d')
                        elif period == 'weekly':
                            # Group by week of month
                            day_of_month = report_date.day
                            week_num = ((day_of_month - 1) // 7) + 1
                            date_key = f"{report_date.year}-{report_date.month:02d}-W{week_num}"
                            display_key = f"Week {week_num}"
                        else:  # monthly
                            # Group by month
                            date_key = report_date.strftime('%Y-%m')
                            display_key = report_date.strftime('%b %Y')
                        
                        time_series_data[date_key]['date'] = display_key
                        time_series_data[date_key]['quantity'] += quantity
                        time_series_data[date_key]['revenue'] += revenue
                        
                        # Track unique order for this period
                        orders_per_period[date_key].add(f"{report_id}-{order_number}")
                        
                        # Only process this item once per order
                        break
        
        # Update the orders count in time series data to reflect unique orders
        for date_key in time_series_data.keys():
            time_series_data[date_key]['orders'] = len(orders_per_period[date_key])
        
        # Convert time series data to sorted list
        chart_data = sorted(
            [{'dateKey': k, **v} for k, v in time_series_data.items()],
            key=lambda x: x['dateKey']
        )
        
        # Remove the dateKey from the final output (used only for sorting)
        for item in chart_data:
            del item['dateKey']
        
        summary = {
            'totalQuantitySold': total_quantity,
            'totalRevenue': round(total_revenue, 2),
            'orderCount': order_count,
            'averageQuantityPerOrder': round(total_quantity / order_count, 2) if order_count > 0 else 0,
            'averageRevenuePerOrder': round(total_revenue / order_count, 2) if order_count > 0 else 0
        }
        
        return {
            'itemInfo': item_info,
            'orderHistory': order_history,
            'chartData': chart_data,
            'summary': summary,
            'period': period,
            'dateRange': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        }
        
    except Exception as e:
        print(f"Error analyzing individual item performance: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'itemInfo': {'productName': product_name, 'category': 'N/A', 'price': 0},
            'orderHistory': [],
            'chartData': [],
            'summary': {
                'totalQuantitySold': 0,
                'totalRevenue': 0,
                'orderCount': 0,
                'averageQuantityPerOrder': 0,
                'averageRevenuePerOrder': 0
            },
            'error': str(e)
        }


# Example usage
if __name__ == '__main__':
    print("=== Items Performance Analysis ===\n")
    
    # Test daily analysis
    print("Daily Performance:")
    daily_data = analyze_sales_data(period='daily', show_sold_only=False)
    print(f"Total items: {len(daily_data)}")
    if daily_data:
        print(f"Top item: {daily_data[0]['productName']} - {daily_data[0]['totalQuantitySold']} sold\n")
    
    # Test weekly analysis
    print("Weekly Performance:")
    weekly_data = analyze_sales_data(period='weekly', show_sold_only=True)
    print(f"Items with sales: {len(weekly_data)}")
    if weekly_data:
        print(f"Top item: {weekly_data[0]['productName']} - {weekly_data[0]['totalQuantitySold']} sold\n")
    
    # Test summary
    print("Performance Summary (Monthly):")
    summary = get_item_performance_summary(period='monthly')
    print(f"Total revenue: ₱{summary['totalRevenue']}")
    print(f"Total items sold: {summary['totalItemsSold']}")
    print(f"Items with sales: {summary['itemsWithSales']}\n")
    
    # Test category performance
    print("Category Performance (Monthly):")
    categories = get_category_performance(period='monthly')
    for cat in categories:
        print(f"{cat['category']}: ₱{cat['totalRevenue']:.2f} ({cat['totalQuantitySold']} items)")
