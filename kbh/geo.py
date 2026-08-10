"""Geography: water proximity, parish lookup, neighbourhood resolution.

Two external geometry sources, both cached to disk on first use:

* Water comes from OpenStreetMap via Overpass. Copenhagen harbour is tidal
  seawater, so ``natural=coastline`` traces Øresund and the whole harbour
  including Nordhavn, Islands Brygge, Christianshavn and Sluseholmen in one
  go. Canals and the three lakes on Søerne are pulled separately.
* Parish polygons come from Boligsiden's own heatmap endpoint, which carries
  the realised m2 price as a property. One fetch gives both the geometry and
  the benchmark.

Distances are computed in a local equirectangular projection centred on
Copenhagen. Over a 25 km span the error against a proper projected CRS is
under a metre, which is far below the precision the scoring curve cares about.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import requests
from shapely.geometry import Point, shape
from shapely.ops import transform
from shapely.strtree import STRtree

from . import config

logger = logging.getLogger(__name__)

# Local projection origin. Roughly Rådhuspladsen.
_LAT0 = 55.6761
_LON0 = 12.5683
_M_PER_DEG_LAT = 110_574.0
_M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(_LAT0))

# Bounding box for the OSM pull: south, west, north, east.
OSM_BBOX: Tuple[float, float, float, float] = (55.58, 12.44, 55.78, 12.70)

# The main Overpass instance times out on this query often enough to be
# unreliable. Mirrors are tried in order.
OVERPASS_URLS: Tuple[str, ...] = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)

PRIME_LAKE_NAMES = {
    "Sankt Jørgens Sø",
    "Skt. Jørgens Sø",
    "Sct. Jørgens Sø",
    "Peblinge Sø",
    "Sortedams Sø",
    "Sortedamssøen",
}

# Ørestad is drained by a grid of engineered canals. OSM tags them as canals,
# which would otherwise put them on the same footing as Christianshavns Kanal
# and the harbour itself. They are not the same product: a flat on
# Hovedkanalen faces a narrow concrete channel between two office blocks, not
# the water Mark asked to be near. Anything inside this box is demoted to
# secondary water.
#
# The northern edge deliberately stops short of Islands Brygge, which is
# genuine harbour front and must keep its prime classification.
ORESTAD_BOX: Tuple[float, float, float, float] = (55.600, 12.560, 55.657, 12.610)


def _in_box(lat: float, lon: float, box: Tuple[float, float, float, float]) -> bool:
    south, west, north, east = box
    return south <= lat <= north and west <= lon <= east


def _to_metres(lon: float, lat: float) -> Tuple[float, float]:
    return ((lon - _LON0) * _M_PER_DEG_LON, (lat - _LAT0) * _M_PER_DEG_LAT)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great circle distance in metres."""
    radius = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------
# Water
# --------------------------------------------------------------------------

OVERPASS_QUERY = """
[out:json][timeout:180];
(
  way["natural"="coastline"]({bbox});
  way["waterway"="canal"]({bbox});
  relation["waterway"="canal"]({bbox});
  way["natural"="water"]({bbox});
  relation["natural"="water"]({bbox});
);
out geom;
"""


def _classify(
    tags: Dict[str, str], coords: Optional[List[List[float]]] = None
) -> Optional[str]:
    """Return 'prime', 'secondary' or None for water we do not care about."""
    name = tags.get("name", "")
    kind: Optional[str] = None

    if tags.get("natural") == "coastline":
        kind = "prime"
    elif tags.get("waterway") == "canal":
        kind = "prime"
    elif tags.get("natural") == "water":
        water = tags.get("water", "")
        lowered = name.lower()
        if water in ("harbour", "canal", "lagoon", "moat"):
            kind = "prime"
        elif name in PRIME_LAKE_NAMES:
            kind = "prime"
        elif "havn" in lowered or "kanal" in lowered or "løbet" in lowered:
            kind = "prime"
        else:
            kind = "secondary"

    if kind == "prime" and coords and _mostly_inside(coords, ORESTAD_BOX):
        return "secondary"
    return kind


def _mostly_inside(
    coords: List[List[float]],
    box: Tuple[float, float, float, float],
    threshold: float = 0.8,
) -> bool:
    """True when at least ``threshold`` of a geometry's vertices fall in the box."""
    if not coords:
        return False
    inside = sum(1 for lon, lat in coords if _in_box(lat, lon, box))
    return inside / len(coords) >= threshold


def fetch_water(force: bool = False) -> Path:
    """Download and cache Copenhagen water geometry from OpenStreetMap.

    Returns the path to the cached GeoJSON. Raises if the download fails and
    no cache exists, rather than quietly returning nothing.
    """
    if config.WATER_GEOJSON.exists() and not force:
        return config.WATER_GEOJSON

    south, west, north, east = OSM_BBOX
    query = OVERPASS_QUERY.format(bbox=f"{south},{west},{north},{east}")

    elements: List[dict] = []
    errors: List[str] = []
    for url in OVERPASS_URLS:
        logger.info("Fetching Copenhagen water geometry from %s", url)
        try:
            response = requests.post(
                url,
                data={"data": query},
                headers={"User-Agent": "kbh-apartment-monitor/1.0"},
                timeout=300,
            )
            response.raise_for_status()
            elements = response.json().get("elements", [])
            if elements:
                break
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            continue

    if not elements:
        raise RuntimeError("every Overpass mirror failed: " + "; ".join(errors))

    features: List[dict] = []
    for element in elements:
        tags = element.get("tags") or {}

        coords: List[List[float]] = []
        if element.get("type") == "way" and element.get("geometry"):
            coords = [[p["lon"], p["lat"]] for p in element["geometry"]]
        elif element.get("type") == "relation":
            for member in element.get("members", []):
                if member.get("geometry"):
                    coords.extend([p["lon"], p["lat"]] for p in member["geometry"])
        if len(coords) < 2:
            continue

        kind = _classify(tags, coords)
        if kind is None:
            continue

        closed = coords[0] == coords[-1] and len(coords) >= 4
        geometry = (
            {"type": "Polygon", "coordinates": [coords]}
            if closed
            else {"type": "LineString", "coordinates": coords}
        )
        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "kind": kind,
                    "name": tags.get("name", ""),
                    "osm_id": element.get("id"),
                },
            }
        )

    if not features:
        raise RuntimeError("Overpass returned no usable water geometry")

    payload = {"type": "FeatureCollection", "features": features}
    config.WATER_GEOJSON.write_text(json.dumps(payload), encoding="utf-8")
    prime = sum(1 for f in features if f["properties"]["kind"] == "prime")
    logger.info(
        "Cached %s water features (%s prime) to %s",
        len(features),
        prime,
        config.WATER_GEOJSON,
    )
    return config.WATER_GEOJSON


@dataclass
class WaterHit:
    distance_m: float
    name: str
    kind: str


class WaterIndex:
    """Nearest water lookup. Prime and secondary water are indexed separately
    so a pond cannot masquerade as the harbour."""

    def __init__(self, geojson_path: Path) -> None:
        raw = json.loads(Path(geojson_path).read_text(encoding="utf-8"))
        self._geoms: Dict[str, List] = {"prime": [], "secondary": []}
        self._names: Dict[str, List[str]] = {"prime": [], "secondary": []}

        for feature in raw.get("features", []):
            kind = feature["properties"].get("kind", "secondary")
            if kind not in self._geoms:
                continue
            try:
                geometry = transform(_to_metres, shape(feature["geometry"]))
            except Exception:
                continue
            if geometry.is_empty:
                continue
            self._geoms[kind].append(geometry)
            self._names[kind].append(feature["properties"].get("name") or "")

        self._trees = {
            kind: (STRtree(geoms) if geoms else None)
            for kind, geoms in self._geoms.items()
        }

    @property
    def ready(self) -> bool:
        return bool(self._geoms["prime"])

    def nearest(self, lat: float, lon: float) -> Optional[WaterHit]:
        """Closest water of either class, preferring prime when it is within
        reach of the scoring curve at all."""
        point = Point(*_to_metres(lon, lat))
        best: Optional[WaterHit] = None

        for kind in ("prime", "secondary"):
            tree = self._trees.get(kind)
            if tree is None:
                continue
            index = tree.nearest(point)
            if index is None:
                continue
            geometry = self._geoms[kind][int(index)]
            distance = float(point.distance(geometry))
            # Most OSM coastline ways carry no name, and "3 m til " reads as a
            # bug rather than as waterfront.
            name = self._names[kind][int(index)] or (
                "havnen eller kysten" if kind == "prime" else "vandet"
            )
            hit = WaterHit(distance, name, kind)
            if kind == "prime" and distance <= config.WATER_ZERO_SCORE_M:
                return hit
            if best is None or distance < best.distance_m:
                best = hit
        return best


# --------------------------------------------------------------------------
# Parishes
# --------------------------------------------------------------------------


@dataclass
class ParishHit:
    code: Optional[int]
    name: str
    sqm_price: Optional[int]
    basis: str  # 'recent', 'yearly' or 'none'


class ParishIndex:
    """Point in polygon lookup over Boligsiden's parish heatmap, carrying the
    realised m2 price for each parish."""

    def __init__(self, feature_collections: Sequence[dict]) -> None:
        self._geoms: List = []
        self._meta: List[ParishHit] = []

        for collection in feature_collections:
            for feature in collection.get("features", []):
                props = feature.get("properties", {})
                try:
                    geometry = shape(feature["geometry"])
                except Exception:
                    continue
                if geometry.is_empty:
                    continue
                recent = props.get("sold_per_area_price")
                yearly = props.get("sold_per_area_price_yearly")
                price = recent or yearly
                basis = "recent" if recent else ("yearly" if yearly else "none")
                self._geoms.append(geometry)
                self._meta.append(
                    ParishHit(
                        code=props.get("code"),
                        name=props.get("name") or "",
                        sqm_price=int(price) if price else None,
                        basis=basis,
                    )
                )

        self._tree = STRtree(self._geoms) if self._geoms else None

    def __len__(self) -> int:
        return len(self._geoms)

    @property
    def ready(self) -> bool:
        return self._tree is not None

    def lookup(self, lat: float, lon: float) -> Optional[ParishHit]:
        if self._tree is None:
            return None
        point = Point(lon, lat)
        for index in self._tree.query(point):
            if self._geoms[int(index)].contains(point):
                return self._meta[int(index)]
        # Just outside every polygon, which happens on reclaimed land in
        # Nordhavn. Fall back to the nearest parish.
        index = self._tree.nearest(point)
        return self._meta[int(index)] if index is not None else None


# --------------------------------------------------------------------------
# Neighbourhood resolution
# --------------------------------------------------------------------------


@dataclass
class NeighbourhoodHit:
    name: str
    tier: int
    source: str  # 'named_area' or 'zip'


def resolve_neighbourhood(
    zip_code: Optional[int], lat: Optional[float], lon: Optional[float]
) -> NeighbourhoodHit:
    """Named sub-areas win over postal codes when the flat sits inside one.

    This is what makes Amager Strandpark rank like a priority neighbourhood
    while the rest of postal code 2300 does not.
    """
    best: Optional[NeighbourhoodHit] = None

    if lat is not None and lon is not None:
        for area in config.NAMED_AREAS:
            if area.bbox is not None:
                matched = _in_box(lat, lon, area.bbox)
            elif area.radius_m is not None:
                matched = haversine_m(lat, lon, area.lat, area.lon) <= area.radius_m
            else:
                matched = False
            if not matched:
                continue
            # An overriding area settles it outright, in either direction.
            if area.override:
                return NeighbourhoodHit(area.name, area.tier, "named_area")
            candidate = NeighbourhoodHit(area.name, area.tier, "named_area")
            if best is None or candidate.tier > best.tier:
                best = candidate

    zip_group = _zip_group(zip_code)
    hood = config.NEIGHBOURHOODS.get(zip_group, config.DEFAULT_NEIGHBOURHOOD)
    zip_hit = NeighbourhoodHit(hood.name, hood.tier, "zip")

    if best is not None and best.tier >= zip_hit.tier:
        return best
    return zip_hit


def _zip_group(zip_code: Optional[int]) -> int:
    """Collapse a postal code into the group Boligsiden itself uses."""
    if zip_code is None:
        return -1
    if zip_code < 1500:
        return 1000
    if zip_code < 1800:
        return 1500
    if zip_code < 2000:
        return 1800
    if zip_code in (2100, 2150, 2200, 2300, 2400, 2450, 2500, 2700, 2720, 2000):
        return zip_code
    return zip_code
