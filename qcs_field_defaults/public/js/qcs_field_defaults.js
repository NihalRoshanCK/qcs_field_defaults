// QCS Field Defaults — Apply configured field defaults on new document creation.
// Reads from frappe.boot.field_defaults and frappe.boot.field_defaults_by_link_doctype.

(function () {
	function is_empty(value) {
		return value === undefined || value === null || value === "";
	}

	function resolve_default_for_link_field(defaults_by_link_doctype, link_doctype, parent_doctype) {
		const bucket = defaults_by_link_doctype[link_doctype] || {};
		const doctypes = bucket.doctypes || {};
		if (Object.prototype.hasOwnProperty.call(doctypes, parent_doctype)) {
			return doctypes[parent_doctype];
		}
		return bucket.default;
	}

	function apply_parent_defaults(frm, defaults) {
		const parent = defaults.parent || {};
		for (const [fieldname, value] of Object.entries(parent)) {
			if (!frm.fields_dict[fieldname]) continue;
			if (!is_empty(frm.doc[fieldname])) continue;
			frm.set_value(fieldname, value);
		}
	}

	function apply_child_defaults_on_row(frm, row, defaults_by_link_doctype) {
		const child_meta = frappe.get_meta(row.doctype);
		if (!child_meta || !child_meta.fields) return;

		for (const df of child_meta.fields) {
			if (df.fieldtype !== "Link" || !df.options) continue;
			const value = resolve_default_for_link_field(
				defaults_by_link_doctype,
				df.options,
				frm.doctype
			);
			if (is_empty(value)) continue;
			if (row[df.fieldname] === value) continue;
			frappe.model.set_value(row.doctype, row.name, df.fieldname, value);
		}
	}

	function get_target_child_table_fieldnames(frm, defaults_by_link_doctype) {
		const out = [];
		for (const table_df of frm.meta.fields || []) {
			if (table_df.fieldtype !== "Table" || !table_df.options) continue;
			const child_meta = frappe.get_meta(table_df.options);
			if (!child_meta || !child_meta.fields) continue;
			const has_match = child_meta.fields.some(
				(df) => df.fieldtype === "Link" && !!defaults_by_link_doctype[df.options]
			);
			if (has_match) out.push(table_df.fieldname);
		}
		return out;
	}

	function apply_child_defaults_on_form(frm, defaults_by_link_doctype) {
		const table_fields = get_target_child_table_fieldnames(frm, defaults_by_link_doctype);
		for (const table_field of table_fields) {
			for (const row of frm.doc[table_field] || []) {
				apply_child_defaults_on_row(frm, row, defaults_by_link_doctype);
			}
		}
	}

	function apply_child_defaults_late(frm, defaults_by_link_doctype) {
		const table_fields = get_target_child_table_fieldnames(frm, defaults_by_link_doctype);
		setTimeout(() => {
			if (!frm.is_new()) return;
			apply_child_defaults_on_form(frm, defaults_by_link_doctype);
			for (const table_field of table_fields) frm.refresh_field(table_field);
		}, 250);

		if (typeof frappe.after_ajax === "function") {
			frappe.after_ajax(() => {
				if (!frm.is_new()) return;
				apply_child_defaults_on_form(frm, defaults_by_link_doctype);
				for (const table_field of table_fields) frm.refresh_field(table_field);
			});
		}
	}

	function register_form_handlers(all_defaults, defaults_by_link_doctype) {
		for (const [dt, defaults] of Object.entries(all_defaults)) {
			frappe.ui.form.on(dt, {
				onload(frm) {
					if (!frm.is_new()) return;
					apply_parent_defaults(frm, defaults);
					apply_child_defaults_on_form(frm, defaults_by_link_doctype);
				},
				refresh(frm) {
					if (!frm.is_new()) return;
					apply_parent_defaults(frm, defaults);
					apply_child_defaults_on_form(frm, defaults_by_link_doctype);
					apply_child_defaults_late(frm, defaults_by_link_doctype);
				},
			});

			const child_doctypes = Object.keys(defaults.children || {});
			for (const child_dt of child_doctypes) {
				frappe.ui.form.on(child_dt, {
					[`${child_dt}_add`](frm, cdt, cdn) {
						const row = locals[cdt] && locals[cdt][cdn];
						if (!row) return;
						apply_child_defaults_on_row(frm, row, defaults_by_link_doctype);
					},
				});
			}
		}
	}

	function apply_query_report_defaults(query_report, defaults_by_link_doctype) {
		if (!query_report || !query_report.filters || !query_report.report_name) return;
		if (query_report._qfd_applied_for_report === query_report.report_name) return;

		let changed = false;
		for (const filter of query_report.filters) {
			const df = filter.df || {};
			if (df.fieldtype !== "Link" || !df.options) continue;
			const value = resolve_default_for_link_field(
				defaults_by_link_doctype,
				df.options,
				query_report.doctype
			);
			if (is_empty(value) || !is_empty(filter.get_value())) continue;
			query_report.set_filter_value(df.fieldname, value);
			changed = true;
		}

		query_report._qfd_applied_for_report = query_report.report_name;
		if (changed) query_report.refresh();
	}

	function register_query_report_patch(defaults_by_link_doctype) {
		if (!(frappe.views && frappe.views.QueryReport)) return;
		if (frappe.views.QueryReport.__qfd_patched) return;

		const original_refresh_report = frappe.views.QueryReport.prototype.refresh_report;
		frappe.views.QueryReport.prototype.refresh_report = function (...args) {
			const out = original_refresh_report.apply(this, args);
			apply_query_report_defaults(this, defaults_by_link_doctype);
			return out;
		};
		frappe.views.QueryReport.__qfd_patched = true;
	}

	$(document).on("app_ready", function () {
		const all_defaults = frappe.boot.field_defaults || {};
		const defaults_by_link_doctype = frappe.boot.field_defaults_by_link_doctype || {};
		register_form_handlers(all_defaults, defaults_by_link_doctype);
		register_query_report_patch(defaults_by_link_doctype);
	});
})();
