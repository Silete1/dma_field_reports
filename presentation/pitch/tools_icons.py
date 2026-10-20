"""Write assets/img/icons-sprite.html: the film's site icons (92 grid) + Tabler outline icons (24 grid, MIT) as <symbol>s.
(ANU sector-pitch kit)

    py -3.11 tools_icons.py

Use in pages: <svg class="ic tb"><use href="#i-sofa"/></svg>  (Tabler)   ·   <svg class="ic"><use href="#i-hq"/></svg>  (site)
Add a sector's icons to icons.json {"key": "tabler-name"} next to this file; browse names at https://tabler.io/icons.
Tabler is fetched once with `npm pack @tabler/icons@3.48.0` into vendor/ (MIT). Never use a Unicode glyph (✓ ✗ ★)
as an icon: the brand fonts lack them, a system font gets embedded and finish.py holds.
"""
import json
import pathlib
import re
import subprocess
import tarfile

HERE = pathlib.Path(__file__).resolve().parent
VENDOR = HERE / "vendor"
T = VENDOR / "tabler" / "icons" / "outline"
if not T.exists():
    VENDOR.mkdir(exist_ok=True)
    subprocess.run("npm pack @tabler/icons@3.48.0 --silent", cwd=VENDOR, shell=True, check=True)
    tgz = next(VENDOR.glob("tabler-icons-*.tgz"))
    with tarfile.open(tgz) as tf:
        tf.extractall(VENDOR)
    (VENDOR / "package").rename(VENDOR / "tabler")
    tgz.unlink()

# the film's own site icons (same drawings in the PDF and the film): office, field, hospital, depot, camp
FILM = {
 "hq": '<path d="M22 84V20h30v64M52 84V38h20v46M14 84h66"/><path d="M30 30h14M30 42h14M30 54h14M30 66h14M59 50h6M59 62h6"/>',
 "field": '<path d="M8 84h76M20 84l14-44 14 44M26 64h16"/><path d="M14 36l40-12 6 6M54 24l-2 22"/><path d="M72 84V36"/><path class="f" d="M72 30c-6-6-3-12 0-18 3 6 7 10 0 18z"/>',
 "hosp": '<path d="M12 84V34h68v50M6 84h80M40 84V68h12v16"/><path class="f" d="M40 12h12v10h10v12H52v10H40V34H30V22h10z"/><path d="M40 12h12v10h10v12H52v10H40V34H30V22h10z"/><path d="M22 46h8M62 46h8M22 58h8M62 58h8"/>',
 "depot": '<path d="M6 44L46 18l40 26M12 40v24h68V40"/><path d="M10 84V70h40v14M50 74h16l8 10H50"/><circle cx="22" cy="86" r="4"/><circle cx="62" cy="86" r="4"/>',
 "camp": '<path d="M6 84h80"/><path d="M10 84V62h22v22M36 84V62h22v22M62 84V62h22v22"/><path d="M14 50h66M46 50V14"/><path class="f" d="M46 14h20l-6 7 6 7H46"/><path d="M46 14h20l-6 7 6 7H46"/>',
}
# common Tabler icons used by earlier editions (key -> tabler outline name)
TAB = {"passport": "book-2", "idcard": "id", "permit": "license", "medical": "test-pipe", "sitepass": "id-badge-2", "security": "shield-check",
       "truck": "truck", "crane": "crane", "invoice": "file-invoice", "clock": "clock-hour-4", "ac": "air-conditioning", "chat": "message-circle",
       "check": "check", "checks": "checks", "sofa": "sofa", "armchair": "armchair", "bed": "bed", "factory": "building-factory-2", "tools": "tools",
       "container": "container", "home": "home", "store": "building-store", "delivery": "truck-delivery", "register": "cash-register",
       "ruler": "ruler-measure", "cut": "cut", "wood": "wood", "warehouse": "building-warehouse", "ship": "ship", "cube": "cube-3d-sphere",
       "dollar": "currency-dollar", "coins": "coins", "receipt": "receipt", "due": "calendar-due", "hammer": "hammer"}
extra = HERE / "icons.json"
if extra.exists():
    TAB.update(json.loads(extra.read_text(encoding="utf-8")))

# a sector's own film-grid drawings (92 grid, shared with the film): icons_film.json {"key": "<svg body>"}
xfilm = HERE / "icons_film.json"
if xfilm.exists():
    FILM.update(json.loads(xfilm.read_text(encoding="utf-8")))

out = ['<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>']
for k, body in FILM.items():
    out.append(f'<symbol id="i-{k}" viewBox="0 0 92 92">{body}</symbol>')
missing = []
for k, n in TAB.items():
    f = T / f"{n}.svg"
    if not f.exists():
        missing.append(n); continue
    s = f.read_text(encoding="utf-8")
    paths = [p for p in re.findall(r"<(?:path|circle|rect|line|polyline|ellipse|polygon)[^>]*/>", s) if 'stroke="none"' not in p]
    out.append(f'<symbol id="i-{k}" viewBox="0 0 24 24" class="tb">{"".join(paths)}</symbol>')
out.append("</defs></svg>")
(HERE / "assets" / "img" / "icons-sprite.html").write_text("\n".join(out), encoding="utf-8")
print(len(out) - 2, "symbols", ("missing tabler names: " + ", ".join(missing)) if missing else "")
