# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

import frappe
from smart_replenishment_module.api.stock_analyzer import update_reorder_points
from smart_replenishment_module.api.recommendation_generator import generate_recommendations
from smart_replenishment_module.utils.logger import log_info, log_error, log_success


def scheduled_update_reorder_points():
	"""Scheduled task - runs daily to update reorder points based on consumption"""
	try:
		settings = frappe.get_single("Replenishment Settings")
		
		result = update_reorder_points()
		
		# Log results for monitoring
		log_info(
			title="Scheduled Reorder Point Update",
			message=f"Updated {result['updated_count']} reorder points, skipped {result['skipped_count']}, errors: {len(result['errors'])}"
		)
		
		return result
	except Exception as e:
		log_error(
			title="Error in scheduled reorder point update",
			message=str(e),
			traceback=frappe.get_traceback()
		)


def scheduled_generate_recommendations():
	"""Scheduled task - runs daily to generate recommendations (if enabled)"""
	try:
		settings = frappe.get_single("Replenishment Settings")
		
		# Check if auto-generation is enabled
		if not settings.auto_generate_enabled:
			return {
				"status": "skipped",
				"message": "Auto-generate is disabled in settings"
			}
		
		result = generate_recommendations()
		
		# Log results
		log_success(
			title="Scheduled Recommendation Generation",
			message=f"Generated {result['created_count']} recommendations, skipped {result['skipped_count']}, errors: {len(result['errors'])}"
		)
		
		return result
	except Exception as e:
		log_error(
			title="Error in scheduled recommendation generation",
			message=str(e),
			traceback=frappe.get_traceback()
		)

