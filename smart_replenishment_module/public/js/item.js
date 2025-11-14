// Auto-populate default values when adding new Item Reorder row
// Only populates if checkboxes are enabled in Replenishment Settings
frappe.ui.form.on("Item Reorder", {
	reorder_levels_add: function(frm, cdt, cdn) {
		// Initialize warehouse_reorder_level with default value (100 units)
		// frappe.model.set_value(cdt, cdn, 'warehouse_reorder_level', 100);
		
		// Fetch settings to check if auto-population is enabled
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Replenishment Settings',
				name: 'Replenishment Settings'
			},
			callback: function(r) {
				if (r.message) {
					const settings = r.message;
					
					// Auto-fill safety stock days if enabled
					if (settings.enable_safety_stock_days == 1 && settings.default_safety_stock_days) {
						frappe.model.set_value(cdt, cdn, 'safety_stock_days', settings.default_safety_stock_days);
					}
					
					// Auto-fill supplier lead time days if enabled
					if (settings.enable_supplier_lead_time_days == 1 && settings.default_supplier_lead_time_days) {
						frappe.model.set_value(cdt, cdn, 'supplier_lead_time_days', settings.default_supplier_lead_time_days);
					}
				}
			}
		});
	},
	warehouse_reorder_level: function(frm, cdt, cdn) {
		// Handle warehouse_reorder_level changes (triggered by system auto-calculation or manual update)
		let row = locals[cdt][cdn];
		
		console.log(`[REORDER DEBUG] warehouse_reorder_level changed for ${row.parent} in ${row.warehouse}: ${row.warehouse_reorder_level}`);
		
		// Trigger recommendation regeneration if reorder level changed
		frappe.call({
			method: 'smart_replenishment_module.api.recommendation_generator.regenerate_recommendations_for_item',
			args: {
				item_code: row.parent,
				warehouse: row.warehouse
			},
			callback: function(r) {
				if (r.message) {
					console.log(`[REORDER DEBUG] Recommendations regenerated: ${r.message.created_count} created, ${r.message.skipped_count} skipped`);
					
					frappe.msgprint({
						title: __('Reorder Point Updated'),
						indicator: 'green',
						message: __(`Reorder point updated to ${row.warehouse_reorder_level} for ${row.parent}. 
							<br>Recommendations status: ${r.message.created_count} created, ${r.message.skipped_count} skipped.`)
					});
				}
			},
			error: function(err) {
				console.log('[REORDER DEBUG] Could not auto-regenerate recommendations', err);
			}
		});
	}
});
