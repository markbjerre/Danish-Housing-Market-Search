"""
Test API call to understand case/price data structure

This script fetches a property from the Boligsiden API to analyze the data structure.
It helps identify all available fields for database enrichment, especially:
- Case pricing data (priceCash field)
- Images (5 sizes per image, webp format)
- Realtor information (ratings, contact info)
- Financing data (mortgage calculations)

USAGE:
    python test_api_case_structure.py

EXAMPLE PROPERTY:
    Property ID: 0a3f50a3-1a8a-32b8-e044-0003ba298018
    Address: Vårbuen 28, 2750 Ballerup
    URL: https://www.boligsiden.dk/adresse/vaarbuen-28-2750-ballerup-01510375__28_______
"""

import requests
import json

# Property ID from database (property with cases)
# This property is known to have an active listing (case)
property_id = "0a3f50a3-1a8a-32b8-e044-0003ba298018"

print("="*80)
print(f"FETCHING PROPERTY DATA FROM API")
print("="*80)
print(f"Property ID: {property_id}")

url = f"https://api.boligsiden.dk/addresses/{property_id}"

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    api_data = response.json()
    
    print(f"\n✅ API Response received")
    print(f"Status Code: {response.status_code}")
    
    # Save full response to file for inspection
    with open('api_test_response.json', 'w', encoding='utf-8') as f:
        json.dump(api_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Full response saved to: api_test_response.json")
    
    # Extract key information
    print("\n" + "="*80)
    print("PROPERTY BASIC INFO")
    print("="*80)
    print(f"Address: {api_data.get('roadName')} {api_data.get('houseNumber')}, {api_data.get('zipCode')} {api_data.get('cityName')}")
    print(f"Address Type: {api_data.get('addressType')}")
    print(f"Living Area: {api_data.get('livingArea')} sqm")
    print(f"Latest Valuation: {api_data.get('latestValuation'):,.0f} kr" if api_data.get('latestValuation') else "Latest Valuation: N/A")
    print(f"Is On Market: {api_data.get('isOnMarket')}")
    
    # Check for cases
    print("\n" + "="*80)
    print("CASES DATA STRUCTURE")
    print("="*80)
    
    cases = api_data.get('cases', [])
    print(f"Number of cases: {len(cases)}")
    
    if cases:
        for i, case in enumerate(cases, 1):
            print(f"\n--- Case #{i} ---")
            print(f"Case ID: {case.get('caseID')}")
            print(f"Status: {case.get('status')}")
            
            # Look for all possible price fields
            print("\n🔍 Checking for price fields:")
            price_fields = ['price', 'currentPrice', 'originalPrice', 'cashPrice', 'listingPrice', 
                          'salePrice', 'askingPrice', 'offerPrice']
            
            for field in price_fields:
                if field in case:
                    print(f"   ✅ {field}: {case[field]}")
            
            # Print all keys in case object
            print(f"\n📋 All keys in case object:")
            for key in case.keys():
                value = case[key]
                if isinstance(value, dict):
                    print(f"   {key}: <dict with keys: {list(value.keys())}>'")
                elif isinstance(value, list):
                    print(f"   {key}: <list with {len(value)} items>")
                else:
                    print(f"   {key}: {value}")
            
            # Check timeOnMarket structure
            if 'timeOnMarket' in case:
                print(f"\n⏱️ Time on Market structure:")
                tom = case['timeOnMarket']
                print(json.dumps(tom, indent=4, ensure_ascii=False))
            
            # Check for priceChanges
            if 'priceChanges' in case:
                price_changes = case['priceChanges']
                print(f"\n💰 Price Changes: {len(price_changes)} records")
                for j, pc in enumerate(price_changes[:3], 1):  # Show first 3
                    print(f"   Change #{j}:")
                    print(f"      {json.dumps(pc, indent=6, ensure_ascii=False)}")
    else:
        print("❌ No cases found in API response")
    
    # Check if there's an offering/listing object
    print("\n" + "="*80)
    print("CHECKING FOR OFFERING/LISTING DATA")
    print("="*80)
    
    offering_fields = ['offering', 'listing', 'currentListing', 'activeListing', 'marketData']
    for field in offering_fields:
        if field in api_data:
            print(f"\n✅ Found '{field}' field:")
            print(json.dumps(api_data[field], indent=2, ensure_ascii=False))
    
    # Check top-level for price fields
    print("\n" + "="*80)
    print("TOP-LEVEL FIELDS IN API RESPONSE")
    print("="*80)
    print(f"Total top-level keys: {len(api_data.keys())}")
    print("\nAll top-level keys:")
    for key in sorted(api_data.keys()):
        print(f"   - {key}")
    
except requests.exceptions.RequestException as e:
    print(f"\n❌ Error fetching from API: {e}")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
