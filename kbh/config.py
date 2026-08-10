"""Search scope, hard filters, neighbourhood tiers and scoring weights.

Everything a human would want to tune lives here. No tuning knobs are hidden
in the scoring module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

PACKAGE_DIR: Path = Path(__file__).resolve().parent
REPO_ROOT: Path = PACKAGE_DIR.parent
DATA_DIR: Path = PACKAGE_DIR / "data"

# Load .env before anything reads os.environ. Silent if the file is absent, so
# the package still imports on a machine that configures things another way.
try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(PACKAGE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass

DB_PATH: Path = Path(os.environ.get("KBH_DB_PATH", DATA_DIR / "kbh.sqlite3"))
WATER_GEOJSON: Path = DATA_DIR / "water.geojson"
PARISH_GEOJSON: Path = DATA_DIR / "parishes.geojson"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# Search scope
# --------------------------------------------------------------------------

PRICE_MIN: int = 5_000_000
PRICE_MAX: int = 10_000_000


@dataclass(frozen=True)
class SearchScope:
    """One Boligsiden query. The API rejects multi-value municipality filters,
    so each municipality and address type combination is its own query."""

    municipality: str
    municipality_code: int
    address_type: str
    label: str


SEARCH_SCOPES: Tuple[SearchScope, ...] = (
    SearchScope("københavn", 101, "condo", "København, ejerlejlighed"),
    SearchScope("frederiksberg", 147, "condo", "Frederiksberg, ejerlejlighed"),
    SearchScope("københavn", 101, "villa", "København, villa og rækkehus"),
    SearchScope("københavn", 101, "terraced house", "København, rækkehus"),
)

# Address types accepted by the benchmark endpoints. Boligsiden groups villas
# and terraced houses into a single benchmark bucket.
BENCHMARK_ADDRESS_TYPE: Dict[str, str] = {
    "condo": "condo",
    "villa": "villa and terraced house",
    "terraced house": "villa and terraced house",
}

BENCHMARK_MUNICIPALITIES: Tuple[int, ...] = (101, 147)

# --------------------------------------------------------------------------
# Hard filters. A listing failing any of these is stored but flagged
# ``excluded`` and never scored, alerted or shown by default.
# --------------------------------------------------------------------------

MIN_LIVING_AREA: int = 90
EXCLUDE_GROUND_FLOOR: bool = True

# Boligsiden floor values seen in the wild for ground level and below.
GROUND_FLOOR_TOKENS: Tuple[str, ...] = ("st", "st.", "0", "kl", "kl.", "k", "sou", "s")

# --------------------------------------------------------------------------
# Neighbourhoods
#
# Boligsiden groups postal codes itself (the ``group`` field on /zip_codes).
# That grouping matches how Copenhageners actually talk about the city, so it
# is the label source. Tier is Mark's stated preference, 0 to 100.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Neighbourhood:
    name: str
    tier: int
    note: str = ""


NEIGHBOURHOODS: Dict[int, Neighbourhood] = {
    2150: Neighbourhood("Nordhavn", 95, "Priority. Waterfront by construction."),
    2100: Neighbourhood("Østerbro", 92, "Priority."),
    2200: Neighbourhood("Nørrebro", 90, "Priority."),
    1500: Neighbourhood("Vesterbro", 88, "Priority."),
    # Postal code 2300 covers Amagerbro, Sundby, Ørestad and the beach in one
    # bucket. The base tier is set for the ordinary parts of it; the named
    # areas below pull the good bits up and Ørestad down.
    2300: Neighbourhood("Amager", 66, "Named areas override this in both directions."),
    1000: Neighbourhood(
        "Indre By", 75, "Not on the priority list but hard to argue with."
    ),
    1800: Neighbourhood("Frederiksberg C", 70, ""),
    2000: Neighbourhood("Frederiksberg", 68, ""),
    2450: Neighbourhood("Sydhavn", 60, "Waterfront pockets score well on water alone."),
    2400: Neighbourhood("Nordvest", 52, ""),
    2500: Neighbourhood("Valby", 48, ""),
    2720: Neighbourhood("Vanløse", 42, ""),
    2700: Neighbourhood("Brønshøj", 38, ""),
}

DEFAULT_NEIGHBOURHOOD: Neighbourhood = Neighbourhood("Øvrige København", 35)

# Named sub-areas that deserve their own tier regardless of postal code.
# Each is a centre point and a radius in metres. Checked before the postal
# code lookup; the highest matching tier wins.


@dataclass(frozen=True)
class NamedArea:
    """A sub-area whose tier differs from its postal code's.

    ``override`` matters. Without it the highest tier wins, which is right for
    areas that are better than their postal code. Ørestad is the opposite
    case: it shares postal code 2300 with Amager Strandpark and Amagerbro but
    is a different place entirely, so it has to be able to pull the tier down.
    """

    name: str
    tier: int
    lat: float
    lon: float
    radius_m: Optional[int] = None
    bbox: Optional[Tuple[float, float, float, float]] = None  # S, W, N, E
    override: bool = False


NAMED_AREAS: Tuple[NamedArea, ...] = (
    NamedArea("Amager Strandpark", 95, 55.66330, 12.63200, radius_m=1200),
    NamedArea("Islands Brygge", 88, 55.66600, 12.58500, radius_m=900),
    NamedArea("Christianshavn", 85, 55.67300, 12.59200, radius_m=900),
    NamedArea("Amagerbro", 74, 55.66100, 12.60300, radius_m=1100),
    NamedArea("Havneholmen og Kalvebod Brygge", 80, 55.66100, 12.56400, radius_m=700),
    NamedArea("Sluseholmen", 72, 55.64600, 12.54300, radius_m=800),
    # Ørestad. Newbuild, well connected, and nothing at all like the parts of
    # Amager on the priority list. Overrides postal code 2300 downwards.
    NamedArea(
        "Ørestad",
        45,
        55.63500,
        12.58000,
        bbox=(55.600, 12.560, 55.657, 12.610),
        override=True,
    ),
)

# --------------------------------------------------------------------------
# Water proximity
#
# Mark asked for the harbour, the canals and the lakes. The OSM extract in
# geo.py separates prime water (harbour basins, canals, the five lakes, the
# Øresund coast) from secondary water (inland ponds, moats, Damhussøen).
# Prime water scores on the full curve; secondary water is capped.
# --------------------------------------------------------------------------

WATER_FULL_SCORE_M: int = 150  # at or under this distance, 100 points
WATER_ZERO_SCORE_M: int = 1800  # at or over this distance, 0 points
SECONDARY_WATER_CAP: float = 55.0  # best a pond can do for you

# --------------------------------------------------------------------------
# Scoring weights. Must sum to 100.
# --------------------------------------------------------------------------

# The factor order, which is also the order the UI shows them in. WEIGHTS is
# set from the active profile further down.
FACTOR_KEYS: Tuple[str, ...] = (
    "sqm_price_vs_benchmark",
    "neighbourhood",
    "water",
    "size",
    "condition",
    "negotiation_leverage",
    "monthly_expense",
)

# Weight profiles.
#
# Re-weighting is arithmetic on numbers that are already stored: every factor's
# 0 to 100 score sits in scores.breakdown, so switching profile recomputes a
# total instantly and costs nothing. The AI verdict is about the flat itself and
# is unaffected, so nothing needs re-reading when the weights change.
PROFILES: Dict[str, Dict[str, Any]] = {
    "balanceret": {
        "name": "Balanceret",
        "note": "Kvadratmeterpris og kvarter vejer tungest. Vand tæller med, "
        "men afgør ikke længere feltet.",
        "weights": {
            "sqm_price_vs_benchmark": 32.0,
            "neighbourhood": 22.0,
            "water": 8.0,
            "size": 15.0,
            "condition": 11.0,
            "negotiation_leverage": 7.0,
            "monthly_expense": 5.0,
        },
    },
    "ved_vandet": {
        "name": "Ved vandet",
        "note": "Den oprindelige vægtning. Nærhed til havn, kanaler og søer "
        "vejer tungt nok til at flytte en bolig flere pladser op.",
        "weights": {
            "sqm_price_vs_benchmark": 30.0,
            "neighbourhood": 20.0,
            "water": 15.0,
            "size": 12.0,
            "condition": 10.0,
            "negotiation_leverage": 8.0,
            "monthly_expense": 5.0,
        },
    },
    "vaerdijaeger": {
        "name": "Værdijæger",
        "note": "Hvad er underprissat, og hvor er sælgeren træt. Finder også "
        "boliger i kvarterer du ikke havde tænkt på.",
        "weights": {
            "sqm_price_vs_benchmark": 45.0,
            "neighbourhood": 12.0,
            "water": 5.0,
            "size": 12.0,
            "condition": 6.0,
            "negotiation_leverage": 15.0,
            "monthly_expense": 5.0,
        },
    },
    "plads_for_pengene": {
        "name": "Plads for pengene",
        "note": "Kvadratmeter først. Rykker de store lejligheder i de billigere "
        "kvarterer op, og straffer høj ejerudgift hårdere.",
        "weights": {
            "sqm_price_vs_benchmark": 30.0,
            "neighbourhood": 14.0,
            "water": 5.0,
            "size": 30.0,
            "condition": 9.0,
            "negotiation_leverage": 5.0,
            "monthly_expense": 7.0,
        },
    },
}

DEFAULT_PROFILE: str = os.environ.get("KBH_PROFILE", "balanceret")

# What the pipeline scores with when nothing overrides it. The web app can
# recompute any listing under any profile without touching this, because the
# per factor scores are stored and only the arithmetic changes.
WEIGHTS: Dict[str, float] = dict(PROFILES[DEFAULT_PROFILE]["weights"])


def normalise_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Scale arbitrary slider values to sum to exactly 100.

    The custom profile lets any number go in any box, so this is what makes the
    result a valid weighting rather than an arbitrary multiplier. The rounding
    remainder lands on the largest weight.
    """
    clean = {k: max(float(weights.get(k, 0) or 0), 0.0) for k in FACTOR_KEYS}
    total = sum(clean.values())
    if total <= 0:
        return dict(PROFILES[DEFAULT_PROFILE]["weights"])
    scaled = {k: round(v * 100.0 / total, 1) for k, v in clean.items()}
    drift = round(100.0 - sum(scaled.values()), 1)
    if drift:
        heaviest = max(scaled, key=lambda k: scaled[k])
        scaled[heaviest] = round(scaled[heaviest] + drift, 1)
    return scaled


FACTOR_LABELS: Dict[str, str] = {
    "sqm_price_vs_benchmark": "Kvadratmeterpris mod sognet",
    "neighbourhood": "Kvarter",
    "water": "Afstand til vand",
    "size": "Størrelse",
    "condition": "Stand, energi og alder",
    "negotiation_leverage": "Forhandlingsposition",
    "monthly_expense": "Ejerudgift",
}

# Bonuses applied after the weighted score, capped in total by BONUS_CAP.
BONUS_BALCONY: float = 3.0
BONUS_TERRACE: float = 2.0
BONUS_ELEVATOR: float = 1.5
BONUS_CAP: float = 5.0

# Size scoring. Below MIN_LIVING_AREA a listing is excluded outright, so this
# curve starts at the floor.
SIZE_FLOOR_M2: int = 90
SIZE_TOP_M2: int = 160
# A flat that only just clears the 90 m2 floor should not score zero on size,
# because it already passed a hard filter to get here.
SIZE_FLOOR_SCORE: float = 30.0

# m2 price against the local benchmark. Ratio below 1.0 means the flat is
# asking less per m2 than its own parish has actually been selling for.
SQM_RATIO_BEST: float = 0.75  # and better, scores 100
SQM_RATIO_PAR: float = 1.00  # at the benchmark
SQM_RATIO_PAR_SCORE: float = 60.0
SQM_RATIO_WORST: float = 1.30  # and worse, scores 0

ENERGY_SCORES: Dict[str, float] = {
    "a2020": 100.0,
    "a2015": 100.0,
    "a2010": 96.0,
    "a1": 96.0,
    "a2": 94.0,
    "a": 92.0,
    "b": 84.0,
    "c": 70.0,
    "d": 55.0,
    "e": 40.0,
    "f": 25.0,
    "g": 10.0,
}

# --------------------------------------------------------------------------
# Alerting
# --------------------------------------------------------------------------

ALERT_SCORE_THRESHOLD: float = float(os.environ.get("KBH_ALERT_THRESHOLD", 72))
DIGEST_HOUR_LOCAL: int = 8
DIGEST_SIZE: int = 8

# A price drop on a listing we already track is worth an alert even if the
# score sits below the threshold, provided the drop is meaningful.
ALERT_PRICE_DROP_PCT: float = 2.0

# --------------------------------------------------------------------------
# AI
# --------------------------------------------------------------------------

# Verdicts run through the claude CLI against the existing subscription, not
# through the API with a key. Set KBH_CLAUDE_BIN to point at a specific binary.
#
# Haiku for the per listing pass. It is reading structured facts and a realtor
# text against an explicit checklist, which is exactly the kind of work that
# does not need a larger model. The synthesis pass runs once a day over already
# gathered results, so it can afford Opus.
AI_MODEL: str = os.environ.get("KBH_AI_MODEL", "claude-haiku-4-5-20251001")
AI_SYNTHESIS_MODEL: str = os.environ.get("KBH_AI_SYNTHESIS_MODEL", "claude-opus-5")

# Listings per CLI call.
#
# Every call carries roughly 38.000 tokens of fixed Claude Code system prompt
# before a single word of listing text. Paying that 200 times is the single
# largest cost in a backfill, and batching is the only thing that touches it.
# Six listings per call cuts the fixed overhead per listing by about 83 pct.
AI_BATCH_SIZE: int = int(os.environ.get("KBH_AI_BATCH_SIZE", 6))

# Send real photos, or the alt text Boligsiden already generated for them.
#
# Every image on Boligsiden carries a machine written description ("En altan med
# trædæk har en åben dør, potteplanter og en bænk med puder"). It answers the
# "what do the photos show" question at zero token cost, where five actual
# images cost around 55.000 input tokens per listing. Off by default; turn it on
# for a shortlist where the pictures genuinely need looking at.
AI_USE_PHOTOS: bool = os.environ.get("KBH_AI_USE_PHOTOS", "0") in ("1", "true", "True")
# Photos dominate the token bill: five of them put a call near 100.000 input
# tokens and 0.23 USD. Drop this to 3 to roughly halve the cost per listing.
AI_MAX_IMAGES: int = int(os.environ.get("KBH_AI_MAX_IMAGES", 5))
AI_ENABLED: bool = os.environ.get("KBH_AI_ENABLED", "1") not in ("0", "false", "False")
# CLI processes are heavier than API calls, so the fan-out is smaller.
AI_WORKERS: int = int(os.environ.get("KBH_AI_WORKERS", 3))

# Do not spend a verdict on a listing the numbers have already ruled out.
# A call runs at roughly 0.10 to 0.15 USD with five photos attached, so reading
# all 500 candidates costs real money, while reading the 250 that score above
# this gate costs half as much and loses nothing worth having. Steady state is
# only the handful that appear or reprice each day.
AI_MIN_SCORE: float = float(os.environ.get("KBH_AI_MIN_SCORE", 62))

# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

BOLIGSIDEN_BASE: str = "https://api.boligsiden.dk"
REQUESTS_PER_SECOND: float = 6.0
HTTP_TIMEOUT: int = 40
HTTP_RETRIES: int = 4

USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@dataclass
class RuntimeConfig:
    """Values read from the environment at run time rather than import time."""

    telegram_token: str = field(
        default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN", "")
    )
    telegram_chat_id: str = field(
        default_factory=lambda: os.environ.get("TELEGRAM_CHAT_ID", "")
    )

    @property
    def telegram_ready(self) -> bool:
        return bool(self.telegram_token and self.telegram_chat_id)

    @property
    def ai_ready(self) -> bool:
        """Verdicts go through the claude CLI, so there is no API key to
        check. Imported inside the property to keep this module dependency
        free at import time."""
        if not AI_ENABLED:
            return False
        from . import ai

        return ai.cli_available()


def validate_weights() -> None:
    """Raise if the weights no longer sum to 100."""
    total = sum(WEIGHTS.values())
    if abs(total - 100.0) > 0.001:
        raise ValueError(f"Scoring weights must sum to 100, got {total}")


validate_weights()
