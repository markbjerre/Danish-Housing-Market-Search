"""
Get all distinct municipalities from Boligsiden API and calculate distances from Copenhagen
"""

import requests
import json
from math import radians, cos, sin, asin, sqrt

# Copenhagen City Hall coordinates
CPH_LAT = 55.6761
CPH_LON = 12.5683
MAX_DISTANCE_KM = 60

# API configuration
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


def get_municipalities_from_api():
    """
    Fetch properties from different municipalities to discover all available municipalities
    """
    print("Fetching sample properties to discover municipalities...")
    print("=" * 80)
    print()
    
    municipalities_data = {}
    
    # Fetch first few pages to get a variety of municipalities
    for page in range(1, 20):  # Sample 20 pages = 400 properties
        try:
            params = {
                'sold': 'false',
                'per_page': '20',
                'page': str(page),
                'sortBy': 'address',
                'sortAscending': 'true'
            }
            
            response = requests.get(
                'https://api.boligsiden.dk/search/addresses',
                params=params,
                headers=API_HEADERS,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error on page {page}: {response.status_code}")
                break
            
            data = response.json()
            addresses = data.get('addresses', [])
            
            if not addresses:
                break
            
            # Fetch full details for each property to get municipality info
            for addr in addresses:
                prop_id = addr.get('addressID')
                if not prop_id:
                    continue
                
                # Fetch full property details
                try:
                    detail_response = requests.get(
                        f'https://api.boligsiden.dk/addresses/{prop_id}',
                        headers=API_HEADERS,
                        timeout=10
                    )
                    
                    if detail_response.status_code == 200:
                        prop_data = detail_response.json()
                        
                        # Extract municipality info
                        municipality_obj = prop_data.get('municipality', {})
                        if municipality_obj:
                            muni_name = municipality_obj.get('name')
                            
                            if muni_name and muni_name not in municipalities_data:
                                # Get coordinates from property
                                lat = prop_data.get('latitude')
                                lon = prop_data.get('longitude')
                                
                                if lat and lon:
                                    municipalities_data[muni_name] = {
                                        'name': muni_name,
                                        'sample_lat': lat,
                                        'sample_lon': lon,
                                        'properties_count': 1
                                    }
                                    print(f"Found municipality: {muni_name} ({len(municipalities_data)} total)")
                                else:
                                    municipalities_data[muni_name] = {
                                        'name': muni_name,
                                        'sample_lat': None,
                                        'sample_lon': None,
                                        'properties_count': 1
                                    }
                            elif muni_name:
                                municipalities_data[muni_name]['properties_count'] += 1
                
                except Exception as e:
                    pass  # Skip properties that fail
            
            print(f"Page {page}/20: Found {len(municipalities_data)} municipalities so far")
        
        except Exception as e:
            print(f"Error fetching page {page}: {str(e)}")
            break
    
    return municipalities_data


def calculate_municipality_distances(municipalities_data):
    """Calculate distance from Copenhagen for each municipality"""
    print()
    print("=" * 80)
    print("CALCULATING DISTANCES FROM COPENHAGEN")
    print("=" * 80)
    print()
    
    municipalities_with_distance = []
    
    for muni_name, muni_info in municipalities_data.items():
        lat = muni_info['sample_lat']
        lon = muni_info['sample_lon']
        
        if lat and lon:
            distance = haversine_distance(CPH_LAT, CPH_LON, lat, lon)
            municipalities_with_distance.append({
                'name': muni_name,
                'distance_km': distance,
                'within_60km': distance <= MAX_DISTANCE_KM,
                'latitude': lat,
                'longitude': lon,
                'properties_count': muni_info['properties_count']
            })
        else:
            municipalities_with_distance.append({
                'name': muni_name,
                'distance_km': None,
                'within_60km': False,
                'latitude': None,
                'longitude': None,
                'properties_count': muni_info['properties_count']
            })
    
    # Sort by distance
    municipalities_with_distance.sort(key=lambda x: x['distance_km'] if x['distance_km'] is not None else 9999)
    
    return municipalities_with_distance


def main():
    print()
    print("=" * 80)
    print("MUNICIPALITY DISTANCE ANALYSIS")
    print("=" * 80)
    print()
    print(f"Reference point: Copenhagen City Hall (55.6761°N, 12.5683°E)")
    print(f"Distance threshold: {MAX_DISTANCE_KM} km")
    print()
    
    # Get municipalities
    municipalities_data = get_municipalities_from_api()
    
    if not municipalities_data:
        print("No municipalities found!")
        return
    
    # Calculate distances
    municipalities = calculate_municipality_distances(municipalities_data)
    
    # Filter within 60km
    within_60km = [m for m in municipalities if m['within_60km']]
    outside_60km = [m for m in municipalities if not m['within_60km']]
    
    # Display results
    print()
    print("=" * 80)
    print("MUNICIPALITIES WITHIN 60KM OF COPENHAGEN")
    print("=" * 80)
    print()
    
    if within_60km:
        print(f"{'Municipality':<30} {'Distance (km)':<15} {'Sample Count'}")
        print("-" * 80)
        for muni in within_60km:
            dist_str = f"{muni['distance_km']:.1f}" if muni['distance_km'] else "N/A"
            print(f"{muni['name']:<30} {dist_str:<15} {muni['properties_count']}")
        
        print()
        print(f"Total: {len(within_60km)} municipalities within {MAX_DISTANCE_KM}km")
    else:
        print("No municipalities found within 60km")
    
    print()
    print("=" * 80)
    print("MUNICIPALITIES OUTSIDE 60KM")
    print("=" * 80)
    print()
    
    if outside_60km:
        print(f"{'Municipality':<30} {'Distance (km)':<15} {'Sample Count'}")
        print("-" * 80)
        for muni in outside_60km[:10]:  # Show first 10
            dist_str = f"{muni['distance_km']:.1f}" if muni['distance_km'] else "N/A"
            print(f"{muni['name']:<30} {dist_str:<15} {muni['properties_count']}")
        
        if len(outside_60km) > 10:
            print(f"... and {len(outside_60km) - 10} more")
        
        print()
        print(f"Total: {len(outside_60km)} municipalities outside {MAX_DISTANCE_KM}km")
    
    # Save to JSON file
    output_data = {
        'reference_point': {
            'name': 'Copenhagen City Hall',
            'latitude': CPH_LAT,
            'longitude': CPH_LON
        },
        'distance_threshold_km': MAX_DISTANCE_KM,
        'municipalities_within_threshold': within_60km,
        'municipalities_outside_threshold': outside_60km,
        'summary': {
            'total_municipalities': len(municipalities),
            'within_threshold': len(within_60km),
            'outside_threshold': len(outside_60km)
        }
    }
    
    output_file = 'municipalities_within_60km.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"✓ Results saved to {output_file}")
    print()
    
    # Generate Python list for use in import script
    municipality_names = [m['name'] for m in within_60km]
    print()
    print("=" * 80)
    print("MUNICIPALITIES LIST FOR IMPORT SCRIPT")
    print("=" * 80)
    print()
    print("# Municipalities within 60km of Copenhagen")
    print(f"MUNICIPALITIES_WITHIN_60KM = {municipality_names}")
    print()
    print("# For API query (comma-separated)")
    print(f"municipalities_param = '{','.join(municipality_names)}'")
    print()


if __name__ == "__main__":
    main()
