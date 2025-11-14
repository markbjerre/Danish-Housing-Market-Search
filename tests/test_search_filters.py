"""
Comprehensive Search Filter Test Suite

Tests all filter combinations for both /api/search and /api/text-search endpoints.
Validates that filters work correctly individually and in combination.

Run with: pytest tests/test_search_filters.py -v
"""

import pytest
import requests
import json
from urllib.parse import urlencode

# Use production URL for testing
API_BASE_URL = "https://ai-vaerksted.cloud/housing"
TIMEOUT = 10


class TestSearchFilters:
    """Test /api/search endpoint with various filter combinations"""

    def test_basic_search_without_filters(self):
        """Test that basic search returns results without filters"""
        response = requests.get(f"{API_BASE_URL}/api/search", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["total"] > 0
        assert len(data["results"]) > 0

    def test_price_filter_min(self):
        """Test minimum price filter"""
        min_price = 4000000
        response = requests.get(
            f"{API_BASE_URL}/api/search?min_price={min_price}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        for prop in data["results"]:
            if prop["price"] is not None:
                assert prop["price"] >= min_price, f"Property {prop['address']} has price {prop['price']} below minimum {min_price}"

    def test_price_filter_max(self):
        """Test maximum price filter"""
        max_price = 6000000
        response = requests.get(
            f"{API_BASE_URL}/api/search?max_price={max_price}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        for prop in data["results"]:
            if prop["price"] is not None:
                assert prop["price"] <= max_price, f"Property {prop['address']} has price {prop['price']} above maximum {max_price}"

    def test_price_filter_range(self):
        """Test price range filter (min and max together)"""
        min_price = 4000000
        max_price = 6000000
        response = requests.get(
            f"{API_BASE_URL}/api/search?min_price={min_price}&max_price={max_price}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        for prop in data["results"]:
            if prop["price"] is not None:
                assert min_price <= prop["price"] <= max_price, \
                    f"Property {prop['address']} has price {prop['price']} outside range {min_price}-{max_price}"

    def test_area_filter_min(self):
        """Test minimum area filter"""
        min_area = 150
        response = requests.get(
            f"{API_BASE_URL}/api/search?min_area={min_area}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        for prop in data["results"]:
            if prop["living_area"] is not None:
                assert prop["living_area"] >= min_area

    def test_area_filter_range(self):
        """Test area range filter"""
        min_area = 150
        max_area = 250
        response = requests.get(
            f"{API_BASE_URL}/api/search?min_area={min_area}&max_area={max_area}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        for prop in data["results"]:
            if prop["living_area"] is not None:
                assert min_area <= prop["living_area"] <= max_area

    def test_rooms_filter(self):
        """Test room count filter"""
        min_rooms = 5
        response = requests.get(
            f"{API_BASE_URL}/api/search?min_rooms={min_rooms}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        for prop in data["results"]:
            if prop["rooms"] is not None:
                assert prop["rooms"] >= min_rooms

    def test_year_filter(self):
        """Test year built filter"""
        min_year = 1950
        response = requests.get(
            f"{API_BASE_URL}/api/search?min_year={min_year}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        for prop in data["results"]:
            if prop["year_built"] is not None:
                assert prop["year_built"] >= min_year

    def test_municipality_filter(self):
        """Test municipality filter"""
        municipality = "Hvidovre"
        response = requests.get(
            f"{API_BASE_URL}/api/search?municipality={municipality}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        for prop in data["results"]:
            assert prop["municipality"] == municipality

    def test_market_status_on_market(self):
        """Test on_market filter for currently listed properties"""
        response = requests.get(
            f"{API_BASE_URL}/api/search?on_market=true",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        for prop in data["results"]:
            assert prop["on_market"] is True

    def test_market_status_sold(self):
        """Test on_market filter for sold properties"""
        response = requests.get(
            f"{API_BASE_URL}/api/search?on_market=false",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        # May have 0 results if no sold properties
        for prop in data["results"]:
            assert prop["on_market"] is False

    def test_combined_filters_price_and_area(self):
        """Test combining price and area filters"""
        min_price = 4000000
        max_price = 6000000
        min_area = 150
        max_area = 250
        response = requests.get(
            f"{API_BASE_URL}/api/search?min_price={min_price}&max_price={max_price}&min_area={min_area}&max_area={max_area}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        for prop in data["results"]:
            if prop["price"] is not None:
                assert min_price <= prop["price"] <= max_price
            if prop["living_area"] is not None:
                assert min_area <= prop["living_area"] <= max_area

    def test_combined_filters_all_types(self):
        """Test combining multiple filter types"""
        response = requests.get(
            f"{API_BASE_URL}/api/search?municipality=Hvidovre&min_price=3000000&max_price=5000000&min_area=100&min_rooms=4&on_market=true",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        for prop in data["results"]:
            assert prop["municipality"] == "Hvidovre"
            assert prop["on_market"] is True
            if prop["price"] is not None:
                assert 3000000 <= prop["price"] <= 5000000
            if prop["living_area"] is not None:
                assert prop["living_area"] >= 100
            if prop["rooms"] is not None:
                assert prop["rooms"] >= 4

    def test_pagination(self):
        """Test pagination works correctly"""
        response_page1 = requests.get(
            f"{API_BASE_URL}/api/search?page=1",
            timeout=TIMEOUT
        )
        response_page2 = requests.get(
            f"{API_BASE_URL}/api/search?page=2",
            timeout=TIMEOUT
        )
        assert response_page1.status_code == 200
        assert response_page2.status_code == 200
        data1 = response_page1.json()
        data2 = response_page2.json()

        # Results should be different on different pages
        if data1["results"] and data2["results"]:
            ids_page1 = {prop["id"] for prop in data1["results"]}
            ids_page2 = {prop["id"] for prop in data2["results"]}
            assert ids_page1.isdisjoint(ids_page2)


class TestTextSearchFilters:
    """Test /api/text-search endpoint with various filter combinations"""

    def test_text_search_basic(self):
        """Test basic text search without filters"""
        response = requests.get(
            f"{API_BASE_URL}/api/text-search?q=hvidovre",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "results" in data
        assert data["total"] > 0

    def test_text_search_with_price_filter(self):
        """Test text search with price filter"""
        min_price = 3000000
        max_price = 5000000
        response = requests.get(
            f"{API_BASE_URL}/api/text-search?q=hvidovre&min_price={min_price}&max_price={max_price}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) > 0

        # Verify all results are within price range
        for prop in data["results"]:
            if prop["price"] is not None:
                assert min_price <= prop["price"] <= max_price, \
                    f"Property {prop['address']} price {prop['price']} outside range"

    def test_text_search_with_rooms_filter(self):
        """Test text search with room count filter"""
        min_rooms = 6
        response = requests.get(
            f"{API_BASE_URL}/api/text-search?q=hvidovre&min_rooms={min_rooms}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        for prop in data["results"]:
            if prop["rooms"] is not None:
                assert prop["rooms"] >= min_rooms

    def test_text_search_with_area_filter(self):
        """Test text search with area filter"""
        min_area = 150
        max_area = 250
        response = requests.get(
            f"{API_BASE_URL}/api/text-search?q=hvidovre&min_area={min_area}&max_area={max_area}",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        for prop in data["results"]:
            if prop["living_area"] is not None:
                assert min_area <= prop["living_area"] <= max_area

    def test_text_search_combined_filters(self):
        """Test text search with multiple filters combined"""
        response = requests.get(
            f"{API_BASE_URL}/api/text-search?q=hvidovre&min_price=3000000&max_price=5000000&min_area=100&min_rooms=4&on_market=true",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) > 0

        for prop in data["results"]:
            assert prop["on_market"] is True
            if prop["price"] is not None:
                assert 3000000 <= prop["price"] <= 5000000
            if prop["living_area"] is not None:
                assert prop["living_area"] >= 100
            if prop["rooms"] is not None:
                assert prop["rooms"] >= 4

    def test_text_search_with_municipality_filter(self):
        """Test text search with municipality filter"""
        response = requests.get(
            f"{API_BASE_URL}/api/text-search?q=copenhagen&municipality=Hvidovre",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        # May return 0 results if no properties match both criteria
        for prop in data["results"]:
            assert prop["municipality"] == "Hvidovre"

    def test_text_search_pagination(self):
        """Test text search pagination"""
        response_page1 = requests.get(
            f"{API_BASE_URL}/api/text-search?q=hvidovre&page=1",
            timeout=TIMEOUT
        )
        response_page2 = requests.get(
            f"{API_BASE_URL}/api/text-search?q=hvidovre&page=2",
            timeout=TIMEOUT
        )
        assert response_page1.status_code == 200
        assert response_page2.status_code == 200

        data1 = response_page1.json()
        data2 = response_page2.json()

        # Results should be different on different pages if both have results
        if data1["results"] and data2["results"]:
            ids_page1 = {prop["id"] for prop in data1["results"]}
            ids_page2 = {prop["id"] for prop in data2["results"]}
            assert ids_page1.isdisjoint(ids_page2)


class TestSortingBehavior:
    """Test sorting functionality"""

    def test_sort_price_desc(self):
        """Test sorting by price descending (high to low)"""
        response = requests.get(
            f"{API_BASE_URL}/api/search?sort_by=price_desc",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        results = data["results"]

        if len(results) > 1:
            prices = [p["price"] for p in results if p["price"] is not None]
            if len(prices) > 1:
                # Check that prices are in descending order
                for i in range(len(prices) - 1):
                    assert prices[i] >= prices[i + 1], \
                        f"Prices not in descending order: {prices[i]} -> {prices[i+1]}"

    def test_sort_price_asc(self):
        """Test sorting by price ascending (low to high)"""
        response = requests.get(
            f"{API_BASE_URL}/api/search?sort_by=price_asc",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        results = data["results"]

        if len(results) > 1:
            prices = [p["price"] for p in results if p["price"] is not None]
            if len(prices) > 1:
                # Check that prices are in ascending order
                for i in range(len(prices) - 1):
                    assert prices[i] <= prices[i + 1], \
                        f"Prices not in ascending order: {prices[i]} -> {prices[i+1]}"

    def test_sort_size_desc(self):
        """Test sorting by size descending"""
        response = requests.get(
            f"{API_BASE_URL}/api/search?sort_by=size_desc",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        results = data["results"]

        if len(results) > 1:
            areas = [p["living_area"] for p in results if p["living_area"] is not None]
            if len(areas) > 1:
                for i in range(len(areas) - 1):
                    assert areas[i] >= areas[i + 1], \
                        f"Areas not in descending order: {areas[i]} -> {areas[i+1]}"


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_search_query(self):
        """Test text search with empty query"""
        response = requests.get(
            f"{API_BASE_URL}/api/text-search?q=",
            timeout=TIMEOUT
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_single_character_search(self):
        """Test text search with single character (too short)"""
        response = requests.get(
            f"{API_BASE_URL}/api/text-search?q=a",
            timeout=TIMEOUT
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_nonexistent_municipality(self):
        """Test search with non-existent municipality"""
        response = requests.get(
            f"{API_BASE_URL}/api/search?municipality=NonExistentCity",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 0

    def test_invalid_page_number(self):
        """Test with invalid page number"""
        response = requests.get(
            f"{API_BASE_URL}/api/search?page=99999",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        # Should return empty or first page

    def test_inverted_price_range(self):
        """Test with min_price > max_price"""
        response = requests.get(
            f"{API_BASE_URL}/api/search?min_price=6000000&max_price=4000000",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        # Should return no results or handle gracefully
        assert isinstance(data["results"], list)

    def test_negative_price(self):
        """Test with negative price filter"""
        response = requests.get(
            f"{API_BASE_URL}/api/search?min_price=-1000000",
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        # Should handle gracefully


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
