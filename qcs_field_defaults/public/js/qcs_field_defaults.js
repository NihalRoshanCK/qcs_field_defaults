// QCS Field Defaults — Apply configured field defaults on new document creation.
// Reads from frappe.boot.field_defaults (injected by extend_bootinfo).
//
// Structure: { "Sales Order": { parent: {field: val}, children: {"SO Item": {field: val}} } }

(function () {
	function is_empty(value) {
		return value === undefined || value === null || value === "";
	}

	function resolve_default_for_link_field(
		defaults_by_link_doctype,
		link_doctype,
		fieldname,
		parent_doctype
	) {
		let bucket = defaults_by_link_doctype[link_doctype] || {};
		let doctypes = bucket.doctypes || {};
		if (Object.prototype.hasOwnProperty.call(doctypes, parent_doctype)) {
			return doctypes[parent_doctype];
		}
		return bucket.default;
	}

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
	let defaults_by_link_doctype = frappe.boot.field_defaults_by_link_doctype || {};

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

	function apply_query_report_defaults(query_report) {
		if (!query_report || !query_report.filters || !query_report.report_name) return;
		if (query_report._qfd_applied_for_report === query_report.report_name) return;

		let changed = false;
		for (const filter of query_report.filters) {
			const df = filter.df || {};
			if (df.fieldtype !== "Link" || !df.options) continue;
			const default_value = resolve_default_for_link_field(
				defaults_by_link_doctype,
				df.options,
				df.fieldname,
				query_report.doctype
			);
			if (default_value === undefined || default_value === null || default_value === "") continue;
			if (!is_empty(filter.get_value())) continue;

			query_report.set_filter_value(df.fieldname, default_value);
			changed = true;
		}

		query_report._qfd_applied_for_report = query_report.report_name;

		// If we set values, refresh once to apply filtered result.
		if (changed) {
			query_report.refresh();
		}
	}

	// Patch Query Report refresh flow to apply defaults once per report load.
	if (frappe.views && frappe.views.QueryReport && !frappe.views.QueryReport.__qfd_patched) {
		const original_refresh_report = frappe.views.QueryReport.prototype.refresh_report;
		frappe.views.QueryReport.prototype.refresh_report = function (...args) {
			const out = original_refresh_report.apply(this, args);
			apply_query_report_defaults(this);
			return out;
		};
		frappe.views.QueryReport.__qfd_patched = true;
	}
})();
