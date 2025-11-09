# API Testing Documentation

## Overview

This directory contains test scripts to validate the Danish Housing Market Search API functionality.

## Test Suite: `test_api_endpoints.py`

Comprehensive test suite that validates all major API endpoints and data quality.

### What It Tests

1. **Server Health Check** - Verifies Flask server is running
2. **API Search - Basic** - Tests `/api/search` endpoint returns proper structure
3. **API Search - On-Market Filter** - Validates on-market property filtering
4. **API Search - Municipality Filter** - Tests municipality-based filtering (uses Hvidovre)
5. **API Search - Price Filter** - Validates price range filtering
6. **API Search - Sorting** - Verifies sorting by price works correctly
7. **API Text Search** - Tests full-text search functionality
8. **API Property Details** - Gets individual property details
9. **Data Quality** - Checks for missing/null data in properties

### Running the Tests

#### Prerequisites

1. Start the Flask server:
```bash
python -m flask --app webapp/app run
```

2. Make sure PostgreSQL is running and database is populated

#### Run All Tests

```bash
python tests/test_api_endpoints.py
```

#### Expected Output

```
╔════════════════════════════════════════════════════════════════════╗
║               DANISH HOUSING API TEST SUITE                        ║
║                                                                    ║
║ Run Time: 2025-11-09 10:30:45                                     ║
║ Server: http://127.0.0.1:5000                                      ║
╚════════════════════════════════════════════════════════════════════╝

[Test details...]

╔════════════════════════════════════════════════════════════════════╗
║                      TEST SUMMARY                                  ║
╠════════════════════════════════════════════════════════════════════╣
║ ✓ PASS | Server Health Check                                      ║
║ ✓ PASS | API Search - Basic                                       ║
║ ✓ PASS | API Search - On-Market Filter                            ║
║ ✓ PASS | API Search - Municipality Filter                         ║
║ ✓ PASS | API Search - Price Filter                                ║
║ ✓ PASS | API Search - Sorting                                     ║
║ ✓ PASS | API Text Search                                          ║
║ ✓ PASS | API Property Details                                     ║
║ ✓ PASS | Data Quality                                             ║
╠════════════════════════════════════════════════════════════════════╣
║ Total: 9/9 passed (100%)                                           ║
╚════════════════════════════════════════════════════════════════════╝
```

### What Each Test Validates

#### 1. Server Health Check
- Ensures Flask server is responding on `http://127.0.0.1:5000`
- Returns helpful error if server is not running

#### 2. API Search - Basic
- Validates response structure (has `results`, `page`, `total`, etc.)
- Checks result objects have required fields (address, city, price, etc.)
- Shows total property count

**Expected**: 228,594+ total properties in database

#### 3. API Search - On-Market Filter
- Fetches properties with `on_market=true` filter
- Verifies all results have `on_market: true`
- Checks how many have prices vs null prices
- Shows sample properties with prices

**Expected**: ~3,663 on-market properties with mix of prices and "price on request"

#### 4. API Search - Municipality Filter  
- Fetches properties from Hvidovre municipality
- Verifies all results are from Hvidovre
- Checks data completeness (living_area, rooms, prices)
- Shows sample properties

**Expected**: 45+ properties in Hvidovre with various levels of completeness

#### 5. API Search - Price Filter
- Filters for properties between 5M-8M DKK
- Shows sample results in price range

**Expected**: Multiple properties found in price range

#### 6. API Search - Sorting
- Gets top 5 properties sorted by price (descending)
- Verifies prices are in descending order

**Expected**: Most expensive properties listed first

#### 7. API Text Search
- Tests full-text search for "Zeus" or "vej" (street name)
- Validates search functionality

**Expected**: Results found or graceful "no results" response

#### 8. API Property Details
- Gets a property ID from search results
- Fetches full details for that property
- Displays complete property object

**Expected**: Full property details returned successfully

#### 9. Data Quality
- Analyzes 50 properties for completeness
- Reports percentage of populated fields
- Checks price data availability

**Expected**: High completeness rates, some nulls OK (especially prices)

### Common Issues & Troubleshooting

#### Server Connection Error
```
✗ FAIL: Cannot connect to http://127.0.0.1:5000
ℹ INFO: Make sure Flask server is running: python -m flask --app webapp/app run
```

**Solution**: Start the Flask server before running tests

#### Database Connection Error
```
✗ FAIL: API returns error about database
```

**Solution**: 
- Ensure PostgreSQL is running
- Check `.env` file has correct database credentials
- Run: `python scripts/import_copenhagen_area.py` to populate database

#### No Properties Found
```
✗ FAIL: No properties found in municipality
```

**Solution**: Database may be empty. Run importer first.

### Performance Notes

- Full test suite should complete in 5-10 seconds
- Timeout is set to 10 seconds per request
- Uses `limit=50` to keep responses reasonable

### Exit Codes

- `0` = All tests passed ✓
- `1` = One or more tests failed ✗

### Integration into CI/CD

To use in automated testing (GitHub Actions, etc.):

```bash
# Run and capture exit code
python tests/test_api_endpoints.py
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "✓ All API tests passed"
else
    echo "✗ API tests failed"
    exit 1
fi
```

### Extending the Tests

To add a new test:

1. Create a new function following the pattern:
```python
def test_my_new_endpoint():
    """Test description"""
    print_test_header("My Test Name")
    
    try:
        # Your test code
        response = requests.get(f"{API_BASE_URL}/api/my-endpoint", timeout=TIMEOUT)
        data = response.json()
        
        # Validation
        if condition:
            print_pass("Validation message")
            return True
        else:
            print_fail("Error message")
            return False
            
    except Exception as e:
        print_fail(f"Error: {str(e)}")
        return False
```

2. Add to `tests` list in `run_all_tests()`:
```python
tests = [
    # ... existing tests ...
    ("My Test Name", test_my_new_endpoint),
]
```

## Other Test Files

- `quick_test.py` - Quick floor plan scraper test
- `clear_database.py` - Utility to clear database
- `diagnose_performance.py` - Performance diagnostics
- `discover_all_municipalities.py` - Municipality discovery utility

## Related Documentation

- See `DEPLOYMENT_CONFIG.md` for API configuration
- See `docs/DATABASE_SCHEMA.md` for database structure
- See `webapp/app.py` for API implementation
