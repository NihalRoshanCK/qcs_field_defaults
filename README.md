## QCS Field Defaults

A standalone Frappe app that provides configurable default field values for documents. It works independently of Frappe's built-in User Permission defaults, making it ideal for sites that use `ignore_user_permissions` Property Setters (which disable Frappe's native default auto-filling).

### The Problem

Frappe's `ignore_user_permissions` flag on a DocField disables **both** permission validation **and** default value auto-filling. Sites that need `ignore_user_permissions` to avoid permission errors on Link fields (e.g. Warehouse, Segment, Division) lose the ability to auto-fill defaults from User Permissions.

This app solves that by providing an independent default-filling mechanism via a configurable **Field Default** DocType.

### How It Works

#### Field Default DocType

Each **Field Default** record defines one default rule:

| Field | Description |
|-------|-------------|
| **DocType** | The target parent doctype (e.g. "Sales Order") |
| **Child DocType** | Optional. A child table of the parent (e.g. "Sales Order Item"). Leave blank for parent fields |
| **Field** | Dynamically populated dropdown showing available fields from the selected doctype |
| **Default Value** | The value to set. Shows autocomplete for Link fields |
| **User** | Optional. Assign this default to a specific user (higher priority) |
| **Role** | Optional. Assign this default to all users with this role (lower priority) |
| **Enabled** | Toggle the rule on/off |

At least one of **User** or **Role** must be set.

#### Priority Resolution

When multiple rules match the same field:

1. **User-specific** rules always win (exact match on current user)
2. **Role-based** rules are the fallback (first match wins if multiple roles apply)

#### Client-Side (Form UI)

On login, all applicable Field Default rules are loaded into `frappe.boot.field_defaults` via `extend_bootinfo`. When a user opens a new form:

- **Parent fields**: Defaults are applied on `onload` (only for new documents)
- **Child table fields**: Defaults are applied when a new row is added to the child table
- Fields that already have a value are **never overwritten** (safe for documents created from other documents like SO from Quotation)

#### Server-Side (API / Programmatic)

A `before_insert` doc_event hook applies defaults when documents are created via the API (`frappe.get_doc({...}).insert()`). Same priority rules and empty-field-only logic apply.

### Examples

**Parent field default:**
- DocType: Sales Order, Field: segment, Default Value: Passenger Cars, Role: Sales User
- Result: Every Sales User gets "Passenger Cars" pre-filled in the Segment field on new Sales Orders

**Child table field default:**
- DocType: Sales Order, Child DocType: Sales Order Item, Field: warehouse, Default Value: Stores - GA, Role: Sales User
- Result: Every new row added to SO Items gets "Stores - GA" as the warehouse

**User override:**
- Role rule: segment = "Passenger Cars" for Sales User role
- User rule: segment = "Fleet" for john@example.com
- Result: John gets "Fleet", everyone else with Sales User role gets "Passenger Cars"

### Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/QuarkCyberSystems/qcs_field_defaults.git --branch develop
bench --site your-site install-app qcs_field_defaults
bench build --app qcs_field_defaults
bench migrate
```

### License

MIT
