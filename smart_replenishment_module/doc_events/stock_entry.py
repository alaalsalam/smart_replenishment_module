# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

"""
Document event handler for Stock Entry.
Updates reorder points when outgoing stock movements are submitted.
"""

from smart_replenishment_module.utils.stock_movement import (
	get_outgoing_items_from_doc,
	queue_reorder_point_update
)


def on_submit(doc, method=None):
	"""
	Triggered when Stock Entry is submitted.
	Updates reorder points for items affected by outgoing stock movements.
	"""
	print(f"[REORDER DEBUG] Stock Entry on_submit() called for {doc.name}")
	print(f"[REORDER DEBUG] Stock Entry type: {doc.stock_entry_type}")
	print(f"[REORDER DEBUG] Number of items: {len(doc.items)}")
	
	# Get outgoing items from the document
	items_to_update = get_outgoing_items_from_doc(doc)
	print(f"[REORDER DEBUG] Items to update from get_outgoing_items_from_doc: {items_to_update}")
	
	# Queue background job to update reorder points
	if items_to_update:
		print(f"[REORDER DEBUG] Queuing reorder point update for {len(items_to_update)} item-warehouse combinations")
		queue_reorder_point_update(doc, items_to_update)
	else:
		print(f"[REORDER DEBUG] No items to update, skipping queue")

