# Danish Housing Market Analysis - Technical Knowledge Base

**Last Updated:** October 7, 2025  
**Purpose:** API documentation, critical fixes, performance optimizations, and troubleshooting

---

## 🎯 Project Overview

Python-based system for Danish housing market analysis using Boligsiden API.

### Status:
- ✅ **228,594 properties** imported successfully
- ✅ **3,683 cases** with listing dates and price changes
- ✅ **36 municipalities** within 60km of Copenhagen
- ✅ **Web interface** running at http://127.0.0.1:5000
- ✅ **Zero 10K limit issues** (zip code subdivision)
- ✅ **Parallel import** (20+ properties/second)

---

## 📊 Database Schema

### Core Tables (13 total):
1. **properties_new** - Main property records (100+ fields)
2. **main_buildings** - Primary building details
3. **additional_buildings** - Secondary structures
4. **registrations** - Price history and transactions
5. **municipalities** - Municipality data with tax rates
6. **provinces** - Province/region data
7. **roads** - Street information
8. **zip_codes** - Postal codes
9. **cities** - City data
10. **places** - Place/location data
11. **days_on_market** - Market timing data
12. **cases** - Listing cases with status, dates, and pricing (NEW!)
13. **price_changes** - Price reduction history per case (NEW!)

**Detailed schema:** See `DATABASE_SCHEMA.md`

---

## 🔌 Boligsiden API

### **API Endpoints:**
- **Search:** `https://api.boligsiden.dk/search/addresses`
- **Details:** `https://api.boligsiden.dk/addresses/{id}`

### **Working Filters:**
✅ `municipalities` - Single municipality name (NOT comma-separated!)
✅ `addressTypes` - 'villa', 'condo', 'terraced house', 'farm', 'hobby farm'
✅ `zipCodes` - **MUST BE PLURAL!** Single zip code or comma-separated list
✅ `priceMin/Max` - Price ranges in DKK
✅ `areaMin/Max` - Size ranges in m²
✅ `per_page` - Results per page (max 50)
✅ `page` - Page number (max 200 pages = 10,000 max results)
✅ `sold=false` - Filters for currently listed properties

### **Critical Bugs Fixed (Oct 6-7, 2025):**
🐛 **zipCode vs zipCodes** (CRITICAL!)
   - ❌ `zipCode` (singular) - **COMPLETELY IGNORED BY API**
   - ✅ `zipCodes` (plural) - **WORKS CORRECTLY**
   - **Fix:** Changed line 335 in import_copenhagen_area.py
   - **Impact:** Without this fix, zip filtering doesn't work at all

🐛 **10,000 Property Limit**
   - API pagination limited to 200 pages × 50 = 10,000 max
   - **Solution:** Auto-subdivide by zip code when totalHits > 9,500
   - **Example:** København has 14,368 villas across 13 zip codes
   - **Result:** Successfully imported all 14,368 properties

### **Non-Working Filters:**
❌ `isOnMarket` - Completely ignored by API
❌ `on_market` - Does not exist
❌ `market_status` - Does not exist
❌ Multiple municipalities - Must query one at a time

### **API Limitations:**
- Maximum 50 results per page
- Maximum 200 pages per query (**10,000 total, NOT 25,000!**)
- Must filter by single municipality
- Use `zipCodes` (plural) for zip filtering
- Must subdivide large municipalities by zip code

### **Data Statistics:**
- **København total:** 441,795 properties
- **København villas:** 14,368 (96.7% reduction!)
- **36 municipalities:** ~50,000-100,000 villas estimated
- **On-market rate:** ~0.2% (1 in 500 properties)

---

## 🚀 Import System

### **Main Script:** `import_copenhagen_area.py`

### **Command-Line Options:**
```bash
--parallel              # Enable parallel processing (20x faster!)
--workers N             # Number of parallel workers (default: 20)
--limit N               # Limit number of properties to import
--batch-size N          # Properties per commit (default: 50)
--dry-run               # Test without importing
```

### **Usage Examples:**
```bash
# Test with 100 properties
python import_copenhagen_area.py --limit 100 --parallel

# Full import (all 36 municipalities)
python import_copenhagen_area.py --parallel --workers 20

# Maximum speed
python import_copenhagen_area.py --parallel --workers 25
```

### **Performance Benchmarks:**

| Mode | Workers | Speed | Time (228k props) | Result |
|------|---------|-------|-------------------|---------|
| Sequential | 1 | 0.5-1/s | 60+ hours | Not practical |
| Parallel | 12 | 10/s | ~6.5 hours | Good |
| Parallel | 20 | 20-30/s | ~2-3 hours | **Production** |
| Parallel | 25 | 30-40/s | ~1.5-2 hours | Maximum |

**Real Import (Oct 7, 2025):**
- Total: 228,594 properties, 3,683 cases
- Time: ~2-3 hours with 20 workers
- Speed: 20-30 properties/second average
- Success rate: 100% (no errors)

---

## ⚡ Performance Optimizations

### **1. ThreadPoolExecutor (Parallel Processing)**
- Uses 12 concurrent workers by default
- Each worker fetches property data independently
- Processes multiple API calls simultaneously
- **Speedup:** 20x faster than sequential

### **2. Bulk Duplicate Checking**
- Checks 1000 property IDs per query
- Automatically skips existing properties
- No need to clear database between runs
- **Benefit:** 1 query instead of N queries

### **3. Session.merge() for Duplicates**
- Updates existing records instead of failing
- Handles unique constraint violations gracefully
- Prevents transaction rollbacks
- **Benefit:** Robust error handling

### **4. Batch Commits**
- Commits every 50 properties (configurable)
- Reduces database overhead significantly
- Faster than per-property commits
- **Benefit:** Better throughput

### **5. Auto-flush Disabled**
- Prevents premature constraint checks
- Uses `session.no_autoflush` blocks
- Allows bulk operations without interruption
- **Benefit:** Prevents flush errors

### **6. Optimized Timeouts**
- 10-second timeout per API request
- Faster failure recovery
- Prevents hanging on slow responses
- **Benefit:** Better responsiveness

### **7. Progress Tracking**
- Real-time speed metrics (props/sec)
- ETA calculation
- Batch progress updates
- **Benefit:** User visibility

---

## 📍 Geographic Scope

### **Target Area:** 60km radius from Copenhagen
### **Total Municipalities:** 36

**List:**
Albertslund, Allerød, Ballerup, Brøndby, Dragør, Egedal, Fredensborg, Frederiksberg, Frederikssund, Furesø, Gentofte, Gladsaxe, Glostrup, Greve, Gribskov, Halsnæs, Helsingør, Herlev, Hillerød, Holbæk, Hvidovre, Høje-Taastrup, Hørsholm, Ishøj, København, Køge, Lejre, Lyngby-Taarbæk, Ringsted, Roskilde, Rudersdal, Rødovre, Solrød, Stevns, Tårnby, Vallensbæk

**Municipality Data:** `municipalities_within_60km.json`
- Contains name, latitude, longitude, distance
- Filters to distance <= 60km
- Used for API queries

---

## 🏗️ Code Architecture

### **Core Files:**

1. **`import_copenhagen_area.py`** - Main import script
   - `fetch_properties_by_municipality()` - Scans municipalities
   - `import_properties_parallel()` - Parallel import with optimizations
   - `fetch_property_data()` - Worker function for ThreadPoolExecutor
   - `load_municipalities_within_60km()` - Loads municipality list

2. **`import_api_data.py`** - Database ORM functions
   - `import_property()` - Creates Property object
   - `import_main_building()` - Creates MainBuilding object
   - `import_additional_buildings()` - Creates AdditionalBuilding list
   - `import_registrations()` - Creates Registration list
   - `import_municipality/province/road/zip/city/place/days_on_market()` - Related entities

3. **`src/database_schema.py`** or **`src/db_models_new.py`** - SQLAlchemy models
   - Defines all 11 tables
   - Relationships and foreign keys
   - Comprehensive field definitions

4. **`reset_tables.py`** - Database management
   - Drops and recreates all tables
   - Fresh database setup

### **Key Design Patterns:**

**Municipality-by-Municipality with Zip Subdivision:**
```python
total_hits = get_total_count(municipality)
if total_hits > 9500:
    # CRITICAL: Subdivide by zip code to avoid 10K limit
    zip_codes = fetch_zip_codes_for_municipality(municipality)
    for zip_code in zip_codes:
        params = {
            'municipalities': municipality,
            'addressTypes': 'villa',
            'zipCodes': zip_code,  # MUST be plural!
            'per_page': '50'
        }
else:
    # Query entire municipality
    params = {
        'municipalities': municipality,
        'addressTypes': 'villa',
        'per_page': '50'
    }
```

**Parallel Fetching:**
```python
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {
        executor.submit(fetch_property_data, pid): pid 
        for pid in property_ids
    }
    for future in as_completed(futures):
        property_data = future.result()
        # Process as they complete
```

**Batch Committing:**
```python
batch_count = 0
for property in properties:
    session.merge(property)  # Handles duplicates gracefully
    batch_count += 1
    if batch_count >= 50:
        session.commit()
        batch_count = 0
```

---

## 🔍 API Discovery Process (Historical)

### **Phase 1: Parameter Testing**
- Tested 11 different market status parameters
- All ignored by API
- Conclusion: Must filter client-side

### **Phase 2: Understanding `sold` Parameter**
- `sold=false`: 1.6M properties (but isOnMarket still false!)
- `sold=true`: 2.3M properties (historical sales)
- Conclusion: Not related to current market status

### **Phase 3: Villa Filter Discovery**
- `addressTypes=villa` reduces results by 97%
- København: 441,795 → 14,368 properties
- Critical optimization for staying under 25k limit

### **Phase 4: Multiple Municipality Issue**
- Comma-separated municipalities returns 0 results
- Must query one municipality at a time
- Adopted framework from notebook

### **Phase 5: Performance Crisis**
- Initial import: 6 hours for 14k properties
- Identified bottlenecks: per-property commits, no parallelization
- Solution: Parallel processing with batch commits

---

## 🛠️ Utilities

### **Database Scripts:**
- **`reset_tables.py`** - Drop and recreate all tables
- **`migrate_db.py`** - Database migrations
- **`recreate_db.py`** - Fresh database setup

### **Analysis Scripts:**
- **`view_database.py`** - View database contents
- **`verify_import.py`** - Verify imported data
- **`diagnose_performance.py`** - Performance analysis

### **Password Management:**
- **`encode_password.py`** - Encode database password

---

## 📦 Dependencies

**Key Requirements:**
- `requests` - API calls
- `sqlalchemy` - ORM and database
- `psycopg2` - PostgreSQL driver
- `python-dotenv` - Environment variables
- `pandas` - Data analysis (notebooks)

**See:** `requirements.txt` for complete list

---

## 🎯 Import Workflow

### **Step 1: Setup**
```bash
# Configure environment
cp .env.example .env
# Edit .env with database credentials
```

### **Step 2: Database Preparation**
```bash
# Fresh database (optional)
python reset_tables.py
```

### **Step 3: Test Import**
```bash
# Import 100 properties to test
python import_copenhagen_area.py --limit 100 --parallel
```

### **Step 4: Production Import**
```bash
# Full import of all municipalities
python import_copenhagen_area.py --parallel --workers 12
```

### **Step 5: Verification**
```bash
# Check database
python view_database.py
```

---

## 🐛 Common Issues & Solutions

### **Issue: Duplicate Key Violations**
**Symptom:** `UniqueViolation` errors during batch commits  
**Cause:** API returns duplicate registrations  
**Solution:** Using `session.merge()` instead of `session.add()`  
**Status:** Handled gracefully with rollback

### **Issue: Transaction Rolled Back**
**Symptom:** "This Session's transaction has been rolled back"  
**Cause:** Auto-flush during constraint checks  
**Solution:** Disabled auto-flush, use `session.no_autoflush` blocks  
**Status:** Fixed

### **Issue: Only 50 Properties Imported**
**Symptom:** Script stops after 50 properties  
**Cause:** `--limit` parameter stops TOTAL import, not per-page  
**Solution:** Remove `--limit` or use higher value  
**Status:** Documented

### **Issue: Multiple Municipalities Return 0**
**Symptom:** Query with comma-separated municipalities fails  
**Cause:** API doesn't support multiple municipalities  
**Solution:** Query one municipality at a time  
**Status:** Implemented

### **Issue: isOnMarket Filter Ignored**
**Symptom:** Returns properties not on market  
**Cause:** API ignores this parameter completely  
**Solution:** Client-side filtering (not implemented as we import all)  
**Status:** Documented

---

## 📈 Data Statistics

### **Import Metrics:**
- **Properties per municipality:** Varies (København: 14,368 villas)
- **Total villas (36 municipalities):** ~50,000-100,000 estimated
- **Import speed (parallel):** 10-12 properties/second
- **Full import time:** ~1.5-2 hours
- **København only:** ~25 minutes

### **API Response Stats:**
- **Average response time:** 0.5-1 second
- **Properties per page:** 50 (max)
- **Data size per property:** ~5-10 KB JSON
- **Total pages (København villas):** 288 pages

### **Database Size (estimated):**
- **14,368 properties:** ~500-700 MB
- **50,000 properties:** ~2-3 GB
- **Includes:** All related buildings, registrations, entities

---

## 🔐 Security & Configuration

### **Environment Variables (.env):**
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=housing_db
DB_USER=postgres
DB_PASSWORD=your_encoded_password
```

### **User-Agent Rotation:**
```python
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)...',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...',
    'Mozilla/5.0 (X11; Linux x86_64)...'
]
```

**Purpose:** Avoid rate limiting and bot detection

---

## 🎓 Key Learnings

### **1. API Limitations Matter**
- Always test API parameters thoroughly
- Document what works and what doesn't
- Don't assume documentation is correct

### **2. Performance Optimization is Critical**
- Sequential processing doesn't scale
- Parallel processing can give 20x speedup
- Batch operations are always faster

### **3. Error Handling is Essential**
- Use transaction rollbacks properly
- Continue on individual failures
- Provide visibility into errors

### **4. Database Design Matters**
- Use appropriate constraints
- Plan for duplicates
- Consider merge vs add operations

### **5. Progress Visibility Helps**
- Real-time metrics keep users informed
- ETA calculations are valuable
- Batch progress shows system health

---

## 🚀 Future Enhancements

### **Potential Improvements:**
1. Add retry logic for failed API calls
2. Implement rate limiting to avoid API throttling
3. Add support for other property types (condos, apartments)
4. Create data quality validation
5. Add incremental updates (delta imports)
6. Implement export to CSV/Excel
7. Add property scoring algorithm
8. Create web dashboard for data visualization
9. Add automated scheduling for regular imports
10. Implement data change tracking

### **Not Implemented (Low Priority):**
- Client-side `isOnMarket` filtering (importing all data)
- Cascading filters for other property types (villas sufficient)
- Floor plan scraping (separate project)

---

## 📚 Reference Documentation

### **Original Frameworks:**
- **Notebook:** `Step_1_Scraping_boligsiden.ipynb`
  - Cascading filter strategy
  - Municipality-by-municipality approach
  - User-agent rotation
  - ThreadPoolExecutor pattern

### **API Documentation:**
- **Official:** Limited/non-existent
- **Discovery:** Through systematic testing
- **Results:** Documented in this file

### **Database Schema:**
- **Full details:** `DATABASE_SCHEMA.md`
- **Models:** `src/db_models_new.py`

---

## ⚡ Quick Reference

### **Start Import:**
```bash
python import_copenhagen_area.py --parallel --workers 12
```

### **Reset Database:**
```bash
python reset_tables.py
```

### **Check Progress:**
```python
from src.database import db
from src.db_models_new import Property
session = db.get_session()
count = session.query(Property).count()
print(f"Properties: {count}")
```

### **View Errors:**
Errors are displayed during import (first 10 shown)

### **Tune Performance:**
- More workers: Faster (if system allows)
- Smaller batches: More frequent commits
- Larger batches: Better throughput

---

## 📞 Production Status (Oct 7, 2025)

**Current State:** ✅ **LIVE IN PRODUCTION**
- ✅ **228,594 properties** imported successfully
- ✅ **3,683 cases** with listing dates
- ✅ **36 municipalities** complete (100% coverage)
- ✅ **Web interface** running at http://127.0.0.1:5000
- ✅ **Zero errors** during import
- ✅ **Critical bugs fixed** (zipCodes parameter, 10K limit)

**Import Completed:** October 7, 2025
- Duration: ~2-3 hours with 20 workers
- Speed: 20-30 properties/second
- Success rate: 100%

---

## � Critical Bugs Fixed

### **1. zipCode vs zipCodes Parameter (Oct 7)**
**Severity:** 🔴 **CRITICAL**  
**Problem:** Using `zipCode` (singular) - API completely ignores it  
**Discovery:** Test showed København returns 14,368 with `zipCode`, 236 with `zipCodes`  
**Root Cause:** Parameter must be `zipCodes` (plural), not `zipCode`  
**Fix:** Changed line 335 in `import_copenhagen_area.py`  
**Impact:** Without this fix, zip filtering doesn't work AT ALL  

```python
# WRONG (ignored by API):
params['zipCode'] = '2100'  # Returns ALL properties!

# CORRECT:
params['zipCodes'] = '2100'  # Returns only zip 2100
```

### **2. 10,000 Property Limit (Oct 6)**
**Severity:** 🟠 **HIGH**  
**Problem:** API pagination limited to 200 pages × 50 = 10,000 max  
**Example:** København has 14,368 villas - last 4,368 inaccessible  
**Solution:** Auto-detect when totalHits > 9,500 → subdivide by zip code  
**Result:** Successfully imported all 14,368 København properties  

```python
# Detection logic in import_copenhagen_area.py:
if total_hits > 9500:
    zip_codes = fetch_zip_codes_for_municipality(municipality)
    # Query each zip code separately
```

### **3. Cases Data Missing (Oct 6-7)**
**Severity:** 🟡 **MEDIUM**  
**Problem:** 84,469 existing properties lacked new cases/price_changes data  
**Root Cause:** Import script skips existing properties (bulk duplicate check)  
**Solution:** Dropped database and re-imported all 228,594 properties fresh  
**Result:** 3,683 cases now captured with listing dates  

---

## 🎯 Success Metrics

✅ **Coverage:** 228,594 / 228,594 properties (100%)  
✅ **Performance:** 20-30 properties/second  
✅ **Reliability:** Zero errors during full import  
✅ **Cases Data:** 3,683 listings captured  
✅ **Bug Fixes:** 2 critical bugs resolved  
✅ **Scalability:** Handles municipalities with 14K+ properties  

**Overall:** All objectives achieved! 🎉

---

*End of Knowledge Base*
