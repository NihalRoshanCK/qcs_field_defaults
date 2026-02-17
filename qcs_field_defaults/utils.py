# Copyright (c) 2026, QCS and contributors
# For license information, please see license.txt

import frappe


def _get_resolved_defaults_by_link_doctype(user=None):
	"""Return resolved defaults keyed by Link options DocType for the given user.

	Role-based rules are applied first (lower priority), then user-specific
	rules override them. Each doctype bucket supports:
	- default: applies to any Link field with matching options doctype
	- fields: applies only to specific fieldname (higher specificity)
	"""
	if not user:
		user = frappe.session.user
	user_roles = frappe.get_roles(user)

	rules = frappe.get_all(
		"Field Default",
		filters={"enabled": 1},
		fields=[
			"reference_doctype",
			"apply_to_all_fields",
			"target_doctype",
			"default_value",
			"user",
			"role",
		],
	)

	defaults_by_link_doctype = {}

	def _ensure_bucket(link_doctype):
		defaults_by_link_doctype.setdefault(link_doctype, {"default": None, "doctypes": {}})
		return defaults_by_link_doctype[link_doctype]

	def _apply_rule(bucket, rule, allow_override):
		if rule.apply_to_all_fields:
			if allow_override or bucket["default"] is None:
				bucket["default"] = rule.default_value
			return

		if rule.target_doctype and (allow_override or rule.target_doctype not in bucket["doctypes"]):
			bucket["doctypes"][rule.target_doctype] = rule.default_value

	# Role-based first (lower priority)
	for rule in rules:
		link_doctype = rule.reference_doctype
		if not link_doctype or not rule.default_value:
			continue
		if rule.role and rule.role in user_roles and not rule.user:
			bucket = _ensure_bucket(link_doctype)
			_apply_rule(bucket, rule, allow_override=False)

	# User-specific overrides
	for rule in rules:
		link_doctype = rule.reference_doctype
		if not link_doctype or not rule.default_value:
			continue
		if rule.user == user:
			bucket = _ensure_bucket(link_doctype)
			_apply_rule(bucket, rule, allow_override=True)

	return defaults_by_link_doctype


def _get_default_value_for_field(defaults_by_link_doctype, link_doctype, fieldname, parent_doctype=None):
	"""Resolve the default value for a specific Link field."""
	bucket = defaults_by_link_doctype.get(link_doctype) or {}
	if parent_doctype and parent_doctype in (bucket.get("doctypes") or {}):
		return bucket["doctypes"][parent_doctype]
	return bucket.get("default")


def get_field_defaults_for_doctype(doctype, user=None):
	"""Get defaults for a specific doctype, based on Link field options DocType.

	Returns dict: {
		"parent": {fieldname: default_value},
		"children": {child_doctype: {fieldname: default_value}}
	}
	"""
	defaults_by_link_doctype = _get_resolved_defaults_by_link_doctype(user=user)
	if not defaults_by_link_doctype:
		return {"parent": {}, "children": {}}

	parent_defaults = {}
	child_defaults = {}

	parent_meta = frappe.get_meta(doctype)
	for df in parent_meta.fields:
		if df.fieldtype == "Link" and df.options in defaults_by_link_doctype:
			value = _get_default_value_for_field(
				defaults_by_link_doctype, df.options, df.fieldname, doctype
			)
			if value is not None:
				parent_defaults[df.fieldname] = value

	for df in parent_meta.fields:
		if df.fieldtype != "Table" or not df.options:
			continue
		child_dt = df.options
		child_meta = frappe.get_meta(child_dt)
		for child_df in child_meta.fields:
			if child_df.fieldtype == "Link" and child_df.options in defaults_by_link_doctype:
				value = _get_default_value_for_field(
					defaults_by_link_doctype, child_df.options, child_df.fieldname, child_dt
				)
				if value is not None:
					child_defaults.setdefault(child_dt, {})
					child_defaults[child_dt][child_df.fieldname] = value

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
	defaults_by_link_doctype = _get_resolved_defaults_by_link_doctype(user=user)
	if not defaults_by_link_doctype:
		return {}

	result = {}
	link_doctypes = list(defaults_by_link_doctype.keys())
	link_fields = frappe.get_all(
		"DocField",
		filters={"fieldtype": "Link", "options": ["in", link_doctypes]},
		fields=["parent", "fieldname", "options"],
	)
	if not link_fields:
		return {}

	parent_doctypes = list({df.parent for df in link_fields})
	doctype_rows = frappe.get_all("DocType", filters={"name": ["in", parent_doctypes]}, fields=["name", "istable"])
	child_doctypes = {d.name for d in doctype_rows if d.istable}

	child_table_links = []
	if child_doctypes:
		child_table_links = frappe.get_all(
			"DocField",
			filters={"fieldtype": "Table", "options": ["in", list(child_doctypes)]},
			fields=["parent", "options"],
		)

	child_to_parents = {}
	for row in child_table_links:
		child_to_parents.setdefault(row.options, set()).add(row.parent)

	for df in link_fields:
		default_value = _get_default_value_for_field(
			defaults_by_link_doctype, df.options, df.fieldname, df.parent
		)
		if default_value is None:
			continue

		if df.parent in child_doctypes:
			for parent_dt in child_to_parents.get(df.parent, set()):
				result.setdefault(parent_dt, {"parent": {}, "children": {}})
				result[parent_dt]["children"].setdefault(df.parent, {})
				result[parent_dt]["children"][df.parent][df.fieldname] = default_value
		else:
			result.setdefault(df.parent, {"parent": {}, "children": {}})
			result[df.parent]["parent"][df.fieldname] = default_value

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
	bootinfo.field_defaults_by_link_doctype = _get_resolved_defaults_by_link_doctype()
