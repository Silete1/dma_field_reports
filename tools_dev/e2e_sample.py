"""End-to-end run on the real EORE_Sep26 sample, inside `odoo-bin shell` (env is given).

    odoo-bin shell -c odoo19_dma_field_reports.conf -d dma_fr_dev < tools_dev/e2e_sample.py
"""
import base64
import glob
import os
import time

SAMPLE = r"C:/Users/Lenovo/Documents/imsma-importer/samples/eore_sep26"
PACKAGE = r"C:/Users/Lenovo/Documents/dma_field_reports/local/imsma_ref_20250302.zip"

Source = env["dma.fr.source"]
src = Source.search([("name", "=", "IMSMA backup 2025-03-02")], limit=1)
if not src:
    src = Source.create({"name": "IMSMA backup 2025-03-02", "mode": "package",
                         "package_file": base64.b64encode(open(PACKAGE, "rb").read()),
                         "package_filename": os.path.basename(PACKAGE)})
if src.state != "ok":
    t = time.time()
    src.action_refresh()
    print(f"loaded in {time.time() - t:.0f}s\n{src.stats}")
env.cr.commit()

xlsm = glob.glob(SAMPLE + "/*.xlsm")[0]
atts = env["ir.attachment"].create([
    {"name": os.path.basename(p), "datas": base64.b64encode(open(p, "rb").read())}
    for p in sorted(glob.glob(SAMPLE + "/*.docx"))])
batch = env["dma.fr.batch"].create({
    "template_id": env.ref("dma_field_reports.template_eore").id,
    "office_id": env.ref("dma_field_reports.office_dma_hq").id,
    "source_file": base64.b64encode(open(xlsm, "rb").read()),
    "source_filename": os.path.basename(xlsm),
    "attachment_ids": [(6, 0, atts.ids)],
})
t = time.time()
batch.action_check()
print(f"\n=== {batch.name}: checked in {time.time() - t:.1f}s; state={batch.state} rows={batch.row_count} "
      f"must-fix={batch.error_count} check={batch.warning_count} ok={batch.ok_count}")
for row in batch.row_ids:
    print(f"\n-- row {row.excel_row}: {row.state}  org={row.org_id.display_name}  place={row.place_id.complete_name}  "
          f"loc={row.location_label}  lat/lon={row.latitude:.5f},{row.longitude:.5f} ({row.coord_note or ''})  "
          f"atts={row.attachment_ids.mapped('name')}")
    for c in row.cell_ids.filtered(lambda c: c.state in ("error", "warning", "info")):
        print(f"   [{c.state:7}] {c.column:3} {c.field_id.name:25} raw={c.raw!r:30} -> {c.message}"
              + (f"   suggest: {c.suggestion}" if c.suggestion else ""))
print("\nnew locations:", [(r.name, r.place_id.complete_name, r.row_count) for r in batch.location_request_ids])
print(batch.column_report)
env.cr.commit()
