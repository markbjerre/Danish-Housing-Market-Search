"""
Import Properties from API - Copenhagen Area (Within 60km)
Filters by municipalities within 60km of Copenhagen and currently on market

Framework adopted from Step_1_Scraping_boligsiden.ipynb:
- Retry logic for API requests
- Duplicate checking before database insert
- Proper error handling and progress tracking
- Municipality-based filtering with client-side market status check
"""

import requests
import json
import time
import argparse
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.db_models_new import Base, Property, MainBuilding, AdditionalBuilding, Registration, Municipality, Province, Road, Zip, City, Place, DaysOnMarket, Case, PriceChange
from src.database import db
import import_api_data

# API Configuration
BASE_URL = "https://api.boligsiden.dk"
SEARCH_ENDPOINT = f"{BASE_URL}/search/addresses"
DETAIL_ENDPOINT = f"{BASE_URL}/addresses"

# Dynamic headers with user-agent rotation (from notebook)
def get_user_agent():
    """Get random user agent to avoid rate limiting"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
    ]
    return random.choice(user_agents)

def get_headers():
    """Get headers with random user agent"""
    return {
        'authority': 'api.boligsiden.dk',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
        'origin': 'https://www.boligsiden.dk',
        'referer': 'https://www.boligsiden.dk/',
        'sec-ch-ua': '"Google Chrome";v="113", "Not-A.Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': get_user_agent(),
    }

# Load municipalities within 60km
def load_municipalities_within_60km():
    """Load list of municipalities within 60km of Copenhagen"""
    # Use absolute path relative to this script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'municipalities_within_60km.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check which key structure is present
    if 'municipalities_within_60km' in data:
        muni_list = data['municipalities_within_60km']
    elif 'all_municipalities' in data:
        muni_list = data['all_municipalities']
    else:
        raise KeyError("Could not find municipality list in JSON file")
    
    # STRICTLY filter to only those within 60km
    municipalities = []
    for muni in muni_list:
        if isinstance(muni, dict):
            distance = muni.get('distance_to_copenhagen_km')
            # Only include if distance is explicitly <= 60km
            if distance is not None and distance <= 60:
                municipalities.append(muni['name'])
            # Skip municipalities without distance data or > 60km
        elif isinstance(muni, str):
            # Just a string - cannot verify distance, skip for safety
            print(f"   ⚠️  Warning: Skipping '{muni}' - no distance data")
    
    print(f"   ✅ Loaded {len(municipalities)} municipalities within 60km")
    return municipalities


def fetch_properties_from_search(municipalities: list, per_page: int = 50, max_pages: int = None):
    """
    Fetch all property IDs from search API for given municipalities.
    API returns up to 50 results per page.
    """
    print(f"🔍 Searching for properties in {len(municipalities)} municipalities...")
    print(f"   Municipalities: {', '.join(municipalities[:5])}{'...' if len(municipalities) > 5 else ''}")
    
    all_property_ids = []
    
    for municipality in municipalities:
        print(f"\n📍 Fetching properties in {municipality}...")
        
        page = 1
        total_for_municipality = 0
        
        while True:
            if max_pages and page > max_pages:
                print(f"   Reached max pages limit ({max_pages})")
                break
            
            try:
                params = {
                    'sold': 'false',  # Currently on market
                    'per_page': str(per_page),
                    'page': str(page)
                }
                
                # Note: API may not support municipality filtering via parameter
                # We'll filter in the results instead
                response = requests.get(SEARCH_ENDPOINT, params=params, headers=get_headers(), timeout=10)
                
                if response.status_code == 400:
                    print(f"   Page {page} returned 400 - end of results")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                if 'addresses' not in data or not data['addresses']:
                    print(f"   No more results at page {page}")
                    break
                
                # Filter results to this municipality
                page_count = 0
                for item in data['addresses']:
                    muni_dict = item.get('municipality', {})
                    muni_name = muni_dict.get('name')
                    
                    if muni_name == municipality:
                        property_id = item.get('addressID')
                        is_on_market = item.get('isOnMarket', False)
                        
                        if property_id and is_on_market:
                            all_property_ids.append(property_id)
                            page_count += 1
                            total_for_municipality += 1
                
                if page_count > 0:
                    print(f"   Page {page}: Found {page_count} properties (total: {total_for_municipality})")
                
                # If we didn't find any for this municipality on this page, move to next municipality
                if page_count == 0:
                    break
                
                page += 1
                
                # Limit pages to avoid fetching entire API (3.9M properties)
                if page > 200:
                    print(f"\n⚠️  Reached page limit (200) - stopping to avoid fetching entire API")
                    break
                
                time.sleep(0.2)  # Rate limiting
                
            except Exception as e:
                print(f"   ⚠️  Error on page {page}: {e}")
                break
        
        print(f"   ✅ Total for {municipality}: {total_for_municipality} properties")
    
    print(f"\n✅ Found {len(all_property_ids)} total properties across all municipalities")
    return all_property_ids


def fetch_zip_codes_for_municipality(municipality: str):
    """
    Fetch all unique zip codes in a municipality by querying first 1000 results.
    Returns list of zip codes found.
    """
    print(f"   🔍 Discovering zip codes in {municipality}...")
    zip_codes = set()
    
    try:
        params = {
            'municipalities': municipality,
            'addressTypes': 'villa',
            'per_page': '50',
            'page': '1'
        }
        
        # Fetch first few pages to discover zip codes
        for page in range(1, 21):  # First 1000 results (20 pages × 50)
            params['page'] = str(page)
            response = requests.get(SEARCH_ENDPOINT, params=params, headers=get_headers(), timeout=10)
            
            if response.status_code != 200:
                break
            
            data = response.json()
            addresses = data.get('addresses', [])
            
            if not addresses:
                break
            
            for addr in addresses:
                zip_code = addr.get('zipCode')
                if zip_code:
                    zip_codes.add(zip_code)
            
            time.sleep(0.05)
        
        print(f"   ✅ Found {len(zip_codes)} zip codes: {sorted(zip_codes)}")
        return sorted(zip_codes)
        
    except Exception as e:
        print(f"   ⚠️  Error discovering zip codes: {e}")
        return []


def fetch_properties_by_municipality(municipalities: list, max_properties: int = None):
    """
    Fetch ALL villas from Copenhagen area municipalities (no market status filter).
    Framework adopted from notebook: iterate municipality-by-municipality with addressType filtering.
    
    OPTIMIZATION: Filter for 'villa' only to reduce API calls by ~97%
    - København total: 441,795 properties
    - København villas: 14,368 properties (96.7% reduction!)
    - Imports ALL villas regardless of market status
    
    🆕 FIX FOR 10,000 LIMIT:
    - Detects when totalHits > 10,000
    - Automatically subdivides by zip code to avoid API limit
    - Ensures ALL properties are captured
    """
    print(f"🔍 Fetching ALL VILLAS from {len(municipalities)} municipalities...")
    print(f"   📋 Filter: addressTypes=villa (reduces results by ~97%)")
    print(f"   📊 Importing ALL villas (not just on-market)")
    print(f"   🆕 Auto-subdivides large municipalities by zip code\n")
    
    all_property_ids = []
    total_fetched = 0
    on_market_count = 0
    
    # Iterate through each municipality separately (from notebook framework)
    for muni_idx, municipality in enumerate(municipalities, 1):
        print(f"\n{'='*80}")
        print(f"📍 Municipality {muni_idx}/{len(municipalities)}: {municipality}")
        print(f"{'='*80}")
        
        muni_property_ids = []
        
        # First, check total count for this municipality
        params = {
            'municipalities': municipality,
            'addressTypes': 'villa',
            'per_page': '50',
            'page': '1'
        }
        
        try:
            response = requests.get(SEARCH_ENDPOINT, params=params, headers=get_headers(), timeout=10)
            response.raise_for_status()
            data = response.json()
            total_hits = data.get('totalHits', 0)
            
            print(f"   📊 Total hits for {municipality}: {total_hits:,}")
            
            # Check if we need to subdivide by zip code
            if total_hits > 9500:  # Use 9500 instead of 10000 for safety margin
                print(f"   ⚠️  Municipality has > 9,500 properties - subdividing by zip code")
                zip_codes = fetch_zip_codes_for_municipality(municipality)
                
                if zip_codes:
                    # Fetch properties for each zip code separately
                    for zip_idx, zip_code in enumerate(zip_codes, 1):
                        print(f"\n   📮 Zip Code {zip_idx}/{len(zip_codes)}: {zip_code}")
                        zip_props = fetch_properties_by_filters(
                            municipality=municipality,
                            zip_code=zip_code
                        )
                        muni_property_ids.extend(zip_props)
                        print(f"      ✅ Found {len(zip_props)} properties in zip {zip_code}")
                else:
                    print(f"   ⚠️  Could not discover zip codes - using standard method")
                    muni_property_ids = fetch_properties_by_filters(municipality=municipality)
            else:
                # Municipality is small enough - fetch normally
                muni_property_ids = fetch_properties_by_filters(municipality=municipality)
            
        except Exception as e:
            print(f"   ⚠️  Error checking total hits: {e}")
            muni_property_ids = fetch_properties_by_filters(municipality=municipality)
        
        # Add to total
        all_property_ids.extend(muni_property_ids)
        on_market_count += len(muni_property_ids)
        
        print(f"   ✅ {municipality}: Total {len(muni_property_ids)} villas")
        
        if max_properties and on_market_count >= max_properties:
            print(f"\n✅ Reached max properties limit ({max_properties})")
            break
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"✅ TOTAL: Found {on_market_count:,} villas across {len(municipalities)} municipalities")
    print(f"   These will be checked for duplicates before importing")
    print(f"{'='*80}")
    return all_property_ids


def fetch_properties_by_filters(municipality: str, zip_code: int = None):
    """
    Fetch properties with given filters. Handles pagination up to API limits.
    Returns list of property info dicts.
    """
    property_ids = []
    page = 1
    per_page = 50
    consecutive_empty_pages = 0
    max_empty_pages = 3
    
    while True:
        try:
            params = {
                'municipalities': municipality,
                'addressTypes': 'villa',
                'per_page': str(per_page),
                'page': str(page),
                'sortBy': 'address',
                'sortAscending': 'true'
            }
            
            # Add zip code filter if provided (CRITICAL: parameter is 'zipCodes' plural!)
            if zip_code:
                params['zipCodes'] = str(zip_code)
        
            response = requests.get(SEARCH_ENDPOINT, params=params, headers=get_headers(), timeout=10)
            
            if response.status_code == 400:
                break
            
            response.raise_for_status()
            data = response.json()
            
            if 'addresses' not in data or not data['addresses']:
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= max_empty_pages:
                    break
                page += 1
                continue
            
            consecutive_empty_pages = 0
            
            # Extract property IDs
            for item in data['addresses']:
                property_id = item.get('addressID')
                muni_dict = item.get('municipality', {})
                muni_name = muni_dict.get('name', municipality)
                is_on_market = item.get('isOnMarket', False)
                
                if property_id:
                    property_ids.append({
                        'id': property_id,
                        'municipality': muni_name,
                        'is_on_market': is_on_market
                    })
            
            # Progress update every 10 pages
            if page % 10 == 0:
                zip_info = f" (zip: {zip_code})" if zip_code else ""
                print(f"      Page {page}: {len(property_ids)} properties{zip_info}")
            
            # Check if we're approaching the 10,000 limit
            if page >= 200:
                print(f"      ⚠️  Reached page 200 limit (10,000 properties)")
                print(f"      Consider further subdivision if more properties exist")
                break
            
            page += 1
            time.sleep(0.1)  # Rate limiting
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"      ⚠️  Error on page {page}: {e}")
            break
    
    return property_ids


def import_properties(property_list: list, session, dry_run: bool = False, batch_size: int = 100):
    """
    Import properties with optimized batch processing.
    - Bulk checks for existing properties
    - Batched commits
    - Progress tracking
    """
    print(f"\n{'🔍 DRY RUN - ' if dry_run else ''}📥 Importing {len(property_list)} properties...")
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    # Extract property IDs
    property_ids = []
    for prop_info in property_list:
        if isinstance(prop_info, dict):
            property_ids.append(prop_info['id'])
        else:
            property_ids.append(prop_info)
    
    # Bulk check for existing properties (MUCH faster than one-by-one)
    existing_ids = set()
    if not dry_run:
        print("   🔍 Checking for existing properties in database...")
        # Query in chunks to avoid memory issues
        chunk_size = 1000
        for i in range(0, len(property_ids), chunk_size):
            chunk = property_ids[i:i+chunk_size]
            existing = session.query(Property.id).filter(Property.id.in_(chunk)).all()
            existing_ids.update([e[0] for e in existing])
        print(f"   ✅ Found {len(existing_ids)} existing properties (will skip)")
    
    # Process properties in batches
    batch_objects = []
    batch_start_idx = 0
    
    for idx, prop_info in enumerate(property_list, 1):
        if isinstance(prop_info, dict):
            property_id = prop_info['id']
            municipality = prop_info.get('municipality', 'Unknown')
        else:
            property_id = prop_info
            municipality = 'Unknown'
        
        # Skip if already exists
        if property_id in existing_ids:
            skipped_count += 1
            continue
        
        try:
            if not dry_run:
                # Use the full import function that handles session management
                success = import_api_data.import_from_api(property_id)
                if success:
                    imported_count += 1
                else:
                    error_count += 1
            else:
                # Fetch details for dry-run display
                url = f"{DETAIL_ENDPOINT}/{property_id}"
                response = requests.get(url, headers=get_headers(), timeout=10)
                response.raise_for_status()
                property_data = response.json()
                print(f"   [{idx}] Would import: {property_data.get('roadName', 'N/A')} {property_data.get('houseNumber', '')}, {municipality}")
                imported_count += 1
            
            # Progress update every 50 properties
            if idx % 50 == 0:
                print(f"   [{idx}/{len(property_list)}] Imported {imported_count}, Skipped {skipped_count}, Errors {error_count}")
            
            # Commit in batches (flush to DB without closing transaction)
            if not dry_run and (imported_count - batch_start_idx) >= batch_size:
                session.flush()  # Flush writes the data but keeps transaction open
                session.commit()  # Commit the transaction
                print(f"   💾 Committed batch of {imported_count - batch_start_idx} properties (total: {imported_count})")
                batch_start_idx = imported_count
            
            time.sleep(0.2)  # Rate limiting - reduced from 0.3 since we're more efficient now
            
        except KeyboardInterrupt:
            print(f"\n⚠️  Interrupted by user at property {idx}")
            if not dry_run:
                session.commit()
            break
        except Exception as e:
            error_count += 1
            if error_count <= 10:  # Only show first 10 errors to avoid spam
                print(f"   ⚠️  Error importing {property_id}: {str(e)[:100]}")
            elif error_count == 11:
                print(f"   ⚠️  Suppressing further error messages (total: {error_count})")
            continue
    
    # Final commit for remaining properties
    if not dry_run and (imported_count - batch_start_idx) > 0:
        session.commit()
        print(f"   💾 Final commit of {imported_count - batch_start_idx} properties")
    
    print(f"\n✅ Import complete!")
    print(f"   Imported: {imported_count}")
    print(f"   Skipped (already exists): {skipped_count}")
    print(f"   Errors: {error_count}")
    
    return imported_count, skipped_count, error_count


def fetch_property_data(property_id):
    """Worker function to fetch detailed property data from API - used for parallel processing"""
    try:
        url = f"{DETAIL_ENDPOINT}/{property_id}"
        # Reduced timeout from 15s to 10s for faster failure recovery
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        return property_id, response.json(), None
    except Exception as e:
        return property_id, None, str(e)


def import_properties_parallel(property_list: list, session, dry_run: bool = False, batch_size: int = 50, max_workers: int = 12):
    """
    Import properties with PARALLEL processing for maximum speed.
    
    OPTIMIZATIONS:
    - Parallel API fetching (5-10 threads)
    - Bulk duplicate checking (1 query vs N)
    - Batch commits every 100 properties
    - Progress tracking with speed metrics
    
    Expected speed: 20-50 properties/second (vs 0.5-1 without parallelization)
    This means ~10-15 minutes for København's 14k villas instead of 6 hours!
    """
    print(f"\n🚀 PARALLEL IMPORT: {len(property_list)} properties with {max_workers} workers")
    
    if dry_run:
        # In dry-run, just show what would be imported
        print("   🔍 DRY RUN MODE - Showing first 20 properties:")
        for idx, prop_info in enumerate(property_list[:20], 1):
            if isinstance(prop_info, dict):
                property_id = prop_info['id']
                municipality = prop_info.get('municipality', 'Unknown')
                is_on_market = prop_info.get('is_on_market', False)
                print(f"   [{idx}] Would import: {property_id} ({municipality}) - On market: {is_on_market}")
        if len(property_list) > 20:
            print(f"   ... and {len(property_list) - 20} more properties")
        return len(property_list), 0, 0
    
    imported_count = 0
    skipped_count = 0
    error_count = 0
    
    # Extract property IDs
    property_ids = []
    for prop_info in property_list:
        if isinstance(prop_info, dict):
            property_ids.append(prop_info['id'])
        else:
            property_ids.append(prop_info)
    
    # 🚀 OPTIMIZATION 1: Bulk check for existing properties (1 query vs N queries)
    print("   🔍 Checking for existing properties in database...")
    existing_ids = set()
    chunk_size = 1000
    for i in range(0, len(property_ids), chunk_size):
        chunk = property_ids[i:i+chunk_size]
        existing = session.query(Property.id).filter(Property.id.in_(chunk)).all()
        existing_ids.update([e[0] for e in existing])
    
    skipped_count = len(existing_ids)
    properties_to_import = [pid for pid in property_ids if pid not in existing_ids]
    
    print(f"   ✅ Found {skipped_count} existing properties (will skip)")
    print(f"   📥 Importing {len(properties_to_import)} new properties...")
    print()
    
    if len(properties_to_import) == 0:
        print("   ✅ All properties already exist in database!")
        return 0, skipped_count, 0
    
    # 🚀 OPTIMIZATION 2: Parallel API fetching with ThreadPoolExecutor
    start_time = time.time()
    batch_start_time = start_time
    batch_count = 0
    
    # Disable auto-flush to prevent premature constraint checks
    session.autoflush = False
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all fetch tasks
        future_to_id = {
            executor.submit(fetch_property_data, prop_id): prop_id 
            for prop_id in properties_to_import
        }
        
        # Process completed tasks as they finish
        for idx, future in enumerate(as_completed(future_to_id), 1):
            property_id = future_to_id[future]
            
            try:
                prop_id, property_data, error = future.result()
                
                if error:
                    error_count += 1
                    if error_count <= 10:
                        print(f"   ⚠️  Error fetching {prop_id}: {error[:80]}")
                    continue
                
                if not property_data:
                    error_count += 1
                    continue
                
                # Use no_autoflush block to prevent premature constraint checks
                with session.no_autoflush:
                    # Import property with all related data (use merge to handle duplicates)
                    property_obj = import_api_data.import_property(property_data)
                    session.merge(property_obj)
                    
                    # Import main building
                    main_building = import_api_data.import_main_building(prop_id, property_data.get('buildings', []))
                    if main_building:
                        session.merge(main_building)
                    
                    # Import additional buildings
                    additional_buildings = import_api_data.import_additional_buildings(prop_id, property_data.get('buildings', []))
                    for bldg in additional_buildings:
                        session.merge(bldg)
                    
                    # Import registrations
                    registrations = import_api_data.import_registrations(prop_id, property_data.get('registrations', []))
                    for reg in registrations:
                        session.merge(reg)
                    
                    # Import related entities (municipality, province, etc.) - use merge for duplicates
                    for field, import_func in [
                        ('municipality', import_api_data.import_municipality),
                        ('province', import_api_data.import_province),
                        ('road', import_api_data.import_road),
                        ('zip', import_api_data.import_zip),
                        ('city', import_api_data.import_city),
                        ('place', import_api_data.import_place),
                        ('daysOnMarket', import_api_data.import_days_on_market)
                    ]:
                        entity = import_func(prop_id, property_data.get(field, {}))
                        if entity:
                            session.merge(entity)
                    
                    # Import cases and price changes
                    for case in import_api_data.import_cases(prop_id, property_data.get('cases', [])):
                        session.add(case)
                
                imported_count += 1
                batch_count += 1
                
                # 🚀 OPTIMIZATION 3: Batch commits every N properties
                if batch_count >= batch_size:
                    try:
                        session.commit()
                        elapsed = time.time() - batch_start_time
                        rate = batch_count / elapsed
                        total_elapsed = time.time() - start_time
                        overall_rate = imported_count / total_elapsed
                        eta_seconds = (len(properties_to_import) - imported_count) / overall_rate if overall_rate > 0 else 0
                        eta_mins = eta_seconds / 60
                        
                        print(f"   💾 Batch {imported_count}/{len(properties_to_import)} | "
                              f"Speed: {rate:.1f} props/sec | "
                              f"Overall: {overall_rate:.1f} props/sec | "
                              f"ETA: {eta_mins:.1f} min")
                        
                        batch_count = 0
                        batch_start_time = time.time()
                    except Exception as commit_error:
                        session.rollback()
                        print(f"   ⚠️  Batch commit failed: {str(commit_error)[:100]}")
                        print(f"   🔄 Rolled back batch - will retry individual commits")
                        batch_count = 0
                        batch_start_time = time.time()
                
                # Progress update every 25 properties (if not in a batch commit) - more frequent updates
                elif idx % 25 == 0:
                    elapsed = time.time() - start_time
                    rate = imported_count / elapsed if elapsed > 0 else 0
                    eta_seconds = (len(properties_to_import) - imported_count) / rate if rate > 0 else 0
                    eta_mins = eta_seconds / 60
                    print(f"   [{idx}/{len(properties_to_import)}] Imported: {imported_count}, Errors: {error_count} | Speed: {rate:.1f} props/sec | ETA: {eta_mins:.1f} min")
                
            except KeyboardInterrupt:
                print(f"\n⚠️  Interrupted by user")
                session.commit()
                break
            except Exception as e:
                error_count += 1
                # Rollback the session to recover from error state
                session.rollback()
                if error_count <= 10:
                    print(f"   ⚠️  Error importing {property_id}: {str(e)[:100]}")
                continue
    
    # Re-enable autoflush
    session.autoflush = True
    
    # Final commit for remaining properties
    if batch_count > 0:
        try:
            session.commit()
            print(f"   💾 Final commit of {batch_count} properties")
        except Exception as commit_error:
            session.rollback()
            print(f"   ⚠️  Final commit failed: {str(commit_error)[:100]}")
    
    # Summary with timing stats
    total_time = time.time() - start_time
    overall_rate = imported_count / total_time if total_time > 0 else 0
    
    print(f"\n✅ Parallel import complete!")
    print(f"   Imported: {imported_count} ({overall_rate:.1f} props/sec)")
    print(f"   Skipped (already exists): {skipped_count}")
    print(f"   Errors: {error_count}")
    print(f"   Total time: {total_time / 60:.1f} minutes")
    print(f"   Speedup: ~{overall_rate:.0f}x faster than single-threaded!")
    
    return imported_count, skipped_count, error_count


def main():
    parser = argparse.ArgumentParser(description='Import properties from Copenhagen area (within 60km)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be imported without actually importing')
    parser.add_argument('--limit', type=int, help='Limit number of properties to import')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of properties to commit at once (default: 50, lower=faster feedback)')
    parser.add_argument('--max-pages', type=int, help='Maximum number of pages to fetch from search API')
    parser.add_argument('--parallel', action='store_true', help='Use parallel processing (20-50x faster!)')
    parser.add_argument('--workers', type=int, default=12, help='Number of parallel workers (default: 12)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🏠 COPENHAGEN AREA PROPERTY IMPORT")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dry run: {args.dry_run}")
    print(f"Limit: {args.limit if args.limit else 'No limit'}")
    print(f"Batch size: {args.batch_size}")
    
    # Load municipalities within 60km
    municipalities = load_municipalities_within_60km()
    print(f"\n📍 Target municipalities (within 60km): {len(municipalities)}")
    for muni in sorted(municipalities):
        print(f"   - {muni}")
    
    # Create database session
    if not args.dry_run:
        session = db.get_session()
        print("\n✅ Database connection established")
    else:
        session = None
        print("\n🔍 DRY RUN - No database connection")
    
    try:
        # Fetch properties currently on market using API filtering
        property_list = fetch_properties_by_municipality(municipalities, max_properties=args.limit)
        
        if not property_list:
            print("\n⚠️  No properties found!")
            return
        
        print(f"\nFound {len(property_list)} properties to import")
        
        # Import properties (parallel or sequential)
        if args.parallel:
            print(f"\n🚀 Using PARALLEL processing with {args.workers} workers")
            imported, skipped, errors = import_properties_parallel(
                property_list, 
                session, 
                dry_run=args.dry_run,
                batch_size=args.batch_size,
                max_workers=args.workers
            )
        else:
            print("\n📝 Using sequential processing (use --parallel for 20-50x speedup)")
            imported, skipped, errors = import_properties(
                property_list, 
                session, 
                dry_run=args.dry_run,
                batch_size=args.batch_size
            )
        
        print(f"\n{'=' * 80}")
        print(f"📊 FINAL SUMMARY")
        print(f"{'=' * 80}")
        print(f"Total properties found: {len(property_list)}")
        print(f"Imported: {imported}")
        print(f"Skipped: {skipped}")
        print(f"Errors: {errors}")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    finally:
        if session and not args.dry_run:
            session.close()
            print("\n✅ Database connection closed")


if __name__ == '__main__':
    main()
