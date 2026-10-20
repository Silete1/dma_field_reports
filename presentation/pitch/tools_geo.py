"""Iraq line art for the delivery edition: project the country outline and the 18 governorates into one SVG space.

    py -3.11 tools_geo.py

Source: geoBoundaries gbOpen IRQ ADM0/ADM1 (simplified), CC0 1.0 (public domain), downloaded to geo/.
Projection: equirectangular around 33°N (x scaled by cos 33°), 1000 units wide, north up.
Writes assets/geo/iraq.js: window.IRQ = {w, h, outline, govs:[{k, ar, d, cx, cy}], cities:{k:[x, y]}}
and a copy for the film lane at ../film/src/iraq.js (same drawing in the PDF and the film).
"""
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
GEO = HERE / "geo"
LAT0 = 33.0
K = math.cos(math.radians(LAT0))

AR = {"Al-Anbar": ("anbar", "الأنبار"), "Karbala": ("karbala", "كربلاء"), "An-Najaf": ("najaf", "النجف"),
      "Babil": ("babil", "بابل"), "Baghdad": ("baghdad", "بغداد"), "Al-Qadisiyah": ("qadisiyah", "القادسية"),
      "Al-Muthanna": ("muthanna", "المثنى"), "Dhi Qar": ("dhiqar", "ذي قار"), "Al-Basrah": ("basra", "البصرة"),
      "Maysan": ("maysan", "ميسان"), "Wasit": ("wasit", "واسط"), "Ninawa": ("ninawa", "نينوى"), "Dohuk": ("dohuk", "دهوك"),
      "Salah al-Din": ("salahaddin", "صلاح الدين"), "Diyala": ("diyala", "ديالى"), "Kirkuk": ("kirkuk", "كركوك"),
      "Erbil": ("erbil", "أربيل"), "Al-Sulaimaniyah": ("sulaymaniyah", "السليمانية")}
# governorate capitals and the headline's places (lon, lat); public geography
CITIES = {"baghdad": (44.366, 33.315), "basra": (47.783, 30.508), "zubair": (47.705, 30.392), "erbil": (44.009, 36.191),
          "mosul": (43.130, 36.340), "najaf": (44.336, 32.000), "karbala": (44.024, 32.616), "hilla": (44.420, 32.483),
          "kirkuk": (44.392, 35.468), "sulaymaniyah": (45.435, 35.557), "dohuk": (42.999, 36.867), "ramadi": (43.300, 33.426),
          "tikrit": (43.679, 34.607), "baqubah": (44.655, 33.750), "kut": (45.819, 32.505), "amarah": (47.140, 31.836),
          "nasiriyah": (46.257, 31.052), "samawah": (45.294, 31.332), "diwaniyah": (44.925, 31.990)}
# which city stands for which governorate on the fee map
CAPITAL = {"anbar": "ramadi", "karbala": "karbala", "najaf": "najaf", "babil": "hilla", "baghdad": "baghdad",
           "qadisiyah": "diwaniyah", "muthanna": "samawah", "dhiqar": "nasiriyah", "basra": "basra", "maysan": "amarah",
           "wasit": "kut", "ninawa": "mosul", "dohuk": "dohuk", "salahaddin": "tikrit", "diyala": "baqubah", "kirkuk": "kirkuk",
           "erbil": "erbil", "sulaymaniyah": "sulaymaniyah"}


def rings(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [p[0] for p in polys]            # outer rings only


def dp(pts, eps):
    """Douglas-Peucker on a list of (x, y)."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1e-9
    dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        x0, y0 = pts[i]
        d = abs(dy * x0 - dx * y0 + x2 * y1 - y2 * x1) / L
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return dp(pts[: idx + 1], eps)[:-1] + dp(pts[idx:], eps)
    return [pts[0], pts[-1]]


def dpring(pts, eps):
    """A closed ring: split at the point farthest from the first, simplify both halves."""
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    far = max(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]))
    a = dp(pts[: far + 1], eps)
    b = dp(pts[far:] + [pts[0]], eps)
    return a[:-1] + b[:-1]


def main():
    adm0 = json.loads((GEO / "adm0.geojson").read_text(encoding="utf-8"))
    adm1 = json.loads((GEO / "adm1.geojson").read_text(encoding="utf-8"))
    allpts = [pt for f in adm0["features"] for r in rings(f["geometry"]) for pt in r]
    lon0, lon1 = min(p[0] for p in allpts), max(p[0] for p in allpts)
    lat0, lat1 = min(p[1] for p in allpts), max(p[1] for p in allpts)
    S = 1000 / ((lon1 - lon0) * K)
    W, H = 1000, round((lat1 - lat0) * S)
    P = lambda lon, lat: ((lon - lon0) * K * S, (lat1 - lat) * S)
    path = lambda pts: "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"

    outline = []
    for f in adm0["features"]:
        for r in rings(f["geometry"]):
            outline.append(path(dpring([P(*p) for p in r], 1.1)))
    govs = []
    for f in adm1["features"]:
        k, ar = AR[f["properties"]["shapeName"]]
        ds = [path(dpring([P(*p) for p in r], 1.6)) for r in rings(f["geometry"])]
        cx, cy = P(*CITIES[CAPITAL[k]])
        govs.append({"k": k, "ar": ar, "d": " ".join(ds), "cx": round(cx, 1), "cy": round(cy, 1), "city": CAPITAL[k]})
    cities = {k: [round(c, 1) for c in P(*v)] for k, v in CITIES.items()}
    data = {"w": W, "h": H, "outline": " ".join(outline), "govs": govs, "cities": cities,
            "src": "geoBoundaries gbOpen IRQ ADM0/ADM1 (simplified), CC0 1.0"}
    js = "// Iraq line art (tools_geo.py). geoBoundaries gbOpen IRQ, CC0 1.0 public domain.\nwindow.IRQ = " + json.dumps(data, ensure_ascii=False) + ";\n"
    out = HERE / "assets" / "geo"
    out.mkdir(parents=True, exist_ok=True)
    (out / "iraq.js").write_text(js, encoding="utf-8")
    film = HERE.parent / "film" / "src"   # the film shares the same drawing
    if film.exists():
        (film / "iraq.js").write_text(js, encoding="utf-8")
    n = data["outline"].count("L") + 1
    print(f"iraq.js: {W}x{H}, outline {n} pts, {len(govs)} governorates, {len(js)//1024} KB")


if __name__ == "__main__":
    main()
