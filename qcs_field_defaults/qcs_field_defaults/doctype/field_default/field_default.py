# Copyright (c) 2026, QCS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FieldDefault(Document):
	def validate(self):
		self.validate_child_doctype()
		self.validate_field_exists()
		self.set_field_doctype()
		self.validate_user_or_role()

	def validate_child_doctype(self):
		"""If child_doctype is set, verify it's a valid child table of the parent."""
		if not self.child_doctype:
			return
		parent_meta = frappe.get_meta(self.reference_doctype)
		valid_children = [df.options for df in parent_meta.fields if df.fieldtype == "Table"]
		if self.child_doctype not in valid_children:
			frappe.throw(
				_("{0} is not a child table of {1}").format(self.child_doctype, self.reference_doctype)
			)

	def validate_field_exists(self):
		target_dt = self.child_doctype or self.reference_doctype
		meta = frappe.get_meta(target_dt)
		if not meta.has_field(self.fieldname):
			frappe.throw(_("Field '{0}' does not exist on {1}").format(self.fieldname, target_dt))

	def set_field_doctype(self):
		target_dt = self.child_doctype or self.reference_doctype
		meta = frappe.get_meta(target_dt)
		df = meta.get_field(self.fieldname)
		if df and df.fieldtype == "Link":
			self.field_doctype = df.options
		else:
			self.field_doctype = None

	def validate_user_or_role(self):
		if not self.user and not self.role:
			frappe.throw(_("Please set either User or Role"))
