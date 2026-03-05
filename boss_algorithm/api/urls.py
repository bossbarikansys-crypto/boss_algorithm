"""
URL configuration for API app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Items performance endpoints
    path('items-performance/', views.items_performance, name='items_performance'),
    path('items-performance/summary/', views.items_performance_summary, name='items_performance_summary'),
    path('items-performance/detail/', views.item_detail_performance, name='item_detail_performance'),
    path('category-performance/', views.category_performance, name='category_performance'),
    
    # Sales performance endpoints
    path('sales-performance/revenue/', views.sales_revenue_over_time, name='sales_revenue_over_time'),
    path('sales-performance/day-of-week/', views.sales_day_of_week, name='sales_day_of_week'),
    path('sales-performance/category-revenue/', views.sales_category_revenue, name='sales_category_revenue'),
    path('sales-performance/summary/', views.sales_summary, name='sales_summary'),
    path('sales-performance/top-items/', views.sales_top_items, name='sales_top_items'),
    path('sales-performance/zero-sales/', views.sales_zero_sales_items, name='sales_zero_sales_items'),
    path('sales-performance/hourly/', views.sales_hourly_distribution, name='sales_hourly_distribution'),
    
    # Inventory comparison endpoints
    path('inventory-comparison/', views.inventory_comparison, name='inventory_comparison'),
    path('inventory-comparison/range/', views.inventory_comparison_range, name='inventory_comparison_range'),
]
