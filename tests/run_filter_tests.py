#!/usr/bin/env python3
"""
Standalone Filter Test Runner
Runs without pytest dependency - tests all filter combinations
"""

import requests
import json
from urllib.parse import urlencode

# Use production URL for testing
API_BASE_URL = "https://ai-vaerksted.cloud/housing"
TIMEOUT = 10

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

passed = 0
failed = 0


def print_header(title: str) -> None:
    """Print test header"""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{title}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")


def print_test(name: str, passed_test: bool, message: str = "") -> None:
    """Print test result"""
    global passed, failed
    if passed_test:
        passed += 1
        print(f"{GREEN}✓ PASS{RESET}: {name}")
        if message:
            print(f"  {message}")
    else:
        failed += 1
        print(f"{RED}✗ FAIL{RESET}: {name}")
        if message:
            print(f"  {RED}{message}{RESET}")


def test_price_filter_text_search():
    """Test text search with price filters"""
    print_header("Test 1: Text Search with Price Filters")

    min_price = 3000000
    max_price = 5000000
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/text-search?q=hvidovre&min_price={min_price}&max_price={max_price}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) > 0

        # Verify all prices are within range
        all_in_range = all(
            (p["price"] is None or min_price <= p["price"] <= max_price)
            for p in data["results"]
        )
        print_test(
            "Price range filter (3-5M DKK)",
            all_in_range,
            f"Found {len(data['results'])} properties, all in price range"
        )
    except Exception as e:
        print_test("Price range filter", False, str(e))


def test_price_and_rooms_filter():
    """Test combining price and rooms filters"""
    print_header("Test 2: Combined Price + Rooms Filters")

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/text-search?q=hvidovre&min_price=3000000&max_price=5000000&min_rooms=6",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()

        valid = all(
            (p["price"] is None or 3000000 <= p["price"] <= 5000000) and
            (p["rooms"] is None or p["rooms"] >= 6)
            for p in data["results"]
        )
        print_test(
            "Price (3-5M) + Rooms (≥6)",
            valid and len(data["results"]) > 0,
            f"Found {len(data['results'])} properties matching both filters"
        )
    except Exception as e:
        print_test("Combined filters", False, str(e))


def test_municipality_filter():
    """Test municipality filter"""
    print_header("Test 3: Municipality Filter")

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/search?municipality=Hvidovre&min_price=3000000&max_price=5000000",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()

        all_correct = all(p["municipality"] == "Hvidovre" for p in data["results"])
        print_test(
            "Municipality filter (Hvidovre)",
            all_correct and len(data["results"]) > 0,
            f"Found {len(data['results'])} properties in Hvidovre"
        )
    except Exception as e:
        print_test("Municipality filter", False, str(e))


def test_area_filter():
    """Test area filter"""
    print_header("Test 4: Living Area Filter")

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/search?min_area=150&max_area=250",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()

        valid = all(
            (p["living_area"] is None or 150 <= p["living_area"] <= 250)
            for p in data["results"]
        )
        print_test(
            "Area filter (150-250 m²)",
            valid and len(data["results"]) > 0,
            f"Found {len(data['results'])} properties in size range"
        )
    except Exception as e:
        print_test("Area filter", False, str(e))


def test_year_filter():
    """Test year built filter"""
    print_header("Test 5: Year Built Filter")

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/search?min_year=1950&max_year=2000",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()

        valid = all(
            (p["year_built"] is None or 1950 <= p["year_built"] <= 2000)
            for p in data["results"]
        )
        print_test(
            "Year filter (1950-2000)",
            valid and len(data["results"]) > 0,
            f"Found {len(data['results'])} properties built in range"
        )
    except Exception as e:
        print_test("Year filter", False, str(e))


def test_market_status_filter():
    """Test market status filter"""
    print_header("Test 6: Market Status Filter")

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/search?on_market=true",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()

        all_on_market = all(p["on_market"] is True for p in data["results"])
        print_test(
            "Market status filter (on_market=true)",
            all_on_market and len(data["results"]) > 0,
            f"Found {len(data['results'])} properties currently on market"
        )
    except Exception as e:
        print_test("Market status filter", False, str(e))


def test_text_search_municipalities():
    """Test text search respects municipality filter"""
    print_header("Test 7: Text Search with Municipality Filter")

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/text-search?q=copenhagen&municipality=Hvidovre",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()

        all_correct = all(p["municipality"] == "Hvidovre" for p in data["results"])
        print_test(
            "Text search filters by municipality",
            all_correct,
            f"Found {len(data['results'])} properties in Hvidovre matching text search"
        )
    except Exception as e:
        print_test("Text search municipality filter", False, str(e))


def test_pagination():
    """Test pagination returns different results"""
    print_header("Test 8: Pagination")

    try:
        r1 = requests.get(f"{API_BASE_URL}/api/search?page=1", timeout=TIMEOUT)
        r2 = requests.get(f"{API_BASE_URL}/api/search?page=2", timeout=TIMEOUT)

        d1 = r1.json()
        d2 = r2.json()

        ids1 = {p["id"] for p in d1["results"]}
        ids2 = {p["id"] for p in d2["results"]}

        no_overlap = len(ids1.intersection(ids2)) == 0
        print_test(
            "Pagination returns different results",
            no_overlap,
            f"Page 1: {len(ids1)} results, Page 2: {len(ids2)} results, overlap: {len(ids1.intersection(ids2))}"
        )
    except Exception as e:
        print_test("Pagination", False, str(e))


def test_sorting():
    """Test sorting functionality"""
    print_header("Test 9: Sorting by Price (Descending)")

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/search?sort_by=price_desc&min_price=4000000",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()

        prices = [p["price"] for p in data["results"] if p["price"] is not None]
        is_sorted = all(prices[i] >= prices[i + 1] for i in range(len(prices) - 1))

        print_test(
            "Sort by price descending",
            is_sorted and len(prices) > 0,
            f"Checked {len(prices)} properties, correctly sorted: {is_sorted}"
        )
    except Exception as e:
        print_test("Sorting", False, str(e))


def test_combined_all_filters():
    """Test combining all filter types"""
    print_header("Test 10: All Filters Combined")

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/search?municipality=Hvidovre&min_price=3000000&max_price=5000000&min_area=100&min_rooms=4&on_market=true",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()

        valid = all(
            p["municipality"] == "Hvidovre" and
            p["on_market"] is True and
            (p["price"] is None or 3000000 <= p["price"] <= 5000000) and
            (p["living_area"] is None or p["living_area"] >= 100) and
            (p["rooms"] is None or p["rooms"] >= 4)
            for p in data["results"]
        )

        print_test(
            "All filters combined",
            valid and len(data["results"]) > 0,
            f"Found {len(data['results'])} properties matching all criteria"
        )
    except Exception as e:
        print_test("Combined filters", False, str(e))


def main():
    """Run all tests"""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}COMPREHENSIVE FILTER TEST SUITE{RESET}")
    print(f"{BOLD}{BLUE}Testing Housing Market Search API{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

    test_price_filter_text_search()
    test_price_and_rooms_filter()
    test_municipality_filter()
    test_area_filter()
    test_year_filter()
    test_market_status_filter()
    test_text_search_municipalities()
    test_pagination()
    test_sorting()
    test_combined_all_filters()

    # Print summary
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}TEST SUMMARY{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}")
    total = passed + failed
    print(f"{GREEN}Passed: {passed}/{total}{RESET}")
    if failed > 0:
        print(f"{RED}Failed: {failed}/{total}{RESET}")
    else:
        print(f"{GREEN}All tests passed! ✓{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")


if __name__ == "__main__":
    main()
