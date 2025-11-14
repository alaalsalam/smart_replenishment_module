# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

import frappe
from frappe import _
from frappe.utils import flt, today, getdate
from erpnext.stock.utils import get_stock_balance
from smart_replenishment_module.api.stock_analyzer import calculate_consumption_metrics, update_reorder_points
from smart_replenishment_module.utils.logger import log_error
from smart_replenishment_module.doc_events.item import get_item_last_purchase_rate


@frappe.whitelist()
def generate_recommendations(warehouse=None, item_group=None):
	"""Generate recommendations for items below reorder point - scans all items and creates recommendations"""

	settings = frappe.get_single("Replenishment Settings")
	consumption_period_days = settings.consumption_period_days
	default_safety_stock_days = settings.enable_safety_stock_days if settings.enable_safety_stock_days else 0

	# Build SQL query to get all Item Reorder records with item details
	reorder_query = """
		SELECT
			ir.name,
			ir.parent as item_code,
			ir.warehouse,
			ir.warehouse_reorder_level,
			ir.warehouse_reorder_qty,
			ir.minimum_stock_level,
			ir.maximum_stock_level,
			ir.safety_stock_days,
			ir.supplier_lead_time_days,
			ir.preferred_supplier,
			ir.average_daily_consumption,
			i.item_name,
			i.item_group,
			i.lead_time_days as item_lead_time_days
			-- Note: last_purchase_rate removed - get it from Purchase Order Item history using get_item_last_purchase_rate()
		FROM `tabItem Reorder` ir
		INNER JOIN `tabItem` i ON ir.parent = i.name
		WHERE i.is_stock_item = 1
		AND i.disabled = 0
	"""

	if warehouse:
		reorder_query += " AND ir.warehouse = %(warehouse)s"

	if item_group:
		reorder_query += " AND i.item_group = %(item_group)s"

	reorder_records = frappe.db.sql(reorder_query, {
		"warehouse": warehouse,
		"item_group": item_group
	}, as_dict=True)

	created_count = 0
	skipped_count = 0
	errors = []

	for record in reorder_records:
		try:
			# Get current stock
			current_stock = get_stock_balance(
				record.item_code,
				record.warehouse,
				with_valuation_rate=False
			) or 0

			# Get reorder level
			reorder_level = flt(record.warehouse_reorder_level, 2)

			# Skip if reorder level not set
			if reorder_level <= 0:
				skipped_count += 1
				continue

			# Check if stock is below reorder point
			if current_stock > reorder_level:
				skipped_count += 1
				continue

			# Check for existing pending/approved recommendation
			existing = frappe.db.exists(
				"Replenishment Recommendation",
				{
					"item_code": record.item_code,
					"warehouse": record.warehouse,
					"status": ["in", ["Pending", "Approved"]]
				}
			)

			if existing:
				skipped_count += 1
				continue

			# Calculate consumption metrics if not available
			if not record.average_daily_consumption:
				metrics = calculate_consumption_metrics(
					record.item_code,
					record.warehouse,
					consumption_period_days
				)
				avg_daily_consumption = metrics["average_daily_consumption"]
				analysis_from_date = metrics["analysis_from_date"]
				analysis_to_date = metrics["analysis_to_date"]
			else:
				avg_daily_consumption = record.average_daily_consumption
				analysis_from_date = None
				analysis_to_date = None

			# Skip if no consumption data
			if avg_daily_consumption == 0:
				skipped_count += 1
				continue

			# Get lead time
			lead_time_days = record.supplier_lead_time_days
			if not lead_time_days:
				lead_time_days = record.item_lead_time_days or 0

			# Get safety stock days
			safety_stock_days = record.safety_stock_days
			if not safety_stock_days:
				safety_stock_days = default_safety_stock_days

			# Get minimum and maximum stock levels from Item Reorder
			minimum_stock_level = flt(record.minimum_stock_level or reorder_level, 2)
			maximum_stock_level = flt(record.maximum_stock_level, 2)

			# If maximum_stock_level is not set, calculate it: reorder_point + reorder_qty
			if not maximum_stock_level or maximum_stock_level <= 0:
				reorder_qty = record.warehouse_reorder_qty
				if not reorder_qty or reorder_qty <= 0:
					# Default: enough for 30 days if reorder qty not set
					reorder_qty = avg_daily_consumption * 30
				maximum_stock_level = flt(reorder_level + reorder_qty, 2)

			# Calculate recommended order quantity
			# First, calculate the quantity needed to reach maximum_stock_level from current stock
			qty_to_reach_max = maximum_stock_level - current_stock

			# Base recommended quantity: use warehouse_reorder_qty if set, otherwise calculate based on consumption
			if record.warehouse_reorder_qty and record.warehouse_reorder_qty > 0:
				base_recommended_qty = record.warehouse_reorder_qty
			else:
				# Calculate: enough to cover lead time + safety stock
				base_recommended_qty = avg_daily_consumption * (lead_time_days + safety_stock_days)

			# Recommended quantity should be the maximum of:
			# 1. Base recommended quantity (warehouse_reorder_qty or calculated)
			# 2. Quantity needed to reach maximum_stock_level
			recommended_qty = max(base_recommended_qty, qty_to_reach_max)

			# Ensure minimum order quantity
			item = frappe.get_doc("Item", record.item_code)
			if item.min_order_qty and item.min_order_qty > recommended_qty:
				recommended_qty = item.min_order_qty

			# Determine priority
			priority = determine_priority(current_stock, reorder_level)

			# Calculate estimated cost
			# Get last purchase rate from Purchase Order Item history, not Item master
			last_purchase_rate = get_item_last_purchase_rate(record.item_code, fallback_to_standard_rate=True, warehouse=record.warehouse)

			# Always calculate estimated_cost (will be 0 if rate is 0, which is fine)
			estimated_cost = flt(last_purchase_rate * recommended_qty, 2) if last_purchase_rate else 0

			# Create recommendation
			# Don't set status manually - let workflow set it automatically to initial state
			recommendation = frappe.get_doc({
				"doctype": "Replenishment Recommendation",
				"item_code": record.item_code,
				"item_name": record.item_name,
				"warehouse": record.warehouse,
				# Status will be set by workflow to initial state ("Pending")
				"priority": priority,
				"current_stock_qty": flt(current_stock, 2),
				"minimum_stock_level": minimum_stock_level,
				"reorder_point": reorder_level,
				"maximum_stock_level": maximum_stock_level,
				"recommended_order_qty": flt(recommended_qty, 2),
				"average_daily_consumption": flt(avg_daily_consumption, 2),
				"lead_time_days": lead_time_days,
				"safety_stock_days": safety_stock_days,
				"preferred_supplier": record.preferred_supplier,
				"estimated_cost": estimated_cost,
				"stock_ledger_analysis_from_date": analysis_from_date,
				"stock_ledger_analysis_to_date": analysis_to_date,
				"consumption_period_days": consumption_period_days
			})

			recommendation.insert(ignore_permissions=True)
			frappe.db.commit()

			created_count += 1

			# Send notification to configured users/roles
			send_notification(recommendation.name, priority)

		except Exception as e:
			error_info = {
				"item": record.item_code,
				"warehouse": record.warehouse,
				"error": str(e)
			}
			errors.append(error_info)

			log_error(
				title=f"Error generating recommendation for {record.item_code} - {record.warehouse}",
				message=str(e),
				item_code=record.item_code,
				warehouse=record.warehouse,
				traceback=frappe.get_traceback()
			)

	result = {
		"created_count": created_count,
		"skipped_count": skipped_count,
		"errors": errors,
		"total_processed": len(reorder_records)
	}

	return result


def determine_priority(current_stock, reorder_point):
	"""Determine priority based on stock level - High if <50% of reorder point, Medium if <80%"""
	if reorder_point == 0:
		return "Low"

	stock_ratio = current_stock / reorder_point

	# Critical: less than 50% of reorder point
	if stock_ratio < 0.5:
		return "High"
	# Low: less than 80% of reorder point
	elif stock_ratio < 0.8:
		return "Medium"
	# Below reorder point but not critical
	else:
		return "Low"


def send_notification(recommendation_name, priority):
	"""Send notification to configured users/roles when recommendation is created"""
	try:
		settings = frappe.get_single("Replenishment Settings")

		# Check if notification should be sent based on priority filter
		notify_on_priority = settings.notification_on_priority or "All"
		if notify_on_priority == "High Only" and priority != "High":
			return
		if notify_on_priority == "High & Medium" and priority == "Low":
			return

		users_to_notify = []

		# Add users from notification_users table
		if settings.notification_users:
			for user_row in settings.notification_users:
				if user_row.user:
					users_to_notify.append(user_row.user)

		# Add users from notification_roles table (get all users with that role)
		if settings.notification_roles:
			for role_row in settings.notification_roles:
				if role_row.role:
					role_users = frappe.get_all(
						"Has Role",
						filters={"role": role_row.role, "parenttype": "User"},
						fields=["parent as user"]
					)
					for user in role_users:
						if user.user not in users_to_notify:
							users_to_notify.append(user.user)

		# Send notification to each user
		for user in users_to_notify:
			notification_doc = frappe.get_doc({
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": "Replenishment Recommendation",
				"document_name": recommendation_name,
				"subject": _("New Replenishment Recommendation: {0}").format(recommendation_name),
				"email_content": _("A new {0} priority replenishment recommendation has been created.").format(priority)
			})
			notification_doc.insert(ignore_permissions=True)

		frappe.db.commit()

	except Exception as e:
		log_error(
			title="Error sending replenishment notification",
			message=str(e),
			reference_doctype="Replenishment Recommendation",
			reference_name=recommendation_name,
			traceback=frappe.get_traceback()
		)


@frappe.whitelist()
def regenerate_recommendations_for_item(item_code, warehouse):
	"""
	Regenerate recommendations when warehouse_reorder_level changes
	Called when reorder point is updated (by system auto-calculation or manually)

	Args:
		item_code: Item code to regenerate recommendations for
		warehouse: Warehouse to regenerate recommendations for

	Returns:
		Dictionary with counts of created/skipped recommendations
	"""
	try:
		# Get current stock
		current_stock = get_stock_balance(item_code, warehouse) or 0

		# Get Item Reorder details
		item_reorder = frappe.db.get_value(
			"Item Reorder",
			{"parent": item_code, "warehouse": warehouse},
			["warehouse_reorder_level", "warehouse_reorder_qty"],
			as_dict=True
		)

		if not item_reorder:
			return {"created_count": 0, "skipped_count": 0}

		# Check if stock is below reorder point
		if current_stock >= item_reorder.warehouse_reorder_level:
			# Cancel any existing pending recommendations (stock recovered)
			existing_recs = frappe.get_all(
				"Replenishment Recommendation",
				filters={
					"item_code": item_code,
					"warehouse": warehouse,
					"status": "Pending",
					"docstatus": 0
				},
				fields=["name"]
			)

			for rec in existing_recs:
				frappe.delete_doc("Replenishment Recommendation", rec.name, force=1)

			frappe.db.commit()
			return {"created_count": 0, "skipped_count": 1, "message": "Stock above reorder level"}

		# Check if recommendation already exists
		existing_rec = frappe.db.get_value(
			"Replenishment Recommendation",
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"status": ["in", ["Pending", "Approved"]],
				"docstatus": ["<", 2]
			},
			"name"
		)

		if existing_rec:
			return {"created_count": 0, "skipped_count": 0, "message": "Recommendation already exists"}

		# Create new recommendation
		result = generate_recommendations(warehouse=warehouse)

		return result

	except Exception as e:
		log_error(
			title="Error regenerating recommendations",
			message=str(e),
			reference_doctype="Item",
			reference_name=item_code,
			traceback=frappe.get_traceback()
		)
		return {"created_count": 0, "skipped_count": 0, "error": str(e)}


@frappe.whitelist()
def get_item_last_purchase_rate_api(item_code):
	"""
	Whitelisted API endpoint to get last purchase rate for client-side calls
	Used by replenishment_recommendation.js to calculate estimated costs

	Args:
		item_code: Item code to get rate for

	Returns:
		Last purchase rate from Purchase Order Item history, or standard_rate as fallback
	"""
	try:
		rate = get_item_last_purchase_rate(item_code, fallback_to_standard_rate=True)
		return {"rate": rate}
	except Exception as e:
		frappe.log_error(
			message=f"Error getting last purchase rate for {item_code}: {str(e)}\n\nTraceback:\n{frappe.get_traceback()}",
			title=f"❌ Get Last Purchase Rate Failed: {item_code}"
		)
		return {"rate": 0, "error": str(e)}


@frappe.whitelist()
def recalculate_recommendation(recommendation_name):
	"""
	Recalculate all fields in a replenishment recommendation using updated logic
	- Gets latest Item Reorder data
	- Calculates maximum_stock_level correctly from Item Reorder table
	- Calculates recommended_order_qty to bring stock to maximum_stock_level
	- Always calculates estimated_cost (even if rate is 0)

	Args:
		recommendation_name: Name of the Replenishment Recommendation to recalculate

	Returns:
		Dictionary with updated field values
	"""
	try:
		from erpnext.stock.utils import get_stock_balance
		from smart_replenishment_module.api.stock_analyzer import calculate_consumption_metrics

		# Get the recommendation document
		rec_doc = frappe.get_doc("Replenishment Recommendation", recommendation_name)

		# Only allow recalculation for Pending recommendations
		if rec_doc.status != "Pending":
			frappe.throw(_("Only Pending recommendations can be recalculated. Current status: {0}").format(rec_doc.status))

		# Get current stock
		current_stock = get_stock_balance(rec_doc.item_code, rec_doc.warehouse) or 0

		# Get Item Reorder data
		item_reorder = frappe.db.get_value(
			"Item Reorder",
			{"parent": rec_doc.item_code, "warehouse": rec_doc.warehouse},
			[
				"warehouse_reorder_level",
				"warehouse_reorder_qty",
				"minimum_stock_level",
				"maximum_stock_level",
				"safety_stock_days",
				"supplier_lead_time_days",
				"preferred_supplier",
				"average_daily_consumption"
			],
			as_dict=True
		)

		if not item_reorder:
			frappe.throw(_("Item Reorder not found for {0} in {1}").format(rec_doc.item_code, rec_doc.warehouse))

		# Get settings
		settings = frappe.get_single("Replenishment Settings")
		consumption_period_days = settings.consumption_period_days
		default_safety_stock_days = settings.enable_safety_stock_days if settings.enable_safety_stock_days else 0

		# Calculate consumption metrics if not available
		if not item_reorder.average_daily_consumption:
			metrics = calculate_consumption_metrics(
				rec_doc.item_code,
				rec_doc.warehouse,
				consumption_period_days
			)
			avg_daily_consumption = metrics["average_daily_consumption"]
			analysis_from_date = metrics["analysis_from_date"]
			analysis_to_date = metrics["analysis_to_date"]
		else:
			avg_daily_consumption = item_reorder.average_daily_consumption
			analysis_from_date = rec_doc.stock_ledger_analysis_from_date
			analysis_to_date = rec_doc.stock_ledger_analysis_to_date

		# Get lead time
		lead_time_days = item_reorder.supplier_lead_time_days
		if not lead_time_days:
			item = frappe.get_doc("Item", rec_doc.item_code)
			lead_time_days = item.lead_time_days or 0

		# Get safety stock days
		safety_stock_days = item_reorder.safety_stock_days
		if not safety_stock_days:
			safety_stock_days = default_safety_stock_days

		# Get reorder level
		reorder_level = flt(item_reorder.warehouse_reorder_level, 2)

		# Get minimum and maximum stock levels from Item Reorder (use actual values from table)
		minimum_stock_level = flt(item_reorder.minimum_stock_level or reorder_level, 2)

		# Use maximum_stock_level from Item Reorder if available, otherwise calculate
		if item_reorder.maximum_stock_level and item_reorder.maximum_stock_level > 0:
			maximum_stock_level = flt(item_reorder.maximum_stock_level, 2)
		else:
			# Fallback: reorder_level + warehouse_reorder_qty (if set) or calculated qty
			if item_reorder.warehouse_reorder_qty and item_reorder.warehouse_reorder_qty > 0:
				maximum_stock_level = flt(reorder_level + item_reorder.warehouse_reorder_qty, 2)
			else:
				# Calculate based on consumption
				calculated_qty = avg_daily_consumption * (lead_time_days + safety_stock_days)
				maximum_stock_level = flt(reorder_level + calculated_qty, 2)

		# Calculate recommended order quantity
		# Priority: Bring stock to maximum_stock_level if possible, otherwise use warehouse_reorder_qty or calculate
		if maximum_stock_level > current_stock:
			# Calculate qty needed to bring stock to maximum_stock_level
			qty_to_max = maximum_stock_level - current_stock

			# Use warehouse_reorder_qty if set, otherwise use calculated qty to reach max
			if item_reorder.warehouse_reorder_qty and item_reorder.warehouse_reorder_qty > 0:
				# Use warehouse_reorder_qty, but ensure it doesn't exceed what's needed to reach max
				recommended_qty = min(item_reorder.warehouse_reorder_qty, qty_to_max)
			else:
				# Calculate: enough to cover lead time + safety stock, but cap at max needed
				calculated_qty = avg_daily_consumption * (lead_time_days + safety_stock_days)
				recommended_qty = min(calculated_qty, qty_to_max)
		else:
			# Stock is already at or above maximum - use warehouse_reorder_qty or calculate
			if item_reorder.warehouse_reorder_qty and item_reorder.warehouse_reorder_qty > 0:
				recommended_qty = item_reorder.warehouse_reorder_qty
			else:
				# Calculate: enough to cover lead time + safety stock
				recommended_qty = avg_daily_consumption * (lead_time_days + safety_stock_days)

		# Ensure minimum order quantity
		item = frappe.get_doc("Item", rec_doc.item_code)
		if item.min_order_qty and item.min_order_qty > recommended_qty:
			recommended_qty = item.min_order_qty

		# Calculate estimated cost - always calculate, even if rate is 0
		last_purchase_rate = get_item_last_purchase_rate(rec_doc.item_code, fallback_to_standard_rate=True, warehouse=rec_doc.warehouse)
		estimated_cost = flt(last_purchase_rate * recommended_qty, 2) if last_purchase_rate else 0

		# Determine priority
		priority = determine_priority(current_stock, reorder_level)

		# Update the recommendation document
		rec_doc.current_stock_qty = flt(current_stock, 2)
		rec_doc.reorder_point = reorder_level
		rec_doc.minimum_stock_level = minimum_stock_level
		rec_doc.maximum_stock_level = maximum_stock_level
		rec_doc.recommended_order_qty = flt(recommended_qty, 2)
		rec_doc.average_daily_consumption = flt(avg_daily_consumption, 2)
		rec_doc.lead_time_days = lead_time_days
		rec_doc.safety_stock_days = safety_stock_days
		rec_doc.preferred_supplier = item_reorder.preferred_supplier
		rec_doc.estimated_cost = estimated_cost
		rec_doc.priority = priority
		if analysis_from_date:
			rec_doc.stock_ledger_analysis_from_date = analysis_from_date
		if analysis_to_date:
			rec_doc.stock_ledger_analysis_to_date = analysis_to_date
		rec_doc.consumption_period_days = consumption_period_days

		rec_doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {
			"success": True,
			"message": _("Recommendation recalculated successfully"),
			"current_stock_qty": rec_doc.current_stock_qty,
			"reorder_point": rec_doc.reorder_point,
			"minimum_stock_level": rec_doc.minimum_stock_level,
			"maximum_stock_level": rec_doc.maximum_stock_level,
			"recommended_order_qty": rec_doc.recommended_order_qty,
			"estimated_cost": rec_doc.estimated_cost,
			"average_daily_consumption": rec_doc.average_daily_consumption,
			"lead_time_days": rec_doc.lead_time_days,
			"safety_stock_days": rec_doc.safety_stock_days
		}

	except Exception as e:
		log_error(
			title=f"Error recalculating recommendation {recommendation_name}",
			message=str(e),
			reference_doctype="Replenishment Recommendation",
			reference_name=recommendation_name,
			traceback=frappe.get_traceback()
		)
		frappe.throw(_("Error recalculating recommendation: {0}").format(str(e)))
