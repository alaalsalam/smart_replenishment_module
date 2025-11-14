# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT


import frappe
from frappe import _
from smart_replenishment_module.utils.logger import log_info, log_error
from frappe.utils import flt


def get_item_last_purchase_rate(item_code, fallback_to_standard_rate=True, warehouse=None):
	"""
		Get last purchase rate from Purchase Order Item history (not Item master).
		Uses ERPNext's get_last_purchase_details which queries Purchase Order/Receipt/Invoice items.

		Fallback order (if no purchase history):
		1. Last purchase rate from PO history
		2. Valuation rate from Item
		3. Standard rate from Item
		4. Return 0

		Args:
			item_code: Item code to get rate for
			fallback_to_standard_rate: If True, fallback to Item valuation_rate/standard_rate if no purchase history
			warehouse: Optional warehouse to get bin valuation rate from

		Returns:
			Last purchase rate, valuation rate, or standard_rate as fallback
	"""
	try:
		from erpnext.stock.doctype.item.item import get_last_purchase_details

		# Try 1: Get last purchase details from Purchase Order/Receipt/Invoice Item history
		last_purchase_details = get_last_purchase_details(item_code)

		if last_purchase_details and last_purchase_details.get("rate"):
			return frappe.utils.flt(last_purchase_details["rate"])

		# Fallback to valuation rate or standard rate if configured
		if fallback_to_standard_rate:
			item = frappe.get_cached_doc("Item", item_code)

			# Try 2: Valuation rate (most accurate for costing)
			if item.valuation_rate and item.valuation_rate > 0:
				return frappe.utils.flt(item.valuation_rate)

			# Try 3: Get valuation rate from Bin if warehouse provided
			if warehouse:
				try:
					bin = frappe.get_cached_doc("Bin", {
						"item_code": item_code,
						"warehouse": warehouse
					})
					if bin and bin.valuation_rate and bin.valuation_rate > 0:
						return frappe.utils.flt(bin.valuation_rate)
				except Exception:
					pass

			# Try 4: Standard rate from Item
			if item.standard_rate and item.standard_rate > 0:
				return frappe.utils.flt(item.standard_rate)

		return 0
	except Exception:
		# If anything fails, fallback to valuation/standard rate
		if fallback_to_standard_rate:
			try:
				item = frappe.get_cached_doc("Item", item_code)
				# Try valuation rate first, then standard rate
				return frappe.utils.flt(item.valuation_rate or item.standard_rate or 0)
			except Exception:
				pass
		return 0


def on_update(doc, method=None):
	"""Triggered when Item is updated - checks if reorder settings changed and recalculates"""

	# Only proceed if reorder_levels table was modified
	if not doc.has_value_changed("reorder_levels"):
		return

	old_doc = doc.get_doc_before_save()
	if not old_doc:
		# New document - no need to recalculate
		return

	recalculate_items = []

	# Compare each row to detect changes
	for new_row in doc.reorder_levels:
		# Find corresponding old row
		old_row = None
		for orow in old_doc.reorder_levels:
			if orow.name == new_row.name:
				old_row = orow
				break

		# New row added - recalculate
		if not old_row:
			recalculate_items.append({
				"item_code": doc.name,
				"warehouse": new_row.warehouse,
				"reason": "new_row"
			})
			continue

		# Lead time changed - affects reorder point calculation
		if old_row.supplier_lead_time_days != new_row.supplier_lead_time_days:
			recalculate_items.append({
				"item_code": doc.name,
				"warehouse": new_row.warehouse,
				"reason": "lead_time_changed",
				"old_value": old_row.supplier_lead_time_days,
				"new_value": new_row.supplier_lead_time_days
			})
			continue

		# Safety stock changed - affects reorder point calculation
		if old_row.safety_stock_days != new_row.safety_stock_days:
			recalculate_items.append({
				"item_code": doc.name,
				"warehouse": new_row.warehouse,
				"reason": "safety_stock_changed",
				"old_value": old_row.safety_stock_days,
				"new_value": new_row.safety_stock_days
			})
			continue

	# Queue recalculation in background to avoid blocking save
	if recalculate_items:
		frappe.enqueue(
			"smart_replenishment_module.doc_events.item.recalculate_reorder_points",
			items=recalculate_items,
			queue="short",
			now=False  # Run in background
		)

		if len(recalculate_items) == 1:
			frappe.msgprint(
				_("Reorder point will be recalculated for {0} in {1} due to {2} change").format(
					recalculate_items[0]["item_code"],
					recalculate_items[0]["warehouse"],
					"lead time" if "lead_time" in recalculate_items[0]["reason"] else "safety stock"
				),
				indicator="blue",
				alert=True
			)
		else:
			frappe.msgprint(
				_("Reorder points will be recalculated for {0} item(s)").format(len(recalculate_items)),
				indicator="blue",
				alert=True
			)


def recalculate_reorder_points(items):
	"""Recalculate reorder points for items - called from background job"""

	from smart_replenishment_module.api.stock_analyzer import update_reorder_points

	for item_info in items:
		try:
			# Recalculate for this specific item-warehouse combination
			result = update_reorder_points(
				item_code=item_info["item_code"],
				warehouse=item_info["warehouse"]
			)

			# Log for tracking
			log_info(
				title="Recalculated reorder point",
				message=f"Recalculated reorder point for {item_info['item_code']} in {item_info['warehouse']}: {result.get('updated_count', 0)} updated",
				item_code=item_info['item_code'],
				warehouse=item_info['warehouse']
			)

			# Check if existing recommendations need updating after recalculation
			_check_and_regenerate_recommendations(
				item_info["item_code"],
				item_info["warehouse"]
			)

		except Exception as e:
			log_error(
				title=f"Error recalculating reorder point for {item_info['item_code']}",
				message=frappe.get_traceback(),
				item_code=item_info.get('item_code'),
				warehouse=item_info.get('warehouse')
			)


def _check_and_regenerate_recommendations(item_code, warehouse):
	from erpnext.stock.utils import get_stock_balance

	item_reorder = frappe.db.get_value(
		"Item Reorder",
		{
			"parent": item_code,
			"warehouse": warehouse
		},
		["warehouse_reorder_level", "minimum_stock_level", "maximum_stock_level"],
		as_dict=True
	)

	if not item_reorder or not item_reorder.warehouse_reorder_level:
		return

	current_stock = get_stock_balance(item_code, warehouse) or 0

	existing_recommendations = frappe.get_all(
		"Replenishment Recommendation",
		filters={
			"item_code": item_code,
			"warehouse": warehouse,
			"status": "Pending"
		},
		fields=["name", "status", "current_stock_qty", "reorder_point"]
	)

	for rec in existing_recommendations:
		# Double-check status before updating (should only be Pending due to filter, but extra safety)
		if rec.status != "Pending":
			continue

		# Update recommendation with new reorder point
		rec_doc = frappe.get_doc("Replenishment Recommendation", rec.name)

		# Verify status is still Pending before updating
		if rec_doc.status != "Pending":
			log_info(
				title="Skipped recommendation update",
				message=f"Skipped updating recommendation {rec.name} - status is {rec_doc.status}, only Pending recommendations can be updated",
				reference_doctype="Replenishment Recommendation",
				reference_name=rec.name,
				item_code=item_code,
				warehouse=warehouse
			)
			continue

		# Update fields
		rec_doc.reorder_point = item_reorder.warehouse_reorder_level
		rec_doc.minimum_stock_level = item_reorder.minimum_stock_level
		rec_doc.maximum_stock_level = item_reorder.maximum_stock_level
		rec_doc.current_stock_qty = current_stock

		# Recalculate recommended quantity if needed
		if current_stock < item_reorder.warehouse_reorder_level:
			# Still below reorder point - update recommendation
			# Get Item Reorder document for warehouse_reorder_qty
			item_reorder_doc = frappe.get_doc(
				"Item Reorder",
				{
					"parent": item_code,
					"warehouse": warehouse
				}
			)

			# Get maximum stock level (use updated value from item_reorder)
			maximum_stock_level = flt(item_reorder.maximum_stock_level, 2)

			# If maximum_stock_level is not set, calculate it: reorder_point + reorder_qty
			if not maximum_stock_level or maximum_stock_level <= 0:
				reorder_qty = item_reorder_doc.warehouse_reorder_qty
				if not reorder_qty or reorder_qty <= 0:
					# Default: enough for 30 days if reorder qty not set
					avg_daily_consumption = rec_doc.average_daily_consumption or 0
					reorder_qty = avg_daily_consumption * 30
				maximum_stock_level = flt(item_reorder.warehouse_reorder_level + reorder_qty, 2)
				# Update the recommendation's maximum_stock_level if we calculated it
				rec_doc.maximum_stock_level = maximum_stock_level

			# Calculate recommended quantity (same logic as recommendation_generator)
			avg_daily_consumption = rec_doc.average_daily_consumption or 0

			# First, calculate the quantity needed to reach maximum_stock_level from current stock
			qty_to_reach_max = maximum_stock_level - current_stock

			# Base recommended quantity: use warehouse_reorder_qty if set, otherwise calculate based on consumption
			if item_reorder_doc.warehouse_reorder_qty and item_reorder_doc.warehouse_reorder_qty > 0:
				base_recommended_qty = item_reorder_doc.warehouse_reorder_qty
			else:
				# Calculate: enough to cover lead time + safety stock
				lead_time = item_reorder_doc.supplier_lead_time_days or 0
				safety_days = item_reorder_doc.safety_stock_days or 0
				base_recommended_qty = avg_daily_consumption * (lead_time + safety_days)

			# Recommended quantity should be the maximum of:
			# 1. Base recommended quantity (warehouse_reorder_qty or calculated)
			# 2. Quantity needed to reach maximum_stock_level
			recommended_qty = max(base_recommended_qty, qty_to_reach_max)

			# Check minimum order quantity
			item = frappe.get_doc("Item", item_code)
			if item.min_order_qty and item.min_order_qty > recommended_qty:
				recommended_qty = item.min_order_qty

			rec_doc.recommended_order_qty = recommended_qty

			# Recalculate estimated cost
			# Get last purchase rate from Purchase Order Item history, not Item master
			rate = get_item_last_purchase_rate(item_code, fallback_to_standard_rate=True, warehouse=warehouse)
			# Always calculate estimated_cost (will be 0 if rate is 0, which is fine)
			rec_doc.estimated_cost = flt(recommended_qty * rate, 2) if rate else 0

			# Update lead time and safety stock days
			rec_doc.lead_time_days = item_reorder_doc.supplier_lead_time_days or 0
			rec_doc.safety_stock_days = item_reorder_doc.safety_stock_days or 0

		# Save changes
		rec_doc.save(ignore_permissions=True)
		frappe.db.commit()

		log_info(
			title="Updated recommendation",
			message=f"Updated recommendation {rec.name} after reorder point recalculation",
			reference_doctype="Replenishment Recommendation",
			reference_name=rec.name,
			item_code=item_code,
			warehouse=warehouse
		)
