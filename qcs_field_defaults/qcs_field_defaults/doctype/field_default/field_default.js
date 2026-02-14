// Copyright (c) 2026, QCS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Field Default", {
	refresh(frm) {
		// Set child_doctype filter to only show child tables of the parent
		frm.set_query("child_doctype", () => {
			if (!frm.doc.reference_doctype) {
				return { filters: { name: ["in", []] } };
			}
			let meta = frappe.get_meta(frm.doc.reference_doctype);
			let child_doctypes = (meta?.fields || [])
				.filter((f) => f.fieldtype === "Table")
				.map((f) => f.options);
			return { filters: { name: ["in", child_doctypes] } };
		});

		// Populate fieldname options on load (for existing records)
		if (frm.doc.reference_doctype) {
			set_fieldname_options(frm);
		}
	},

	reference_doctype(frm) {
		frm.set_value("child_doctype", "");
		frm.set_value("fieldname", "");
		frm.set_value("default_value", "");
		frm.set_value("field_doctype", "");
		set_fieldname_options(frm);
	},

	child_doctype(frm) {
		frm.set_value("fieldname", "");
		frm.set_value("default_value", "");
		frm.set_value("field_doctype", "");
		set_fieldname_options(frm);
	},

	fieldname(frm) {
		frm.set_value("default_value", "");
		if (!frm.doc.fieldname) {
			frm.set_value("field_doctype", "");
			return;
		}

		// Auto-populate field_doctype for Dynamic Link autocomplete
		let target_dt = frm.doc.child_doctype || frm.doc.reference_doctype;
		if (!target_dt) return;

		frappe.model.with_doctype(target_dt, () => {
			let meta = frappe.get_meta(target_dt);
			let field = (meta?.fields || []).find((f) => f.fieldname === frm.doc.fieldname);
			if (field && field.fieldtype === "Link") {
				frm.set_value("field_doctype", field.options);
			} else {
				frm.set_value("field_doctype", "");
			}
		});
	},
});

function set_fieldname_options(frm) {
	let target_dt = frm.doc.child_doctype || frm.doc.reference_doctype;
	if (!target_dt) {
		frm.set_df_property("fieldname", "options", [""]);
		return;
	}

	frappe.model.with_doctype(target_dt, () => {
		let meta = frappe.get_meta(target_dt);
		if (!meta) return;

		// Show Link and Select fields (the types that commonly need defaults)
		let allowed_types = ["Link", "Select", "Data", "Int", "Check"];
		let options = meta.fields
			.filter(
				(f) => allowed_types.includes(f.fieldtype) && !f.hidden && f.fieldname !== "name"
			)
			.map((f) => ({
				label: `${f.label} (${f.fieldname})`,
				value: f.fieldname,
			}));

		// Build newline-separated options string for Select field
		let options_str = [""].concat(options.map((o) => o.value)).join("\n");
		frm.set_df_property("fieldname", "options", options_str);

		// Refresh to show updated options
		frm.refresh_field("fieldname");
	});
}
