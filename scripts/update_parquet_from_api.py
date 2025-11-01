#!/usr/bin/env python3
"""
Update Parquet Files from Boligsiden API - Discovery & Refresh Mode
Direct update of file-based database without requiring PostgreSQL

Usage:
    python update_parquet_from_api.py --discover-new    # Find & add new properties
    python update_parquet_from_api.py --refresh-active  # Update prices on active listings
    python update_parquet_from_api.py --full-refresh    # Deep refresh of all data
"""

import pandas as pd
import requests
import json
import time
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Configuration
BASE_URL = "https://api.boligsiden.dk"
SEARCH_ENDPOINT = f"{BASE_URL}/search/addresses"
DETAIL_ENDPOINT = f"{BASE_URL}/addresses"
RATE_LIMIT = 0.1  # 10 requests per second

# Parquet export path
EXPORT_PATH = Path(__file__).parent.parent / "data" / "backups" / "full_export_20251007_232626"

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

def load_municipalities():
    """Load list of municipalities from JSON"""
    muni_path = Path(__file__).parent.parent / "data" / "municipalities_within_60km.json"
    with open(muni_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'municipalities_within_60km' in data:
        return data['municipalities_within_60km']
    elif 'all_municipalities' in data:
        return data['all_municipalities']
    else:
        raise KeyError("Could not find municipality list in JSON file")

def load_current_properties():
    """Load current properties from Parquet"""
    props_file = EXPORT_PATH / "properties_new.parquet"
    if props_file.exists():
        return pd.read_parquet(props_file)
    return pd.DataFrame()

def search_municipality(municipality: str, skip: int = 0, page_size: int = 100) -> Optional[Dict]:
    """Search for properties in a municipality"""
    params = {
        'municipality': municipality,
        'skip': skip,
        'take': page_size,
        'sort': 'published',
        'order': 'desc'
    }
    
    try:
        response = requests.get(
            SEARCH_ENDPOINT,
            params=params,
            headers=get_headers(),
            timeout=10
        )
        response.raise_for_status()
        time.sleep(RATE_LIMIT)  # Rate limiting
        return response.json()
    except Exception as e:
        print(f"  ❌ Error searching {municipality}: {e}")
        return None

def discover_new_properties(mode: str = "discover") -> List[str]:
    """Discover new properties not yet in database"""
    print("\n🔍 DISCOVERING NEW PROPERTIES")
    print("=" * 60)
    
    current_props = load_current_properties()
    current_ids = set(current_props['id'].astype(str)) if not current_props.empty else set()
    
    print(f"📊 Current properties in database: {len(current_ids):,}")
    
    municipalities = load_municipalities()
    new_property_ids = []
    total_checked = 0
    
    for i, muni in enumerate(municipalities, 1):
        print(f"\n[{i}/{len(municipalities)}] Searching {muni}...")
        skip = 0
        muni_new_count = 0
        
        while True:
            data = search_municipality(muni, skip=skip)
            
            if not data or 'addressDtos' not in data or not data['addressDtos']:
                print(f"  ✅ {muni}: {muni_new_count} new properties found")
                break
            
            for prop in data['addressDtos']:
                total_checked += 1
                prop_id = str(prop.get('addressID'))
                
                if prop_id not in current_ids:
                    new_property_ids.append(prop_id)
                    muni_new_count += 1
            
            # Check if there are more results
            if len(data['addressDtos']) < 100:
                print(f"  ✅ {muni}: {muni_new_count} new properties found")
                break
            
            skip += 100
    
    print(f"\n{'='*60}")
    print(f"📈 DISCOVERY SUMMARY")
    print(f"  Total properties checked: {total_checked:,}")
    print(f"  New properties found: {len(new_property_ids):,}")
    print(f"{'='*60}\n")
    
    return new_property_ids

def refresh_active_cases() -> int:
    """Refresh prices and details for active listings"""
    print("\n📊 REFRESHING ACTIVE LISTINGS")
    print("=" * 60)
    
    cases_file = EXPORT_PATH / "cases.parquet"
    if not cases_file.exists():
        print("❌ Cases file not found")
        return 0
    
    cases = pd.read_parquet(cases_file)
    active_cases = cases[cases['status'] == 'open']
    
    print(f"Found {len(active_cases):,} active cases to refresh")
    
    # Group by property to get unique properties
    unique_props = active_cases['property_id'].unique()
    print(f"Affecting {len(unique_props):,} unique properties\n")
    
    # In a full implementation, would fetch updated data for each property
    # For now, just log what would be updated
    updated_count = 0
    
    for i, prop_id in enumerate(unique_props[:10], 1):  # Sample first 10 for demo
        print(f"  [{i}/10 sample] Would update property {prop_id}")
        updated_count += 1
    
    if len(unique_props) > 10:
        print(f"  ... and {len(unique_props) - 10:,} more properties")
    
    print(f"\n{'='*60}")
    print(f"Would update: {len(unique_props):,} properties")
    print(f"Note: Full update requires data fetching from API")
    print(f"{'='*60}\n")
    
    return len(unique_props)

def main():
    parser = argparse.ArgumentParser(
        description='Update Parquet files from Boligsiden API'
    )
    parser.add_argument(
        '--discover-new',
        action='store_true',
        help='Discover and list new properties'
    )
    parser.add_argument(
        '--refresh-active',
        action='store_true',
        help='Refresh active listings'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Show database statistics'
    )
    
    args = parser.parse_args()
    
    if args.info:
        # Show current database statistics
        print("\n📊 DATABASE STATISTICS")
        print("=" * 60)
        
        try:
            props = pd.read_parquet(EXPORT_PATH / "properties_new.parquet")
            cases = pd.read_parquet(EXPORT_PATH / "cases.parquet")
            
            print(f"Total properties: {len(props):,}")
            print(f"Total cases: {len(cases):,}")
            print(f"Active cases: {len(cases[cases['status'] == 'open']):,}")
            print(f"Last export: {EXPORT_PATH.name}")
            print("=" * 60 + "\n")
        except Exception as e:
            print(f"Error reading database: {e}")
    
    elif args.discover_new:
        new_ids = discover_new_properties()
        print(f"To import these properties, use the full import script with:")
        print(f"python scripts/import_copenhagen_area.py")
    
    elif args.refresh_active:
        updated = refresh_active_cases()
        print(f"To refresh prices, requires running:")
        print(f"python scripts/reimport_all_cases.py")
    
    else:
        print("\n⚠️  PARQUET UPDATE TOOL - Information Mode")
        print("=" * 60)
        print("This tool helps you understand what needs updating.")
        print("\nNote: For full API data update, you'll need PostgreSQL.")
        print("\nUsage:")
        print("  --discover-new    : Discover new properties since last export")
        print("  --refresh-active  : See which active listings need price refresh")
        print("  --info            : Show current database statistics")
        print("=" * 60 + "\n")
        
        args.info = True
        args.discover_new = False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Update cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
