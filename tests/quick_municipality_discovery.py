"""
Quick Municipality Name Discovery
Just extract ALL unique municipality names from API without fetching coordinates.
Then compare against our expected list to verify spellings.
"""

import requests
import json
import time
from collections import Counter

# API Configuration
BASE_URL = "https://api.boligsiden.dk"
SEARCH_ENDPOINT = f"{BASE_URL}/search/addresses"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.boligsiden.dk/',
    'Origin': 'https://www.boligsiden.dk',
}

# Expected Copenhagen-area municipalities from our reference file
EXPECTED_MUNICIPALITIES = [
    'København', 'Frederiksberg', 'Tårnby', 'Dragør', 'Hvidovre', 'Brøndby',
    'Vallensbæk', 'Ishøj', 'Albertslund', 'Glostrup', 'Rødovre', 'Herlev',
    'Gladsaxe', 'Gentofte', 'Lyngby-Taarbæk', 'Ballerup', 'Furesø', 'Egedal',
    'Rudersdal', 'Hørsholm', 'Fredensborg', 'Allerød', 'Hillerød',
    'Høje-Taastrup', 'Greve', 'Solrød', 'Køge', 'Roskilde', 'Lejre',
    'Stevns', 'Ringsted', 'Faxe', 'Gribskov', 'Halsnæs', 'Frederikssund'
]


def discover_municipality_names(max_pages_per_strategy: int = 50):
    """Quickly discover all municipality names without fetching full details"""
    
    print("=" * 80)
    print("🏛️  QUICK MUNICIPALITY NAME DISCOVERY")
    print("=" * 80)
    print(f"Sampling up to {max_pages_per_strategy} pages per sort strategy...\n")
    
    # Different sort strategies
    sort_strategies = [
        {'sortBy': 'address', 'sortAscending': 'true'},
        {'sortBy': 'address', 'sortAscending': 'false'},
        {'sortBy': 'soldDate', 'sortAscending': 'true'},
        {'sortBy': 'price', 'sortAscending': 'true'},
    ]
    
    all_municipalities = Counter()
    
    for idx, strategy in enumerate(sort_strategies, 1):
        print(f"📊 Strategy {idx}/{len(sort_strategies)}: sortBy={strategy['sortBy']}, ascending={strategy['sortAscending']}")
        
        for page in range(1, max_pages_per_strategy + 1):
            try:
                params = {
                    'sold': 'false',
                    'per_page': '20',
                    'page': str(page),
                    **strategy
                }
                
                response = requests.get(SEARCH_ENDPOINT, params=params, headers=HEADERS, timeout=10)
                
                if response.status_code == 400:
                    print(f"   Reached page limit at page {page}")
                    break
                
                response.raise_for_status()
                data = response.json()
                
                # API uses 'addresses' not 'results'
                if 'addresses' in data and data['addresses']:
                    for item in data['addresses']:
                        muni_dict = item.get('municipality')
                        if muni_dict and isinstance(muni_dict, dict):
                            muni_name = muni_dict.get('name')
                            if muni_name:
                                all_municipalities[muni_name] += 1
                else:
                    print(f"   No more results at page {page}")
                    break
                
                # Progress
                if page % 10 == 0:
                    print(f"   Page {page}: {len(all_municipalities)} unique municipalities so far")
                
                time.sleep(0.1)  # Quick delay
                
            except KeyboardInterrupt:
                print("\n⚠️  Interrupted by user")
                break
            except Exception as e:
                print(f"   Error on page {page}: {e}")
                break
        
        print(f"   ✅ Found {len(all_municipalities)} unique municipalities after strategy {idx}\n")
    
    return all_municipalities


def analyze_results(all_municipalities: Counter):
    """Analyze discovered municipalities"""
    
    print("\n" + "=" * 80)
    print("📊 ANALYSIS RESULTS")
    print("=" * 80)
    
    discovered = set(all_municipalities.keys())
    expected = set(EXPECTED_MUNICIPALITIES)
    
    print(f"\n📈 Summary:")
    print(f"   Total unique municipalities discovered: {len(discovered)}")
    print(f"   Expected Copenhagen-area municipalities: {len(expected)}")
    
    # Check which expected ones were found
    found_expected = discovered & expected
    not_found_expected = expected - discovered
    
    print(f"\n✅ Expected municipalities FOUND in API ({len(found_expected)}):")
    for muni in sorted(found_expected):
        count = all_municipalities[muni]
        print(f"   {muni:25s} - {count:,} properties")
    
    if not_found_expected:
        print(f"\n⚠️  Expected municipalities NOT FOUND in API ({len(not_found_expected)}):")
        for muni in sorted(not_found_expected):
            print(f"   {muni}")
    
    # Check for similar spellings
    additional = discovered - expected
    if additional:
        print(f"\n🔍 Additional municipalities discovered ({len(additional)}):")
        # Show top 30 by property count
        sorted_additional = sorted([(m, all_municipalities[m]) for m in additional], 
                                  key=lambda x: x[1], reverse=True)
        for muni, count in sorted_additional[:30]:
            print(f"   {muni:25s} - {count:,} properties")
        
        if len(additional) > 30:
            print(f"   ... and {len(additional) - 30} more")
    
    # Show top 10 overall
    print(f"\n🏆 Top 10 municipalities by property count:")
    for muni, count in all_municipalities.most_common(10):
        in_expected = "✓" if muni in expected else " "
        print(f"   {in_expected} {muni:25s} - {count:,} properties")
    
    # Save results
    output = {
        'total_discovered': len(discovered),
        'expected_count': len(expected),
        'found_expected': len(found_expected),
        'not_found_expected': list(sorted(not_found_expected)),
        'all_municipalities': {name: count for name, count in all_municipalities.most_common()}
    }
    
    filename = 'municipality_names_discovered.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to {filename}")


def main():
    """Main execution"""
    print("\n🚀 Quick municipality name discovery...")
    print("   This will scan API results to find all municipality names\n")
    
    municipalities = discover_municipality_names(max_pages_per_strategy=50)
    analyze_results(municipalities)
    
    print("\n✅ Discovery complete!")


if __name__ == '__main__':
    main()
