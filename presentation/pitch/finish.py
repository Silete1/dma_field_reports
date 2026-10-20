"""Finish the sector PDF: metadata, size, font check, then publish (or hold).   (ANU sector-pitch kit)

    py -3.11 finish.py [--publish]

Settings come from pitch.json: name, publish_dir (relative to the repo's business_intel folder), pages (optional),
title, subject, keywords. Holds while the build used placeholder captures or fallback (target) figures,
while build.py or render.mjs reported errors/fails, when a fallback font (Times, Arial, Segoe, Cambria,
Consolas) got embedded, or when the page count is not the configured one.
"""
import json
import shutil
import sys
from pathlib import Path

import fitz  # PyMuPDF

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "pitch.json").read_text(encoding="utf-8"))
BI = HERE.parents[2]                                   # business_intel
PUB = BI / CFG["publish_dir"]
NAME = CFG["name"]
pdf = HERE / "out" / f"{NAME}.pdf"
build = json.loads((HERE / "out" / "build.json").read_text(encoding="utf-8"))
render = json.loads((HERE / "out" / "render.json").read_text(encoding="utf-8"))

doc = fitz.open(pdf)
doc.set_metadata({"title": CFG.get("title", NAME), "author": "ANU", "subject": CFG.get("subject", ""),
                  "creator": "ANU sector-pitch kit (Chromium print + PyMuPDF)", "producer": "ANU",
                  "keywords": CFG.get("keywords", "ANU, Odoo 19")})
fonts = sorted({f[3].split("+")[-1] for p in doc for f in p.get_fonts(full=True)})
pages = doc.page_count
tmp = pdf.with_suffix(".tmp.pdf")
doc.save(tmp, garbage=3, deflate=True)
doc.close()
tmp.replace(pdf)
hold = []
if build["placeholders"]:
    hold.append(f"{len(build['placeholders'])} placeholder captures: {', '.join(build['placeholders'])}")
if build["fallback_keys"]:
    hold.append(f"{len(build['fallback_keys'])} figures from targets.json: {', '.join(build['fallback_keys'][:8])}")
if build["errors"] or render["fails"]:
    hold.append("gates: " + "; ".join(build["errors"] + render["fails"])[:300])
bad = [f for f in fonts if any(x in f for x in ("Segoe", "Cambria", "Times", "Arial", "Consolas"))]
if bad:
    hold.append(f"fallback fonts embedded: {bad} (an SVG <text> or a ✓ glyph without a brand font; see references/08-lessons.md)")
if CFG.get("pages") and pages != CFG["pages"]:
    hold.append(f"{pages} pages, {CFG['pages']} expected (pitch.json; remove \"pages\" to skip this check)")
res = {"pdf": str(pdf), "bytes": pdf.stat().st_size, "pages": pages, "fonts": fonts, "hold": hold, "published": False}
if "--publish" in sys.argv and not hold:
    PUB.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pdf, PUB / pdf.name)
    sheet = HERE / "out" / "sheet.png"
    if sheet.exists():
        shutil.copyfile(sheet, PUB / f"{NAME} - sheet.png")
    res["published"] = str(PUB / pdf.name)
print(json.dumps(res, ensure_ascii=False, indent=1))
sys.exit(1 if hold else 0)
