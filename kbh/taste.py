"""What the ratings say about what Mark actually likes.

The score in scoring.py encodes what he *said* he wants. This module measures
what he *does*, by comparing the listings he rated 4 or 5 against the ones he
rated 1 or 2, attribute by attribute.

Two rules the analysis sticks to, because the alternative is a machine that
sounds confident about eleven data points:

* Nothing is reported below a minimum sample. A gap computed from three liked
  and two disliked flats is noise wearing a percentage sign.
* Every finding carries its n. A pattern is a claim about evidence, so the
  evidence travels with it.
"""

from __future__ import annotations

import json
import sqlite3
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from . import config, db

LIKED = (4, 5)
DISLIKED = (1, 2)

# Below this many ratings on each side, say so and stop rather than produce a
# reading that looks quantitative and is not.
MIN_PER_SIDE = 4
MIN_GROUP = 3


@dataclass
class Finding:
    label: str
    liked: float
    disliked: float
    unit: str = ""
    n_liked: int = 0
    n_disliked: int = 0
    higher_is_liked: bool = True

    @property
    def gap(self) -> float:
        return self.liked - self.disliked

    @property
    def strength(self) -> float:
        """Gap as a share of the larger value, so factors on different scales
        can be ranked against each other."""
        base = max(abs(self.liked), abs(self.disliked), 1e-9)
        return abs(self.gap) / base

    def sentence(self) -> str:
        direction = "højere" if self.gap > 0 else "lavere"
        return (
            f"{self.label}: {self.liked:,.0f}{self.unit} blandt dem du kan lide "
            f"mod {self.disliked:,.0f}{self.unit} blandt dem du ikke kan lide "
            f"({direction})"
        ).replace(",", ".")


@dataclass
class TasteReport:
    total_rated: int = 0
    n_liked: int = 0
    n_disliked: int = 0
    enough_data: bool = False
    findings: List[Finding] = field(default_factory=list)
    neighbourhoods: List[Dict[str, Any]] = field(default_factory=list)
    agreement: Optional[float] = None
    suggested_weights: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    comments: List[Dict[str, Any]] = field(default_factory=list)
    ai_summary: str = ""


NUMERIC_ATTRIBUTES = [
    ("living_area", "Størrelse", " m2", True),
    ("price", "Pris", " kr.", True),
    ("per_area_price", "Kvadratmeterpris", " kr/m2", False),
    ("water_distance_m", "Afstand til vand", " m", False),
    ("monthly_expense", "Ejerudgift", " kr/md.", False),
    ("year_built", "Byggeår", "", True),
    ("days_listed", "Dage til salg", "", True),
    ("number_of_rooms", "Værelser", "", True),
]


def _mean(values: Sequence[float]) -> Optional[float]:
    clean = [v for v in values if v is not None]
    return statistics.mean(clean) if clean else None


def analyse(conn: sqlite3.Connection, rater: Optional[str] = None) -> TasteReport:
    """What one person's ratings say about what they actually like.

    Per person on purpose. Two buyers averaged together produce a preference
    profile that describes neither of them, and the disagreements are exactly
    the signal worth keeping rather than smoothing away.
    """
    rows = [dict(r) for r in db.rated_listings(conn, rater=rater)]
    report = TasteReport(total_rated=len(rows))

    liked = [r for r in rows if r["stars"] in LIKED]
    disliked = [r for r in rows if r["stars"] in DISLIKED]
    report.n_liked, report.n_disliked = len(liked), len(disliked)

    # Comments are collected regardless of sample size. Numbers need a
    # threshold before they mean anything; a written sentence about a specific
    # flat is worth reading from the first one.
    report.comments = [
        {
            "case_id": r["case_id"],
            "address": r["address"],
            "stars": r["stars"],
            "note": r["rating_note"],
            "neighbourhood": r.get("neighbourhood"),
            "price": r.get("price"),
            "living_area": r.get("living_area"),
            "per_area_price": r.get("per_area_price"),
            "water_distance_m": r.get("water_distance_m"),
        }
        for r in rows
        if (r.get("rating_note") or "").strip()
    ]

    if len(liked) < MIN_PER_SIDE or len(disliked) < MIN_PER_SIDE:
        report.notes.append(
            f"Der skal mindst være {MIN_PER_SIDE} boliger med 4 til 5 stjerner og "
            f"{MIN_PER_SIDE} med 1 til 2, før mønstrene betyder noget. Lige nu: "
            f"{len(liked)} og {len(disliked)}."
        )
        return report

    report.enough_data = True

    # --- numeric attributes ------------------------------------------------
    for key, label, unit, higher_is_liked in NUMERIC_ATTRIBUTES:
        a = _mean([r.get(key) for r in liked])
        b = _mean([r.get(key) for r in disliked])
        if a is None or b is None:
            continue
        report.findings.append(
            Finding(
                label=label,
                liked=a,
                disliked=b,
                unit=unit,
                n_liked=len(liked),
                n_disliked=len(disliked),
                higher_is_liked=higher_is_liked,
            )
        )

    # --- the score's own factors ------------------------------------------
    # This is the useful one: it says which parts of the scoring model are
    # actually tracking his judgement and which are along for the ride.
    for factor_key, factor_label in config.FACTOR_LABELS.items():
        a = _mean([_factor_score(r, factor_key) for r in liked])
        b = _mean([_factor_score(r, factor_key) for r in disliked])
        if a is None or b is None:
            continue
        report.findings.append(
            Finding(
                label=f"Faktor: {factor_label}",
                liked=a,
                disliked=b,
                unit=" point",
                n_liked=len(liked),
                n_disliked=len(disliked),
            )
        )

    report.findings.sort(key=lambda f: f.strength, reverse=True)

    # --- neighbourhoods ----------------------------------------------------
    hoods: Dict[str, List[int]] = {}
    for row in rows:
        if row.get("neighbourhood"):
            hoods.setdefault(row["neighbourhood"], []).append(row["stars"])
    report.neighbourhoods = sorted(
        (
            {"name": name, "n": len(stars), "avg": round(statistics.mean(stars), 2)}
            for name, stars in hoods.items()
            if len(stars) >= MIN_GROUP
        ),
        key=lambda h: h["avg"],
        reverse=True,
    )

    # --- does the score agree with him? ------------------------------------
    report.agreement = _agreement(rows)

    # --- what the weights would look like if they followed his ratings -----
    report.suggested_weights = _suggested_weights(report.findings)

    return report


def _factor_score(row: Dict[str, Any], key: str) -> Optional[float]:
    raw = row.get("breakdown")
    if not raw:
        return None
    try:
        breakdown = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return None
    for factor in breakdown:
        if factor.get("key") == key:
            # A neutral placeholder is an absence of evidence, not evidence of
            # an average flat, so it must not drag the mean toward 50.
            return None if factor.get("neutral") else factor.get("score")
    return None


def _agreement(rows: Sequence[Dict[str, Any]]) -> Optional[float]:
    """Spearman style rank agreement between the model score and the stars.

    Reported so the model can be caught disagreeing with him, which is the
    whole point of collecting ratings.
    """
    pairs = [(r.get("score_when_rated") or r.get("score"), r["stars"]) for r in rows]
    pairs = [(s, k) for s, k in pairs if s is not None]
    if len(pairs) < 6:
        return None

    def ranks(values: Sequence[float]) -> List[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        for rank, index in enumerate(order):
            out[index] = float(rank)
        return out

    x = ranks([p[0] for p in pairs])
    y = ranks([float(p[1]) for p in pairs])
    n = len(pairs)
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    return round(num / den, 3) if den else None


def _suggested_weights(findings: Sequence[Finding]) -> Dict[str, float]:
    """Re-weight the scoring factors in proportion to how well each one
    separates liked from disliked.

    Deliberately a suggestion and nothing more. It is printed for a human to
    accept or ignore, never applied automatically: a handful of ratings should
    not be allowed to silently rewrite the model.
    """
    label_to_key = {f"Faktor: {v}": k for k, v in config.FACTOR_LABELS.items()}
    separations: Dict[str, float] = {}
    for finding in findings:
        key = label_to_key.get(finding.label)
        if key is None:
            continue
        # Only count a factor when liked flats score higher on it.
        separations[key] = max(finding.gap, 0.0)

    total = sum(separations.values())
    if total <= 0:
        return {}

    # Blend halfway toward the observed separation, so a small sample nudges
    # the weights rather than replacing them.
    suggested = {}
    for key, current in config.WEIGHTS.items():
        observed = 100.0 * separations.get(key, 0.0) / total
        suggested[key] = round((current + observed) / 2, 1)

    scale = 100.0 / sum(suggested.values())
    scaled = {k: round(v * scale, 1) for k, v in suggested.items()}

    # Rounding to one decimal leaves the total a tenth or two off 100, and
    # config.validate_weights() raises on exactly that. Since the whole point
    # is that these can be pasted straight into config.py, the remainder is
    # pushed onto the largest weight so the suggestion is always valid.
    drift = round(100.0 - sum(scaled.values()), 1)
    if drift:
        heaviest = max(scaled, key=lambda k: scaled[k])
        scaled[heaviest] = round(scaled[heaviest] + drift, 1)
    return scaled
