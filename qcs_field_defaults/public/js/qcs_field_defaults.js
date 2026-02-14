// QCS Field Defaults — Apply configured field defaults on new document creation.
// Reads from frappe.boot.field_defaults (injected by extend_bootinfo).
//
// Structure: { "Sales Order": { parent: {field: val}, children: {"SO Item": {field: val}} } }

(function () {
	function apply_parent_defaults(frm, defaults) {
		let parent = defaults.parent || {};
		for (const [fieldname, value] of Object.entries(parent)) {
			if (frm.fields_dict[fieldname] && !frm.doc[fieldname]) {
				frm.set_value(fieldname, value);
			}
		}
	}

	function apply_child_defaults(frm, row, defaults) {
		let child_defaults = (defaults.children || {})[row.doctype];
		if (!child_defaults) return;

		for (const [fieldname, value] of Object.entries(child_defaults)) {
			if (!row[fieldname]) {
				frappe.model.set_value(row.doctype, row.name, fieldname, value);
			}
		}
	}

	// Register handlers for every doctype that has defaults configured
	let all_defaults = frappe.boot.field_defaults || {};

	for (const [dt, defaults] of Object.entries(all_defaults)) {
		// Parent field defaults — on form load
		frappe.ui.form.on(dt, {
			onload(frm) {
				if (!frm.is_new()) return;
				apply_parent_defaults(frm, defaults);
			},
		});

		// Child table defaults — on row add
		let child_doctypes = Object.keys(defaults.children || {});
		for (const child_dt of child_doctypes) {
			frappe.ui.form.on(child_dt, {
				[child_dt + "_add"](frm, cdt, cdn) {
					let row = locals[cdt][cdn];
					apply_child_defaults(frm, row, defaults);
				},
			});
		}
	}
})();
