"""
Discover All Municipalities from Boligsiden API
Performs large-scale random sampling to:
1. Discover ALL municipality names and their exact API spellings
2. Get representative coordinates for each municipality
3. Calculate distance from Copenhagen for each
4. Identify municipalities within 60km radius
"""

import requests
import json
import random
import time
import math
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Copenhagen City Hall coordinates
COPENHAGEN_LAT = 55.6761
COPENHAGEN_LON = 12.5683

# API Configuration
BASE_URL = "https://api.boligsiden.dk"
SEARCH_ENDPOINT = f"{BASE_URL}/search/addresses"
DETAIL_ENDPOINT = f"{BASE_URL}/addresses"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.boligsiden.dk/',
    'Origin': 'https://www.boligsiden.dk',
}

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two coordinates using Haversine formula"""
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def fetch_property_ids_random(total_samples: int = 10000) -> List[Tuple[str, str]]:
    """
    Fetch property IDs randomly from different pages and sort methods.
    Returns list of (property_id, municipality_name) tuples.
    """
    print(f"🔍 Fetching {total_samples} random property samples from API...")
    
    # Different sort strategies to get diverse samples
    sort_strategies = [
        {'sortBy': 'address', 'sortAscending': 'true'},
        {'sortBy': 'address', 'sortAscending': 'false'},
        {'sortBy': 'soldDate', 'sortAscending': 'true'},
        {'sortBy': 'soldDate', 'sortAscending': 'false'},
        {'sortBy': 'price', 'sortAscending': 'true'},
        {'sortBy': 'price', 'sortAscending': 'false'},
    ]
    
    property_data = []
    properties_per_strategy = total_samples // len(sort_strategies)
    
    for idx, strategy in enumerate(sort_strategies):
        print(f"\n📊 Strategy {idx+1}/{len(sort_strategies)}: sortBy={strategy['sortBy']}, ascending={strategy['sortAscending']}")
        
        # For each strategy, sample from early pages (1-100) to avoid pagination limits
        # Use different starting points and steps to get diversity
        pages_to_try = list(range(1, 101, 2))  # Pages 1, 3, 5, ..., 99
        if idx >= 3:
            # For second half of strategies, use even pages
            pages_to_try = list(range(2, 101, 2))  # Pages 2, 4, 6, ..., 100
        
        # Shuffle to randomize
        random.shuffle(pages_to_try)
        
        collected_this_strategy = 0
        target_for_strategy = properties_per_strategy
        
        for page in pages_to_try:
            if collected_this_strategy >= target_for_strategy:
                break
                
            try:
                params = {
                    'sold': 'false',
                    'per_page': '20',
                    'page': str(page),
                    **strategy
                }
                
                response = requests.get(SEARCH_ENDPOINT, params=params, headers=HEADERS, timeout=10)
                
                if response.status_code == 400:
                    # Page out of range, skip
                    continue
                    
                response.raise_for_status()
                data = response.json()
                
                if 'results' in data:
                    for item in data['results']:
                        if 'id' in item and 'municipality' in item:
                            municipality = item['municipality']
                            if municipality:  # Skip if None
                                property_data.append((item['id'], municipality))
                                collected_this_strategy += 1
                                
                                if len(property_data) >= total_samples:
                                    print(f"✅ Reached {total_samples} samples!")
                                    return property_data
                
                # Progress update
                if len(property_data) % 500 == 0 and len(property_data) > 0:
                    print(f"   Collected {len(property_data)} samples so far...")
                
                # Respectful delay
                time.sleep(0.2)
                
            except KeyboardInterrupt:
                print(f"\n⚠️  Interrupted by user")
                return property_data
            except Exception as e:
                if "400" not in str(e):  # Don't spam 400 errors
                    print(f"⚠️  Error on page {page}: {e}")
                continue
        
        print(f"   Collected {collected_this_strategy} samples with this strategy")
    
    print(f"✅ Collected {len(property_data)} total samples")
    return property_data


def get_property_coordinates(property_id: str) -> Tuple[float, float] | None:
    """Fetch full property details to get coordinates"""
    try:
        url = f"{DETAIL_ENDPOINT}/{property_id}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        lat = data.get('lat')
        lon = data.get('lon')
        
        if lat and lon:
            return (float(lat), float(lon))
        
    except Exception as e:
        print(f"⚠️  Error fetching details for {property_id}: {e}")
    
    return None


def discover_municipalities(sample_size: int = 10000, max_properties_per_municipality: int = 3) -> Dict:
    """
    Discover all municipalities by sampling properties and fetching their coordinates.
    
    Args:
        sample_size: Total number of properties to sample
        max_properties_per_municipality: Max properties to fetch details for per municipality
    
    Returns:
        Dictionary mapping municipality name to its info
    """
    print("=" * 80)
    print("🏛️  MUNICIPALITY DISCOVERY - Large Scale Random Sampling")
    print("=" * 80)
    
    # Step 1: Collect property IDs and municipality names
    property_samples = fetch_property_ids_random(sample_size)
    
    # Step 2: Group by municipality
    print("\n📦 Grouping properties by municipality...")
    municipality_properties = defaultdict(list)
    for prop_id, municipality in property_samples:
        municipality_properties[municipality].append(prop_id)
    
    unique_municipalities = len(municipality_properties)
    print(f"✅ Found {unique_municipalities} unique municipalities")
    print(f"   Top 10 by property count:")
    sorted_munis = sorted(municipality_properties.items(), key=lambda x: len(x[1]), reverse=True)
    for name, props in sorted_munis[:10]:
        print(f"      {name}: {len(props)} properties")
    
    # Step 3: Fetch coordinates for representative properties from each municipality
    print(f"\n🌍 Fetching coordinates for up to {max_properties_per_municipality} properties per municipality...")
    municipality_info = {}
    
    for idx, (municipality, property_ids) in enumerate(municipality_properties.items(), 1):
        print(f"\n[{idx}/{unique_municipalities}] {municipality} ({len(property_ids)} properties sampled)")
        
        # Try to get coordinates from multiple properties (in case first one fails)
        coords_list = []
        for prop_id in property_ids[:max_properties_per_municipality]:
            coords = get_property_coordinates(prop_id)
            if coords:
                coords_list.append(coords)
            time.sleep(0.3)  # Respectful delay
            
            if len(coords_list) >= max_properties_per_municipality:
                break
        
        if coords_list:
            # Use average coordinates if we got multiple
            avg_lat = sum(c[0] for c in coords_list) / len(coords_list)
            avg_lon = sum(c[1] for c in coords_list) / len(coords_list)
            
            # Calculate distance from Copenhagen
            distance = calculate_distance(COPENHAGEN_LAT, COPENHAGEN_LON, avg_lat, avg_lon)
            
            municipality_info[municipality] = {
                'name': municipality,
                'lat': round(avg_lat, 6),
                'lon': round(avg_lon, 6),
                'distance_km': round(distance, 2),
                'sample_count': len(property_ids),
                'coordinates_found': len(coords_list)
            }
            
            print(f"   ✅ {municipality}: {distance:.1f} km from Copenhagen")
        else:
            print(f"   ❌ {municipality}: Could not get coordinates")
            municipality_info[municipality] = {
                'name': municipality,
                'lat': None,
                'lon': None,
                'distance_km': None,
                'sample_count': len(property_ids),
                'coordinates_found': 0
            }
    
    return municipality_info


def save_results(municipality_info: Dict, filename: str = 'municipalities_discovered.json'):
    """Save discovery results to JSON file"""
    # Sort by distance (None values last)
    sorted_info = sorted(
        municipality_info.values(),
        key=lambda x: (x['distance_km'] is None, x['distance_km'] if x['distance_km'] is not None else 0)
    )
    
    output = {
        'total_municipalities': len(municipality_info),
        'municipalities_with_coords': sum(1 for m in municipality_info.values() if m['lat'] is not None),
        'copenhagen_reference': {
            'lat': COPENHAGEN_LAT,
            'lon': COPENHAGEN_LON
        },
        'municipalities': sorted_info
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to {filename}")


def analyze_results(municipality_info: Dict, distance_threshold: int = 60):
    """Print analysis of discovered municipalities"""
    print("\n" + "=" * 80)
    print("📊 ANALYSIS RESULTS")
    print("=" * 80)
    
    total = len(municipality_info)
    with_coords = [m for m in municipality_info.values() if m['lat'] is not None]
    without_coords = [m for m in municipality_info.values() if m['lat'] is None]
    
    print(f"\n📈 Summary:")
    print(f"   Total unique municipalities: {total}")
    print(f"   With coordinates: {len(with_coords)}")
    print(f"   Without coordinates: {len(without_coords)}")
    
    if with_coords:
        within_threshold = [m for m in with_coords if m['distance_km'] <= distance_threshold]
        beyond_threshold = [m for m in with_coords if m['distance_km'] > distance_threshold]
        
        print(f"\n🎯 Within {distance_threshold} km of Copenhagen: {len(within_threshold)} municipalities")
        print(f"   Beyond {distance_threshold} km: {len(beyond_threshold)} municipalities")
        
        print(f"\n✅ Municipalities within {distance_threshold} km (sorted by distance):")
        for m in sorted(within_threshold, key=lambda x: x['distance_km']):
            print(f"   {m['name']:20s} - {m['distance_km']:6.1f} km ({m['sample_count']} properties sampled)")
        
        print(f"\n🔍 Closest 10 municipalities:")
        for m in sorted(with_coords, key=lambda x: x['distance_km'])[:10]:
            print(f"   {m['name']:20s} - {m['distance_km']:6.1f} km")
        
        print(f"\n🌍 Farthest 10 municipalities:")
        for m in sorted(with_coords, key=lambda x: x['distance_km'], reverse=True)[:10]:
            print(f"   {m['name']:20s} - {m['distance_km']:6.1f} km")
    
    if without_coords:
        print(f"\n⚠️  Municipalities without coordinates ({len(without_coords)}):")
        for m in without_coords:
            print(f"   {m['name']} ({m['sample_count']} properties sampled)")


def main():
    """Main execution"""
    print("🚀 Starting large-scale municipality discovery...")
    print(f"   Target sample size: 10,000 properties")
    print(f"   Strategy: Random sampling across multiple sort methods and page ranges\n")
    
    # Discover municipalities
    municipality_info = discover_municipalities(sample_size=10000, max_properties_per_municipality=3)
    
    # Save results
    save_results(municipality_info)
    
    # Analyze
    analyze_results(municipality_info, distance_threshold=60)
    
    print("\n✅ Discovery complete!")


if __name__ == '__main__':
    main()
