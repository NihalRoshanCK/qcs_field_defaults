# Copyright (c) 2026, QCS and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from qcs_field_defaults.qcs_field_defaults.doctype.perm_level_rule.perm_level_rule import (
	PermLevelRule,
)


def _make_rule(reference_doctype="Purchase Order", perm_level=1, fields=None):
	"""Create a mock PermLevelRule document."""
	doc = MagicMock(spec=PermLevelRule)
	doc.reference_doctype = reference_doctype
	doc.perm_level = perm_level
	doc.doctype = "Perm Level Rule"
	doc.name = f"{reference_doctype}-Level-{perm_level}"

	mock_fields = []
	for f in fields or []:
		source_dt = f.get("source_doctype", reference_doctype)
		row = frappe._dict(
			source_doctype=source_dt,
			fieldname=f["fieldname"],
			label="",
			fieldtype="",
		)
		mock_fields.append(row)
	doc.fields = mock_fields

	return doc


class TestValidateFieldsExist(FrappeTestCase):
	"""Tests for validate_fields_exist()."""

	@patch("qcs_field_defaults.qcs_field_defaults.doctype.perm_level_rule.perm_level_rule.frappe")
	def test_valid_fields_pass(self, mock_frappe):
		mock_meta = MagicMock()
		mock_meta.has_field.return_value = True
		mock_frappe.get_meta.return_value = mock_meta

		doc = _make_rule(fields=[
			{"fieldname": "grand_total"},
			{"fieldname": "rate", "source_doctype": "Purchase Order Item"},
		])
		PermLevelRule.validate_fields_exist(doc)

		mock_frappe.throw.assert_not_called()

	@patch("qcs_field_defaults.qcs_field_defaults.doctype.perm_level_rule.perm_level_rule.frappe")
	def test_invalid_field_throws(self, mock_frappe):
		mock_meta = MagicMock()
		mock_meta.has_field.side_effect = lambda f: f != "nonexistent"
		mock_frappe.get_meta.return_value = mock_meta
		mock_frappe.throw.side_effect = frappe.ValidationError
		mock_frappe._ = frappe._

		doc = _make_rule(fields=[
			{"fieldname": "grand_total"},
			{"fieldname": "nonexistent"},
		])

		with self.assertRaises(frappe.ValidationError):
			PermLevelRule.validate_fields_exist(doc)

	def test_no_doctype_skips(self):
		doc = _make_rule(fields=[{"fieldname": "rate"}])
		doc.reference_doctype = ""
		PermLevelRule.validate_fields_exist(doc)


class TestPopulateFieldMetadata(FrappeTestCase):
	"""Tests for populate_field_metadata()."""

	@patch("qcs_field_defaults.qcs_field_defaults.doctype.perm_level_rule.perm_level_rule.frappe")
	def test_fills_label_and_fieldtype(self, mock_frappe):
		mock_df = MagicMock()
		mock_df.label = "Rate"
		mock_df.fieldtype = "Currency"

		mock_meta = MagicMock()
		mock_meta.get_field.return_value = mock_df
		mock_frappe.get_meta.return_value = mock_meta

		doc = _make_rule(fields=[{"fieldname": "rate"}])
		PermLevelRule.populate_field_metadata(doc)

		self.assertEqual(doc.fields[0].label, "Rate")
		self.assertEqual(doc.fields[0].fieldtype, "Currency")

	@patch("qcs_field_defaults.qcs_field_defaults.doctype.perm_level_rule.perm_level_rule.frappe")
	def test_uses_source_doctype_for_child_fields(self, mock_frappe):
		"""Child table fields should look up metadata from source_doctype, not reference_doctype."""
		parent_meta = MagicMock()
		child_meta = MagicMock()

		child_df = MagicMock()
		child_df.label = "Rate"
		child_df.fieldtype = "Currency"
		child_meta.get_field.return_value = child_df

		mock_frappe.get_meta.side_effect = lambda dt: {
			"Purchase Order": parent_meta,
			"Purchase Order Item": child_meta,
		}[dt]

		doc = _make_rule(fields=[
			{"fieldname": "rate", "source_doctype": "Purchase Order Item"},
		])
		PermLevelRule.populate_field_metadata(doc)

		self.assertEqual(doc.fields[0].label, "Rate")
		# Verify child_meta was used, not parent_meta
		child_meta.get_field.assert_called_with("rate")
		parent_meta.get_field.assert_not_called()


class TestSyncPropertySetters(FrappeTestCase):
	"""Tests for sync_property_setters()."""

	@patch("qcs_field_defaults.qcs_field_defaults.doctype.perm_level_rule.perm_level_rule.frappe")
	def test_creates_property_setters_for_parent_and_child(self, mock_frappe):
		doc = _make_rule(fields=[
			{"fieldname": "grand_total"},
			{"fieldname": "rate", "source_doctype": "Purchase Order Item"},
		])
		doc._old_fields = set()

		PermLevelRule.sync_property_setters(doc)

		self.assertEqual(mock_frappe.make_property_setter.call_count, 2)

		# First call: parent field
		call1 = mock_frappe.make_property_setter.call_args_list[0][0][0]
		self.assertEqual(call1["doctype"], "Purchase Order")
		self.assertEqual(call1["fieldname"], "grand_total")

		# Second call: child table field
		call2 = mock_frappe.make_property_setter.call_args_list[1][0][0]
		self.assertEqual(call2["doctype"], "Purchase Order Item")
		self.assertEqual(call2["fieldname"], "rate")

	@patch("qcs_field_defaults.qcs_field_defaults.doctype.perm_level_rule.perm_level_rule.frappe")
	def test_removes_stale_property_setters(self, mock_frappe):
		doc = _make_rule(fields=[{"fieldname": "grand_total"}])
		doc._old_fields = {
			("Purchase Order", "grand_total"),
			("Purchase Order Item", "rate"),
		}

		mock_frappe.db.get_value.return_value = "PS-00001"

		PermLevelRule.sync_property_setters(doc)

		# Should delete the PS for the removed child field
		mock_frappe.delete_doc.assert_called_once_with(
			"Property Setter", "PS-00001", ignore_permissions=True
		)

	@patch("qcs_field_defaults.qcs_field_defaults.doctype.perm_level_rule.perm_level_rule.frappe")
	def test_no_deletion_when_no_removals(self, mock_frappe):
		doc = _make_rule(fields=[
			{"fieldname": "grand_total"},
			{"fieldname": "rate", "source_doctype": "Purchase Order Item"},
		])
		doc._old_fields = {
			("Purchase Order", "grand_total"),
			("Purchase Order Item", "rate"),
		}

		PermLevelRule.sync_property_setters(doc)

		mock_frappe.delete_doc.assert_not_called()


class TestRemoveAllPropertySetters(FrappeTestCase):
	"""Tests for remove_all_property_setters() (on trash)."""

	@patch("qcs_field_defaults.qcs_field_defaults.doctype.perm_level_rule.perm_level_rule.frappe")
	def test_deletes_all_on_trash(self, mock_frappe):
		doc = _make_rule(fields=[
			{"fieldname": "grand_total"},
			{"fieldname": "rate", "source_doctype": "Purchase Order Item"},
		])
		mock_frappe.db.get_value.side_effect = ["PS-00001", "PS-00002"]

		PermLevelRule.remove_all_property_setters(doc)

		self.assertEqual(mock_frappe.delete_doc.call_count, 2)

	@patch("qcs_field_defaults.qcs_field_defaults.doctype.perm_level_rule.perm_level_rule.frappe")
	def test_skips_missing_property_setters(self, mock_frappe):
		doc = _make_rule(fields=[{"fieldname": "grand_total"}])
		mock_frappe.db.get_value.return_value = None

		PermLevelRule.remove_all_property_setters(doc)

		mock_frappe.delete_doc.assert_not_called()
