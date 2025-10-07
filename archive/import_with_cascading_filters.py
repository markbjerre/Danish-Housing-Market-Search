"""
Optimized import using cascading filters to reduce API calls
Based on notebook framework but adapted for current market (isOnMarket=True)
"""

import requests
import json
import time
import random
from datetime import datetime

BASE_URL = "https://api.boligsiden.dk/search/addresses"

# Property types to iterate through
PROPERTY_TYPES = ['villa', 'condo', 'terraced house']

# Price ranges (in DKK) - for breaking down large result sets
PRICE_RANGES = [
    (0, 2000000),
    (2000000, 4000000),
    (4000000, 6000000),
    (6000000, 8000000),
    (8000000, 10000000),
    (10000000, 15000000),
    (15000000, 25000000),
    (25000000, None)  # No upper limit
]

# Area ranges (in sqm) - for further breakdown if needed
AREA_RANGES = [
    (0, 50),
    (50, 80),
    (80, 120),
    (120, 180),
    (180, 250),
    (250, None)  # No upper limit
]

def get_user_agent():
    """Random user agent to avoid rate limiting"""
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
        'user-agent': get_user_agent(),
    }

def check_total_hits(municipality, property_type=None, price_min=None, price_max=None, area_min=None, area_max=None):
    """Check how many results a query would return"""
    params = {
        'municipalities': municipality,
        'per_page': '1',
        'page': '1'
    }
    
    if property_type:
        params['addressTypes'] = property_type
    if price_min is not None:
        params['priceMin'] = str(price_min)
    if price_max is not None:
        params['priceMax'] = str(price_max)
    if area_min is not None:
        params['areaMin'] = str(area_min)
    if area_max is not None:
        params['areaMax'] = str(area_max)
    
    try:
        response = requests.get(BASE_URL, params=params, headers=get_headers(), timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('totalHits', 0)
    except Exception as e:
        print(f"   Error checking hits: {e}")
    
    return 0

def scan_segment(municipality, property_type=None, price_min=None, price_max=None, area_min=None, area_max=None, max_pages=500):
    """Scan a filtered segment of properties"""
    params = {
        'municipalities': municipality,
        'per_page': '50',
        'page': '1',
        'sortBy': 'address'
    }
    
    if property_type:
        params['addressTypes'] = property_type
    if price_min is not None:
        params['priceMin'] = str(price_min)
    if price_max is not None:
        params['priceMax'] = str(price_max)
    if area_min is not None:
        params['areaMin'] = str(area_min)
    if area_max is not None:
        params['areaMax'] = str(area_max)
    
    on_market_properties = []
    page = 1
    
    while page <= max_pages:
        params['page'] = str(page)
        
        try:
            response = requests.get(BASE_URL, params=params, headers=get_headers(), timeout=10)
            
            if response.status_code != 200:
                break
            
            data = response.json()
            addresses = data.get('addresses', [])
            
            if not addresses:
                break
            
            # Filter for isOnMarket=True
            for addr in addresses:
                if addr.get('isOnMarket') is True:
                    on_market_properties.append(addr.get('addressID'))
            
            page += 1
            time.sleep(0.1)  # Rate limiting
            
        except Exception as e:
            print(f"   Error on page {page}: {e}")
            break
    
    return on_market_properties

def process_municipality_with_cascading_filters(municipality):
    """Process one municipality using cascading filters"""
    print(f"\n{'='*100}")
    print(f"📍 Processing: {municipality}")
    print(f"{'='*100}\n")
    
    all_on_market = []
    
    # Level 1: Check if we can process without filtering
    total_hits = check_total_hits(municipality)
    print(f"Total properties in {municipality}: {total_hits:,}")
    
    if total_hits <= 10000:
        print(f"✓ Under 10k limit - scanning all...")
        properties = scan_segment(municipality)
        all_on_market.extend(properties)
        print(f"   Found {len(properties)} properties with isOnMarket=True")
    else:
        # Level 2: Filter by property type
        print(f"✗ Over 10k limit - applying property type filters...")
        
        for prop_type in PROPERTY_TYPES:
            type_hits = check_total_hits(municipality, property_type=prop_type)
            print(f"\n   {prop_type}: {type_hits:,} properties")
            
            if type_hits <= 10000:
                print(f"      ✓ Under 10k - scanning...")
                properties = scan_segment(municipality, property_type=prop_type)
                all_on_market.extend(properties)
                print(f"      Found {len(properties)} with isOnMarket=True")
            else:
                # Level 3: Add price ranges
                print(f"      ✗ Over 10k - applying price filters...")
                
                for price_min, price_max in PRICE_RANGES:
                    price_label = f"{price_min//1000}k-{price_max//1000 if price_max else 'max'}k"
                    price_hits = check_total_hits(municipality, prop_type, price_min, price_max)
                    
                    if price_hits > 0:
                        print(f"         {price_label}: {price_hits:,} properties", end="")
                        
                        if price_hits <= 10000:
                            print(f" - scanning...")
                            properties = scan_segment(municipality, prop_type, price_min, price_max)
                            all_on_market.extend(properties)
                            print(f"            Found {len(properties)} with isOnMarket=True")
                        else:
                            print(f" - too many, skipping (would need area filters)")
                    
                    time.sleep(0.2)  # Rate limiting
    
    print(f"\n{'='*100}")
    print(f"✅ {municipality} complete: Found {len(all_on_market)} properties currently on market")
    print(f"{'='*100}\n")
    
    return all_on_market

# Test with København
if __name__ == "__main__":
    print("="*100)
    print("OPTIMIZED IMPORT WITH CASCADING FILTERS")
    print("="*100)
    
    # Test with single municipality
    properties = process_municipality_with_cascading_filters("København")
    
    print(f"\n\n{'='*100}")
    print(f"FINAL RESULT")
    print(f"{'='*100}")
    print(f"Total properties found with isOnMarket=True: {len(properties)}")
    print(f"Unique property IDs: {len(set(properties))}")
