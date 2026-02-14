# Copyright (c) 2026, QCS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PermLevelRule(Document):
	def validate(self):
		self.validate_fields_exist()
		self.populate_field_metadata()
		self._capture_old_fields()

	def on_update(self):
		self.sync_property_setters()

	def on_trash(self):
		self.remove_all_property_setters()

	def validate_fields_exist(self):
		"""Ensure every field in the child table exists on its source doctype."""
		if not self.reference_doctype:
			return

		meta_cache = {}
		for row in self.fields:
			dt = row.source_doctype or self.reference_doctype
			if dt not in meta_cache:
				meta_cache[dt] = frappe.get_meta(dt)
			if not meta_cache[dt].has_field(row.fieldname):
				frappe.throw(
					_("Field '{0}' does not exist on {1}").format(row.fieldname, dt)
				)

	def populate_field_metadata(self):
		"""Auto-fill label and fieldtype from doctype metadata."""
		if not self.reference_doctype:
			return

		meta_cache = {}
		for row in self.fields:
			dt = row.source_doctype or self.reference_doctype
			if dt not in meta_cache:
				meta_cache[dt] = frappe.get_meta(dt)
			df = meta_cache[dt].get_field(row.fieldname)
			if df:
				row.label = df.label
				row.fieldtype = df.fieldtype

	def _capture_old_fields(self):
		"""Capture previous set of (source_doctype, fieldname) from DB before save."""
		self._old_fields = set()
		if not self.is_new():
			old_rows = frappe.get_all(
				"Perm Level Rule Field",
				filters={"parent": self.name, "parenttype": self.doctype},
				fields=["source_doctype", "fieldname"],
			)
			self._old_fields = {(r.source_doctype, r.fieldname) for r in old_rows}

	def sync_property_setters(self):
		"""Create/update Property Setters for current fields, remove stale ones."""
		current_fields = {(row.source_doctype, row.fieldname) for row in self.fields}

		for row in self.fields:
			dt = row.source_doctype or self.reference_doctype
			frappe.make_property_setter(
				{
					"doctype": dt,
					"fieldname": row.fieldname,
					"property": "permlevel",
					"value": str(self.perm_level),
					"property_type": "Int",
				},
				is_system_generated=False,
			)

		# Reset perm_level for fields that were removed from this rule
		removed = getattr(self, "_old_fields", set()) - current_fields
		for source_dt, fieldname in removed:
			self._delete_property_setter(source_dt, fieldname)

	def remove_all_property_setters(self):
		"""Remove all Property Setters created by this rule."""
		for row in self.fields:
			dt = row.source_doctype or self.reference_doctype
			self._delete_property_setter(dt, row.fieldname)

	def _delete_property_setter(self, doctype, fieldname):
		"""Delete the permlevel Property Setter for a specific field on a doctype."""
		ps_name = frappe.db.get_value(
			"Property Setter",
			{
				"doc_type": doctype,
				"field_name": fieldname,
				"property": "permlevel",
			},
		)
		if ps_name:
			frappe.delete_doc("Property Setter", ps_name, ignore_permissions=True)
