"""
Import properties directly from Boligsiden API with filters:
1. Only properties with is_on_market = True (via API query)
2. Only properties within 60km of Copenhagen (client-side filter)
"""

import os
import sys
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from math import radians, cos, sin, asin, sqrt
from datetime import datetime
import time
import argparse

# Load environment
load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db_models_new import Base
from import_api_data import (
    import_property, import_main_building, import_additional_buildings,
    import_registrations, import_municipality, import_province,
    import_road, import_zip, import_city, import_place, import_days_on_market,
    safe_get
)
from copenhagen_municipalities import COPENHAGEN_AREA_MUNICIPALITIES, MUNICIPALITIES_PARAM

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'housing_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Copenhagen coordinates (City Hall Square)
CPH_LAT = 55.6761
CPH_LON = 12.5683
MAX_DISTANCE_KM = 60

# API configuration
API_BASE_URL = "https://api.boligsiden.dk"
API_SEARCH_URL = f"{API_BASE_URL}/search/addresses"

# API headers (mimicking browser request)
API_HEADERS = {
    'authority': 'api.boligsiden.dk',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
    'origin': 'https://www.boligsiden.dk',
    'referer': 'https://www.boligsiden.dk/',
    'sec-ch-ua': '"Google Chrome";v="120", "Not-A.Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return c * 6371  # Earth radius in km


def check_distance_filter(api_data):
    """Check if property is within 60km of Copenhagen"""
    lat = safe_get(api_data, 'latitude')
    lon = safe_get(api_data, 'longitude')
    
    if lat is None or lon is None:
        return False, None
    
    distance = haversine_distance(CPH_LAT, CPH_LON, lat, lon)
    
    if distance > MAX_DISTANCE_KM:
        return False, distance
    
    return True, distance


def fetch_properties_from_api(limit=None, delay=0.5):
    """
    Fetch properties from Boligsiden API search endpoint
    
    Args:
        limit: Maximum number of properties to fetch (None = all available)
        delay: Delay between API requests in seconds
    
    Returns:
        List of property IDs from properties on market
    """
    property_ids = []
    page = 1  # API pages start at 1
    per_page = 20  # API returns 20 per page (max 500 pages)
    
    print("Fetching properties from Boligsiden API...")
    print(f"Filter: sold=false (currently for sale)")
    print()
    
    while True:
        try:
            # Query API for properties currently on market (not sold)
            params = {
                'sold': 'false',  # Get properties currently for sale
                'per_page': str(per_page),
                'page': str(page),
                'sortBy': 'address',  # Sort by address for consistent results
                'sortAscending': 'true'
            }
            
            response = requests.get(API_SEARCH_URL, params=params, headers=API_HEADERS, timeout=30)
            
            if response.status_code != 200:
                print(f"API returned status {response.status_code}, stopping")
                print(f"Response: {response.text[:200]}")
                break
            
            data = response.json()
            addresses = data.get('addresses', [])
            total_hits = data.get('totalHits', 0)
            
            if not addresses:
                print(f"No more results at page {page}")
                break
            
            # Extract property IDs (use 'addressID' field)
            for addr in addresses:
                prop_id = addr.get('addressID')
                if prop_id:
                    property_ids.append(prop_id)
            
            print(f"Page {page}: Found {len(addresses)} properties (total: {len(property_ids)} / {total_hits})")
            
            # Check if we've hit the limit
            if limit and len(property_ids) >= limit:
                property_ids = property_ids[:limit]
                print(f"Reached limit of {limit} properties")
                break
            
            # Check if there are more pages (max 500 pages per API limitation)
            if len(property_ids) >= total_hits:
                print(f"Retrieved all {total_hits} available properties")
                break
            
            if page >= 500:
                print(f"Reached API page limit (500 pages)")
                break
            
            page += 1
            
            # Rate limiting delay
            if delay > 0:
                time.sleep(delay)
                
        except Exception as e:
            print(f"Error fetching page {page}: {str(e)}")
            break
    
    return property_ids


def import_property_from_api(property_id, session):
    """Import a single property from API"""
    try:
        # Fetch property details
        url = f"{API_BASE_URL}/addresses/{property_id}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return False, f"api_error_{response.status_code}"
        
        api_data = response.json()
        
        # Check distance filter
        passes, distance = check_distance_filter(api_data)
        
        if not passes:
            if distance is None:
                return False, "no_coordinates"
            else:
                return False, f"too_far_{distance:.1f}km"
        
        # Import property
        property_obj = import_property(api_data)
        session.add(property_obj)
        
        # Buildings
        main_building = import_main_building(property_id, safe_get(api_data, 'buildings'))
        if main_building:
            session.add(main_building)
        
        for additional_building in import_additional_buildings(property_id, safe_get(api_data, 'buildings')):
            session.add(additional_building)
        
        # Registrations
        for registration in import_registrations(property_id, safe_get(api_data, 'registrations')):
            session.add(registration)
        
        # Related entities
        municipality = import_municipality(property_id, safe_get(api_data, 'municipality'))
        if municipality:
            session.add(municipality)
        
        province = import_province(property_id, safe_get(api_data, 'province'))
        if province:
            session.add(province)
        
        road = import_road(property_id, safe_get(api_data, 'road'))
        if road:
            session.add(road)
        
        zip_obj = import_zip(property_id, safe_get(api_data, 'zip'))
        if zip_obj:
            session.add(zip_obj)
        
        city = import_city(property_id, safe_get(api_data, 'city'))
        if city:
            session.add(city)
        
        place = import_place(property_id, safe_get(api_data, 'place'))
        if place:
            session.add(place)
        
        days_on_market = import_days_on_market(property_id, safe_get(api_data, 'daysOnMarket'))
        if days_on_market:
            session.add(days_on_market)
        
        session.commit()
        return True, f"imported_{distance:.1f}km"
        
    except Exception as e:
        session.rollback()
        return False, f"error: {str(e)[:100]}"


def bulk_import_from_api(limit=None, batch_size=50, delay=0.5, dry_run=False):
    """
    Import properties directly from API with filters
    
    Args:
        limit: Maximum number of properties to fetch from search (None = all)
        batch_size: Commit to database every N properties
        delay: Delay between API requests in seconds
        dry_run: If True, only check filters without importing
    """
    session = Session()
    
    print("=" * 80)
    print("BULK IMPORT FROM BOLIGSIDEN API")
    print("=" * 80)
    print()
    print(f"Filters:")
    print(f"  1. API Query: isOnMarket=true")
    print(f"  2. Client-side: Within {MAX_DISTANCE_KM}km of Copenhagen (55.6761°N, 12.5683°E)")
    print()
    print(f"Settings:")
    print(f"  Batch size: {batch_size} properties")
    print(f"  API delay: {delay}s between requests")
    print(f"  Search limit: {limit if limit else 'All available'}")
    print()
    
    if dry_run:
        print("DRY RUN MODE - No data will be imported")
        print()
    
    # Step 1: Fetch property IDs from search API
    print("-" * 80)
    print("STEP 1: Fetching property IDs from API")
    print("-" * 80)
    print()
    
    property_ids = fetch_properties_from_api(limit=limit, delay=delay)
    
    if not property_ids:
        print("No properties found!")
        session.close()
        return
    
    print()
    print(f"✓ Found {len(property_ids)} properties marked as 'on market'")
    print()
    
    # Step 2: Import each property with distance filter
    print("-" * 80)
    print("STEP 2: Importing properties with distance filter")
    print("-" * 80)
    print()
    
    stats = {
        'total': len(property_ids),
        'imported': 0,
        'too_far': 0,
        'no_coordinates': 0,
        'errors': 0,
        'api_errors': 0
    }
    
    start_time = time.time()
    
    for i, property_id in enumerate(property_ids, 1):
        try:
            if dry_run:
                # Just check distance filter
                url = f"{API_BASE_URL}/addresses/{property_id}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    api_data = response.json()
                    passes, distance = check_distance_filter(api_data)
                    
                    if passes:
                        stats['imported'] += 1
                    elif distance is None:
                        stats['no_coordinates'] += 1
                    else:
                        stats['too_far'] += 1
                else:
                    stats['api_errors'] += 1
            else:
                # Actually import
                success, reason = import_property_from_api(property_id, session)
                
                if success:
                    stats['imported'] += 1
                elif reason == "no_coordinates":
                    stats['no_coordinates'] += 1
                elif reason.startswith("too_far"):
                    stats['too_far'] += 1
                elif reason.startswith("api_error"):
                    stats['api_errors'] += 1
                elif reason.startswith("error"):
                    stats['errors'] += 1
            
            # Progress update
            if i % 10 == 0 or i == stats['total']:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                eta = (stats['total'] - i) / rate if rate > 0 else 0
                
                print(f"Progress: {i}/{stats['total']} ({i/stats['total']*100:.1f}%) | "
                      f"Imported: {stats['imported']} | "
                      f"Rate: {rate:.1f}/s | "
                      f"ETA: {eta/60:.1f}m")
            
            # Batch commit (only in non-dry-run mode)
            if not dry_run and i % batch_size == 0:
                session.commit()
            
            # Rate limiting
            if delay > 0:
                time.sleep(delay)
                
        except KeyboardInterrupt:
            print("\n\nInterrupted by user!")
            break
        except Exception as e:
            print(f"\nUnexpected error on property {property_id}: {str(e)}")
            stats['errors'] += 1
    
    if not dry_run:
        session.commit()
    
    session.close()
    
    # Final report
    elapsed_total = time.time() - start_time
    
    print()
    print("=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print()
    print(f"Total properties found (on market):  {stats['total']:>8}")
    print(f"Passed distance filter & imported:   {stats['imported']:>8} ({stats['imported']/stats['total']*100:.1f}%)")
    print()
    print("Filtered out:")
    print(f"  Too far (>{MAX_DISTANCE_KM}km):            {stats['too_far']:>8} ({stats['too_far']/stats['total']*100:.1f}%)")
    print(f"  No coordinates:                  {stats['no_coordinates']:>8} ({stats['no_coordinates']/stats['total']*100:.1f}%)")
    print(f"  API errors:                      {stats['api_errors']:>8} ({stats['api_errors']/stats['total']*100:.1f}%)")
    print(f"  Import errors:                   {stats['errors']:>8} ({stats['errors']/stats['total']*100:.1f}%)")
    print()
    print(f"Time elapsed: {elapsed_total/60:.1f} minutes")
    print(f"Average rate: {stats['total']/elapsed_total:.1f} properties/second")
    print()


def main():
    parser = argparse.ArgumentParser(description='Bulk import from Boligsiden API')
    parser.add_argument('--limit', type=int, help='Maximum number of properties to fetch from search')
    parser.add_argument('--batch-size', type=int, default=50, help='Commit every N properties (default: 50)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between API requests in seconds (default: 0.5)')
    parser.add_argument('--dry-run', action='store_true', help='Check filters without importing')
    
    args = parser.parse_args()
    
    bulk_import_from_api(
        limit=args.limit,
        batch_size=args.batch_size,
        delay=args.delay,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
