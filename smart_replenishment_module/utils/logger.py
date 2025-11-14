# Copyright (c) 2024, Zeiad Madboly and Contributors
# License: MIT

import frappe
from frappe.utils import now
from typing import Optional


def log_activity(
	title: str,
	message: str,
	log_type: str = "Info",
	severity: str = "Low",
	reference_doctype: Optional[str] = None,
	reference_name: Optional[str] = None,
	item_code: Optional[str] = None,
	warehouse: Optional[str] = None,
	traceback: Optional[str] = None,
	**kwargs
) -> str:
	"""Create a log entry in Replenishment Activity Log"""
	try:
		log_doc = frappe.get_doc({
			"doctype": "Replenishment Activity Log",
			"title": title,
			"message": message,
			"log_type": log_type,
			"severity": severity,
			"timestamp": now(),
			"status": "Active",
			"user": frappe.session.user,
			"module": "Smart Replenishment"
		})
		
		if reference_doctype:
			log_doc.reference_doctype = reference_doctype
		if reference_name:
			log_doc.reference_name = reference_name
		if item_code:
			log_doc.item_code = item_code
		if warehouse:
			log_doc.warehouse = warehouse
		if traceback:
			log_doc.traceback = traceback
		
		for key, value in kwargs.items():
			if hasattr(log_doc, key):
				setattr(log_doc, key, value)
		
		log_doc.insert(ignore_permissions=True)
		frappe.db.commit()
		
		return log_doc.name
		
	except Exception as e:
		frappe.log_error(
			title=f"Error creating activity log: {title}",
			message=f"Failed to create log entry: {str(e)}\nOriginal message: {message}"
		)
		return None


def log_info(title: str, message: str, **kwargs) -> str:
	"""Log informational message"""
	return log_activity(
		title=title,
		message=message,
		log_type="Info",
		severity="Low",
		**kwargs
	)


def log_warning(title: str, message: str, **kwargs) -> str:
	"""Log warning message"""
	return log_activity(
		title=title,
		message=message,
		log_type="Warning",
		severity="Medium",
		**kwargs
	)


def log_error(title: str, message: str, traceback: Optional[str] = None, **kwargs) -> str:
	"""Log error message"""
	return log_activity(
		title=title,
		message=message,
		log_type="Error",
		severity="High",
		traceback=traceback or frappe.get_traceback(),
		**kwargs
	)


def log_success(title: str, message: str, **kwargs) -> str:
	"""Log success message"""
	return log_activity(
		title=title,
		message=message,
		log_type="Success",
		severity="Low",
		**kwargs
	)


def log_critical_error(title: str, message: str, traceback: Optional[str] = None, **kwargs) -> str:
	"""Log critical error message"""
	return log_activity(
		title=title,
		message=message,
		log_type="Error",
		severity="Critical",
		traceback=traceback or frappe.get_traceback(),
		**kwargs
	)

