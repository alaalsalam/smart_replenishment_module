// Copyright (c) 2024, Zeiad Madboly and Contributors
// License: MIT

frappe.listview_settings['Replenishment Recommendation'] = {
	add_fields: ['status', 'priority', 'current_stock_qty', 'reorder_point'],
	
	get_indicator: function(doc) {
		// Color-coded status badges for quick visual identification
		const status_colors = {
			'Pending': 'orange',
			'Approved': 'blue',
			'Ordered': 'green',
			'Rejected': 'red'
		};
		return [__(doc.status), status_colors[doc.status] || 'gray', 'status,=,' + doc.status];
	},
	
	formatters: {
		priority: function(value) {
			// Color-code priority values
			const colors = {
				'High': 'red',
				'Medium': 'orange',
				'Low': 'yellow'
			};
			return `<span class="indicator ${colors[value] || 'gray'}">${value}</span>`;
		},
		
		current_stock_qty: function(value, doc) {
			// Show stock quantity with color based on ratio to reorder point
			if (doc.reorder_point && doc.reorder_point > 0) {
				const ratio = value / doc.reorder_point;
				let color = 'green';
				if (ratio < 0.5) color = 'red';      // Critical
				else if (ratio < 0.8) color = 'orange';  // Low
				else if (ratio <= 1) color = 'yellow';     // Below reorder point
				
				return `<span class="indicator ${color}">${value}</span>`;
			}
			return value;
		}
	},
	
	
};

