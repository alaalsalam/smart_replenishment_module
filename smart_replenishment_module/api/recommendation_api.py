# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

import frappe
from frappe import _
from frappe.utils import flt
from smart_replenishment_module.api.recommendation_generator import generate_recommendations
from smart_replenishment_module.utils.logger import log_error


@frappe.whitelist()
def get_recommendations(filters=None, page=1, page_size=10, sort_by="priority"):
	# Handle JSON string filters from API calls
	if isinstance(filters, str):
		import json
		filters = json.loads(filters)
	
	if not filters:
		filters = {}
	
	query_filters = {}
	
	# Filters
	if filters.get("status"):
		query_filters["status"] = filters["status"]
	
	if filters.get("priority"):
		query_filters["priority"] = filters["priority"]
	
	if filters.get("warehouse"):
		query_filters["warehouse"] = filters["warehouse"]
	
	if filters.get("item_code"):
		query_filters["item_code"] = filters["item_code"]
	
	if filters.get("item_group"):
		query_filters["item_group"] = filters["item_group"]
	
	page = int(page)
	page_size = int(page_size)
	offset = (page - 1) * page_size
	
	total_count = frappe.db.count("Replenishment Recommendation", filters=query_filters)
	
	# Sorting
	if sort_by == "priority":
		order_by = "FIELD(priority, 'High', 'Medium', 'Low')"
	elif sort_by == "created":
		order_by = "creation DESC"
	elif sort_by == "current_stock_qty":
		order_by = "current_stock_qty ASC"
	else:
		order_by = "modified DESC"
	
	# Priority sorting	
	if sort_by == "priority":
		recommendations = frappe.db.sql("""
			SELECT 
				name,
				item_code,
				item_name,
				warehouse,
				status,
				priority,
				current_stock_qty,
				reorder_point,
				recommended_order_qty,
				average_daily_consumption,
				lead_time_days,
				safety_stock_days,
				preferred_supplier,
				estimated_cost,
				purchase_order,
				creation,
				modified
			FROM `tabReplenishment Recommendation`
			WHERE {conditions}
			ORDER BY FIELD(priority, 'High', 'Medium', 'Low'), modified DESC
			LIMIT %(limit)s OFFSET %(offset)s
		""".format(
			conditions=build_where_conditions(query_filters)
		), {
			**query_filters,
			"limit": page_size,
			"offset": offset
		}, as_dict=True)
	else:
		recommendations = frappe.get_all(
			"Replenishment Recommendation",
			filters=query_filters,
			fields=[
				"name", "item_code", "item_name", "warehouse", "status", "priority",
				"current_stock_qty", "reorder_point", "recommended_order_qty",
				"average_daily_consumption", "lead_time_days", "safety_stock_days",
				"preferred_supplier", "estimated_cost", "purchase_order",
				"creation", "modified"
			],
			order_by=order_by,
			limit=page_size,
			limit_start=offset
		)
	
	# Calculate total pages - ceiling division
	total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0
	
	# Set HTTP status for API response
	frappe.local.response["http_status_code"] = 200
	
	return {
		"data": recommendations,
		"total_count": total_count,
		"page": page,
		"page_size": page_size,
		"total_pages": total_pages
	}


def build_where_conditions(filters):
	"""Build WHERE conditions for SQL query"""
	conditions = []
	
	if filters.get("status"):
		conditions.append("status = %(status)s")
	
	if filters.get("priority"):
		conditions.append("priority = %(priority)s")
	
	if filters.get("warehouse"):
		conditions.append("warehouse = %(warehouse)s")
	
	if filters.get("item_code"):
		conditions.append("item_code = %(item_code)s")
	
	# Need subquery for item_group since it's on Item, not Recommendation
	if filters.get("item_group"):
		conditions.append("item_code IN (SELECT name FROM `tabItem` WHERE item_group = %(item_group)s)")
	
	# Return always-true condition if no filters (to avoid empty WHERE clause)
	if not conditions:
		return "1=1"
	
	return " AND ".join(conditions)


@frappe.whitelist()
def trigger_recommendation_generation(warehouse=None):
	"""Manually trigger recommendation generations"""
	try:
		result = generate_recommendations(warehouse=warehouse)
		
		frappe.local.response["http_status_code"] = 200
		
		return {
			"status": "success",
			"created_count": result["created_count"],
			"skipped_count": result["skipped_count"],
			"total_processed": result["total_processed"],
			"errors": result.get("errors", [])
		}
	except Exception as e:
		frappe.local.response["http_status_code"] = 500
		log_error(
			title="Error triggering recommendation generation",
			message=str(e),
			traceback=frappe.get_traceback()
		)
		return {
			"status": "error",
			"message": str(e)
		}


@frappe.whitelist(methods=['POST'])
def approve_recommendation(recommendation_name):
	"""API endpoint to approve a recommendation - mainly for external integrations"""
	try:
		recommendation = frappe.get_doc("Replenishment Recommendation", recommendation_name)
		
		# Validate status before approving
		if recommendation.status != "Pending":
			frappe.local.response["http_status_code"] = 400
			return {
				"status": "error",
				"message": _("Only pending recommendations can be approved. Current status: {0}").format(
					recommendation.status
				)
			}
		
		recommendation.status = "Approved"
		recommendation.save(ignore_permissions=True)
		frappe.db.commit()
		
		frappe.local.response["http_status_code"] = 200
		
		return {
			"status": "success",
			"recommendation": recommendation.name,
			"new_status": "Approved"
		}
	except Exception as e:
		frappe.local.response["http_status_code"] = 500
		log_error(
			title="Error approving recommendation",
			message=str(e),
			reference_doctype="Replenishment Recommendation",
			reference_name=recommendation_name,
			traceback=frappe.get_traceback()
		)
		return {
			"status": "error",
			"message": str(e)
		}


@frappe.whitelist(methods=['POST'])
def create_purchase_order(recommendation_name):
	try:
		from smart_replenishment_module.api.purchase_order_creator import create_purchase_order_from_recommendation
		
		result = create_purchase_order_from_recommendation(recommendation_name)
		
		frappe.local.response["http_status_code"] = 200
		
		return {
			"status": "success",
			**result
		}
	except Exception as e:
		frappe.local.response["http_status_code"] = 500
		log_error(
			title="Error creating Purchase Order",
			message=str(e),
			reference_doctype="Replenishment Recommendation",
			reference_name=recommendation_name,
			traceback=frappe.get_traceback()
		)
		return {
			"status": "error",
			"message": str(e)
		}

