"""Scoring.

Seven weighted factors, each normalised to 0 to 100, then a small capped
bonus for balcony, terrace and lift. Weights live in config.py.

Two principles the code sticks to:

* A missing input never silently becomes a zero. It becomes an explicitly
  neutral score and the factor is flagged, so a flat is never punished for
  Boligsiden having a gap in its data.
* Every factor returns its own reasoning string. The score is auditable line
  by line, which matters when the thing wakes you up at seven in the morning
  telling you to look at a flat.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from . import config


@dataclass
class FactorScore:
    key: str
    score: float
    weight: float
    reason: str
    neutral: bool = False

    @property
    def contribution(self) -> float:
        return self.score * self.weight / 100.0

    @property
    def label(self) -> str:
        return config.FACTOR_LABELS.get(self.key, self.key)


@dataclass
class MarketContext:
    """Peer statistics computed across the current candidate pool.

    Relative factors need something to be relative to. Using the live pool
    rather than a fixed constant means the scoring adapts as the market moves
    without anyone editing a threshold.
    """

    median_days_listed: float = 90.0
    median_expense_per_sqm: float = 45.0
    median_favourites_per_week: float = 4.0

    @classmethod
    def from_listings(cls, rows: Sequence[Dict[str, Any]]) -> "MarketContext":
        def median_of(values: List[float], fallback: float) -> float:
            clean = [v for v in values if v is not None and v > 0]
            return statistics.median(clean) if len(clean) >= 5 else fallback

        days = [r.get("days_listed") for r in rows]

        expense = []
        for r in rows:
            area, cost = r.get("living_area"), r.get("monthly_expense")
            if area and cost and area > 0:
                expense.append(cost / area)

        favourites = []
        for r in rows:
            favs, listed = r.get("favourites"), r.get("days_listed")
            if favs is not None and listed and listed > 0:
                favourites.append(favs / max(listed / 7.0, 1.0))

        return cls(
            median_days_listed=median_of(days, 90.0),
            median_expense_per_sqm=median_of(expense, 45.0),
            median_favourites_per_week=median_of(favourites, 4.0),
        )


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _lerp(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    if x1 == x0:
        return y0
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


# --------------------------------------------------------------------------
# Factors
# --------------------------------------------------------------------------


def score_sqm_price(
    listing: Dict[str, Any], benchmark: Optional[int], basis: str
) -> FactorScore:
    """Asking price per m2 against what the flat's own parish has actually
    been selling for. The single heaviest factor."""
    weight = config.WEIGHTS["sqm_price_vs_benchmark"]
    area = listing.get("living_area")
    price = listing.get("price")

    if not area or not price or area <= 0:
        return FactorScore(
            "sqm_price_vs_benchmark",
            50.0,
            weight,
            "Mangler pris eller areal",
            neutral=True,
        )
    if not benchmark or benchmark <= 0:
        return FactorScore(
            "sqm_price_vs_benchmark",
            50.0,
            weight,
            "Intet lokalt benchmark tilgængeligt",
            neutral=True,
        )

    own = price / area
    ratio = own / benchmark

    if ratio <= config.SQM_RATIO_BEST:
        score = 100.0
    elif ratio <= config.SQM_RATIO_PAR:
        score = _lerp(
            ratio,
            config.SQM_RATIO_BEST,
            100.0,
            config.SQM_RATIO_PAR,
            config.SQM_RATIO_PAR_SCORE,
        )
    elif ratio <= config.SQM_RATIO_WORST:
        score = _lerp(
            ratio,
            config.SQM_RATIO_PAR,
            config.SQM_RATIO_PAR_SCORE,
            config.SQM_RATIO_WORST,
            0.0,
        )
    else:
        score = 0.0

    delta = (ratio - 1.0) * 100
    direction = "under" if delta < 0 else "over"
    basis_note = "seneste salg" if basis == "recent" else "salg over 12 mdr."
    reason = (
        f"{own:,.0f} kr/m2 mod {benchmark:,.0f} kr/m2 i sognet "
        f"({abs(delta):.0f} pct. {direction}, {basis_note})"
    ).replace(",", ".")
    return FactorScore("sqm_price_vs_benchmark", _clamp(score), weight, reason)


def score_neighbourhood(neighbourhood: str, tier: int, source: str) -> FactorScore:
    weight = config.WEIGHTS["neighbourhood"]
    note = "navngivet område" if source == "named_area" else "postnummer"
    return FactorScore(
        "neighbourhood", float(_clamp(tier)), weight, f"{neighbourhood} (via {note})"
    )


def score_water(distance_m: Optional[float], name: str, kind: str) -> FactorScore:
    """Distance to the harbour, the canals, the lakes or the Øresund coast.

    The curve is deliberately steep close in: 150 m from the water and 900 m
    from the water are different products, not a difference of degree.
    """
    weight = config.WEIGHTS["water"]
    if distance_m is None:
        return FactorScore("water", 50.0, weight, "Ingen koordinat", neutral=True)

    if distance_m <= config.WATER_FULL_SCORE_M:
        score = 100.0
    elif distance_m >= config.WATER_ZERO_SCORE_M:
        score = 0.0
    else:
        span = config.WATER_ZERO_SCORE_M - config.WATER_FULL_SCORE_M
        normalised = (distance_m - config.WATER_FULL_SCORE_M) / span
        score = 100.0 * (1.0 - normalised**0.75)

    if kind == "secondary":
        score = min(score, config.SECONDARY_WATER_CAP)

    where = name or ("havn eller kyst" if kind == "prime" else "vandområde")
    return FactorScore(
        "water", _clamp(score), weight, f"{distance_m:.0f} m til {where}"
    )


def score_size(listing: Dict[str, Any]) -> FactorScore:
    weight = config.WEIGHTS["size"]
    area = listing.get("living_area")
    if not area or area <= 0:
        return FactorScore("size", 50.0, weight, "Areal mangler", neutral=True)

    if area <= config.SIZE_FLOOR_M2:
        score = config.SIZE_FLOOR_SCORE
    elif area >= config.SIZE_TOP_M2:
        score = 100.0
    else:
        score = _lerp(
            area,
            config.SIZE_FLOOR_M2,
            config.SIZE_FLOOR_SCORE,
            config.SIZE_TOP_M2,
            100.0,
        )

    rooms = listing.get("number_of_rooms")
    room_note = f", {rooms:.0f} vær." if rooms else ""
    return FactorScore("size", _clamp(score), weight, f"{area:.0f} m2{room_note}")


def score_condition(listing: Dict[str, Any]) -> FactorScore:
    """Energy label, effective age and BBR fixture flags.

    Energy label is the one that costs real money later: a G label on a
    1900 ejendom means the ejerforening has a bill coming.
    """
    weight = config.WEIGHTS["condition"]
    parts: List[float] = []
    part_weights: List[float] = []
    notes: List[str] = []

    label = (listing.get("energy_label") or "").strip().lower()
    if label in config.ENERGY_SCORES:
        parts.append(config.ENERGY_SCORES[label])
        part_weights.append(0.40)
        notes.append(f"energimærke {label.upper()}")

    built = listing.get("year_built")
    renovated = listing.get("year_renovated")
    effective = max([y for y in (built, renovated) if y] or [0])
    if effective:
        if effective >= 2015:
            age_score = 100.0
        elif effective <= 1900:
            age_score = 30.0
        else:
            age_score = _lerp(effective, 1900, 30.0, 2015, 100.0)
        parts.append(age_score)
        part_weights.append(0.45)
        if renovated and renovated > (built or 0):
            notes.append(f"opført {built}, renoveret {renovated}")
        else:
            notes.append(f"opført {built}")

    kitchen = (listing.get("kitchen_condition") or "").lower()
    bathroom = (listing.get("bathroom_condition") or "").lower()
    if kitchen or bathroom:
        fixture = 100.0
        if "uden" in kitchen or "adgang til" in kitchen:
            fixture -= 50.0
            notes.append("intet eget køkken i BBR")
        if "uden" in bathroom or "adgang til" in bathroom:
            fixture -= 50.0
            notes.append("intet eget bad i BBR")
        parts.append(_clamp(fixture))
        part_weights.append(0.15)

    if not parts:
        return FactorScore("condition", 50.0, weight, "Ingen stand-data", neutral=True)

    total_weight = sum(part_weights)
    score = sum(p * w for p, w in zip(parts, part_weights)) / total_weight
    return FactorScore("condition", _clamp(score), weight, ", ".join(notes))


def score_negotiation(listing: Dict[str, Any], market: MarketContext) -> FactorScore:
    """How much room there is to bid under asking.

    Deliberately rewards weak demand. A flat with 300 views after four months
    is a flat whose seller is running out of patience, which is a different
    and more useful thing than a flat that is objectively good.
    """
    weight = config.WEIGHTS["negotiation_leverage"]
    parts: List[float] = []
    part_weights: List[float] = []
    notes: List[str] = []

    days = listing.get("days_listed")
    if days is not None:
        if days <= 14:
            days_score = 0.0
        elif days >= 180:
            days_score = 100.0
        else:
            days_score = _lerp(days, 14, 0.0, 180, 100.0)
        parts.append(days_score)
        part_weights.append(0.40)
        relative = days / market.median_days_listed if market.median_days_listed else 1
        notes.append(f"{days} dage til salg ({relative:.1f}x medianen)")

    drop = listing.get("price_change_pct")
    if drop is not None:
        if drop >= 0:
            drop_score = 0.0
        elif drop <= -10:
            drop_score = 100.0
        else:
            drop_score = _lerp(drop, 0.0, 0.0, -10.0, 100.0)
        parts.append(drop_score)
        part_weights.append(0.35)
        if drop < 0:
            notes.append(f"prisen sat ned {abs(drop):.1f} pct.")

    favourites = listing.get("favourites")
    if favourites is not None and days and days > 7:
        per_week = favourites / (days / 7.0)
        baseline = market.median_favourites_per_week or 1.0
        ratio = per_week / baseline
        # Weak interest means leverage, so the score runs inverse to demand.
        if ratio <= 0.3:
            demand_score = 100.0
        elif ratio >= 2.0:
            demand_score = 0.0
        else:
            demand_score = _lerp(ratio, 0.3, 100.0, 2.0, 0.0)
        parts.append(demand_score)
        part_weights.append(0.25)
        notes.append(f"{favourites} favoritter ({ratio:.1f}x normal interesse)")

    if not parts:
        return FactorScore(
            "negotiation_leverage",
            50.0,
            weight,
            "Ingen markedsdata endnu",
            neutral=True,
        )

    score = sum(p * w for p, w in zip(parts, part_weights)) / sum(part_weights)
    return FactorScore(
        "negotiation_leverage",
        _clamp(score),
        weight,
        "; ".join(notes) or "Nyligt udbudt",
    )


def score_expense(listing: Dict[str, Any], market: MarketContext) -> FactorScore:
    """Monthly ejerudgift per m2 against the pool median.

    A flat 8 pct. under benchmark on m2 price with an ejerudgift 60 pct. above
    the median is not cheap. This factor is what stops that flat ranking.
    """
    weight = config.WEIGHTS["monthly_expense"]
    area = listing.get("living_area")
    cost = listing.get("monthly_expense")

    if not area or not cost or area <= 0:
        return FactorScore(
            "monthly_expense", 50.0, weight, "Ejerudgift ikke oplyst", neutral=True
        )

    per_sqm = cost / area
    baseline = market.median_expense_per_sqm or per_sqm
    ratio = per_sqm / baseline

    if ratio <= 0.70:
        score = 100.0
    elif ratio <= 1.00:
        score = _lerp(ratio, 0.70, 100.0, 1.00, 60.0)
    elif ratio >= 1.50:
        score = 0.0
    else:
        score = _lerp(ratio, 1.00, 60.0, 1.50, 0.0)

    reason = (
        f"{cost:,.0f} kr/md, {per_sqm:.0f} kr/m2/md ({ratio:.2f}x medianen)"
    ).replace(",", ".")
    return FactorScore("monthly_expense", _clamp(score), weight, reason)


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


@dataclass
class ScoreResult:
    total: float
    bonus: float
    factors: List[FactorScore] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "total": round(self.total, 1),
            "bonus": round(self.bonus, 1),
            "breakdown": [
                {
                    "key": f.key,
                    "label": f.label,
                    "score": round(f.score, 1),
                    "weight": f.weight,
                    "contribution": round(f.contribution, 2),
                    "reason": f.reason,
                    "neutral": f.neutral,
                }
                for f in self.factors
            ],
        }
        payload.update(self.meta)
        return payload

    @property
    def headline(self) -> str:
        """The two factors that moved this listing furthest from average."""
        ranked = sorted(
            self.factors, key=lambda f: (f.score - 50) * f.weight, reverse=True
        )
        best = ranked[0] if ranked else None
        worst = ranked[-1] if len(ranked) > 1 else None
        bits = []
        if best and best.score > 55:
            bits.append(f"Stærk på {best.label.lower()}: {best.reason}")
        if worst and worst.score < 45:
            bits.append(f"Svag på {worst.label.lower()}: {worst.reason}")
        return ". ".join(bits) or "Gennemsnitlig på tværs af faktorerne"


def score_listing(
    listing: Dict[str, Any],
    benchmark: Optional[int],
    basis: str,
    neighbourhood: str,
    tier: int,
    neighbourhood_source: str,
    water_distance: Optional[float],
    water_name: str,
    water_kind: str,
    market: MarketContext,
    weights: Optional[Dict[str, float]] = None,
) -> ScoreResult:
    """Run every factor and assemble the weighted total.

    ``weights`` overrides the configured profile. The individual factor scores
    do not depend on it, which is what lets the web app re-rank the whole pool
    under a different profile without recomputing anything.
    """
    factors = [
        score_sqm_price(listing, benchmark, basis),
        score_neighbourhood(neighbourhood, tier, neighbourhood_source),
        score_water(water_distance, water_name, water_kind),
        score_size(listing),
        score_condition(listing),
        score_negotiation(listing, market),
        score_expense(listing, market),
    ]

    if weights:
        for factor in factors:
            factor.weight = weights.get(factor.key, factor.weight)

    weighted = sum(f.contribution for f in factors)

    bonus = 0.0
    bonus_notes: List[str] = []
    # The API flag under-reports balconies, so both the description text and,
    # once it exists, the model's own reading of the listing can override it.
    # See the note at the top of parse.py. balcony_ai is authoritative in both
    # directions when present, because it is the only source that has looked at
    # the text and the photo descriptions together.
    ai_says = listing.get("balcony_ai")
    if ai_says is not None:
        has_balcony = bool(ai_says)
        note = "altan (bekræftet af vurderingen)" if has_balcony else ""
    else:
        has_balcony = bool(
            listing.get("has_balcony") or listing.get("has_balcony_text")
        )
        note = "altan" if listing.get("has_balcony") else "altan (nævnt i teksten)"

    if has_balcony:
        bonus += config.BONUS_BALCONY
        bonus_notes.append(note)
    if listing.get("has_terrace"):
        bonus += config.BONUS_TERRACE
        bonus_notes.append("terrasse")
    if listing.get("has_elevator"):
        bonus += config.BONUS_ELEVATOR
        bonus_notes.append("elevator")
    bonus = min(bonus, config.BONUS_CAP)

    total = _clamp(weighted + bonus)

    area = listing.get("living_area") or 0
    price = listing.get("price") or 0
    ratio = (price / area / benchmark) if (area and price and benchmark) else None

    meta = {
        "neighbourhood": neighbourhood,
        "neighbourhood_tier": tier,
        "parish_sqm_price": benchmark,
        "benchmark_basis": basis,
        "sqm_price_ratio": round(ratio, 4) if ratio else None,
        "water_distance_m": round(water_distance, 1)
        if water_distance is not None
        else None,
        "water_name": water_name,
        "water_kind": water_kind,
        "bonus_notes": bonus_notes,
    }
    return ScoreResult(total=total, bonus=bonus, factors=factors, meta=meta)
