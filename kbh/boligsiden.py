"""Boligsiden API client.

Covers the endpoints the villa pipeline never used. Verified live against
api.boligsiden.dk on 10 August 2026:

    GET /search/cases                                   59 filter params
    GET /cases/{caseID}                                 full listing payload
    GET /cases/{caseID}/timeline                        listing price events
    GET /addresses/{addressID}/timeline                 sale history since 1990s
    GET /cases/bulk/stats?caseID=..&caseID=..           views, clicks, favourites
    GET /case/stats/municipality-average                avg price and m2 by rooms
    GET /municipalities/{code}/parish_divisions/heatmap parish m2 benchmarks
    GET /municipalities/{code}/zip_codes/heatmap        postal code m2 benchmarks

Quirks worth knowing, all confirmed by testing rather than documentation:

* ``municipalities`` takes exactly one name. A comma separated list returns
  zero hits rather than an error, which is a silent trap.
* ``zipCodes`` behaves the same way. Repeat the parameter instead.
* ``sortBy=semanticRanking`` is rejected by /search/cases even though the
  frontend bundle lists it as a valid sort value.
* The parish heatmap returns either ``sold_per_area_price`` (recent sales) or
  ``sold_per_area_price_yearly`` (a wider window used where recent volume is
  thin). Some parishes return neither.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Iterable, Iterator, List, Optional

import requests

from . import config

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple thread safe token spacing. Boligsiden tolerates roughly 10
    requests per second; we sit below that deliberately."""

    def __init__(self, per_second: float) -> None:
        self._min_interval = 1.0 / per_second
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            sleep_for = self._min_interval - (now - self._last)
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last = time.monotonic()


class BoligsidenError(RuntimeError):
    """Raised when the API refuses a request we cannot retry our way out of."""


class BoligsidenClient:
    """Thin, honest wrapper. Returns parsed JSON and raises on real failures
    rather than swallowing them into empty results."""

    def __init__(self, base: str = config.BOLIGSIDEN_BASE) -> None:
        self.base = base.rstrip("/")
        self._limiter = RateLimiter(config.REQUESTS_PER_SECOND)
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": config.USER_AGENT,
                "Accept": "application/json",
                "Referer": "https://www.boligsiden.dk/",
                "Origin": "https://www.boligsiden.dk",
            }
        )

    # -- plumbing ---------------------------------------------------------

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base}{path}"
        last_error: Optional[Exception] = None

        for attempt in range(config.HTTP_RETRIES):
            self._limiter.wait()
            try:
                response = self._session.get(
                    url, params=params, timeout=config.HTTP_TIMEOUT
                )
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(2**attempt)
                continue

            if response.status_code == 200:
                return response.json()
            if response.status_code == 404:
                return None
            if response.status_code in (429, 500, 502, 503, 504):
                last_error = BoligsidenError(f"{response.status_code} on {path}")
                time.sleep(2**attempt)
                continue
            raise BoligsidenError(
                f"{response.status_code} on {path}: {response.text[:200]}"
            )

        raise BoligsidenError(
            f"gave up on {path} after {config.HTTP_RETRIES} attempts: {last_error}"
        )

    # -- search -----------------------------------------------------------

    def search_cases(self, **filters: Any) -> Dict[str, Any]:
        """One page of /search/cases. Pass filters straight through."""
        return self._get("/search/cases", filters) or {"cases": [], "totalHits": 0}

    def iter_cases(
        self,
        municipality: str,
        address_type: str,
        price_min: int,
        price_max: int,
        per_page: int = 50,
        max_pages: int = 200,
    ) -> Iterator[Dict[str, Any]]:
        """Page through every active listing matching the scope.

        Boligsiden caps pagination at 10.000 results. Our price band and single
        municipality keep us three orders of magnitude below that, so no
        subdivision logic is needed here.
        """
        page = 1
        seen = 0
        total: Optional[int] = None

        while page <= max_pages:
            payload = self.search_cases(
                addressTypes=address_type,
                municipalities=municipality,
                priceMin=price_min,
                priceMax=price_max,
                per_page=per_page,
                page=page,
            )
            cases = payload.get("cases") or []
            if total is None:
                total = payload.get("totalHits", 0)
                logger.info(
                    "%s / %s: %s listings between %s and %s kr",
                    municipality,
                    address_type,
                    total,
                    price_min,
                    price_max,
                )
            if not cases:
                return
            for case in cases:
                seen += 1
                yield case
            if total is not None and seen >= total:
                return
            page += 1

    # -- detail -----------------------------------------------------------

    def case(self, case_id: str) -> Optional[Dict[str, Any]]:
        return self._get(f"/cases/{case_id}")

    def case_timeline(self, case_id: str) -> List[Dict[str, Any]]:
        payload = self._get(f"/cases/{case_id}/timeline") or {}
        return payload.get("timeline") or []

    def address_timeline(self, address_id: str) -> List[Dict[str, Any]]:
        """Sale history for the physical address, back to the early 1990s,
        plus a ``built`` event. This is how we tell what the current seller
        paid and when."""
        payload = self._get(f"/addresses/{address_id}/timeline")
        return payload if isinstance(payload, list) else []

    # The endpoint answers 400 above 25 ids per request.
    BULK_STATS_CHUNK = 25

    def bulk_stats(
        self, case_ids: Iterable[str], chunk: int = BULK_STATS_CHUNK
    ) -> Dict[str, Dict[str, int]]:
        """Page views, click count and favourites, keyed by case id.

        This is the demand signal. No consumer facing part of Boligsiden shows
        it, and it is the difference between a flat nobody wants and a flat
        that is about to go in a bidding round.
        """
        ids = [i for i in case_ids if i]
        out: Dict[str, Dict[str, int]] = {}
        for start in range(0, len(ids), chunk):
            batch = ids[start : start + chunk]
            payload = self._get("/cases/bulk/stats", {"caseID": batch})
            if isinstance(payload, dict):
                out.update(payload)
        return out

    # -- benchmarks -------------------------------------------------------

    def parish_heatmap(
        self, municipality_code: int, address_type: str
    ) -> Dict[str, Any]:
        """GeoJSON FeatureCollection of parish (sogn) polygons carrying
        realised m2 prices. The sharpest geographic benchmark the API offers:
        Copenhagen alone splits into 56 parishes."""
        return self._get(
            f"/municipalities/{municipality_code}/parish_divisions/heatmap",
            {"addressType": address_type},
        ) or {"features": []}

    def zip_heatmap(self, municipality_code: int, address_type: str) -> Dict[str, Any]:
        return self._get(
            f"/municipalities/{municipality_code}/zip_codes/heatmap",
            {"addressType": address_type},
        ) or {"features": []}

    def municipality_average(
        self, municipality_code: int, address_type: str
    ) -> List[Dict[str, Any]]:
        """Average price and m2 price split by room count. Note the singular
        ``/case/`` in the path, which is not a typo on our side."""
        payload = self._get(
            "/case/stats/municipality-average",
            {"municipalityCode": municipality_code, "addressType": address_type},
        )
        return payload if isinstance(payload, list) else []

    def open_case_count(self) -> int:
        payload = self._get("/cases/open/count") or {}
        return int(payload.get("totalCount", 0))
