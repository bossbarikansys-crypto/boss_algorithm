"""
Inventory Comparison Algorithm

This module compares sold items with inventory changes to validate if the actual
inventory consumption matches the expected consumption based on product composition.

It analyzes:
1. Items sold during the day (from Sales data)
2. Product composition (ingredients/components used per item)
3. Day shift initial inventory vs Night shift final inventory
4. Calculates expected vs actual inventory changes
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
            'mongodb+srv://dbUser:bossbarikan@barikandb.rsrkuro.mongodb.net/'
        )
        
        client = MongoClient(mongodb_uri)
        return client
    except Exception as e:
        print(f"Error connecting to MongoDB: {str(e)}")
        raise


def get_sales_for_date(date: str, shift: Optional[str] = None) -> tuple[Dict[str, int], List[Dict[str, Any]]]:
    """
    Get all sales data for a specific date, optionally filtered by shift.
    
    Args:
        date: Date string in format YYYY-MM-DD
        shift: Optional shift filter ('day' or 'night'). If None, returns all sales.
    
    Returns:
        Tuple of:
        - Dictionary mapping product names to quantities sold
        - List of detailed sales items with compositionBreakdown and isSpecialItem flags
    """
    try:
        client = get_mongodb_connection()
        db = client['Sales']
        sales_collection = db['salesReport']
        
        # Parse the date
        target_date = datetime.strptime(date, '%Y-%m-%d')
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        print(f"Querying sales for date range: {start_date} to {end_date}")
        
        # Query sales for this date
        sales_query = {
            'date': {
                '$gte': start_date,
                '$lte': end_date
            }
        }
        
        sales_docs = list(sales_collection.find(sales_query))
        print(f"Found {len(sales_docs)} sales documents")
        
        # Extract all items sold and detailed items info
        items_sold = defaultdict(int)
        detailed_sales = []
        
        for sale_doc in sales_docs:
            if 'orders' in sale_doc:
                for order in sale_doc['orders']:
                    # Filter by shift if specified
                    order_shift = order.get('shift')
                    if shift and order_shift != shift:
                        # Skip this order if shift filter is specified and doesn't match
                        # For backward compatibility, if order_shift is None, include it
                        if order_shift is not None:
                            continue
                    
                    if 'items' in order:
                        for item in order['items']:
                            product_name = item.get('productName', '')
                            quantity = item.get('quantitySold', 0)
                            if product_name and quantity:
                                items_sold[product_name] += quantity
                                
                                # Store detailed item info
                                detailed_item = {
                                    'productName': product_name,
                                    'category': item.get('category', ''),
                                    'quantitySold': quantity,
                                    'isSpecialItem': item.get('isSpecialItem', False),
                                    'compositionBreakdown': item.get('compositionBreakdown', [])
                                }
                                detailed_sales.append(detailed_item)
        
        shift_msg = f" ({shift} shift)" if shift else ""
        print(f"Found {len(items_sold)} unique items sold on {date}{shift_msg}")
        print(f"Items sold details: {dict(items_sold)}")
        
        # Check for special items
        special_items_count = sum(1 for item in detailed_sales if item.get('isSpecialItem'))
        if special_items_count > 0:
            print(f"Found {special_items_count} special item entries with compositionBreakdown")
        
        return dict(items_sold), detailed_sales
    
    except Exception as e:
        print(f"Error fetching sales data: {str(e)}")
        raise


def get_product_compositions() -> Dict[str, Dict[str, Any]]:
    """
    Get all product compositions from the database.
    
    Returns:
        Dictionary mapping menu item names to their composition details
    """
    try:
        client = get_mongodb_connection()
        db = client['Sales']
        composition_collection = db['productComposition']
        
        compositions_docs = list(composition_collection.find({}))
        
        # Build a lookup dictionary
        compositions = {}
        for doc in compositions_docs:
            menu_item_name = doc.get('menuItemName', '')
            composition_items = doc.get('compositionItems', [])
            
            if menu_item_name:
                compositions[menu_item_name] = {
                    'menuItemId': doc.get('menuItemId', ''),
                    'compositionItems': composition_items
                }
        
        print(f"Found {len(compositions)} product compositions")
        
        # Debug: Show a sample of compositions
        if compositions:
            sample_key = list(compositions.keys())[0]
            print(f"Sample composition - Menu item: {sample_key}")
            sample_comp = compositions[sample_key]
            if sample_comp.get('compositionItems'):
                print(f"  Composition items: {sample_comp['compositionItems'][:2]}")  # Show first 2 items
        
        return compositions
    
    except Exception as e:
        print(f"Error fetching product compositions: {str(e)}")
        raise


def detect_restocks(initial_inventory: Dict[str, Dict[str, float]], final_inventory: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """
    Detect restocks by comparing initial and final inventory.
    If final > initial, it means items were restocked.
    
    Args:
        initial_inventory: Initial inventory quantities
        final_inventory: Final inventory quantities
    
    Returns:
        Dictionary with restock quantities per category and item
    """
    restocks = defaultdict(lambda: defaultdict(float))
    
    # Get all categories from both inventories
    all_categories = set(initial_inventory.keys()) | set(final_inventory.keys())
    
    for category in all_categories:
        initial_items = initial_inventory.get(category, {})
        final_items = final_inventory.get(category, {})
        
        # Get all items in this category
        all_items = set(initial_items.keys()) | set(final_items.keys())
        
        for item_name in all_items:
            initial_qty = initial_items.get(item_name, 0)
            final_qty = final_items.get(item_name, 0)
            
            # If final > initial, items were restocked
            if final_qty > initial_qty:
                restock_qty = final_qty - initial_qty
                restocks[category][item_name] = restock_qty
                print(f"    Restock detected: {item_name} ({category}): +{restock_qty}")
    
    return dict(restocks)


def format_quantity(quantity: float, category: str = '') -> float:
    """
    Format quantity based on category.
    Cigarettes keep decimals, others show whole numbers for .0 values.
    
    Args:
        quantity: The quantity to format
        category: The category name
    
    Returns:
        Formatted quantity
    """
    if category.lower() == 'cigarettes' or 'cigarette' in category.lower():
        # Cigarettes keep decimals
        formatted = round(quantity, 2)
        # Return as int if it's a whole number, otherwise keep decimal
        return int(formatted) if formatted == int(formatted) else formatted
    else:
        # Other categories: show whole numbers for .0 values
        formatted = round(quantity, 1)
        return int(formatted) if formatted == int(formatted) else formatted


def get_inventory_for_shift(date: str, shift: str, inventory_time: str, inventory_type: str = 'dining') -> Dict[str, Any]:
    """
    Get inventory data for a specific shift and time.
    
    Args:
        date: Date string in format YYYY-MM-DD
        shift: 'day' or 'night'
        inventory_time: 'Initial' or 'Final'
        inventory_type: 'dining' or 'kitchen'
    
    Returns:
        Dictionary with inventory categories and items
    """
    try:
        client = get_mongodb_connection()
        db = client['Inventory']  # Inventory data is in Inventory database
        
        # Select collection based on inventory type
        collection_name = 'Dining' if inventory_type == 'dining' else 'Kitchen'
        inventory_collection = db[collection_name]
        
        # Parse the date
        target_date = datetime.strptime(date, '%Y-%m-%d')
        start_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Query inventory
        inventory_query = {
            'date': {
                '$gte': start_date,
                '$lte': end_date
            },
            'shift': shift,
            'inventoryTime': inventory_time
        }
        
        inventory_doc = inventory_collection.find_one(inventory_query)
        
        if inventory_doc:
            print(f"Found {shift} shift {inventory_time} inventory for {date}")
            return inventory_doc
        else:
            print(f"No {shift} shift {inventory_time} inventory found for {date}")
            return {'categories': {}}
    
    except Exception as e:
        print(f"Error fetching inventory data: {str(e)}")
        raise


def calculate_expected_consumption(items_sold: Dict[str, int], compositions: Dict[str, Dict[str, Any]], detailed_sales: List[Dict[str, Any]] = None) -> tuple[Dict[str, Dict[str, float]], Dict[str, Any]]:
    """
    Calculate actual inventory usage based on items sold and their compositions.
    This represents what SHOULD have been consumed based on sales (Actual Usage).
    For special items (isSpecialItem=true), uses compositionBreakdown from sales report directly.
    
    Args:
        items_sold: Dictionary mapping product names to quantities sold
        compositions: Dictionary mapping product names to their composition details
        detailed_sales: List of detailed sales items with compositionBreakdown and isSpecialItem flags
    
    Returns:
        Tuple of:
        - Dictionary with actual usage requirements per category and inventory item (based on compositions)
        - Dictionary with special items breakdown information
    """
    expected_consumption = defaultdict(lambda: defaultdict(float))
    special_items_breakdown = defaultdict(lambda: defaultdict(float))
    
    print(f"\n=== Calculating Actual Usage (from Sales & Compositions) ===")
    print(f"Menu items sold: {list(items_sold.keys())}")
    
    # Create a mapping of product names to their special item info
    special_items_map = {}
    if detailed_sales:
        for item in detailed_sales:
            product_name = item.get('productName', '')
            if item.get('isSpecialItem') and item.get('compositionBreakdown'):
                if product_name not in special_items_map:
                    special_items_map[product_name] = []
                special_items_map[product_name].append(item)
    
    for product_name, quantity_sold in items_sold.items():
        # Check if this is a special item with compositionBreakdown
        if product_name in special_items_map:
            print(f"\n  Menu item '{product_name}' (sold: {quantity_sold}) - SPECIAL ITEM DETECTED")
            print(f"    Using compositionBreakdown from sales report instead of product composition")
            
            # Process each sale instance of this special item
            for special_item in special_items_map[product_name]:
                qty = special_item.get('quantitySold', 0)
                composition_breakdown = special_item.get('compositionBreakdown', [])
                
                print(f"    Processing {qty} unit(s) with {len(composition_breakdown)} composed items")
                
                for comp_item in composition_breakdown:
                    composed_item_name = comp_item.get('composedItem', '')
                    quantity_used = comp_item.get('quantityUsed', 0)
                    
                    if composed_item_name and quantity_used:
                        # Check if this composed item has a product composition
                        # (e.g., "RED HORSE" menu item -> "RED HORSE STALLION" inventory item)
                        if composed_item_name in compositions:
                            print(f"      -> {composed_item_name}: {quantity_used} × {qty} = {qty * quantity_used}")
                            print(f"         (Found composition for '{composed_item_name}', using its inventory items)")
                            
                            # Use the composition of this menu item to get actual inventory items
                            sub_composition = compositions[composed_item_name]
                            sub_composition_items = sub_composition.get('compositionItems', [])
                            
                            for sub_comp_item in sub_composition_items:
                                inv_item_name = sub_comp_item.get('inventoryItemName', '')
                                inv_category = sub_comp_item.get('inventoryCategory', '')
                                item_quantity = sub_comp_item.get('quantity', 0)
                                
                                # Calculate total consumption: special_item_qty × composed_item_qty × inventory_item_qty
                                total_consumption = qty * quantity_used * item_quantity
                                expected_consumption[inv_category][inv_item_name] += total_consumption
                                
                                # Track breakdown at inventory item level
                                # So "PALE PILSEN" shows that it was used in "MIXED BUCKET"
                                special_items_breakdown[product_name][inv_item_name] += total_consumption
                                
                                print(f"            -> {inv_item_name} ({inv_category}): {item_quantity} × {quantity_used} × {qty} = {total_consumption}")
                        else:
                            # Composed item doesn't have a composition, treat as direct inventory item
                            # Track special item breakdown for the composed item (e.g., "RED HORSE")
                            special_items_breakdown[product_name][composed_item_name] += qty * quantity_used
                            # The category will be determined when we match it with inventory
                            expected_consumption['_special_items'][composed_item_name] += qty * quantity_used
                            print(f"      -> {composed_item_name}: {quantity_used} × {qty} = {qty * quantity_used}")
                            print(f"         (No composition found, will match with inventory later)")
        
        elif product_name in compositions:
            # Normal item - use product composition from database
            composition = compositions[product_name]
            composition_items = composition.get('compositionItems', [])
            
            print(f"\n  Menu item '{product_name}' (sold: {quantity_sold})")
            print(f"    Has {len(composition_items)} inventory items in composition")
            
            for comp_item in composition_items:
                inv_item_name = comp_item.get('inventoryItemName', '')
                inv_category = comp_item.get('inventoryCategory', '')
                item_quantity = comp_item.get('quantity', 0)
                
                # Calculate total consumption for this inventory item
                total_consumption = quantity_sold * item_quantity
                expected_consumption[inv_category][inv_item_name] += total_consumption
                
                print(f"      -> {inv_item_name} ({inv_category}): {item_quantity} × {quantity_sold} = {total_consumption}")
        else:
            print(f"\n  Menu item '{product_name}' (sold: {quantity_sold}) - NO COMPOSITION FOUND")
    
    print(f"\nTotal actual usage requirements (from compositions) by category:")
    for cat, items in expected_consumption.items():
        print(f"  {cat}: {len(items)} items")
    
    if special_items_breakdown:
        print(f"\n!!! SPECIAL ITEMS BREAKDOWN:")
        for special_item, breakdown in special_items_breakdown.items():
            print(f"  {special_item}:")
            for composed_item, qty in breakdown.items():
                print(f"    - {composed_item}: {qty}")
    
    special_items_info = {
        'breakdown': dict(special_items_breakdown),
        'count': len(special_items_breakdown)
    }
    
    return dict(expected_consumption), special_items_info


def get_inventory_quantities(inventory_doc: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """
    Extract inventory quantities from inventory document.
    
    Args:
        inventory_doc: Inventory document from MongoDB
    
    Returns:
        Dictionary with quantities per category and item
        Format: {category: {item_name: quantity}}
    """
    inventory_quantities = defaultdict(lambda: defaultdict(float))
    
    if 'categories' in inventory_doc:
        for category, items in inventory_doc['categories'].items():
            if isinstance(items, list):
                for item in items:
                    product_name = item.get('productName', '')
                    quantity = item.get('quantity', 0)
                    quantity_is_no_record = item.get('quantityIsNoRecord', False)
                    
                    # If no record, treat as 0
                    if quantity_is_no_record:
                        quantity = 0
                    else:
                        # Handle both numeric and string quantities (Kitchen uses strings)
                        if isinstance(quantity, str):
                            try:
                                quantity = float(quantity) if quantity.strip() else 0
                            except (ValueError, AttributeError):
                                quantity = 0
                        elif quantity is None:
                            quantity = 0
                    
                    if product_name:
                        inventory_quantities[category][product_name] = quantity
    
    # Debug: Show what was loaded
    if inventory_quantities:
        print(f"  Loaded inventory quantities for {len(inventory_quantities)} categories")
        for cat, items in inventory_quantities.items():
            print(f"    Category '{cat}': {len(items)} items")
    else:
        print(f"  No inventory quantities loaded (empty or missing categories)")
    
    return dict(inventory_quantities)


def has_meaningful_inventory(inventory_quantities: Dict[str, Dict[str, float]]) -> bool:
    """
    Check if inventory data has meaningful content (not just empty categories).
    
    Args:
        inventory_quantities: Dictionary with quantities per category and item
    
    Returns:
        True if there is at least one item with a quantity, False otherwise
    """
    if not inventory_quantities:
        return False
    
    for category, items in inventory_quantities.items():
        if items:  # If category has any items
            return True
    
    return False


def match_special_items_to_inventory(expected_consumption: Dict[str, Dict[str, float]], inventory: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    """
    Match special items (from _special_items category) to their actual inventory categories.
    
    Args:
        expected_consumption: Expected consumption with _special_items category
        inventory: Inventory data with actual categories
    
    Returns:
        Updated expected_consumption with special items moved to their proper categories
    """
    if '_special_items' not in expected_consumption:
        return expected_consumption
    
    print("\n--- Matching Special Items to Inventory Categories ---")
    special_items = expected_consumption.get('_special_items', {})
    
    for item_name, quantity in special_items.items():
        found = False
        for category, items in inventory.items():
            if item_name in items:
                print(f"  Found '{item_name}' in category '{category}' - adding {quantity} to expected consumption")
                expected_consumption[category][item_name] += quantity
                found = True
                break
        
        if not found:
            print(f"  Warning: '{item_name}' not found in any inventory category")
    
    # Remove the _special_items category
    del expected_consumption['_special_items']
    
    return expected_consumption


def compare_inventory_with_expected(
    day_initial: Dict[str, Dict[str, float]],
    day_final: Dict[str, Dict[str, float]],
    night_initial: Dict[str, Dict[str, float]],
    night_final: Dict[str, Dict[str, float]],
    expected_consumption: Dict[str, Dict[str, float]],
    special_items_info: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Compare expected usage (from inventory changes) with actual usage (from sales compositions).
    Takes into account restocks during day and night shifts.
    
    Expected Usage = (Day Initial + Restocks) - Night Final (what inventory says was consumed)
    Actual Usage = Based on product compositions and sales (what SHOULD have been consumed)
    Discrepancy = Actual Usage - Expected Usage
    
    Negative discrepancy = Less sold than consumed from inventory = shortage/missing items
    Positive discrepancy = More sold than consumed from inventory = overstock/surplus
    
    Args:
        day_initial: Day shift initial inventory quantities
        day_final: Day shift final inventory quantities
        night_initial: Night shift initial inventory quantities
        night_final: Night shift final inventory quantities
        expected_consumption: Actual usage requirements based on sales compositions
        special_items_info: Information about special items breakdown
    
    Returns:
        Dictionary with comparison results including discrepancies
    """
    # Detect restocks during day shift
    print("\n--- Detecting Day Shift Restocks ---")
    day_restocks = detect_restocks(day_initial, day_final)
    
    # Detect restocks during night shift
    print("\n--- Detecting Night Shift Restocks ---")
    night_restocks = detect_restocks(night_initial, night_final)
    
    # Combine restocks
    total_restocks = defaultdict(lambda: defaultdict(float))
    for category in set(list(day_restocks.keys()) + list(night_restocks.keys())):
        for item_name in set(list(day_restocks.get(category, {}).keys()) + list(night_restocks.get(category, {}).keys())):
            total_restocks[category][item_name] = day_restocks.get(category, {}).get(item_name, 0) + night_restocks.get(category, {}).get(item_name, 0)
    
    comparison_results = {
        'categories': {},
        'restocks': {
            'day': dict(day_restocks),
            'night': dict(night_restocks),
            'total': dict(total_restocks)
        },
        'specialItemsInfo': special_items_info or {},
        'summary': {
            'total_items_checked': 0,
            'items_with_discrepancy': 0,
            'items_matching': 0,
            'items_overstock': 0,
            'items_not_in_inventory': 0,
            'total_restocks': sum(sum(items.values()) for items in total_restocks.values())
        }
    }
    
    # Get all categories from expected consumption
    all_categories = set(expected_consumption.keys())
    
    print(f"\nCategories in expected consumption: {all_categories}")
    print(f"Categories in day initial inventory: {set(day_initial.keys())}")
    print(f"Categories in night final inventory: {set(night_final.keys())}")
    
    for category in all_categories:
        category_results = {
            'items': {}
        }
        
        expected_items = expected_consumption.get(category, {})
        print(f"\n--- Processing category: {category} ---")
        print(f"Expected items in this category: {list(expected_items.keys())}")
        print(f"Initial inventory items in this category: {list(day_initial.get(category, {}).keys())}")
        if night_final:
            print(f"Final inventory items in this category: {list(night_final.get(category, {}).keys())}")
        else:
            print(f"Final inventory items in this category: {list(day_final.get(category, {}).keys())}")
        
        for item_name, expected_qty in expected_items.items():
            comparison_results['summary']['total_items_checked'] += 1
            
            # Get initial and final quantities
            initial_qty = day_initial.get(category, {}).get(item_name, None)
            
            # Determine which final inventory to use
            # If night_final has data, use it (full day comparison or when night shift data is in night_final)
            # Otherwise use day_final (shift-specific comparison where final is in day_final param)
            if night_final and category in night_final and item_name in night_final.get(category, {}):
                final_qty = night_final.get(category, {}).get(item_name, None)
            else:
                final_qty = day_final.get(category, {}).get(item_name, None)
            
            # Get restock quantity for this item
            restock_qty = total_restocks.get(category, {}).get(item_name, 0)
            
            # Check if this item is part of a special item's composition
            special_item_usage = {}
            if special_items_info and 'breakdown' in special_items_info:
                for special_item, breakdown in special_items_info['breakdown'].items():
                    if item_name in breakdown:
                        special_item_usage[special_item] = breakdown[item_name]
            
            print(f"  Item: {item_name}")
            print(f"    Initial qty: {initial_qty}")
            print(f"    Restocks: {restock_qty}")
            print(f"    Final qty: {final_qty}")
            print(f"    Actual usage (from sales composition): {expected_qty}")
            if special_item_usage:
                print(f"    Special item usage: {special_item_usage}")
            print(f"    Expected usage (from inventory): ({initial_qty} + {restock_qty}) - {final_qty} = {initial_qty + restock_qty - final_qty if initial_qty is not None and final_qty is not None else 'N/A'}")
            
            # Calculate actual consumption (difference)
            if initial_qty is not None and final_qty is not None:
                # Expected Usage = (Day Initial + Restocks) - Night Final
                # This is what the inventory difference tells us was consumed
                expected_usage_from_inventory = initial_qty + restock_qty - final_qty
                
                # Actual Usage = based on product compositions and sales
                # This is what SHOULD have been consumed based on what was sold
                actual_usage_from_sales = expected_qty
                
                # Discrepancy = Actual (from sales) - Expected (from inventory)
                # Example: If inventory shows 24 consumed but only 10 sold = 10 - 24 = -14 (shortage)
                # Example: If inventory shows 10 consumed but 20 sold = 20 - 10 = +10 (overstock)
                discrepancy = actual_usage_from_sales - expected_usage_from_inventory
                
                # Format quantities based on category
                formatted_initial = format_quantity(initial_qty, category)
                formatted_final = format_quantity(final_qty, category)
                formatted_restock = format_quantity(restock_qty, category)
                formatted_expected_usage = format_quantity(expected_usage_from_inventory, category)
                formatted_actual_usage = format_quantity(actual_usage_from_sales, category)
                formatted_discrepancy = format_quantity(discrepancy, category)
                
                # Determine status based on discrepancy
                # Negative discrepancy = Less sold than inventory shows consumed = missing items/shortage
                # Positive discrepancy = More sold than inventory shows consumed = overstock/surplus
                if abs(discrepancy) < 0.01:
                    status = 'match'
                elif discrepancy < 0:
                    status = 'discrepancy'  # Negative discrepancy = shortage/missing items
                else:
                    status = 'overstock'  # Positive discrepancy = leftovers/overstock
                
                item_result = {
                    'productName': item_name,
                    'dayInitialQty': formatted_initial,
                    'nightFinalQty': formatted_final,
                    'restockQty': formatted_restock,
                    'actualConsumption': formatted_expected_usage,  # Expected from inventory
                    'expectedConsumption': formatted_actual_usage,  # Actual from sales compositions
                    'discrepancy': formatted_discrepancy,
                    'status': status,
                    'discrepancyPercentage': (abs(discrepancy) / actual_usage_from_sales * 100) if actual_usage_from_sales != 0 else 0
                }
                
                # Add special item breakdown if available
                if special_item_usage:
                    item_result['specialItemUsage'] = special_item_usage
                
                # Update summary counters based on status
                if status == 'match':
                    comparison_results['summary']['items_matching'] += 1
                elif status == 'overstock':
                    comparison_results['summary']['items_overstock'] += 1
                else:  # status == 'discrepancy'
                    comparison_results['summary']['items_with_discrepancy'] += 1
            else:
                # Item not found in inventory
                formatted_actual_usage = format_quantity(expected_qty, category)
                item_result = {
                    'productName': item_name,
                    'dayInitialQty': initial_qty,
                    'nightFinalQty': final_qty,
                    'restockQty': 0,
                    'actualConsumption': None,
                    'expectedConsumption': formatted_actual_usage,
                    'discrepancy': None,
                    'status': 'not_in_inventory',
                    'message': 'Item not found in inventory records'
                }
                
                # Add special item breakdown if available
                if special_item_usage:
                    item_result['specialItemUsage'] = special_item_usage
                
                comparison_results['summary']['items_not_in_inventory'] += 1
            
            category_results['items'][item_name] = item_result
        
        comparison_results['categories'][category] = category_results
    
    return comparison_results


def analyze_inventory_comparison(date: str, inventory_type: str = 'dining', shift: Optional[str] = None) -> Dict[str, Any]:
    """
    Main function to analyze inventory comparison for a specific date.
    
    Args:
        date: Date string in format YYYY-MM-DD
        inventory_type: 'dining' or 'kitchen'
        shift: Optional shift filter ('day' or 'night'). If None, compares full day (day initial to night final).
               If 'day', compares day initial to day final.
               If 'night', compares night initial to night final.
    
    Returns:
        Complete comparison analysis with results and summary
    """
    try:
        shift_msg = f" ({shift} shift)" if shift else " (full day)"
        print(f"\n=== Starting Inventory Comparison for {date}{shift_msg} ===\n")
        
        # Step 1: Get sales data
        print(f"Step 1: Fetching sales data for {shift or 'all'} shift(s)...")
        items_sold, detailed_sales = get_sales_for_date(date, shift)
        
        if not items_sold:
            return {
                'success': False,
                'message': f'No sales data found for {date}',
                'date': date,
                'inventoryType': inventory_type
            }
        
        # Step 2: Get product compositions
        print("\nStep 2: Fetching product compositions...")
        compositions = get_product_compositions()
        
        # Step 3: Calculate actual usage from compositions
        print("\nStep 3: Calculating actual usage (from sales & compositions)...")
        expected_consumption, special_items_info = calculate_expected_consumption(items_sold, compositions, detailed_sales)
        
        # Step 4: Get day shift initial inventory
        print("\nStep 4: Fetching day shift initial inventory...")
        day_initial_doc = get_inventory_for_shift(date, 'day', 'Initial', inventory_type)
        day_initial_quantities = get_inventory_quantities(day_initial_doc)
        
        # Step 5: Get day shift final inventory
        print("\nStep 5: Fetching day shift final inventory...")
        day_final_doc = get_inventory_for_shift(date, 'day', 'Final', inventory_type)
        day_final_quantities = get_inventory_quantities(day_final_doc)
        
        # Step 6: Get night shift initial inventory
        print("\nStep 6: Fetching night shift initial inventory...")
        night_initial_doc = get_inventory_for_shift(date, 'night', 'Initial', inventory_type)
        night_initial_quantities = get_inventory_quantities(night_initial_doc)
        
        # Step 7: Get night shift final inventory
        print("\nStep 7: Fetching night shift final inventory...")
        night_final_doc = get_inventory_for_shift(date, 'night', 'Final', inventory_type)
        night_final_quantities = get_inventory_quantities(night_final_doc)
        
        # Step 8: Match special items with inventory categories
        print("\nStep 8: Matching special items with inventory categories...")
        expected_consumption = match_special_items_to_inventory(expected_consumption, day_initial_quantities)
        
        # Step 9: Compare expected usage (from inventory) vs actual usage (from sales)
        print("\nStep 9: Comparing expected usage (inventory) vs actual usage (sales)...")
        
        # Determine which inventories to compare based on shift
        if shift == 'day':
            # For day shift, compare day initial to day final
            print("Using day shift comparison: day initial -> day final")
            comparison = compare_inventory_with_expected(
                day_initial_quantities,
                day_final_quantities,
                {},  # Empty dict for night initial to avoid double-counting restocks
                {},  # Empty dict for night final to avoid double-counting restocks
                expected_consumption,
                special_items_info
            )
        elif shift == 'night':
            # For night shift, compare night initial to night final
            print("Using night shift comparison: night initial -> night final")
            comparison = compare_inventory_with_expected(
                night_initial_quantities,  # Use night initial as "day initial"
                night_final_quantities,    # Use night final as "day final"
                {},  # Empty dict for night initial to avoid double-counting restocks
                {},  # Empty dict for night final to avoid double-counting restocks
                expected_consumption,
                special_items_info
            )
        else:
            # Full day comparison: day initial to night final
            print("Using full day comparison: day initial -> night final")
            comparison = compare_inventory_with_expected(
                day_initial_quantities,
                day_final_quantities,
                night_initial_quantities,
                night_final_quantities,
                expected_consumption,
                special_items_info
            )
        
        # Prepare final result
        result = {
            'success': True,
            'date': date,
            'inventoryType': inventory_type,
            'shift': shift,  # Include shift in the result
            'itemsSold': items_sold,
            'expectedConsumption': expected_consumption,
            'specialItemsInfo': special_items_info,
            'comparison': comparison,
            'summary': comparison['summary']
        }
        
        print(f"\n=== Inventory Comparison Complete ===")
        print(f"Total items checked: {comparison['summary']['total_items_checked']}")
        print(f"Items matching: {comparison['summary']['items_matching']}")
        print(f"Items with discrepancy: {comparison['summary']['items_with_discrepancy']}")
        print(f"Items not in inventory: {comparison['summary']['items_not_in_inventory']}")
        
        return result
    
    except Exception as e:
        print(f"Error in analyze_inventory_comparison: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'date': date,
            'inventoryType': inventory_type
        }


def get_date_range_comparison(start_date: str, end_date: str, inventory_type: str = 'dining') -> List[Dict[str, Any]]:
    """
    Analyze inventory comparison for a date range.
    
    Args:
        start_date: Start date string in format YYYY-MM-DD
        end_date: End date string in format YYYY-MM-DD
        inventory_type: 'dining' or 'kitchen'
    
    Returns:
        List of comparison results for each date
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        results = []
        current = start
        
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            result = analyze_inventory_comparison(date_str, inventory_type)
            results.append(result)
            current += timedelta(days=1)
        
        return results
    
    except Exception as e:
        print(f"Error in get_date_range_comparison: {str(e)}")
        return [{
            'success': False,
            'error': str(e)
        }]


if __name__ == '__main__':
    # Test the algorithm
    import sys
    
    if len(sys.argv) > 1:
        test_date = sys.argv[1]
    else:
        # Default to yesterday
        test_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"Testing inventory comparison for date: {test_date}")
    result = analyze_inventory_comparison(test_date, 'dining')
    
    # Print results in a readable format
    import json
    print("\n" + "="*80)
    print("RESULTS:")
    print("="*80)
    print(json.dumps(result, indent=2, default=str))
