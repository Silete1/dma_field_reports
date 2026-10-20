"""Build the sector pitch page file: figures + captures + markers -> ed.html   (ANU sector-pitch kit)

    py -3.11 build.py [--caps=final]

* Settings: pitch.json (name, figures files, …).
* Figures: `{{key.sub|fmt}}` in pages.html, from ../figures.json (the demo database) plus any extra figure
  files named in pitch.json "extra_figures" ({"designer_raw": "designer/figures_designer.json"}), over
  targets.json (fallbacks used until the database exists; publishing holds while any is used).
  The sector's own mapping lives in sector_derive.py: `def derive(f, fmt)` turns raw figures into page keys.
  fmt: int · usd · usd2 · usdm · iqdb · d1 · pct · dm · dmy · hm · json · raw.
* Captures: `<img class="cap" data-cap="NAME" ...>` takes ../captures/<caps>/NAME.png when it exists,
  otherwise a placeholder of the size in placeholders.json; its markers (NAME.markers.json, or the
  placeholder's) are written into window.MARKERS for layout.js.
* <!--ICONS--> is replaced by assets/img/icons-sprite.html (py -3.11 tools_icons.py).
* Page numbers: every <p class="pno"> is renumbered from the order of the sections; {{page.<data-page>}} prints a
  section's page number (use it in index/ladder references), so pages can be added, dropped or reordered freely.
Writes ed.html and out/build.json (fallback keys, placeholders, errors). Exit 1 on errors.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                      # business_intel/tmp/<slug> (the render server's root)
CFG = json.loads((HERE / "pitch.json").read_text(encoding="utf-8"))
CAPDIR = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--caps=")), CFG.get("caps", "final"))
CAPS = ROOT / "captures" / CAPDIR
errors, fallback, placeholders = [], [], []

targets = json.loads((HERE / "targets.json").read_text(encoding="utf-8")) if (HERE / "targets.json").exists() else {}
figs_path = ROOT / "figures.json"
figures = json.loads(figs_path.read_text(encoding="utf-8")) if figs_path.exists() else {}
for key, rel in (CFG.get("extra_figures") or {}).items():
    p = ROOT / rel
    if p.exists():
        figures[key] = json.loads(p.read_text(encoding="utf-8"))

MONTHS = ["كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران", "تموز", "آب", "أيلول", "تشرين الأول", "تشرين الثاني", "كانون الأول"]


def fmt(v, f):
    if f == "json":
        return json.dumps(v, ensure_ascii=False).replace("—", "، ").replace("–", "، ")
    if isinstance(v, str):
        v = v.replace(" — ", "، ").replace("—", "، ").replace(" – ", "، ")   # house rule: no em/en dashes
    if f in ("dm", "dmy", "hm") and isinstance(v, str) and re.match(r"\d{4}-\d{2}-\d{2}", v):
        y, mo, d = int(v[:4]), int(v[5:7]), int(v[8:10])
        if f == "hm":
            return v[11:16]
        return f"{d} {MONTHS[mo - 1]}" + (f" {y}" if f == "dmy" else "")
    if f in ("", "raw") or isinstance(v, str):
        return str(v)
    if f == "int":
        return f"{round(v):,}"
    if f == "usd2":
        return f"${v:,.2f}"
    if f == "usd":
        return f"${round(v):,}"
    if f == "usdm":
        return f"{v / 1e6:.2f}"
    if f == "iqdb":
        return f"{v / 1e9:.2f}"
    if f == "d1":
        return f"{v:.1f}"
    if f == "pct":
        return f"{v * 100:.1f}%"
    return str(v)


def lookup(key):
    for src, name in ((figures, "figures"), (targets, "targets")):
        cur = src
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
                cur = cur[int(part)]
            else:
                cur = None
                break
        if cur is not None:
            if name == "targets":
                fallback.append(key)
            return cur
    errors.append(f"missing figure {key}")
    return f"⟦{key}⟧"


# the sector's own figure mapping
sd = HERE / "sector_derive.py"
if sd.exists():   # also before the DB lands, so verified sector facts show on placeholders
    spec = importlib.util.spec_from_file_location("sector_derive", sd)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        mod.derive(figures, fmt)
    except Exception as e:  # a broken mapping must show, not silently fall back
        errors.append(f"sector_derive.derive failed: {e!r}")

src = (HERE / "pages.html").read_text(encoding="utf-8")
sprite = HERE / "assets" / "img" / "icons-sprite.html"
if "<!--ICONS-->" in src:
    if sprite.exists():
        src = src.replace("<!--ICONS-->", sprite.read_text(encoding="utf-8"))
    else:
        errors.append("assets/img/icons-sprite.html missing: run py -3.11 tools_icons.py")
html = re.sub(r"\{\{\s*([\w.]+)\s*(?:\|\s*(\w+))?\s*\}\}",
              lambda m: m.group(0) if m.group(1).startswith("page.") else fmt(lookup(m.group(1)), m.group(2) or ""), src)

ph_spec = json.loads((HERE / "placeholders.json").read_text(encoding="utf-8")) if (HERE / "placeholders.json").exists() else {}
markers = {}


def norm_markers(d):
    crop = d.get("crop_css") or {}
    w = crop.get("width") or d.get("w")
    h = crop.get("height") or d.get("h")
    out = []
    for m in d.get("markers", []):
        b = m.get("box") or m.get("box_css")
        if isinstance(b, dict):
            b = [b["x"], b["y"], b["width"], b["height"]]
        out.append({"n": m["n"], "box": b, "label": m.get("label", "")})
    return {"w": w, "h": h, "markers": out}


def placeholder_svg(name, w, h):
    (HERE / "placeholders").mkdir(exist_ok=True)
    path = HERE / "placeholders" / f"{name}.svg"
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<rect width="100%" height="100%" fill="#F1F5F9"/>'
        f'<g stroke="#CBD5E1" stroke-width="1">' + "".join(f'<line x1="0" y1="{y}" x2="{w}" y2="{y}"/>' for y in range(40, h, 40)) + "</g>"
        f'<text x="50%" y="50%" text-anchor="middle" font-family="Anu Mono, monospace" font-size="28" fill="#475569">{name} {w}x{h}</text></svg>',
        encoding="utf-8")
    return f"placeholders/{name}.svg"


def swap(m):
    tag = m.group(0)
    name = re.search(r'data-cap="([\w-]+)"', tag).group(1)
    png = CAPS / f"{name}.png"
    mj = CAPS / f"{name}.markers.json"
    if png.exists():
        src_attr = f"../captures/{CAPDIR}/{name}.png"
        if mj.exists():
            markers[name] = norm_markers(json.loads(mj.read_text(encoding="utf-8")))
        cls_extra = ""
    else:
        spec = ph_spec.get(name)
        if not spec:
            errors.append(f"no placeholder spec for {name}")
            spec = {"w": 1060, "h": 560, "markers": []}
        src_attr = placeholder_svg(name, spec["w"], spec["h"])
        markers[name] = norm_markers(spec)
        placeholders.append(name)
        cls_extra = " ph"
    tag = re.sub(r'\ssrc="[^"]*"', "", tag)
    tag = tag.replace('class="cap', f'class="cap{cls_extra}', 1)
    if name in markers and markers[name]["w"] and "data-w=" not in tag:
        tag = tag.replace("<img", f'<img data-w="{markers[name]["w"]}"', 1)
    return tag.replace("<img", f'<img src="{src_attr}"', 1)


html = re.sub(r'<img\b[^>]*class="cap[^"]*"[^>]*>', swap, html)

# page numbers: every <p class="pno"> is renumbered from the section order ("06 / 13"), so pages can be added,
# removed or reordered freely; index/ladder page references (e.g. <span class="pgr">) can use {{page.<data-page>}}.
parts = re.split(r'(<section class="pg\b)', html)
total = html.count('<section class="pg')
out, n = [parts[0]], 0
for i in range(1, len(parts), 2):
    n += 1
    body = re.sub(r'<p class="pno">.*?</p>', f'<p class="pno"><b>{n:02d}</b> / {total}</p>', parts[i + 1], count=1, flags=re.S)
    out += [parts[i], body]
html = "".join(out)
pages = {m.group(1): f"{k:02d}" for k, m in enumerate(re.finditer(r'<section class="pg[^"]*" data-page="([\w-]+)"', html), 1)}
def page_ref(m):
    if m.group(1) not in pages:
        errors.append(f"page reference {m.group(1)} names no section data-page")
    return pages.get(m.group(1), "??")


html = re.sub(r"\{\{page\.([\w-]+)\}\}", page_ref, html)
html = html.replace("<!--MARKERS-->", "<script>window.MARKERS=" + json.dumps(markers, ensure_ascii=False) + ";</script>")
visible = re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S)
if re.search(r"[—–]", re.sub(r"<[^>]+>", "", visible)):
    errors.append("an em/en dash is on a page (house rule: use a comma or a new line)")
(HERE / "ed.html").write_text(html, encoding="utf-8")
res = {"figures": "figures.json" if figures else "targets.json", "caps": CAPDIR, "fallback_keys": sorted(set(fallback)),
       "placeholders": placeholders, "errors": errors}
(HERE / "out").mkdir(exist_ok=True)
(HERE / "out" / "build.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
sys.exit(1 if errors else 0)
