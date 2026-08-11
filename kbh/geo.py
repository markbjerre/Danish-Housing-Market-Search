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

# Overpass mirrors, tried in order. Every one of them fails often enough that
# a single URL is not usable.
#
# Two traps are baked into this list. ``overpass.private.coffee`` no longer
# resolves at all and has been removed. ``overpass.osm.ch`` is worse than down:
# it answers 200 with an empty ``elements`` array instead of an error, so a
# caller that only checks the status code caches an empty file and concludes
# Copenhagen has no railway stations. Every fetch here therefore treats an
# empty result as a failure and moves to the next mirror.
OVERPASS_URLS: Tuple[str, ...] = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
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


def bbox_string() -> str:
    south, west, north, east = OSM_BBOX
    return f"{south},{west},{north},{east}"


def _overpass(query: str, label: str, attempts: int = 2) -> List[dict]:
    """Run an Overpass query against the mirrors until one answers usefully.

    An empty ``elements`` array counts as a failure, not as an answer. See the
    note on OVERPASS_URLS. The whole rotation is retried ``attempts`` times,
    because a 504 from every mirror is usually a busy minute rather than a
    permanent condition.
    """
    errors: List[str] = []
    for attempt in range(1, attempts + 1):
        for url in OVERPASS_URLS:
            logger.info(
                "Fetching %s geometry from %s (attempt %s)", label, url, attempt
            )
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
                    return elements
                errors.append(f"{url}: 200 but no elements")
            except Exception as exc:
                errors.append(f"{url}: {exc}")
                continue
    raise RuntimeError(
        f"every Overpass mirror failed for {label}: " + "; ".join(errors[-6:])
    )


def _way_coords(element: dict) -> List[List[float]]:
    """Longitude and latitude pairs for a way or a relation."""
    coords: List[List[float]] = []
    if element.get("type") == "way" and element.get("geometry"):
        coords = [[p["lon"], p["lat"]] for p in element["geometry"]]
    elif element.get("type") == "relation":
        for member in element.get("members", []):
            if member.get("geometry"):
                coords.extend([p["lon"], p["lat"]] for p in member["geometry"])
    return coords


def fetch_water(force: bool = False) -> Path:
    """Download and cache Copenhagen water geometry from OpenStreetMap.

    Returns the path to the cached GeoJSON. Raises if the download fails and
    no cache exists, rather than quietly returning nothing.
    """
    if config.WATER_GEOJSON.exists() and not force:
        return config.WATER_GEOJSON

    query = OVERPASS_QUERY.format(bbox=bbox_string())
    elements = _overpass(query, "water")

    features: List[dict] = []
    for element in elements:
        tags = element.get("tags") or {}

        coords = _way_coords(element)
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
# Transit
#
# Metro and S-tog platforms. Both are nodes rather than ways, so this is a
# nearest point lookup rather than a nearest geometry one.
#
# The classification is not obvious. OSM Denmark tags the Copenhagen Metro as
# ``station=subway``, which is what you would expect, but it tags the S-tog as
# ``station=light_rail``, which is not: an S-tog is a heavy suburban rail
# system and nothing like a tram. Anything left over (Hovedbanegården,
# Nørreport, Østerport and the regional stops) carries no ``station`` tag at
# all. All three are real rail service and all three count.
# --------------------------------------------------------------------------

TRANSIT_QUERY = """
[out:json][timeout:180];
(
  node["railway"="station"]({bbox});
  node["railway"="halt"]({bbox});
);
out;
"""

TRANSIT_KINDS: Dict[str, str] = {
    "subway": "metro",
    "light_rail": "s-tog",
    "train": "regionaltog",
}


def _transit_kind(tags: Dict[str, str]) -> str:
    station = tags.get("station", "")
    if station in TRANSIT_KINDS:
        return TRANSIT_KINDS[station]
    network = (tags.get("network") or "").lower()
    if "s-tog" in network:
        return "s-tog"
    if "metro" in network:
        return "metro"
    return "regionaltog"


def fetch_transit(force: bool = False) -> Path:
    """Download and cache metro, S-tog and regional station positions."""
    if config.TRANSIT_GEOJSON.exists() and not force:
        return config.TRANSIT_GEOJSON

    elements = _overpass(TRANSIT_QUERY.format(bbox=bbox_string()), "transit")

    features: List[dict] = []
    for element in elements:
        lat, lon = element.get("lat"), element.get("lon")
        if lat is None or lon is None:
            continue
        tags = element.get("tags") or {}
        # Disused and construction platforms are still tagged as stations, and
        # a flat is not well served by a station that has not opened or has
        # closed.
        if tags.get("disused") or tags.get("construction") or tags.get("abandoned"):
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "kind": _transit_kind(tags),
                    "name": tags.get("name", ""),
                    "osm_id": element.get("id"),
                },
            }
        )

    if not features:
        raise RuntimeError("Overpass returned no usable station geometry")

    payload = {"type": "FeatureCollection", "features": features}
    config.TRANSIT_GEOJSON.write_text(json.dumps(payload), encoding="utf-8")
    counts: Dict[str, int] = {}
    for feature in features:
        kind = feature["properties"]["kind"]
        counts[kind] = counts.get(kind, 0) + 1
    logger.info(
        "Cached %s stations to %s: %s", len(features), config.TRANSIT_GEOJSON, counts
    )
    return config.TRANSIT_GEOJSON


@dataclass
class TransitHit:
    distance_m: float
    name: str
    kind: str


class TransitIndex:
    """Nearest rail station of any kind."""

    def __init__(self, geojson_path: Path) -> None:
        raw = json.loads(Path(geojson_path).read_text(encoding="utf-8"))
        self._geoms: List = []
        self._meta: List[Tuple[str, str]] = []

        for feature in raw.get("features", []):
            try:
                geometry = transform(_to_metres, shape(feature["geometry"]))
            except Exception:
                continue
            if geometry.is_empty:
                continue
            self._geoms.append(geometry)
            props = feature.get("properties", {})
            self._meta.append((props.get("name") or "", props.get("kind") or "station"))

        self._tree = STRtree(self._geoms) if self._geoms else None

    @property
    def ready(self) -> bool:
        return bool(self._geoms)

    def nearest(self, lat: float, lon: float) -> Optional[TransitHit]:
        if self._tree is None:
            return None
        point = Point(*_to_metres(lon, lat))
        index = self._tree.nearest(point)
        if index is None:
            return None
        name, kind = self._meta[int(index)]
        distance = float(point.distance(self._geoms[int(index)]))
        return TransitHit(distance, name or "station", kind)


# --------------------------------------------------------------------------
# Noise
#
# Road and rail lines that a home can be too close to. Only the classes that
# actually carry through traffic are pulled: residential and unclassified
# streets are the normal condition of living in a city and would add nothing
# but a constant to every listing.
#
# ``railway=rail`` is included because the S-tog and regional lines are a
# genuine noise source above ground, and because the same line that makes a
# station convenient makes the flat backing onto it unpleasant. Tunnels and
# subways are excluded: the Metro is almost entirely underground in the
# expensive parts of the city and makes no noise there at all.
# --------------------------------------------------------------------------

NOISE_QUERY = """
[out:json][timeout:240];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]({bbox});
  way["railway"="rail"]({bbox});
);
out geom;
"""


def _parse_lanes(raw: Optional[str]) -> Optional[float]:
    """OSM lane counts are free text often enough to need guarding."""
    if not raw:
        return None
    try:
        return float(str(raw).split(";")[0].strip())
    except (TypeError, ValueError):
        return None


def _parse_maxspeed(raw: Optional[str]) -> Optional[float]:
    """Speed limits arrive as '50', '50 km/h', 'DK:urban' and worse."""
    if not raw:
        return None
    text = str(raw).strip().lower()
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        try:
            return float(digits[:3])
        except ValueError:
            return None
    # The implicit Danish defaults, for ways that state a zone instead.
    return {"dk:urban": 50.0, "dk:rural": 80.0, "dk:motorway": 130.0}.get(text)


def _noise_class(tags: Dict[str, str]) -> Optional[str]:
    """Which noise source class a way belongs to, or None to ignore it."""
    # Anything in a tunnel or a covered cutting is not heard at street level.
    if tags.get("tunnel") or tags.get("covered") == "yes":
        return None
    if tags.get("railway") == "rail":
        if tags.get("service") in ("siding", "yard", "spur", "crossover"):
            return None
        if tags.get("usage") == "industrial":
            return None
        return "railway"
    highway = tags.get("highway", "")
    if highway in config.NOISE_HIGHWAY_CLASSES:
        return highway
    return None


def fetch_noise(force: bool = False) -> Path:
    """Download and cache the road and rail lines that generate noise.

    The emission weight is computed here and stored on each feature, so the
    lookup at scoring time is geometry only.
    """
    if config.NOISE_GEOJSON.exists() and not force:
        return config.NOISE_GEOJSON

    elements = _overpass(NOISE_QUERY.format(bbox=bbox_string()), "noise")

    features: List[dict] = []
    for element in elements:
        tags = element.get("tags") or {}
        kind = _noise_class(tags)
        if kind is None:
            continue
        coords = _way_coords(element)
        if len(coords) < 2:
            continue
        weight = config.noise_weight(
            kind,
            lanes=_parse_lanes(tags.get("lanes")),
            maxspeed=_parse_maxspeed(tags.get("maxspeed")),
        )
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "kind": kind,
                    "name": tags.get("name", ""),
                    "weight": round(weight, 1),
                    "osm_id": element.get("id"),
                },
            }
        )

    if not features:
        raise RuntimeError("Overpass returned no usable noise geometry")

    payload = {"type": "FeatureCollection", "features": features}
    config.NOISE_GEOJSON.write_text(json.dumps(payload), encoding="utf-8")
    counts: Dict[str, int] = {}
    for feature in features:
        kind = feature["properties"]["kind"]
        counts[kind] = counts.get(kind, 0) + 1
    logger.info(
        "Cached %s noise sources to %s: %s", len(features), config.NOISE_GEOJSON, counts
    )
    return config.NOISE_GEOJSON


@dataclass
class NoiseHit:
    """One noise source affecting an address."""

    kind: str
    distance_m: float
    name: str
    weight: float

    @property
    def reach_m(self) -> float:
        return config.noise_reach_m(self.weight)

    @property
    def penalty(self) -> float:
        """Points off, decaying linearly to nothing at the source's reach."""
        reach = self.reach_m
        if self.distance_m >= reach:
            return 0.0
        return self.weight * (1.0 - self.distance_m / reach)


class NoiseIndex:
    """Road and rail noise sources near an address.

    One tree over everything, because the loudness now lives on the feature
    rather than in its class. The lookup takes every source whose reach covers
    the point, so a flat between a motorway and a railway is charged for both.

    Results are grouped by street before they are returned. That matters more
    than it looks: OSM splits Åboulevard into 24 separate ways, and charging a
    flat once per way would put a quiet address next to a busy road at zero.
    One street contributes once, at its nearest point.
    """

    def __init__(self, geojson_path: Path) -> None:
        raw = json.loads(Path(geojson_path).read_text(encoding="utf-8"))
        self._geoms: List = []
        self._meta: List[Tuple[str, str, float]] = []

        for feature in raw.get("features", []):
            props = feature.get("properties", {})
            kind = props.get("kind")
            if kind not in config.NOISE_LABELS:
                continue
            try:
                geometry = transform(_to_metres, shape(feature["geometry"]))
            except Exception:
                continue
            if geometry.is_empty:
                continue
            weight = props.get("weight")
            if weight is None:
                weight = config.noise_weight(kind)
            self._geoms.append(geometry)
            self._meta.append((kind, props.get("name") or "", float(weight)))

        self._tree = STRtree(self._geoms) if self._geoms else None
        # The furthest any source can be heard, which bounds the query window.
        self._max_reach = max(
            (config.noise_reach_m(m[2]) for m in self._meta), default=0.0
        )

    @property
    def ready(self) -> bool:
        return bool(self._geoms)

    def nearby(self, lat: float, lon: float) -> List[NoiseHit]:
        """Every street and line whose noise reaches this address.

        Sorted loudest first, so the reasoning string names what actually
        dominates rather than whatever happens to be nearest.
        """
        if self._tree is None:
            return []
        point = Point(*_to_metres(lon, lat))
        candidates = self._tree.query(point.buffer(self._max_reach))

        # Nearest way per street, so a road split into many OSM ways counts once.
        best: Dict[Tuple[str, str], NoiseHit] = {}
        for index in candidates:
            kind, name, weight = self._meta[int(index)]
            distance = float(point.distance(self._geoms[int(index)]))
            if distance >= config.noise_reach_m(weight):
                continue
            # Unnamed segments group by class alone, which is the best that can
            # be done without a street name to join on.
            key = (kind, name)
            current = best.get(key)
            if current is None or distance < current.distance_m:
                best[key] = NoiseHit(kind, distance, name, weight)

        return sorted(best.values(), key=lambda h: h.penalty, reverse=True)


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
