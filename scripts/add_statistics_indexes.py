"""
Add indexes for statistics queries.

Idempotent: safe to run multiple times. Uses IF NOT EXISTS where supported.

Run after schema is in place, before statistics API is used.
Usage:
    python scripts/add_statistics_indexes.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5434')
DB_NAME = os.getenv('DB_NAME', 'housing_db')
DB_USER = os.getenv('DB_USER', 'housing')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

if not DB_PASSWORD:
    DB_PASSWORD = os.getenv('DATABASE_URL', '').split(':')[2].split('@')[0] if os.getenv('DATABASE_URL') else ''

DATABASE_URL = os.getenv('DATABASE_URL') or (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


INDEXES = [
    ("idx_registrations_date", "CREATE INDEX IF NOT EXISTS idx_registrations_date ON registrations(date)"),
    ("idx_registrations_municipality_date", "CREATE INDEX IF NOT EXISTS idx_registrations_municipality_date ON registrations(municipality_code, date)"),
    ("idx_registrations_type", "CREATE INDEX IF NOT EXISTS idx_registrations_type ON registrations(type)"),
    ("idx_cases_sold_date", "CREATE INDEX IF NOT EXISTS idx_cases_sold_date ON cases(sold_date) WHERE sold_date IS NOT NULL"),
    ("idx_cases_created_date", "CREATE INDEX IF NOT EXISTS idx_cases_created_date ON cases(created_date)"),
    ("idx_cases_status", "CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)"),
    ("idx_price_changes_date", "CREATE INDEX IF NOT EXISTS idx_price_changes_date ON price_changes(change_date)"),
]


def main() -> int:
    """Create statistics indexes. Returns 0 on success, 1 on error."""
    print("Adding statistics indexes...")
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        for name, sql in INDEXES:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"  OK: {name}")
            except Exception as e:
                print(f"  FAIL: {name} - {e}")
                return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
