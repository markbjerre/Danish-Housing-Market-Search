"""Web interface.

Runs on its own port and its own SQLite file, separate from the villa Flask
app in webapp/. Read only against the database: everything that writes lives
in the pipeline.

    python -m kbh.webapp.app
    http://127.0.0.1:5001
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

from flask import Flask, abort, jsonify, render_template, request

from .. import ai, config, db, taste

app = Flask(__name__)


# --------------------------------------------------------------------------
# Who is looking
#
# There is no login screen and there should not be one. Traefik does HTTP
# basic auth in front of the app and, by default, passes the Authorization
# header through to the backend, so the username it already validated is the
# identity. One password each, no user table, no session handling.
#
# Locally there is no proxy and no header, so it falls back to the configured
# default rater. That keeps `python -m kbh.webapp.app` working exactly as
# before for a single user.
#
# This is authentication for *identity*, not for security: the app trusts the
# username because Traefik refuses to forward the request without a valid
# password. Exposing the app directly, with no proxy, would let anyone claim
# any name. Do not do that.
# --------------------------------------------------------------------------


def current_rater() -> str:
    auth = request.authorization
    if auth and auth.username:
        return auth.username.strip().lower()
    return config.DEFAULT_RATER


def rater_label(name: str) -> str:
    return config.RATER_NAMES.get(name, name.capitalize())


@app.context_processor
def inject_rater() -> Dict[str, Any]:
    who = current_rater()
    return {"rater": who, "rater_label": rater_label(who)}


# --------------------------------------------------------------------------
# Presentation helpers, exposed to Jinja
# --------------------------------------------------------------------------


@app.template_filter("kr")
def fmt_kr(value: Optional[float]) -> str:
    if value is None:
        return "?"
    return f"{value:,.0f}".replace(",", ".")


@app.template_filter("pct")
def fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "?"
    return f"{value:+.0f}%"


def reweight(row: Dict[str, Any], weights: Dict[str, float]) -> Dict[str, Any]:
    """Recompute a listing's total under a different weighting.

    This is the whole trick behind the profile switcher: every factor's 0 to 100
    score is already stored, so a new profile is arithmetic on numbers we have.
    No API call, no model, nothing re-read. The AI verdict describes the flat and
    is unaffected by how the flat is weighted.
    """
    breakdown = row.get("breakdown") or []
    if not breakdown:
        return row

    total = 0.0
    for factor in breakdown:
        weight = weights.get(factor["key"], 0.0)
        factor["weight"] = weight
        factor["contribution"] = round(factor["score"] * weight / 100.0, 2)
        total += factor["contribution"]

    row["breakdown"] = sorted(breakdown, key=lambda f: -f["weight"])
    row["score"] = max(0.0, min(100.0, total + (row.get("bonus") or 0.0)))
    return row


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    data = dict(row)
    data["breakdown"] = json.loads(data["breakdown"]) if data.get("breakdown") else []
    data["verdict"] = json.loads(data["ai_verdict"]) if data.get("ai_verdict") else None
    data["images"] = json.loads(data["image_urls"]) if data.get("image_urls") else []
    ratio = data.get("sqm_price_ratio")
    data["vs_benchmark_pct"] = (ratio - 1) * 100 if ratio else None

    area, cost = data.get("living_area"), data.get("monthly_expense")
    data["expense_per_sqm"] = (cost / area) if (area and cost) else None
    return data


# Ejerudgift carries only 5 pct. of the score, so a flat with an outlying
# monthly cost can still rank well on everything else. Flagging it in the UI is
# what stops that slipping past. The threshold is a multiple of the pool median
# rather than a fixed kr/m2 figure, so it does not quietly stop meaning anything
# as the market moves.
EXPENSE_WARNING_MULTIPLE = 1.7


def flag_expense_outliers(rows: List[Dict[str, Any]]) -> None:
    values = sorted(r["expense_per_sqm"] for r in rows if r.get("expense_per_sqm"))
    if len(values) < 10:
        return
    median = values[len(values) // 2]
    threshold = median * EXPENSE_WARNING_MULTIPLE
    for row in rows:
        per_sqm = row.get("expense_per_sqm")
        row["expense_is_outlier"] = bool(per_sqm and per_sqm > threshold)
        row["expense_median"] = median


FILTERS = {
    "min_score": ("Min. score", 0),
    "max_price": ("Maks. pris", config.PRICE_MAX),
    "min_area": ("Min. m²", config.MIN_LIVING_AREA),
    "max_water": ("Maks. m til vand", 5000),
}


def apply_filters(rows: List[Dict[str, Any]], args: Any) -> List[Dict[str, Any]]:
    def num(key: str, default: float) -> float:
        try:
            return float(args.get(key, default))
        except (TypeError, ValueError):
            return default

    min_score = num("min_score", 0)
    max_price = num("max_price", config.PRICE_MAX)
    min_area = num("min_area", 0)
    max_water = num("max_water", 10**9)
    hood = args.get("hood") or ""
    verdict = args.get("verdict") or ""
    only_balcony = args.get("balcony") == "1"
    only_drops = args.get("drops") == "1"

    out = []
    for row in rows:
        if (row.get("score") or 0) < min_score:
            continue
        if (row.get("price") or 0) > max_price:
            continue
        if (row.get("living_area") or 0) < min_area:
            continue
        water = row.get("water_distance_m")
        if water is not None and water > max_water:
            continue
        if hood and row.get("neighbourhood") != hood:
            continue
        if only_balcony:
            # The model's reading wins where it exists, in both directions.
            confirmed = row.get("balcony_ai")
            has = (
                bool(confirmed)
                if confirmed is not None
                else bool(row.get("has_balcony") or row.get("has_balcony_text"))
            )
            if not has:
                continue
        if only_drops and not ((row.get("price_change_pct") or 0) < 0):
            continue
        if verdict:
            current = (row.get("verdict") or {}).get("verdict")
            if current != verdict:
                continue
        out.append(row)
    return out


SORTS = {
    "score": ("Score", lambda r: -(r.get("score") or 0)),
    "value": ("Bedste pris mod benchmark", lambda r: r.get("sqm_price_ratio") or 9),
    "price": ("Laveste pris", lambda r: r.get("price") or 10**9),
    "sqm": ("Flest m²", lambda r: -(r.get("living_area") or 0)),
    "water": (
        "Tættest på vand",
        lambda r: (
            r.get("water_distance_m")
            if r.get("water_distance_m") is not None
            else 10**9
        ),
    ),
    "new": (
        "Nyest udbudt",
        lambda r: r.get("days_listed") if r.get("days_listed") is not None else 10**9,
    ),
    "stale": ("Længst til salg", lambda r: -(r.get("days_listed") or 0)),
    "expense": (
        "Laveste ejerudgift pr. m²",
        lambda r: r.get("expense_per_sqm") or 10**9,
    ),
}


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


@app.route("/")
def index():
    with db.session() as conn:
        # A profile can be previewed with ?profil=..., which does not save it.
        profile_key, weights = db.active_weights(conn)
        preview = request.args.get("profil")
        if preview and preview in config.PROFILES:
            profile_key, weights = preview, dict(config.PROFILES[preview]["weights"])
        rows = [
            reweight(row_to_dict(r), weights)
            for r in db.active_listings(conn, rater=current_rater())
        ]
        stats = summary_stats(conn)
    flag_expense_outliers(rows)

    hoods = sorted({r["neighbourhood"] for r in rows if r.get("neighbourhood")})
    filtered = apply_filters(rows, request.args)
    sort_key = request.args.get("sort", "score")
    filtered.sort(key=SORTS.get(sort_key, SORTS["score"])[1])

    return render_template(
        "index.html",
        rows=filtered,
        total=len(rows),
        hoods=hoods,
        sorts=SORTS,
        sort_key=sort_key,
        stats=stats,
        args=request.args,
        weights=weights,
        labels=config.FACTOR_LABELS,
        profiles=config.PROFILES,
        profile_key=profile_key,
        factor_keys=config.FACTOR_KEYS,
    )


@app.route("/api/profile", methods=["POST"])
def api_profile():
    """Switch the weighting. Instant: no listing is re-read or re-evaluated."""
    payload = request.get_json(silent=True) or request.form
    key = (payload.get("profile") or "").strip()

    with db.session() as conn:
        if key == "custom":
            raw = payload.get("weights") or {}
            weights = config.normalise_weights(
                {k: float(raw.get(k, 0) or 0) for k in config.FACTOR_KEYS}
            )
            db.set_pref(conn, "custom_weights", weights)
            db.set_pref(conn, "profile", "custom")
        elif key in config.PROFILES:
            db.set_pref(conn, "profile", key)
        else:
            return jsonify({"error": "ukendt profil"}), 400
        active_key, active = db.active_weights(conn)

    return jsonify({"ok": True, "profile": active_key, "weights": active})


@app.route("/bolig/<case_id>")
def detail(case_id: str):
    with db.session() as conn:
        row = db.listing(conn, case_id, rater=current_rater())
        if row is None:
            abort(404)
        _, weights = db.active_weights(conn)
        data = reweight(row_to_dict(row), weights)
        data["price_events"] = [dict(r) for r in db.price_events(conn, case_id)]
        data["sale_history"] = [
            dict(r) for r in db.sale_history(conn, data.get("address_id") or "")
        ]
    return render_template("detail.html", row=data, labels=config.FACTOR_LABELS)


@app.route("/udelukkede")
def excluded():
    """Everything the hard filters removed, and why. Nothing disappears
    silently: if the filters are wrong, this page is how you find out."""
    with db.session() as conn:
        detail_rows = conn.execute(
            "SELECT address, price, living_area, floor, zip_code, exclusion_reason, "
            "boligsiden_url FROM listings WHERE is_active = 1 AND excluded = 1 "
            "ORDER BY exclusion_reason, price"
        ).fetchall()
        reasons = conn.execute(
            "SELECT exclusion_reason, COUNT(*) c FROM listings "
            "WHERE is_active = 1 AND excluded = 1 GROUP BY 1 ORDER BY c DESC"
        ).fetchall()
    grouped: Dict[str, int] = {}
    for r in reasons:
        key = (
            "Under 90 m²"
            if "under grænsen" in (r["exclusion_reason"] or "")
            else (
                "Stue eller kælder"
                if "Stue" in (r["exclusion_reason"] or "")
                else (r["exclusion_reason"] or "Andet")
            )
        )
        grouped[key] = grouped.get(key, 0) + r["c"]
    return render_template(
        "excluded.html", rows=[dict(r) for r in detail_rows], grouped=grouped
    )


@app.route("/api/rate", methods=["POST"])
def api_rate():
    """Save a star rating and an optional comment. Zero stars clears it."""
    payload = request.get_json(silent=True) or request.form
    case_id = (payload.get("case_id") or "").strip()
    if not case_id:
        return jsonify({"error": "case_id mangler"}), 400
    try:
        stars = int(payload.get("stars", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "stars skal være et tal"}), 400
    if stars < 0 or stars > 5:
        return jsonify({"error": "stars skal være mellem 0 og 5"}), 400

    note = (payload.get("note") or "").strip()[:2000]

    with db.session() as conn:
        if (
            conn.execute(
                "SELECT 1 FROM listings WHERE case_id = ?", (case_id,)
            ).fetchone()
            is None
        ):
            return jsonify({"error": "ukendt bolig"}), 404
        db.save_rating(conn, case_id, stars, note, rater=current_rater())
        counts = db.rating_counts(conn, rater=current_rater())
    return jsonify(
        {"ok": True, "case_id": case_id, "stars": stars, "note": note, "counts": counts}
    )


@app.route("/bedoem")
def rate_view():
    """One listing at a time, stars and a comment, keyboard driven.

    The point is volume: the taste analysis needs tens of judgements, and
    nobody produces those from a page that requires a round trip per rating.
    """
    with db.session() as conn:
        _, weights = db.active_weights(conn)
        pending = [
            reweight(row_to_dict(r), weights)
            for r in db.unrated_listings(conn, limit=300, rater=current_rater())
        ]
        pending.sort(key=lambda r: -(r.get("score") or 0))
        counts = db.rating_counts(conn, rater=current_rater())
        recent = [
            row_to_dict(r) for r in db.rated_listings(conn, rater=current_rater())
        ][:12]
    flag_expense_outliers(pending)
    return render_template("rate.html", queue=pending, counts=counts, recent=recent)


@app.route("/moenstre")
def patterns():
    """What the ratings say about what he actually likes."""
    refresh = request.args.get("ai") == "1"
    # ?rater=x reads someone else's patterns without pretending to be them.
    # Useful for comparing two people; it changes nothing and writes nothing.
    who = request.args.get("rater") or current_rater()
    with db.session() as conn:
        report = taste.analyse(conn, rater=who)
        _, active_weights = db.active_weights(conn)
        rated = [
            reweight(row_to_dict(r), active_weights)
            for r in db.rated_listings(conn, rater=who)
        ]
        everyone = db.raters(conn)

    if refresh and report.comments:
        try:
            report.ai_summary = ai.taste_summary(report.comments, report.findings)
        except Exception as exc:
            report.notes.append(f"AI-opsummeringen fejlede: {exc}")

    return render_template(
        "patterns.html",
        report=report,
        rated=rated,
        viewing=who,
        viewing_label=rater_label(who),
        everyone=everyone,
        weights=config.WEIGHTS,
        labels=config.FACTOR_LABELS,
    )


@app.route("/uenighed")
def disagreements():
    """Where two people scored the same home differently.

    The point of keeping ratings per person rather than averaging them. Two
    buyers agreeing needs no discussion; a two star gap is the conversation to
    have before spending a Saturday on a viewing.
    """
    try:
        min_gap = max(1, min(4, int(request.args.get("gap", 2))))
    except (TypeError, ValueError):
        min_gap = 2

    with db.session() as conn:
        rows = [dict(r) for r in db.disagreements(conn, min_gap=min_gap)]
        everyone = db.raters(conn)

    return render_template(
        "disagreements.html",
        rows=rows,
        everyone=everyone,
        min_gap=min_gap,
    )


@app.route("/api/listings")
def api_listings():
    with db.session() as conn:
        _, weights = db.active_weights(conn)
        rows = [
            reweight(row_to_dict(r), weights)
            for r in db.active_listings(conn, rater=current_rater())
        ]
    return jsonify(apply_filters(rows, request.args))


@app.route("/api/map")
def api_map():
    """Minimal payload for the map: one point per listing."""
    with db.session() as conn:
        _, weights = db.active_weights(conn)
        rows = [
            reweight(row_to_dict(r), weights)
            for r in db.active_listings(conn, rater=current_rater())
        ]
    rows = apply_filters(rows, request.args)
    return jsonify(
        [
            {
                "id": r["case_id"],
                "lat": r["lat"],
                "lon": r["lon"],
                "score": r.get("score"),
                "address": r.get("address"),
                "price": r.get("price"),
                "area": r.get("living_area"),
                "hood": r.get("neighbourhood"),
            }
            for r in rows
            if r.get("lat") and r.get("lon")
        ]
    )


def summary_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    active = conn.execute(
        "SELECT COUNT(*) c FROM listings WHERE is_active = 1 AND excluded = 0"
    ).fetchone()["c"]
    filtered = conn.execute(
        "SELECT COUNT(*) c FROM listings WHERE is_active = 1 AND excluded = 1"
    ).fetchone()["c"]
    verdicts = conn.execute("SELECT COUNT(*) c FROM ai_verdicts").fetchone()["c"]
    last_run = conn.execute(
        "SELECT started_at, new_listings, price_drops, delisted FROM runs "
        "WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    recommended = conn.execute(
        "SELECT COUNT(*) c FROM ai_verdicts WHERE verdict LIKE '%\"se den\"%'"
    ).fetchone()["c"]
    return {
        "active": active,
        "filtered": filtered,
        "verdicts": verdicts,
        "recommended": recommended,
        "last_run": dict(last_run) if last_run else None,
    }


def main() -> None:
    port = int(os.environ.get("KBH_WEB_PORT", 5001))
    app.run(
        host=os.environ.get("KBH_WEB_HOST", "127.0.0.1"),
        port=port,
        debug=os.environ.get("KBH_DEBUG") == "1",
    )


if __name__ == "__main__":
    main()
