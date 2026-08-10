"""SQLite store.

The villa pipeline uses PostgreSQL on the homelab. This subsystem deliberately
does not: the candidate pool is under two thousand rows, it needs to run on a
laptop, a VPS and a cron job without a database server in the path, and every
row is disposable because Boligsiden is the source of truth.

Schema is created on demand and migrations are additive only.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    case_id            TEXT PRIMARY KEY,
    address_id         TEXT,
    address            TEXT,
    road_name          TEXT,
    house_number       TEXT,
    floor              TEXT,
    door               TEXT,
    zip_code           INTEGER,
    city_name          TEXT,
    municipality       TEXT,
    municipality_code  INTEGER,
    address_type       TEXT,
    lat                REAL,
    lon                REAL,
    price              INTEGER,
    per_area_price     INTEGER,
    living_area        REAL,
    number_of_rooms    REAL,
    number_of_floors   INTEGER,
    number_of_bathrooms INTEGER,
    year_built         INTEGER,
    year_renovated     INTEGER,
    energy_label       TEXT,
    monthly_expense    INTEGER,
    down_payment       INTEGER,
    net_mortgage       INTEGER,
    is_houseboat       INTEGER,
    has_balcony        INTEGER,
    has_balcony_text   INTEGER,
    balcony_ai         INTEGER,
    has_terrace        INTEGER,
    has_elevator       INTEGER,
    open_house_at      TEXT,
    floor_plan_url     TEXT,
    kitchen_condition  TEXT,
    bathroom_condition TEXT,
    heating            TEXT,
    days_listed        INTEGER,
    price_change_pct   REAL,
    latest_valuation   INTEGER,
    description_title  TEXT,
    description_body   TEXT,
    realtor_name       TEXT,
    case_url           TEXT,
    boligsiden_url     TEXT,
    image_url          TEXT,
    image_urls         TEXT,
    status             TEXT,
    is_active          INTEGER DEFAULT 1,
    excluded           INTEGER DEFAULT 0,
    exclusion_reason   TEXT,
    first_seen         TEXT,
    last_seen          TEXT,
    delisted_at        TEXT
);

CREATE TABLE IF NOT EXISTS price_events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id   TEXT NOT NULL,
    observed  TEXT NOT NULL,
    price     INTEGER NOT NULL,
    source    TEXT NOT NULL,
    UNIQUE (case_id, price, source, observed)
);

CREATE TABLE IF NOT EXISTS sale_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    address_id TEXT NOT NULL,
    sold_at    TEXT,
    price      INTEGER,
    event_type TEXT,
    UNIQUE (address_id, sold_at, price, event_type)
);

CREATE TABLE IF NOT EXISTS demand (
    case_id      TEXT NOT NULL,
    captured_at  TEXT NOT NULL,
    page_views   INTEGER,
    clicks       INTEGER,
    favourites   INTEGER,
    PRIMARY KEY (case_id, captured_at)
);

CREATE TABLE IF NOT EXISTS scores (
    case_id            TEXT PRIMARY KEY,
    scored_at          TEXT,
    total              REAL,
    bonus              REAL,
    breakdown          TEXT,
    neighbourhood      TEXT,
    neighbourhood_tier INTEGER,
    parish             TEXT,
    parish_sqm_price   INTEGER,
    benchmark_basis    TEXT,
    benchmark_source   TEXT,
    headline           TEXT,
    sqm_price_ratio    REAL,
    water_distance_m   REAL,
    water_name         TEXT,
    water_kind         TEXT
);

CREATE TABLE IF NOT EXISTS ai_verdicts (
    case_id     TEXT PRIMARY KEY,
    created_at  TEXT,
    model       TEXT,
    price_seen  INTEGER,
    verdict     TEXT
);

CREATE TABLE IF NOT EXISTS benchmarks (
    kind         TEXT NOT NULL,
    key          TEXT NOT NULL,
    address_type TEXT NOT NULL,
    sqm_price    INTEGER,
    basis        TEXT,
    updated_at   TEXT,
    PRIMARY KEY (kind, key, address_type)
);

CREATE TABLE IF NOT EXISTS preferences (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ratings (
    case_id    TEXT PRIMARY KEY,
    stars      INTEGER NOT NULL,
    note       TEXT,
    rated_at   TEXT NOT NULL,
    -- The score at the moment of rating, kept so a later rescore cannot
    -- rewrite history and make the taste analysis compare against numbers
    -- that did not exist when the judgement was made.
    score_when_rated REAL
);

CREATE TABLE IF NOT EXISTS alerts (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id  TEXT NOT NULL,
    kind     TEXT NOT NULL,
    sent_at  TEXT NOT NULL,
    detail   TEXT
);

CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at   TEXT,
    finished_at  TEXT,
    seen         INTEGER,
    new_listings INTEGER,
    price_drops  INTEGER,
    delisted     INTEGER,
    errors       TEXT
);

CREATE INDEX IF NOT EXISTS idx_listings_active ON listings (is_active, excluded);
CREATE INDEX IF NOT EXISTS idx_listings_zip ON listings (zip_code);
CREATE INDEX IF NOT EXISTS idx_price_events_case ON price_events (case_id, observed);
CREATE INDEX IF NOT EXISTS idx_alerts_case ON alerts (case_id, kind);
CREATE INDEX IF NOT EXISTS idx_demand_case ON demand (case_id, captured_at);
"""

LISTING_COLUMNS: List[str] = [
    "case_id",
    "address_id",
    "address",
    "road_name",
    "house_number",
    "floor",
    "door",
    "zip_code",
    "city_name",
    "municipality",
    "municipality_code",
    "address_type",
    "lat",
    "lon",
    "price",
    "per_area_price",
    "living_area",
    "number_of_rooms",
    "number_of_floors",
    "number_of_bathrooms",
    "year_built",
    "year_renovated",
    "energy_label",
    "monthly_expense",
    "down_payment",
    "net_mortgage",
    "is_houseboat",
    "has_balcony",
    "has_balcony_text",
    "has_terrace",
    "has_elevator",
    "open_house_at",
    "floor_plan_url",
    "kitchen_condition",
    "bathroom_condition",
    "heating",
    "days_listed",
    "price_change_pct",
    "latest_valuation",
    "description_title",
    "description_body",
    "realtor_name",
    "case_url",
    "boligsiden_url",
    "image_url",
    "image_urls",
    "status",
    "is_active",
    "excluded",
    "exclusion_reason",
    "first_seen",
    "last_seen",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Optional[Path] = None) -> sqlite3.Connection:
    target = Path(path or config.DB_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns that CREATE TABLE IF NOT EXISTS will not add to an existing
    table. Additive only: nothing here drops or rewrites data."""
    wanted = {
        "listings": [
            ("has_balcony_text", "INTEGER"),
            ("open_house_at", "TEXT"),
            ("floor_plan_url", "TEXT"),
            ("is_houseboat", "INTEGER"),
            ("balcony_ai", "INTEGER"),
        ],
        "scores": [
            ("benchmark_source", "TEXT"),
            ("headline", "TEXT"),
        ],
    }
    for table, columns in wanted.items():
        existing = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, sql_type in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")


@contextmanager
def session(path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    conn = connect(path)
    try:
        init(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Writes
# --------------------------------------------------------------------------


def upsert_listing(conn: sqlite3.Connection, row: Dict[str, Any]) -> str:
    """Insert or update one listing. Returns 'new', 'price_drop', 'price_rise'
    or 'seen' so the caller knows whether it is worth alerting on."""
    case_id = row["case_id"]
    existing = conn.execute(
        "SELECT price, is_active FROM listings WHERE case_id = ?", (case_id,)
    ).fetchone()

    stamp = now_iso()
    row = dict(row)
    row["last_seen"] = stamp
    row.setdefault("is_active", 1)

    if existing is None:
        row["first_seen"] = stamp
        columns = [c for c in LISTING_COLUMNS if c in row]
        conn.execute(
            f"INSERT INTO listings ({','.join(columns)}) "
            f"VALUES ({','.join('?' for _ in columns)})",
            [row[c] for c in columns],
        )
        _record_price(conn, case_id, row.get("price"), "listed", stamp)
        return "new"

    columns = [
        c for c in LISTING_COLUMNS if c in row and c != "case_id" and c != "first_seen"
    ]
    conn.execute(
        f"UPDATE listings SET {','.join(f'{c}=?' for c in columns)}, delisted_at=NULL "
        f"WHERE case_id = ?",
        [row[c] for c in columns] + [case_id],
    )

    old_price = existing["price"]
    new_price = row.get("price")
    if old_price and new_price and new_price != old_price:
        _record_price(conn, case_id, new_price, "change", stamp)
        return "price_drop" if new_price < old_price else "price_rise"
    return "seen"


def _record_price(
    conn: sqlite3.Connection,
    case_id: str,
    price: Optional[int],
    source: str,
    stamp: str,
) -> None:
    if not price:
        return
    conn.execute(
        "INSERT OR IGNORE INTO price_events (case_id, observed, price, source) "
        "VALUES (?,?,?,?)",
        (case_id, stamp, int(price), source),
    )


def mark_delisted(conn: sqlite3.Connection, seen_ids: List[str]) -> int:
    """Anything active that this run did not see has left the market."""
    if not seen_ids:
        return 0
    placeholders = ",".join("?" for _ in seen_ids)
    cursor = conn.execute(
        f"UPDATE listings SET is_active = 0, delisted_at = ? "
        f"WHERE is_active = 1 AND case_id NOT IN ({placeholders})",
        [now_iso()] + seen_ids,
    )
    return cursor.rowcount


def save_demand(conn: sqlite3.Connection, stats: Dict[str, Dict[str, int]]) -> None:
    stamp = now_iso()
    conn.executemany(
        "INSERT OR REPLACE INTO demand (case_id, captured_at, page_views, clicks, favourites) "
        "VALUES (?,?,?,?,?)",
        [
            (
                case_id,
                stamp,
                s.get("pageViews"),
                s.get("totalClickCount"),
                s.get("totalFavourites"),
            )
            for case_id, s in stats.items()
        ],
    )


def save_sale_history(
    conn: sqlite3.Connection, address_id: str, timeline: List[Dict[str, Any]]
) -> None:
    rows = [
        (address_id, event.get("at"), event.get("price"), event.get("type"))
        for event in timeline
        if event.get("type") in ("sold", "built")
    ]
    if rows:
        conn.executemany(
            "INSERT OR IGNORE INTO sale_history (address_id, sold_at, price, event_type) "
            "VALUES (?,?,?,?)",
            rows,
        )


def save_score(conn: sqlite3.Connection, case_id: str, result: Dict[str, Any]) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO scores (case_id, scored_at, total, bonus, breakdown, "
        "neighbourhood, neighbourhood_tier, parish, parish_sqm_price, benchmark_basis, "
        "benchmark_source, headline, sqm_price_ratio, water_distance_m, water_name, "
        "water_kind) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            case_id,
            now_iso(),
            result["total"],
            result.get("bonus", 0.0),
            json.dumps(result["breakdown"], ensure_ascii=False),
            result.get("neighbourhood"),
            result.get("neighbourhood_tier"),
            result.get("parish"),
            result.get("parish_sqm_price"),
            result.get("benchmark_basis"),
            result.get("benchmark_source"),
            result.get("headline"),
            result.get("sqm_price_ratio"),
            result.get("water_distance_m"),
            result.get("water_name"),
            result.get("water_kind"),
        ),
    )


def save_benchmarks(
    conn: sqlite3.Connection,
    kind: str,
    address_type: str,
    rows: Dict[str, Dict[str, Any]],
) -> None:
    stamp = now_iso()
    conn.executemany(
        "INSERT OR REPLACE INTO benchmarks (kind, key, address_type, sqm_price, basis, updated_at) "
        "VALUES (?,?,?,?,?,?)",
        [
            (kind, key, address_type, value.get("sqm_price"), value.get("basis"), stamp)
            for key, value in rows.items()
        ],
    )


def save_verdict(
    conn: sqlite3.Connection,
    case_id: str,
    model: str,
    price_seen: Optional[int],
    verdict: Dict[str, Any],
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO ai_verdicts (case_id, created_at, model, price_seen, verdict) "
        "VALUES (?,?,?,?,?)",
        (
            case_id,
            now_iso(),
            model,
            price_seen,
            json.dumps(verdict, ensure_ascii=False),
        ),
    )


def apply_verdict_corrections(
    conn: sqlite3.Connection, case_id: str, verdict: Dict[str, Any]
) -> bool:
    """Write back facts the model established that the API got wrong.

    Boligsiden's ``hasBalcony`` is demonstrably unreliable, so the model is
    asked to judge it from the listing text and photo descriptions. Stored in
    its own column rather than overwriting the API value, so the disagreement
    stays visible instead of being erased.

    Takes effect on the next scoring pass, since scoring runs before the model
    does. Returns True when the model disagreed with the API.
    """
    confirmed = verdict.get("balcony_confirmed")
    if confirmed is None:
        return False

    conn.execute(
        "UPDATE listings SET balcony_ai = ? WHERE case_id = ?",
        (1 if confirmed else 0, case_id),
    )
    row = conn.execute(
        "SELECT has_balcony, has_balcony_text FROM listings WHERE case_id = ?",
        (case_id,),
    ).fetchone()
    if row is None:
        return False
    claimed = bool(row["has_balcony"] or row["has_balcony_text"])
    return claimed != bool(confirmed)


def record_alert(
    conn: sqlite3.Connection, case_id: str, kind: str, detail: str = ""
) -> None:
    conn.execute(
        "INSERT INTO alerts (case_id, kind, sent_at, detail) VALUES (?,?,?,?)",
        (case_id, kind, now_iso(), detail),
    )


def already_alerted(conn: sqlite3.Connection, case_id: str, kind: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM alerts WHERE case_id = ? AND kind = ? LIMIT 1", (case_id, kind)
    ).fetchone()
    return row is not None


def start_run(conn: sqlite3.Connection) -> int:
    cursor = conn.execute("INSERT INTO runs (started_at) VALUES (?)", (now_iso(),))
    conn.commit()
    return int(cursor.lastrowid)


def finish_run(
    conn: sqlite3.Connection,
    run_id: int,
    seen: int,
    new_listings: int,
    price_drops: int,
    delisted: int,
    errors: str = "",
) -> None:
    conn.execute(
        "UPDATE runs SET finished_at=?, seen=?, new_listings=?, price_drops=?, "
        "delisted=?, errors=? WHERE id=?",
        (now_iso(), seen, new_listings, price_drops, delisted, errors, run_id),
    )


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------

LISTING_VIEW = """
SELECT l.*, s.total AS score, s.bonus, s.breakdown, s.neighbourhood,
       s.neighbourhood_tier, s.parish, s.parish_sqm_price, s.benchmark_basis,
       s.benchmark_source, s.headline,
       s.sqm_price_ratio, s.water_distance_m, s.water_name, s.water_kind,
       v.verdict AS ai_verdict, v.created_at AS ai_created_at,
       d.page_views, d.clicks, d.favourites,
       rt.stars, rt.note AS rating_note, rt.rated_at
FROM listings l
LEFT JOIN scores s ON s.case_id = l.case_id
LEFT JOIN ai_verdicts v ON v.case_id = l.case_id
LEFT JOIN (
    SELECT case_id, page_views, clicks, favourites,
           ROW_NUMBER() OVER (PARTITION BY case_id ORDER BY captured_at DESC) AS rn
    FROM demand
) d ON d.case_id = l.case_id AND d.rn = 1
LEFT JOIN ratings rt ON rt.case_id = l.case_id
"""


def get_pref(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except (TypeError, ValueError):
        return default


def set_pref(conn: sqlite3.Connection, key: str, value: Any) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?,?,?)",
        (key, json.dumps(value, ensure_ascii=False), now_iso()),
    )


def active_weights(conn: sqlite3.Connection) -> Tuple[str, Dict[str, float]]:
    """The weighting in force: (profile key, weights).

    Stored rather than held in config so the web app, the pipeline and the
    Telegram alerts all rank listings the same way.
    """
    key = get_pref(conn, "profile", config.DEFAULT_PROFILE)
    if key == "custom":
        custom = get_pref(conn, "custom_weights")
        if custom:
            return "custom", config.normalise_weights(custom)
        key = config.DEFAULT_PROFILE
    if key not in config.PROFILES:
        key = config.DEFAULT_PROFILE
    return key, dict(config.PROFILES[key]["weights"])


def save_rating(
    conn: sqlite3.Connection, case_id: str, stars: int, note: str = ""
) -> None:
    """Store or replace a rating. Zero stars removes it."""
    if stars <= 0:
        conn.execute("DELETE FROM ratings WHERE case_id = ?", (case_id,))
        return
    score = conn.execute(
        "SELECT total FROM scores WHERE case_id = ?", (case_id,)
    ).fetchone()
    conn.execute(
        "INSERT OR REPLACE INTO ratings (case_id, stars, note, rated_at, "
        "score_when_rated) VALUES (?,?,?,?,?)",
        (
            case_id,
            int(stars),
            note or None,
            now_iso(),
            score["total"] if score else None,
        ),
    )


def rated_listings(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    return conn.execute(
        f"{LISTING_VIEW} WHERE rt.stars IS NOT NULL ORDER BY rt.stars DESC, s.total DESC"
    ).fetchall()


def unrated_listings(conn: sqlite3.Connection, limit: int = 200) -> List[sqlite3.Row]:
    """Candidates still awaiting a verdict from Mark, best first."""
    return conn.execute(
        f"{LISTING_VIEW} WHERE l.is_active = 1 AND l.excluded = 0 "
        f"AND rt.stars IS NULL ORDER BY s.total DESC NULLS LAST LIMIT {int(limit)}"
    ).fetchall()


def rating_counts(conn: sqlite3.Connection) -> Dict[str, int]:
    total = conn.execute("SELECT COUNT(*) c FROM ratings").fetchone()["c"]
    rows = conn.execute(
        "SELECT stars, COUNT(*) c FROM ratings GROUP BY stars"
    ).fetchall()
    out = {str(r["stars"]): r["c"] for r in rows}
    out["total"] = total
    return out


def active_listings(
    conn: sqlite3.Connection,
    include_excluded: bool = False,
    limit: Optional[int] = None,
) -> List[sqlite3.Row]:
    where = "WHERE l.is_active = 1" + (
        "" if include_excluded else " AND l.excluded = 0"
    )
    sql = f"{LISTING_VIEW} {where} ORDER BY s.total DESC NULLS LAST"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql).fetchall()


def listing(conn: sqlite3.Connection, case_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(f"{LISTING_VIEW} WHERE l.case_id = ?", (case_id,)).fetchone()


def price_events(conn: sqlite3.Connection, case_id: str) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT observed, price, source FROM price_events WHERE case_id = ? ORDER BY observed",
        (case_id,),
    ).fetchall()


def sale_history(conn: sqlite3.Connection, address_id: str) -> List[sqlite3.Row]:
    return conn.execute(
        "SELECT sold_at, price, event_type FROM sale_history WHERE address_id = ? "
        "ORDER BY sold_at DESC",
        (address_id,),
    ).fetchall()


def benchmark_map(
    conn: sqlite3.Connection, kind: str, address_type: str
) -> Dict[str, int]:
    rows = conn.execute(
        "SELECT key, sqm_price FROM benchmarks WHERE kind = ? AND address_type = ? "
        "AND sqm_price IS NOT NULL",
        (kind, address_type),
    ).fetchall()
    return {row["key"]: row["sqm_price"] for row in rows}
