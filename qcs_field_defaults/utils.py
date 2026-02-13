# Copyright (c) 2026, QCS and contributors
# For license information, please see license.txt

import frappe


def get_field_defaults_for_doctype(doctype, user=None):
	"""Get applicable defaults for user on this doctype.

	Returns dict: {
		"parent": {fieldname: default_value},
		"children": {child_doctype: {fieldname: default_value}}
	}
	"""
	if not user:
		user = frappe.session.user
	user_roles = frappe.get_roles(user)

	rules = frappe.get_all(
		"Field Default",
		filters={"reference_doctype": doctype, "enabled": 1},
		fields=["fieldname", "default_value", "user", "role", "child_doctype"],
	)

	parent_defaults = {}
	child_defaults = {}

	# Pass 1: role-based (lower priority)
	for rule in rules:
		if rule.role and rule.role in user_roles and not rule.user:
			if rule.child_doctype:
				child_defaults.setdefault(rule.child_doctype, {})
				child_defaults[rule.child_doctype].setdefault(rule.fieldname, rule.default_value)
			else:
				parent_defaults.setdefault(rule.fieldname, rule.default_value)

	# Pass 2: user-specific (overrides role-based)
	for rule in rules:
		if rule.user == user:
			if rule.child_doctype:
				child_defaults.setdefault(rule.child_doctype, {})
				child_defaults[rule.child_doctype][rule.fieldname] = rule.default_value
			else:
				parent_defaults[rule.fieldname] = rule.default_value

	return {"parent": parent_defaults, "children": child_defaults}


def get_all_field_defaults_for_user(user=None):
	"""Get all defaults grouped by doctype for boot data.

	Returns dict: {
		doctype: {
			"parent": {fieldname: default_value},
			"children": {child_doctype: {fieldname: default_value}}
		}
	}
	"""
	if not user:
		user = frappe.session.user
	user_roles = frappe.get_roles(user)

	rules = frappe.get_all(
		"Field Default",
		filters={"enabled": 1},
		fields=["reference_doctype", "child_doctype", "fieldname", "default_value", "user", "role"],
	)

	result = {}

	# Role-based first (lower priority)
	for rule in rules:
		if rule.role and rule.role in user_roles and not rule.user:
			dt = rule.reference_doctype
			result.setdefault(dt, {"parent": {}, "children": {}})
			if rule.child_doctype:
				result[dt]["children"].setdefault(rule.child_doctype, {})
				result[dt]["children"][rule.child_doctype].setdefault(rule.fieldname, rule.default_value)
			else:
				result[dt]["parent"].setdefault(rule.fieldname, rule.default_value)

	# User-specific overrides
	for rule in rules:
		if rule.user == user:
			dt = rule.reference_doctype
			result.setdefault(dt, {"parent": {}, "children": {}})
			if rule.child_doctype:
				result[dt]["children"].setdefault(rule.child_doctype, {})
				result[dt]["children"][rule.child_doctype][rule.fieldname] = rule.default_value
			else:
				result[dt]["parent"][rule.fieldname] = rule.default_value

	return result


def apply_field_defaults(doc, method=None):
	"""before_insert hook: set defaults on new documents."""
	if frappe.flags.in_migrate or frappe.flags.in_install:
		return

	defaults = get_field_defaults_for_doctype(doc.doctype)

	# Apply parent field defaults
	for fieldname, value in defaults["parent"].items():
		if doc.meta.has_field(fieldname) and not doc.get(fieldname):
			doc.set(fieldname, value)

	# Apply child table field defaults
	for child_doctype, child_fields in defaults["children"].items():
		child_meta = frappe.get_meta(child_doctype)
		for row in doc.get_all_children():
			if row.doctype == child_doctype:
				for fieldname, value in child_fields.items():
					if child_meta.has_field(fieldname) and not row.get(fieldname):
						row.set(fieldname, value)


def extend_bootinfo(bootinfo):
	"""Inject field defaults into boot data for client-side."""
	bootinfo.field_defaults = get_all_field_defaults_for_user()
