# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

import frappe
from frappe import _
from frappe.utils import flt, today, add_days, getdate, cint
from frappe.model.workflow import get_workflow
from smart_replenishment_module.utils.logger import log_error
from smart_replenishment_module.doc_events.item import get_item_last_purchase_rate


@frappe.whitelist()
def create_purchase_order_from_recommendation(recommendation_name):
	"""Create PO from approved recommendation - called from on_submit hook"""
	recommendation = frappe.get_doc("Replenishment Recommendation", recommendation_name)

	# Only create PO for approved recommendations
	if recommendation.status != "Approved":
		frappe.throw(
			_("Only approved recommendations can be converted to Purchase Orders. Current status: {0}").format(
				recommendation.status
			)
		)

	# Prevent duplicate PO creation
	if recommendation.purchase_order:
		frappe.throw(
			_("Purchase Order {0} already exists for this recommendation").format(
				recommendation.purchase_order
			)
		)

	# Get supplier based on selection strategy (Preferred, Shortest Lead Time, etc.)
	supplier_result = get_supplier_with_lead_time(recommendation)

	if not supplier_result or not supplier_result.get("supplier"):
		frappe.throw(
			_("No supplier found for Item {0}. Please set a preferred supplier or default supplier.").format(
				recommendation.item_code
			)
		)

	supplier = supplier_result["supplier"]
	# Use supplier-specific lead time if available, fallback to recommendation's lead time
	supplier_lead_time = supplier_result.get("lead_time_days") or recommendation.lead_time_days or 0

	warehouse_doc = frappe.get_doc("Warehouse", recommendation.warehouse)
	company = warehouse_doc.company

	if not company:
		frappe.throw(
			_("Company not found for Warehouse {0}").format(recommendation.warehouse)
		)

	# Get company and supplier currencies
	company_doc = frappe.get_doc("Company", company)
	company_currency = company_doc.default_currency

	# Get supplier currency (if not set, use company currency)
	supplier_doc = frappe.get_doc("Supplier", supplier)
	supplier_currency = supplier_doc.default_currency if supplier_doc.default_currency else company_currency

	# Calculate schedule date based on supplier lead time
	schedule_date = add_days(today(), supplier_lead_time)

	po = frappe.new_doc("Purchase Order")
	po.supplier = supplier
	po.company = company
	po.currency = supplier_currency
	po.transaction_date = today()
	po.schedule_date = schedule_date

	# Use Frappe's standard get_item_details to get proper rate and item details
	# This handles last_purchase_rate from Purchase Order Item history, not Item master
	from erpnext.stock.get_item_details import get_item_details

	item_details = get_item_details({
		"item_code": recommendation.item_code,
		"warehouse": recommendation.warehouse,
		"supplier": supplier,
		"company": company,
		"currency": supplier_currency,
		"transaction_date": today(),
		"qty": recommendation.recommended_order_qty,
		"doctype": "Purchase Order",
		"conversion_rate": 1.0  # Same currency, no conversion needed
	}, doc=po.as_dict())

	# Get rate from item details (handles price lists, last purchase rate from PO items, etc.)
	rate = item_details.get("rate") or item_details.get("price_list_rate") or 0

	# If no rate found, use our custom function to get valuation rate
	if not rate or rate == 0:
		rate = get_item_last_purchase_rate(recommendation.item_code, fallback_to_standard_rate=True, warehouse=recommendation.warehouse)

	po.append("items", {
		"item_code": recommendation.item_code,
		"item_name":  recommendation.item_name,
		"warehouse": recommendation.warehouse,
		"qty": recommendation.recommended_order_qty,
		"rate": rate,
		"schedule_date": schedule_date,
		"uom": item_details.get("stock_uom") or item_details.get("uom")
	})

	# Purchase Order status field has specific valid values
	valid_po_statuses = ["", "Draft", "On Hold", "To Receive and Bill", "To Bill", "To Receive",
	                     "Completed", "Cancelled", "Closed", "Delivered"]

	# Set status to "Draft" for new Purchase Orders
	po.status = "Draft"

	# Set missing values (calculates taxes, totals, etc.)
	po.set_missing_values()

	# Ensure status remains "Draft" after set_missing_values()
	po.status = "Draft"

	po.insert(ignore_permissions=True)

	# Reload to get the actual saved state
	po.reload()

	# Verify and enforce Draft status after insert
	if po.status != "Draft" or po.docstatus != 0:
		frappe.db.set_value("Purchase Order", po.name, "status", "Draft")
		frappe.db.commit()
		po.reload()

	frappe.db.commit()


	# Update status to "Ordered" and link PO when creation succeeds
	# Use raw SQL for direct update (workflow state "Ordered" exists but we update programmatically)
	frappe.db.sql("""
		UPDATE `tabReplenishment Recommendation`
		SET purchase_order = %s, status = %s
		WHERE name = %s
	""", (po.name, "Ordered", recommendation.name))
	frappe.db.commit()

	return {
		"purchase_order": po.name,
		"supplier": supplier,
		"company": company,
		"total_amount": po.grand_total,
		"status": "success"
	}


def get_supplier_for_recommendation(recommendation):
	"""Select supplier based on configured strategy"""
	settings = frappe.get_single("Replenishment Settings")
	strategy = settings.supplier_selection_strategy or "Preferred Supplier"

	# Strategy 1: Use preferred supplier (simple, default)
	if strategy == "Preferred Supplier":
		# Priority 1: Preferred supplier from recommendation
		if recommendation.preferred_supplier:
			return recommendation.preferred_supplier

		# Priority 2: Preferred supplier from Item Reorder (manually entered)
		item_reorder = frappe.db.get_value(
			"Item Reorder",
			{
				"parent": recommendation.item_code,
				"warehouse": recommendation.warehouse
			},
			"preferred_supplier"
		)

		if item_reorder:
			return item_reorder

		# No supplier found - user must manually enter preferred_supplier in Item Reorder table
		return None

	# Strategy 2-4: Intelligent selection from multiple suppliers
	suppliers_data = get_suppliers_with_metrics(recommendation)

	if not suppliers_data:
		# Fallback to preferred supplier logic if no data available
		return get_supplier_for_recommendation_fallback(recommendation)

	# Strategy 2: Pick supplier with shortest delivery time
	if strategy == "Shortest Lead Time":
		best_supplier = min(suppliers_data, key=lambda x: x.get("lead_time_days", 999))
		return best_supplier["supplier"]

	# Strategy 3: Pick cheapest supplier
	elif strategy == "Lowest Cost":
		best_supplier = min(suppliers_data, key=lambda x: x.get("price", 999999))
		return best_supplier["supplier"]

	# Strategy 4: Balance between lead time and cost (50/50 weight)
	elif strategy == "Balanced (Lead Time + Cost)":
		if len(suppliers_data) == 1:
			return suppliers_data[0]["supplier"]

		# Normalize values to 0-1 scale for fair comparison
		max_lead_time = max(s.get("lead_time_days", 0) for s in suppliers_data) or 1
		max_price = max(s.get("price", 0) for s in suppliers_data) or 1

		best_score = float('inf')
		best_supplier = None

		for supplier_data in suppliers_data:
			lead_time = supplier_data.get("lead_time_days", 0)
			price = supplier_data.get("price", 0)

			# Normalize: lower is better for both
			normalized_lead_time = (lead_time / max_lead_time) if max_lead_time > 0 else 0
			normalized_price = (price / max_price) if max_price > 0 else 0
			# Combined score: 50% lead time, 50% cost
			score = (normalized_lead_time * 0.5) + (normalized_price * 0.5)

			if score < best_score:
				best_score = score
				best_supplier = supplier_data["supplier"]

		return best_supplier

	return get_supplier_for_recommendation_fallback(recommendation)


def get_supplier_with_metrics_for_strategy(recommendation):
	"""Get supplier based on intelligent selection strategy - returns supplier with metrics"""
	settings = frappe.get_single("Replenishment Settings")
	strategy = settings.supplier_selection_strategy or "Preferred Supplier"

	# Preferred Supplier strategy is handled separately (doesn't need metrics evaluation)
	if strategy == "Preferred Supplier":
		return None

	# Get all available suppliers with their lead times and prices for evaluation
	suppliers_data = get_suppliers_with_metrics(recommendation)

	if not suppliers_data:
		return None

	# Apply selection strategy and return supplier with full metrics
	if strategy == "Shortest Lead Time":
		# Pick supplier with minimum lead time
		best_supplier = min(suppliers_data, key=lambda x: x.get("lead_time_days", 999))
		return best_supplier

	elif strategy == "Lowest Cost":
		# Pick supplier with minimum price
		best_supplier = min(suppliers_data, key=lambda x: x.get("price", 999999))
		return best_supplier

	elif strategy == "Balanced (Lead Time + Cost)":
		# If only one supplier, return it
		if len(suppliers_data) == 1:
			return suppliers_data[0]

		# Normalize values for fair comparison
		max_lead_time = max(s.get("lead_time_days", 0) for s in suppliers_data) or 1
		max_price = max(s.get("price", 0) for s in suppliers_data) or 1

		best_score = float('inf')
		best_supplier_data = None

		# Calculate balanced score for each supplier
		for supplier_data in suppliers_data:
			lead_time = supplier_data.get("lead_time_days", 0)
			price = supplier_data.get("price", 0)

			# Normalize to 0-1 scale (lower is better for both)
			normalized_lead_time = (lead_time / max_lead_time) if max_lead_time > 0 else 0
			normalized_price = (price / max_price) if max_price > 0 else 0
			# Combined score: 50% lead time weight, 50% cost weight
			score = (normalized_lead_time * 0.5) + (normalized_price * 0.5)

			if score < best_score:
				best_score = score
				best_supplier_data = supplier_data

		return best_supplier_data

	return None


def get_suppliers_with_metrics(recommendation):
	"""Get all suppliers for an item with their lead times and prices - used for intelligent selection"""
	suppliers_data = []

	# Get suppliers manually entered in Item Reorder table (preferred_supplier field)
	# Users manually set preferred suppliers for different warehouses in Item Reorder table
	item_reorder_suppliers = frappe.get_all(
		"Item Reorder",
		filters={
			"parent": recommendation.item_code,
			"preferred_supplier": ["!=", ""]  # Only get rows where preferred_supplier is manually entered
		},
		fields=["preferred_supplier", "warehouse", "supplier_lead_time_days"],
		as_dict=True
	)

	# Get unique suppliers from Item Reorder table
	all_suppliers = set()
	for item_reorder in item_reorder_suppliers:
		if item_reorder.preferred_supplier:
			all_suppliers.add(item_reorder.preferred_supplier)

	if not all_suppliers:
		return []

	warehouse_doc = frappe.get_doc("Warehouse", recommendation.warehouse)
	company = warehouse_doc.company

	# Get price list for fetching prices
	default_price_list = frappe.db.get_value("Company", company, "default_supplier_price_list")
	if not default_price_list:
		# Fallback: get any buying price list
		price_list = frappe.db.get_value(
			"Price List",
			{"buying": 1, "enabled": 1},
			"name",
			order_by="creation asc"
		)
		default_price_list = price_list

	# Create a map of suppliers from Item Reorder for quick lookup
	# Key: supplier, Value: {warehouse: warehouse, lead_time: lead_time}
	item_reorder_map = {}
	for item_reorder in item_reorder_suppliers:
		if item_reorder.preferred_supplier:
			# Store warehouse-specific data if available
			if item_reorder.preferred_supplier not in item_reorder_map:
				item_reorder_map[item_reorder.preferred_supplier] = []
			item_reorder_map[item_reorder.preferred_supplier].append({
				"warehouse": item_reorder.warehouse,
				"lead_time_days": item_reorder.supplier_lead_time_days
			})

	# For each supplier, get lead time and price
	for supplier in all_suppliers:
		lead_time = None
		price = None

		# Priority 1: Get lead time from Item Reorder (warehouse-specific, manually entered)
		# First check if this supplier is set as preferred for this specific warehouse
		if supplier in item_reorder_map:
			# Check if there's a warehouse-specific entry for this supplier
			for reorder_entry in item_reorder_map[supplier]:
				if reorder_entry["warehouse"] == recommendation.warehouse and reorder_entry["lead_time_days"]:
					lead_time = reorder_entry["lead_time_days"]
					break

			# If no warehouse-specific match, use any available lead time from Item Reorder for this supplier
			if not lead_time:
				for reorder_entry in item_reorder_map[supplier]:
					if reorder_entry["lead_time_days"]:
						lead_time = reorder_entry["lead_time_days"]
						break

		# Also check general Item Reorder for this warehouse (without preferred supplier match)
		if not lead_time:
			item_reorder_general = frappe.db.get_value(
				"Item Reorder",
				{
					"parent": recommendation.item_code,
					"warehouse": recommendation.warehouse
				},
				"supplier_lead_time_days"
			)
			if item_reorder_general:
				lead_time = item_reorder_general

		# Priority 2: Get from Item Price (supplier-specific, if configured in price list)
		if not lead_time:
			item_price = frappe.db.get_value(
				"Item Price",
				{
					"item_code": recommendation.item_code,
					"supplier": supplier,
					"price_list": default_price_list,
					"buying": 1
				},
				["lead_time_days", "price_list_rate"],
				as_dict=True,
				order_by="valid_from desc"  # Get most recent price
			)

			if item_price:
				if item_price.lead_time_days:
					lead_time = item_price.lead_time_days
				price = item_price.price_list_rate

		# Priority 3: Fallback to Item level lead time
		if not lead_time:
			item = frappe.get_doc("Item", recommendation.item_code)
			lead_time = item.lead_time_days or 0

		# Get price if not found in Item Price
		if not price:
			# Get last purchase rate from Purchase Order Item history, not Item master
			price = get_item_last_purchase_rate(recommendation.item_code, fallback_to_standard_rate=True, warehouse=recommendation.warehouse)

		suppliers_data.append({
			"supplier": supplier,
			"lead_time_days": lead_time or 0,
			"price": price or 0
		})

	return suppliers_data


def get_supplier_for_recommendation_fallback(recommendation):
	"""Fallback supplier selection - uses only Item Reorder table (manually entered preferred suppliers)"""
	# Priority 1: Preferred supplier from recommendation
	if recommendation.preferred_supplier:
		return recommendation.preferred_supplier

	# Priority 2: Preferred supplier from Item Reorder (manually entered)
	item_reorder = frappe.db.get_value(
		"Item Reorder",
		{
			"parent": recommendation.item_code,
			"warehouse": recommendation.warehouse
		},
		"preferred_supplier"
	)

	if item_reorder:
		return item_reorder

	# No supplier found - user must manually enter preferred_supplier in Item Reorder table
	return None


def get_supplier_with_lead_time(recommendation):
	"""Get supplier and its specific lead time - handles different selection strategies"""
	settings = frappe.get_single("Replenishment Settings")
	strategy = settings.supplier_selection_strategy or "Preferred Supplier"

	# For intelligent strategies, use lead time from evaluation process
	if strategy != "Preferred Supplier":
		supplier_data = get_supplier_with_metrics_for_strategy(recommendation)
		if supplier_data:
			return {
				"supplier": supplier_data["supplier"],
				"lead_time_days": supplier_data.get("lead_time_days", 0)
			}
		# Fallback if no data found
		supplier = get_supplier_for_recommendation(recommendation)
		if not supplier:
			return None

	# For Preferred Supplier strategy, get supplier first
	supplier = get_supplier_for_recommendation(recommendation)

	if not supplier:
		return None

	# Get supplier-specific lead time (Priority: Item Reorder → Item Price → Recommendation → Item Level)
	lead_time = None

	# Priority 1: Item Reorder (warehouse-specific, manually entered)
	item_reorder = frappe.db.get_value(
		"Item Reorder",
		{
			"parent": recommendation.item_code,
			"warehouse": recommendation.warehouse,
			"preferred_supplier": supplier
		},
		"supplier_lead_time_days"
	)
	if item_reorder:
		lead_time = item_reorder

	# Priority 2: Item Price (supplier-specific, if configured in price list)
	if not lead_time:
		warehouse_doc = frappe.get_doc("Warehouse", recommendation.warehouse)
		company = warehouse_doc.company

		default_price_list = frappe.db.get_value("Company", company, "default_supplier_price_list")
		if not default_price_list:
			price_list = frappe.db.get_value(
				"Price List",
				{"buying": 1, "enabled": 1},
				"name",
				order_by="creation asc"
			)
			default_price_list = price_list

		if default_price_list:
			item_price = frappe.db.get_value(
				"Item Price",
				{
					"item_code": recommendation.item_code,
					"supplier": supplier,
					"price_list": default_price_list,
					"buying": 1
				},
				"lead_time_days",
				order_by="valid_from desc"
			)
			if item_price:
				lead_time = item_price

	# Priority 3: Use recommendation's lead time (from reorder point calculation)
	if not lead_time:
		lead_time = recommendation.lead_time_days or 0

	# Priority 4: Fallback to Item level lead time
	if not lead_time:
		item = frappe.get_doc("Item", recommendation.item_code)
		lead_time = item.lead_time_days or 0

	return {
		"supplier": supplier,
		"lead_time_days": lead_time or 0
	}

