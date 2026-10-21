# DMA Field Reports: user walkthrough

**العربية:** [USER_GUIDE.ar.md](USER_GUIDE.ar.md)

This guide is for DMA HQ and RMAC staff who turn an operator's Excel file into reports for IMSMA NG. It also covers the one-time setup a manager does.

The module takes the operator's Excel file and finds every problem in it. You fix the problems in Odoo, then download one zip that the IMSMA Workbench imports. IMSMA NG stays the system of record, and Odoo never writes to the IMSMA database.

Version 19.0.0.2.0. Ready: EORE and the location reports it needs. Other forms (QA/Survey123, Hazard, NTS, TS, Completion, UXO, Progress, Victim) come later as new templates, and they will use the same screens.

Where the Odoo user language is Arabic, every screen, message and download is in Arabic. Labels below are given in English with the Arabic in brackets.

---

## 1. Who can do what

Set roles in **Settings → Users** → open the user → section **DMA Field Reports**.

| Role | Can |
|---|---|
| **User** (المستخدم) | Upload operator files, fix problems, export the IMSMA zips. For DMA HQ and RMAC data officers. |
| **Manager** (المدير) | Everything a User can, plus: load IMSMA data and maintain templates, value translations, offices and id counters. |
| *(none)* | Does not see the app. |

The app is **Field Reports** (التقارير الميدانية) on the Odoo home screen.

---

## 2. One-time setup (Manager)

### 2.1 Load the IMSMA data

Odoo checks every value against IMSMA's own lists: gazetteer, locations, organisations, forms, and custom fields with their values. It needs a copy of those lists, which you load from one of two sources. You choose which.

**Field Reports → Configuration → IMSMA data source** (التهيئة ← مصدر بيانات IMSMA) → **New**.

**Option A: IMSMA backup package** (حزمة النسخة الاحتياطية لـ IMSMA). Use this when Odoo cannot reach IMSMA.

1. On any PC with Python 3 and an IMSMA backup folder, run:
   ```
   python addons/dma_field_reports/tools/imsma_ref_extract.py --backup "Backup_YYYY_MM_DD_hh_mm_ss\Dump.sql" --out imsma_ref.zip
   ```
   `--backup` also accepts a folder of `copy_*.txt` files.
2. In Odoo, set **Mode** to *IMSMA backup package* and upload `imsma_ref.zip` in **Package (zip)**.
3. Press **Load IMSMA data** (تحميل بيانات IMSMA). This takes about a minute.

**Option B: live IMSMA database** (قاعدة بيانات IMSMA المباشرة). Use this when the Odoo server can reach IMSMA's PostgreSQL.

1. Set **Mode** to *Live IMSMA database (read-only)*.
2. Enter **Host**, **Port**, **Database** (usually `imsma`), **User** and **Password**. Use a read-only PostgreSQL user.
3. Press **Test connection** (اختبار الاتصال), then **Load IMSMA data**.
4. Optional: tick **Refresh every night** (التحديث كل ليلة).

Notes for both options:
- After a load, the source shows **Data as of** and the counts of what was loaded.
- Only one source is used for checking at a time: the one with **Use for checking** (الاستخدام في التدقيق) ticked.
- Load again whenever IMSMA has changed: a newer backup, new locations, or newly approved reports. Each load also marks exported reports that are now in IMSMA as **In IMSMA**.
- Optional: upload `maXMLSchema.xsd` on the source. Every export is then validated against it.
- The package holds lists, not report contents. It still comes from IMSMA, so keep it off public places such as a public GitHub repo.

To see what was loaded, open **Field Reports → IMSMA data** (بيانات IMSMA):
- **Gazetteer** (الدليل الجغرافي)
- **Locations** (المواقع)
- **Organisations** (المؤسسات)
- **Forms** (الاستمارات)
- **Custom fields and values** (الحقول المخصصة وقيمها)

These screens are read-only.

### 2.2 Offices and id counters

**Configuration → Offices** (المكاتب): one line per office that imports, with the code it uses in IMSMA ids. The built-in offices are DMA HQ = `CI` and RMAC South = `SI`. Add other offices here.

**Configuration → IMSMA id counters** (عدّادات معرّفات IMSMA) give each new report its IMSMA id, for example `Education-CI-75322`. A counter never goes below the highest number already in IMSMA, so ids are never reused. You normally don't touch these.

### 2.3 Form templates and blank files for operators

**Configuration → Form templates** (قوالب الاستمارات): one template per form. Each template says:
- which sheet and rows hold the data;
- which Excel column feeds which IMSMA field. Columns are found by header text in English or Arabic, not by position, so moved columns still work.
- what each column must contain, and whether it is required.

For each template, upload a **Blank file for operators** (النموذج الفارغ للمنظمات). Users can then download it from any batch and send it to the operator.

### 2.4 Value translations

**Configuration → Value translations** (مطابقات القيم) turns the operators' own wording into the exact IMSMA value. For example, an Arabic answer becomes IMSMA's English list value.

There are three kinds of entry:
- **Built in** (about 60 common Arabic answers).
- **Learned from a fix**: added automatically when a user fixes a value with *Remember for future files* ticked.
- **Manual**: added by a manager.

If a translation was learned wrongly, archive it here.

---

## 3. Processing an operator file (User)

**Field Reports → Batches → New** (الدفعات ← جديد).

Each batch shows a coloured box at the top that says which step it is on and what to press next. The buttons in the header only appear when they apply.

| Status | Meaning |
|---|---|
| Uploaded (مرفوع) | File uploaded, not yet checked |
| Problems to fix (مشكلات يجب إصلاحها) | Some reports have must-fix problems |
| New locations in IMSMA (مواقع جديدة في IMSMA) | Waiting for new locations to be approved in IMSMA |
| Ready to export (جاهز للتصدير) | Everything required is in place |
| Exported (مُصدَّر) | Zip downloaded, waiting for the IMSMA import |
| In IMSMA (في IMSMA) | Every report was found in IMSMA |
| Cancelled (ملغاة) | Nothing will be exported |

### Step 1: upload

1. Choose the **Form** (الاستمارة), for example EORE.
2. Choose the **Office** (المكتب).
3. Upload the **Operator file** (ملف الجهة المنفذة).
4. Drop the Word reports and photos into **Attachments** (المرفقات). You can drop them one by one or as one zip.
   - Attachments are matched to reports by the file names listed in the file's attachments column.
   - When that column is empty, they are matched by the organisation's report id.
5. Press **Check** (تدقيق).

The check reads every row and compares every value with the IMSMA data. Problems come in three levels:
- **Must fix** (يجب إصلاحه): the report cannot be exported until it is fixed or left out.
- **Check**: a warning. You can still export.
- **Note** (ملاحظة): information only.

The batch also warns when a report is a duplicate inside the file, or was already exported in an earlier batch.

### Step 2: fix problems

Press **Fix problems** (إصلاح المشكلات). Problems are grouped by column and then by value, so one fix covers every row with the same wrong text.

On a problem row, press the wrench. The dialog matches the kind of problem:

| Dialog | Use |
|---|---|
| **Pick a value** (اختيار قيمة) | The text is not an IMSMA list value. Pick the right value; the closest matches are suggested. |
| **Pick an organisation** (اختيار مؤسسة) | The organisation name is not known to IMSMA. |
| **Pick a place** (اختيار مكان) | The village or area is not found. Choose one of three answers (below). |
| **Swap coordinates** (تبديل الإحداثيات) | Latitude and longitude were entered the wrong way round. |
| **Correct the value** (تصحيح القيمة) | A wrong date, number or text. Type the correct value. |

The three answers for a place:
- **It is an existing IMSMA location** (إنه موقع IMSMA موجود): pick it. The IMSMA locations closest to the report's coordinates are listed, with their distances.
- **It is a gazetteer place, written differently**: pick the place.
- **It is a village or site inside a gazetteer place** (the default): pick the area. A new IMSMA location is then created for it in step 3.

At the bottom of every dialog:
- **Fix every row with this value** (إصلاح كل الصفوف التي تحمل هذه القيمة) is on by default.
- **Remember for future files** (الحفظ للملفات القادمة) is on by default. The next file with the same text is then translated automatically.

Press **Apply** (تطبيق). Every fix is written to the batch's chatter with the user's name.

Other tools in this step:
- **Accept** (قبول), on a warning, accepts it as it is. Use it for things like a long comment or a known missing photo.
- **Leave out of the export** (استبعاد من التصدير) drops a report that should not go to IMSMA. **Include again** (إعادة التضمين) brings it back.
- **Problem list for the operator** (قائمة المشكلات للمنظمة) downloads an Excel list of the open problems, in Arabic for Arabic users, to send back to the operator.
- **Check again** (إعادة التدقيق) re-reads everything, for example after you load newer IMSMA data.

The **Reports** tab (التقارير) shows one line per report with its status. The **File columns** tab (أعمدة الملف) shows how each Excel column was matched.

### Step 3: new locations (only when needed)

When some places have no IMSMA location yet, IMSMA must create those locations before the reports can be linked to them.

1. Press **Export new locations** (تصدير المواقع الجديدة). This downloads a zip of Location reports.
2. In the **IMSMA Workbench**, import the zip and approve the location reports.
3. Back in Odoo, press **Locations approved in IMSMA** (تمت الموافقة على المواقع في IMSMA).
   - With a live source, Odoo reloads the IMSMA data by itself.
   - With a package source, a manager loads a newer package.

The **New locations** tab (مواقع جديدة) lists each requested location and its status.

### Step 4: export to IMSMA

1. Press **Export to IMSMA** (تصدير إلى IMSMA). The zip contains:
   - `xml/`: one maXML field report per report;
   - `attachments/`;
   - `manifest.csv`: one line per report, with its IMSMA ids;
   - `README.txt`: how to import it.
2. In the **IMSMA Workbench**, import the zip and approve the reports.
3. The next time the IMSMA data is loaded, the batch moves to **In IMSMA** by itself.

Every export is kept in the **Exports** tab (عمليات التصدير), so you can download it again.

### Changing your mind

- **Re-open** (إعادة الفتح), on an exported batch, lets you fix more and export again. The reports keep the IMSMA ids they already have, so IMSMA updates the same reports instead of making duplicates.
- **Cancel batch** (إلغاء الدفعة) means nothing from it will be exported. **Back to draft** (إعادة إلى المسودة) undoes a cancel.

---

## 4. Daily routine in short

1. **New** batch → form, office, Excel file, attachments → **Check**.
2. **Fix problems** → wrench → **Apply**. Repeat until no must-fix problem is left, or leave the bad reports out.
3. If asked: **Export new locations** → import and approve in IMSMA → **Locations approved in IMSMA**.
4. **Export to IMSMA** → import and approve in the IMSMA Workbench.
5. The manager loads fresh IMSMA data, and the batch turns **In IMSMA**.

---

## 5. When something goes wrong

| You see | Do |
|---|---|
| "No IMSMA data is loaded" | A manager must do §2.1 first. |
| A whole column flagged as unknown | Its header text is not in the template. A manager adds the header in **Form templates** → the column's headers. |
| The same Arabic answer is flagged in every file | Fix it once with *Remember for future files* ticked. |
| Correct village, but "not found" | It may be new to IMSMA: use "inside a gazetteer place" and go through step 3. |
| "Already exported" warning | The same report was in an earlier batch. Leave it out, unless you mean to send an update. |
| A missing attachment warning | Drop the file into Attachments and press **Check again**, or **Accept** it. |
| Export button not showing | Must-fix problems are left, or new locations are still waiting. The box at the top says which. |
| Form version warning on the template | IMSMA has a newer version of the form. A manager reviews the template. |

---

## 6. Installing on a server

See [DEPLOY.md](../DEPLOY.md): copy the module, back up, install or upgrade, set roles, load the IMSMA data.
