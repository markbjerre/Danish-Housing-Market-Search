# Current Filters Applied in import_copenhagen_area.py

## API Search Parameters (line ~220)

```python
params = {
    'municipalities': municipality,    # Filter by single municipality
    'addressTypes': 'villa',          # 🎯 ONLY VILLAS (97% reduction!)
    'per_page': str(per_page),        # 50 results per page
    'page': str(page),                # Current page number
    'sortBy': 'address',              # Sort by address
    'sortAscending': 'true'           # Sort ascending
}
```

## Current Filters:
1. **Municipality**: Only one municipality at a time (from 60km list)
2. **Address Type**: `villa` ONLY (excludes apartments, condos, etc.)
3. **Distance**: Only municipalities within 60km of Copenhagen (36 total)
4. **Market Status**: ALL villas (both on-market and sold properties)

## ISSUE: 10,000 Property Limit Per Municipality

**Problem**: Line 162 has a hard limit of 200 pages
- 200 pages × 50 per page = **10,000 properties maximum**
- For København with 14,368 villas, we'll miss **4,368 properties** (30%!)

**Root Cause**:
```python
if page > 200:
    print(f"\n⚠️  Reached page limit (200) - stopping to avoid fetching entire API")
    break
```

## Solution Strategy

The API's `totalHits` field tells us the total count. If totalHits > 10,000, we need to:

### Option 1: Subdivide by Zip Code
- Split large municipalities into zip code groups
- Example: København has many zip codes (2100, 2200, 2300, etc.)
- Each zip code search will have < 10,000 results

### Option 2: Subdivide by Additional Filters
- Use `minPrice` / `maxPrice` ranges
- Use `minArea` / `maxArea` ranges  
- Use `yearBuilt` ranges

### Option 3: API Pagination Investigation
- Check if API supports pagination beyond 200 pages
- Check if API has alternative endpoints for bulk export

## Recommended Fix: Zip Code Subdivision

For municipalities with > 10,000 properties:
1. Fetch all unique zip codes in that municipality
2. Run separate searches for each zip code
3. Combine results

This ensures we never hit the 10,000 limit per search.
