"""
Quick Municipality Distance Analysis
Fetch a few hundred properties at once and calculate distances
"""

import requests
import json
import math
from collections import defaultdict

# Copenhagen City Hall coordinates
COPENHAGEN_LAT = 55.6761
COPENHAGEN_LON = 12.5683

# API Configuration
BASE_URL = "https://api.boligsiden.dk"
SEARCH_ENDPOINT = f"{BASE_URL}/search/addresses"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
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


print("=" * 80)
print("📍 QUICK MUNICIPALITY DISTANCE ANALYSIS")
print("=" * 80)
print("\nFetching properties to map all municipalities...\n")

# Collect coordinates for all municipalities
municipality_coords = {}
municipality_counts = defaultdict(int)

# Fetch default response (50 properties per call)
for attempt in range(10):  # Try 10 times to get more municipalities
    try:
        print(f"Fetching batch {attempt + 1}...")
        response = requests.get(SEARCH_ENDPOINT, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'addresses' in data:
            for item in data['addresses']:
                muni_dict = item.get('municipality', {})
                muni_name = muni_dict.get('name')
                
                if muni_name:
                    municipality_counts[muni_name] += 1
                    
                    # Store first found coordinates
                    if muni_name not in municipality_coords:
                        coords = item.get('coordinates', {})
                        lat = coords.get('lat')
                        lon = coords.get('lon')
                        
                        if lat and lon:
                            municipality_coords[muni_name] = (float(lat), float(lon))
                            print(f"  ✓ Mapped: {muni_name}")
        
        print(f"  Total municipalities mapped: {len(municipality_coords)}\n")
        
    except Exception as e:
        print(f"  Error: {e}\n")
        break

print(f"\n✅ Collected coordinates for {len(municipality_coords)} municipalities\n")

# Calculate distances
print("=" * 80)
print("📊 CALCULATING DISTANCES")
print("=" * 80)

municipality_distances = []

for muni_name, coords in municipality_coords.items():
    lat, lon = coords
    distance = calculate_distance(COPENHAGEN_LAT, COPENHAGEN_LON, lat, lon)
    
    municipality_distances.append({
        'name': muni_name,
        'lat': round(lat, 6),
        'lon': round(lon, 6),
        'distance_km': round(distance, 2),
        'properties_sampled': municipality_counts.get(muni_name, 0)
    })

# Sort by distance
municipality_distances.sort(key=lambda x: x['distance_km'])

# Filter by 60km threshold
within_60km = [m for m in municipality_distances if m['distance_km'] <= 60]
beyond_60km = [m for m in municipality_distances if m['distance_km'] > 60]

print(f"\n✅ Distances calculated for {len(municipality_distances)} municipalities")
print(f"   Within 60 km: {len(within_60km)}")
print(f"   Beyond 60 km: {len(beyond_60km)}")

# Display results
print("\n" + "=" * 80)
print(f"📍 MUNICIPALITIES WITHIN 60 KM OF COPENHAGEN")
print("=" * 80)
print(f"\n{'Distance':>10s} | {'Municipality':25s} | {'Coord (lat, lon)':20s}")
print("-" * 80)

for m in within_60km:
    print(f"{m['distance_km']:9.1f} km | {m['name']:25s} | ({m['lat']}, {m['lon']})")

# Show municipalities just beyond
if beyond_60km:
    print(f"\n{'Distance':>10s} | {'Municipality':25s} | (Just beyond 60 km)")
    print("-" * 80)
    for m in beyond_60km[:5]:
        print(f"{m['distance_km']:9.1f} km | {m['name']:25s}")

# Save results
output = {
    'analysis_date': '2025-01-04',
    'copenhagen_reference': {
        'lat': COPENHAGEN_LAT,
        'lon': COPENHAGEN_LON,
        'location': 'Copenhagen City Hall'
    },
    'distance_threshold_km': 60,
    'within_threshold': within_60km,
    'beyond_threshold': beyond_60km,
    'summary': {
        'total_municipalities_analyzed': len(municipality_distances),
        'within_threshold': len(within_60km),
        'beyond_threshold': len(beyond_60km)
    }
}

filename = 'municipalities_within_60km.json'
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n💾 Results saved to {filename}")

# Generate Python list
within_60km_names = sorted([m['name'] for m in within_60km])

print(f"\n🐍 Python list for code (sorted alphabetically):")
print("=" * 80)
print("# Copenhagen area municipalities within 60 km")
print("COPENHAGEN_60KM_MUNICIPALITIES = [")
for name in within_60km_names:
    print(f"    '{name}',")
print("]")

print(f"\n🔗 API filter parameter:")
print("=" * 80)
print("municipalities=" + ",".join(within_60km_names))

print("\n✅ Analysis complete!")
