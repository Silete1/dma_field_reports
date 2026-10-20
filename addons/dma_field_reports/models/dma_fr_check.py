"""Checking: every value of every row, then the checks that need several values of a row.

Nothing aborts: each problem is written on its cell (state, code, message,
suggestions). A fix (cell.override, a value mapping, a chosen place) is used
the next time the row is checked.
"""
import base64
import datetime
import io
import mimetypes
import re
import zipfile
from collections import defaultdict

from psycopg2.extras import execute_values

from odoo import _, fields, models

from ..services import geo, text

def _differs(record, fname, value):
    """True when writing value would change record[fname] (avoids needless writes and recomputes)."""
    field = record._fields[fname]
    current = record[fname]
    if field.type == "many2one":
        return (current.id or False) != (value or False)
    if field.type in ("many2many", "one2many"):
        if isinstance(value, list) and value and value[0][0] == 6:
            return set(current.ids) != set(value[0][2])
        return True
    if field.type == "float":
        return round(current or 0.0, 7) != round(value or 0.0, 7)
    return (current or False) != (value or False)


DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%d/%m/%y", "%d %B %Y", "%d %b %Y"]
PLACE_ROLES = ("province", "district", "subdistrict", "city")


class Ctx:
    """Everything a check needs, loaded once per run."""

    def __init__(self, batch):
        env = batch.env
        self.env = env
        self.batch = batch
        self.today = fields.Date.context_today(batch)
        maps = defaultdict(dict)
        for m in env["dma.fr.value.map"].search([]):
            maps[m.scope][m.source_norm] = m.target_value
        self.maps = maps
        self.options = {}
        for f in batch.template_id.field_ids:
            if f.datatype in ("list", "multi"):
                opts = f.allowed_options()
                self.options[f.id] = {"by_norm": {}, "list": opts}
                for value, _usage in opts:
                    self.options[f.id]["by_norm"].setdefault(text.norm(value), value)
        orgs = env["dma.fr.ref.org"].search([])
        self.org_by_guid = {o.guid: o for o in orgs}
        self.org_by_key = {}
        for o in orgs:
            for k in (o.localid_norm, o.name_norm):
                if k:
                    self.org_by_key.setdefault(k, o)
        self.orgs = orgs
        # gazetteer in memory
        self.places = {}
        self._by_level = {}
        self.place_cache = {}  # address (+ rounded point) -> (place, area, [(role, flag args)])
        self.children = defaultdict(list)
        env.cr.execute("SELECT id, name, name_norm, level, parent_id FROM dma_fr_ref_place WHERE active")
        for pid, name, norm_, level, parent in env.cr.fetchall():
            self.places[pid] = (name, norm_ or text.norm(name), level, parent)
            self.children[parent].append(pid)
        self.alias = defaultdict(set)
        env.cr.execute("SELECT place_id, alias_norm FROM dma_fr_ref_place_alias")
        for pid, a in env.cr.fetchall():
            if a:
                self.alias[pid].add(a)
        self.loc_by_place_name = {}
        self.loc_by_guid = {}
        self.loc_count = defaultdict(int)
        self.loc_points = []  # (location, lat, lon) of IMSMA locations that have a point
        for loc in env["dma.fr.ref.location"].search([]):
            self.loc_by_guid[loc.guid] = loc
            if loc.latitude or loc.longitude:
                self.loc_points.append((loc, loc.latitude, loc.longitude))
            if loc.place_id:
                self.loc_count[loc.place_id.id] += 1
                for key in {loc.name_norm, text.norm((loc.name or "").split("/")[0])}:
                    if key:
                        self.loc_by_place_name.setdefault((loc.place_id.id, key), loc)
        self.tasks = set(env["dma.fr.ref.task"].search([]).mapped("localid_norm"))
        if "dma.task.order" in env:  # task orders kept in Odoo (dma_task_orders module), when installed
            TO = env["dma.task.order"].sudo()
            for fname in ("name", "reference", "imsma_localid", "localid"):
                if fname in TO._fields and TO._fields[fname].type == "char":
                    self.tasks |= {text.norm(v) for v in TO.search([]).mapped(fname) if v}
        self.attachments = batch._attachment_index()

    # ------------------------------------------------------------- places
    def place_matches(self, pid, key):
        name, norm_, _level, _parent = self.places[pid]
        return key and (norm_ == key or key in self.alias.get(pid, ()))

    def descendants(self, pid, level):
        out, stack = [], list(self.children.get(pid, []))
        while stack:
            c = stack.pop()
            if self.places[c][2] == level:
                out.append(c)
            stack.extend(self.children.get(c, []))
        return out

    def by_level(self, level):
        if level not in self._by_level:
            self._by_level[level] = [pid for pid, p in self.places.items() if p[2] == level]
        return self._by_level[level]

    def nearest_locations(self, lat, lon, max_km=10.0, limit=3):
        """[(km, location)] of IMSMA locations near a point, nearest first."""
        if not (lat or lon):
            return []
        # cheap box filter first (0.1 degree is about 10 km here)
        box = max_km / 100.0 + 0.01
        hits = [(geo.distance_km(lat, lon, la, lo), loc) for loc, la, lo in self.loc_points
                if abs(la - lat) < box and abs(lo - lon) < box]
        return sorted((h for h in hits if h[0] <= max_km), key=lambda h: h[0])[:limit]


class DmaFrBatchCheck(models.Model):
    _inherit = "dma.fr.batch"

    def _attachment_index(self):
        """{normalised file stem: attachment}. A zip among the attachments is unpacked once."""
        self.ensure_one()
        Att = self.env["ir.attachment"]
        for att in self.attachment_ids.filtered(lambda a: (a.name or "").lower().endswith(".zip")):
            try:
                with zipfile.ZipFile(io.BytesIO(base64.b64decode(att.datas))) as z:
                    new = []
                    for info in z.infolist():
                        if info.is_dir() or info.file_size == 0:
                            continue
                        name = info.filename.rsplit("/", 1)[-1]
                        new.append({"name": name, "datas": base64.b64encode(z.read(info)),
                                    "res_model": "dma.fr.batch", "res_id": self.id,
                                    "mimetype": mimetypes.guess_type(name)[0] or "application/octet-stream"})
                    self.attachment_ids = [(3, att.id)] + [(4, a.id) for a in Att.create(new)]
            except zipfile.BadZipFile:
                continue
        index = {}
        for att in self.attachment_ids:
            stem = (att.name or "").rsplit(".", 1)[0]
            index.setdefault(text.norm(stem), att)
            index.setdefault(text.norm(att.name), att)
        return index

    # ================================================================= main
    def _run_check(self, rows=None):
        self.ensure_one()
        rows = rows or self.row_ids
        ctx = Ctx(self)
        new_vals = {}  # cell -> (state, code, message, suggestion, value)
        row_writes = []
        seen_report_ids = defaultdict(list)
        for row in rows:
            if row.excluded:
                continue
            results = {}
            values = {}
            for cell in row.cell_ids:
                res = self._check_value(ctx, cell)
                results[cell.id] = res
                values.setdefault(cell.field_id.role, []).append((cell, res))
            row_vals = self._check_row(ctx, row, values, results)
            row_writes.append((row, row_vals))
            for cell, res in values.get("org_report_id", []):
                if res.get("py"):
                    seen_report_ids[text.norm(res["py"])].append((row, cell))
            for cell in row.cell_ids:
                res = results[cell.id]
                value = res.get("value") or None
                if value is not None and not cell.override and value == cell.raw:
                    value = None  # same as the file: not stored (see dma.fr.cell.sent_value)
                new_vals[cell] = (res.get("state", "ok"), res.get("code") or None, res.get("message") or None,
                                  res.get("suggestion") or None, value)
        # same organisation report id twice in this batch, or already exported in an earlier batch
        self._flag_repeated_reports(seen_report_ids, new_vals)
        self._write_cells(new_vals)
        for row, vals in row_writes:
            changes = {k: v for k, v in vals.items() if _differs(row, k, v)}
            if changes:
                row.write(changes)
        self._make_location_requests(rows)
        return True

    def _flag_repeated_reports(self, seen_report_ids, new_vals):
        done = self.env["dma.fr.cell"].search([
            ("batch_id", "!=", self.id), ("field_id.role", "=", "org_report_id"), ("row_id.imsma_state", "!=", "not_sent"),
            ("row_excluded", "=", False), ("raw", "!=", False)])
        earlier = defaultdict(list)
        for c in done:
            earlier[text.norm(c.raw)].append(c)
        for key, hits in seen_report_ids.items():
            if len(hits) > 1:
                rows_txt = ", ".join(str(r.excel_row) for r, _c in hits)
                for _row, cell in hits:
                    new_vals[cell] = ("warning", "duplicate_in_batch",
                                      _("The same report id is on rows %s.", rows_txt), None, cell.raw)
            for _row, cell in hits:
                if key in earlier:
                    prev = earlier[key][0]
                    new_vals[cell] = ("warning", "already_exported",
                                      _("Already exported in batch %(batch)s (%(id)s). Leave this row out unless it "
                                        "corrects that report.", batch=prev.batch_id.name,
                                        id=prev.row_id.object_localid or "-"), None, cell.raw)

    def _write_cells(self, new_vals):
        """Write only the cells whose result changed, in one SQL statement (thousands of cells on big files)."""
        rank = {"error": 3, "warning": 2, "info": 1}
        changed = [(c.id, *v, rank.get(v[0], 0)) for c, v in new_vals.items()
                   if (c.state, c.code or None, c.message or None, c.suggestion or None, c.value or None) != v]
        if not changed:
            return
        self.env.flush_all()
        execute_values(self.env.cr._obj, """
            UPDATE dma_fr_cell AS c SET state = v.state, code = v.code, message = v.message,
                   suggestion = v.suggestion, value = v.value, severity = v.severity,
                   write_uid = %s, write_date = now() at time zone 'UTC'
            FROM (VALUES %%s) AS v(id, state, code, message, suggestion, value, severity)
            WHERE c.id = v.id""" % int(self.env.uid), changed, page_size=2000)
        cells = self.env["dma.fr.cell"].browse([c[0] for c in changed])
        cells.invalidate_recordset(["state", "code", "message", "suggestion", "value", "severity"])
        cells.modified(["state", "code", "message", "suggestion", "value", "severity"])

    # ============================================================ one value
    def _check_value(self, ctx, cell):
        f = cell.field_id
        raw = cell.override if cell.override not in (False, None, "") else cell.raw
        raw = text.clean(raw)
        res = {"state": "ok", "value": raw, "py": raw or None}
        if not raw and not (f.datatype == "date" and cell.raw_date and not cell.override):
            if f.required:
                return {"state": "error", "code": "required", "message": _("Required: this cell is empty."),
                        "value": "", "py": None}
            return {"state": "empty", "value": "", "py": None}
        dt = f.datatype
        if dt == "text":
            if f.max_length and len(raw) > f.max_length:
                res.update(state="warning", code="too_long",
                           message=_("%(n)s characters; IMSMA keeps %(max)s.", n=len(raw), max=f.max_length))
        elif dt in ("integer", "number"):
            num = geo.parse_decimal(raw)
            if num is None:
                return {"state": "error", "code": "bad_number", "message": _("'%s' is not a number.", raw), "value": raw}
            if dt == "integer" and not float(num).is_integer():
                return {"state": "error", "code": "bad_number", "message": _("A whole number is expected."), "value": raw}
            if num < 0:
                return {"state": "error", "code": "bad_number", "message": _("Negative numbers are not allowed."),
                        "value": raw}
            res.update(value=str(int(num)) if float(num).is_integer() else str(num), py=num)
        elif dt == "date":
            d, warn = self._parse_date(cell, raw)
            if not d:
                return {"state": "error", "code": "bad_date",
                        "message": _("'%s' is not a date. Write it as YYYY-MM-DD or DD/MM/YYYY.", raw), "value": raw}
            res.update(value=d.isoformat(), py=d)
            if d > ctx.today and f.role not in ("planned_start", "planned_end"):
                res.update(state="error", code="future_date", message=_("This date is in the future."))
            elif d.year < 2000:
                res.update(state="error", code="bad_date", message=_("This date is before 2000."))
            elif warn:
                res.update(state="warning", code="ambiguous_date", message=warn)
        elif dt in ("list", "multi"):
            parts = text.split_multi(raw) if dt == "multi" else [raw]
            out, unknown = [], []
            for part in parts:
                v = self._map_list_value(ctx, f, part)
                if v:
                    if v not in out:
                        out.append(v)
                else:
                    unknown.append(part)
            if unknown:
                opts = ctx.options.get(f.id, {}).get("list", [])
                sugg = text.best_matches(unknown[0], [(v, v) for v, _u in opts], limit=3, cutoff=0.5)
                return {"state": "error", "code": "unknown_value", "value": ", ".join(out),
                        "message": _("Not an IMSMA value: %s", ", ".join(f"'{u}'" for u in unknown)),
                        "suggestion": " | ".join(s[2] for s in sugg), "py": out}
            res.update(value=", ".join(out), py=out)
        elif dt == "organisation":
            org = self._resolve_org(ctx, raw)
            if not org:
                sugg = text.best_matches(raw, [(o.guid, o.localid or o.name) for o in ctx.orgs], limit=3, cutoff=0.6)
                sugg += text.best_matches(raw, [(o.guid, o.name) for o in ctx.orgs], limit=3, cutoff=0.6)
                names = []
                for _s, g, _l in sorted(sugg, key=lambda t: -t[0]):
                    o = ctx.org_by_guid[g]
                    if o.display_name not in names:
                        names.append(o.display_name)
                return {"state": "error", "code": "unknown_org", "value": raw,
                        "message": _("'%s' is not an organisation in IMSMA.", raw),
                        "suggestion": " | ".join(names[:3])}
            res.update(value=org.display_name, py=org)
        return res

    def _parse_date(self, cell, raw):
        if cell.raw_date and not cell.override:
            return cell.raw_date, None
        for fmt in DATE_FORMATS:
            try:
                d = datetime.datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
            warn = None
            m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-]\d{2,4}$", raw)
            if m and int(m.group(1)) <= 12 and int(m.group(2)) <= 12 and m.group(1) != m.group(2):
                warn = _("Read as day/month: %s. Check it is not month/day.", d.strftime("%d %B %Y"))
            return d, warn
        return None, None

    def _map_list_value(self, ctx, f, part):
        key = text.norm(part)
        if not key:
            return None
        mapped = ctx.maps.get(f.mapping_scope, {}).get(key)
        if mapped:
            return mapped
        return ctx.options.get(f.id, {}).get("by_norm", {}).get(key)

    def _resolve_org(self, ctx, raw):
        mapped = ctx.maps.get("organisation", {}).get(text.norm(raw))
        if mapped and mapped in ctx.org_by_guid:
            return ctx.org_by_guid[mapped]
        if raw in ctx.org_by_guid:
            return ctx.org_by_guid[raw]
        return ctx.org_by_key.get(text.norm(raw))

    # ============================================================== one row
    def _check_row(self, ctx, row, values, results):
        def first(role):
            items = values.get(role) or []
            return items[0] if items else (None, {})

        def flag(cell, state, code, message, suggestion=None):
            if cell is None:
                return
            r = results[cell.id]
            rank = {"ok": 0, "empty": 0, "info": 1, "warning": 2, "error": 3}
            if rank[state] >= rank.get(r.get("state", "ok"), 0):
                r.update(state=state, code=code, message=message, suggestion=suggestion)

        row_vals = {"org_id": False, "report_date": False, "latitude": 0.0, "longitude": 0.0, "coord_note": False,
                    "location_id": False}
        cell, res = first("organisation")
        if res.get("py") and not isinstance(res["py"], str):
            row_vals["org_id"] = res["py"].id
        cell, res = first("report_date")
        if isinstance(res.get("py"), datetime.date):
            row_vals["report_date"] = res["py"]

        # --- dates in order
        def date_of(role):
            return first(role)[1].get("py") if isinstance(first(role)[1].get("py"), datetime.date) else None
        a_start, a_end = date_of("actual_start"), date_of("actual_end")
        p_start, p_end = date_of("planned_start"), date_of("planned_end")
        if a_start and a_end and a_end < a_start:
            flag(first("actual_end")[0], "error", "date_order", _("Ends before it starts (%s).", a_start.isoformat()))
        if p_start and p_end and p_end < p_start:
            flag(first("planned_end")[0], "error", "date_order", _("Planned end is before planned start."))
        rep = row_vals["report_date"]
        if rep and a_end and rep < a_end:
            flag(first("report_date")[0], "warning", "date_order",
                 _("The report is dated before the activity ended (%s).", a_end.isoformat()))

        # --- coordinates first: they help to find the place
        self._check_coordinates(ctx, values, flag, row_vals, first)

        # --- place and location
        self._check_place(ctx, row, values, results, flag, row_vals)

        # --- task dossier
        cell, res = first("task_dossier")
        if cell and res.get("py") and text.norm(res["py"]) not in ctx.tasks:
            flag(cell, "warning", "unknown_task",
                 _("No task order '%s' in IMSMA or Odoo. Check the id; IMSMA will still accept the report.", res["py"]))

        # --- attachments: listed names, else the organisation's report id
        atts = self.env["ir.attachment"]
        cell, res = first("attachments")
        names = text.split_multi(res.get("py") or "") if cell else []
        if names:
            missing = []
            for n in names:
                att = ctx.attachments.get(text.norm(n.rsplit(".", 1)[0])) or ctx.attachments.get(text.norm(n))
                if att:
                    atts |= att
                else:
                    missing.append(n)
            if missing:
                flag(cell, "error", "missing_attachment",
                     _("Not among the uploaded attachments: %s", ", ".join(missing)))
        else:
            rcell, rres = first("org_report_id")
            key = text.norm(rres.get("py") or "")
            att = ctx.attachments.get(key) if key else None
            if att:
                atts |= att
            elif rcell and key and ctx.attachments:
                flag(rcell, "warning", "missing_attachment",
                     _("No uploaded attachment is named like this report id."))
        row_vals["attachment_ids"] = [(6, 0, atts.ids)]

        # --- EORE: at least one person reached
        if self.kind == "eore":
            audience = [res.get("py") for cell, res in values.get("cdf", [])
                        if re.search(r"\((5-12|13-18|19\+)\)", cell.field_id.name or "")]
            if audience and not any(isinstance(v, (int, float)) and v > 0 for v in audience):
                c = next((cell for cell, _r in values.get("cdf", []) if "(5-12)" in (cell.field_id.name or "")), None)
                flag(c, "warning", "no_audience", _("No audience counted in any age group."))
        return row_vals

    def _check_place(self, ctx, row, values, results, flag, row_vals):
        def raw_of(role):
            items = values.get(role) or []
            return (items[0][0], text.clean(items[0][1].get("value"))) if items else (None, "")

        guid_cell, guid_raw = raw_of("location_guid")
        chosen = row.location_manual_id if row.location_manual_id.active else None
        if not chosen and guid_raw and guid_raw in ctx.loc_by_guid:  # the file already names the IMSMA location
            chosen = ctx.loc_by_guid[guid_raw]
        if chosen:
            row_vals.update(location_id=chosen.id, place_id=chosen.place_id.id or row.place_id.id,
                            location_request_id=False, area_id=chosen.place_id.id)
            return
        cells = {r: raw_of(r) for r in PLACE_ROLES}
        name_cell, name_raw = raw_of("location_name")
        if not any(v for _c, v in cells.values()) and not row.place_manual:
            return
        place = row.place_id.id if row.place_manual and row.place_id else None
        if not place:
            key = tuple(v for _c, v in cells.values()) + (
                round(row_vals.get("latitude") or 0, 3), round(row_vals.get("longitude") or 0, 3))
            cached = ctx.place_cache.get(key)
            if cached is None:
                flags = []
                cell_role = {c.id: r for r, (c, _v) in cells.items() if c}

                def record(cell, *args):
                    if cell is not None:
                        flags.append((cell_role.get(cell.id), args))
                place, area = self._resolve_place(ctx, cells, record, row_vals)
                cached = ctx.place_cache[key] = (place, area, flags)
            place, area, flags = cached
            for role, args in flags:
                flag(cells[role][0] if role else None, *args)
            row_vals["area_id"] = area or False
        if not place:
            row_vals["place_id"] = False
            row_vals["location_request_id"] = False
            return
        row_vals["place_id"] = place
        # location under that place: given location name, else the typed village name
        city_cell, city_raw = cells["city"]
        loc_name = name_raw or city_raw or ctx.places[place][0]
        loc = (ctx.loc_by_place_name.get((place, text.norm(loc_name)))
               or (ctx.loc_by_place_name.get((place, ctx.places[place][1])) if not name_raw else None))
        if loc:
            row_vals["location_id"] = loc.id
            row_vals["location_request_id"] = False
        else:
            # the request itself is made after the loop (_make_location_requests), from this cell's note
            target = name_cell if name_raw else city_cell
            flag(target, "info", "new_location",
                 _("No IMSMA location '%(name)s' in %(place)s yet: it will be created first (step 3).",
                   name=loc_name, place=ctx.places[place][0]))

    def _resolve_place(self, ctx, cells, flag, row_vals):
        """Walk province > district > (sub-district) > city.

        Returns (city place id or None, deepest place id matched). Flags the first cell that does not match.
        """
        prov_cell, prov = cells["province"]
        dist_cell, dist = cells["district"]
        sub_cell, sub = cells["subdistrict"]
        city_cell, city = cells["city"]
        candidates = ctx.by_level("province")
        province = self._pick(ctx, candidates, prov)
        if prov and not province:
            self._flag_place(ctx, flag, prov_cell, prov, candidates, _("province"))
            return None, None
        districts = ctx.descendants(province, "district") if province else ctx.by_level("district")
        district = self._pick(ctx, districts, dist)
        if dist and not district:
            self._flag_place(ctx, flag, dist_cell, dist, districts, _("district"))
            return None, province
        top = district or province
        subdistrict = None
        if sub:
            subs = ctx.descendants(top, "subdistrict") if top else ctx.by_level("subdistrict")
            subdistrict = self._pick(ctx, subs, sub)
            if not subdistrict:
                self._flag_place(ctx, flag, sub_cell, sub, subs, _("sub-district"))
                return None, top
        area = subdistrict or top
        if not city:
            if city_cell:
                flag(city_cell, "error", "required", _("Give the city, town or village."))
            return None, area
        cities = ctx.descendants(area, "city") if area else ctx.by_level("city")
        found = [c for c in cities if ctx.place_matches(c, text.norm(city))]
        if not found:
            near = ctx.nearest_locations(row_vals.get("latitude"), row_vals.get("longitude"))
            near_txt = [f"{loc.name} ({loc.localid}, {km:.1f} km)" for km, loc in near]
            self._flag_place(ctx, flag, city_cell, city, cities, _("city / town / village"), extra=near_txt)
            return None, area
        if len(found) > 1:  # duplicate gazetteer entries: prefer the one IMSMA locations use
            found.sort(key=lambda c: -ctx.loc_count.get(c, 0))
        return found[0], area

    def _pick(self, ctx, candidates, raw):
        if not raw:
            return None
        key = text.norm(raw)
        hits = [c for c in candidates if ctx.place_matches(c, key)]
        return hits[0] if hits else None

    def _flag_place(self, ctx, flag, cell, raw, candidates, what, extra=None):
        sugg = [s[2] for s in text.best_matches(raw, [(c, ctx.places[c][0]) for c in candidates], limit=3, cutoff=0.7)]
        message = _("'%(raw)s' is not a %(what)s of the IMSMA gazetteer here.", raw=raw, what=what)
        if extra:
            message += " " + _("IMSMA locations nearby: %s.", "; ".join(extra))
        flag(cell, "error", "unknown_place", message, " | ".join(sugg))

    def _check_coordinates(self, ctx, values, flag, row_vals, first):
        lat_cell, lat_res = first("latitude")
        lon_cell, lon_res = first("longitude")
        mgrs_cell, mgrs_res = first("mgrs")
        lat = geo.parse_decimal(lat_res.get("value")) if lat_cell else None
        lon = geo.parse_decimal(lon_res.get("value")) if lon_cell else None
        mgrs_txt = text.clean(mgrs_res.get("value")) if mgrs_cell else ""
        from_mgrs = geo.parse_mgrs(mgrs_txt) if mgrs_txt else None
        if mgrs_txt and not from_mgrs:
            flag(mgrs_cell, "error", "bad_mgrs", _("'%s' is not a valid MGRS grid reference.", mgrs_txt))
        if lat is not None and lon is not None:
            if not geo.in_iraq(lat, lon):
                if geo.in_iraq(lon, lat):
                    flag(lat_cell, "error", "latlon_swapped",
                         _("Latitude and longitude are swapped (%(lat)s, %(lon)s is outside Iraq).", lat=lat, lon=lon))
                    return
                flag(lat_cell, "error", "out_of_iraq", _("This point (%(lat)s, %(lon)s) is outside Iraq.", lat=lat, lon=lon))
                return
            row_vals.update(latitude=lat, longitude=lon)
            if from_mgrs:
                d = geo.distance_km(lat, lon, *from_mgrs)
                if d > 1:
                    flag(mgrs_cell, "warning", "mgrs_mismatch",
                         _("MGRS and lat/long are %.1f km apart. Lat/long will be sent.", d))
            return
        if from_mgrs:
            row_vals.update(latitude=from_mgrs[0], longitude=from_mgrs[1])
            if lat is not None or lon is not None:
                missing = lat_cell if lat is None else lon_cell
                flag(missing, "info", "from_mgrs", _("Missing: taken from the MGRS (%.6f, %.6f).", *from_mgrs))
                row_vals["coord_note"] = _("lat/long completed from MGRS")
            else:
                row_vals["coord_note"] = _("from MGRS")
            if not geo.in_iraq(*from_mgrs):
                flag(mgrs_cell, "error", "out_of_iraq", _("This MGRS point is outside Iraq."))
            return
        target = lat_cell or mgrs_cell
        if target and (lat is not None or lon is not None):
            flag(lat_cell if lat is None else lon_cell, "error", "required",
                 _("Give both latitude and longitude, or an MGRS reference."))
        elif target:
            flag(target, "warning", "no_coordinates", _("No coordinates: the report will have no point on the map."))

    def _make_location_requests(self, rows):
        """Group rows that need a new IMSMA location into one request per (place, name)."""
        Req = self.env["dma.fr.location.request"]
        existing = {(r.place_id.id, text.norm(r.name)): r for r in self.location_request_ids}
        used = set(self.row_ids.filtered(lambda r: r not in rows and r.location_request_id).location_request_id.ids)
        # rows that need a new location carry the note "new_location" on their city or location-name cell
        for row in rows.filtered(lambda r: not r.excluded and not r.location_id and r.place_id):
            cell = row.cell_ids.filtered(lambda c: c.code == "new_location")[:1]
            if not cell:
                row.location_request_id = False
                continue
            name = text.clean(cell.override or cell.raw) or row.place_id.name
            key = (row.place_id.id, text.norm(name))
            req = existing.get(key)
            if not req:
                req = Req.create({"batch_id": self.id, "name": name, "place_id": row.place_id.id})
                existing[key] = req
            row.location_request_id = req
            used.add(req.id)
        # drop requests nobody needs any more (only before they are exported)
        (self.location_request_ids.filtered(lambda r: r.state == "draft" and r.id not in used)).unlink()
