"""Generate data/dma_fr_template_eore.xml (the EORE column list) from one table.

Sources: the DMA EORE Template English (Sep 2026) headers, the Access tool's MRE
mapping (analysis/mappings/MRE_MDC.csv) and IMSMA's customdefinedfield (GUIDs
checked against the 2025-03-02 backup: the old tool's Magazin GUID had a typo,
fixed here; 'Funded by' keeps the CDF_ID text IMSMA accepted for years).
"""
from xml.sax.saxutils import escape

# (label, headers (| separated), role, datatype, required, cdf_id_text, cdf_guid, extra)
COLS = [
    ("Funded by", "Funded by", "cdf", "list", True,
     "MRE.SINGLE_SELECT.cdf_project_funded_by_international", "c0a8-cc01-160e6ac65d2-2fbf5fc1-1d-ab3", {}),
    ("Date of report", "Date of report", "report_date", "date", True,
     "MRE.DATE.DataEntryDate", "c0a8-be01-14a576cd5ab-d47cc197-7-fb6d", {}),
    ("Reported by", "Reported by", "reporting_person", "text", True, "", "", {}),
    ("Position", "Position", "reporting_position", "text", True, "", "", {}),
    ("Organisation", "Organization|Organisation", "organisation", "organisation", True, "", "", {}),
    ("Sub-contractor", "Sub-contractor|Subcontractor", "subcontractor", "organisation", False,
     "MRE.ORGANISATION.cdf_subcontractor", "c0a8-0a03-18616f9ca4c-b42bee9e-11-d6a", {}),
    ("Task dossier id", "Task dossier ID|Task dossier", "task_dossier", "text", True,
     "MRE.TEXT_FIELD.cdf_task_dossier", "7f00-0001-163eba88097-435586b2-12-b16", {}),
    ("Province", "Location / Province|Province", "province", "text", True, "", "", {}),
    ("District", "Location / District|District", "district", "text", True, "", "", {}),
    ("Sub-district", "Location / Subdistrict|Subdistrict|Sub-district", "subdistrict", "text", False, "", "", {}),
    ("City / town / village", "Location / City/Town/Village|City/Town/Village|City", "city", "text", True, "", "", {}),
    ("Location name", "Location / Location name|Location name", "location_name", "text", False,
     "MRE.TEXT_FIELD.location_name", "c0a8-cc01-160d646a477-e4890c7a-6-6f46", {}),
    ("MGRS", "Location / MGRS|MGRS", "mgrs", "text", False, "", "", {}),
    ("Latitude", "Location / Lat|Lat|Latitude", "latitude", "number", False, "", "", {}),
    ("Longitude", "Location / Long|Long|Longitude", "longitude", "number", False, "", "", {}),
    ("Planned start date", "Planned start date", "planned_start", "date", False, "", "", {}),
    ("Planned end date", "Planned end date", "planned_end", "date", False, "", "", {}),
    ("Actual start date", "Actual start date", "actual_start", "date", True, "", "", {}),
    ("Actual end date", "Actual end date", "actual_end", "date", True, "", "", {}),
    ("Activity type", "Activity type", "cdf", "multi", False,
     "MRE.MULTI_SELECT.Supported Activity type:", "c0a8-00a2-1307eaec3d1-37d76cff-6c-66b", {}),
    ("Awareness type", "Awareness type for impacted communities", "cdf", "multi", False,
     "MRE.MULTI_SELECT.CDF-Awareness type for impacted communities from", "c0a8-429c-1524042ff34-acafed6d-e89-45", {}),
    ("EORE type", "EORE type|MRE type", "cdf", "list", False,
     "MRE.SINGLE_SELECT.MRE Type", "7f00-0001-13f7a2fa1c2-3963ba9f-39-b37", {}),
    ("EORE sub-type", "EORE Sub Type|MRE Sub Type", "cdf", "list", False,
     "MRE.SINGLE_SELECT.MRE SubType", "7f00-0001-13f7a2f797a-7f9d8df5-b-99ae", {}),
    ("Folders", "Number of material distribution / Folders|Folders", "cdf", "integer", False,
     "MRE.TEXT_FIELD.CDF-Folders", "c0a8-429c-15240426832-2130ec27-e87-aa", {}),
    ("Bags", "Number of material distribution / Bags|Bags", "cdf", "integer", False,
     "MRE.NUMBER.Bags", "c0a8-00a2-1307eb6ceb7-8e95ba4-7a-a5a4", {}),
    ("Magazines", "Number of material distribution / Magazin|Magazin|Magazines", "cdf", "integer", False,
     "MRE.TEXT_FIELD.CDF-K_Magazin", "c0a8-429c-15240423292-575ac7de-e86-ec", {}),
    ("Posters", "Number of material distribution / Posters|Posters", "cdf", "integer", False,
     "MRE.NUMBER.CDF-Posters", "c0a8-00a2-1307eb6ad26-824766f4-78-e7f", {}),
    ("Football", "Number of material distribution / Football|Football", "cdf", "integer", False,
     "MRE.TEXT_FIELD.CDF-Football", "c0a8-429c-1524041f14e-8e5c9557-e84-12", {}),
    ("School supplement", "Number of material distribution / School Supplement|School Supplement", "cdf", "integer",
     False, "MRE.TEXT_FIELD.CDF-School Supplement", "c0a8-429c-15240429e21-ac26f53a-e88-51", {}),
    ("T-shirts", "Number of material distribution / T-Shirts|T-Shirts", "cdf", "integer", False,
     "MRE.NUMBER.T-Shirts", "c0a8-00a2-1307eb6df23-278df5b0-7b-83e", {}),
    ("Snake and ladder game", "Number of material distribution / Snake And Ladder Game|Snake And Ladder Game", "cdf",
     "integer", False, "MRE.TEXT_FIELD.CDF-K_Snake And Ladder Game", "c0a8-429c-15240420c0e-af838b06-e85-43", {}),
    ("Warning signs (flexes)", "Number of material distribution / Warning Signs(Flexes)|Warning Signs(Flexes)", "cdf",
     "integer", False, "MRE.NUMBER.cdf_warning_signs_flexes", "c0a8-0a03-18616f9d624-a36660bb-12-92e", {}),
    ("Booklets", "Number of material distribution / Booklets|Booklets", "cdf", "integer", False,
     "MRE.NUMBER.CDF-Booklets", "c0a8-00a2-1307eb6ba93-aa1c77c7-79-9c3", {}),
    ("Leaflets", "Number of material distribution / Leaflet|Leaflet|Leaflets", "cdf", "integer", False,
     "MRE.NUMBER.cdf_leaflet", "7f00-0001-1684b591ec6-8192abd0-c-2def", {}),
    ("Other material", "Number of material distribution / Others", "cdf", "text", False,
     "MRE.TEXT_FIELD.CDF-Others", "c0a8-00a2-1307eb66129-93304ab1-72-4aa", {}),
    ("Narrative and reasons", "Narrative of the project and Reasons for EORE activity|Narrative", "reason", "text",
     False, "", "", {}),
    ("Children (5-12) male", "Audience by Gender with Age Info / Children (5-12) Male|Children (5-12) Male", "cdf",
     "integer", False, "MRE.NUMBER.Children (5-12) Male", "c0a8-00a2-1307eb69ece-b2845e67-77-e8d", {}),
    ("Children (5-12) female", "Audience by Gender with Age Info / Children (5-12) Female|Children (5-12) Female",
     "cdf", "integer", False, "MRE.NUMBER.Children (5-12) Female", "c0a8-00a2-1307eb6eb19-fe78d05b-7c-216", {}),
    ("Youth (13-18) male", "Audience by Gender with Age Info / Youth (13-18) Male|Youth (13-18) Male", "cdf",
     "integer", False, "MRE.NUMBER.Youth (13-18) Male", "c0a8-00a2-1307eb67aea-d21a92af-74-705", {}),
    ("Youth (13-18) female", "Audience by Gender with Age Info / Youth (13-18) Female|Youth (13-18) Female", "cdf",
     "integer", False, "MRE.NUMBER.Youth (13-18) Female", "c0a8-00a2-1307eb69086-4a9eece4-76-15b", {}),
    ("Adult (19+) male", "Audience by Gender with Age Info / Adult (19+) Male|Adult (19+) Male", "cdf", "integer",
     False, "MRE.NUMBER.Adult (19+) Male", "c0a8-00a2-1307eb68599-a7300e06-75-e58", {}),
    ("Adult (19+) female", "Audience by Gender with Age Info / Adult (19+) Female|Adult (19+) Female", "cdf",
     "integer", False, "MRE.NUMBER.Adult (19+) Female", "c0a8-00a2-1307eb66e58-fc4928ad-73-7ac", {}),
    ("Audience type", "Audience type", "cdf", "list", False,
     "MRE.SINGLE_SELECT.Audience Type", "7f00-0001-13f7a2f8f6a-74bbbd46-28-907", {}),
    ("Comment", "Comment|Comments", "comments", "text", False, "", "", {}),
    ("Organisation's report id", "Org Internal Report ID", "org_report_id", "text", False,
     "MRE.TEXT_FIELD.org_internal_report_id", "7f00-0001-168474668b0-39469722-11-7cc", {}),
    ("MAC owner", "MAC Owner", "cdf", "list", True,
     "MRE.SINGLE_SELECT.mac_owner", "c0a7-f58e-1773eacedb7-ef3a9ab4-10-dff", {}),
    ("Remote risk education", "Type of Remote Risk Education|Remote Risk Education", "cdf", "multi", False,
     "MRE.MULTI_SELECT.remote_risk_education", "c0a7-f58e-17744186186-c50dcf38-a-7b29", {}),
    ("Audio method", "Audio Activity / Audio Method Name|Audio Method Name", "cdf", "text", False,
     "MRE.TEXT_FIELD.audio_method_name", "c0a7-f58e-177441ad76e-3069cf02-f-43dd", {}),
    ("Audio broadcasts", "Audio Activity / Number of Audio Broadcasting|Number of Audio Broadcasting", "cdf",
     "integer", False, "MRE.NUMBER.audio_broadcast_number", "c0a7-f58e-177441e424e-4c6cff4-11-3f90", {}),
    ("Visual method", "Visual Activity / Visual Method Name|Visual Method Name", "cdf", "text", False,
     "MRE.TEXT_FIELD.visual_method_name", "c0a7-f58e-177441a615e-b3e8f04c-e-a24a", {}),
    ("Visual broadcasts", "Visual Activity / Number of Visual Broadcasting|Number of Visual Broadcasting", "cdf",
     "integer", False, "MRE.NUMBER.visual_broadcast_number", "c0a7-f58e-177441dd216-97c316d8-10-48e", {}),
    ("SMS sent", "Number of SMS", "cdf", "integer", False,
     "MRE.NUMBER.sms_number", "c0a7-f58e-177441f999e-f75a7727-12-88b", {}),
    ("QA DMA representative 1", "QA DMA Representative 1", "cdf", "text", False,
     "MRE.TEXT_FIELD.qa_dma_representative1", "c0a7-f58e-1773ea40657-21222ff4-e-ff37", {}),
    ("QA visit date 1", "QA Visit Date 1", "cdf", "date", False,
     "MRE.DATE.qa_visit_date", "c0a7-f58e-1773ea32a65-f5c441dd-c-1732", {}),
    ("QA verification date 1", "QA Verification Date 1", "cdf", "date", False,
     "MRE.DATE.qa_verification_date", "c0a7-f58e-1773ea376b4-30bb190-d-93de2", {}),
    ("QA DMA representative 2", "QA DMA Representative 2", "cdf", "text", False,
     "MRE.TEXT_FIELD.qa_dma_representative2", "c0a7-f58e-1773ea4638e-47b27625-f-bef2", {}),
    ("QA visit date 2", "QA Visit Date 2", "cdf", "date", False,
     "MRE.DATE.qa_visit_date2", "c0a7-f58e-1774346bbf0-e336bccf-27-4b8", {}),
    ("QA verification date 2", "QA Verification Date 2", "cdf", "date", False,
     "MRE.DATE.qa_verification_date2", "c0a7-f58e-17743467dc8-ffc393cd-26-fcb", {}),
    ("Attachments", "Attachments", "attachments", "text", False, "", "", {}),
    ("IM date", "im_date|IM date", "cdf", "date", False,
     "MRE.DATE.im_date", "7f00-0001-16846f04502-1c81925b-c-8cbd", {}),
    ("Received date", "received_date|Received date", "cdf", "date", False,
     "MRE.DATE.received_date", "7f00-0001-168474b90a9-928c1d96-14-742", {}),
    ("IMSMA location GUID", "location_guid", "location_guid", "text", False, "", "", {}),
    ("Received by", "Received By", "cdf", "text", False,
     "MRE.TEXT_FIELD.received_by", "7f00-0001-1684b6f0707-670b5011-1-b0b8", {}),
    ("Received by position", "Received by Position", "cdf", "text", False,
     "MRE.TEXT_FIELD.received_by_position", "7f00-0001-1684b6f5f6e-e81b773f-2-46c3", {}),
]


def main(path):
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           "<!-- Generated by tools_dev/gen_eore_template.py: edit there, or in Odoo after install. -->",
           '<odoo noupdate="1">',
           '    <record id="template_eore" model="dma.fr.template">',
           '        <field name="name">EORE (DMA Excel template)</field>',
           '        <field name="sequence">10</field>',
           '        <field name="kind">eore</field>',
           '        <field name="imsma_form_name">DMA Explosive Ordnance Risk Education Form</field>',
           '        <field name="checked_form_version">23</field>',
           '        <field name="object_element">MREActivity</field>',
           '        <field name="sheet_name">EORE</field>',
           '        <field name="header_row">4</field>',
           '        <field name="header_rows">2</field>',
           '        <field name="first_data_row">6</field>',
           '        <field name="object_id_type">Education</field>',
           '        <field name="object_id_prefix">Education</field>',
           '        <field name="report_id_prefix">FR-MRE</field>',
           '        <field name="note"><![CDATA[<p>The "DMA EORE Template English" workbook (sheet EORE, headers on rows 4-5, '
           'data from row 6). Columns are found by their header text, so they may be moved.</p>]]></field>',
           "    </record>"]
    for i, (label, headers, role, dt, req, cdf_text, cdf_guid, _extra) in enumerate(COLS, start=1):
        rid = "eore_f%02d" % i
        out.append(f'    <record id="{rid}" model="dma.fr.template.field">')
        out.append('        <field name="template_id" ref="template_eore"/>')
        out.append(f'        <field name="sequence">{i * 10}</field>')
        out.append(f'        <field name="name">{escape(label)}</field>')
        out.append(f'        <field name="headers">{escape(chr(10).join(headers.split("|")))}</field>')
        out.append(f'        <field name="role">{role}</field>')
        out.append(f'        <field name="datatype">{dt}</field>')
        out.append(f'        <field name="required" eval="{req}"/>')
        if cdf_text:
            out.append(f'        <field name="cdf_id_text">{escape(cdf_text)}</field>')
            out.append(f'        <field name="cdf_guid">{cdf_guid}</field>')
        out.append("    </record>")
    out.append("</odoo>")
    with open(path, "w", encoding="utf8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print(f"{len(COLS)} columns -> {path}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
