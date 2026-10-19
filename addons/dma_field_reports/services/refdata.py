"""IMSMA NG reference data: one package format, built from a backup or read live.

Package (zip): manifest.json + UTF-8 CSV files with a header row.

    forms.csv          guid, name, version, published_on, active
    cdfs.csv           cdf_id, name, datatype, entity, label, active
    cdf_options.csv    cdf_id, value, usage          (values stored for list CDFs, with counts)
    places.csv         guid, name, level, parent_guid
    place_aliases.csv  guid, alias
    locations.csv      guid, localid, name, place_guid, active
    organisations.csv  guid, localid, name, active
    tasks.csv          guid, localid
    id_usage.csv       prefix, max_number            (highest number in use per id prefix)
    idtypes.csv        name, next_number             (live only: IMSMA's own counters)
    reports.csv        guid, localid, form_guid, status

Pure Python (stdlib); psycopg2 only for the live reader. Run as a script to
build a package from a backup (see tools/imsma_ref_extract.py).
"""
import csv
import datetime
import hashlib
import io
import json
import os
import re
import zipfile

FORMAT = "dma-fr-reference"
FORMAT_VERSION = 1
FILES = {
    "forms.csv": ["guid", "name", "version", "published_on", "active"],
    "cdfs.csv": ["cdf_id", "name", "datatype", "entity", "label", "active"],
    "cdf_options.csv": ["cdf_id", "value", "usage"],
    "places.csv": ["guid", "name", "level", "parent_guid", "lat", "lon"],
    "place_aliases.csv": ["guid", "alias"],
    "locations.csv": ["guid", "localid", "name", "place_guid", "active", "lat", "lon"],
    "organisations.csv": ["guid", "localid", "name", "active"],
    "tasks.csv": ["guid", "localid"],
    "id_usage.csv": ["prefix", "max_number"],
    "idtypes.csv": ["name", "next_number"],
    "reports.csv": ["guid", "localid", "form_guid", "status"],
}
LIST_DATATYPES = ("SINGLE_SELECT", "MULTI_SELECT")
# tables whose local ids tell which numbers are taken, per prefix
ID_TABLES = {
    "mre": "mre_localid", "location": "location_localid", "qa": "localid", "hazard": "hazard_localid",
    "hazreduc": "hazreduc_localid", "victim": "victim_localid", "accident": "accident_localid",
    "fieldreport": "fieldreport_localid",
}
_TRAILING_NUMBER = re.compile(r"^(.*?)(\d+)\s*$")
BS = "\\"


# ---------------------------------------------------------------- COPY reading

def _unescape(value):
    if value == BS + "N":
        return None
    if BS not in value:
        return value
    out, i = [], 0
    while i < len(value):
        c = value[i]
        if c == BS and i + 1 < len(value):
            n = value[i + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v"}.get(n, n))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _copy_header(line):
    # COPY public.table (a, b, "c") FROM stdin;
    m = re.match(r"COPY\s+(?:\w+\.)?(\w+)\s*\((.*)\)\s+FROM\s+stdin;", line)
    if not m:
        return None, None
    cols = [c.strip().strip('"') for c in m.group(2).split(",")]
    return m.group(1), cols


def _iter_copy_lines(lines, cols):
    for line in lines:
        line = line.rstrip("\r\n")
        if line == BS + ".":
            return
        parts = line.split("\t")
        if len(parts) != len(cols):
            continue
        yield {c: _unescape(p) for c, p in zip(cols, parts)}


class BackupSource:
    """Rows of IMSMA tables from a pg_dump `Dump.sql` or a folder of `copy_<table>.txt` extracts."""

    def __init__(self, path):
        self.path = path
        self.is_folder = os.path.isdir(path)

    def tables(self, wanted):
        """Yield (table, row) for the wanted tables, in file order. One pass."""
        wanted = set(wanted)
        if self.is_folder:
            for table in sorted(wanted):
                fn = os.path.join(self.path, f"copy_{table}.txt")
                if not os.path.exists(fn):
                    continue
                with open(fn, encoding="utf8", newline="") as f:
                    name, cols = _copy_header(f.readline())
                    for row in _iter_copy_lines(f, cols):
                        yield table, row
            return
        with open(self.path, encoding="utf8", errors="replace", newline="") as f:
            for line in f:
                if not line.startswith("COPY "):
                    continue
                table, cols = _copy_header(line)
                if table in wanted:
                    for row in _iter_copy_lines(f, cols):
                        yield table, row
                else:
                    for raw in f:  # skip the block without parsing it
                        if raw.rstrip("\r\n") == BS + ".":
                            break


# ---------------------------------------------------------------- building

def _bool(v):
    return "true" if str(v).lower() in ("t", "true", "1") else "false"


def _level_name(level):
    level = (level or "").strip().lower().replace("-", "").replace(" ", "")
    return {"subdistrict": "subdistrict", "city": "city", "district": "district",
            "province": "province", "country": "country"}.get(level, level)


def _box_centre(r):
    """Centre of a gazetteer node's bounding box, or (None, None)."""
    try:
        y = (float(r["upperlefty"]) + float(r["lowerrighty"])) / 2
        x = (float(r["upperleftx"]) + float(r["lowerrightx"])) / 2
    except (TypeError, ValueError, KeyError):
        return None, None
    return y, x


def _coord(v):
    """Keep only plausible numbers ('' otherwise), rounded to ~1 m."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    return "" if f == 0 or abs(f) > 180 else f"{f:.6f}"


def _track_id(usage, localid):
    m = _TRAILING_NUMBER.match((localid or "").strip())
    if m:
        prefix, number = m.group(1), int(m.group(2))
        if number > usage.get(prefix, -1):
            usage[prefix] = number


def build_from_backup(path, dump_date=None):
    """Read a backup and return {file name: [rows as dicts]} plus a manifest dict."""
    src = BackupSource(path)
    out = {name: [] for name in FILES}
    levels, enums, list_cdfs, usage = {}, {}, set(), {}
    pass1 = ["gazetteerlevel", "imsmaenum", "customdefinedfield", "fieldreportdesc", "gazetteer",
             "gazetteeralternativenames", "location", "organisation", "task", "location_has_geospatialinfo",
             "z_php_location", "z_php_k1_gaz_location"] + [t for t in ID_TABLES if t != "location"]
    gaz_rows = []
    loc_geo, loc_xy, place_xy = {}, {}, {}
    for table, r in src.tables(pass1):
        if table == "location_has_geospatialinfo":
            loc_geo.setdefault(r["geospatialinfo_guid"], r["location_guid"])
        elif table == "z_php_location":  # DMA reporting table: location point (fallback when no geo link table)
            if r.get("location_latitude") and r.get("location_longitude"):
                loc_xy.setdefault(r["location_guid"], (r["location_latitude"], r["location_longitude"]))
        elif table == "z_php_k1_gaz_location":  # DMA reporting table: city coordinates
            if r.get("gazetteer_latitude") and r.get("gazetteer_longitude"):
                place_xy.setdefault(r["gazetteer_guid"], (r["gazetteer_latitude"], r["gazetteer_longitude"]))
        if table == "gazetteerlevel":
            levels[r["gazlevel_guid"]] = _level_name(r.get("level"))
        elif table == "imsmaenum":
            enums[r["imsmaenum_guid"]] = r["enumvalue"]
        elif table == "customdefinedfield":
            out["cdfs.csv"].append({"cdf_id": r["cdf_id"], "name": r["name"], "datatype": r["cdf_datatype"],
                                    "entity": r["entitytype"], "label": r["label"], "active": _bool(r["isactive"])})
            if r["cdf_datatype"] in LIST_DATATYPES:
                list_cdfs.add(r["cdf_id"])
        elif table == "fieldreportdesc":
            out["forms.csv"].append({"guid": r["fieldreportdesc_guid"], "name": r["fieldreportname"],
                                     "version": r["version"], "published_on": (r["publisheddate"] or "")[:19],
                                     "active": _bool(r["isactive"])})
        elif table == "gazetteer":
            gaz_rows.append(r)
        elif table == "gazetteeralternativenames":
            if r.get("alternativename"):
                out["place_aliases.csv"].append({"guid": r["gazetteer_guid"], "alias": r["alternativename"]})
        elif table == "location":
            out["locations.csv"].append({"guid": r["location_guid"], "localid": (r["location_localid"] or "").strip(),
                                         "name": r["locationname"] or "", "place_guid": r["gazetteer_guid"] or "",
                                         "active": _bool(r["isactive"])})
            _track_id(usage, r["location_localid"])
        elif table == "organisation":
            out["organisations.csv"].append({"guid": r["org_guid"], "localid": (r["org_localid"] or "").strip(),
                                             "name": r["orgname"] or "", "active": _bool(r["isactive"])})
        elif table == "task":
            out["tasks.csv"].append({"guid": r["guid"], "localid": (r["localid"] or "").strip()})
        if table in ID_TABLES and table != "location":
            _track_id(usage, r.get(ID_TABLES[table]))
            if table == "fieldreport":
                out["reports.csv"].append({"guid": r["fieldreport_guid"], "localid": (r["fieldreport_localid"] or "").strip(),
                                           "form_guid": r["fieldreportdesc_guid"],
                                           "status": r["workbenchstatusenum_guid"]})
    # enum table may come after fieldreport in the dump: resolve statuses at the end
    for r in out["reports.csv"]:
        r["status"] = enums.get(r["status"], "")
    for r in gaz_rows:
        xy = place_xy.get(r["gazetteer_guid"]) or _box_centre(r)
        out["places.csv"].append({"guid": r["gazetteer_guid"], "name": r["gazetteername"] or "",
                                  "level": levels.get(r["gazlevel_guid"], ""), "parent_guid": r["parentgazetteer_guid"] or "",
                                  "lat": _coord(xy[0]), "lon": _coord(xy[1])})
    # pass 2: values stored for list CDFs (cdfvalue is the biggest table: stream, count only),
    # and the first map point of each location (geopoint, only the shapes of locations)
    counts = {}
    for table, r in src.tables(["cdfvalue", "geopoint"] if loc_geo else ["cdfvalue"]):
        if table == "cdfvalue":
            if r["cdf_id"] in list_cdfs and r.get("stringvalue"):
                key = (r["cdf_id"], r["stringvalue"].strip())
                counts[key] = counts.get(key, 0) + 1
        elif r["geospatialinfo_guid"] in loc_geo and r.get("latitude") and r.get("longitude"):
            loc_xy.setdefault(loc_geo[r["geospatialinfo_guid"]], (r["latitude"], r["longitude"]))
    for r in out["locations.csv"]:
        xy = loc_xy.get(r["guid"], (None, None))
        r["lat"], r["lon"] = _coord(xy[0]), _coord(xy[1])
    out["cdf_options.csv"] = [{"cdf_id": k[0], "value": k[1], "usage": n} for k, n in sorted(counts.items())]
    out["id_usage.csv"] = [{"prefix": p, "max_number": n} for p, n in sorted(usage.items())]
    manifest = {"source": "backup", "backup_path": os.path.basename(os.path.normpath(path)),
                "dump_date": dump_date or _guess_dump_date(path)}
    return out, manifest


def _guess_dump_date(path):
    m = re.search(r"Backup_(\d{4})_(\d{2})_(\d{2})", path.replace("\\", "/"))
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


# ---------------------------------------------------------------- live (read-only)

LIVE_QUERIES = {
    "forms.csv": "SELECT fieldreportdesc_guid AS guid, fieldreportname AS name, version, "
                 "to_char(publisheddate, 'YYYY-MM-DD HH24:MI:SS') AS published_on, isactive AS active FROM fieldreportdesc",
    "cdfs.csv": "SELECT cdf_id, name, cdf_datatype AS datatype, entitytype AS entity, label, isactive AS active FROM customdefinedfield",
    "cdf_options.csv": "SELECT v.cdf_id, trim(v.stringvalue) AS value, count(*) AS usage FROM cdfvalue v "
                       "JOIN customdefinedfield d ON d.cdf_id = v.cdf_id "
                       "WHERE d.cdf_datatype IN ('SINGLE_SELECT', 'MULTI_SELECT') AND coalesce(trim(v.stringvalue), '') <> '' "
                       "GROUP BY 1, 2",
    "places.csv": "SELECT g.gazetteer_guid AS guid, g.gazetteername AS name, l.level, coalesce(g.parentgazetteer_guid, '') AS parent_guid, "
                  "(g.upperlefty + g.lowerrighty) / 2 AS lat, (g.upperleftx + g.lowerrightx) / 2 AS lon "
                  "FROM gazetteer g LEFT JOIN gazetteerlevel l ON l.gazlevel_guid = g.gazlevel_guid",
    "place_aliases.csv": "SELECT gazetteer_guid AS guid, alternativename AS alias FROM gazetteeralternativenames "
                         "WHERE coalesce(alternativename, '') <> ''",
    "locations.csv": "SELECT l.location_guid AS guid, trim(l.location_localid) AS localid, l.locationname AS name, "
                     "coalesce(l.gazetteer_guid, '') AS place_guid, l.isactive AS active, p.latitude AS lat, p.longitude AS lon "
                     "FROM location l LEFT JOIN LATERAL (SELECT gp.latitude, gp.longitude FROM location_has_geospatialinfo lg "
                     "JOIN geopoint gp ON gp.geospatialinfo_guid = lg.geospatialinfo_guid "
                     "WHERE lg.location_guid = l.location_guid ORDER BY gp.pointno LIMIT 1) p ON true",
    "organisations.csv": "SELECT org_guid AS guid, trim(org_localid) AS localid, orgname AS name, isactive AS active FROM organisation",
    "tasks.csv": "SELECT guid, trim(localid) AS localid FROM task",
    "idtypes.csv": "SELECT name, nextnumber AS next_number FROM localidtype",
    "reports.csv": "SELECT f.fieldreport_guid AS guid, trim(f.fieldreport_localid) AS localid, "
                   "f.fieldreportdesc_guid AS form_guid, coalesce(e.enumvalue, '') AS status "
                   "FROM fieldreport f LEFT JOIN imsmaenum e ON e.imsmaenum_guid = f.workbenchstatusenum_guid",
}


def read_live(conn_params, timeout_s=120):
    """Read the reference data from a live IMSMA PostgreSQL, in a READ ONLY transaction."""
    import psycopg2  # only needed here

    conn = psycopg2.connect(connect_timeout=15, options=f"-c statement_timeout={timeout_s * 1000}",
                            application_name="dma_field_reports (read-only)", **conn_params)
    try:
        conn.set_session(readonly=True, autocommit=False)
        out = {name: [] for name in FILES}
        with conn.cursor() as cr:
            for name, sql in LIVE_QUERIES.items():
                cr.execute(sql)
                cols = [d[0] for d in cr.description]
                for rec in cr.fetchall():
                    row = dict(zip(cols, rec))
                    if "active" in row:
                        row["active"] = _bool("t" if row["active"] in (True, "t") else "f")
                    if name == "places.csv":
                        row["level"] = _level_name(row["level"])
                    if "lat" in row:
                        row["lat"], row["lon"] = _coord(row["lat"]), _coord(row["lon"])
                    out[name].append(row)
            usage = {}
            for table, col in ID_TABLES.items():
                cr.execute(f"SELECT {col} FROM {table}")  # fixed table/column names, no user input
                for (localid,) in cr.fetchall():
                    _track_id(usage, localid)
            out["id_usage.csv"] = [{"prefix": p, "max_number": n} for p, n in sorted(usage.items())]
        conn.rollback()
    finally:
        conn.close()
    return out, {"source": "live", "dump_date": datetime.date.today().isoformat()}


# ---------------------------------------------------------------- package i/o

def write_package(out, manifest, fileobj):
    """Write the package zip to a binary file object."""
    files = {}
    with zipfile.ZipFile(fileobj, "w", zipfile.ZIP_DEFLATED) as z:
        for name, cols in FILES.items():
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
            w.writeheader()
            for row in out.get(name, []):
                w.writerow(row)
            data = buf.getvalue().encode("utf8")
            z.writestr(name, data)
            files[name] = {"rows": len(out.get(name, [])), "sha256": hashlib.sha256(data).hexdigest()}
        manifest = dict(manifest, format=FORMAT, format_version=FORMAT_VERSION,
                        created_at=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        files=files)
        z.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    return manifest


def read_package(data):
    """bytes -> ({file name: [rows]}, manifest). Raises ValueError with a readable reason."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as e:
        raise ValueError("The file is not a zip package.") from e
    with z:
        if "manifest.json" not in z.namelist():
            raise ValueError("manifest.json is missing: this is not an IMSMA reference package.")
        manifest = json.loads(z.read("manifest.json").decode("utf8"))
        if manifest.get("format") != FORMAT or manifest.get("format_version") != FORMAT_VERSION:
            raise ValueError(f"Unsupported package format {manifest.get('format')} v{manifest.get('format_version')}.")
        out = {}
        for name, info in manifest.get("files", {}).items():
            raw = z.read(name)
            if hashlib.sha256(raw).hexdigest() != info["sha256"]:
                raise ValueError(f"{name} is damaged (checksum mismatch).")
            out[name] = list(csv.DictReader(io.StringIO(raw.decode("utf8"), newline="")))
        for name in FILES:
            out.setdefault(name, [])
    return out, manifest
