"""
Verify import/refresh data integrity.

Run as final step after refresh_listings.py or import_copenhagen_area.py.
Exit 0 if all checks pass, 1 on critical failure.

Usage:
    python scripts/verify_import_integrity.py
"""

import os
import sys
from datetime import datetime, date
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5434')
DB_NAME = os.getenv('DB_NAME', 'housing_db')
DB_USER = os.getenv('DB_USER', 'housing')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

if not DB_PASSWORD and os.getenv('DATABASE_URL'):
    try:
        DB_PASSWORD = os.getenv('DATABASE_URL', '').split(':')[2].split('@')[0]
    except IndexError:
        pass

DATABASE_URL = os.getenv('DATABASE_URL') or (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

EXPECTED_MUNICIPALITIES = 36
PRICE_MIN = 10_000
PRICE_MAX = 500_000_000
STALE_DAYS = 30


def run_query(conn, sql: str, params=None):
    """Execute query and return first row or scalar."""
    result = conn.execute(text(sql), params or {})
    row = result.fetchone()
    return row[0] if row and len(row) == 1 else row


def main() -> int:
    """Run integrity checks. Returns 0 on pass, 1 on critical fail."""
    engine = create_engine(DATABASE_URL)
    failed = False

    with engine.connect() as conn:
        # Row counts
        props = run_query(conn, "SELECT COUNT(*) FROM properties_new")
        regs = run_query(conn, "SELECT COUNT(*) FROM registrations")
        cases = run_query(conn, "SELECT COUNT(*) FROM cases")

        print(f"Row counts: properties={props:,}, registrations={regs:,}, cases={cases:,}")

        if props < 1000:
            print("  WARN: Very few properties - import may be incomplete")
        if regs < 10000:
            print("  WARN: Few registrations - historical data may be sparse")

        # Date coverage
        latest_reg = run_query(conn, "SELECT MAX(date)::date FROM registrations WHERE date IS NOT NULL")
        if latest_reg:
            d = latest_reg.date() if isinstance(latest_reg, datetime) else latest_reg
            age = (date.today() - d).days
            print(f"Latest registration date: {latest_reg} ({age} days ago)")
            if age > STALE_DAYS:
                print("  WARN: Data may be stale for statistics")
        else:
            print("  WARN: No registration dates found")

        # Municipality coverage
        mun_count = run_query(conn, "SELECT COUNT(DISTINCT name) FROM municipalities WHERE name IS NOT NULL")
        print(f"Municipalities: {mun_count} (expected {EXPECTED_MUNICIPALITIES})")
        if mun_count < EXPECTED_MUNICIPALITIES:
            print("  WARN: Some municipalities may be missing")

        # Price sanity
        bad_price = run_query(conn, """
            SELECT COUNT(*) FROM registrations
            WHERE amount IS NOT NULL AND (amount < :min_p OR amount > :max_p)
        """, {"min_p": PRICE_MIN, "max_p": PRICE_MAX})
        if bad_price and bad_price > 0:
            print(f"  WARN: {bad_price} registrations with price outside {PRICE_MIN}-{PRICE_MAX} kr")

        # Orphan check (registrations without valid property)
        orphan_regs = run_query(conn, """
            SELECT COUNT(*) FROM registrations r
            WHERE NOT EXISTS (SELECT 1 FROM properties_new p WHERE p.id = r.property_id)
        """)
        if orphan_regs and orphan_regs > 0:
            print(f"  FAIL: {orphan_regs} orphan registrations (no matching property)")
            failed = True

        # Null municipality_code in registrations
        null_mun = run_query(conn, "SELECT COUNT(*) FROM registrations WHERE municipality_code IS NULL")
        if null_mun and null_mun > 0:
            pct = 100 * null_mun / regs if regs else 0
            print(f"  INFO: {null_mun} registrations ({pct:.1f}%) without municipality_code - excluded from kommune stats")

    print("Verification complete." if not failed else "Verification FAILED.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
