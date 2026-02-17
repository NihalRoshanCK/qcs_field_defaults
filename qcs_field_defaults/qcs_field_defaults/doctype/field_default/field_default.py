# Copyright (c) 2026, QCS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class FieldDefault(Document):
	def validate(self):
		self.validate_reference_doctype()
		self.validate_target_scope()
		self.validate_default_value_exists()
		self.validate_user_or_role()

	def validate_reference_doctype(self):
		if not self.reference_doctype:
			frappe.throw(_("Please select a DocType"))

	def validate_default_value_exists(self):
		if not self.default_value:
			return
		if not frappe.db.exists(self.reference_doctype, self.default_value):
			frappe.throw(
				_("Value '{0}' does not exist in DocType {1}").format(
					self.default_value, self.reference_doctype
				)
			)

	def validate_user_or_role(self):
		if not self.user and not self.role:
			frappe.throw(_("Please set either User or Role"))

	def validate_target_scope(self):
		if self.apply_to_all_fields:
			self.target_doctype = None
			self.target_fieldname = None
			return

		if not self.target_doctype:
			frappe.throw(_("Please select Target DocType"))

		self.target_fieldname = None
