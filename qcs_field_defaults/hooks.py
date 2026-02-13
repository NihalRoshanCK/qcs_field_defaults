app_name = "qcs_field_defaults"
app_title = "Qcs Field Defaults"
app_publisher = "QCS"
app_description = "Tool to set defaults on fields"
app_email = "info@quarkcs.com"
app_license = "mit"

required_apps = ["frappe"]

app_include_js = "/assets/qcs_field_defaults/js/qcs_field_defaults.js"

extend_bootinfo = "qcs_field_defaults.utils.extend_bootinfo"

doc_events = {
	"*": {
		"before_insert": "qcs_field_defaults.utils.apply_field_defaults",
	}
}
