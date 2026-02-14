// Copyright (c) 2026, QCS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Perm Level Rule", {
	refresh(frm) {
		add_select_fields_button(frm);
	},

	reference_doctype(frm) {
		frm.clear_table("fields");
		frm.refresh_field("fields");
		add_select_fields_button(frm);
	},
});

function add_select_fields_button(frm) {
	// Remove any previous instance so we don't duplicate
	frm.remove_custom_button(__("Select Fields"));

	if (!frm.doc.reference_doctype) return;

	frm.add_custom_button(__("Select Fields"), () => {
		show_field_selector(frm);
	});
}

function get_data_fields(meta) {
	const layout_types = new Set([
		"Section Break",
		"Column Break",
		"Tab Break",
		"HTML",
		"Fold",
	]);
	return meta.fields.filter((f) => !layout_types.has(f.fieldtype));
}

function show_field_selector(frm) {
	let parent_dt = frm.doc.reference_doctype;

	// Build a set of already-selected keys: "doctype|fieldname"
	let existing = new Set(
		(frm.doc.fields || []).map((r) => `${r.source_doctype}|${r.fieldname}`)
	);

	// Collect all doctypes to show: parent + its child tables
	let doctypes_to_load = [parent_dt];
	let parent_meta = frappe.get_meta(parent_dt);
	if (parent_meta) {
		for (let df of parent_meta.fields) {
			if (df.fieldtype === "Table" && df.options) {
				doctypes_to_load.push(df.options);
			}
		}
	}

	// Ensure all doctype metadata is loaded, then build the dialog
	let promises = doctypes_to_load.map(
		(dt) =>
			new Promise((resolve) => {
				frappe.model.with_doctype(dt, resolve);
			})
	);

	Promise.all(promises).then(() => {
		let dialog_fields = [];
		let all_doctypes_meta = {};

		for (let dt of doctypes_to_load) {
			let meta = frappe.get_meta(dt);
			if (!meta) continue;
			all_doctypes_meta[dt] = meta;

			let data_fields = get_data_fields(meta);
			if (!data_fields.length) continue;

			let options = data_fields.map((f) => ({
				label: `${f.label || f.fieldname} (${f.fieldname}) [${f.fieldtype}]`,
				value: f.fieldname,
				checked: existing.has(`${dt}|${f.fieldname}`),
			}));

			// Section heading
			let heading =
				dt === parent_dt ? parent_dt : `${dt} (child table)`;
			dialog_fields.push({
				fieldtype: "HTML",
				options: `<h5 class="mt-3 mb-2">${heading}</h5>`,
			});

			dialog_fields.push({
				fieldtype: "MultiCheck",
				fieldname: dt,
				options: options,
				columns: 2,
			});
		}

		let d = new frappe.ui.Dialog({
			title: __("Select Fields for {0}", [parent_dt]),
			fields: dialog_fields,
			size: "extra-large",
			primary_action_label: __("Apply"),
			primary_action(values) {
				frm.clear_table("fields");

				for (let dt of doctypes_to_load) {
					let selected = values[dt] || [];
					let meta = all_doctypes_meta[dt];
					if (!meta) continue;

					for (let fieldname of selected) {
						let df = meta.fields.find(
							(f) => f.fieldname === fieldname
						);
						let row = frm.add_child("fields");
						row.source_doctype = dt;
						row.fieldname = fieldname;
						row.label = df?.label || fieldname;
						row.fieldtype = df?.fieldtype || "";
					}
				}

				frm.refresh_field("fields");
				frm.dirty();
				d.hide();
			},
		});
		d.show();
	});
}
