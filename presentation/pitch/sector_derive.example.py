"""EXAMPLE sector_derive.py (the two finished editions' mappings). Copy the parts you need into sector_derive.py.

build.py calls derive(figures, fmt) once, before it fills {{keys}} in pages.html. Use it to:
* turn lists the demo lane wrote into page keys (a timeline list -> {step: time});
* compute what the pages print but the database does not store (days between two dates, "4 of 36");
* add VERIFIED sector facts (from the research file, with their source in the page copy) under f["sector"], so they
  are not demo data and never count as fallbacks;
* make one number agree everywhere (e.g. copy the kitchen's exact price into the order bars).
Keep it pure: read f, add keys, never delete what the demo wrote.
"""


def derive(f, fmt):
    """Worked example: the furniture edition (first half) and the services edition (second half) in one function."""
    if not f:
        return
    # verified sector facts, COSIT 2023 (research 01 §A1): not demo data, so they live here, not in targets
    f.setdefault("sector", {"small_shops": 3688, "tiny_pct": 55, "inputs_pct": 53})
    # furniture: fur_demo's shapes -> the page keys
    cs = f.get("cost") or {}
    if cs.get("boards_used") is not None and cs.get("boards_planned") is not None:
        cs["boards_over"] = cs["boards_used"] - cs["boards_planned"]
    rt = f.get("rate") or {}
    if rt.get("gap_official_pct") is not None:
        rt["gap_pct"] = round(rt["gap_official_pct"])
    rm = f.get("room") or {}
    if isinstance(rm.get("pieces"), list):
        out = []
        for p in rm["pieces"]:
            q = dict(p)
            if q.get("k") == "wardrobe" and q.get("state") == "swap":
                q["name"] = (rm.get("swap_in") or q["name"]).replace(" موديل ", "، من ")
                q["doors"] = 6
            elif q.get("k") == "mirror" and q.get("state") == "short":
                q["name"] = "مراية، ناقصة بالبصرة"
            else:
                q["name"] = q["name"].replace(" موديل 214", "")
            if q.get("k") == "stand" and (q.get("qty") or 1) > 1:
                q["share"] = round(q["share"] / 2)
                out.append(dict(q))
            out.append(q)
        rm["pieces_draw"] = out
    mo = f.get("money") or {}
    if isinstance(mo.get("orders"), list):
        mo["orders_draw"] = [dict(o, name=(o.get("customer") if str(o.get("name", "")).startswith("S0") else o.get("name"))) for o in mo["orders"]][:6]
        kt = f.get("kitchen") or {}
        for o in mo["orders_draw"]:
            if kt.get("name") and o.get("name") == kt.get("name") and kt.get("price_usd"):
                o["paid"], o["total"] = kt.get("deposit_usd", o["paid"]), kt["price_usd"]
    dg = (f.get("digest") or {}).get("kpis") or {}
    if dg:
        f["dg"] = {"late": dg.get("kpi_anu_late_orders"), "deposits": dg.get("kpi_anu_deposits"), "balances": dg.get("kpi_anu_balances"),
                   "short": dg.get("kpi_anu_rooms_short"), "rate": dg.get("kpi_anu_rate")}
    # furniture: the designer lane's raw figures
    dr = f.get("designer_raw")
    if dr:
        c = dr.get("cost") or {}
        sb = (dr.get("sheets_by_type") or [{}])[0]
        tq = dr.get("time_to_quote_s") or {}
        f["designer"] = {
            "price_usd": dr.get("price_usd"), "cost_usd": c.get("total_cost"), "sheets": dr.get("sheets"), "parts": dr.get("parts"),
            "cabinets": dr.get("cabinets"), "cnc_ops": dr.get("cnc_operations"), "yield_pct": sb.get("yield_pct"),
            "waste_pct": (dr.get("waste_pct") or {}).get("mdf_oak_18"), "offcuts": sb.get("reusable_offcuts"),
            "margin_pct": round(dr.get("margin_pct") or 0), "margin_usd": dr.get("margin_usd"),
            "quote_name": (dr.get("quotation") or {}).get("name"),
            "quote_s": round(sum(v for v in tq.values() if isinstance(v, (int, float))), 1),
            "price": [
                {"label": "أجهزة مشتراة", "v": c.get("appliances_bought", 0)},
                {"label": "ألواح وسطح عمل", "v": c.get("boards_and_worktop", 0)},
                {"label": "إكسسوارات وحواف", "v": round(c.get("edging_and_fittings", 0) + c.get("consumables_and_packaging", 0), 2)},
                {"label": "شغل", "v": c.get("labour", 0)},
                {"label": "مصاريف عامة", "v": c.get("overhead_8pct", 0)},
                {"label": "الهامش", "v": dr.get("margin_usd", 0)},
            ],
        }
    r = f.get("rental", {})
    if isinstance(r.get("blocked"), list):
        r["blocked_count"] = len(r["blocked"])
    if r.get("late_returns"):
        r["late_days"] = r["late_returns"][0].get("days_late")
        r["late_serial"] = r["late_returns"][0].get("serials", [""])[0]
        r["late_client"] = r["late_returns"][0].get("client")
    rj = f.get("rajesh", {})
    for d in rj.get("documents", []):
        if d.get("type") == "الإقامة":
            rj["residency_days"] = d.get("days_left")
    ap = f.get("approval", {})
    for st in ap.get("steps", []):
        if st.get("status") == "pending":
            ap["pending"] = st.get("role")
            ap["pending_name"] = st.get("name")
    if isinstance(f.get("docs_expired"), dict):
        f["docs_expired_total"] = f["docs_expired"].get("total")
    ids = {"الإقامة": "residency", "إجازة العمل": "permit", "جواز السفر": "passport", "باج دخول الموقع": "sitepass",
           "الموافقة الأمنية": "security", "سمة الدخول": "visa", "شهادة التأمين الصحي": "insurance"}
    for d in rj.get("documents", []):
        t = d.get("type", "")
        key = ids.get(t) or ("medical" if "الفحص" in t else None)
        if key:
            rj.setdefault("doc", {})[key] = d
    for i, st in enumerate(ap.get("steps", [])):
        at = st.get("approved_at_local") or ""
        st["when"] = (fmt(at, "dm") + " " + at[11:16]) if at else ""
    # v4: the route page's countdown, the payment clock's term, the fleet card
    import datetime as _dt
    def _d(x):
        try: return _dt.date.fromisoformat(str(x)[:10])
        except Exception: return None
    day = _d((f.get("as_of") or {}).get("day"))
    lb = f.get("late_batch") or {}
    if day and _d(lb.get("first_expiry")):
        lb["days_to_expiry"] = (_d(lb["first_expiry"]) - day).days
    oi = f.get("ar_oldest_invoice") or {}
    if _d(oi.get("date")) and _d(oi.get("due")):
        oi["term_days"] = (_d(oi["due"]) - _d(oi["date"])).days
    # v4: the redo lane's lists, as the pages address them
    ft = f.get("fsm_task") or {}
    if isinstance(ft.get("timeline"), list):
        ft["tl"] = {e.get("step"): e.get("at_local") for e in ft["timeline"]}
    cr = f.get("crane") or {}
    for e in cr.get("history") or []:
        if e.get("event") in ("issued", "expired", "blocked", "next_inspection"):
            cr[{"issued": "cert_issued", "next_inspection": "next_inspection"}.get(e["event"], e["event"])] = e.get("date")
    fl = f.get("fleet") or {}
    if fl.get("expired_list"):
        e = fl["expired_list"][0]
        fl["expired_row"] = {"plate": e.get("plate"), "doc": e.get("document"), "date": e.get("expiry"), "driver": e.get("driver"), "vehicle": e.get("vehicle")}
    ip = f.get("invoice_path") or {}
    if ip.get("reminders") and oi.get("term_days") is not None:
        ip["ticks"] = " ".join(str(oi["term_days"] + r.get("days_after_due", 0)) for r in ip["reminders"])
        ip["reminder_count"] = len(ip["reminders"])
        ip["reminder_dates"] = "، ".join(fmt(r.get("date", ""), "dm") for r in ip["reminders"])
