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
TRANSIT_GEOJSON: Path = DATA_DIR / "transit.geojson"
NOISE_GEOJSON: Path = DATA_DIR / "noise.geojson"

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
    "rooms",
    "transit",
    "noise",
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
        "note": "Kvadratmeterpris og kvarter vejer tungest. Vand, metro og "
        "vejstøj tæller med, men afgør ikke feltet alene.",
        "weights": {
            "sqm_price_vs_benchmark": 27.0,
            "neighbourhood": 15.0,
            "water": 7.0,
            "size": 10.0,
            "rooms": 8.0,
            "transit": 8.0,
            "noise": 6.0,
            "condition": 8.0,
            "negotiation_leverage": 6.0,
            "monthly_expense": 5.0,
        },
    },
    "ved_vandet": {
        "name": "Ved vandet",
        "note": "Nærhed til havn, kanaler og søer vejer tungt nok til at "
        "flytte en bolig flere pladser op.",
        "weights": {
            "sqm_price_vs_benchmark": 26.0,
            "neighbourhood": 15.0,
            "water": 14.0,
            "size": 9.0,
            "rooms": 7.0,
            "transit": 6.0,
            "noise": 5.0,
            "condition": 8.0,
            "negotiation_leverage": 6.0,
            "monthly_expense": 4.0,
        },
    },
    "vaerdijaeger": {
        "name": "Værdijæger",
        "note": "Hvad er underprissat, og hvor er sælgeren træt. Finder også "
        "boliger i kvarterer du ikke havde tænkt på.",
        "weights": {
            "sqm_price_vs_benchmark": 40.0,
            "neighbourhood": 8.0,
            "water": 4.0,
            "size": 8.0,
            "rooms": 5.0,
            "transit": 5.0,
            "noise": 4.0,
            "condition": 5.0,
            "negotiation_leverage": 16.0,
            "monthly_expense": 5.0,
        },
    },
    "plads_for_pengene": {
        "name": "Plads for pengene",
        "note": "Kvadratmeter og værelser først. Rykker de store lejligheder i "
        "de billigere kvarterer op, og straffer høj ejerudgift hårdere.",
        "weights": {
            "sqm_price_vs_benchmark": 26.0,
            "neighbourhood": 10.0,
            "water": 4.0,
            "size": 22.0,
            "rooms": 12.0,
            "transit": 6.0,
            "noise": 5.0,
            "condition": 6.0,
            "negotiation_leverage": 4.0,
            "monthly_expense": 5.0,
        },
    },
}

DEFAULT_PROFILE: str = os.environ.get("KBH_PROFILE", "balanceret")

# What the pipeline scores with when nothing overrides it. The web app can
# recompute any listing under any profile without touching this, because the
# per factor scores are stored and only the arithmetic changes.
WEIGHTS: Dict[str, float] = dict(PROFILES[DEFAULT_PROFILE]["weights"])


def normalise_weights(
    weights: Dict[str, float], fill_missing: bool = False
) -> Dict[str, float]:
    """Scale arbitrary slider values to sum to exactly 100.

    The custom profile lets any number go in any box, so this is what makes the
    result a valid weighting rather than an arbitrary multiplier. The rounding
    remainder lands on the largest weight.

    ``fill_missing`` decides what an absent factor means, and the two cases are
    genuinely different. Coming from the slider form, absent means the slider
    was dragged to zero and the factor should be switched off. Coming from a
    weighting saved before a new factor existed, absent means the question was
    never asked, and zeroing it would silently disable the new factor for
    anyone with a saved custom profile. That is how rooms, transit and noise
    were switched off for their first run after being added.
    """
    if fill_missing:
        defaults = PROFILES[DEFAULT_PROFILE]["weights"]
        weights = {k: weights.get(k, defaults.get(k, 0.0)) for k in FACTOR_KEYS}
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
    "rooms": "Værelser og rumfordeling",
    "transit": "Afstand til metro og S-tog",
    "noise": "Vejstøj og banestøj",
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

# --------------------------------------------------------------------------
# Rooms
#
# Square metres and rooms are not the same question. A 120 m2 three room and a
# 120 m2 five room score identically on size and are different homes, which is
# why this is its own factor rather than a term inside the size curve.
#
# Mark's stated preference is more than three rooms, so four is where the curve
# turns steeply upwards. Three is liveable rather than wrong, so it sits below
# par rather than at zero.
# --------------------------------------------------------------------------

ROOM_SCORES: Dict[int, float] = {
    1: 0.0,
    2: 15.0,
    3: 45.0,
    4: 85.0,
    5: 100.0,
}
# Anything at or above this many rooms gets the top score.
ROOM_TOP_COUNT: int = 5

# Rooms alone can be gamed by chopping a flat into cupboards, so a very low
# mean area per room takes points back off. Living area includes kitchen,
# bathroom and hallway while the room count does not, so a normal Copenhagen
# flat lands well above this and is untouched.
ROOM_AREA_TIGHT_M2: float = 20.0
ROOM_AREA_PENALTY_MAX: float = 15.0

# --------------------------------------------------------------------------
# Transit
#
# Copenhagen is a rail city, and at this price point walking distance to a
# metro or S-tog platform separates two otherwise identical flats.
#
# The curve starts falling at 250 m rather than at a comfortable five minute
# walk, because a flatter curve measured against the real pool put half of all
# listings at 98 or better and the factor separated nothing. Median distance
# across the pool is 437 m, so 250 m is where the discrimination actually is.
# Zero at 1.500 m, roughly an eighteen minute walk, which is where people
# start cycling instead and stop counting the station as theirs.
# --------------------------------------------------------------------------

TRANSIT_FULL_SCORE_M: int = 250
TRANSIT_ZERO_SCORE_M: int = 1500

# --------------------------------------------------------------------------
# Noise
#
# Road noise is modelled from lane count and speed limit, NOT from the OSM
# highway class. That is not a stylistic choice, it is forced by how Denmark
# is tagged, and getting it wrong makes the factor worse than useless.
#
# Danish OSM reserves primary and secondary for the national numbered road
# network. Every major urban artery in Copenhagen is therefore tagged
# tertiary: H.C. Andersens Boulevard, Åboulevard, Vesterbrogade, Jagtvej,
# Tagensvej, Amagerbrogade and Østerbrogade are all the same class as a quiet
# residential through street. A model built on highway class scores the
# busiest road in the country as silent.
#
# Lanes and speed are both tagged on 90 pct. and 99 pct. of those ways
# respectively, and they separate the same streets properly: H.C. Andersens
# Boulevard runs 3 to 5 lanes at 50 to 60, while Nørrebrogade runs 1 to 2
# lanes at 40 because it has been traffic calmed. That is the real difference
# between the two addresses, and the class tag cannot see it.
#
# This is a proxy for traffic volume, not measured sound. Denmark publishes
# actual modelled Lden contours under the EU noise directive, which would be
# strictly better; the portal serving them needs registration, so it is on the
# to-do list rather than in here.
# --------------------------------------------------------------------------

# Lane count to a base emission weight. Traffic volume scales roughly with the
# number of lanes provided for it.
NOISE_LANE_WEIGHT: Dict[int, float] = {1: 12.0, 2: 28.0, 3: 48.0, 4: 66.0, 5: 80.0}
NOISE_LANE_TOP: int = 5  # this many lanes or more takes the top weight
NOISE_LANE_DEFAULT: float = 28.0  # untagged, treated as an ordinary two lane street

# Speed limit multiplier. Tyre noise dominates above about 40 km/h and rises
# with speed, so the same traffic is louder on a 60 road than on a 30 one.
NOISE_SPEED_MULT: Dict[int, float] = {
    30: 0.70,
    40: 0.85,
    50: 1.00,
    60: 1.15,
    70: 1.30,
    80: 1.45,
}
NOISE_SPEED_DEFAULT: float = 1.00

# Floors for grade separated high volume roads, whose lane tagging understates
# what it is like to live beside them.
NOISE_CLASS_FLOOR: Dict[str, float] = {
    "motorway": 92.0,
    "trunk": 80.0,
    "primary": 55.0,
}

# A train is a train, so railways carry a fixed weight rather than a modelled
# one. Tunnels are excluded at fetch time.
NOISE_RAILWAY_WEIGHT: float = 55.0

# How far a source of a given weight carries, in metres. The loudest roads
# reach about 500 m, an ordinary two lane street about 200 m.
NOISE_REACH_BASE_M: float = 80.0
NOISE_REACH_PER_WEIGHT_M: float = 4.2

# Highway classes worth pulling at all. Residential and unclassified streets
# are the normal condition of living in a city and would add a constant to
# every listing rather than telling them apart.
NOISE_HIGHWAY_CLASSES: Tuple[str, ...] = (
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
)

NOISE_LABELS: Dict[str, str] = {
    "motorway": "motorvej",
    "trunk": "indfaldsvej",
    "primary": "større trafikvej",
    "secondary": "trafikvej",
    "tertiary": "bytrafikvej",
    "railway": "jernbane",
}


def noise_weight(
    kind: str, lanes: Optional[float] = None, maxspeed: Optional[float] = None
) -> float:
    """Emission weight, 0 to 100, for one road or railway.

    Kept here rather than in geo.py so the whole noise model is tunable from
    the one file a human is expected to edit.
    """
    if kind == "railway":
        return NOISE_RAILWAY_WEIGHT

    if lanes and lanes > 0:
        count = int(round(lanes))
        base = NOISE_LANE_WEIGHT.get(
            min(count, NOISE_LANE_TOP), NOISE_LANE_WEIGHT[NOISE_LANE_TOP]
        )
    else:
        base = NOISE_LANE_DEFAULT

    if maxspeed and maxspeed > 0:
        # Round to the nearest tabulated limit rather than requiring an exact
        # match, so an unusual 45 or 55 still lands somewhere sensible.
        nearest = min(NOISE_SPEED_MULT, key=lambda s: abs(s - maxspeed))
        multiplier = NOISE_SPEED_MULT[nearest]
    else:
        multiplier = NOISE_SPEED_DEFAULT

    weight = base * multiplier
    return max(weight, NOISE_CLASS_FLOOR.get(kind, 0.0))


def noise_reach_m(weight: float) -> float:
    """How far a source of this weight is still audible enough to matter."""
    return NOISE_REACH_BASE_M + NOISE_REACH_PER_WEIGHT_M * weight


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
