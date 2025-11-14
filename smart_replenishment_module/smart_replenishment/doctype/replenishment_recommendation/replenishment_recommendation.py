# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

import frappe
from frappe.model.document import Document
from frappe import _


class ReplenishmentRecommendation(Document):
	def validate(self):
		self.validate_duplicate_recommendation()
		self.validate_quantities()
		self.validate_status_transitions()
		self.validate_approved_status_update()
	
	def validate_duplicate_recommendation(self):
		"""Prevent duplicate pending/approved recommendations for same item-warehouse"""
		if self.status in ["Pending", "Approved"]:
			existing = frappe.db.exists(
				"Replenishment Recommendation",
				{
					"item_code": self.item_code,
					"warehouse": self.warehouse,
					"status": ["in", ["Pending", "Approved"]],
					"docstatus": ["!=", 2],  # Exclude cancelled documents
					"name": ["!=", self.name]
				}
			)
			if existing:
				frappe.throw(
					_("A {0} recommendation already exists for Item {1} in Warehouse {2}").format(
						self.status, self.item_code, self.warehouse
					)
				)
	
	def validate_quantities(self):
		if self.recommended_order_qty <= 0:
			frappe.throw(_("Recommended Order Quantity must be greater than 0"))
	
	def validate_status_transitions(self):
		"""Prevent manual status changes - status should only be changed by workflow"""
		if self.is_new():
			return
		
		# If workflow is active, let workflow validation handle status transitions
		# Workflow validation will prevent invalid transitions
		workflow_exists = frappe.db.exists("Workflow", {"document_type": "Replenishment Recommendation", "is_active": 1})
		if workflow_exists:
			# Workflow is active - workflow validation will handle status changes
			# We only need to prevent direct field edits in the UI
			# Check if this is a direct field change (not from workflow)
			# If _doc_before_save exists and status changed, workflow validation will check it
			# If _doc_before_save doesn't exist, this might be a programmatic change (like from workflow)
			# So we skip validation and let workflow handle it
			return
		
		# No workflow - prevent manual changes (status is read-only)
		old_status = frappe.db.get_value("Replenishment Recommendation", self.name, "status")
		if old_status and self.status != old_status:
			frappe.throw(
				_("Status cannot be changed manually. Status changes are managed by the workflow system. Current status: {0}").format(old_status)
			)
	
	def validate_approved_status_update(self):
		"""Prevent updates to approved recommendations - only pending recommendations can be updated"""
		if self.is_new():
			return
		
		# Get the original status from database
		old_status = frappe.db.get_value("Replenishment Recommendation", self.name, "status")
		
		# If the original status was "Approved", prevent any updates
		# Allow status changes (which are handled by workflow validation)
		if old_status == "Approved":
			# Check if this is just a status change (allowed by workflow)
			if self.status != "Approved":
				# Status is changing from Approved - this might be workflow transitioning to Ordered
				# Allow it if workflow is active
				workflow_exists = frappe.db.exists("Workflow", {"document_type": "Replenishment Recommendation", "is_active": 1})
				if workflow_exists:
					return  # Workflow is Causing the status change
			
			# If status is still Approved, check if any other fields changed
			# Get the original document to compare
			old_doc = self.get_doc_before_save()
			if old_doc:
				# Check if any significant fields changed (excluding status, modified, etc.)
				fields_to_check = [
					"recommended_order_qty", "reorder_point", "minimum_stock_level",
					"maximum_stock_level", "priority", "preferred_supplier",
					"estimated_cost", "lead_time_days", "safety_stock_days"
				]
				
				for field in fields_to_check:
					if hasattr(self, field) and hasattr(old_doc, field):
						if getattr(self, field) != getattr(old_doc, field):
							frappe.throw(
								_("Approved recommendations cannot be updated. Only pending recommendations can be modified. Current status: {0}").format(old_status)
							)
	
	def on_submit(self):
		"""Auto-create PO when recommendation is submitted (only for approved status)"""
		# Workflow transitions to Approved or Rejected both submit the document (docstatus=1)
		# Only create PO for Approved status
		if self.status == "Approved":
			try:
				self.create_purchase_order()
			except Exception as e:
				# Log but don't fail - document is already submitted
				from smart_replenishment_module.utils.logger import log_error
				log_error(
					title=f"Error creating PO on submit for {self.name}",
					message=str(e),
					reference_doctype="Replenishment Recommendation",
					reference_name=self.name,
					traceback=frappe.get_traceback()
				)
				# Don't re-raise - document is already submitted
		elif self.status == "Rejected":
			# Rejected recommendations are submitted and locked, but don't create PO
			# Add audit trail comment
			self.add_comment(
				"Workflow",
				_("Recommendation rejected. No purchase order will be created. Document is now locked.")
			)
	
	def create_purchase_order(self):
		"""Create PO from approved recommendation - called from on_submit hook"""
		if self.status != "Approved":
			# Only log if we're in on_submit (self.docstatus == 1)
			# Otherwise, show message to user
			if self.docstatus == 1:
				from smart_replenishment_module.utils.logger import log_error
				log_error(
					title=f"Recommendation {self.name} not approved",
					message=f"Cannot create PO for recommendation with status: {self.status}",
					reference_doctype="Replenishment Recommendation",
					reference_name=self.name
				)
			else:
				frappe.msgprint(
					_("Purchase Order can only be created for Approved recommendations. Current status: {0}").format(self.status),
					alert=True,
					indicator="orange"
				)
			return
		
		if self.purchase_order:
			msg = _("Purchase Order {0} already exists for this recommendation").format(self.purchase_order)
			if self.docstatus == 1:
				# Just log, don't show message
				pass
			else:
				frappe.msgprint(msg, alert=True, indicator="blue")
			return
		
		from smart_replenishment_module.api.purchase_order_creator import create_purchase_order_from_recommendation
		
		try:
			result = create_purchase_order_from_recommendation(self.name)
			# Reload to get updated PO link and status
			self.reload()
			
			# Add comment for audit trail
			self.add_comment(
				"Comment",
				_("Purchase Order {0} created automatically for {1} units to supplier {2}").format(
					result.get("purchase_order"),
					self.recommended_order_qty,
					result.get("supplier")
				)
			)
			
			frappe.msgprint(
				_("Purchase Order {0} created successfully").format(result.get("purchase_order")),
				alert=True,
				indicator="green"
			)
			
		except Exception as e:
			from smart_replenishment_module.utils.logger import log_error
			log_error(
				title=_("Purchase Order Creation Failed for {0}").format(self.name),
				message=frappe.get_traceback(),
				reference_doctype="Replenishment Recommendation",
				reference_name=self.name,
				item_code=self.item_code,
				warehouse=self.warehouse
			)
			frappe.throw(
				_("Could not create Purchase Order: {0}").format(str(e))
			)
	
	def on_update(self):
		"""Update current stock when document is updated"""
		if self.item_code and self.warehouse:
			self.current_stock_qty = self.get_current_stock()
	
	def get_current_stock(self):
		"""Get current stock balance - used for display and calculations"""
		from erpnext.stock.utils import get_stock_balance
		stock_balance = get_stock_balance(
			self.item_code,
			self.warehouse,
			with_valuation_rate=False
		)
		return stock_balance or 0
	
	def before_save(self):
		"""Update stock quantity before saving - ensures it's always current"""
		if self.item_code and self.warehouse:
			self.current_stock_qty = self.get_current_stock()

