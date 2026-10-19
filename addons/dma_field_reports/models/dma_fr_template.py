"""Form templates: how the columns of an operator file map to an IMSMA field report.

This is the part that was hard-coded VBA in the Access tool. Columns are found
by header text (any of the aliases), never by letter, so a moved or added
column does not shift anything. A new custom field is a new line here.
"""
from odoo import _, api, fields, models

from ..services import text

KINDS = [
    ("eore", "EORE (Explosive Ordnance Risk Education)"),
    ("location", "Location"),
    ("qa", "Quality Assurance (Survey123)"),
    ("hazard", "Hazard"),
    ("uxo_spot", "UXO Spot"),
    ("nts", "Non-Technical Survey"),
    ("ts", "Technical Survey"),
    ("completion", "Completion"),
    ("uxo_completion", "UXO Spot Completion"),
    ("progress", "Progress"),
    ("victim", "Victim / VA survey"),
]
ROLES = [
    ("cdf", "IMSMA custom field (CDF)"),
    ("reporting_person", "Reported by"),
    ("reporting_position", "Position of the reporter"),
    ("report_date", "Date of report"),
    ("organisation", "Organisation (operator)"),
    ("subcontractor", "Sub-contractor (organisation CDF)"),
    ("task_dossier", "Task dossier id"),
    ("province", "Place: province"),
    ("district", "Place: district"),
    ("subdistrict", "Place: sub-district"),
    ("city", "Place: city / town / village"),
    ("location_name", "Location name"),
    ("location_guid", "IMSMA location GUID"),
    ("mgrs", "Coordinates: MGRS"),
    ("latitude", "Coordinates: latitude"),
    ("longitude", "Coordinates: longitude"),
    ("planned_start", "Planned start date"),
    ("planned_end", "Planned end date"),
    ("actual_start", "Actual start date"),
    ("actual_end", "Actual end date"),
    ("reason", "Reason / narrative"),
    ("comments", "Comments"),
    ("attachments", "Attachment file names"),
    ("org_report_id", "Organisation's own report id"),
    ("ignore", "Not sent to IMSMA"),
]
DATATYPES = [
    ("text", "Text"),
    ("integer", "Whole number"),
    ("number", "Number"),
    ("date", "Date"),
    ("list", "One value from a list"),
    ("multi", "Several values from a list"),
    ("organisation", "Organisation"),
]


class DmaFrTemplate(models.Model):
    _name = "dma.fr.template"
    _description = "Field report template"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    kind = fields.Selection(KINDS, required=True)
    active = fields.Boolean(default=True)
    imsma_form_name = fields.Char("IMSMA form", required=True,
                                  help="Exact name of the field report form in IMSMA. Its GUID and current version "
                                       "are taken from the IMSMA data at export time.")
    form_id = fields.Many2one("dma.fr.ref.form", "Current IMSMA version", compute="_compute_form_id")
    checked_form_version = fields.Integer(
        "Mapping checked against version",
        help="The IMSMA form version this column list was last checked against. When IMSMA publishes a newer "
             "version, a warning asks a manager to look at the list again.")
    form_version_warning = fields.Char(compute="_compute_form_id")
    object_element = fields.Char("maXML activity element", help="e.g. MREActivity")
    sheet_name = fields.Char("Sheet", required=True, default="Sheet1")
    header_row = fields.Integer("First header row", default=1, required=True)
    header_rows = fields.Integer("Header rows", default=1, required=True,
                                help="2 when a group header (e.g. 'Location') sits over sub-headers (e.g. 'Province').")
    first_data_row = fields.Integer("First data row", default=2, required=True)
    object_id_type = fields.Char("IMSMA id type of the object", help="e.g. Education, LOC (IMSMA localidtype name)")
    object_id_prefix = fields.Char("Object id prefix", help="e.g. 'Education' gives Education-CI-75322")
    report_id_prefix = fields.Char("Report id prefix", help="e.g. 'FR-MRE' gives FR-MRE-CI-75322")
    field_ids = fields.One2many("dma.fr.template.field", "template_id", "Columns", copy=True)
    field_count = fields.Integer(compute="_compute_field_count")
    note = fields.Html(translate=True)

    @api.depends("imsma_form_name", "checked_form_version")
    def _compute_form_id(self):
        Form = self.env["dma.fr.ref.form"]
        for rec in self:
            form = Form.latest(rec.imsma_form_name) if rec.imsma_form_name else Form
            rec.form_id = form
            rec.form_version_warning = False
            if not form:
                rec.form_version_warning = _("No active IMSMA form named '%s' in the IMSMA data.", rec.imsma_form_name)
            elif rec.checked_form_version and form.version_num > rec.checked_form_version:
                rec.form_version_warning = _(
                    "IMSMA now has version %(new)s of this form; the columns were checked against version %(old)s. "
                    "Check the list, then set the checked version to %(new)s.",
                    new=form.version, old=rec.checked_form_version)

    def _compute_field_count(self):
        for rec in self:
            rec.field_count = len(rec.field_ids)

    def fields_by_role(self):
        out = {}
        for f in self.field_ids:
            out.setdefault(f.role, self.env["dma.fr.template.field"])
            out[f.role] |= f
        return out


class DmaFrTemplateField(models.Model):
    _name = "dma.fr.template.field"
    _description = "Column of a field report template"
    _order = "template_id, sequence, id"

    template_id = fields.Many2one("dma.fr.template", required=True, index=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char("Label", required=True, translate=True)
    headers = fields.Text(
        "Column headers", required=True,
        help="One header per line. A column whose header matches any line is used. Write 'Group / Sub' for a "
             "column under a group header. Case, spaces, punctuation, * and # are ignored; Arabic headers work.")
    role = fields.Selection(ROLES, required=True, default="cdf")
    datatype = fields.Selection(DATATYPES, required=True, default="text")
    required = fields.Boolean()
    max_length = fields.Integer(help="Warn when the text is longer (0 = no limit).")
    cdf_id_text = fields.Char("IMSMA CDF id", help="Exactly as in IMSMA, typos and spaces included.")
    cdf_guid = fields.Char("IMSMA CDF GUID")
    cdf_ref_id = fields.Many2one("dma.fr.ref.cdf", "Custom field in IMSMA data", compute="_compute_cdf_ref")
    cdf_missing = fields.Boolean(compute="_compute_cdf_ref")
    fixed_options = fields.Text("Allowed values",
                                help="One per line. When empty, list values are checked against the values IMSMA "
                                     "has stored for the custom field.")
    help_text = fields.Char("Help for users", translate=True)

    @api.depends("cdf_guid", "cdf_id_text")
    def _compute_cdf_ref(self):
        Cdf = self.env["dma.fr.ref.cdf"].with_context(active_test=False)
        for rec in self:
            ref = Cdf.search([("cdf_id", "=", rec.cdf_guid)], limit=1) if rec.cdf_guid else Cdf
            rec.cdf_ref_id = ref
            rec.cdf_missing = bool(rec.role in ("cdf", "subcontractor", "task_dossier", "org_report_id")
                                   and rec.cdf_guid and not ref and Cdf.search_count([], limit=1))

    def header_list(self):
        return [h.strip() for h in (self.headers or "").splitlines() if h.strip()]

    def allowed_options(self):
        """[(value, usage)] the field accepts, preferred first."""
        self.ensure_one()
        if self.fixed_options:
            return [(v.strip(), 0) for v in self.fixed_options.splitlines() if v.strip()]
        if self.cdf_ref_id:
            opts = self.cdf_ref_id.option_ids.filtered("active")
            return [(o.value, o.usage) for o in opts.sorted(lambda o: (not o.is_preferred, -o.usage))]
        return []

    @property
    def mapping_scope(self):
        """Key under which learned value mappings are stored: shared by every template using the same CDF."""
        if self.role == "organisation" or self.role == "subcontractor":
            return "organisation"
        return self.cdf_guid or f"field:{self.id}"


class DmaFrValueMap(models.Model):
    _name = "dma.fr.value.map"
    _description = "Value translation (file text -> IMSMA value)"
    _order = "scope, source_value"
    _rec_name = "source_value"

    scope = fields.Char(required=True, index=True,
                        help="CDF GUID of the list field, or 'organisation'. A mapping applies to that field only.")
    scope_label = fields.Char("Field", compute="_compute_scope_label")
    source_value = fields.Char("Text in the file", required=True)
    source_norm = fields.Char(index=True)
    target_value = fields.Char("IMSMA value", required=True,
                               help="The IMSMA list value, or the IMSMA GUID of the organisation.")
    origin = fields.Selection([("seeded", "Built in"), ("learned", "Learned from a fix"), ("manual", "Manual")],
                              default="manual", required=True)
    active = fields.Boolean(default=True)

    _uniq = models.Constraint("unique(scope, source_norm)", "This text already has a mapping for this field.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["source_norm"] = text.norm(vals.get("source_value"))
        return super().create(vals_list)

    def write(self, vals):
        if "source_value" in vals:
            vals["source_norm"] = text.norm(vals["source_value"])
        return super().write(vals)

    def _compute_scope_label(self):
        Field = self.env["dma.fr.template.field"]
        for rec in self:
            if rec.scope == "organisation":
                rec.scope_label = _("Organisation")
            else:
                f = Field.search([("cdf_guid", "=", rec.scope)], limit=1)
                rec.scope_label = f.name if f else rec.scope
