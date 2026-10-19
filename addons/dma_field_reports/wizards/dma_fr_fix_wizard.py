"""One dialog to fix a problem, for every row of the batch that has the same value."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services import text

PLACE_ROLES = ("province", "district", "subdistrict", "city")


class DmaFrFixWizard(models.TransientModel):
    _name = "dma.fr.fix.wizard"
    _description = "Fix a problem"

    cell_id = fields.Many2one("dma.fr.cell", required=True, readonly=True)
    batch_id = fields.Many2one(related="cell_id.batch_id")
    field_id = fields.Many2one(related="cell_id.field_id")
    raw = fields.Char(related="cell_id.raw", string="In the file")
    message = fields.Char(related="cell_id.message", string="Problem")
    code = fields.Char(related="cell_id.code")
    mode = fields.Selection([("list", "Pick a value"), ("org", "Pick an organisation"), ("place", "Pick a place"),
                             ("swap", "Swap coordinates"), ("text", "Correct the value")],
                            compute="_compute_mode")
    part = fields.Char("Value to fix", compute="_compute_mode",
                       help="For a cell with several values, the first one IMSMA does not know.")
    same_count = fields.Integer("Rows with the same value", compute="_compute_same")
    apply_all = fields.Boolean("Fix every row with this value", default=True)
    remember = fields.Boolean("Remember for future files", default=True,
                              help="Next time any file has this text in this column, it is translated automatically.")
    # list
    cdf_ref_id = fields.Many2one(related="cell_id.field_id.cdf_ref_id")
    option_id = fields.Many2one("dma.fr.ref.option", "IMSMA value",
                                domain="[('cdf_ref_id', '=', cdf_ref_id), ('is_preferred', '=', True)]")
    fixed_value = fields.Char("IMSMA value ", help="For lists that are not an IMSMA custom field.")
    # organisation
    org_id = fields.Many2one("dma.fr.ref.org", "Organisation in IMSMA")
    # place
    area_id = fields.Many2one(related="cell_id.row_id.area_id", string="Area found")
    place_choice = fields.Selection(
        [("existing", "It is an existing IMSMA location"),
         ("same", "It is a gazetteer place, written differently"),
         ("inside", "It is a village or site inside a gazetteer place: create it as a new IMSMA location")],
        default="inside")
    location_pick_id = fields.Many2one("dma.fr.ref.location", "IMSMA location")
    nearby_html = fields.Html(compute="_compute_nearby", sanitize=False)
    place_id = fields.Many2one("dma.fr.ref.place", "Place in the IMSMA gazetteer",
                               domain="[('level', '=', 'city'), ('id', 'child_of', area_id or [])]")
    # text
    new_value = fields.Char("Correct value")
    suggestion_html = fields.Html(compute="_compute_mode", sanitize=False)

    @api.depends("cell_id")
    def _compute_mode(self):
        for w in self:
            c, f = w.cell_id, w.cell_id.field_id
            w.part = False
            if c.code == "latlon_swapped":
                w.mode = "swap"
            elif c.code == "unknown_org":
                w.mode = "org"
            elif c.code in ("unknown_place",) or (f.role in PLACE_ROLES and c.state == "error"):
                w.mode = "place"
            elif c.code == "unknown_value" or (c.code == "required" and f.datatype in ("list", "multi")):
                w.mode = "list"
                raw = c.override or c.raw
                parts = text.split_multi(raw) if f.datatype == "multi" else [text.clean(raw)]
                w.part = next((p for p in parts if p and not w._is_known(f, p)), parts[0] if parts else "")
            elif c.code == "required" and f.datatype == "organisation":
                w.mode = "org"
            else:
                w.mode = "text"
            sugg = [s for s in (c.suggestion or "").split(" | ") if s]
            w.suggestion_html = (
                "<div class='text-muted'>" + _("Closest matches: ") + ", ".join(f"<b>{s}</b>" for s in sugg) + "</div>"
            ) if sugg else False

    def _is_known(self, field, part):
        key = text.norm(part)
        if self.env["dma.fr.value.map"].search_count([("scope", "=", field.mapping_scope), ("source_norm", "=", key)]):
            return True
        return any(text.norm(v) == key for v, _u in field.allowed_options())

    @api.depends("cell_id", "apply_all")
    def _compute_same(self):
        for w in self:
            w.same_count = len(w._target_cells())

    def _nearby(self):
        row = self.cell_id.row_id
        if not (row.latitude or row.longitude):
            return []
        from ..models.dma_fr_check import Ctx  # noqa: PLC0415

        ctx = Ctx.__new__(Ctx)  # only the location points are needed
        ctx.loc_points = [(l, l.latitude, l.longitude) for l in self.env["dma.fr.ref.location"].search(
            [("latitude", ">", row.latitude - 0.2), ("latitude", "<", row.latitude + 0.2),
             ("longitude", ">", row.longitude - 0.2), ("longitude", "<", row.longitude + 0.2)])]
        return Ctx.nearest_locations(ctx, row.latitude, row.longitude, max_km=15, limit=5)

    @api.depends("cell_id")
    def _compute_nearby(self):
        for w in self:
            near = w._nearby() if w.cell_id.field_id.role in PLACE_ROLES else []
            w.nearby_html = ("<div class='text-muted mb-2'>" + _("IMSMA locations near the report's point: ")
                             + "; ".join(f"<b>{l.name}</b> ({l.localid}, {km:.1f} km)" for km, l in near)
                             + "</div>") if near else False

    @api.onchange("mode")
    def _onchange_prefill(self):
        """Pre-select the best suggestion so a single click on Apply is often enough."""
        c = self.cell_id
        if self.mode == "place":
            near = self._nearby()
            if near:
                self.location_pick_id = near[0][1]
                if near[0][0] <= 2:
                    self.place_choice = "existing"
        first = (c.suggestion or "").split(" | ")[0] if c.suggestion else ""
        if not first:
            return
        if self.mode == "list" and self.cdf_ref_id:
            self.option_id = self.env["dma.fr.ref.option"].search(
                [("cdf_ref_id", "=", self.cdf_ref_id.id), ("value", "=", first)], limit=1)
        elif self.mode == "org":
            key = first.split(" · ")[0]
            self.org_id = self.env["dma.fr.ref.org"].search(["|", ("localid", "=", key), ("name", "=", first)], limit=1)
        elif self.mode == "place":
            row = c.row_id
            self.place_id = self.env["dma.fr.ref.place"].search(
                [("level", "=", "city"), ("name", "=", first)] +
                ([("id", "child_of", row.area_id.id)] if row.area_id else []), limit=1)

    def _target_cells(self):
        self.ensure_one()
        c = self.cell_id
        if not self.apply_all:
            return c
        return self.env["dma.fr.cell"].search([("batch_id", "=", c.batch_id.id), ("field_id", "=", c.field_id.id),
                                               ("raw", "=", c.raw), ("code", "=", c.code)])

    def action_apply(self):
        self.ensure_one()
        cells = self._target_cells()
        Cell = cells.with_context(dma_fr_no_recheck=True)
        f = self.field_id
        Map = self.env["dma.fr.value.map"]
        if self.mode == "list":
            target = self.option_id.value if self.option_id else text.clean(self.fixed_value)
            if not target:
                raise UserError(_("Pick the IMSMA value."))
            if self.remember and self.part:
                self._upsert_map(f.mapping_scope, self.part, target)
            else:
                for c in Cell:
                    raw = c.override or c.raw
                    if f.datatype == "multi":
                        parts = [target if text.norm(p) == text.norm(self.part) else p for p in text.split_multi(raw)]
                        c.override = ", ".join(parts)
                    else:
                        c.override = target
        elif self.mode == "org":
            if not self.org_id:
                raise UserError(_("Pick the organisation."))
            if self.remember and self.raw:
                self._upsert_map("organisation", self.raw, self.org_id.guid)
            else:
                Cell.write({"override": self.org_id.localid or self.org_id.name})
        elif self.mode == "place" and self.place_choice == "existing":
            if not self.location_pick_id:
                raise UserError(_("Pick the IMSMA location."))
            cells.row_id.write({"location_manual_id": self.location_pick_id.id,
                                "place_id": self.location_pick_id.place_id.id, "place_manual": True})
            Cell.write({"state": "ok", "code": False, "message": False})
        elif self.mode == "place":
            if not self.place_id:
                raise UserError(_("Pick the place."))
            rows = cells.row_id
            rows.write({"place_id": self.place_id.id, "place_manual": True, "location_manual_id": False})
            if self.place_choice == "same":
                if self.remember and text.norm(self.raw) != self.place_id.name_norm:
                    self.env["dma.fr.ref.place.alias"].create(
                        {"place_id": self.place_id.id, "alias": self.raw, "origin": "learned"})
                Cell.filtered(lambda x: x.field_id.role == "city").write({"override": self.place_id.name})
            # the place cells of these rows no longer block
            Cell.write({"state": "ok", "code": False, "message": False})
        elif self.mode == "swap":
            for c in Cell:
                row = c.row_id
                lat = row.cell_ids.filtered(lambda x: x.field_id.role == "latitude")[:1]
                lon = row.cell_ids.filtered(lambda x: x.field_id.role == "longitude")[:1]
                a, b = lat.override or lat.raw, lon.override or lon.raw
                lat.with_context(dma_fr_no_recheck=True).override = b
                lon.with_context(dma_fr_no_recheck=True).override = a
        else:
            if not self.new_value and f.required:
                raise UserError(_("Type the correct value."))
            Cell.write({"override": self.new_value})
        batch = self.cell_id.batch_id
        batch._run_check(cells.row_id)
        batch._update_state()
        batch.message_post(body=_("%(user)s fixed %(field)s ('%(raw)s') on %(n)s row(s).", user=self.env.user.name,
                                  field=f.name, raw=self.raw, n=len(cells.row_id)))
        return {"type": "ir.actions.act_window_close"}

    def _upsert_map(self, scope, source, target):
        Map = self.env["dma.fr.value.map"].with_context(active_test=False)
        existing = Map.search([("scope", "=", scope), ("source_norm", "=", text.norm(source))], limit=1)
        if existing:
            existing.write({"target_value": target, "active": True, "origin": "learned"})
        else:
            Map.create({"scope": scope, "source_value": source, "target_value": target, "origin": "learned"})
