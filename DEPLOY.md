# Deploying DMA Field Reports to the DMA Odoo server

Version 19.0.0.2.0. Tested on 2026-10-20 against a copy of the live module set:
- integ/dma-unified 4a1ffb4 (dma_theme, dma_accreditation, gov_hr_base, gov_hr_deputation);
- dma_task_orders 71f6cb9;
- Odoo 19 Community.

All 16 module tests pass, run with the real IMSMA data loaded, on a fresh database and on one upgraded from 19.0.0.1.0. The module needs only `base`, `mail` and `web`.

The Python libraries it uses (openpyxl, lxml, psycopg2) are in Odoo 19's own requirements and in the official `odoo:19` image. No pip install is needed.

## 1. Copy the module
Put the folder `dma_field_reports` (from `dma_field_reports_module.zip`) next to the other DMA modules on the server, in the addons folder the Odoo container reads (on dmawebsite.immapiraq.org: `~/odoo19/addons`).

## 2. Back up, then install
```
pg_dump -Fc dma > ~/backups/pre-field-reports-$(date +%Y%m%d-%H%M).dump      # inside/next to the db container
docker compose stop odoo
docker compose run --rm --no-deps odoo odoo -c /etc/odoo/odoo.conf -d dma -i dma_field_reports --stop-after-init --no-http </dev/null
docker compose start odoo
```
Arabic loads with the module when Arabic is already installed on the database. If Arabic labels are missing, run:
```
docker compose run --rm --no-deps odoo odoo -c /etc/odoo/odoo.conf -d dma -u dma_field_reports --i18n-overwrite --stop-after-init --no-http </dev/null
```

## 2b. Already installed 19.0.0.1.0? Upgrade instead
Same backup and stop/start, then run `-u dma_field_reports` instead of `-i`. The upgrade:
- adds the Arabic headers to the EORE columns a manager has not changed;
- adds the built-in Arabic list translations, and never overwrites a mapping someone made;
- loads the new Arabic texts.

## 3. Give people access
In Settings > Users, section **DMA Field Reports**:
- **User:** uploads operator files, fixes problems and exports the IMSMA zips (DMA HQ / RMAC staff).
- **Manager:** also loads IMSMA data and maintains templates, value translations, offices and id counters.

Admin is a Manager by default. Staff without either role do not see the app.

## 4. Load IMSMA data (Manager, once)
On a PC that has an IMSMA backup and Python 3:
```
python dma_field_reports/tools/imsma_ref_extract.py --backup "Backup_YYYY_MM_DD_hh_mm_ss\Dump.sql" --out imsma_ref.zip
```
Then, in Field Reports > Configuration > IMSMA data source: create the source, mode *IMSMA backup package*, upload `imsma_ref.zip`, press **Load IMSMA data**. On a 1-vCPU server the load takes about a minute.

The package holds lists, not report contents, but it comes from IMSMA: do not post it anywhere public.

## 5. Check offices and counters
Configuration > Offices holds DMA HQ = `CI` and RMAC South = `SI`. Add the other offices that import, with the code they use in IMSMA ids.

## 6. First real batch
Upload one EORE file and export it. Import the zip into IMSMA with the Workbench and check the reports. Do this with a test copy of IMSMA if you have one; otherwise import one report first and review it before doing a whole batch.

## Undo
Uninstall the module from Apps, or restore the backup from step 2. The module writes nothing to IMSMA and changes no other module's data.
