"""IMSMA reference snapshot: read-only copies of the IMSMA lists that checking and export need.

Filled by dma.fr.source (live connection or backup package). Records are matched
by IMSMA GUID on every refresh: updated, created, or archived; never deleted,
so batches keep their links.
"""
from odoo import api, fields, models

from ..services import text

PLACE_LEVELS = [
    ("country", "Country"),
    ("province", "Province"),
    ("district", "District"),
    ("subdistrict", "Sub-district"),
    ("city", "City / town / village"),
]
IMSMA_LEVEL_LABEL = {"country": "Country", "province": "Province", "district": "District",
                     "subdistrict": "SubDistrict", "city": "City"}


class DmaFrRefForm(models.Model):
    _name = "dma.fr.ref.form"
    _description = "IMSMA field report form"
    _order = "name, version_num desc"
    _rec_names_search = ["name"]

    guid = fields.Char(required=True, index=True, readonly=True)
    name = fields.Char(required=True, readonly=True)
    version = fields.Char(readonly=True, help="As IMSMA writes it, e.g. 23 or 1.0.01")
    version_num = fields.Integer("Version number", readonly=True, help="Leading number of the version, for sorting.")
    published_on = fields.Char(readonly=True)
    is_active_in_imsma = fields.Boolean("Active in IMSMA", readonly=True)
    active = fields.Boolean(default=True)

    _guid_uniq = models.Constraint("unique(guid)", "IMSMA GUID must be unique.")

    @api.depends("name", "version")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name} v{rec.version}"

    @api.model
    def latest(self, name):
        """Newest form version that is active in IMSMA, by exact name (case-insensitive)."""
        forms = self.search([("is_active_in_imsma", "=", True)]).filtered(
            lambda f: f.name.strip().casefold() == (name or "").strip().casefold())
        return forms.sorted(lambda f: (f.published_on or "", f.version_num), reverse=True)[:1]


class DmaFrRefCdf(models.Model):
    _name = "dma.fr.ref.cdf"
    _description = "IMSMA custom field"
    _order = "entity, name"
    _rec_name = "cdf_id"

    cdf_id = fields.Char("IMSMA CDF id", required=True, index=True, readonly=True)
    name = fields.Char(readonly=True)
    label = fields.Char(readonly=True)
    datatype = fields.Char(readonly=True)
    entity = fields.Char(readonly=True)
    active = fields.Boolean(default=True)
    option_ids = fields.One2many("dma.fr.ref.option", "cdf_ref_id", string="Values used in IMSMA")

    _cdf_uniq = models.Constraint("unique(cdf_id)", "CDF id must be unique.")


class DmaFrRefOption(models.Model):
    _name = "dma.fr.ref.option"
    _description = "Value of an IMSMA list field"
    _order = "cdf_ref_id, usage desc, value"
    _rec_name = "value"

    cdf_ref_id = fields.Many2one("dma.fr.ref.cdf", "Custom field", required=True, index=True, ondelete="cascade")
    value = fields.Char(required=True)
    value_norm = fields.Char(index=True)
    usage = fields.Integer("Used in IMSMA", help="How many times IMSMA has stored this value.")
    is_preferred = fields.Boolean(
        "Preferred", default=True,
        help="Offered when fixing a value. Untick spellings that should not be used any more.")
    active = fields.Boolean(default=True)

    _value_uniq = models.Constraint("unique(cdf_ref_id, value)", "A value is listed once per field.")

    @api.depends("value", "usage")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.value} ({rec.usage})" if rec.usage else rec.value


class DmaFrRefPlace(models.Model):
    _name = "dma.fr.ref.place"
    _description = "IMSMA gazetteer place"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "complete_name"
    _rec_name = "complete_name"
    _rec_names_search = ["name", "complete_name", "alias_ids.alias"]

    guid = fields.Char(required=True, index=True, readonly=True)
    name = fields.Char(required=True, readonly=True)
    name_norm = fields.Char(index=True)
    level = fields.Selection(PLACE_LEVELS, index=True, readonly=True)
    parent_id = fields.Many2one("dma.fr.ref.place", "Parent", index=True, ondelete="restrict", readonly=True)
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("dma.fr.ref.place", "parent_id", "Children")
    complete_name = fields.Char(compute="_compute_complete_name", store=True, recursive=True)
    alias_ids = fields.One2many("dma.fr.ref.place.alias", "place_id", "Other names")
    location_ids = fields.One2many("dma.fr.ref.location", "place_id", "IMSMA locations")
    location_count = fields.Integer(compute="_compute_location_count")
    latitude = fields.Float(digits=(10, 6), readonly=True)
    longitude = fields.Float(digits=(10, 6), readonly=True)
    active = fields.Boolean(default=True)

    _guid_uniq = models.Constraint("unique(guid)", "IMSMA GUID must be unique.")

    @api.depends("name", "parent_id.complete_name", "level")
    def _compute_complete_name(self):
        for rec in self:
            if rec.parent_id and rec.parent_id.level != "country":
                rec.complete_name = f"{rec.parent_id.complete_name} / {rec.name}"
            else:
                rec.complete_name = rec.name

    def _compute_location_count(self):
        counts = {p.id: n for p, n in self.env["dma.fr.ref.location"]._read_group(
            [("place_id", "in", self.ids)], ["place_id"], ["__count"])}
        for rec in self:
            rec.location_count = counts.get(rec.id, 0)

    def chain(self):
        """[(guid, name, IMSMA level label)] from this place up to the country."""
        self.ensure_one()
        out, node = [], self
        while node:
            out.append((node.guid, node.name, IMSMA_LEVEL_LABEL.get(node.level, node.level or "")))
            node = node.parent_id
        return out


class DmaFrRefPlaceAlias(models.Model):
    _name = "dma.fr.ref.place.alias"
    _description = "Other name of a gazetteer place"
    _rec_name = "alias"

    place_id = fields.Many2one("dma.fr.ref.place", required=True, index=True, ondelete="cascade")
    alias = fields.Char(required=True)
    alias_norm = fields.Char(index=True)
    origin = fields.Selection([("imsma", "IMSMA"), ("learned", "Learned from a fix"), ("manual", "Manual")],
                              default="manual")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["alias_norm"] = text.norm(vals.get("alias"))
        return super().create(vals_list)


class DmaFrRefLocation(models.Model):
    _name = "dma.fr.ref.location"
    _description = "IMSMA location"
    _order = "localid"
    _rec_names_search = ["name", "localid"]

    guid = fields.Char(required=True, index=True, readonly=True)
    localid = fields.Char("IMSMA id", index=True, readonly=True)
    name = fields.Char(readonly=True)
    name_norm = fields.Char(index=True)
    place_id = fields.Many2one("dma.fr.ref.place", "Gazetteer place", index=True, readonly=True)
    latitude = fields.Float(digits=(10, 6), readonly=True)
    longitude = fields.Float(digits=(10, 6), readonly=True)
    origin = fields.Selection([("imsma", "In IMSMA"), ("confirmed", "Confirmed in Odoo, waiting for IMSMA data")],
                              default="imsma", readonly=True)
    active = fields.Boolean(default=True)

    _guid_uniq = models.Constraint("unique(guid)", "IMSMA GUID must be unique.")

    @api.depends("name", "localid")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.localid} · {rec.name}" if rec.localid else rec.name


class DmaFrRefOrg(models.Model):
    _name = "dma.fr.ref.org"
    _description = "IMSMA organisation"
    _order = "name"
    _rec_names_search = ["name", "localid"]

    guid = fields.Char(required=True, index=True, readonly=True)
    localid = fields.Char("IMSMA code", index=True, readonly=True)
    localid_norm = fields.Char(index=True)
    name = fields.Char(readonly=True)
    name_norm = fields.Char(index=True)
    active = fields.Boolean(default=True)

    _guid_uniq = models.Constraint("unique(guid)", "IMSMA GUID must be unique.")

    @api.depends("name", "localid")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.localid} · {rec.name}" if rec.localid and rec.localid != rec.name else rec.name


class DmaFrRefTask(models.Model):
    _name = "dma.fr.ref.task"
    _description = "IMSMA task (dossier)"
    _rec_name = "localid"

    guid = fields.Char(required=True, index=True, readonly=True)
    localid = fields.Char(index=True, readonly=True)
    localid_norm = fields.Char(index=True)

    _guid_uniq = models.Constraint("unique(guid)", "IMSMA GUID must be unique.")


class DmaFrRefIdUsage(models.Model):
    _name = "dma.fr.ref.idusage"
    _description = "Highest IMSMA number in use per id prefix"
    _rec_name = "prefix"

    prefix = fields.Char(required=True, index=True, readonly=True,
                         help="Local id without its number, e.g. 'Education-CI-' or 'LOC-SI-'.")
    max_number = fields.Integer(readonly=True)
    source = fields.Selection([("usage", "Ids found in IMSMA data"), ("counter", "IMSMA counter (localidtype)")],
                              default="usage", readonly=True)

    _prefix_uniq = models.Constraint("unique(prefix, source)", "One row per prefix and source.")
