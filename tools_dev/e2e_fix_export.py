"""Continue the real-sample run: fix the problems the way a user would, then export. Run in odoo-bin shell."""
import base64
import io
import zipfile

OUT = r"C:/Users/Lenovo/Documents/dma_field_reports/local/"
batch = env["dma.fr.batch"].search([], order="id desc", limit=1)
Wiz = env["dma.fr.fix.wizard"]


def problem(row_no, field_name):
    return batch.cell_ids.filtered(lambda c: c.excel_row == row_no and c.field_id.name == field_name
                                   and c.state in ("error", "warning"))[:1]


def fix(cell, **vals):
    w = Wiz.create(dict({"cell_id": cell.id}, **vals))
    w._onchange_prefill()
    for k, v in vals.items():
        setattr(w, k, v)
    print(f"  fix row {cell.excel_row} {cell.field_id.name} {cell.raw!r} mode={w.mode} rows={w.same_count}")
    w.action_apply()


Opt = env["dma.fr.ref.option"]
funded = batch.template_id.field_ids.filtered(lambda f: f.name == "Funded by").cdf_ref_id
fix(problem(6, "Funded by"), option_id=Opt.search([("cdf_ref_id", "=", funded.id), ("value", "=", "PMWRA")]).id)
fix(problem(9, "Funded by"), option_id=Opt.search([("cdf_ref_id", "=", funded.id), ("value", "=", "Norway")]).id)
mac = batch.template_id.field_ids.filtered(lambda f: f.name == "MAC owner").cdf_ref_id
fix(problem(8, "MAC owner"), option_id=Opt.search([("cdf_ref_id", "=", mac.id), ("value", "=", "RMAC-N")]).id)
# Alkasarah = the IMSMA location 0.8 km away (قرية الكسارة)
c = problem(6, "City / town / village")
w = Wiz.create({"cell_id": c.id})
w._onchange_prefill()
print("  nearest pick for Alkasarah:", w.location_pick_id.display_name, w.place_choice)
w.place_choice = "existing"
w.action_apply()
# Alraas Algharbi and Alsangak: new locations inside the Haditha city node
haditha = env["dma.fr.ref.place"].search([("level", "=", "city"), ("name", "=", "Al Haditha")], limit=1)
for row_no in (8, 9):
    c = problem(row_no, "City / town / village")
    if c:
        fix(c, place_choice="inside", place_id=haditha.id, apply_all=False)

batch.invalidate_recordset()
print(f"after fixes: state={batch.state} must-fix={batch.error_count} check={batch.warning_count}")
for c in batch.cell_ids.filtered(lambda c: c.state == "error"):
    print("  still:", c.excel_row, c.field_id.name, c.raw, c.message)
print("new locations:", [(r.name, r.place_id.complete_name, r.state) for r in batch.location_request_ids])

act = batch.action_export_locations()
exp = batch.export_ids[:1]
open(OUT + exp.filename, "wb").write(base64.b64decode(exp.file))
print("locations zip:", exp.filename, exp.counter_note)
batch.action_confirm_locations()
print(f"after confirm: state={batch.state} must-fix={batch.error_count}")
act = batch.action_export()
exp = batch.export_ids.filtered(lambda e: e.kind == "reports")[:1]
open(OUT + exp.filename, "wb").write(base64.b64decode(exp.file))
print("reports zip:", exp.filename, exp.report_count, exp.counter_note)
with zipfile.ZipFile(io.BytesIO(base64.b64decode(exp.file))) as z:
    for n in z.namelist():
        print("   ", n, z.getinfo(n).file_size)
for r in batch.row_ids:
    print("  row", r.excel_row, r.object_localid, r.report_localid, r.location_id.display_name, r.imsma_state)
env.cr.commit()
