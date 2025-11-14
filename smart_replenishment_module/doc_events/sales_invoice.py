# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

"""
Document event handler for Sales Invoice.
Updates reorder points when stock is updated (if update_stock=1).
"""

from smart_replenishment_module.utils.stock_movement import (
	get_outgoing_items_from_doc,
	queue_reorder_point_update
)


def on_submit(doc, method=None):
	"""
	Triggered when Sales Invoice is submitted.
	Updates reorder points for items affected by outgoing stock movements.
	Only processes if update_stock=1.
	"""
	print(f"[REORDER DEBUG] Sales Invoice on_submit() called for {doc.name}")
	print(f"[REORDER DEBUG] Sales Invoice update_stock: {doc.update_stock}, is_return: {doc.is_return}")
	print(f"[REORDER DEBUG] Number of items: {len(doc.items)}")
	
	if doc.update_stock == 1:
		# Get outgoing items from the document
		items_to_update = get_outgoing_items_from_doc(doc)
		print(f"[REORDER DEBUG] Items to update from get_outgoing_items_from_doc: {items_to_update}")
		
		# Queue background job to update reorder points
		if items_to_update:
			print(f"[REORDER DEBUG] Queuing reorder point update for {len(items_to_update)} item-warehouse combinations")
			queue_reorder_point_update(doc, items_to_update)
		else:
			print(f"[REORDER DEBUG] No items to update, skipping queue")
	else:
		print(f"[REORDER DEBUG] update_stock is not 1, skipping reorder point update")

