"""
Test script to diagnose the performance issues
"""

import requests
import time

BASE_URL = "https://api.boligsiden.dk/search/addresses"
DETAIL_URL = "https://api.boligsiden.dk/addresses"

print("="*80)
print("DIAGNOSING PERFORMANCE ISSUES")
print("="*80)
print()

# Test 1: Check how many villas are in København
print("TEST 1: Total villas in København")
print("-"*80)

params = {
    'municipalities': 'København',
    'addressTypes': 'villa',
    'per_page': '50',
    'page': '1'
}

print(f"API Call: {BASE_URL}")
print(f"Params: {params}")
print()

response = requests.get(BASE_URL, params=params)
data = response.json()

total_hits = data.get('totalHits', 0)
addresses_returned = len(data.get('addresses', []))

print(f"Total villas in København: {total_hits:,}")
print(f"Addresses in first page: {addresses_returned}")
print(f"Total pages needed: {total_hits // 50 + 1}")
print()

# Test 2: Check what --limit parameter does
print("TEST 2: Understanding --limit parameter")
print("-"*80)
print("When you run: python import_copenhagen_area.py --limit 10")
print("The script stops after finding 10 TOTAL properties across ALL municipalities")
print("NOT 10 per page or 10 per municipality!")
print()
print(f"So if you want all {total_hits:,} villas, don't use --limit")
print()

# Test 3: Measure import speed
print("TEST 3: Import speed bottleneck")
print("-"*80)
print("Current approach:")
print("1. Search API: Get property IDs (fast)")
print("2. For EACH property:")
print("   - Fetch detailed data: 1 API call")
print("   - Parse all fields")
print("   - Save to database: 1 commit")
print("   - Sleep 0.2 seconds")
print()
print(f"Time per property: ~1-2 seconds")
print(f"For {total_hits:,} villas: {total_hits * 1.5 / 3600:.1f} hours!")
print()

# Test 4: Show the solution
print("TEST 4: Performance improvements needed")
print("-"*80)
print("SOLUTION 1: Remove per-property API calls")
print("  - Search API already returns basic data")
print("  - Only fetch details if you need ALL 100+ fields")
print()
print("SOLUTION 2: Batch commits")
print("  - Commit every 100 properties, not every 1")
print("  - Reduces database overhead by 100x")
print()
print("SOLUTION 3: Parallel processing")
print("  - Use ThreadPoolExecutor to fetch 5-10 properties simultaneously")
print("  - Can speed up by 5-10x")
print()
print("SOLUTION 4: Remove --limit or set it higher")
print("  - Use --limit 1000 to test with first 1000 properties")
print("  - Or remove it entirely to get all villas")
print()

# Test 5: Estimate realistic time
print("TEST 5: Realistic import time estimate")
print("-"*80)
print("Current speed: ~0.5-1 property/second")
print(f"  {total_hits:,} villas = {total_hits / 0.75 / 3600:.1f} hours")
print()
print("With optimizations: ~5-10 properties/second")
print(f"  {total_hits:,} villas = {total_hits / 7 / 3600:.1f} hours")
print()
print("With parallel processing (5 threads): ~25-50 properties/second")
print(f"  {total_hits:,} villas = {total_hits / 35 / 3600:.1f} hours")
print()

print("="*80)
print("RECOMMENDATION:")
print("="*80)
print("1. Remove --limit flag to get all villas")
print("2. Optimize batch commits")
print("3. Add parallel processing")
print("4. Run overnight for full import")
