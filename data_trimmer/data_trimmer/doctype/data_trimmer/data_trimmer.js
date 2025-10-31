// Copyright (c) 2025, DAS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Data Trimmer", {
    document_type(frm) {
		set_date_field_value(frm);
    },
	refresh: function(frm) {
		set_date_field_value(frm);
		
		frm.add_custom_button("Start Trimming", () => {
            frappe.call({
                method: "data_trimmer.data_trimmer.doctype.data_trimmer_settings.data_trimmer_settings.enqueue_trim_job",
            });
        }).addClass("btn-primary");
	}
});

function set_date_field_value(frm){
	if (!frm.doc.document_type) return;

	frappe.model.with_doctype(frm.doc.document_type, () => {
		const fields = frappe.meta.get_docfields(frm.doc.document_type);

		const date_fields = fields
			.filter(df => ["Date", "Datetime"].includes(df.fieldtype))
			.map(df => df.fieldname);

		if (!date_fields.includes("creation")) date_fields.push("creation");
		if (!date_fields.includes("modified")) date_fields.push("modified");

		const df = frm.fields_dict.date_field;
		if (df) {
			df.df.options = date_fields.join("\n");
			df.refresh();
		}

		if (!frm.doc.date_field && date_fields.includes("creation")) {
			frm.set_value("date_field", "creation");
		}
	});
}