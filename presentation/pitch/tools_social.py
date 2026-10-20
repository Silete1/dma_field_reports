"""Social images for the edition: fill social.src.html with the same figures as the PDF, then render.

    py -3.11 tools_social.py && node social.mjs

Figures: ../figures.json through sector_derive.derive (as build.py), falling back to targets.json. Writes social.html;
social.mjs screenshots every <section class="so" data-name> at its own size into output/<slug>/social/<name>.png.
"""
import importlib.util
import json
import pathlib
import re
import sys

H = pathlib.Path(__file__).resolve().parent
targets = json.loads((H / "targets.json").read_text(encoding="utf-8"))
fp = H.parent / "figures.json"
figures = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}
spec = importlib.util.spec_from_file_location("bld", H / "build.py")
src = (H / "build.py").read_text(encoding="utf-8")
ns = {"re": re, "json": json}
exec(src[src.index("MONTHS = "):src.index("def lookup")], ns)          # the kit's fmt(), unchanged
fmt = ns["fmt"]
if True:   # also before the DB lands, so verified sector facts fill in (as build.py)
    sd = importlib.util.spec_from_file_location("sector_derive", H / "sector_derive.py")
    mod = importlib.util.module_from_spec(sd); sd.loader.exec_module(mod); mod.derive(figures, fmt)
missing, fallback = [], []


def look(key):
    for srcd, name in ((figures, "f"), (targets, "t")):
        cur = srcd
        for part in key.split("."):
            cur = cur.get(part) if isinstance(cur, dict) else None
            if cur is None:
                break
        if cur is not None:
            if name == "t":
                fallback.append(key)
            return cur
    missing.append(key)
    return f"⟦{key}⟧"


html = (H / "social.src.html").read_text(encoding="utf-8")
html = re.sub(r"\{\{\s*([\w.]+)\s*(?:\|\s*(\w+))?\s*\}\}", lambda m: fmt(look(m.group(1)), m.group(2) or ""), html)
html = html.replace("<!--ICONS-->", (H / "assets" / "img" / "icons-sprite.html").read_text(encoding="utf-8"))
if re.search(r"[—–]", re.sub(r"<[^>]+>", "", re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S))):
    missing.append("an em/en dash is visible")
(H / "social.html").write_text(html, encoding="utf-8")
print(json.dumps({"figures": "figures.json" if figures else "targets.json", "fallback": sorted(set(fallback)), "errors": missing}, ensure_ascii=False))
sys.exit(1 if missing else 0)
