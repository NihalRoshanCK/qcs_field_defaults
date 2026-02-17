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
| **DocType** | The Link target DocType (for example `Warehouse`, `Segment`, `Cost Center`) |
| **Apply To All Fields** | If enabled, apply to all Link fields with matching `DocType` options |
| **Target DocType** | Required only when `Apply To All Fields` is disabled; applies to all matching Link fields in that DocType |
| **Default Value** | Record to use as default wherever a Link field has this DocType in its `options` |
| **User** | Optional. Assign this default to a specific user (higher priority) |
| **Role** | Optional. Assign this default to all users with this role (lower priority) |
| **Enabled** | Toggle the rule on/off |

At least one of **User** or **Role** must be set.

#### Priority Resolution

When multiple rules match the same field:

1. **User-specific** rules always win (exact match on current user)
2. **Role-based** rules are the fallback (first match wins if multiple roles apply)
3. **Target DocType** (if set) is more specific than a DocType-wide rule

#### Client-Side (Form UI)

On login, all applicable Field Default rules are loaded into `frappe.boot.field_defaults` via `extend_bootinfo`. When a user opens a new form:

- **Parent fields**: If a Link field points to a configured DocType, its default is applied
- **Child table fields**: Same behavior for Link fields in child rows
- Fields that already have a value are **never overwritten** (safe for documents created from other documents like SO from Quotation)

#### Server-Side (API / Programmatic)

A `before_insert` doc_event hook applies defaults when documents are created via the API (`frappe.get_doc({...}).insert()`). Same priority rules and empty-field-only logic apply.

### Examples

**Global Link default by DocType:**
- DocType: Warehouse, Default Value: Stores - GA, Role: Sales User
- Result: Every Sales User gets `Stores - GA` in any empty Link field whose options DocType is `Warehouse`

**User override:**
- Role rule: DocType `Warehouse` -> `Stores - GA` for Sales User role
- User rule: DocType `Warehouse` -> `Showroom D1 - GAASP` for john@example.com
- Result: John gets `Showroom D1 - GAASP`, everyone else with Sales User role gets `Stores - GA`

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
