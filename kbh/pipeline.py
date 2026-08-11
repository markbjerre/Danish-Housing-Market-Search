"""The run.

    fetch -> filter -> benchmark -> score -> AI verdict -> notify

One pass takes a couple of minutes for the full pool. Everything is
idempotent: running it twice in a row changes nothing except last_seen.

    python -m kbh.pipeline run              full pass, alerts on
    python -m kbh.pipeline run --no-alerts  full pass, silent
    python -m kbh.pipeline run --no-ai      numbers only
    python -m kbh.pipeline digest           send the morning digest
    python -m kbh.pipeline rescore          rescore without refetching
    python -m kbh.pipeline top -n 15        print the leaderboard
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import ai, benchmarks, config, db, geo, notify, parse, scoring
from .boligsiden import BoligsidenClient

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Fetch
# --------------------------------------------------------------------------


def fetch_all(
    client: BoligsidenClient,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Every active listing across every configured scope.

    Returns the parsed rows and the raw cases keyed by case id, because the
    raw payload carries the image list the AI step needs.
    """
    rows: List[Dict[str, Any]] = []
    raw: Dict[str, Dict[str, Any]] = {}
    seen: set[str] = set()

    for scope in config.SEARCH_SCOPES:
        count = 0
        for case in client.iter_cases(
            municipality=scope.municipality,
            address_type=scope.address_type,
            price_min=config.PRICE_MIN,
            price_max=config.PRICE_MAX,
        ):
            case_id = case.get("caseID")
            if not case_id or case_id in seen:
                continue
            seen.add(case_id)
            raw[case_id] = case
            rows.append(parse.case_to_row(case))
            count += 1
        logger.info("%s: %s listings", scope.label, count)

    return rows, raw


# --------------------------------------------------------------------------
# Score
# --------------------------------------------------------------------------


def load_geometry(
    errors: Optional[List[str]] = None,
) -> Tuple[
    Optional[geo.WaterIndex], Optional[geo.TransitIndex], Optional[geo.NoiseIndex]
]:
    """Build the three geometry indexes, tolerating each one failing alone.

    A dead Overpass mirror must not take the whole run down, and it must not
    silently take a factor to zero either: a missing index makes its factor
    score an explicit neutral and says so in the log.
    """
    loaders = (
        ("water", geo.fetch_water, geo.WaterIndex),
        ("transit", geo.fetch_transit, geo.TransitIndex),
        ("noise", geo.fetch_noise, geo.NoiseIndex),
    )
    built: List[Any] = []
    for label, fetch, index_class in loaders:
        try:
            built.append(index_class(fetch()))
        except Exception as exc:
            if errors is not None:
                errors.append(f"{label} geometry unavailable: {exc}")
            logger.error(
                "%s geometry unavailable, that factor goes neutral: %s", label, exc
            )
            built.append(None)
    return built[0], built[1], built[2]


def score_all(
    conn: sqlite3.Connection,
    rows: Sequence[Dict[str, Any]],
    bench: benchmarks.BenchmarkSet,
    water: Optional[geo.WaterIndex],
    transit: Optional[geo.TransitIndex] = None,
    noise: Optional[geo.NoiseIndex] = None,
) -> Dict[str, Dict[str, Any]]:
    """Score every listing that survived the hard filters."""
    candidates = [r for r in rows if not r.get("excluded")]

    # Demand numbers feed the negotiation factor, so they must be attached
    # before the market context is computed.
    demand = {
        row["case_id"]: row
        for row in conn.execute(
            "SELECT case_id, page_views, clicks, favourites FROM ("
            "  SELECT *, ROW_NUMBER() OVER (PARTITION BY case_id ORDER BY captured_at DESC) rn"
            "  FROM demand) WHERE rn = 1"
        ).fetchall()
    }
    for row in candidates:
        stats = demand.get(row["case_id"])
        if stats:
            row["page_views"] = stats["page_views"]
            row["clicks"] = stats["clicks"]
            row["favourites"] = stats["favourites"]

    # The peer benchmark is derived from the pool itself, so it has to be
    # rebuilt on every run rather than cached.
    bench.attach_peers(candidates)

    # Score with whatever profile is active in the UI, so the leaderboard, the
    # Telegram alerts and the digest cannot disagree with each other.
    profile_key, weights = db.active_weights(conn)
    logger.info(
        "Scoring with the %s profile: %s",
        profile_key,
        ", ".join(f"{config.FACTOR_LABELS[k]} {v:.0f}" for k, v in weights.items()),
    )

    market = scoring.MarketContext.from_listings(candidates)
    logger.info(
        "Market context: median %s dage til salg, %.0f kr/m2/md ejerudgift, "
        "%.1f favoritter pr. uge",
        market.median_days_listed,
        market.median_expense_per_sqm,
        market.median_favourites_per_week,
    )

    results: Dict[str, Dict[str, Any]] = {}
    for row in candidates:
        bench_hit = bench.lookup(row)
        hood = geo.resolve_neighbourhood(
            row.get("zip_code"), row.get("lat"), row.get("lon")
        )

        has_point = bool(row.get("lat") and row.get("lon"))

        water_hit = None
        if water is not None and water.ready and has_point:
            water_hit = water.nearest(row["lat"], row["lon"])

        transit_hit = None
        if transit is not None and transit.ready and has_point:
            transit_hit = transit.nearest(row["lat"], row["lon"])

        # None and [] mean different things here. None says the geometry was
        # not available and the factor scores a neutral; [] says it was checked
        # and the address is quiet.
        noise_hits = None
        if noise is not None and noise.ready and has_point:
            noise_hits = noise.nearby(row["lat"], row["lon"])

        result = scoring.score_listing(
            listing=row,
            benchmark=bench_hit.sqm_price,
            basis=bench_hit.basis,
            neighbourhood=hood.name,
            tier=hood.tier,
            neighbourhood_source=hood.source,
            water_distance=water_hit.distance_m if water_hit else None,
            water_name=water_hit.name if water_hit else "",
            water_kind=water_hit.kind if water_hit else "",
            market=market,
            weights=weights,
            transit_distance=transit_hit.distance_m if transit_hit else None,
            transit_name=transit_hit.name if transit_hit else "",
            transit_kind=transit_hit.kind if transit_hit else "",
            noise_hits=noise_hits,
        )

        payload = result.as_dict()
        payload["parish"] = bench.parish_name(row)
        payload["benchmark_source"] = bench_hit.source_name
        payload["headline"] = result.headline
        db.save_score(conn, row["case_id"], payload)
        results[row["case_id"]] = payload

    # Drop scores for listings that have since been excluded or delisted.
    # Without this, tightening a filter leaves the old score behind and every
    # count that joins on the scores table quietly disagrees with reality.
    stale = conn.execute(
        "DELETE FROM scores WHERE case_id IN ("
        "  SELECT s.case_id FROM scores s JOIN listings l ON l.case_id = s.case_id"
        "  WHERE l.excluded = 1 OR l.is_active = 0)"
    ).rowcount
    if stale:
        logger.info(
            "Removed %s scores for listings that are no longer candidates", stale
        )

    conn.commit()
    return results


# --------------------------------------------------------------------------
# AI
# --------------------------------------------------------------------------


def _stripe(items: Sequence[str], size: int) -> List[List[str]]:
    """Deal a score-sorted list round robin into batches instead of slicing it.

    Slicing puts adjacent scores together, and adjacent scores are very often
    two flats in the same building: Flyndervej 3B and 3C landed in one batch and
    the model duly wrote "samme projekt som 3C" and "mindste af alle udbudte".
    Dealing the cards instead means a batch holds six unrelated flats from
    different neighbourhoods, which leaves far less to cross-reference.
    """
    if size <= 1:
        return [[item] for item in items]
    count = (len(items) + size - 1) // size
    batches: List[List[str]] = [[] for _ in range(count)]
    for index, item in enumerate(items):
        batches[index % count].append(item)
    return [b for b in batches if b]


def _needs_verdict(
    conn: sqlite3.Connection, case_id: str, price: Optional[int]
) -> bool:
    """Re-run the model when a listing is new or when its price has moved.

    A verdict written against a 9.2m asking price is stale advice once the
    seller drops to 8.4m, and the price assessment is the part Mark reads.
    """
    row = conn.execute(
        "SELECT price_seen FROM ai_verdicts WHERE case_id = ?", (case_id,)
    ).fetchone()
    if row is None:
        return True
    return row["price_seen"] != price


def run_ai(
    conn: sqlite3.Connection,
    rows: Sequence[Dict[str, Any]],
    scores: Dict[str, Dict[str, Any]],
    raw: Dict[str, Dict[str, Any]],
    limit: Optional[int] = None,
    workers: Optional[int] = None,
    min_score: Optional[float] = None,
) -> int:
    """Ask Claude about everything new or repriced, best scoring first."""
    workers = workers or config.AI_WORKERS
    if not config.RuntimeConfig().ai_ready:
        logger.warning("AI skipped: claude CLI not found on PATH (or KBH_AI_ENABLED=0)")
        return 0

    by_id = {r["case_id"]: r for r in rows}
    gate = config.AI_MIN_SCORE if min_score is None else min_score

    eligible = [cid for cid in scores if scores[cid]["total"] >= gate]
    pending = [
        case_id
        for case_id in eligible
        if _needs_verdict(conn, case_id, by_id.get(case_id, {}).get("price"))
    ]
    pending.sort(key=lambda cid: scores[cid]["total"], reverse=True)

    skipped_by_gate = len(scores) - len(eligible)
    truncated = 0
    if limit and len(pending) > limit:
        truncated = len(pending) - limit
        pending = pending[:limit]

    # Say out loud what was left unread. A quiet cap looks identical to full
    # coverage from the outside.
    if skipped_by_gate:
        logger.info(
            "%s listings below the score gate of %s, no verdict requested",
            skipped_by_gate,
            gate,
        )
    if truncated:
        logger.info("%s eligible listings left unread because of --ai-limit", truncated)

    if not pending:
        logger.info("No listings need an AI verdict")
        return 0
    logger.info("Asking Claude about %s listings", len(pending))

    history_cache = {
        case_id: [
            dict(r)
            for r in db.sale_history(conn, by_id[case_id].get("address_id") or "")
        ]
        for case_id in pending
    }

    def candidate(case_id: str) -> ai.Candidate:
        score = scores[case_id]
        images = parse.image_context(raw.get(case_id, {}))
        return ai.Candidate(
            case_id=case_id,
            listing=dict(by_id[case_id]),
            score=score,
            sale_history=history_cache.get(case_id, []),
            benchmark_source=score.get("benchmark_source", "lokalområdet"),
            photo_alts=images["alt_texts"],
            image_urls=images["urls"],
        )

    # Real vision only applies to a single listing at a time, so asking for
    # photos has to force the batch size to one. Otherwise the setting would be
    # silently ignored, which is worse than it being unavailable.
    batch_size = 1 if config.AI_USE_PHOTOS else max(1, config.AI_BATCH_SIZE)
    if config.AI_USE_PHOTOS:
        logger.info(
            "KBH_AI_USE_PHOTOS is on, so batching is disabled "
            "(images are only sent for single listings)"
        )
    batches = _stripe(pending, batch_size)
    logger.info(
        "%s listings in %s batches of up to %s", len(pending), len(batches), batch_size
    )

    def work(
        ids: Sequence[str],
    ) -> Tuple[Dict[str, ai.Verdict], List[str], Optional[str]]:
        try:
            verdicts = ai.evaluate_batch([candidate(cid) for cid in ids])
        except Exception as exc:
            return {}, list(ids), f"{type(exc).__name__}: {exc}"
        missing = [cid for cid in ids if cid not in verdicts]
        return verdicts, missing, None

    done = 0
    corrections = 0
    unanswered: List[str] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, ids) for ids in batches]
        for future in as_completed(futures):
            verdicts, missing, error = future.result()
            if error:
                logger.error("AI batch failed: %s", error)
            unanswered.extend(missing)
            for case_id, verdict in verdicts.items():
                db.save_verdict(
                    conn,
                    case_id,
                    verdict.model,
                    by_id.get(case_id, {}).get("price"),
                    verdict.payload,
                )
                if db.apply_verdict_corrections(conn, case_id, verdict.payload):
                    corrections += 1
                done += 1
            conn.commit()
            logger.info("  %s/%s verdicts", done, len(pending))

    # A listing the batch dropped gets one more try on its own, where there is
    # no chance of the model losing track of which flat it is describing.
    if unanswered:
        logger.info(
            "Retrying %s listings the batches did not answer for", len(unanswered)
        )
        for case_id in unanswered:
            try:
                verdict = ai.evaluate(candidate(case_id))
            except Exception as exc:
                logger.error("AI failed for %s: %s", case_id, exc)
                continue
            db.save_verdict(
                conn,
                case_id,
                verdict.model,
                by_id.get(case_id, {}).get("price"),
                verdict.payload,
            )
            if db.apply_verdict_corrections(conn, case_id, verdict.payload):
                corrections += 1
            done += 1
        conn.commit()

    if corrections:
        logger.info(
            "%s listings where the model disagreed with the API about the "
            "balcony. Applied on the next scoring pass.",
            corrections,
        )

    conn.commit()
    spend = ai.COST.summary()
    logger.info(
        "AI verdicts written: %s of %s attempted, %s USD (%s per call)",
        done,
        len(pending),
        spend["usd"],
        spend["usd_per_call"],
    )
    return done


# --------------------------------------------------------------------------
# Alerts
# --------------------------------------------------------------------------


def _is_first_run(conn: sqlite3.Connection) -> bool:
    """True when no alert has ever been sent from this database.

    Keyed off the alerts table rather than the runs table, so it stays true
    through however many silent `--no-alerts` runs happen during setup, and
    flips the moment the first real alert goes out.
    """
    row = conn.execute("SELECT 1 FROM alerts LIMIT 1").fetchone()
    return row is None


def send_alerts(
    conn: sqlite3.Connection, events: Dict[str, str], scores: Dict[str, Dict[str, Any]]
) -> int:
    """Instant pings. One per listing per event kind, never repeated."""
    tg = notify.Telegram()
    if not tg.ready:
        logger.warning("Telegram not configured, alerts suppressed")
        return 0

    # On a first run every listing on the market is "new", which would fire
    # fifty pings in a row and teach Mark to mute the bot on day one. The
    # backlog goes out as a single digest instead; instant alerts start from the
    # second run, when "new" means genuinely new.
    if _is_first_run(conn):
        logger.info(
            "First run: %s listings are new by definition, so instant alerts are "
            "suppressed. Sending one digest instead.",
            len(events),
        )
        send_digest(conn)
        for case_id, kind in events.items():
            if case_id in scores:
                db.record_alert(conn, case_id, kind, "suppressed on first run")
        conn.commit()
        return 0

    sent = 0
    ranked = sorted(
        ((cid, kind) for cid, kind in events.items() if cid in scores),
        key=lambda pair: scores[pair[0]]["total"],
        reverse=True,
    )

    for case_id, kind in ranked:
        score = scores[case_id]
        row = db.listing(conn, case_id)
        if row is None:
            continue
        data = dict(row)
        data["score"] = score["total"]
        data.update(
            {
                k: score.get(k)
                for k in (
                    "neighbourhood",
                    "parish",
                    "parish_sqm_price",
                    "sqm_price_ratio",
                    "water_distance_m",
                    "water_name",
                )
            }
        )

        worth_it = score["total"] >= config.ALERT_SCORE_THRESHOLD
        if kind == "price_drop":
            drop = data.get("price_change_pct") or 0
            worth_it = worth_it or abs(drop) >= config.ALERT_PRICE_DROP_PCT
        if not worth_it:
            continue
        if db.already_alerted(conn, case_id, kind):
            continue

        verdict = ai.verdict_from_row(row)
        caption = notify.format_listing(data, verdict, score.get("headline", ""), kind)

        ok = (
            tg.send_photo(data["image_url"], caption)
            if data.get("image_url")
            else tg.send(caption)
        )
        if ok:
            db.record_alert(conn, case_id, kind, f"score={score['total']:.0f}")
            sent += 1

    conn.commit()
    logger.info("Alerts sent: %s", sent)
    return sent


def send_digest(
    conn: sqlite3.Connection,
    changes: Optional[Dict[str, int]] = None,
    use_ai: bool = True,
) -> bool:
    """The morning summary over the whole board."""
    tg = notify.Telegram()
    rows = db.active_listings(conn, limit=config.DIGEST_SIZE)

    items: List[Dict[str, Any]] = []
    for row in rows:
        data = dict(row)
        data["verdict"] = ai.verdict_from_row(row)
        items.append(data)

    if changes is None:
        last = conn.execute(
            "SELECT new_listings, price_drops, delisted FROM runs "
            "WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
        changes = {
            "new": last["new_listings"] if last else 0,
            "price_drops": last["price_drops"] if last else 0,
            "delisted": last["delisted"] if last else 0,
        }
    changes["active"] = conn.execute(
        "SELECT COUNT(*) c FROM listings WHERE is_active = 1 AND excluded = 0"
    ).fetchone()["c"]

    summary = ""
    if use_ai and config.RuntimeConfig().ai_ready and items:
        try:
            summary = ai.daily_summary(items, changes)
        except Exception as exc:
            logger.error("Digest summary failed: %s", exc)

    text = notify.format_digest(items, changes, summary)
    if not tg.ready:
        print(text)
        return False
    return tg.send(text, disable_preview=True)


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def run(
    alerts: bool = True,
    use_ai: bool = True,
    ai_limit: Optional[int] = None,
    ai_min_score: Optional[float] = None,
) -> Dict[str, Any]:
    client = BoligsidenClient()

    with db.session() as conn:
        run_id = db.start_run(conn)
        errors: List[str] = []

        try:
            logger.info("Refreshing local benchmarks")
            bench = benchmarks.refresh(client, conn)

            water, transit, noise = load_geometry(errors)

            logger.info("Fetching listings")
            rows, raw = fetch_all(client)
            logger.info(
                "Fetched %s listings, %s excluded by hard filters",
                len(rows),
                sum(1 for r in rows if r.get("excluded")),
            )

            events: Dict[str, str] = {}
            for row in rows:
                outcome = db.upsert_listing(conn, row)
                if outcome in ("new", "price_drop"):
                    events[row["case_id"]] = outcome
            delisted = db.mark_delisted(conn, [r["case_id"] for r in rows])
            conn.commit()

            candidate_ids = [r["case_id"] for r in rows if not r.get("excluded")]
            logger.info(
                "Fetching demand statistics for %s listings", len(candidate_ids)
            )
            db.save_demand(conn, client.bulk_stats(candidate_ids))
            conn.commit()

            # Sale history for every candidate that does not have it yet.
            # Keying off the "new" event alone would leave a half populated
            # table whenever an earlier run died partway through, which is
            # exactly what happened on the first run of this pipeline.
            have_history = {
                row["address_id"]
                for row in conn.execute(
                    "SELECT DISTINCT address_id FROM sale_history"
                ).fetchall()
            }
            by_id = {r["case_id"]: r for r in rows}
            missing = [
                by_id[cid]["address_id"]
                for cid in candidate_ids
                if by_id[cid].get("address_id")
                and by_id[cid]["address_id"] not in have_history
            ]
            if missing:
                logger.info("Fetching sale history for %s addresses", len(missing))
                for address_id in missing:
                    db.save_sale_history(
                        conn, address_id, client.address_timeline(address_id)
                    )
                conn.commit()

            scores = score_all(conn, rows, bench, water, transit, noise)
            logger.info("Scored %s listings", len(scores))

            verdicts = 0
            if use_ai:
                verdicts = run_ai(
                    conn, rows, scores, raw, limit=ai_limit, min_score=ai_min_score
                )

            sent = send_alerts(conn, events, scores) if alerts else 0

            new_count = sum(1 for k in events.values() if k == "new")
            drop_count = sum(1 for k in events.values() if k == "price_drop")
            db.finish_run(
                conn,
                run_id,
                len(rows),
                new_count,
                drop_count,
                delisted,
                "; ".join(errors),
            )
            conn.commit()

            return {
                "seen": len(rows),
                "scored": len(scores),
                "excluded": sum(1 for r in rows if r.get("excluded")),
                "new": new_count,
                "price_drops": drop_count,
                "delisted": delisted,
                "verdicts": verdicts,
                "alerts": sent,
                "ai_spend": ai.COST.summary(),
                "errors": errors,
            }

        except Exception:
            detail = traceback.format_exc()
            db.finish_run(conn, run_id, 0, 0, 0, 0, detail[:2000])
            conn.commit()
            tg = notify.Telegram()
            if tg.ready:
                tg.send(notify.format_run_error(detail))
            raise


def rescore() -> Dict[str, Any]:
    """Recompute scores from stored listings without touching the search API.

    Benchmarks and water geometry are still fetched, because both are cheap
    and both move.
    """
    client = BoligsidenClient()
    with db.session() as conn:
        bench = benchmarks.refresh(client, conn)
        water, transit, noise = load_geometry()

        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM listings WHERE is_active = 1"
            ).fetchall()
        ]
        scores = score_all(conn, rows, bench, water, transit, noise)
        return {"scored": len(scores)}


def print_top(limit: int = 15) -> None:
    with db.session() as conn:
        rows = db.active_listings(conn, limit=limit)
        if not rows:
            print(
                "Ingen boliger i databasen endnu. Kør 'python -m kbh.pipeline run' først."
            )
            return
        print(
            f"{'#':>3} {'Score':>6} {'Pris':>11} {'m2':>5} {'kr/m2':>8} "
            f"{'vs sogn':>8}  {'Kvarter':<22} Adresse"
        )
        for index, row in enumerate(rows, start=1):
            ratio = row["sqm_price_ratio"]
            delta = f"{(ratio - 1) * 100:+.0f}%" if ratio else "-"
            price = f"{row['price']:,}".replace(",", ".") if row["price"] else "-"
            print(
                f"{index:>3} {row['score'] or 0:>6.1f} {price:>11} "
                f"{row['living_area'] or 0:>5.0f} {row['per_area_price'] or 0:>8,.0f} "
                f"{delta:>8}  {(row['neighbourhood'] or '')[:22]:<22} {row['address']}".replace(
                    ",", "."
                )
            )
            verdict = ai.verdict_from_row(row)
            if verdict:
                print(
                    f"      {verdict.get('verdict', '')}: {verdict.get('one_liner', '')}"
                )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="kbh.pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="full pass")
    run_cmd.add_argument("--no-alerts", action="store_true")
    run_cmd.add_argument("--no-ai", action="store_true")
    run_cmd.add_argument(
        "--ai-limit",
        type=int,
        default=None,
        help="only send the N best scoring listings to the model",
    )
    run_cmd.add_argument(
        "--ai-min-score",
        type=float,
        default=None,
        help=f"score gate for verdicts (default {config.AI_MIN_SCORE})",
    )

    sub.add_parser("rescore", help="recompute scores from stored data")

    digest_cmd = sub.add_parser("digest", help="send the morning digest")
    digest_cmd.add_argument("--no-ai", action="store_true")

    top_cmd = sub.add_parser("top", help="print the leaderboard")
    top_cmd.add_argument("-n", type=int, default=15)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.command == "run":
        result = run(
            alerts=not args.no_alerts,
            use_ai=not args.no_ai,
            ai_limit=args.ai_limit,
            ai_min_score=args.ai_min_score,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "rescore":
        print(json.dumps(rescore(), ensure_ascii=False, indent=2))
    elif args.command == "digest":
        with db.session() as conn:
            send_digest(conn, use_ai=not args.no_ai)
    elif args.command == "top":
        print_top(args.n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
