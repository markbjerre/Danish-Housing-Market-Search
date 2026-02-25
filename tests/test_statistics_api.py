"""
Statistics API tests.

Run with: python tests/test_statistics_api.py
Or: python -m pytest tests/test_statistics_api.py -v

Requires app running at API_BASE_URL (default http://127.0.0.1:5000).
For production: API_BASE_URL=https://ai-vaerksted.cloud HOUSING_BASE=/housing python tests/test_statistics_api.py

When DB is unavailable, endpoints return 503; tests accept 200 or 503.
"""

import os
import sys
import requests
from urllib.parse import urlencode

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

API_BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:5000')
TIMEOUT = 15


def get(path: str, params: dict = None) -> requests.Response:
    """GET request with optional base path for /housing."""
    base = os.getenv('HOUSING_BASE', '')
    url = f"{API_BASE_URL}{base}{path}"
    if params:
        url += '?' + urlencode(params)
    return requests.get(url, timeout=TIMEOUT)


def test_health():
    """Statistics health endpoint returns ok and row_counts, or 503 when DB unavailable."""
    r = get('/api/statistics/health')
    assert r.status_code in (200, 503), f"Expected 200 or 503, got {r.status_code}"
    d = r.json()
    assert 'ok' in d
    if r.status_code == 200:
        assert d['ok'] is True
        assert 'row_counts' in d
        assert 'properties' in d['row_counts']
        assert 'registrations' in d['row_counts']
    else:
        assert d.get('ok') is False
        assert 'error' in d


def test_market_overview():
    """Market overview returns active_listings, sold_this_month, avg_sqm_price_national, or 503 when DB down."""
    r = get('/api/statistics/market-overview')
    assert r.status_code in (200, 503)
    d = r.json()
    if r.status_code == 200:
        assert 'active_listings' in d
        assert 'sold_this_month' in d
        assert 'schema_version' in d


def test_price_trends():
    """Price trends returns data array, or 503 when DB down."""
    r = get('/api/statistics/price-trends', {'months': 6})
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        d = r.json()
        assert 'data' in d
        assert isinstance(d['data'], list)


def test_sales_volume():
    """Sales volume returns data array, or 503 when DB down."""
    r = get('/api/statistics/sales-volume', {'months': 6})
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        d = r.json()
        assert 'data' in d
        assert isinstance(d['data'], list)


def test_kommune_summary():
    """Kommune summary returns data array with municipality names, or 503 when DB down."""
    r = get('/api/statistics/kommune-summary')
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        d = r.json()
        assert 'data' in d
        assert isinstance(d['data'], list)
        if d['data']:
            assert 'name' in d['data'][0]
            assert 'sales_count' in d['data'][0] or 'avg_sqm_price' in d['data'][0]


def test_weekly_summary_json():
    """Weekly summary returns JSON with summary when format=json, or 503 when DB down."""
    r = get('/api/statistics/weekly-summary', {'format': 'json'})
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        d = r.json()
        assert 'period' in d
        assert 'summary' in d
        assert 'active_listings' in d['summary']


def test_weekly_summary_text():
    """Weekly summary returns plain text when format=text, or 503 when DB down."""
    r = get('/api/statistics/weekly-summary', {'format': 'text'})
    assert r.status_code in (200, 503)
    assert 'text/plain' in r.headers.get('Content-Type', '')
    if r.status_code == 200:
        assert 'Housing Weekly' in r.text or 'Active' in r.text


def test_statistics_page():
    """Statistics page loads (200 or 503 when DB down)."""
    r = get('/statistics')
    assert r.status_code in (200, 503)
    assert 'Housing Market Statistics' in r.text or 'statistics' in r.text.lower() or 'Database unavailable' in r.text


if __name__ == '__main__':
    import subprocess
    tests = [
        test_health,
        test_market_overview,
        test_price_trends,
        test_sales_volume,
        test_kommune_summary,
        test_weekly_summary_json,
        test_weekly_summary_text,
        test_statistics_page,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  OK: {t.__name__}")
        except Exception as e:
            print(f"  FAIL: {t.__name__} - {e}")
            failed += 1
    print(f"\n{failed}/{len(tests)} failed")
    sys.exit(1 if failed else 0)
