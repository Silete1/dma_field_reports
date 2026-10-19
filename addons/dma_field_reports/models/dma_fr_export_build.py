"""Export: zips of maXML files for the IMSMA NG Workbench import. Odoo never writes to IMSMA."""
import base64
import csv
import hashlib
import io
import mimetypes
import uuid
import zipfile

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..services import maxml, text

README = """DMA Field Reports - {kind}
Batch {batch} - exported {when} by {user}

How to import (IMSMA NG Workbench)
1. Copy the files of the attachments folder (if any) into the attachments folder of the IMSMA server
   (for example C:\\IMSMAng\\server\\attachments).
2. In IMSMA: Data Entry > Import, choose the files of the xml folder.
3. Review and approve the imported reports in the Workbench.
{counters}
Then load fresh IMSMA data in Odoo (live refresh or a new backup package):
Odoo marks the reports as "In IMSMA".

---
طريقة الاستيراد في IMSMA NG
١. انسخ ملفات مجلد attachments (إن وجدت) إلى مجلد المرفقات في خادم IMSMA.
٢. في IMSMA: Data Entry > Import واختر ملفات مجلد xml.
٣. راجع التقارير المستوردة ووافق عليها في Workbench.
"""


def _uuid():
    return str(uuid.uuid4())


class DmaFrBatchExport(models.Model):
    _inherit = "dma.fr.batch"

    # ------------------------------------------------------------ guards
    def _assert_fresh(self):
        source = self.env["dma.fr.source"].current()
        if not source:
            raise UserError(_("No IMSMA data is loaded."))
        if self.source_stamp != source.stamp:
            self.action_check()
            if self.error_count:
                raise UserError(_("The IMSMA data was reloaded since the last check. The batch was checked again "
                                  "and now has problems to fix."))
        return source

    def _form(self, template):
        form = self.env["dma.fr.ref.form"].latest(template.imsma_form_name)
        if not form:
            raise UserError(_("IMSMA has no active form named '%s'. Load newer IMSMA data or correct the template.",
                              template.imsma_form_name))
        return form

    def _creator(self):
        return f"{self.env.user.name} (DMA Field Reports)"

    def _store_export(self, kind, name, data, count, note=""):
        return self.env["dma.fr.export"].create({
            "batch_id": self.id, "kind": kind, "file": base64.b64encode(data), "filename": name,
            "report_count": count, "counter_note": note})

    def _download(self, export):
        return {"type": "ir.actions.act_url", "target": "self",
                "url": f"/web/content/dma.fr.export/{export.id}/file/{export.filename}?download=true"}

    # ------------------------------------------------------------ locations (zip A)
    def action_export_locations(self):
        self.ensure_one()
        self._assert_fresh()
        reqs = self.location_request_ids.filtered(lambda r: r.state == "draft")
        if not reqs:
            raise UserError(_("There are no new locations to export."))
        blocking = self.cell_ids.filtered(lambda c: c.state == "error" and not c.row_excluded
                                          and c.field_id.role in ("province", "district", "subdistrict", "city",
                                                                  "location_name"))
        if blocking:
            raise UserError(_("Fix the place problems first (%s cells).", len(blocking)))
        template = self.env["dma.fr.template"].search([("kind", "=", "location")], limit=1)
        if not template:
            raise UserError(_("The Location template is missing."))
        form = self._form(template)
        code = self.office_id.code
        prefixes = [f"{template.object_id_prefix}-{code}-", f"{template.report_id_prefix}-{code}-"]
        first = self.env["dma.fr.counter"].allocate(template.object_id_type, len(reqs), prefixes)
        buf, files = io.BytesIO(), []
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for n, req in enumerate(reqs, start=first):
                req.write({"localid": f"{template.object_id_prefix}-{code}-{n}",
                           "report_localid": f"{template.report_id_prefix}-{code}-{n}",
                           "guid": req.guid or _uuid(), "fieldreport_guid": req.fieldreport_guid or _uuid()})
                rep = maxml.Report(form.guid, form.name, form.version, req.report_localid, req.fieldreport_guid,
                                   self._creator())
                rep.report_info(reporting_org="Directorate for Mine Action Iraq", reporting_date=fields.Date.today(),
                                verified_by=self.env.user.name)
                rep.location(req.guid, req.localid, req.name, req.place_id.chain())
                data = rep.tostring()
                self._validate_xml(data, req.report_localid)
                z.writestr(f"xml/{req.report_localid}.xml", data)
                files.append(req.report_localid)
            note = _("LOC counter in IMSMA (localidtype '%(t)s'): at least %(n)s.",
                     t=template.object_id_type, n=first + len(reqs))
            z.writestr("README.txt", README.format(kind="new locations", batch=self.name, when=fields.Datetime.now(),
                                                   user=self.env.user.name, counters=note))
        reqs.write({"state": "exported"})
        export = self._store_export("locations", f"{self.name.replace('/', '-')}_locations.zip", buf.getvalue(),
                                    len(reqs), note)
        self.state = "locations"
        self.message_post(body=_("%(n)s new location(s) exported: %(ids)s. %(note)s",
                                 n=len(reqs), ids=", ".join(files), note=note))
        return self._download(export)

    def action_confirm_locations(self):
        """The location reports are imported and approved in IMSMA: let the activities link to them."""
        self.ensure_one()
        reqs = self.location_request_ids.filtered(lambda r: r.state == "exported")
        if not reqs:
            raise UserError(_("No exported location is waiting for approval."))
        source = self.env["dma.fr.source"].current()
        if source.mode == "live":
            source.action_refresh()
        Loc = self.env["dma.fr.ref.location"]
        not_found = []
        for req in reqs:
            loc = Loc.search([("localid", "=", req.localid)], limit=1)
            if not loc and source.mode == "live":
                not_found.append(req.localid)
                continue
            if not loc:  # backup package: trust the user until the next package shows the location
                loc = Loc.create({"guid": req.guid, "localid": req.localid, "name": req.name,
                                  "name_norm": text.norm(req.name), "place_id": req.place_id.id, "origin": "confirmed"})
            req.write({"state": "confirmed", "ref_location_id": loc.id})
            req.row_ids.write({"location_id": loc.id})
        if not_found:
            raise UserError(_("IMSMA does not have these locations yet: %s. Approve them in the Workbench first.",
                              ", ".join(not_found)))
        self.message_post(body=_("New locations confirmed as approved in IMSMA."))
        self.action_check()
        return True

    # ------------------------------------------------------------ field reports (zip B)
    def action_export(self):
        self.ensure_one()
        self._assert_fresh()
        rows = self.row_ids.filtered(lambda r: not r.excluded)
        if not rows:
            raise UserError(_("No report to export."))
        if self.error_count:
            raise UserError(_("%s report(s) still have problems that must be fixed (or leave them out).",
                              self.error_count))
        waiting = self.location_request_ids.filtered(lambda r: r.state != "confirmed" and r.row_ids - r.row_ids.filtered("excluded"))
        if waiting:
            raise UserError(_("%s new location(s) must be created and approved in IMSMA first (step 3).", len(waiting)))
        t = self.template_id
        form = self._form(t)
        code = self.office_id.code
        todo = rows.filtered(lambda r: not r.object_localid)
        if todo:
            prefixes = [f"{t.object_id_prefix}-{code}-", f"{t.report_id_prefix}-{code}-"]
            n = self.env["dma.fr.counter"].allocate(t.object_id_type, len(todo), prefixes)
            for row in todo:
                row.write({"object_localid": f"{t.object_id_prefix}-{code}-{n}",
                           "report_localid": f"{t.report_id_prefix}-{code}-{n}",
                           "object_guid": _uuid(), "fieldreport_guid": _uuid()})
                n += 1
        builder = getattr(self, f"_build_{t.kind}", None)
        if not builder:
            raise UserError(_("Export of '%s' reports is not available yet.", t.name))
        buf, manifest = io.BytesIO(), []
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for row in rows:
                rep = maxml.Report(form.guid, form.name, form.version, row.report_localid, row.fieldreport_guid,
                                   self._creator())
                att_files = builder(rep, row)
                data = rep.tostring()
                self._validate_xml(data, row.report_localid)
                z.writestr(f"xml/{row.report_localid}.xml", data)
                for stored_name, content in att_files:
                    z.writestr(f"attachments/{stored_name}", content)
                manifest.append({"excel_row": row.excel_row, "report_id": row.report_localid,
                                 "imsma_id": row.object_localid, "fieldreport_guid": row.fieldreport_guid,
                                 "object_guid": row.object_guid, "attachments": " ".join(s for s, _c in att_files),
                                 "sha256": hashlib.sha256(data).hexdigest()})
            out = io.StringIO()
            w = csv.DictWriter(out, fieldnames=list(manifest[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(manifest)
            z.writestr("manifest.csv", out.getvalue().encode("utf-8-sig"))
            top = max(int(r.object_localid.rsplit("-", 1)[1]) for r in rows)
            note = _("Counter in IMSMA (localidtype '%(t)s'): at least %(n)s.", t=t.object_id_type, n=top + 1)
            z.writestr("README.txt", README.format(kind=t.name, batch=self.name, when=fields.Datetime.now(),
                                                   user=self.env.user.name, counters=note))
        rows.write({"imsma_state": "sent"})
        version = len(self.export_ids.filtered(lambda e: e.kind == "reports")) + 1
        suffix = f"_v{version}" if version > 1 else ""
        export = self._store_export("reports", f"{self.name.replace('/', '-')}_{t.kind}{suffix}.zip", buf.getvalue(),
                                    len(rows), note)
        self.state = "exported"
        self.message_post(body=_("%(n)s report(s) exported (%(first)s to %(last)s). %(note)s",
                                 n=len(rows), first=rows[0].object_localid, last=rows[-1].object_localid, note=note))
        return self._download(export)

    def _validate_xml(self, data, label):
        source = self.env["dma.fr.source"].current()
        if source and source.xsd_file:
            errors = maxml.validate(data, base64.b64decode(source.xsd_file))
            if errors:
                raise UserError(_("%(label)s does not match IMSMA's schema:\n%(errors)s",
                                  label=label, errors="\n".join(errors[:10])))

    # ------------------------------------------------------------ builders per form
    def _cells(self, row):
        """{role: [(cell, field)]} with the checked value of each cell."""
        out = {}
        for c in row.cell_ids:
            out.setdefault(c.field_id.role, []).append(c)
        return out

    @staticmethod
    def _val(cells, role):
        c = cells.get(role)
        return c[0].value if c and c[0].value else None

    def _attachments(self, rep, row):
        files = []
        for i, att in enumerate(row.attachment_ids, start=1):
            ext = (att.name or "").rsplit(".", 1)[-1].lower() if "." in (att.name or "") else "bin"
            guid = _uuid()
            content = base64.b64decode(att.datas or b"")
            rep.attachment(guid, f"{i}.{ext}", len(content), self.env.user.name,
                           mime=att.mimetype or mimetypes.guess_type(att.name or "")[0])
            files.append((f"{i}.{guid}.{ext}", content))
        return files

    def _cdfs(self, rep, parent, cells):
        for c in cells.get("cdf", []):
            f = c.field_id
            if not c.value or not f.cdf_id_text or not f.cdf_guid:
                continue
            dt = maxml.datatype_of(f.cdf_id_text, f.cdf_ref_id.datatype)
            if f.datatype == "multi":
                value = [v.strip() for v in c.value.split(", ") if v.strip()]
            elif f.datatype == "list":
                value = [c.value]
            else:
                value = c.value
            rep.cdf(parent, f.cdf_id_text, f.cdf_guid, value, dt)

    def _cdf_simple(self, rep, parent, cells, role):
        for c in cells.get(role, []):
            f = c.field_id
            if c.value and f.cdf_id_text and f.cdf_guid:
                rep.cdf(parent, f.cdf_id_text, f.cdf_guid, c.value,
                        maxml.datatype_of(f.cdf_id_text, f.cdf_ref_id.datatype))

    def _build_eore(self, rep, row):
        cells = self._cells(row)
        rep.report_info(reporting_person=self._val(cells, "reporting_person"),
                        reporting_position=self._val(cells, "reporting_position"),
                        reporting_date=row.report_date or fields.Date.today(),
                        verified_by=self.env.user.name)
        att_files = self._attachments(rep, row)
        act = rep.activity(self.template_id.object_element or "MREActivity", "MREIdentification",
                           row.object_guid, row.object_localid)
        if row.org_id:
            rep.organisation(act, "MREOrganisation", row.org_id.name, row.org_id.guid, row.org_id.localid)
        for c in cells.get("subcontractor", []):
            org = self._resolve_org_value(c)
            if org and c.field_id.cdf_guid:
                rep.cdf(act, c.field_id.cdf_id_text, c.field_id.cdf_guid,
                        {"name": org.name, "guid": org.guid, "localid": org.localid}, "ORGANISATION")
        if row.latitude or row.longitude:
            rep.point(act, _uuid(), lat=row.latitude, lon=row.longitude)
        elif self._val(cells, "mgrs"):
            rep.point(act, _uuid(), mgrs=self._val(cells, "mgrs").replace(" ", ""))
        rep.duration(act, "MREActivityDuration",
                     actual=(self._val(cells, "actual_start"), self._val(cells, "actual_end")),
                     planned=(self._val(cells, "planned_start"), self._val(cells, "planned_end")))
        reason = self._val(cells, "reason")
        if reason:
            maxml._sub(act, "MREReason", reason)
        comments = self._val(cells, "comments")
        if comments:
            maxml._sub(act, "Comments", comments)
        for role in ("task_dossier", "org_report_id", "location_name", "report_date"):
            self._cdf_simple(rep, act, cells, role)
        self._cdfs(rep, act, cells)
        loc = row.location_id
        if loc:
            rep.location_association(act, loc.guid, loc.localid)
        return att_files

    def _resolve_org_value(self, cell):
        Org = self.env["dma.fr.ref.org"]
        val = cell.value or ""
        if " · " in val:
            return Org.search([("localid", "=", val.split(" · ")[0])], limit=1)
        return Org.search([("name", "=", val)], limit=1)
