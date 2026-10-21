# DMA Field Reports (Odoo 19)

Replaces the iMMAP "Excel to IMSMA" Access tool. DMA/RMAC staff upload an operator's Excel file in
Odoo, see every problem at once, fix them in place, and download one zip of IMSMA NG maXML field
reports (with attachments) for the IMSMA Workbench import. IMSMA NG stays the system of record;
Odoo never writes to the IMSMA database.

**User walkthrough:** [docs/USER_GUIDE.md](docs/USER_GUIDE.md) (English), [docs/USER_GUIDE.ar.md](docs/USER_GUIDE.ar.md) (العربية). Server install: [DEPLOY.md](DEPLOY.md).

Design: `../imsma-importer/DESIGN.md`. Analysis of the old tool: `../imsma-importer/analysis/`.

## Status (2026-10-20, version 19.0.0.2.0)

- EORE (the DMA EORE Template English, Sep 2026) works end to end: check, fix, new locations, export.
- Location reports are generated from other batches.
- English and Arabic (UI, messages, and Arabic headers and answers in the operator file).
- Problem list for the operator (Excel), blank operator template per form, warning when a report was already exported.
- 600-row file: read 6 s, check 4 s, a fix on 300 rows 1.4 s (local PC).
- Other forms (QA/Survey123, Hazard, NTS, TS, Completion, UXO, Progress, Victim): templates to add,
  using `analysis/mappings/*.csv` of the old tool.
- Not yet tried: importing an exported zip into a real IMSMA NG (needs a test instance) and
  validating against `maXMLSchema.xsd` (upload it on the IMSMA data source to switch the check on).

## How it works

1. **IMSMA data** (manager, once and then when IMSMA changes): Configuration > IMSMA data source.
   - *Backup package*: on any PC with Python 3,
     `python addons/dma_field_reports/tools/imsma_ref_extract.py --backup <Backup_...\Dump.sql> --out imsma_ref.zip`,
     then upload the zip. It holds lists only (forms, custom fields and values used, gazetteer, locations
     with points, organisations, task ids, ids in use, report ids/statuses), but it still comes from IMSMA:
     keep it out of git.
   - *Live*: host/database/user of a read-only PostgreSQL user; optional nightly refresh.
2. **Batch** (user): Field Reports > Batches > New. Pick the form and office, upload the Excel file and
   drop the attachments (or a zip). Press **Check**.
3. **Fix problems**: grouped by column; the wrench opens a dialog that fixes every row with the same
   value and can remember the translation for future files. Unknown villages show the IMSMA locations
   nearest to the report's coordinates.
4. **New locations**: places without an IMSMA location are exported first as Location reports
   (zip A); import and approve them in IMSMA, then press *Locations approved*.
5. **Export to IMSMA**: zip B with `xml/`, `attachments/`, `manifest.csv`, `README.txt`.
6. The next IMSMA data load marks the reports *In IMSMA*.

## Development

```
odoo-bin -c odoo19_dma_field_reports.conf -d dma_fr_dev -u dma_field_reports   # port 8077, own DB
odoo-bin -c ... -d dma_fr_test -i dma_field_reports --test-tags dma_fr --stop-after-init
```

`tools_dev/` holds the scripts used to build the EORE template (`gen_eore_template.py`), check CDF ids
against IMSMA, and run the real-sample end-to-end (`e2e_sample.py`, `e2e_fix_export.py`). Real IMSMA
data and operator files stay in `local/` (git-ignored).
