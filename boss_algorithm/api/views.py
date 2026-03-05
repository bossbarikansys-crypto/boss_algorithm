from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import sys
import os

# Add the parent directory to the path to import itemsAlgo
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from itemsAlgo import (
        analyze_sales_data,
        get_item_performance_summary,
        get_category_performance,
        get_individual_item_performance
    )
except ImportError as e:
    print(f"Error importing itemsAlgo: {e}")
    # Define fallback functions
    def analyze_sales_data(period='daily', show_sold_only=False):
        return []
    def get_item_performance_summary(period='daily'):
        return {}
    def get_category_performance(period='daily'):
        return []
    def get_individual_item_performance(product_name, period='monthly', year=None, month=None):
        return {}

# Import sales performance functions
try:
    from salesAlgo import (
        analyze_revenue_over_time,
        analyze_day_of_week_performance,
        analyze_category_revenue,
        get_sales_summary,
        analyze_top_selling_items,
        analyze_hourly_distribution,
        analyze_zero_sales_items
    )
except ImportError as e:
    print(f"Error importing salesAlgo: {e}")
    # Define fallback functions
    def analyze_revenue_over_time(period='daily', start_date=None, end_date=None):
        return []
    def analyze_day_of_week_performance():
        return []
    def analyze_category_revenue(period='monthly', start_date=None, end_date=None):
        return []
    def get_sales_summary(period='monthly', start_date=None, end_date=None):
        return {}
    def analyze_top_selling_items(period='monthly', start_date=None, end_date=None, limit=10):
        return []
    def analyze_hourly_distribution():
        return {}
    def analyze_zero_sales_items(period='monthly', start_date=None, end_date=None):
        return []

# Import inventory comparison functions
try:
    from itemsInv import (
        analyze_inventory_comparison,
        get_date_range_comparison
    )
except ImportError as e:
    print(f"Error importing itemsInv: {e}")
    # Define fallback functions
    def analyze_inventory_comparison(date, inventory_type='dining'):
        return {'success': False, 'error': 'itemsInv module not available'}
    def get_date_range_comparison(start_date, end_date, inventory_type='dining'):
        return [{'success': False, 'error': 'itemsInv module not available'}]


@csrf_exempt
@require_http_methods(["GET"])
def items_performance(request):
    """
    API endpoint to get items performance data.
    
    Query parameters:
    - period: 'daily', 'weekly', or 'monthly' (default: 'daily')
    - show_sold_only: 'true' or 'false' (default: 'false')
    - week: week number (1-5) for weekly period
    - day: day number (1-31) for daily period
    - month: month number (1-12) for monthly period
    """
    try:
        # Get query parameters
        period = request.GET.get('period', 'daily').lower()
        show_sold_only_param = request.GET.get('show_sold_only', 'false').lower()
        show_sold_only = show_sold_only_param == 'true'
        week_param = request.GET.get('week', None)
        day_param = request.GET.get('day', None)
        month_param = request.GET.get('month', None)
        week_number = int(week_param) if week_param else None
        day_number = int(day_param) if day_param else None
        month_number = int(month_param) if month_param else None
        
        print(f"API called - period: {period}, show_sold_only: {show_sold_only}, week: {week_number}, day: {day_number}, month: {month_number}")
        
        # Validate period parameter
        if period not in ['daily', 'weekly', 'monthly']:
            return JsonResponse({
                'error': 'Invalid period. Must be daily, weekly, or monthly.'
            }, status=400)
        
        # Get items performance data
        items_data = analyze_sales_data(
            period=period, 
            show_sold_only=show_sold_only, 
            week_number=week_number,
            day_number=day_number,
            month_number=month_number
        )
        
        print(f"Retrieved {len(items_data)} items")
        
        # Get date range for the period
        from itemsAlgo import get_date_range
        date_range = get_date_range(period, week_number=week_number, day_number=day_number, month_number=month_number)
        
        print(f"Date range: {date_range['start']} to {date_range['end']}")
        
        return JsonResponse({
            'success': True,
            'period': period,
            'show_sold_only': show_sold_only,
            'week_number': week_number,
            'day_number': day_number,
            'month_number': month_number,
            'total_items': len(items_data),
            'dateRange': {
                'start': date_range['start'].isoformat(),
                'end': date_range['end'].isoformat()
            },
            'items': items_data
        }, safe=False)
        
    except Exception as e:
        print(f"Error in items_performance: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def items_performance_summary(request):
    """
    API endpoint to get items performance summary.
    
    Query parameters:
    - period: 'daily', 'weekly', or 'monthly' (default: 'daily')
    - week: week number (1-5) for weekly period
    - day: day number (1-31) for daily period
    - month: month number (1-12) for monthly period
    """
    try:
        # Get query parameters
        period = request.GET.get('period', 'daily').lower()
        week_param = request.GET.get('week', None)
        day_param = request.GET.get('day', None)
        month_param = request.GET.get('month', None)
        week_number = int(week_param) if week_param else None
        day_number = int(day_param) if day_param else None
        month_number = int(month_param) if month_param else None
        
        # Validate period parameter
        if period not in ['daily', 'weekly', 'monthly']:
            return JsonResponse({
                'error': 'Invalid period. Must be daily, weekly, or monthly.'
            }, status=400)
        
        # Get summary data
        summary_data = get_item_performance_summary(
            period=period,
            week_number=week_number,
            day_number=day_number,
            month_number=month_number
        )
        
        # Convert datetime objects to strings for JSON serialization
        if 'dateRange' in summary_data:
            summary_data['dateRange'] = {
                'start': summary_data['dateRange']['start'].isoformat(),
                'end': summary_data['dateRange']['end'].isoformat()
            }
        
        return JsonResponse({
            'success': True,
            **summary_data
        }, safe=False)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def category_performance(request):
    """
    API endpoint to get category performance data.
    
    Query parameters:
    - period: 'daily', 'weekly', or 'monthly' (default: 'daily')
    """
    try:
        # Get query parameters
        period = request.GET.get('period', 'daily').lower()
        
        # Validate period parameter
        if period not in ['daily', 'weekly', 'monthly']:
            return JsonResponse({
                'error': 'Invalid period. Must be daily, weekly, or monthly.'
            }, status=400)
        
        # Get category performance data
        category_data = get_category_performance(period=period)
        
        return JsonResponse({
            'success': True,
            'period': period,
            'total_categories': len(category_data),
            'categories': category_data
        }, safe=False)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def item_detail_performance(request):
    """
    API endpoint to get detailed performance data for a specific item.
    
    Query parameters:
    - product_name: Name of the product (required)
    - period: 'daily', 'weekly', or 'monthly' (default: 'monthly')
    - year: Year to analyze (default: current year)
    - month: Month to analyze for daily/weekly (default: current month)
    """
    try:
        # Get query parameters
        product_name = request.GET.get('product_name', None)
        
        if not product_name:
            return JsonResponse({
                'success': False,
                'error': 'product_name parameter is required'
            }, status=400)
        
        period = request.GET.get('period', 'monthly').lower()
        year_param = request.GET.get('year', None)
        month_param = request.GET.get('month', None)
        
        year = int(year_param) if year_param else None
        month = int(month_param) if month_param else None
        
        # Validate period parameter
        if period not in ['daily', 'weekly', 'monthly']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid period. Must be daily, weekly, or monthly.'
            }, status=400)
        
        print(f"Fetching item detail for: {product_name}, period: {period}, year: {year}, month: {month}")
        
        # Get detailed item performance data
        item_data = get_individual_item_performance(
            product_name=product_name,
            period=period,
            year=year,
            month=month
        )
        
        return JsonResponse({
            'success': True,
            **item_data
        }, safe=False)
        
    except Exception as e:
        print(f"Error in item_detail_performance: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Sales Performance Endpoints

@csrf_exempt
@require_http_methods(["GET"])
def sales_revenue_over_time(request):
    """
    API endpoint to get revenue data over time.
    
    Query parameters:
    - period: 'daily', 'weekly', 'monthly', 'custom', 'specific_month', 'specific_week', 'specific_day'
    - start_date: Start date for custom period (YYYY-MM-DD)
    - end_date: End date for custom period (YYYY-MM-DD)
    - year: Specific year
    - month: Specific month (1-12)
    - week: Specific week of month (1-5)
    - day: Specific day of month (1-31)
    """
    try:
        period = request.GET.get('period', 'daily').lower()
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        year = int(request.GET.get('year')) if request.GET.get('year') else None
        month = int(request.GET.get('month')) if request.GET.get('month') else None
        week = int(request.GET.get('week')) if request.GET.get('week') else None
        day = int(request.GET.get('day')) if request.GET.get('day') else None
        
        if period not in ['daily', 'weekly', 'monthly', 'custom', 'specific_month', 'specific_week', 'specific_day']:
            return JsonResponse({
                'error': 'Invalid period.'
            }, status=400)
        
        revenue_data = analyze_revenue_over_time(
            period=period, start_date=start_date, end_date=end_date,
            year=year, month=month, week=week, day=day
        )
        
        return JsonResponse({
            'success': True,
            'period': period,
            'data': revenue_data
        }, safe=False)
        
    except Exception as e:
        print(f"Error in sales_revenue_over_time: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def sales_day_of_week(request):
    """
    API endpoint to get average performance by day of week.
    """
    try:
        dow_data = analyze_day_of_week_performance()
        
        return JsonResponse({
            'success': True,
            'data': dow_data
        }, safe=False)
        
    except Exception as e:
        print(f"Error in sales_day_of_week: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def sales_category_revenue(request):
    """
    API endpoint to get revenue by category.
    
    Query parameters:
    - period: Period type
    - start_date: Start date for custom period (YYYY-MM-DD)
    - end_date: End date for custom period (YYYY-MM-DD)
    - year: Specific year
    - month: Specific month (1-12)
    - week: Specific week of month (1-5)
    - day: Specific day of month (1-31)
    """
    try:
        period = request.GET.get('period', 'monthly').lower()
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        year = int(request.GET.get('year')) if request.GET.get('year') else None
        month = int(request.GET.get('month')) if request.GET.get('month') else None
        week = int(request.GET.get('week')) if request.GET.get('week') else None
        day = int(request.GET.get('day')) if request.GET.get('day') else None
        
        category_data = analyze_category_revenue(
            period=period, start_date=start_date, end_date=end_date,
            year=year, month=month, week=week, day=day
        )
        
        return JsonResponse({
            'success': True,
            'period': period,
            'data': category_data
        }, safe=False)
        
    except Exception as e:
        print(f"Error in sales_category_revenue: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def sales_summary(request):
    """
    API endpoint to get overall sales summary.
    
    Query parameters:
    - period: Period type
    - start_date: Start date for custom period (YYYY-MM-DD)
    - end_date: End date for custom period (YYYY-MM-DD)
    - year: Specific year
    - month: Specific month (1-12)
    - week: Specific week of month (1-5)
    - day: Specific day of month (1-31)
    """
    try:
        period = request.GET.get('period', 'monthly').lower()
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        year = int(request.GET.get('year')) if request.GET.get('year') else None
        month = int(request.GET.get('month')) if request.GET.get('month') else None
        week = int(request.GET.get('week')) if request.GET.get('week') else None
        day = int(request.GET.get('day')) if request.GET.get('day') else None
        
        summary_data = get_sales_summary(
            period=period, start_date=start_date, end_date=end_date,
            year=year, month=month, week=week, day=day
        )
        
        return JsonResponse({
            'success': True,
            'period': period,
            'summary': summary_data
        }, safe=False)
        
    except Exception as e:
        print(f"Error in sales_summary: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def sales_top_items(request):
    """
    API endpoint to get top selling items.
    
    Query parameters:
    - period: Period type
    - start_date: Start date for custom period (YYYY-MM-DD)
    - end_date: End date for custom period (YYYY-MM-DD)
    - year: Specific year
    - month: Specific month (1-12)
    - week: Specific week of month (1-5)
    - day: Specific day of month (1-31)
    - limit: Number of items to return (default: 10)
    """
    try:
        period = request.GET.get('period', 'monthly').lower()
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        year = int(request.GET.get('year')) if request.GET.get('year') else None
        month = int(request.GET.get('month')) if request.GET.get('month') else None
        week = int(request.GET.get('week')) if request.GET.get('week') else None
        day = int(request.GET.get('day')) if request.GET.get('day') else None
        limit = int(request.GET.get('limit', 10))
        
        top_items = analyze_top_selling_items(
            period=period, start_date=start_date, end_date=end_date,
            year=year, month=month, week=week, day=day, limit=limit
        )
        
        return JsonResponse({
            'success': True,
            'period': period,
            'data': top_items
        }, safe=False)
        
    except Exception as e:
        print(f"Error in sales_top_items: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def sales_zero_sales_items(request):
    """
    API endpoint to get items with zero sales in the period.
    
    Query parameters:
    - period: Period type
    - start_date: Start date for custom period (YYYY-MM-DD)
    - end_date: End date for custom period (YYYY-MM-DD)
    - year: Specific year
    - month: Specific month (1-12)
    - week: Specific week of month (1-5)
    - day: Specific day of month (1-31)
    """
    try:
        period = request.GET.get('period', 'monthly').lower()
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        year = int(request.GET.get('year')) if request.GET.get('year') else None
        month = int(request.GET.get('month')) if request.GET.get('month') else None
        week = int(request.GET.get('week')) if request.GET.get('week') else None
        day = int(request.GET.get('day')) if request.GET.get('day') else None
        
        zero_sales_items = analyze_zero_sales_items(
            period=period, start_date=start_date, end_date=end_date,
            year=year, month=month, week=week, day=day
        )
        
        return JsonResponse({
            'success': True,
            'period': period,
            'data': zero_sales_items
        }, safe=False)
        
    except Exception as e:
        print(f"Error in sales_zero_sales_items: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def sales_hourly_distribution(request):
    """
    API endpoint to get revenue distribution by shift (morning/night).
    Accepts the same period query params as other sales endpoints.
    """
    try:
        period = request.GET.get('period', 'daily').lower()
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        year = int(request.GET.get('year')) if request.GET.get('year') else None
        month = int(request.GET.get('month')) if request.GET.get('month') else None
        week = int(request.GET.get('week')) if request.GET.get('week') else None
        day = int(request.GET.get('day')) if request.GET.get('day') else None

        hourly_data = analyze_hourly_distribution(
            period=period,
            start_date=start_date,
            end_date=end_date,
            year=year,
            month=month,
            week=week,
            day=day
        )
        
        return JsonResponse({
            'success': True,
            'data': hourly_data
        }, safe=False)
        
    except Exception as e:
        print(f"Error in sales_hourly_distribution: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Inventory Comparison Endpoints

@csrf_exempt
@require_http_methods(["GET"])
def inventory_comparison(request):
    """
    API endpoint to compare inventory with sales data based on product composition.
    
    Query parameters:
    - date: Date to analyze in YYYY-MM-DD format (required)
    - inventory_type: 'dining' or 'kitchen' (default: 'dining')
    - shift: Optional shift filter 'day' or 'night' (default: None for full day)
    
    This endpoint compares:
    - If shift='day': Day shift initial to day shift final inventory
    - If shift='night': Night shift initial to night shift final inventory
    - If shift not specified: Day shift initial to night shift final inventory (full day)
    - Expected consumption based on items sold and their composition
    
    Returns:
    - Items sold during the selected shift(s)
    - Expected consumption per inventory item
    - Actual inventory changes
    - Discrepancies between expected and actual consumption
    """
    try:
        # Get query parameters
        date = request.GET.get('date', None)
        inventory_type = request.GET.get('inventory_type', 'dining').lower()
        shift = request.GET.get('shift', None)
        
        if not date:
            return JsonResponse({
                'success': False,
                'error': 'date parameter is required (format: YYYY-MM-DD)'
            }, status=400)
        
        if inventory_type not in ['dining', 'kitchen']:
            return JsonResponse({
                'success': False,
                'error': 'inventory_type must be either "dining" or "kitchen"'
            }, status=400)
        
        # Validate shift parameter if provided
        if shift and shift not in ['day', 'night']:
            return JsonResponse({
                'success': False,
                'error': 'shift must be either "day" or "night" if provided'
            }, status=400)
        
        # Validate date format
        from datetime import datetime
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }, status=400)
        
        print(f"Analyzing inventory comparison for date: {date}, type: {inventory_type}, shift: {shift or 'full day'}")
        
        # Get inventory comparison data
        result = analyze_inventory_comparison(date, inventory_type, shift)
        
        return JsonResponse(result, safe=False)
        
    except Exception as e:
        print(f"Error in inventory_comparison: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def inventory_comparison_range(request):
    """
    API endpoint to compare inventory for a date range.
    
    Query parameters:
    - start_date: Start date in YYYY-MM-DD format (required)
    - end_date: End date in YYYY-MM-DD format (required)
    - inventory_type: 'dining' or 'kitchen' (default: 'dining')
    
    Returns:
    - List of comparison results for each date in the range
    """
    try:
        # Get query parameters
        start_date = request.GET.get('start_date', None)
        end_date = request.GET.get('end_date', None)
        inventory_type = request.GET.get('inventory_type', 'dining').lower()
        
        if not start_date or not end_date:
            return JsonResponse({
                'success': False,
                'error': 'start_date and end_date parameters are required (format: YYYY-MM-DD)'
            }, status=400)
        
        if inventory_type not in ['dining', 'kitchen']:
            return JsonResponse({
                'success': False,
                'error': 'inventory_type must be either "dining" or "kitchen"'
            }, status=400)
        
        # Validate date formats
        from datetime import datetime
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD'
            }, status=400)
        
        print(f"Analyzing inventory comparison range: {start_date} to {end_date}, type: {inventory_type}")
        
        # Get inventory comparison data for date range
        results = get_date_range_comparison(start_date, end_date, inventory_type)
        
        return JsonResponse({
            'success': True,
            'start_date': start_date,
            'end_date': end_date,
            'inventory_type': inventory_type,
            'total_days': len(results),
            'results': results
        }, safe=False)
        
    except Exception as e:
        print(f"Error in inventory_comparison_range: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

