"""Coordinates: MGRS <-> WGS84, the Iraq box and simple checks. Pure Python."""
import math
import re

# Iraq with a margin of about 10 km
IRAQ_BOX = (29.0, 38.7, 37.45, 48.8)  # min lat, min lon, max lat, max lon

_A = 6378137.0
_F = 1 / 298.257223563
_E2 = _F * (2 - _F)
_EP2 = _E2 / (1 - _E2)
_K0 = 0.9996
_LAT_BANDS = "CDEFGHJKLMNPQRSTUVWX"
_SET_COLS = ["ABCDEFGH", "JKLMNPQR", "STUVWXYZ"]
_ROW_LETTERS = "ABCDEFGHJKLMNPQRSTUV"
_MGRS = re.compile(r"^(\d{1,2})([C-HJ-NP-X])([A-HJ-NP-Z])([A-HJ-NP-V])(\d*)$")


def in_iraq(lat, lon):
    return IRAQ_BOX[0] <= lat <= IRAQ_BOX[2] and IRAQ_BOX[1] <= lon <= IRAQ_BOX[3]


def distance_km(lat1, lon1, lat2, lon2):
    """Great-circle distance (haversine), kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def _utm_to_latlon(zone, northern, easting, northing):
    x = easting - 500000.0
    y = northing if northern else northing - 10000000.0
    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    m = y / _K0
    mu = m / (_A * (1 - _E2 / 4 - 3 * _E2 ** 2 / 64 - 5 * _E2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - _E2)) / (1 + math.sqrt(1 - _E2))
    phi1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
            + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
            + (151 * e1 ** 3 / 96) * math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    n1 = _A / math.sqrt(1 - _E2 * math.sin(phi1) ** 2)
    t1 = math.tan(phi1) ** 2
    c1 = _EP2 * math.cos(phi1) ** 2
    r1 = _A * (1 - _E2) / (1 - _E2 * math.sin(phi1) ** 2) ** 1.5
    d = x / (n1 * _K0)
    lat = phi1 - (n1 * math.tan(phi1) / r1) * (
        d ** 2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * _EP2) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * _EP2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = lon0 + (d - (1 + 2 * t1 + c1) * d ** 3 / 6
                  + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * _EP2 + 24 * t1 ** 2) * d ** 5 / 120) / math.cos(phi1)
    return math.degrees(lat), math.degrees(lon)


def _latlon_to_utm(lat, lon, zone=None):
    if zone is None:
        zone = int((lon + 180) // 6) + 1
    lon0 = math.radians((zone - 1) * 6 - 180 + 3)
    phi, lam = math.radians(lat), math.radians(lon)
    n = _A / math.sqrt(1 - _E2 * math.sin(phi) ** 2)
    t = math.tan(phi) ** 2
    c = _EP2 * math.cos(phi) ** 2
    a = math.cos(phi) * (lam - lon0)
    m = _A * ((1 - _E2 / 4 - 3 * _E2 ** 2 / 64 - 5 * _E2 ** 3 / 256) * phi
              - (3 * _E2 / 8 + 3 * _E2 ** 2 / 32 + 45 * _E2 ** 3 / 1024) * math.sin(2 * phi)
              + (15 * _E2 ** 2 / 256 + 45 * _E2 ** 3 / 1024) * math.sin(4 * phi)
              - (35 * _E2 ** 3 / 3072) * math.sin(6 * phi))
    easting = _K0 * n * (a + (1 - t + c) * a ** 3 / 6 + (5 - 18 * t + t ** 2 + 72 * c - 58 * _EP2) * a ** 5 / 120) + 500000.0
    northing = _K0 * (m + n * math.tan(phi) * (a ** 2 / 2 + (5 - t + 9 * c + 4 * c ** 2) * a ** 4 / 24
                                              + (61 - 58 * t + t ** 2 + 600 * c - 330 * _EP2) * a ** 6 / 720))
    if lat < 0:
        northing += 10000000.0
    return zone, easting, northing


def parse_mgrs(text):
    """MGRS string -> (lat, lon) of the square's centre, or None if it is not valid MGRS.

    Accepts spaces ('38S KC 87787 32517') and 1..5-digit precision.
    """
    s = re.sub(r"\s+", "", str(text or "")).upper()
    m = _MGRS.match(s)
    if not m:
        return None
    zone, band, col, row, digits = int(m.group(1)), m.group(2), m.group(3), m.group(4), m.group(5)
    if not 1 <= zone <= 60 or len(digits) % 2 or len(digits) > 10:
        return None
    half = len(digits) // 2
    precision = 10 ** (5 - half)
    e_in = int(digits[:half] or 0) * precision
    n_in = int(digits[half:] or 0) * precision
    set_cols = _SET_COLS[(zone - 1) % 3]
    if col not in set_cols:
        return None
    easting = (set_cols.index(col) + 1) * 100000 + e_in + precision / 2
    row_offset = 5 if zone % 2 == 0 else 0
    row_idx = (_ROW_LETTERS.index(row) - row_offset) % 20
    # northing of the bottom of the latitude band, then add 2,000 km cycles until inside the band
    band_lat = -80 + _LAT_BANDS.index(band) * 8
    _z, _e, band_north = _latlon_to_utm(band_lat, (zone - 1) * 6 - 180 + 3, zone)
    northern = band >= "N"
    if not northern:
        band_north -= 10000000.0
    northing = row_idx * 100000 + n_in + precision / 2
    while northing < band_north - 100000:
        northing += 2000000
    lat, lon = _utm_to_latlon(zone, northern, easting, northing if northern else northing + 10000000.0)
    return lat, lon


def to_mgrs(lat, lon, digits=5):
    """WGS84 -> MGRS string (northern hemisphere use is enough for Iraq)."""
    zone, easting, northing = _latlon_to_utm(lat, lon)
    band = _LAT_BANDS[min(int((lat + 80) // 8), 19)]
    col = _SET_COLS[(zone - 1) % 3][int(easting // 100000) - 1]
    row_offset = 5 if zone % 2 == 0 else 0
    row = _ROW_LETTERS[(int(northing // 100000) + row_offset) % 20]
    e = int(easting % 100000) // 10 ** (5 - digits)
    n = int(northing % 100000) // 10 ** (5 - digits)
    return f"{zone}{band}{col}{row}{e:0{digits}d}{n:0{digits}d}"


def parse_decimal(value):
    """'33.87', '33,87', 33.87 -> float; anything else -> None."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "")
    if text.count(",") == 1 and "." not in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None
