"""
Refresh active listings from Boligsiden API.

Two-phase approach per municipality:

  Phase 1 — Update known active listings (detail API):
    Query DB for is_on_market=True properties, fetch each via /addresses/{id},
    update property + case data, mark any that are no longer on-market.

  Phase 2 — Discover new listings (search API):
    Page through search results for the municipality, insert any property
    found as on-market that is not yet in the DB.

Usage:
    python scripts/refresh_listings.py --test                       # Albertslund, 20 active props, no commit
    python scripts/refresh_listings.py --municipality Albertslund   # Single municipality, full run
    python scripts/refresh_listings.py                              # All 36 municipalities
    python scripts/refresh_listings.py --skip-discovery             # Phase 1 only (faster daily refresh)
"""

import sys
import os
import time
import random
import argparse
import requests
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.db_models_new import (
    Property, Case, PriceChange, CaseImage,
    MainBuilding, AdditionalBuilding, Registration,
    Municipality, Province, Road, Zip, City, Place, DaysOnMarket,
)
import scripts.import_api_data as importer

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_BASE    = "https://api.boligsiden.dk"
DETAIL_URL  = f"{API_BASE}/addresses"
SEARCH_URL  = f"{API_BASE}/search/addresses"
RATE_LIMIT  = 0.15  # seconds between API calls

DB_URL = (
    os.getenv('DATABASE_URL') or
    "postgresql://{user}:{pw}@{host}:{port}/{db}".format(
        user=os.getenv('DB_USER', 'housing'),
        pw=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5434'),
        db=os.getenv('DB_NAME', 'housing_db'),
    )
)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
]

ALL_MUNICIPALITIES = [
    'København', 'Frederiksberg', 'Gentofte', 'Gladsaxe', 'Lyngby-Taarbæk',
    'Rudersdal', 'Hørsholm', 'Allerød', 'Fredensborg', 'Helsingør',
    'Hillerød', 'Gribskov', 'Halsnæs', 'Frederikssund', 'Egedal',
    'Furesø', 'Ballerup', 'Herlev', 'Rødovre', 'Brøndby',
    'Glostrup', 'Albertslund', 'Høje-Taastrup', 'Ishøj', 'Vallensbæk',
    'Hvidovre', 'Tårnby', 'Dragør', 'Greve', 'Solrød',
    'Køge', 'Stevns', 'Faxe', 'Holbæk', 'Ringsted', 'Roskilde', 'Lejre',
]


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def get_headers() -> dict:
    return {
        'authority': 'api.boligsiden.dk',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en;q=0.9',
        'origin': 'https://www.boligsiden.dk',
        'referer': 'https://www.boligsiden.dk/',
        'user-agent': random.choice(USER_AGENTS),
    }


def fetch_detail(property_id: str) -> dict | None:
    """Fetch full property data from detail endpoint. Returns None on 404/error."""
    try:
        r = requests.get(
            f"{DETAIL_URL}/{property_id}",
            headers=get_headers(),
            timeout=15,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"    ⚠  Detail API error for {property_id}: {e}")
        return None


def fetch_search_page(municipality: str, page: int) -> dict | None:
    """Fetch one page of search results for a municipality."""
    try:
        r = requests.get(
            SEARCH_URL,
            params={
                'municipalities': municipality,
                'addressTypes': 'villa',
                'page': str(page),
                'sortBy': 'address',
                'sortAscending': 'true',
            },
            headers=get_headers(),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"    ⚠  Search API error page {page}: {e}")
        return None


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------

def upsert_property(session, api_data: dict) -> Property:
    """Insert or update a property from API data."""
    prop_id  = api_data.get('addressID')
    coords   = api_data.get('coordinates') or {}
    sold_d   = api_data.get('latestSoldCaseDescription') or {}
    bsi      = api_data.get('boligsidenInfo') or {}
    links    = (api_data.get('_links') or {})

    fields = dict(
        address_type=api_data.get('addressType'),
        road_name=api_data.get('roadName'),
        house_number=api_data.get('houseNumber'),
        city_name=api_data.get('cityName'),
        zip_code=api_data.get('zipCode'),
        place_name=api_data.get('placeName'),
        latitude=coords.get('lat'),
        longitude=coords.get('lon'),
        coordinate_type=coords.get('type'),
        living_area=api_data.get('livingArea'),
        weighted_area=api_data.get('weightedArea'),
        latest_valuation=api_data.get('latestValuation'),
        property_number=api_data.get('propertyNumber'),
        is_on_market=api_data.get('isOnMarket'),
        is_public=api_data.get('isPublic'),
        allow_new_valuation_info=api_data.get('allowNewValuationInfo'),
        energy_label=api_data.get('energyLabel'),
        entry_address_id=api_data.get('entryAddressID'),
        gstkvhx=api_data.get('gstkvhx'),
        slug=api_data.get('slug'),
        slug_address=api_data.get('slugAddress'),
        api_href=(links.get('self') or {}).get('href'),
        bfe_numbers=api_data.get('bfeNumbers'),
        latest_sold_case_title=sold_d.get('title'),
        latest_sold_case_body=sold_d.get('body'),
        latest_sold_case_date=importer.parse_date(sold_d.get('date')),
        boligsiden_latest_sold_area=bsi.get('latestSoldArea'),
    )
    parts = [fields['road_name'], fields['house_number']]
    if fields['city_name'] and fields['zip_code']:
        parts.append(f"{fields['zip_code']} {fields['city_name']}")
    fields['address'] = ' '.join(p for p in parts if p)

    prop = session.get(Property, prop_id)
    if prop is None:
        prop = Property(id=prop_id, **fields)
        session.add(prop)
    else:
        for k, v in fields.items():
            setattr(prop, k, v)
    return prop


def upsert_case(session, property_id: str, case_data: dict) -> tuple[Case, str]:
    """
    Insert or update a case by caseID.
    Returns (case, 'INSERT'|'UPDATE').
    """
    case_id = case_data.get('caseID')
    tom     = case_data.get('timeOnMarket') or {}
    current = tom.get('current') or {}
    total   = tom.get('total') or {}
    re      = case_data.get('realEstate') or {}

    fields = dict(
        property_id=property_id,
        status=case_data.get('status'),
        current_price=case_data.get('priceCash'),
        price_change_percentage=case_data.get('priceChangePercentage'),
        per_area_price=case_data.get('perAreaPrice'),
        monthly_expense=case_data.get('monthlyExpense'),
        down_payment=re.get('downPayment'),
        gross_mortgage=re.get('grossMortgage'),
        net_mortgage=re.get('netMortgage'),
        days_on_market_current=current.get('days'),
        days_on_market_total=total.get('days'),
        days_listed=(case_data.get('daysListed') or {}).get('days'),
        lot_area=case_data.get('lotArea'),
        basement_area=case_data.get('basementArea'),
        year_built=case_data.get('yearBuilt'),
        description_title=case_data.get('descriptionTitle'),
        description_body=case_data.get('descriptionBody'),
        case_url=case_data.get('caseUrl'),
        provider_case_id=case_data.get('providerCaseID'),
        has_balcony=case_data.get('hasBalcony'),
        has_terrace=case_data.get('hasTerrace'),
        has_elevator=case_data.get('hasElevator'),
        highlighted=case_data.get('highlighted'),
        distinction=case_data.get('distinction'),
        realtors_info=total.get('realtors', []),
    )

    case = session.query(Case).filter_by(case_id=case_id).first()
    if case is None:
        case = Case(case_id=case_id, **fields)
        session.add(case)
        # Add price changes on first insert only
        for pc in case_data.get('priceChanges') or []:
            cd = pc.get('created')
            if cd:
                try:
                    cd = datetime.fromisoformat(cd.replace('Z', '+00:00'))
                except ValueError:
                    cd = None
            case.price_changes.append(PriceChange(
                change_date=cd,
                old_price=pc.get('oldPrice'),
                new_price=pc.get('newPrice'),
                price_change_amount=pc.get('priceChange'),
            ))
        return case, 'INSERT'
    else:
        for k, v in fields.items():
            setattr(case, k, v)
        return case, 'UPDATE'


# ---------------------------------------------------------------------------
# Phase 1: Update known active listings
# ---------------------------------------------------------------------------

def refresh_active_listings(session, municipality: str, dry_run: bool, limit: int | None = None):
    """
    Fetch detail data for all is_on_market=True properties in this municipality.
    Update their data; mark as off-market if the API reports isOnMarket=False or 404.
    """
    from src.db_models_new import Municipality as MuniModel

    active_props = (
        session.query(Property)
        .join(Property.municipality_info)
        .filter(MuniModel.name == municipality, Property.is_on_market == True)
        .all()
    )

    if limit:
        active_props = active_props[:limit]

    print(f"\n  Phase 1 — Refreshing {len(active_props)} known active listings")

    updated = delisted = errors = cases_inserted = cases_updated = 0

    for prop in active_props:
        api_data = fetch_detail(prop.id)
        time.sleep(RATE_LIMIT)

        if api_data is None:
            # 404 or API error — mark off-market
            if not dry_run:
                prop.is_on_market = False
            delisted += 1
            print(f"    ✗ {prop.id} — 404/error, marked off-market")
            continue

        still_on_market = api_data.get('isOnMarket', False)

        if not dry_run:
            upsert_property(session, api_data)
            for case_data in (api_data.get('cases') or []):
                _, action = upsert_case(session, prop.id, case_data)
                if action == 'INSERT':
                    cases_inserted += 1
                else:
                    cases_updated += 1

        if not still_on_market:
            if not dry_run:
                prop.is_on_market = False
            delisted += 1
        else:
            updated += 1

    print(f"    Updated:        {updated}")
    print(f"    Delisted:       {delisted}")
    print(f"    Cases inserted: {cases_inserted}")
    print(f"    Cases updated:  {cases_updated}")
    print(f"    Errors:         {errors}")

    return dict(updated=updated, delisted=delisted,
                cases_inserted=cases_inserted, cases_updated=cases_updated, errors=errors)


# ---------------------------------------------------------------------------
# Phase 2: Discover new on-market listings
# ---------------------------------------------------------------------------

def discover_new_listings(session, municipality: str, dry_run: bool):
    """
    Page through search results for municipality, insert any on-market property
    not yet in the DB. Skips off-market results silently.
    """
    print(f"\n  Phase 2 — Discovering new listings in {municipality}")

    # Pre-load all existing property IDs for this municipality (fast set lookup)
    from src.db_models_new import Municipality as MuniModel
    existing_ids = {
        r[0] for r in
        session.query(Property.id)
        .join(Property.municipality_info)
        .filter(MuniModel.name == municipality)
        .all()
    }

    inserted = skipped_existing = skipped_off_market = cases_inserted = 0
    page = 1

    while True:
        data = fetch_search_page(municipality, page)
        if not data:
            break

        addresses = data.get('addresses') or []
        if not addresses:
            break

        total_hits = data.get('totalHits', 0)

        for addr in addresses:
            prop_id = addr.get('addressID')
            if not prop_id:
                continue
            if prop_id in existing_ids:
                skipped_existing += 1
                continue
            if not addr.get('isOnMarket'):
                skipped_off_market += 1
                continue

            # New on-market property not in DB
            if not dry_run:
                try:
                    upsert_property(session, addr)
                    for case_data in (addr.get('cases') or []):
                        upsert_case(session, prop_id, case_data)
                        cases_inserted += 1
                    existing_ids.add(prop_id)
                    inserted += 1
                except Exception as e:
                    print(f"    ⚠  Error inserting {prop_id}: {e}")
                    session.rollback()
            else:
                road = addr.get('roadName', '')
                num  = addr.get('houseNumber', '')
                print(f"    [NEW] {road} {num} ({prop_id})")
                inserted += 1

        if (page * 50) >= total_hits:
            break
        page += 1
        time.sleep(RATE_LIMIT)

    print(f"    New listings inserted:  {inserted}")
    print(f"    Cases inserted:         {cases_inserted}")
    print(f"    Skipped (in DB):        {skipped_existing}")
    print(f"    Skipped (off-market):   {skipped_off_market}")
    print(f"    Pages fetched:          {page}")

    return dict(new_inserted=inserted, new_cases_inserted=cases_inserted)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def refresh_municipality(
    session, municipality: str,
    dry_run: bool,
    skip_discovery: bool,
    active_limit: int | None = None,
):
    print(f"\n{'='*60}")
    print(f"  {municipality}{'  [DRY RUN]' if dry_run else ''}")
    print(f"{'='*60}")

    stats = {}

    p1 = refresh_active_listings(session, municipality, dry_run, limit=active_limit)
    stats.update(p1)

    if not skip_discovery:
        p2 = discover_new_listings(session, municipality, dry_run)
        stats.update(p2)

    return stats


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Refresh active listings from Boligsiden API')
    parser.add_argument('--test', action='store_true',
                        help='Test run: Albertslund, first 20 active properties only, no DB writes')
    parser.add_argument('--municipality', type=str,
                        help='Refresh a single municipality by name')
    parser.add_argument('--dry-run', action='store_true',
                        help='Fetch and parse but do not write to DB')
    parser.add_argument('--skip-discovery', action='store_true',
                        help='Skip Phase 2 (new listing discovery) — faster for daily refresh')
    args = parser.parse_args()

    dry_run        = args.test or args.dry_run
    skip_discovery = args.skip_discovery
    active_limit   = 20 if args.test else None

    if args.test:
        municipalities = ['Albertslund']
        print("🧪 TEST MODE — Albertslund, first 20 active properties, no DB writes")
    elif args.municipality:
        municipalities = [args.municipality]
    else:
        municipalities = ALL_MUNICIPALITIES

    engine  = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    totals = dict(updated=0, delisted=0, cases_inserted=0, cases_updated=0,
                  errors=0, new_inserted=0, new_cases_inserted=0)

    try:
        for muni in municipalities:
            stats = refresh_municipality(
                session, muni,
                dry_run=dry_run,
                skip_discovery=skip_discovery,
                active_limit=active_limit,
            )
            for k in totals:
                totals[k] += stats.get(k, 0)

            if not dry_run:
                session.commit()
                print(f"\n  ✅ Committed {muni}")

    except KeyboardInterrupt:
        print("\n⚠  Interrupted — rolling back")
        session.rollback()
    finally:
        session.close()

    print(f"\n{'='*60}")
    print("  TOTALS")
    print(f"{'='*60}")
    for k, v in totals.items():
        print(f"  {k:<25} {v}")


if __name__ == '__main__':
    main()
