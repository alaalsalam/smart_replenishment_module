# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

import frappe
from frappe import _
from smart_replenishment_module.utils.logger import log_info, log_error


def on_cancel(doc, method=None):
	"""Handle Purchase Order cancellation - reset linked Replenishment Recommendation"""
	# Find recommendations linked to this Purchase Order
	recommendations = frappe.get_all(
		"Replenishment Recommendation",
		filters={"purchase_order": doc.name},
		fields=["name", "status", "item_code", "warehouse"]
	)
	
	if not recommendations:
		return
	
	for rec in recommendations:
		try:
			# Get current status before update
			old_status = rec.status
			
			# Use SQL to directly update status and clear purchase_order link
			# This bypasses workflow validation since the recommendation might be in "Ordered" state (submitted)
			frappe.db.sql("""
				UPDATE `tabReplenishment Recommendation`
				SET purchase_order = NULL, status = %s
				WHERE name = %s
			""", ("Pending", rec.name))
			frappe.db.commit()
			
			# Reload the document to add comment
			rec_doc = frappe.get_doc("Replenishment Recommendation", rec.name)
			
			# Add comment for audit trail
			comment_message = _("Purchase Order {0} was cancelled. Recommendation status reset from {1} to Pending for review.").format(
				doc.name, old_status
			)
			
			# If document is submitted (docstatus=1), note that user may need to cancel it manually to edit
			if rec_doc.docstatus == 1:
				comment_message += " " + _("Note: Recommendation is still submitted. Cancel it manually if you need to edit it.")
			
			rec_doc.add_comment("Workflow", comment_message)
			
			log_info(
				title="Recommendation reset after PO cancellation",
				message=f"Recommendation {rec.name} reset to Pending after Purchase Order {doc.name} was cancelled (was {old_status})",
				reference_doctype="Replenishment Recommendation",
				reference_name=rec.name,
				item_code=rec.item_code,
				warehouse=rec.warehouse
			)
			
		except Exception as e:
			log_error(
				title=f"Error resetting recommendation {rec.name} after PO cancellation",
				message=str(e),
				reference_doctype="Replenishment Recommendation",
				reference_name=rec.name,
				traceback=frappe.get_traceback()
			)

