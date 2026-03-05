"""
Sales Performance Algorithm

This module analyzes sales data from MongoDB to calculate sales performance metrics,
including revenue analysis, order statistics, and day-of-week patterns.
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


def get_date_range(period: str, start_date: Optional[str] = None, end_date: Optional[str] = None, 
                   year: Optional[int] = None, month: Optional[int] = None, 
                   week: Optional[int] = None, day: Optional[int] = None) -> Dict[str, datetime]:
    """
    Calculate the start and end dates based on the specified period.
    
    Args:
        period: 'daily', 'weekly', 'monthly', 'custom', 'specific_month', 'specific_week', 'specific_day'
        start_date: Optional start date string (YYYY-MM-DD)
        end_date: Optional end date string (YYYY-MM-DD)
        year: Specific year
        month: Specific month (1-12)
        week: Specific week of month (1-5)
        day: Specific day of month (1-31)
    
    Returns:
        Dictionary with 'start' and 'end' datetime objects
    """
    today = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    current_year = year if year else datetime.now().year
    current_month = month if month else datetime.now().month
    
    if period == 'custom' and start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
        end = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
        return {'start': start, 'end': end}
    
    if period == 'specific_day' and day:
        # Specific day of a specific month and year
        start = datetime(current_year, current_month, day, 0, 0, 0, 0)
        end = datetime(current_year, current_month, day, 23, 59, 59, 999999)
        return {'start': start, 'end': end}
    
    if period == 'specific_week' and week:
        # Specific week of a specific month and year
        week_start_day = ((week - 1) * 7) + 1
        last_day_of_month = (datetime(current_year, current_month % 12 + 1, 1) - timedelta(days=1)).day if current_month < 12 else 31
        week_end_day = min(week * 7, last_day_of_month)
        
        start = datetime(current_year, current_month, week_start_day, 0, 0, 0, 0)
        end = datetime(current_year, current_month, week_end_day, 23, 59, 59, 999999)
        return {'start': start, 'end': end}
    
    if period == 'specific_month':
        # Entire specific month and year
        start = datetime(current_year, current_month, 1, 0, 0, 0, 0)
        if current_month == 12:
            end = datetime(current_year, 12, 31, 23, 59, 59, 999999)
        else:
            last_day = (datetime(current_year, current_month + 1, 1) - timedelta(days=1)).day
            end = datetime(current_year, current_month, last_day, 23, 59, 59, 999999)
        return {'start': start, 'end': end}
    
    if period == 'daily':
        # Last 7 days
        start = (datetime.now() - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'weekly':
        # Last 4 weeks (28 days)
        start = (datetime.now() - timedelta(days=27)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    elif period == 'monthly':
        # Last 12 months
        start = (datetime.now() - timedelta(days=365)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    else:
        # Default to last 30 days
        start = (datetime.now() - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = today
    
    return {'start': start, 'end': end}


def calculate_total_revenue(sales_report: Dict[str, Any]) -> float:
    """
    Calculate total revenue from a sales report including cash, online, and charge slips.
    Handles both old and new database structures.
    """
    try:
        total = 0.0
        
        # Get denominations structure
        denominations = sales_report.get('denominations', {})
        morning_data = denominations.get('morning', {})
        night_data = denominations.get('night', {})
        
        # Check if new nested structure exists (morning/night contain 'denominations' object)
        # New structure: denominations.morning.denominations.d1000
        # Old structure: denominations.morning.d1000
        
        # Process morning shift
        if 'denominations' in morning_data and isinstance(morning_data['denominations'], dict):
            # New nested structure
            morning_denom = morning_data['denominations']
            morning_online = morning_data.get('onlineTransaction', 0)
            morning_charge_slips = morning_data.get('chargeSlips', [])
        else:
            # Old flat structure
            morning_denom = morning_data
            morning_online = 0
            morning_charge_slips = []
        
        # Process night shift
        if 'denominations' in night_data and isinstance(night_data['denominations'], dict):
            # New nested structure
            night_denom = night_data['denominations']
            night_online = night_data.get('onlineTransaction', 0)
            night_charge_slips = night_data.get('chargeSlips', [])
        else:
            # Old flat structure
            night_denom = night_data
            night_online = 0
            night_charge_slips = []
        
        # Calculate denominations total
        for denom_key, value in morning_denom.items():
            if denom_key.startswith('d') and isinstance(value, (int, float)):
                try:
                    amount = int(denom_key[1:])
                    total += amount * value
                except ValueError:
                    continue
        
        for denom_key, value in night_denom.items():
            if denom_key.startswith('d') and isinstance(value, (int, float)):
                try:
                    amount = int(denom_key[1:])
                    total += amount * value
                except ValueError:
                    continue
        
        # Add online transactions (new structure: already extracted above)
        total += morning_online + night_online
        
        # Add online transactions (old structure: fallback)
        online = sales_report.get('onlineTransaction', {})
        if isinstance(online, dict):
            total += online.get('morning', 0) + online.get('night', 0)
        
        # Add charge slips (new structure: shift-specific)
        if isinstance(morning_charge_slips, list):
            for slip in morning_charge_slips:
                if isinstance(slip, dict):
                    total += slip.get('amount', 0)
                elif isinstance(slip, (int, float)):
                    total += slip
        
        if isinstance(night_charge_slips, list):
            for slip in night_charge_slips:
                if isinstance(slip, dict):
                    total += slip.get('amount', 0)
                elif isinstance(slip, (int, float)):
                    total += slip
        
        # Add charge slips (old structure: root level, fallback)
        charge_slips = sales_report.get('chargeSlips', sales_report.get('chargeSlip', []))
        if isinstance(charge_slips, list):
            for slip in charge_slips:
                if isinstance(slip, dict):
                    total += slip.get('amount', 0)
                elif isinstance(slip, (int, float)):
                    total += slip
        
        return round(total, 2)
    except Exception as e:
        print(f"Error calculating revenue: {e}")
        import traceback
        traceback.print_exc()
        return 0.0


def calculate_total_orders(sales_report: Dict[str, Any]) -> int:
    """
    Calculate total number of orders from a sales report.
    """
    try:
        orders = sales_report.get('orders', [])
        return len(orders)
    except Exception as e:
        print(f"Error calculating total orders: {e}")
        return 0


def analyze_revenue_over_time(period: str = 'daily', start_date: Optional[str] = None, end_date: Optional[str] = None,
                             year: Optional[int] = None, month: Optional[int] = None,
                             week: Optional[int] = None, day: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Analyze revenue over time based on the specified period.
    
    Args:
        period: 'daily', 'weekly', 'monthly', 'custom', 'specific_month', 'specific_week', 'specific_day'
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        year: Specific year
        month: Specific month (1-12)
        week: Specific week of month (1-5)
        day: Specific day of month (1-31)
    
    Returns:
        List of dictionaries with date, revenue, orders, and average order value
    """
    try:
        db = get_mongodb_connection()
        sales_collection = db['salesReport']
        
        date_range = get_date_range(period, start_date, end_date, year, month, week, day)
        
        # Query sales reports within date range
        sales_reports = sales_collection.find({
            'date': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            }
        }).sort('date', 1)
        
        results = []
        for report in sales_reports:
            revenue = calculate_total_revenue(report)
            orders = calculate_total_orders(report)
            avg_order_value = round(revenue / orders, 2) if orders > 0 else 0
            
            date_str = report['date'].strftime('%Y-%m-%d')
            day_of_week = report.get('dayOfWeek', report['date'].strftime('%A'))
            
            results.append({
                'date': date_str,
                'dayOfWeek': day_of_week,
                'revenue': revenue,
                'orders': orders,
                'averageOrderValue': avg_order_value
            })
        
        return results
    
    except Exception as e:
        print(f"Error analyzing revenue over time: {e}")
        return []


def analyze_day_of_week_performance() -> List[Dict[str, Any]]:
    """
    Analyze average performance by day of the week (Monday-Sunday).
    
    Returns:
        List of dictionaries with day of week statistics
    """
    try:
        db = get_mongodb_connection()
        sales_collection = db['salesReport']
        
        # Get all sales reports
        sales_reports = sales_collection.find({})
        
        # Group by day of week
        day_stats = defaultdict(lambda: {'revenue': [], 'orders': []})
        
        for report in sales_reports:
            day_of_week = report.get('dayOfWeek', report['date'].strftime('%A'))
            revenue = calculate_total_revenue(report)
            orders = calculate_total_orders(report)
            
            day_stats[day_of_week]['revenue'].append(revenue)
            day_stats[day_of_week]['orders'].append(orders)
        
        # Calculate averages
        results = []
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for day in days_order:
            if day in day_stats:
                revenues = day_stats[day]['revenue']
                orders = day_stats[day]['orders']
                
                avg_revenue = round(sum(revenues) / len(revenues), 2) if revenues else 0
                avg_orders = round(sum(orders) / len(orders), 2) if orders else 0
                total_occurrences = len(revenues)
                
                results.append({
                    'dayOfWeek': day,
                    'averageRevenue': avg_revenue,
                    'averageOrders': avg_orders,
                    'totalOccurrences': total_occurrences
                })
            else:
                results.append({
                    'dayOfWeek': day,
                    'averageRevenue': 0,
                    'averageOrders': 0,
                    'totalOccurrences': 0
                })
        
        return results
    
    except Exception as e:
        print(f"Error analyzing day of week performance: {e}")
        return []


def analyze_category_revenue(period: str = 'monthly', start_date: Optional[str] = None, end_date: Optional[str] = None,
                             year: Optional[int] = None, month: Optional[int] = None,
                             week: Optional[int] = None, day: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Analyze revenue by category.
    
    Args:
        period: Time period for analysis
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        year: Specific year
        month: Specific month (1-12)
        week: Specific week of month (1-5)
        day: Specific day of month (1-31)
    
    Returns:
        List of dictionaries with category revenue data
    """
    try:
        db = get_mongodb_connection()
        sales_collection = db['salesReport']
        
        date_range = get_date_range(period, start_date, end_date, year, month, week, day)
        
        # Query sales reports within date range
        sales_reports = sales_collection.find({
            'date': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            }
        })
        
        # Aggregate revenue by category
        category_revenue = defaultdict(lambda: {'revenue': 0, 'quantity': 0})
        
        for report in sales_reports:
            items = report.get('items', [])
            for item in items:
                category = item.get('category', 'Unknown')
                quantity = item.get('quantitySold', 0)
                price = item.get('price', 0)
                
                revenue = quantity * price
                category_revenue[category]['revenue'] += revenue
                category_revenue[category]['quantity'] += quantity
        
        # Convert to list and sort by revenue
        results = []
        for category, data in category_revenue.items():
            results.append({
                'category': category,
                'revenue': round(data['revenue'], 2),
                'quantity': data['quantity']
            })
        
        results.sort(key=lambda x: x['revenue'], reverse=True)
        
        return results
    
    except Exception as e:
        print(f"Error analyzing category revenue: {e}")
        return []


def get_sales_summary(period: str = 'monthly', start_date: Optional[str] = None, end_date: Optional[str] = None,
                     year: Optional[int] = None, month: Optional[int] = None,
                     week: Optional[int] = None, day: Optional[int] = None) -> Dict[str, Any]:
    """
    Get overall sales summary including total revenue, total orders, growth rates, etc.
    
    Args:
        period: Time period for analysis
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        year: Specific year
        month: Specific month (1-12)
        week: Specific week of month (1-5)
        day: Specific day of month (1-31)
    
    Returns:
        Dictionary with summary statistics
    """
    try:
        db = get_mongodb_connection()
        sales_collection = db['salesReport']
        
        date_range = get_date_range(period, start_date, end_date, year, month, week, day)
        
        # Query sales reports within date range
        sales_reports = list(sales_collection.find({
            'date': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            }
        }).sort('date', 1))
        
        if not sales_reports:
            return {
                'totalRevenue': 0,
                'totalOrders': 0,
                'averageOrderValue': 0,
                'averageDailyRevenue': 0,
                'growthRate': 0,
                'totalDays': 0
            }
        
        # Calculate totals
        # Use totalSales field from reports (this is the expected sales amount)
        total_sales = sum(report.get('totalSales', 0) for report in sales_reports)
        
        # Use totalOS field (this is the actual collected amount including online)
        total_os = sum(report.get('totalOS', 0) for report in sales_reports)
        
        # Calculate actual cash collected (denominations + online + charge slips)
        total_cash_collected = sum(calculate_total_revenue(report) for report in sales_reports)
        
        total_orders = sum(calculate_total_orders(report) for report in sales_reports)
        total_days = len(sales_reports)
        
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
        
        # Calculate gross revenue from items in orders (for reference)
        gross_revenue = 0.0
        for report in sales_reports:
            orders = report.get('orders', [])
            for order in orders:
                for item in order.get('items', []):
                    quantity = item.get('quantitySold', 0)
                    price = item.get('price', 0)
                    gross_revenue += quantity * price
        
        # Calculate overcollected and shorts separately per report
        total_overcollected = 0.0
        total_shorts = 0.0
        
        for report in sales_reports:
            report_total_os = report.get('totalOS', 0)
            report_total_sales = report.get('totalSales', 0)
            difference = report_total_os - report_total_sales
            
            if difference > 0:
                # OS is greater than Sales = Overcollected
                total_overcollected += difference
            elif difference < 0:
                # OS is less than Sales = Short
                total_shorts += abs(difference)
        
        # The cash variance is the difference between expected sales and actual collected
        # Positive = Shorts (collected less than expected), Negative = Overcollected (collected more than expected)
        cash_variance = total_sales - total_cash_collected
        
        avg_order_value = round(total_cash_collected / total_orders, 2) if total_orders > 0 else 0
        avg_daily_revenue = round(total_cash_collected / total_days, 2) if total_days > 0 else 0
        
        # Calculate growth rate (comparing first half vs second half)
        growth_rate = 0
        if len(sales_reports) >= 2:
            mid_point = len(sales_reports) // 2
            first_half = sales_reports[:mid_point]
            second_half = sales_reports[mid_point:]
            
            first_half_revenue = sum(calculate_total_revenue(report) for report in first_half)
            second_half_revenue = sum(calculate_total_revenue(report) for report in second_half)
            
            if first_half_revenue > 0:
                growth_rate = round(((second_half_revenue - first_half_revenue) / first_half_revenue) * 100, 2)
        
        return {
            'grossRevenue': round(gross_revenue, 2),
            'totalDiscounts': round(total_discounts, 2),
            'totalSales': round(total_sales, 2),  # Expected sales from report
            'totalOS': round(total_os, 2),  # What should be collected
            'totalRevenue': round(total_cash_collected, 2),  # Actual cash collected
            'cashVariance': round(cash_variance, 2),  # Difference between OS and actual cash
            'totalOvercollected': round(total_overcollected, 2),  # Sum of positive differences
            'totalShorts': round(total_shorts, 2),  # Sum of negative differences (absolute)
            'totalOrders': total_orders,
            'averageOrderValue': avg_order_value,
            'averageDailyRevenue': avg_daily_revenue,
            'growthRate': growth_rate,
            'totalDays': total_days,
            'startDate': date_range['start'].strftime('%Y-%m-%d'),
            'endDate': date_range['end'].strftime('%Y-%m-%d')
        }
    
    except Exception as e:
        print(f"Error getting sales summary: {e}")
        return {
            'totalRevenue': 0,
            'totalOrders': 0,
            'averageOrderValue': 0,
            'averageDailyRevenue': 0,
            'growthRate': 0,
            'totalDays': 0,
            'error': str(e)
        }


def analyze_top_selling_items(period: str = 'monthly', start_date: Optional[str] = None, end_date: Optional[str] = None,
                             year: Optional[int] = None, month: Optional[int] = None,
                             week: Optional[int] = None, day: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get top selling items by quantity and revenue.
    
    Args:
        period: Time period for analysis
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        year: Specific year
        month: Specific month (1-12)
        week: Specific week of month (1-5)
        day: Specific day of month (1-31)
        limit: Number of top items to return
    
    Returns:
        List of top selling items
    """
    try:
        db = get_mongodb_connection()
        sales_collection = db['salesReport']
        
        date_range = get_date_range(period, start_date, end_date, year, month, week, day)
        
        # Query sales reports within date range
        sales_reports = sales_collection.find({
            'date': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            }
        })
        
        # Aggregate items
        item_stats = defaultdict(lambda: {'quantity': 0, 'revenue': 0, 'category': ''})
        
        for report in sales_reports:
            items = report.get('items', [])
            for item in items:
                product_name = item.get('productName', 'Unknown')
                category = item.get('category', 'Unknown')
                quantity = item.get('quantitySold', 0)
                price = item.get('price', 0)
                
                item_stats[product_name]['quantity'] += quantity
                item_stats[product_name]['revenue'] += quantity * price
                item_stats[product_name]['category'] = category
        
        # Convert to list and sort
        results = []
        for product_name, data in item_stats.items():
            results.append({
                'productName': product_name,
                'category': data['category'],
                'totalQuantity': data['quantity'],
                'totalRevenue': round(data['revenue'], 2)
            })
        
        results.sort(key=lambda x: x['totalRevenue'], reverse=True)
        
        return results[:limit]
    
    except Exception as e:
        print(f"Error analyzing top selling items: {e}")
        return []


def analyze_hourly_distribution() -> Dict[str, Any]:
    """
    Analyze revenue distribution between morning and night shifts.
    
    Returns:
        Dictionary with morning and night revenue statistics
    """
    try:
        db = get_mongodb_connection()
        sales_collection = db['salesReport']
        
        # Get all sales reports
        sales_reports = sales_collection.find({})
        
        morning_total = 0
        night_total = 0
        
        for report in sales_reports:
            # Calculate morning revenue
            morning_denom = report.get('denominations', {}).get('morning', {})
            for denom_key, value in morning_denom.items():
                if denom_key.startswith('d'):
                    amount = int(denom_key[1:])
                    morning_total += amount * value
            
            morning_online = report.get('onlineTransaction', {}).get('morning', 0)
            morning_total += morning_online
            
            # Calculate night revenue
            night_denom = report.get('denominations', {}).get('night', {})
            for denom_key, value in night_denom.items():
                if denom_key.startswith('d'):
                    amount = int(denom_key[1:])
                    night_total += amount * value
            
            night_online = report.get('onlineTransaction', {}).get('night', 0)
            night_total += night_online
        
        total = morning_total + night_total
        morning_percentage = round((morning_total / total * 100), 2) if total > 0 else 0
        night_percentage = round((night_total / total * 100), 2) if total > 0 else 0
        
        return {
            'morning': {
                'revenue': round(morning_total, 2),
                'percentage': morning_percentage
            },
            'night': {
                'revenue': round(night_total, 2),
                'percentage': night_percentage
            },
            'total': round(total, 2)
        }
    
    except Exception as e:
        print(f"Error analyzing hourly distribution: {e}")
        return {
            'morning': {'revenue': 0, 'percentage': 0},
            'night': {'revenue': 0, 'percentage': 0},
            'total': 0
        }


def analyze_zero_sales_items(period: str = 'monthly', start_date: Optional[str] = None, end_date: Optional[str] = None,
                             year: Optional[int] = None, month: Optional[int] = None,
                             week: Optional[int] = None, day: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get items with zero sales in the specified period.
    
    Args:
        period: Time period for analysis
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        year: Specific year
        month: Specific month (1-12)
        week: Specific week of month (1-5)
        day: Specific day of month (1-31)
    
    Returns:
        List of items with zero sales
    """
    try:
        db = get_mongodb_connection()
        sales_collection = db['salesReport']
        menu_collection = db['menu']
        
        date_range = get_date_range(period, start_date, end_date, year, month, week, day)
        
        # Get all menu items
        all_menu_items = list(menu_collection.find({}, {
            '_id': 0,
            'productName': 1,
            'category': 1,
            'price': 1
        }))
        
        # Query sales reports within date range
        sales_reports = sales_collection.find({
            'date': {
                '$gte': date_range['start'],
                '$lte': date_range['end']
            }
        })
        
        # Get set of sold product names
        sold_items = set()
        for report in sales_reports:
            items = report.get('items', [])
            for item in items:
                product_name = item.get('productName', '')
                if product_name:
                    sold_items.add(product_name)
        
        # Find items not in sold_items
        zero_sales_items = []
        for menu_item in all_menu_items:
            product_name = menu_item.get('productName', '')
            if product_name and product_name not in sold_items:
                zero_sales_items.append({
                    'productName': product_name,
                    'category': menu_item.get('category', 'Unknown'),
                    'price': menu_item.get('price', 0)
                })
        
        # Sort by category and then by product name
        zero_sales_items.sort(key=lambda x: (x['category'], x['productName']))
        
        return zero_sales_items
    
    except Exception as e:
        print(f"Error analyzing zero sales items: {e}")
        return []


# Main function for testing
if __name__ == "__main__":
    print("Testing Sales Performance Algorithm")
    print("=" * 50)
    
    # Test revenue over time
    print("\n1. Revenue Over Time (Last 7 days):")
    revenue_data = analyze_revenue_over_time('daily')
    for entry in revenue_data:
        print(f"  {entry['date']} ({entry['dayOfWeek']}): ₱{entry['revenue']}, {entry['orders']} orders")
    
    # Test day of week performance
    print("\n2. Day of Week Performance:")
    dow_data = analyze_day_of_week_performance()
    for entry in dow_data:
        print(f"  {entry['dayOfWeek']}: Avg ₱{entry['averageRevenue']}, {entry['averageOrders']} orders")
    
    # Test sales summary
    print("\n3. Sales Summary:")
    summary = get_sales_summary('monthly')
    print(f"  Total Revenue: ₱{summary['totalRevenue']}")
    print(f"  Total Orders: {summary['totalOrders']}")
    print(f"  Avg Order Value: ₱{summary['averageOrderValue']}")
    print(f"  Growth Rate: {summary['growthRate']}%")
    
    # Test category revenue
    print("\n4. Category Revenue:")
    category_data = analyze_category_revenue('monthly')
    for entry in category_data[:5]:
        print(f"  {entry['category']}: ₱{entry['revenue']}")
    
    # Test top selling items
    print("\n5. Top Selling Items:")
    top_items = analyze_top_selling_items('monthly', limit=5)
    for entry in top_items:
        print(f"  {entry['productName']}: {entry['totalQuantity']} sold, ₱{entry['totalRevenue']}")
    
    # Test hourly distribution
    print("\n6. Hourly Distribution:")
    hourly_data = analyze_hourly_distribution()
    print(f"  Morning: ₱{hourly_data['morning']['revenue']} ({hourly_data['morning']['percentage']}%)")
    print(f"  Night: ₱{hourly_data['night']['revenue']} ({hourly_data['night']['percentage']}%)")
