# Copyright (c) 2025, DAS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_months, now_datetime
from frappe import _
import traceback

class DataTrimmerSettings(Document):
    pass

@frappe.whitelist()
def run_data_trimmer(simulate=False, enqueue_per_doctype=True):
    #Cek Jika Data Trim Di Disable Untuk Semua Doc
    if frappe.db.get_single_value("Data Trimmer Settings", "disabled"):
        print("Trimming disabled")
        return

    #Ambil Active Rule Doc Yang Akan Di trim
    rules = frappe.get_all(
        "Data Trimmer",
        filters={"disabled": 0},
        fields=["name", "document_type"]
    )

    if not rules:
        print("No active trimming rules found.")
        return

    for rule_info in rules:
        doctype_name = rule_info.document_type
        #Enqueue per Active Doctype Biar Di Pecah Per Doctype Tidak Sekaligus
        if enqueue_per_doctype:
            frappe.enqueue(
                "data_trimmer.data_trimmer.doctype.data_trimmer_settings.data_trimmer_settings._run_single_doctype_trim",
                queue="long",
                job_name=f"Trim {doctype_name}",
                rule_name=rule_info.name,
                simulate=simulate,
            )
            print(f"Enqueued trimming for {doctype_name}")
        else:
            _run_single_doctype_trim(rule_name=rule_info.name, simulate=simulate)


@frappe.whitelist()
def _run_single_doctype_trim(rule_name, simulate=False):
    try:
        rule_doc = frappe.get_doc("Data Trimmer", rule_name)
        doctype_name = rule_doc.document_type
        print(f"Running Data Trim for {doctype_name} ===")
        move_data_to_archive(rule_doc, simulate)
    except Exception:
        frappe.log_error(traceback.format_exc(), f"Trim failed: {rule_name}")
        print(f"Error while trimming {rule_name}")


def move_data_to_archive(rule, simulate=False):
    #Memindahkan data ke archive
    doctype = rule.document_type
    archive_prefix = rule.archive_prefix or "_Archive"
    main_table = f"tab{doctype}"
    archive_table = f"{main_table}{archive_prefix}"

    #Cari Tanggal Cutoff Dari Retention Period, Jadi Yang Tersisa Hanya Jumlah Bulan di Retention
    cutoff_date = add_months(now_datetime(), -rule.retention_period)
    date_field = rule.date_field or "creation"
    batch_size = rule.batch_size or 500

    #Dilakukan Prepare Tabel Archive Dulu
    frappe.db.commit()
    print(f"Ensuring archive table {archive_table} exists...")
    frappe.db.sql(f"CREATE TABLE IF NOT EXISTS `{archive_table}` LIKE `{main_table}`")
    frappe.db.commit()

    #Bikin Juga Child Tabel Yang Terkait
    meta = frappe.get_meta(doctype)
    child_tables = [
        f"tab{f.options}" for f in meta.fields if f.fieldtype == "Table" and f.options
    ]
    for child_table in child_tables:
        child_archive = f"{child_table}{archive_prefix}"
        print(f"Ensuring archive child table {child_archive} exists...")
        frappe.db.sql(f"CREATE TABLE IF NOT EXISTS `{child_archive}` LIKE `{child_table}`")
    frappe.db.commit()

    total_moved = 0
    batch_index = 0

    while True:
        #Proses pindah ke archive per batch file sampai tidak tersisa row diluar retention period
        rows = frappe.db.sql(
            f"""SELECT name FROM `{main_table}`
                WHERE `{date_field}` < %s
                ORDER BY `{date_field}` ASC
                LIMIT {batch_size}""",
            (cutoff_date,),
            as_dict=True,
        )

        if not rows:
            print("No more records to trim.")
            break

        names = [r["name"] for r in rows]
        batch_index += 1
        print(f"Processing batch #{batch_index}, {len(names)} records from {doctype}...")

        #Simulate ini buat testing jadi ga bener2 mindah
        if simulate:
            print(f"Simulating move: would archive {len(names)} records (first: {names[0]}, last: {names[-1]})")
            total_moved += len(names)
            continue

        try:
            placeholders = ",".join(["%s"] * len(names))

            frappe.db.sql(
                f"INSERT INTO `{archive_table}` SELECT * FROM `{main_table}` WHERE name IN ({placeholders})",
                tuple(names),
            )

            for child_table in child_tables:
                child_archive = f"{child_table}{archive_prefix}"
                frappe.db.sql(
                    f"INSERT INTO `{child_archive}` SELECT * FROM `{child_table}` WHERE parent IN ({placeholders})",
                    tuple(names),
                )
                frappe.db.sql(
                    f"DELETE FROM `{child_table}` WHERE parent IN ({placeholders})",
                    tuple(names),
                )

            frappe.db.sql(
                f"DELETE FROM `{main_table}` WHERE name IN ({placeholders})",
                tuple(names),
            )

            frappe.db.commit()
            total_moved += len(names)

            #Log Yang Pindah Di Simpan Di Doctype Batch Trim Log
            frappe.get_doc({
                "doctype": "Batch Trim Log",
                "document_type": doctype,
                "first_record": names[0],
                "last_record": names[-1],
                "record_count": len(names),
                "trimmed_by": frappe.session.user or "System",
                "trimmed_on": now_datetime(),
            }).insert(ignore_permissions=True)
            frappe.db.commit()

        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(str(e), f"Trim failed on {doctype}")
            print(f"Error in batch #{batch_index}: {e}")
            break

    print(f"Trimming complete for {doctype}. Total moved: {total_moved}")


@frappe.whitelist()
def enqueue_trim_job():
    #Enqueue untuk di panggil di tombol start triming
    frappe.enqueue(
        "data_trimmer.data_trimmer.doctype.data_trimmer_settings.data_trimmer_settings.run_data_trimmer",
        queue="long",
        job_name="Data Trimmer Background Job"
    )
    frappe.msgprint("Data trimming job has been queued.")
