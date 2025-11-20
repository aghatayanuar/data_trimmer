// Copyright (c) 2025, DAS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Data Trimmer Settings", {
    refresh(frm) {
        frm.add_custom_button("Start Trimming", () => {
            frappe.call({
                method: "data_trimmer.data_trimmer.doctype.data_trimmer_settings.data_trimmer_settings.enqueue_trim_job",
            });
        }).addClass("btn-primary");
    }
});






