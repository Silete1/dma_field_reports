"""Build IMSMA NG maXML 2.0 MineActionFieldReport documents with lxml (always escaped).

The element order and literal values follow what the iMMAP Access tool sent
and IMSMA NG 6 accepted for about 14,000 EORE reports (2019-2025), with its
bugs left out (see imsma-importer/analysis/vba-review.md).
"""
import datetime
import mimetypes

from lxml import etree

NS = "maXMLArtifactLibrary"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
NSMAP = {"ma": NS, "xsd": "http://www.w3.org/2001/XMLSchema", "xsi": XSI}
CDF_DATATYPE = {  # IMSMA cdf_datatype -> maXML DataType label
    "TEXT_FIELD": "Text", "NUMBER": "Numeric", "DATE": "Date", "SINGLE_SELECT": "List",
    "MULTI_SELECT": "List", "ORGANISATION": "ORGANISATION",
}
IRAQ_COUNTRY_NAME = "Iraq"


def _sub(parent, tag, text=None, **attrs):
    el = etree.SubElement(parent, tag, {k: str(v) for k, v in attrs.items() if v is not None})
    if text is not None:
        el.text = str(text)
    return el


def _dt(value, time="00:00:00"):
    """date/datetime/'YYYY-MM-DD' -> 'YYYY-MM-DDThh:mm:ss'."""
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(value, datetime.date):
        return f"{value.isoformat()}T{time}"
    return f"{str(value)[:10]}T{time}"


def _d(value):
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _num(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def datatype_of(cdf_id_text, cdf_datatype=None):
    """maXML DataType for a CDF, from IMSMA's datatype or from the id ('MRE.NUMBER.Bags')."""
    if cdf_datatype in CDF_DATATYPE:
        return CDF_DATATYPE[cdf_datatype]
    parts = (cdf_id_text or "").split(".")
    return CDF_DATATYPE.get(parts[1] if len(parts) > 2 else "", "Text")


class Report:
    """One MineActionFieldReport file."""

    def __init__(self, form_guid, form_name, form_version, report_id, fieldreport_guid, creator, now=None):
        self.now = now or datetime.datetime.now().replace(microsecond=0)
        self.root = etree.Element(f"{{{NS}}}MineActionFieldReport", nsmap=NSMAP)
        self.root.set(f"{{{XSI}}}schemaLocation", f"{NS} maXMLSchema.xsd")
        head = _sub(self.root, "DocumentHeader")
        _sub(head, "DocumentName", "MineActionFieldReport")
        _sub(head, "SchemaVersion", "maXML 2.0")
        info = _sub(head, "FileCreationInfo")
        _sub(info, "FileCreationDateTime", _dt(self.now))
        _sub(info, "FileCreator", creator or "DMA Field Reports")
        crs = _sub(head, "DocumentCoordinateReferenceSystem")
        _sub(crs, "CoordinateSystem", "Geodetic Latitude Longitude", originalValue="WGS 1984")
        _sub(crs, "Datum", "WGS-84")
        self.fr = _sub(self.root, "FieldReport")
        self.info = _sub(self.fr, "FieldReportInfo", reportID=report_id, reportGUID=form_guid,
                         fieldReportGUID=fieldreport_guid)
        _sub(self.info, "FieldReportName", form_name)
        _sub(self.info, "Version", form_version)

    # -- FieldReportInfo ---------------------------------------------------
    def report_info(self, reporting_person=None, reporting_position=None, reporting_org=None,
                    reporting_date=None, verified_by=None):
        if reporting_person:
            _sub(self.info, "ReportingPerson", reporting_person)
        if reporting_position:
            _sub(self.info, "ReportingPosition", reporting_position)
        _sub(self.info, "ReportingOrg", reporting_org or "Directorate for Mine Action Iraq")
        if reporting_date:
            _sub(self.info, "ReportingDate", _d(reporting_date))
        _sub(self.info, "VerifyingDate", _d(self.now))
        if verified_by:
            _sub(self.info, "VerifiedBy", verified_by)
        _sub(self.info, "ReportCompletedDate", _d(self.now))

    # -- attachments (FieldReport level, before the activity) -----------------
    def attachment(self, guid, file_name, size, enterer, mime=None):
        att = _sub(self.fr, "Attachment")
        _sub(att, "guid", guid)
        _sub(att, "fileName", file_name)
        _sub(att, "mimeType", mime or mimetypes.guess_type(file_name)[0] or "application/octet-stream")
        _sub(att, "fileSize", size)
        _sub(att, "dataEntryDate", _dt(self.now))
        _sub(att, "dataEnterer", enterer or "DMA Field Reports")
        _sub(att, "fileData")
        return att

    # -- activity helpers ----------------------------------------------------
    def activity(self, element, ident_element, guid, original_id):
        act = _sub(self.fr, element, displayPosition=0)
        ident = _sub(act, ident_element)
        _sub(ident, "GUID", guid)
        _sub(ident, "OriginalID", original_id)
        return act

    @staticmethod
    def organisation(parent, element, name, guid, localid):
        org = _sub(parent, element)
        _sub(org, "OrganisationName", name)
        oid = _sub(org, "OrganisationID")
        _sub(oid, "GUID", guid)
        _sub(oid, "OriginalID", localid)
        return org

    @staticmethod
    def cdf(parent, cdf_id, cdf_guid, value, datatype):
        """value: str/number/date, a list (multi-select), or a dict organisation {name, guid, localid}."""
        el = _sub(parent, "CDF", displayPosition=0)
        _sub(el, "CDF_ID", cdf_id)
        _sub(el, "CDF_GUID", cdf_guid)
        if datatype == "ORGANISATION":
            v = _sub(el, "Value")
            _sub(v, "OrganisationName", value["name"])
            oid = _sub(v, "OrganisationID")
            _sub(oid, "GUID", value["guid"])
            _sub(oid, "OriginalID", value["localid"])
        elif isinstance(value, (list, tuple)):
            for item in value:
                _sub(el, "Value", item)
        elif datatype == "Date":
            _sub(el, "Value", _dt(value, "15:00:00"))
        elif datatype == "Numeric":
            _sub(el, "Value", _num(value))
        else:
            _sub(el, "Value", value)
        _sub(el, "DataType", datatype)
        return el

    @staticmethod
    def point(parent, guid, lat=None, lon=None, mgrs=None):
        """One reference point: decimal degrees when known, else MGRS."""
        geo = _sub(parent, "GeospatialInfo")
        crs = _sub(geo, "CoordinateReferenceSystem")
        if lat is not None and lon is not None:
            _sub(crs, "CoordinateSystem", "WGS 1984", originalValue="WGS 1984")
            _sub(crs, "CoordinateFormat", "Decimal Degrees", originalValue="Decimal Degrees")
            sp = _sub(geo, "SinglePoint", GUID=guid, LocalID="Point_1", originalXcoord=f"{lon:.8f}",
                      originalYcoord=f"{lat:.8f}", userInputFormat="X and Y")
            xy = _sub(sp, "XY")
            _sub(xy, "X", f"{lon:.8f}")
            _sub(xy, "Y", f"{lat:.8f}")
            _sub(sp, "TypeOfPoint", "Reference Point")
        else:
            _sub(crs, "CoordinateSystem", "MGRS", originalValue="MGRS")
            _sub(crs, "CoordinateFormat", "MGRS", originalValue="MGRS")
            sp = _sub(geo, "SinglePoint", GUID=guid, LocalID="Point_1", originalXcoord="", originalYcoord="",
                      userInputFormat="MGRS")
            _sub(sp, "MGRS", mgrs)
            _sub(sp, "TypeOfPoint", "Benchmark")
        _sub(sp, "PointName", "Point - 1")
        _sub(sp, "PointNumber", 1)
        return geo

    @staticmethod
    def duration(parent, element, actual=(None, None), planned=(None, None)):
        if not any(actual) and not any(planned):
            return None
        dur = _sub(parent, element)
        if any(actual):
            a = _sub(dur, "ActualDuration")
            if actual[0]:
                _sub(a, "StartDate", _dt(actual[0]))
            if actual[1]:
                _sub(a, "EndDate", _dt(actual[1]))
        if any(planned):
            p = _sub(dur, "PlannedDuration")
            if planned[0]:
                _sub(p, "StartDate", _dt(planned[0]))
            if planned[1]:
                _sub(p, "EndDate", _dt(planned[1]))
        return dur

    @staticmethod
    def location_association(parent, guid, localid):
        a = _sub(parent, "Association", type="NEW")
        ident = _sub(a, "AssociationIdentification")
        _sub(ident, "GUID", guid)
        _sub(ident, "OriginalID", localid)
        target = _sub(a, "TargetInformation", object="LOCATION")
        _sub(target, "Name", localid)
        return a

    def location(self, guid, original_id, name, chain):
        """A Location object. chain: [(guid, name, level_label)] from city up to province."""
        loc = _sub(self.fr, "Location", displayPosition=0)
        ident = _sub(loc, "LocationIdentification")
        _sub(ident, "GUID", guid)
        _sub(ident, "OriginalID", original_id)
        _sub(loc, "LocationName", name)
        parent = loc
        for i, (g, n, level) in enumerate(chain):
            el = _sub(parent, "AdministrativeArea" if i == 0 else "ParentAdministration", administrativeAreaID=g)
            _sub(el, "AdministrativeName", n)
            _sub(el, "AdministrativeLevel", level)
            parent = el
        _sub(loc, "CreationDateTime", _dt(self.now))
        return loc

    # -- output --------------------------------------------------------------
    def tostring(self, encoding="UTF-16"):
        return etree.tostring(self.root, xml_declaration=True, encoding=encoding, pretty_print=True)


def validate(xml_bytes, xsd_bytes):
    """Validate against maXMLSchema.xsd. Returns a list of error strings (empty = valid)."""
    schema = etree.XMLSchema(etree.fromstring(xsd_bytes))
    doc = etree.fromstring(xml_bytes)
    if schema.validate(doc):
        return []
    return [f"line {e.line}: {e.message}" for e in schema.error_log]
