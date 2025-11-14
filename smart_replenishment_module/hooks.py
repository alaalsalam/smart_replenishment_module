app_name = "smart_replenishment_module"
app_title = "Smart Replenishment Module"
app_publisher = "Zeiad Madboly"
app_description = "Smart Replenishment Module for a pharmacy supply chain platform. This module should analyze inventory levels, consumption patterns, and supplier information to automatically generate purchase orders when stock levels reach reorder points."
app_email = "zeiadmadboly@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "smart_replenishment_module",
# 		"logo": "/assets/smart_replenishment_module/logo.png",
# 		"title": "Smart Replenishment Module",
# 		"route": "/smart_replenishment_module",
# 		"has_permission": "smart_replenishment_module.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/smart_replenishment_module/css/smart_replenishment_module.css"
# app_include_js = "/assets/smart_replenishment_module/js/smart_replenishment_module.js"

# include js, css files in header of web template
# web_include_css = "/assets/smart_replenishment_module/css/smart_replenishment_module.css"
# web_include_js = "/assets/smart_replenishment_module/js/smart_replenishment_module.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "smart_replenishment_module/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Item": "public/js/item.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "smart_replenishment_module/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "smart_replenishment_module.utils.jinja_methods",
# 	"filters": "smart_replenishment_module.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "smart_replenishment_module.install.before_install"
# after_install = "smart_replenishment_module.install.after_install"
after_migrate = "smart_replenishment_module.utils.install.execute"

# Uninstallation
# ------------

# before_uninstall = "smart_replenishment_module.uninstall.before_uninstall"
# after_uninstall = "smart_replenishment_module.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "smart_replenishment_module.utils.before_app_install"
# after_app_install = "smart_replenishment_module.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "smart_replenishment_module.utils.before_app_uninstall"
# after_app_uninstall = "smart_replenishment_module.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "smart_replenishment_module.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Item": {
		"on_update": "smart_replenishment_module.doc_events.item.on_update"
	},
	"Purchase Order": {
		"on_cancel": "smart_replenishment_module.doc_events.purchase_order.on_cancel"
	},
	"Stock Entry": {
		"on_submit": "smart_replenishment_module.doc_events.stock_entry.on_submit"
	},
	"Delivery Note": {
		"on_submit": "smart_replenishment_module.doc_events.delivery_note.on_submit"
	},
	"Sales Invoice": {
		"on_submit": "smart_replenishment_module.doc_events.sales_invoice.on_submit"
	}
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": [
		"smart_replenishment_module.scheduler_events.scheduled_tasks.scheduled_update_reorder_points",
		"smart_replenishment_module.scheduler_events.scheduled_tasks.scheduled_generate_recommendations"
	]
}

# Fixtures
# ---------------

fixtures = [
	# Extract workflow for the Replenishment Recommendation Doctype
	{
		"dt": "Workflow",
		"filters": [
			["name", "=", "Replenishment Recommendation Workflow"]
		]
	},
	# Extract workspace for the Smart Replenishment Module
	{
		"dt": "Workspace",
		"filters": [
			["name", "=", "Smart Replenishment Module"]
		]
	}
]	

# Testing
# -------

# before_tests = "smart_replenishment_module.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "smart_replenishment_module.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "smart_replenishment_module.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["smart_replenishment_module.utils.before_request"]
# after_request = ["smart_replenishment_module.utils.after_request"]

# Job Events
# ----------
# before_job = ["smart_replenishment_module.utils.before_job"]
# after_job = ["smart_replenishment_module.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"smart_replenishment_module.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

