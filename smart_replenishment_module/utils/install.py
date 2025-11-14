# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	custom_fields()
	property_setters()
	create_workflow_states()
	disable_standared_actions()


def custom_fields():
	"""Create custom fields for Item and Item Reorder doctypes"""
	fields = {
		"Item": [
			{
				"fieldname": "requires_prescription",
				"fieldtype": "Check",
				"label": "Requires Prescription",
				"description": "Indicates if this medication requires a valid prescription from a licensed healthcare provider",
				"insert_after": "is_stock_item",
				"default": 0
			}
		],
		"Item Reorder": [
			{
				"fieldname": "minimum_stock_level",
				"fieldtype": "Float",
				"label": "Minimum Stock Level",
				"description": "Minimum stock level for this item-warehouse. Auto-calculated as reorder point, but can be manually overridden.",
				"insert_after": "warehouse_reorder_qty",
				"precision": "2",
				"non_negative": 1
			},
			{
				"fieldname": "maximum_stock_level",
				"fieldtype": "Float",
				"label": "Maximum Stock Level",
				"description": "Maximum stock level for this item-warehouse. Auto-calculated as (Reorder Point + Reorder Qty), but can be manually overridden.",
				"insert_after": "minimum_stock_level",
				"precision": "2",
				"non_negative": 1
			},
			{
				"fieldname": "safety_stock_days",
				"fieldtype": "Int",
				"label": "Safety Stock (Days)",
				"description": "Number of days of safety stock buffer. This dynamically adjusts with consumption patterns.",
				"insert_after": "maximum_stock_level",
				"non_negative": 1
			},
			{
				"fieldname": "supplier_lead_time_days",
				"fieldtype": "Int",
				"label": "Supplier Lead Time (Days)",
				"description": "Number of days for supplier to deliver. Overrides item-level lead time if specified.",
				"insert_after": "safety_stock_days",
				"non_negative": 1
			},
			{
				"fieldname": "preferred_supplier",
				"fieldtype": "Link",
				"label": "Preferred Supplier",
				"options": "Supplier",
				"description": "Preferred supplier for this item-warehouse combination",
				"insert_after": "supplier_lead_time_days"
			},
			{
				"fieldname": "average_daily_consumption",
				"fieldtype": "Float",
				"label": "Average Daily Consumption",
				"description": "Auto-calculated average daily consumption based on stock ledger analysis",
				"insert_after": "preferred_supplier",
				"read_only": 1,
				"precision": "2"
			},
			{
				"fieldname": "last_calculation_date",
				"fieldtype": "Date",
				"label": "Last Calculation Date",
				"description": "Date when consumption metrics were last calculated",
				"insert_after": "average_daily_consumption",
				"read_only": 1
			}
		]
	}
	
	create_custom_fields(fields, ignore_validate=True)


def property_setters():
	"""Create property setters to modify field properties (make fields non-required or read-only)"""
	ps_list = [
		# Make material_request_type non-required (we don't use standard auto-reorder)
		{
			"name": "Item Reorder-material_request_type-reqd",
			"field_name": "material_request_type",
			"property": "reqd",
			"property_type": "Check",
			"value": "0"
		},
		# Make warehouse_reorder_level mandatory - it's essential for the replenishment logic
		{
			"name": "Item Reorder-warehouse_reorder_level-reqd",
			"field_name": "warehouse_reorder_level",
			"property": "reqd",
			"property_type": "Check",
			"value": "1"
		},
		# Make calculated fields read-only - they're auto-updated by the system
		# {
		# 	"name": "Item Reorder-warehouse_reorder_level-read_only",
		# 	"field_name": "warehouse_reorder_level",
		# 	"property": "read_only",
		# 	"property_type": "Check",
		# 	"value": "1"
		# },
		{
			"name": "Item Reorder-minimum_stock_level-read_only",
			"field_name": "minimum_stock_level",
			"property": "read_only",
			"property_type": "Check",
			"value": "1"
		},
		{
			"name": "Item Reorder-maximum_stock_level-read_only",
			"field_name": "maximum_stock_level",
			"property": "read_only",
			"property_type": "Check",
			"value": "1"
		}
	]
	
	# Create property setters if they don't exist
	for ps in ps_list:
		if not frappe.db.exists("Property Setter", {"name": ps["name"]}):
			property_setter = frappe.new_doc("Property Setter")
			property_setter.doctype_or_field = "DocField"
			property_setter.doc_type = "Item Reorder"
			property_setter.field_name = ps["field_name"]
			property_setter.property = ps["property"]
			property_setter.property_type = ps["property_type"]
			property_setter.value = ps["value"]
			property_setter.insert(ignore_permissions=True)
			frappe.db.commit()


def create_workflow_states():
	"""Create Workflow State records required for Replenishment Recommendation workflow"""
	workflow_states = [
		{
			"name": "Ordered",
			"workflow_state_name": "Ordered"
		}
	]
	
	for state in workflow_states:
		if not frappe.db.exists("Workflow State", state["name"]):
			workflow_state = frappe.new_doc("Workflow State")
			workflow_state.workflow_state_name = state["workflow_state_name"]
			workflow_state.insert(ignore_permissions=True)
			frappe.db.commit()


def disable_standared_actions():
	stock_settings = frappe.get_single("Stock Settings")
	stock_settings.auto_indent = 0
	stock_settings.save(ignore_permissions=True)