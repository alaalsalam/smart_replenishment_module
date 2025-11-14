# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, today, date_diff
from datetime import datetime, timedelta
from smart_replenishment_module.utils.logger import log_error


@frappe.whitelist()
def calculate_consumption_metrics(item_code, warehouse, consumption_period_days=90):
	"""Calculate average daily consumption from stock ledger entries"""
	
	to_date = today()
	from_date = add_days(to_date, -consumption_period_days)
	
	# Only count outgoing transactions (sales, deliveries, stock issues)
	outgoing_voucher_types = [
		"Delivery Note",
		"Stock Entry"
		
	]
	
	# Query stock ledger for consumption (negative qty = outgoing)
	consumption_data = frappe.db.sql("""
		SELECT 
			SUM(ABS(actual_qty)) as total_consumption,
			COUNT(DISTINCT posting_date) as days_with_transactions
		FROM `tabStock Ledger Entry`
		WHERE 
			item_code = %(item_code)s
			AND warehouse = %(warehouse)s
			AND posting_date >= %(from_date)s
			AND posting_date <= %(to_date)s
			AND actual_qty < 0
			AND voucher_type IN %(voucher_types)s
			AND is_cancelled = 0
	""", {
		"item_code": item_code,
		"warehouse": warehouse,
		"from_date": from_date,
		"to_date": to_date,
		"voucher_types": outgoing_voucher_types
	}, as_dict=True)
	
	total_consumption = flt(consumption_data[0].get("total_consumption", 0)) if consumption_data else 0
	days_with_transactions = flt(consumption_data[0].get("days_with_transactions", 0)) if consumption_data else 0
	
	# Calculate average daily consumption based on configured method
	# Get the calculation method from settings
	settings = frappe.get_single("Replenishment Settings")
	calculation_method = settings.consumption_calculation_method or "Active Days Only"
	
	if calculation_method == "Active Days Only":
		# Use days with transactions (more accurate for sporadic sales)
		effective_days = days_with_transactions if days_with_transactions > 0 else consumption_period_days
	else:
		# Use full period (more conservative, accounts for idle days)
		effective_days = consumption_period_days
	
	if effective_days == 0 or total_consumption == 0:
		average_daily_consumption = 0
	else:
		average_daily_consumption = total_consumption / effective_days
	
	result = {
		"average_daily_consumption": flt(average_daily_consumption, 2),
		"total_consumption": flt(total_consumption, 2),
		"analysis_from_date": from_date,
		"analysis_to_date": to_date,
		"consumption_period_days": consumption_period_days,
		"days_with_transactions": int(days_with_transactions)
	}
	
	return result


@frappe.whitelist()
def update_reorder_points(item_code=None, warehouse=None):
	"""Update reorder points for all items based on consumption analysis"""
	
	settings = frappe.get_single("Replenishment Settings")
	# consumption_period_days: How many days to look back for consumption analysis (from global settings)
	consumption_period_days = settings.consumption_period_days
	# Default safety stock days (can be overridden per item)
	default_safety_stock_days = settings.enable_safety_stock_days if settings.enable_safety_stock_days else 0
	
	
	filters = {}
	if item_code:
		filters["parent"] = item_code
	if warehouse:
		filters["warehouse"] = warehouse
	
	reorder_records = frappe.get_all(
		"Item Reorder",
		filters=filters,
		fields=["name", "parent", "warehouse", "warehouse_reorder_level", "warehouse_reorder_qty"]
	)
	
	updated_count = 0
	skipped_count = 0
	errors = []
	
	for record in reorder_records:
		try:
			# Calculate consumption from stock ledger
			metrics = calculate_consumption_metrics(
				record.parent,
				record.warehouse,
				consumption_period_days
			)
			
			# Skip if no consumption data (new item or no sales)
			if metrics["average_daily_consumption"] == 0:
				skipped_count += 1
				continue
			
			reorder_doc = frappe.get_doc("Item Reorder", record.name)
			
			# Get lead time - prefer warehouse-specific, fallback to item-level
			lead_time_days = reorder_doc.supplier_lead_time_days
			if not lead_time_days:
				item = frappe.get_doc("Item", record.parent)
				lead_time_days = item.lead_time_days or 0
			
			# Get safety stock - prefer warehouse-specific, fallback to default
			safety_stock_days = reorder_doc.safety_stock_days
			if not safety_stock_days:
				safety_stock_days = default_safety_stock_days
			
			# Calculate reorder point: (Avg Daily Consumption × Lead Time) + (Avg Daily Consumption × Safety Stock)
			avg_daily_consumption = metrics["average_daily_consumption"]
			reorder_point = avg_daily_consumption * (lead_time_days + safety_stock_days)
			
			minimum_stock_level = flt(reorder_point, 2)
			
			# Calculate max stock level
			reorder_qty = reorder_doc.warehouse_reorder_qty
			if not reorder_qty or reorder_qty <= 0:
				# Default: enough for 30 days if reorder qty not set
				reorder_qty = avg_daily_consumption * 30
			
			maximum_stock_level = flt(reorder_point + reorder_qty, 2)
			
			# Update all calculated fields
			reorder_doc.warehouse_reorder_level = minimum_stock_level
			reorder_doc.minimum_stock_level = minimum_stock_level
			reorder_doc.maximum_stock_level = maximum_stock_level
			reorder_doc.average_daily_consumption = avg_daily_consumption
			reorder_doc.last_calculation_date = today()
			
			reorder_doc.save(ignore_permissions=True)
			frappe.db.commit()
			
			updated_count += 1
			
		except Exception as e:
			error_msg = f"Error updating reorder point for {record.parent} in {record.warehouse}: {str(e)}"
			error_info = {
				"item": record.parent,
				"warehouse": record.warehouse,
				"error": str(e)
			}
			errors.append(error_info)
			
			# Log to Frappe Error Log for visibility in UI
			frappe.log_error(
				message=f"{error_msg}\n\nTraceback:\n{frappe.get_traceback()}",
				title=f"❌ Reorder Point Calculation Failed: {record.parent}"
			)
			
			# Also log to our custom activity log
			log_error(
				title=f"Error updating reorder point for {record.parent} - {record.warehouse}",
				message=str(e),
				item_code=record.parent,
				warehouse=record.warehouse,
				traceback=frappe.get_traceback()
			)
	
	result = {
		"updated_count": updated_count,
		"skipped_count": skipped_count,
		"errors": errors,
		"total_processed": len(reorder_records)
	}
	
	return result

