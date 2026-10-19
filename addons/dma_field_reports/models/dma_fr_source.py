"""Where the IMSMA reference data comes from: a live read-only connection or a backup package."""
import base64
import logging
import os
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services import refdata, text

_logger = logging.getLogger(__name__)
LEVEL_ORDER = ["country", "province", "district", "subdistrict", "city", ""]


def _f(v):
    try:
        return round(float(v), 6)
    except (TypeError, ValueError):
        return 0.0


class DmaFrSource(models.Model):
    _name = "dma.fr.source"
    _description = "IMSMA reference source"
    _inherit = ["mail.thread"]
    _order = "is_current desc, id desc"

    name = fields.Char(required=True, tracking=True)
    mode = fields.Selection(
        [("package", "IMSMA backup package"), ("live", "Live IMSMA database (read-only)")],
        required=True, default="package", tracking=True,
        help="Package: a zip built from an IMSMA backup with tools/imsma_ref_extract.py. "
             "Live: Odoo reads IMSMA's PostgreSQL directly, read-only.")
    is_current = fields.Boolean("Use for checking", default=True, tracking=True,
                                help="Only one source is used at a time.")
    # live
    db_host = fields.Char("Host")
    db_port = fields.Integer("Port", default=5432)
    db_name = fields.Char("Database", default="imsma")
    db_user = fields.Char("User")
    db_password = fields.Char("Password", groups="dma_field_reports.group_dma_fr_manager", copy=False)
    # package
    package_file = fields.Binary("Package (zip)", attachment=True, copy=False)
    package_filename = fields.Char()
    server_path = fields.Char("Or path on the server",
                              help="For packages too large to upload: a path to the zip on the Odoo server.")
    xsd_file = fields.Binary("maXMLSchema.xsd", attachment=True,
                             help="Optional. When set, every exported file is checked against IMSMA's schema.")
    xsd_filename = fields.Char()
    # state
    state = fields.Selection([("new", "Not loaded"), ("ok", "Loaded"), ("failed", "Failed")], default="new",
                             readonly=True, tracking=True)
    dump_date = fields.Char("Data as of", readonly=True)
    refreshed_on = fields.Datetime(readonly=True)
    refreshed_by = fields.Many2one("res.users", readonly=True)
    stats = fields.Text(readonly=True)
    last_error = fields.Text(readonly=True)
    stamp = fields.Char(readonly=True, help="Changes every time the data is reloaded; batches remember it.")
    auto_refresh = fields.Boolean("Refresh every night", help="Live sources only.")

    @api.constrains("is_current")
    def _check_one_current(self):
        if self.search_count([("is_current", "=", True)]) > 1:
            raise UserError(_("Only one IMSMA source can be used for checking. Untick the other one first."))

    @api.model
    def current(self):
        return self.search([("is_current", "=", True), ("state", "=", "ok")], limit=1)

    # ------------------------------------------------------------------ actions
    def _conn_params(self):
        self.ensure_one()
        if not (self.db_host and self.db_name and self.db_user):
            raise UserError(_("Fill in host, database and user."))
        return {"host": self.db_host, "port": self.db_port or 5432, "dbname": self.db_name,
                "user": self.db_user, "password": self.sudo().db_password or ""}

    def action_test_connection(self):
        self.ensure_one()
        import psycopg2

        try:
            conn = psycopg2.connect(connect_timeout=10, **self._conn_params())
            conn.set_session(readonly=True)
            with conn.cursor() as cr:
                cr.execute("SELECT count(*) FROM fieldreportdesc")
                n = cr.fetchone()[0]
            conn.close()
        except Exception as e:  # noqa: BLE001 - show any connection error to the user
            raise UserError(_("Could not read IMSMA: %s", e)) from e
        return self._notify(_("Connected. IMSMA has %s form definitions.", n), "success")

    def action_refresh(self):
        for src in self:
            try:
                if src.mode == "live":
                    out, manifest = refdata.read_live(src._conn_params())
                else:
                    out, manifest = refdata.read_package(src._package_bytes())
                with self.env.cr.savepoint():
                    stats = self.env["dma.fr.source"]._load_snapshot(out)
                    stats.update(self.env["dma.fr.row"]._reconcile_with_imsma(out["reports.csv"]))
            except (ValueError, UserError) as e:
                src.write({"state": "failed", "last_error": str(e)})
                raise UserError(str(e)) from e
            src.write({
                "state": "ok", "last_error": False, "dump_date": manifest.get("dump_date") or "",
                "refreshed_on": fields.Datetime.now(), "refreshed_by": self.env.uid,
                "stats": "\n".join(f"{k}: {v}" for k, v in stats.items()),
                "stamp": f"{src.id}-{fields.Datetime.now().isoformat()}",
            })
            src.message_post(body=_("IMSMA data loaded (as of %(date)s).", date=manifest.get("dump_date") or "?"))
        return self._notify(_("IMSMA data loaded."), "success")

    def _package_bytes(self):
        self.ensure_one()
        if self.package_file:
            return base64.b64decode(self.package_file)
        if self.server_path:
            if not os.path.isfile(self.server_path):
                raise UserError(_("No file at %s on the server.", self.server_path))
            with open(self.server_path, "rb") as f:
                return f.read()
        raise UserError(_("Upload the package zip or give its path on the server."))

    @api.model
    def _cron_refresh_live(self):
        for src in self.search([("mode", "=", "live"), ("auto_refresh", "=", True), ("is_current", "=", True)]):
            try:
                src.action_refresh()
            except UserError as e:
                _logger.warning("IMSMA live refresh of %s failed: %s", src.name, e)

    def _notify(self, message, kind="info"):
        return {"type": "ir.actions.client", "tag": "display_notification",
                "params": {"message": message, "type": kind, "sticky": False,
                           "next": {"type": "ir.actions.client", "tag": "soft_reload"}}}

    # ------------------------------------------------------------------ loading
    @api.model
    def _upsert(self, model, key, rows, make_vals):
        """Create/update records of `model` matched on `key`; archive those not in rows. Returns counts."""
        Model = self.env[model].with_context(active_test=False)
        existing = {getattr(r, key): r for r in Model.search([])}
        seen, to_create, updated = set(), [], 0
        for row in rows:
            vals = make_vals(row)
            if vals is None:
                continue
            k = vals[key]
            if k in seen:
                continue
            seen.add(k)
            rec = existing.get(k)
            if rec:
                changes = {}
                for f, v in vals.items():
                    current = rec[f]
                    if isinstance(rec._fields[f], fields.Many2one):
                        current = current.id or False
                    elif isinstance(rec._fields[f], fields.Float):
                        current = round(current or 0.0, 6)
                    if current != v:
                        changes[f] = v
                if changes:
                    rec.write(changes)
                    updated += 1
            else:
                to_create.append(vals)
        created = Model.create(to_create) if to_create else Model
        stale = [r.id for k, r in existing.items() if k not in seen and r.active]
        if stale and "active" in Model._fields:
            Model.browse(stale).write({"active": False})
        return {"created": len(created), "updated": updated, "archived": len(stale)}

    @api.model
    def _load_snapshot(self, out):
        stats = {}
        b = lambda v: str(v).lower() == "true"  # noqa: E731
        stats["forms"] = self._upsert("dma.fr.ref.form", "guid", out["forms.csv"], lambda r: {
            "guid": r["guid"], "name": r["name"], "version": r["version"] or "",
            "version_num": int(re.match(r"\d*", r["version"] or "").group() or 0),
            "published_on": r["published_on"], "is_active_in_imsma": b(r["active"]), "active": True})
        stats["custom fields"] = self._upsert("dma.fr.ref.cdf", "cdf_id", out["cdfs.csv"], lambda r: {
            "cdf_id": r["cdf_id"], "name": r["name"], "label": r["label"], "datatype": r["datatype"],
            "entity": r["entity"], "active": b(r["active"])})
        cdf_ids = {c.cdf_id: c.id for c in self.env["dma.fr.ref.cdf"].with_context(active_test=False).search([])}
        Option = self.env["dma.fr.ref.option"].with_context(active_test=False)
        opts = {(o.cdf_ref_id.id, o.value): o for o in Option.search([])}
        new_opts, seen = [], set()
        for r in out["cdf_options.csv"]:
            cid = cdf_ids.get(r["cdf_id"])
            if not cid:
                continue
            key = (cid, r["value"])
            seen.add(key)
            if key in opts:
                if opts[key].usage != int(r["usage"]):
                    opts[key].usage = int(r["usage"])
            else:
                new_opts.append({"cdf_ref_id": cid, "value": r["value"], "value_norm": text.norm(r["value"]),
                                 "usage": int(r["usage"])})
        Option.create(new_opts)
        stats["list values"] = {"created": len(new_opts), "total": len(seen)}

        # gazetteer, parents first
        Place = self.env["dma.fr.ref.place"].with_context(active_test=False)
        by_guid = {p.guid: p for p in Place.search([])}
        rows = sorted(out["places.csv"], key=lambda r: LEVEL_ORDER.index(r["level"]) if r["level"] in LEVEL_ORDER else 5)
        created = updated = 0
        for level in LEVEL_ORDER:
            batch = []
            for r in rows:
                if (r["level"] if r["level"] in LEVEL_ORDER else "") != level:
                    continue
                vals = {"guid": r["guid"], "name": r["name"], "name_norm": text.norm(r["name"]),
                        "level": r["level"] or False, "active": True,
                        "latitude": _f(r.get("lat")), "longitude": _f(r.get("lon")),
                        "parent_id": by_guid[r["parent_guid"]].id if r["parent_guid"] in by_guid else False}
                rec = by_guid.get(r["guid"])
                if rec:
                    if (rec.name, rec.parent_id.id, rec.level, round(rec.latitude, 6), round(rec.longitude, 6)) != (
                            vals["name"], vals["parent_id"], vals["level"], vals["latitude"], vals["longitude"]):
                        rec.write(vals)
                        updated += 1
                else:
                    batch.append(vals)
            for rec in Place.create(batch) if batch else []:
                by_guid[rec.guid] = rec
                created += 1
        stats["places"] = {"created": created, "updated": updated}
        Alias = self.env["dma.fr.ref.place.alias"]
        Alias.search([("origin", "=", "imsma")]).unlink()
        Alias.create([{"place_id": by_guid[r["guid"]].id, "alias": r["alias"], "origin": "imsma"}
                      for r in out["place_aliases.csv"] if r["guid"] in by_guid])

        # locations: keep the ones confirmed in Odoo until IMSMA data has them
        stats["locations"] = self._upsert("dma.fr.ref.location", "guid", out["locations.csv"], lambda r: {
            "guid": r["guid"], "localid": r["localid"], "name": r["name"], "name_norm": text.norm(r["name"]),
            "place_id": by_guid[r["place_guid"]].id if r["place_guid"] in by_guid else False,
            "latitude": _f(r.get("lat")), "longitude": _f(r.get("lon")),
            "active": b(r["active"]), "origin": "imsma"})
        imsma_localids = {r["localid"] for r in out["locations.csv"]}
        pending = self.env["dma.fr.ref.location"].search([("origin", "=", "confirmed")])
        pending.filtered(lambda l: l.localid in imsma_localids).write({"active": False})
        pending.filtered(lambda l: l.localid not in imsma_localids).write({"active": True})

        stats["organisations"] = self._upsert("dma.fr.ref.org", "guid", out["organisations.csv"], lambda r: {
            "guid": r["guid"], "localid": r["localid"], "localid_norm": text.norm(r["localid"]),
            "name": r["name"], "name_norm": text.norm(r["name"]), "active": b(r["active"])})
        stats["tasks"] = self._upsert("dma.fr.ref.task", "guid", out["tasks.csv"], lambda r: {
            "guid": r["guid"], "localid": r["localid"], "localid_norm": text.norm(r["localid"])})
        Usage = self.env["dma.fr.ref.idusage"]
        self.env.cr.execute("DELETE FROM dma_fr_ref_idusage")
        Usage.invalidate_model()
        Usage.create([{"prefix": r["prefix"], "max_number": int(r["max_number"]), "source": "usage"}
                      for r in out["id_usage.csv"]]
                     + [{"prefix": r["name"], "max_number": int(r["next_number"] or 1) - 1, "source": "counter"}
                        for r in out["idtypes.csv"]])
        stats["id prefixes"] = len(out["id_usage.csv"])
        return stats
