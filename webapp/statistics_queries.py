"""
Statistics query helpers for housing market analytics.

Uses registrations (type='normal') for historical sales. Excludes family/auction.
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.db_models_new import Property, Case, Registration, Municipality


def get_data_as_of(session: Session) -> Optional[datetime]:
    """Latest registration date for data freshness."""
    r = session.execute(
        text("SELECT MAX(date) FROM registrations WHERE type = 'normal' AND date IS NOT NULL")
    ).scalar()
    return r


def get_row_counts(session: Session) -> dict:
    """Lightweight row counts for health check."""
    props = session.query(Property).count()
    regs = session.query(Registration).count()
    cases = session.query(Case).count()
    return {"properties": props, "registrations": regs, "cases": cases}


def get_market_overview(session: Session) -> dict:
    """Active listings, sold this month, avg sqm price (national)."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    active = session.query(Property.id).join(Case).filter(
        Property.is_on_market == True,
        Case.status == 'open',
        Case.current_price.isnot(None)
    ).distinct().count()

    sold_this_month = session.query(Registration).filter(
        Registration.type == 'normal',
        Registration.date >= month_start,
        Registration.date <= now
    ).count()

    # Avg kr/sqm from recent registrations (last 12 months)
    year_ago = now - timedelta(days=365)
    sqm_result = session.execute(text("""
        SELECT AVG(per_area_price) as avg_sqm
        FROM registrations
        WHERE type = 'normal'
          AND date >= :since
          AND per_area_price IS NOT NULL
          AND per_area_price BETWEEN 10000 AND 200000
    """), {"since": year_ago}).fetchone()
    avg_sqm = float(sqm_result[0]) if sqm_result and sqm_result[0] else None

    return {
        "active_listings": active,
        "sold_this_month": sold_this_month,
        "avg_sqm_price_national": round(avg_sqm, 0) if avg_sqm else None,
    }


def get_price_trends(
    session: Session,
    municipality: Optional[str] = None,
    period: str = "month",
    months: int = 12
) -> list:
    """Time series: date, avg_sqm_price, median_sqm_price, count."""
    from datetime import date
    end = date.today()
    start = end - timedelta(days=months * 31)

    mun_filter = ""
    params = {"start": start, "end": end}
    if municipality and municipality != "all":
        mun_filter = " AND m.name = :municipality"
        params["municipality"] = municipality

    trunc = "month" if period == "month" else "quarter" if period == "quarter" else "year"
    sql = f"""
        SELECT
            date_trunc('{trunc}', r.date)::date as period,
            AVG(r.per_area_price) as avg_sqm,
            COUNT(*) as cnt
        FROM registrations r
        JOIN properties_new p ON p.id = r.property_id
        JOIN municipalities m ON m.property_id = p.id
        WHERE r.type = 'normal'
          AND r.date >= :start AND r.date <= :end
          AND r.per_area_price IS NOT NULL
          AND r.per_area_price BETWEEN 10000 AND 200000
          {mun_filter}
        GROUP BY date_trunc('{trunc}', r.date)
        ORDER BY period
        LIMIT 100
    """
    rows = session.execute(text(sql), params).fetchall()
    return [
        {"date": str(r[0]), "avg_sqm_price": round(float(r[1]), 0), "count": r[2]}
        for r in rows
    ]


def get_sales_volume(
    session: Session,
    municipality: Optional[str] = None,
    months: int = 12
) -> list:
    """Time series: date, sales_count."""
    from datetime import date
    end = date.today()
    start = end - timedelta(days=months * 31)

    mun_filter = ""
    params = {"start": start, "end": end}
    if municipality and municipality != "all":
        mun_filter = " AND m.name = :municipality"
        params["municipality"] = municipality

    sql = f"""
        SELECT date_trunc('month', r.date)::date as period, COUNT(*) as cnt
        FROM registrations r
        JOIN properties_new p ON p.id = r.property_id
        JOIN municipalities m ON m.property_id = p.id
        WHERE r.type = 'normal'
          AND r.date >= :start AND r.date <= :end
          {mun_filter}
        GROUP BY date_trunc('month', r.date)
        ORDER BY period
        LIMIT 24
    """
    rows = session.execute(text(sql), params).fetchall()
    return [{"date": str(r[0]), "sales_count": r[1]} for r in rows]


def get_kommune_summary(session: Session, municipality: Optional[str] = None) -> list:
    """Per-kommune: name, sales_count, avg_sqm_price, sqm_price_yoy_pct, avg_living_area."""
    from datetime import date
    now = date.today()
    this_year_start = now.replace(month=1, day=1)
    last_year_start = this_year_start.replace(year=this_year_start.year - 1)

    mun_filter = ""
    params = {"y1_start": this_year_start, "y1_end": now, "y0_start": last_year_start, "y0_end": this_year_start}
    if municipality and municipality != "all":
        mun_filter = " AND m.name = :municipality"
        params["municipality"] = municipality

    sql = f"""
        WITH yearly AS (
            SELECT
                m.name,
                m.municipality_code,
                AVG(CASE WHEN r.date >= :y1_start AND r.date <= :y1_end THEN r.per_area_price END) as avg_this_year,
                AVG(CASE WHEN r.date >= :y0_start AND r.date < :y0_end THEN r.per_area_price END) as avg_last_year,
                COUNT(CASE WHEN r.date >= :y1_start AND r.date <= :y1_end THEN 1 END) as sales_this_year,
                AVG(r.living_area) as avg_area
            FROM registrations r
            JOIN properties_new p ON p.id = r.property_id
            JOIN municipalities m ON m.property_id = p.id
            WHERE r.type = 'normal'
              AND r.per_area_price IS NOT NULL
              AND r.per_area_price BETWEEN 10000 AND 200000
              {mun_filter}
            GROUP BY m.name, m.municipality_code
        )
        SELECT
            name,
            sales_this_year,
            ROUND(avg_this_year::numeric, 0) as avg_sqm_price,
            CASE WHEN avg_last_year > 0
                THEN ROUND(100.0 * (avg_this_year - avg_last_year) / avg_last_year, 1)
                ELSE NULL END as sqm_price_yoy_pct,
            ROUND(avg_area::numeric, 1) as avg_living_area
        FROM yearly
        WHERE name IS NOT NULL
        ORDER BY sales_this_year DESC NULLS LAST
    """
    rows = session.execute(text(sql), params).fetchall()
    return [
        {
            "name": r[0],
            "sales_count": r[1],
            "avg_sqm_price": int(r[2]) if r[2] else None,
            "sqm_price_yoy_pct": float(r[3]) if r[3] is not None else None,
            "avg_living_area": float(r[4]) if r[4] else None,
        }
        for r in rows
    ]


def get_weekly_summary(session: Session) -> dict:
    """Compact digest for OpenClaw: active, sold 7d, avg kr/sqm, YoY, top/bottom kommuner."""
    from datetime import date, timedelta
    now = date.today()
    week_ago = now - timedelta(days=7)
    year_ago = now - timedelta(days=365)

    active = session.query(Property.id).join(Case).filter(
        Property.is_on_market == True,
        Case.status == 'open',
        Case.current_price.isnot(None)
    ).distinct().count()

    sold_7d = session.query(Registration).filter(
        Registration.type == 'normal',
        Registration.date >= week_ago,
        Registration.date <= datetime.now()
    ).count()

    avg_sqm = session.execute(text("""
        SELECT AVG(per_area_price) FROM registrations
        WHERE type = 'normal' AND date >= :since
          AND per_area_price BETWEEN 10000 AND 200000
    """), {"since": year_ago}).scalar()
    avg_sqm = round(float(avg_sqm), 0) if avg_sqm else None

    # YoY: this week vs same week last year
    last_year_week_start = week_ago.replace(year=week_ago.year - 1)
    last_year_week_end = last_year_week_start + timedelta(days=7)
    yoy = session.execute(text("""
        WITH curr AS (
            SELECT AVG(per_area_price) as v FROM registrations
            WHERE type = 'normal' AND date >= :week_ago
              AND per_area_price BETWEEN 10000 AND 200000
        ),
        prev AS (
            SELECT AVG(per_area_price) as v FROM registrations
            WHERE type = 'normal' AND date >= :ly_start AND date < :ly_end
              AND per_area_price BETWEEN 10000 AND 200000
        )
        SELECT CASE WHEN prev.v > 0 THEN 100.0 * (curr.v - prev.v) / prev.v ELSE NULL END FROM curr, prev
    """), {"week_ago": week_ago, "ly_start": last_year_week_start, "ly_end": last_year_week_end}).scalar()

    top_sales = session.execute(text("""
        SELECT m.name FROM registrations r
        JOIN properties_new p ON p.id = r.property_id
        JOIN municipalities m ON m.property_id = p.id
        WHERE r.type = 'normal' AND r.date >= :since
        GROUP BY m.name ORDER BY COUNT(*) DESC LIMIT 3
    """), {"since": week_ago}).fetchall()
    top_sales = [r[0] for r in top_sales if r[0]]

    bottom_price = session.execute(text("""
        SELECT m.name FROM registrations r
        JOIN properties_new p ON p.id = r.property_id
        JOIN municipalities m ON m.property_id = p.id
        WHERE r.type = 'normal' AND r.date >= :since AND r.per_area_price BETWEEN 10000 AND 200000
        GROUP BY m.name ORDER BY AVG(r.per_area_price) ASC LIMIT 3
    """), {"since": year_ago}).fetchall()
    bottom_price = [r[0] for r in bottom_price if r[0]]

    return {
        "active_listings": active,
        "sold_last_7_days": sold_7d,
        "avg_sqm_price_national": avg_sqm,
        "sqm_price_yoy_pct": round(float(yoy), 1) if yoy is not None else None,
        "top_3_kommuner_by_sales": top_sales,
        "bottom_3_kommuner_by_price": bottom_price,
    }
