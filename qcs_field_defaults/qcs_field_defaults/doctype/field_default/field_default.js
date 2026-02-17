// Copyright (c) 2026, QCS and contributors
// For license information, please see license.txt

function sync_target_scope_fields(frm) {
	const apply_all = !!frm.doc.apply_to_all_fields;
	if (apply_all && frm.doc.target_doctype) {
		frm.set_value("target_doctype", "");
	}
}

frappe.ui.form.on("Field Default", {
	refresh(frm) {
		sync_target_scope_fields(frm);
	},
	reference_doctype(frm) {
		frm.set_value("default_value", "");
		sync_target_scope_fields(frm);
	},
	apply_to_all_fields(frm) {
		sync_target_scope_fields(frm);
	},
});
