"""Local m2 price benchmarks.

Three levels, used in order of preference:

1. Parish (sogn). Copenhagen splits into 56 of them and the spread is large:
   Hans Egedes in Nordhavn sits near 90.700 kr/m2 while Husumvold sits near
   35.600. Postal code 2200 alone contains parishes 14 pct. apart. This is the
   level that makes "cheap for the area" mean something.
2. Postal code. Used where the parish returns no realised sales.
3. Municipality average by room count. The last resort.

Boligsiden reports either ``sold_per_area_price`` from recent sales or
``sold_per_area_price_yearly`` over a wider window where recent volume is
thin. Which one was used is carried through to the score reasoning, because a
benchmark built on a twelve month window deserves less confidence.
"""

from __future__ import annotations

import logging
import sqlite3
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import config, db, geo
from .boligsiden import BoligsidenClient

logger = logging.getLogger(__name__)


@dataclass
class Benchmark:
    sqm_price: Optional[int]
    basis: str  # 'recent', 'yearly', 'zip', 'municipality', 'peers' or 'none'
    source_name: str


# Peer benchmark.
#
# Parishes are administrative units, not economic ones, and some of them
# straddle two completely different markets. Copenhagen's worst case is the
# Islands Brygges parish: it covers both Islands Brygge at roughly 73.000
# kr/m2 and the whole of Ørestad at roughly 53.000. Benchmarking an Ørestad
# flat against that parish makes every Ørestad flat look 25 to 45 pct.
# underpriced, which is exactly what the first version of this scorer did. Its
# top twelve came back nine tenths Ørestad.
#
# So a flat is also benchmarked against its immediate competition: the median
# asking price per m2 of nearby listings of the same type. Asking prices sit
# above realised prices, hence the haircut. The two benchmarks are combined
# with min(), because "cheap" should mean cheap against both the wider area
# and the flats you would actually be bidding against.
PEER_RADIUS_M: int = 1200
PEER_MIN_COUNT: int = 8
PEER_ASKING_HAIRCUT: float = 0.97


class PeerBenchmark:
    """Median asking kr/m2 among nearby comparable listings."""

    def __init__(self, rows: Sequence[Dict[str, Any]]) -> None:
        self._points: Dict[str, List[Tuple[float, float, float]]] = {}
        for row in rows:
            lat, lon = row.get("lat"), row.get("lon")
            area, price = row.get("living_area"), row.get("price")
            if not (lat and lon and area and price) or area <= 0:
                continue
            key = config.BENCHMARK_ADDRESS_TYPE.get(
                row.get("address_type") or "condo", "condo"
            )
            self._points.setdefault(key, []).append((lat, lon, price / area))

    def lookup(self, listing: Dict[str, Any]) -> Optional[int]:
        lat, lon = listing.get("lat"), listing.get("lon")
        if not lat or not lon:
            return None
        key = config.BENCHMARK_ADDRESS_TYPE.get(
            listing.get("address_type") or "condo", "condo"
        )
        area = listing.get("living_area") or 0
        price = listing.get("price") or 0
        own_sqm = (price / area) if area else None

        nearby = [
            sqm
            for plat, plon, sqm in self._points.get(key, [])
            if geo.haversine_m(lat, lon, plat, plon) <= PEER_RADIUS_M
        ]
        # Remove one instance of the listing's own price so nothing is ever
        # compared against itself.
        if own_sqm is not None and own_sqm in nearby:
            nearby.remove(own_sqm)

        if len(nearby) < PEER_MIN_COUNT:
            return None
        return int(statistics.median(nearby) * PEER_ASKING_HAIRCUT)


class BenchmarkSet:
    """Everything needed to price a flat against its own patch of the city."""

    def __init__(
        self,
        parish_indexes: Dict[str, geo.ParishIndex],
        zip_prices: Dict[str, Dict[str, int]],
        municipality_avg: Dict[str, Dict[str, int]],
    ) -> None:
        # Keyed by address type. Benchmarking a condo against villa sales in
        # the same parish would be worse than having no benchmark at all.
        self.parish_indexes = parish_indexes
        self.zip_prices = zip_prices
        self.municipality_avg = municipality_avg
        self.peers: Optional[PeerBenchmark] = None

    def attach_peers(self, rows: Sequence[Dict[str, Any]]) -> None:
        """Build the peer benchmark from the current candidate pool. Must be
        called before scoring; without it the parish benchmark stands alone."""
        self.peers = PeerBenchmark(rows)

    def lookup(self, listing: Dict[str, Any]) -> Benchmark:
        area = self._area_benchmark(listing)
        peer = self.peers.lookup(listing) if self.peers is not None else None

        if area.sqm_price and peer:
            if peer < area.sqm_price:
                return Benchmark(
                    peer,
                    "peers",
                    f"nabolaget inden for {PEER_RADIUS_M} m "
                    f"(strammere end {area.source_name})",
                )
            return area
        if area.sqm_price:
            return area
        if peer:
            return Benchmark(peer, "peers", f"nabolaget inden for {PEER_RADIUS_M} m")
        return area

    def _area_benchmark(self, listing: Dict[str, Any]) -> Benchmark:
        address_type = config.BENCHMARK_ADDRESS_TYPE.get(
            listing.get("address_type") or "condo", "condo"
        )
        lat, lon = listing.get("lat"), listing.get("lon")

        index = self.parish_indexes.get(address_type)
        if index is not None and lat and lon:
            hit = index.lookup(lat, lon)
            if hit and hit.sqm_price:
                return Benchmark(hit.sqm_price, hit.basis, f"sognet {hit.name}")

        zip_code = listing.get("zip_code")
        if zip_code:
            price = self.zip_prices.get(address_type, {}).get(str(zip_code))
            if price:
                return Benchmark(price, "zip", f"postnummer {zip_code}")

        rooms = listing.get("number_of_rooms")
        key = _room_bucket(rooms)
        price = self.municipality_avg.get(address_type, {}).get(key)
        if price:
            return Benchmark(price, "municipality", f"kommunen, {key} vær.")

        return Benchmark(None, "none", "intet benchmark")

    def parish_name(self, listing: Dict[str, Any]) -> Optional[str]:
        address_type = config.BENCHMARK_ADDRESS_TYPE.get(
            listing.get("address_type") or "condo", "condo"
        )
        index = self.parish_indexes.get(address_type)
        lat, lon = listing.get("lat"), listing.get("lon")
        if index is None or not lat or not lon:
            return None
        hit = index.lookup(lat, lon)
        return hit.name if hit else None


def _room_bucket(rooms: Optional[float]) -> str:
    if not rooms:
        return "3"
    count = int(rooms)
    return "4+" if count >= 4 else str(max(count, 1))


def refresh(client: BoligsidenClient, conn: sqlite3.Connection) -> BenchmarkSet:
    """Pull every benchmark level from the API and persist it.

    Called once per pipeline run. Cheap: eight requests total.
    """
    address_types = sorted(set(config.BENCHMARK_ADDRESS_TYPE.values()))

    parish_collections: Dict[str, List[dict]] = {a: [] for a in address_types}
    zip_prices: Dict[str, Dict[str, int]] = {}
    municipality_avg: Dict[str, Dict[str, int]] = {}

    for address_type in address_types:
        zip_rows: Dict[str, Dict[str, Any]] = {}
        for code in config.BENCHMARK_MUNICIPALITIES:
            collection = client.parish_heatmap(code, address_type)
            if collection.get("features"):
                parish_collections[address_type].append(collection)
                _persist_parishes(conn, address_type, collection)

            for feature in client.zip_heatmap(code, address_type).get("features", []):
                props = feature.get("properties", {})
                zip_code = props.get("zip_code")
                recent = props.get("sold_per_area_price")
                yearly = props.get("sold_per_area_price_yearly")
                price = recent or yearly
                if zip_code and price:
                    zip_rows[str(zip_code)] = {
                        "sqm_price": int(price),
                        "basis": "recent" if recent else "yearly",
                    }

            for row in client.municipality_average(code, address_type):
                rooms = str(row.get("numberRooms") or "")
                price = row.get("avgPriceM2")
                if rooms and price:
                    bucket = municipality_avg.setdefault(address_type, {})
                    # Averaging across the two municipalities would blur the
                    # difference, so the first (Copenhagen) wins.
                    bucket.setdefault(rooms, int(price))

        zip_prices[address_type] = {k: v["sqm_price"] for k, v in zip_rows.items()}
        db.save_benchmarks(conn, "zip", address_type, zip_rows)
        db.save_benchmarks(
            conn,
            "municipality",
            address_type,
            {
                k: {"sqm_price": v, "basis": "municipality"}
                for k, v in municipality_avg.get(address_type, {}).items()
            },
        )

    conn.commit()

    parish_indexes = {
        address_type: geo.ParishIndex(collections)
        for address_type, collections in parish_collections.items()
        if collections
    }
    logger.info(
        "Benchmarks loaded: %s, %s postal codes",
        ", ".join(f"{len(idx)} {name} sogne" for name, idx in parish_indexes.items()),
        sum(len(v) for v in zip_prices.values()),
    )
    return BenchmarkSet(parish_indexes, zip_prices, municipality_avg)


def _persist_parishes(
    conn: sqlite3.Connection, address_type: str, collection: dict
) -> None:
    rows: Dict[str, Dict[str, Any]] = {}
    for feature in collection.get("features", []):
        props = feature.get("properties", {})
        code = props.get("code")
        if code is None:
            continue
        recent = props.get("sold_per_area_price")
        yearly = props.get("sold_per_area_price_yearly")
        price = recent or yearly
        rows[str(code)] = {
            "sqm_price": int(price) if price else None,
            "basis": "recent" if recent else ("yearly" if yearly else "none"),
        }
    if rows:
        db.save_benchmarks(conn, "parish", address_type, rows)


def load_cached(conn: sqlite3.Connection, client: BoligsidenClient) -> BenchmarkSet:
    """Rebuild a BenchmarkSet without refetching everything.

    Parish geometry is not stored locally, so this still pulls the heatmaps.
    It exists so the web app can score on demand without a full pipeline run.
    """
    parish_indexes = {
        address_type: geo.ParishIndex(
            [
                client.parish_heatmap(code, address_type)
                for code in config.BENCHMARK_MUNICIPALITIES
            ]
        )
        for address_type in sorted(set(config.BENCHMARK_ADDRESS_TYPE.values()))
    }
    zip_prices = {
        address_type: db.benchmark_map(conn, "zip", address_type)
        for address_type in sorted(set(config.BENCHMARK_ADDRESS_TYPE.values()))
    }
    municipality_avg = {
        address_type: db.benchmark_map(conn, "municipality", address_type)
        for address_type in sorted(set(config.BENCHMARK_ADDRESS_TYPE.values()))
    }
    return BenchmarkSet(parish_indexes, zip_prices, municipality_avg)
