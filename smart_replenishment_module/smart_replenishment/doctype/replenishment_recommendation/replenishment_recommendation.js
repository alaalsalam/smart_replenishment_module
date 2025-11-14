// Copyright (c) 2024, Zeiad Madboly and Contributors
// License: MIT

frappe.ui.form.on('Replenishment Recommendation', {
	refresh: function(frm) {
		// Show Create PO button only if approved and no PO exists yet
		// (POs are normally auto-created on submit, but this is for manual creation)
		// Hide button if already in "Ordered" state (PO already created)
		if (frm.doc.status === 'Approved' && !frm.doc.purchase_order) {
			frm.add_custom_button(__('Create Purchase Order'), function() {
				create_purchase_order(frm);
			}, __('Actions'));
		}

		// Recalculate button - useful for testing or manual updates
		if (frm.doc.item_code && frm.doc.warehouse) {
			frm.add_custom_button(__('Recalculate'), function() {
				recalculate_metrics(frm);
			}, __('Actions'));
		}

		// Update visual indicator showing stock level status
		update_stock_level_indicator(frm);
	},

	item_code: function(frm) {
		// Auto-fill item name and update estimated cost when item is selected
		if (frm.doc.item_code) {
			frappe.db.get_value('Item', frm.doc.item_code, 'item_name', (r) => {
				if (r) {
					frm.set_value('item_name', r.item_name);
					// Update cost if cost not already set
					if (!frm.doc.estimated_cost) {
						update_estimated_cost(frm);
					}
				}
			});
		}
	},

	warehouse: function(frm) {
		// Update current stock when warehouse changes
		if (frm.doc.warehouse && frm.doc.item_code) {
			update_current_stock(frm);
		}
	},

	recommended_order_qty: function(frm) {
		// Recalculate estimated cost when quantity changes
		if (frm.doc.recommended_order_qty && frm.doc.item_code) {
			update_estimated_cost(frm);
		}
	}
});

function create_purchase_order(frm) {
	// Manual PO creation - normally happens automatically on submit
	frappe.confirm(
		__('Create Purchase Order for this recommendation?'),
		function() {
			frappe.call({
				method: 'smart_replenishment_module.api.purchase_order_creator.create_purchase_order_from_recommendation',
				args: {
					recommendation_name: frm.doc.name
				},
				callback: function(r) {
					if (r.message && r.message.purchase_order) {
						frappe.show_alert({
							message: __('Purchase Order {0} created successfully', [r.message.purchase_order]),
							indicator: 'green'
						}, 5);
						frm.reload_doc();
					}
				},
				error: function(r) {
					frappe.msgprint({
						title: __('Error'),
						message: r.message || __('Failed to create Purchase Order'),
						indicator: 'red'
					});
				}
			});
		}
	);
}

function recalculate_metrics(frm) {
	// Recalculate all recommendation fields using updated logic
	if (!frm.doc.item_code || !frm.doc.warehouse) {
		frappe.msgprint(__('Please select Item Code and Warehouse first'));
		return;
	}

	if (!frm.doc.name) {
		frappe.msgprint(__('Please save the document first before recalculating'));
		return;
	}

	// Show loading indicator
	frappe.show_alert({
		message: __('Recalculating recommendation...'),
		indicator: 'blue'
	}, 2);

	frappe.call({
		method: 'smart_replenishment_module.api.recommendation_generator.recalculate_recommendation',
		args: {
			recommendation_name: frm.doc.name
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				// Update all fields with recalculated values
				if (r.message.current_stock_qty !== undefined) {
					frm.set_value('current_stock_qty', r.message.current_stock_qty);
				}
				if (r.message.reorder_point !== undefined) {
					frm.set_value('reorder_point', r.message.reorder_point);
				}
				if (r.message.minimum_stock_level !== undefined) {
					frm.set_value('minimum_stock_level', r.message.minimum_stock_level);
				}
				if (r.message.maximum_stock_level !== undefined) {
					frm.set_value('maximum_stock_level', r.message.maximum_stock_level);
				}
				if (r.message.recommended_order_qty !== undefined) {
					frm.set_value('recommended_order_qty', r.message.recommended_order_qty);
				}
				if (r.message.estimated_cost !== undefined) {
					frm.set_value('estimated_cost', r.message.estimated_cost);
				}
				if (r.message.average_daily_consumption !== undefined) {
					frm.set_value('average_daily_consumption', r.message.average_daily_consumption);
				}
				if (r.message.lead_time_days !== undefined) {
					frm.set_value('lead_time_days', r.message.lead_time_days);
				}
				if (r.message.safety_stock_days !== undefined) {
					frm.set_value('safety_stock_days', r.message.safety_stock_days);
				}

				// Update visual indicator
				update_stock_level_indicator(frm);

				frappe.show_alert({
					message: r.message.message || __('Recommendation recalculated successfully'),
					indicator: 'green'
				}, 5);
			}
		},
		error: function(r) {
			frappe.msgprint({
				title: __('Error'),
				message: r.message || __('Failed to recalculate recommendation'),
				indicator: 'red'
			});
		}
	});
}

function update_current_stock(frm) {
	if (frm.doc.item_code && frm.doc.warehouse) {
		frappe.call({
			method: 'erpnext.stock.utils.get_stock_balance',
			args: {
				item_code: frm.doc.item_code,
				warehouse: frm.doc.warehouse
			},
			callback: function(r) {
				if (r.message !== undefined) {
					frm.set_value('current_stock_qty', r.message || 0);
					update_stock_level_indicator(frm);
				}
			}
		});
	}
}

function update_estimated_cost(frm) {
	if (frm.doc.item_code && frm.doc.recommended_order_qty) {
		// Get last purchase rate from Purchase Order Item history, not Item master
		frappe.call({
			method: 'smart_replenishment_module.api.recommendation_generator.get_item_last_purchase_rate_api',
			args: {
				item_code: frm.doc.item_code
			},
			callback: function(r) {
				// Always calculate estimated_cost, even if rate is 0 (so it shows 0 instead of missing)
				const last_purchase_rate = (r.message && r.message.rate) ? r.message.rate : 0;
				const estimated_cost = last_purchase_rate * frm.doc.recommended_order_qty;
				frm.set_value('estimated_cost', estimated_cost);
			}
		});
	}
}

function update_stock_level_indicator(frm) {
	// Show visual indicator of stock level relative to reorder point
	if (!frm.doc.current_stock_qty && !frm.doc.reorder_point) {
		return;
	}

	const stock_ratio = frm.doc.reorder_point > 0
		? frm.doc.current_stock_qty / frm.doc.reorder_point
		: 0;

	let indicator_color = 'green';
	let indicator_message = __('Stock Level: Adequate');

	// Color coding: red = critical, orange = low, yellow = below reorder point
	if (stock_ratio < 0.5) {
		indicator_color = 'red';
		indicator_message = __('Stock Level: Critical');
	} else if (stock_ratio < 0.8) {
		indicator_color = 'orange';
		indicator_message = __('Stock Level: Low');
	} else if (stock_ratio <= 1) {
		indicator_color = 'yellow';
		indicator_message = __('Stock Level: Below Reorder Point');
	}

	// Auto-update priority based on stock level
	if (stock_ratio < 0.5 && frm.doc.priority !== 'High') {
		frm.set_value('priority', 'High');
	} else if (stock_ratio < 0.8 && frm.doc.priority !== 'Medium' && frm.doc.priority !== 'High') {
		frm.set_value('priority', 'Medium');
	}

	if (frm.doc.current_stock_qty !== undefined) {
		frm.dashboard.add_indicator(
			indicator_message,
			indicator_color
		);
	}
}

