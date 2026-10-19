# Part of DMA Field Reports. See LICENSE file for full copyright and licensing details.
{
    "name": "DMA Field Reports",
    "summary": "Check and fix operator field data in Odoo, then export it as IMSMA NG field reports",
    "description": """
Directorate of Mine Action - Field Reports
==========================================

Replaces the iMMAP "Excel to IMSMA" Access tool. DMA and RMAC staff upload the
operators' Excel files, see every problem at once, fix them in place, and
download one zip of maXML 2.0 field reports (with attachments) for the IMSMA NG
Workbench import. IMSMA NG stays the system of record.

IMSMA reference data (forms, custom fields and their values, gazetteer,
locations, organisations, ids in use) comes either from a read-only
connection to the IMSMA database or from a package built from an IMSMA backup.
Odoo never writes to IMSMA.
""",
    "version": "19.0.0.1.0",
    "category": "Services",
    "license": "LGPL-3",
    "author": "Directorate of Mine Action",
    "depends": ["base", "mail", "web"],
    "external_dependencies": {"python": ["openpyxl", "lxml"]},
    "data": [
        "security/dma_field_reports_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/dma_fr_office_data.xml",
        "data/dma_fr_template_eore.xml",
        "data/dma_fr_template_location.xml",
        "data/dma_fr_value_map_data.xml",
        "data/ir_cron_data.xml",
        "views/dma_fr_batch_views.xml",
        "views/dma_fr_cell_views.xml",
        "views/dma_fr_template_views.xml",
        "views/dma_fr_source_views.xml",
        "views/dma_fr_ref_views.xml",
        "wizards/dma_fr_fix_wizard_views.xml",
        "views/dma_fr_menus.xml",
    ],
    "installable": True,
    "application": True,
}
