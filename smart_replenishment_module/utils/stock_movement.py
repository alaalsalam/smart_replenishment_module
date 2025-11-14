# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

"""
Generic utility functions for handling stock movements across different doctypes.
Used by Stock Entry, Delivery Note, and Sales Invoice to update reorder points.
"""

import frappe
from frappe import _
from smart_replenishment_module.utils.logger import log_info, log_error


def get_outgoing_items_from_doc(doc):
	"""
	Extract item-warehouse combinations from outgoing stock movement documents.
	
	Supports:
	- Stock Entry (Material Issue, Material Transfer)
	- Delivery Note (items with warehouse)
	- Sales Invoice (items with warehouse, only if update_stock=1)
	
	Args:
		doc: Document object (Stock Entry, Delivery Note, or Sales Invoice)
		
	Returns:
		set: Set of tuples (item_code, warehouse) for outgoing stock movements
	"""
	print(f"[REORDER DEBUG] get_outgoing_items_from_doc() called for {doc.doctype} {doc.name}")
	items_to_update = set()
	doctype = doc.doctype
	print(f"[REORDER DEBUG] Document type: {doctype}")
	
	# Stock Entry
	if doctype == "Stock Entry":
		outgoing_types = ["Material Issue", "Material Transfer"]
		print(f"[REORDER DEBUG] Stock Entry type: {doc.stock_entry_type}")
		
		if doc.stock_entry_type not in outgoing_types:
			print(f"[REORDER DEBUG] Stock Entry type {doc.stock_entry_type} not in outgoing types, returning empty set")
			return items_to_update
		
		print(f"[REORDER DEBUG] Processing {len(doc.items)} items in Stock Entry")
		for item in doc.items:
			# Material Issue: source warehouse is outgoing
			if doc.stock_entry_type == "Material Issue":
				if item.s_warehouse and item.item_code:
					items_to_update.add((item.item_code, item.s_warehouse))
					print(f"[REORDER DEBUG] Added Material Issue: {item.item_code} from {item.s_warehouse}")
			# Material Transfer: source warehouse is outgoing, destination is incoming
			elif doc.stock_entry_type == "Material Transfer":
				if item.s_warehouse and item.item_code:
					items_to_update.add((item.item_code, item.s_warehouse))
					print(f"[REORDER DEBUG] Added Material Transfer source: {item.item_code} from {item.s_warehouse}")
				# Note: destination warehouse is incoming, not outgoing, so we don't update it
	
	# Delivery Note
	elif doctype == "Delivery Note":
		# Delivery Note always reduces stock (unless it's a return)
		print(f"[REORDER DEBUG] Delivery Note is_return: {doc.is_return}")
		if not doc.is_return:
			print(f"[REORDER DEBUG] Processing {len(doc.items)} items in Delivery Note")
			for item in doc.items:
				if item.warehouse and item.item_code:
					items_to_update.add((item.item_code, item.warehouse))
					print(f"[REORDER DEBUG] Added Delivery Note: {item.item_code} from {item.warehouse}")
	
	# Sales Invoice
	elif doctype == "Sales Invoice":
		# Sales Invoice only updates stock if update_stock=1
		print(f"[REORDER DEBUG] Sales Invoice update_stock: {doc.update_stock}, is_return: {doc.is_return}")
		if doc.update_stock == 1 and not doc.is_return:
			print(f"[REORDER DEBUG] Processing {len(doc.items)} items in Sales Invoice")
			for item in doc.items:
				if item.warehouse and item.item_code:
					items_to_update.add((item.item_code, item.warehouse))
					print(f"[REORDER DEBUG] Added Sales Invoice: {item.item_code} from {item.warehouse}")
	
	print(f"[REORDER DEBUG] get_outgoing_items_from_doc() returning {len(items_to_update)} item-warehouse combinations: {items_to_update}")
	return items_to_update


def queue_reorder_point_update(doc, items_warehouses):
	"""
	Queue background job to update reorder points for affected items.
	
	Args:
		doc: Document object that triggered the update
		items_warehouses: Set of tuples (item_code, warehouse)
	"""
	print(f"[REORDER DEBUG] queue_reorder_point_update() called for {doc.doctype} {doc.name}")
	print(f"[REORDER DEBUG] Items to queue: {items_warehouses}")
	
	if not items_warehouses:
		print(f"[REORDER DEBUG] No items to queue, returning early")
		return
	
	print(f"[REORDER DEBUG] Enqueuing background job with {len(items_warehouses)} item-warehouse combinations")
	
	# Queue background job - doesn't block document submission
	frappe.enqueue(
		"smart_replenishment_module.utils.stock_movement.update_reorder_points_for_items",
		items_warehouses=list(items_warehouses),
		reference_doctype=doc.doctype,
		reference_name=doc.name,
		queue="short",
		
	)
	
	print(f"[REORDER DEBUG] Background job enqueued successfully")
	
	log_info(
		title=f"{doc.doctype} submitted - reorder points update queued",
		message=f"Queued reorder point update for {len(items_warehouses)} item-warehouse combinations from {doc.doctype} {doc.name}",
		reference_doctype=doc.doctype,
		reference_name=doc.name
	)


def update_reorder_points_for_items(items_warehouses, reference_doctype=None, reference_name=None):
	"""
	Update reorder points for specific item-warehouse combinations.
	Called from background job after document submission.
	
	Args:
		items_warehouses: List of tuples (item_code, warehouse)
		reference_doctype: Optional doctype name for logging
		reference_name: Optional document name for logging
	"""
	print(f"[REORDER DEBUG] update_reorder_points_for_items() called from background job")
	print(f"[REORDER DEBUG] Reference: {reference_doctype} {reference_name}")
	print(f"[REORDER DEBUG] Items to process: {items_warehouses}")
	
	from smart_replenishment_module.api.stock_analyzer import update_reorder_points
	
	updated_count = 0
	errors = []
	
	for item_code, warehouse in items_warehouses:
		print(f"[REORDER DEBUG] Processing item: {item_code}, warehouse: {warehouse}")
		try:
			# Check if Item Reorder exists for this combination
			item_reorder = frappe.db.exists(
				"Item Reorder",
				{
					"parent": item_code,
					"warehouse": warehouse
				}
			)
			
			print(f"[REORDER DEBUG] Item Reorder exists check: {item_reorder}")
			
			if not item_reorder:
				# No Item Reorder configured - skip
				print(f"[REORDER DEBUG] No Item Reorder found for {item_code} in {warehouse}, skipping")
				continue
			
			print(f"[REORDER DEBUG] Calling update_reorder_points() for {item_code} in {warehouse}")
			# Update reorder points for this specific item-warehouse
			result = update_reorder_points(item_code=item_code, warehouse=warehouse)
			
			print(f"[REORDER DEBUG] update_reorder_points() result: {result}")
			
			if result.get("updated_count", 0) > 0:
				updated_count += result["updated_count"]
				print(f"[REORDER DEBUG] Successfully updated {result['updated_count']} reorder point(s)")
				
				log_info(
					title="Reorder point updated after stock movement",
					message=f"Updated reorder point for {item_code} in {warehouse}",
					reference_doctype="Item",
					reference_name=item_code
				)
			else:
				print(f"[REORDER DEBUG] No reorder points updated (updated_count=0)")
			
			# Always check if stock is below reorder level and generate recommendations
			# (Stock movement might have caused stock to go below reorder level even if reorder point wasn't updated)
			print(f"[REORDER DEBUG] Checking if stock is below reorder level for {item_code} in {warehouse}")
			try:
				from erpnext.stock.utils import get_stock_balance
				from smart_replenishment_module.api.recommendation_generator import regenerate_recommendations_for_item
				
				current_stock = get_stock_balance(item_code, warehouse) or 0
				reorder_level = frappe.db.get_value(
					"Item Reorder",
					{"parent": item_code, "warehouse": warehouse},
					"warehouse_reorder_level"
				) or 0
				
				print(f"[REORDER DEBUG] Current stock: {current_stock}, Reorder level: {reorder_level}")
				
				if reorder_level > 0 and current_stock < reorder_level:
					print(f"[REORDER DEBUG] Stock ({current_stock}) is below reorder level ({reorder_level}), generating recommendations")
					rec_result = regenerate_recommendations_for_item(item_code, warehouse)
					print(f"[REORDER DEBUG] Recommendation generation result: {rec_result}")
					
					if rec_result.get("created_count", 0) > 0:
						log_info(
							title="Recommendation generated after stock movement",
							message=f"Generated {rec_result['created_count']} recommendation(s) for {item_code} in {warehouse} (stock below reorder level)",
							reference_doctype="Item",
							reference_name=item_code
						)
				else:
					if reorder_level == 0:
						print(f"[REORDER DEBUG] Reorder level is 0, skipping recommendation check")
					else:
						print(f"[REORDER DEBUG] Stock ({current_stock}) is above reorder level ({reorder_level}), no recommendation needed")
			except Exception as rec_error:
				rec_error_msg = f"Error generating recommendations for {item_code} in {warehouse}: {str(rec_error)}"
				print(f"[REORDER DEBUG] ❌ ERROR: {rec_error_msg}")
				print(f"[REORDER DEBUG] Traceback: {frappe.get_traceback()}")
				
				# Log to Frappe Error Log for visibility
				frappe.log_error(
					message=f"{rec_error_msg}\n\nTraceback:\n{frappe.get_traceback()}",
					title=f"❌ Recommendation Generation Failed: {item_code}"
				)
				# Don't fail the whole job if recommendation generation fails
				pass
		
		except Exception as e:
			error_msg = f"Error updating reorder point for {item_code} in {warehouse}: {str(e)}"
			errors.append(error_msg)
			
			# Print to console for debugging
			print(f"[REORDER DEBUG] ❌ ERROR: {error_msg}")
			print(f"[REORDER DEBUG] Traceback: {frappe.get_traceback()}")
			
			# Log to Frappe Error Log for visibility in UI
			frappe.log_error(
				message=f"{error_msg}\n\nTraceback:\n{frappe.get_traceback()}",
				title=f"❌ Stock Movement Reorder Update Failed: {item_code}"
			)
			
			# Also log to our custom activity log
			log_error(
				title="Error updating reorder point after stock movement",
				message=error_msg,
				reference_doctype="Item",
				reference_name=item_code,
				traceback=frappe.get_traceback()
			)
	
	# Log summary if there were updates
	if updated_count > 0:
		log_info(
			title="Reorder points updated after stock movement",
			message=f"Updated {updated_count} reorder point(s) from {reference_doctype} {reference_name}",
			reference_doctype=reference_doctype or "Stock Movement",
			reference_name=reference_name
		)
	
	# Log errors if any
	if errors:
		frappe.log_error(
			"\n".join(errors),
			f"{reference_doctype or 'Stock Movement'}: Reorder Point Update Errors"
		)
	
	return {
		"updated_count": updated_count,
		"errors": errors
	}

