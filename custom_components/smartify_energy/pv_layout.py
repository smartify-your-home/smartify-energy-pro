"""PV surfaces for the calculated forecast: geometry, validation, migration.

A surface is drawn on an aerial photo (area = roof polygon, line = facade or
simple edge) or kept as a manual entry (migrated from the old option fields).
The azimuth is derived from the geometry: for an area it is the outward normal
of the marked eave edge (Traufkante), for a line one of its two normals
(selectable with ``flip``). Tilt is always entered by the user.

No Home Assistant imports here so the module can be tested offline.
"""
from __future__ import annotations

import re
from math import atan2, cos, degrees, hypot, isfinite, log, pi, radians, tan
from typing import Any

CONF_SOLAR_SURFACES = "solar_surfaces"
MAX_SURFACES = 4  # solar_model uses at most four surfaces
BIFACIALITY_DEFAULT = 0.7  # typical rear/front ratio of bifacial modules
CLOSE_TOLERANCE_M = 0.3  # last area point this close to the first = closing click
EARTH_RADIUS = 6378137.0
KINDS = ("area", "line", "manual")
INPUTS = ("kwp", "modules")

# basemap.at orthophoto (Austria), WMTS google3857, CC BY 4.0
MAP_ZOOM_DEFAULT = 19
MAP_ZOOM_MIN = 17
MAP_ZOOM_MAX = 20
MAP_GRID = 5  # 5 × 5 tiles of 256 px around the centre
MAP_TILE_URLS = (
    "https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/{z}/{y}/{x}.jpeg",
    "https://maps.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/{z}/{y}/{x}.jpeg",
)
MAP_ATTRIBUTION = "Luftbild: basemap.at (CC BY 4.0)"


# ── Legacy option fields (solar_1_kwp … solar_4_azimuth) ─────────────────────
def legacy_surfaces(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Old form fields → manual surfaces (only arrays with kWp > 0)."""
    out = []
    for i in range(1, 5):
        try:
            kwp = float(cfg.get(f"solar_{i}_kwp") or 0)
        except (TypeError, ValueError):
            continue
        if kwp <= 0:
            continue
        out.append({
            "id": f"s{i}", "name": f"Fläche {i}", "kind": "manual", "points": [],
            "edge": 0, "flip": False,
            "tilt": float(cfg.get(f"solar_{i}_tilt", 30) or 0),
            "azimuth": float(cfg.get(f"solar_{i}_azimuth", 180) or 0) % 360,
            "input": "kwp", "kwp": kwp, "modules": 0, "module_wp": 0.0, "area_m2": None,
            "bifacial": False, "bifaciality": BIFACIALITY_DEFAULT,
        })
    return out


def legacy_mirror(surfaces: list[dict[str, Any]]) -> dict[str, float]:
    """Write the first four surfaces into the old fields as well.

    Keeps a downgrade to an older SEP version working; unused slots get 0 kWp
    so values from the original setup data cannot reappear.
    """
    out: dict[str, float] = {}
    for i in range(1, 5):
        s = surfaces[i - 1] if i <= len(surfaces) else None
        out[f"solar_{i}_kwp"] = round(effective_kwp(s), 3) if s else 0.0
        out[f"solar_{i}_tilt"] = float(s["tilt"]) if s else 30.0
        out[f"solar_{i}_azimuth"] = float(s["azimuth"]) if s else 180.0
    return out


def surfaces_from_config(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Stored surfaces (new format) or migrated legacy fields."""
    stored = cfg.get(CONF_SOLAR_SURFACES)
    if isinstance(stored, list):
        result = []
        for raw in stored[:MAX_SURFACES]:
            try:
                result.append(normalize_surface(raw))
            except ValueError:
                continue
        return result
    return legacy_surfaces(cfg)


def effective_kwp(surface: dict[str, Any] | None) -> float:
    if not surface:
        return 0.0
    if surface.get("input") == "modules":
        return float(surface.get("modules") or 0) * float(surface.get("module_wp") or 0) / 1000
    return float(surface.get("kwp") or 0)


def model_surfaces(surfaces: list[dict[str, Any]]) -> list[dict[str, float]]:
    """What the solar model needs: kWp, tilt, azimuth, bifaciality (kWp > 0 only)."""
    out = []
    for s in surfaces[:MAX_SURFACES]:
        if effective_kwp(s) <= 0:
            continue
        item = {"kwp": round(effective_kwp(s), 3), "tilt": float(s["tilt"]), "azimuth": float(s["azimuth"])}
        if s.get("bifacial"):
            item["bifaciality"] = float(s.get("bifaciality") or BIFACIALITY_DEFAULT)
        out.append(item)
    return out


# ── Geometry ─────────────────────────────────────────────────────────────────
def _local_xy(points: list[list[float]]) -> list[tuple[float, float]]:
    """lat/lon → metres east/north around the first point (small areas)."""
    lat0, lon0 = points[0]
    k = cos(radians(lat0))
    return [(radians(lon - lon0) * EARTH_RADIUS * k, radians(lat - lat0) * EARTH_RADIUS)
            for lat, lon in points]


def _azimuth(east: float, north: float) -> float:
    return round((degrees(atan2(east, north)) + 360) % 360, 1)


def _edge_normals(xy, edge: int) -> tuple[tuple[float, float], tuple[float, float]]:
    (x1, y1), (x2, y2) = xy[edge], xy[(edge + 1) % len(xy)]
    ex, ey = x2 - x1, y2 - y1
    return (ey, -ex), (-ey, ex)


def area_outward_azimuth(points: list[list[float]], edge: int, flip: bool = False) -> float:
    """Outward normal of the eave edge = direction the roof plane faces."""
    xy = _local_xy(points)
    cx = sum(x for x, _ in xy) / len(xy)
    cy = sum(y for _, y in xy) / len(xy)
    (x1, y1), (x2, y2) = xy[edge], xy[(edge + 1) % len(xy)]
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    n1, n2 = _edge_normals(xy, edge)
    outward = n1 if n1[0] * (mx - cx) + n1[1] * (my - cy) >= 0 else n2
    if flip:
        outward = (-outward[0], -outward[1])
    return _azimuth(*outward)


def line_azimuth(points: list[list[float]], flip: bool = False) -> float:
    """Normal of a line; default the one closer to south, flip selects the other."""
    xy = _local_xy(points)
    n1, n2 = _edge_normals(xy, 0)
    a1, a2 = _azimuth(*n1), _azimuth(*n2)
    first, second = (a1, a2) if abs(a1 - 180) <= abs(a2 - 180) else (a2, a1)
    return second if flip else first


def projected_area_m2(points: list[list[float]]) -> float:
    xy = _local_xy(points)
    s = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(xy, xy[1:] + xy[:1], strict=True))
    return round(abs(s) / 2, 1)


def default_edge(points: list[list[float]]) -> int:
    """Longer edges first; among them the one facing closest to south."""
    xy = _local_xy(points)
    lengths = [hypot(xy[(i + 1) % len(xy)][0] - xy[i][0], xy[(i + 1) % len(xy)][1] - xy[i][1])
               for i in range(len(xy))]
    longest = max(lengths)
    candidates = [i for i, length in enumerate(lengths) if length >= 0.5 * longest]
    return min(candidates, key=lambda i: abs(area_outward_azimuth(points, i) - 180))


# ── Validation ───────────────────────────────────────────────────────────────
def _num(raw: dict, key: str, low: float, high: float, default: float | None = None) -> float:
    value = raw.get(key, default)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key}: keine Zahl") from None
    if not isfinite(number) or not low <= number <= high:
        raise ValueError(f"{key}: muss zwischen {low:g} und {high:g} liegen")
    return number


def _points(raw: Any) -> list[list[float]]:
    if not isinstance(raw, list):
        raise ValueError("points: Liste erwartet")
    out = []
    for p in raw:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise ValueError("points: [lat, lon] erwartet")
        lat, lon = float(p[0]), float(p[1])
        if not (isfinite(lat) and isfinite(lon) and -85 <= lat <= 85 and -180 <= lon <= 180):
            raise ValueError("points: Koordinate außerhalb des gültigen Bereichs")
        out.append([round(lat, 8), round(lon, 8)])
    return out


def normalize_surface(raw: Any) -> dict[str, Any]:
    """Validate one surface and derive azimuth and area from its geometry."""
    if not isinstance(raw, dict):
        raise ValueError("Fläche: Objekt erwartet")
    kind = raw.get("kind", "manual")
    if kind not in KINDS:
        raise ValueError("kind: area, line oder manual")
    name = str(raw.get("name") or "").strip()[:40] or "PV-Fläche"
    sid = str(raw.get("id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,24}", sid):
        raise ValueError("id: ungültig")
    flip = bool(raw.get("flip", False))
    tilt = _num(raw, "tilt", 0, 90, 30)
    bifacial = bool(raw.get("bifacial", False))
    bifaciality = _num(raw, "bifaciality", 0.5, 1.0, BIFACIALITY_DEFAULT) if bifacial else BIFACIALITY_DEFAULT
    mode = raw.get("input", "kwp")
    if mode not in INPUTS:
        raise ValueError("input: kwp oder modules")
    kwp = modules = module_wp = 0.0
    if mode == "kwp":
        kwp = _num(raw, "kwp", 0.01, 100)
    else:
        modules = _num(raw, "modules", 1, 500)
        if modules != int(modules):
            raise ValueError("modules: ganze Zahl erwartet")
        module_wp = _num(raw, "module_wp", 50, 1000)
    points: list[list[float]] = []
    edge = 0
    area = None
    if kind == "manual":
        azimuth = _num(raw, "azimuth", 0, 360, 180) % 360
    else:
        points = _points(raw.get("points"))
        need = 3 if kind == "area" else 2
        if len(points) < need or (kind == "line" and len(points) != 2):
            raise ValueError("points: Fläche braucht mindestens 3, Linie genau 2 Punkte")
        if len({tuple(p) for p in points}) != len(points):
            raise ValueError("points: doppelte Punkte")
        xy = _local_xy(points)
        if kind == "area" and len(points) > 3 and hypot(*xy[-1]) < CLOSE_TOLERANCE_M:
            # Clicked the start point again to close the polygon: not a corner.
            points, xy = points[:-1], xy[:-1]
        if max(hypot(x, y) for x, y in xy[1:]) > 2000:
            raise ValueError("points: Fläche größer als 2 km")
        if kind == "area":
            area = projected_area_m2(points)
            if area < 0.5:
                raise ValueError("points: Fläche zu klein")
            edge = raw.get("edge")
            edge = int(edge) if isinstance(edge, (int, float)) and not isinstance(edge, bool) else -1
            if not 0 <= edge < len(points):
                edge = default_edge(points)
            azimuth = area_outward_azimuth(points, edge, flip)
        else:
            if hypot(*xy[1]) < 0.3:
                raise ValueError("points: Linie zu kurz")
            azimuth = line_azimuth(points, flip)
    return {
        "id": sid, "name": name, "kind": kind, "points": points, "edge": edge, "flip": flip,
        "tilt": round(tilt, 1), "azimuth": round(azimuth, 1), "input": mode,
        "kwp": round(kwp, 3), "modules": int(modules), "module_wp": round(module_wp, 1),
        "area_m2": area, "bifacial": bifacial, "bifaciality": round(bifaciality, 2),
    }


def normalize_surfaces(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError("surfaces: Liste erwartet")
    if len(raw) > MAX_SURFACES:
        raise ValueError(f"Höchstens {MAX_SURFACES} PV-Flächen")
    result = []
    for index, item in enumerate(raw, start=1):
        try:
            result.append(normalize_surface(item))
        except ValueError as err:
            raise ValueError(f"Fläche {index}: {err}") from None
    if len({s["id"] for s in result}) != len(result):
        raise ValueError("Doppelte Flächen-ID")
    return result


# ── Map tiles (Web Mercator) ─────────────────────────────────────────────────
def tile_xy(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Fractional tile coordinates of a WGS84 point."""
    n = 2 ** zoom
    x = (lon + 180) / 360 * n
    lat_r = radians(lat)
    y = (1 - log(tan(lat_r) + 1 / cos(lat_r)) / pi) / 2 * n
    return x, y


def tile_grid(lat: float, lon: float, zoom: int, size: int = MAP_GRID) -> list[tuple[int, int]]:
    """size × size tiles with the centre point in the middle tile."""
    cx, cy = tile_xy(lat, lon, zoom)
    half = size // 2
    return [(int(cx) + dx, int(cy) + dy)
            for dy in range(-half, size - half) for dx in range(-half, size - half)]
