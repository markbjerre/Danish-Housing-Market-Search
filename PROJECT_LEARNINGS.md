# Project Learnings - Technical Decisions & Insights

**Last Updated:** October 7, 2025

---

## 🔌 API DISCOVERIES

### Critical Field Name Issues
- **`priceCash` not `price`** - Primary listing price field
- **`zipCodes` not `zipCode`** - Must be plural for filtering
- **`size` is object** - Parse `size.width` and `size.height`, not string
- **`alt` not `altText`** - Image accessibility text field
- **`isOnMarket` doesn't work** - Filter ignored by API

### API Limitations
- **10,000 max results** - 200 pages × 50 per page (NOT 25,000!)
- **Single municipality only** - Can't filter multiple at once
- **Rate limits exist** - Stay under 10 req/sec for safety
- **Pagination is strict** - No way around the 10K limit except subdivision

### Working Filters
✅ `municipalities` - Single name  
✅ `zipCodes` - Comma-separated list (PLURAL!)  
✅ `addressTypes` - villa, condo, etc.  
✅ `priceMin/Max` - Price ranges  
✅ `areaMin/Max` - Size ranges  
✅ `sold=false` - Active listings only

---

## 🏗️ ARCHITECTURE DECISIONS

### Why Store Image URLs Instead of Files?
**Decision:** Store CDN URLs, not download images  
**Rationale:**
- URLs: ~5 MB total
- Downloaded: ~180-370 GB total
- Boligsiden CDN is professional (fast, reliable)
- Multiple responsive sizes already available
- WebP format (modern, efficient)

**Trade-off:** External dependency, but acceptable for this use case

### Why 14 Normalized Tables?
**Decision:** Split data across 14 tables vs. one huge table  
**Rationale:**
- Flexibility for queries
- Avoid data duplication
- Each table has clear purpose
- Easy to add new data types
- Better for incremental updates

**Trade-off:** More complex queries, but worth it for maintainability

### Why Parquet for Backups?
**Decision:** Use Parquet format for database exports  
**Rationale:**
- Columnar format (efficient compression)
- Fast to read/write
- Preserves data types
- Widely supported
- Better than CSV for large datasets

**Trade-off:** Less human-readable than CSV, but tools exist

### Why Re-Import Cases Only?
**Decision:** Separate function to update cases without touching properties  
**Rationale:**
- Property data rarely changes (address, building details)
- Case data changes frequently (prices, status, images)
- Faster updates (skip building/registration processing)
- Reduces API calls

**Trade-off:** More complex import logic, but much faster updates

---

## ⚡ PERFORMANCE OPTIMIZATIONS

### Parallel Processing (20x Speedup)
**Problem:** Sequential import took 60+ hours  
**Solution:** ThreadPoolExecutor with 20 workers  
**Result:** 2-3 hours for 228K properties  
**Learning:** I/O-bound tasks benefit massively from parallelization

### Batch Progress Tracking
**Problem:** No visibility into long-running imports  
**Solution:** Progress updates every 100 properties  
**Result:** Better user experience, easier debugging  
**Learning:** Feedback matters even for automated processes

### Skip Existing Properties
**Problem:** Re-importing same data wastes time  
**Solution:** Check database before API call  
**Result:** Incremental imports are fast  
**Learning:** Database check is cheaper than API call

### Zip Code Subdivision
**Problem:** 10K limit blocks large municipalities  
**Solution:** Auto-split by zip codes when > 9,500 results  
**Result:** Successfully imported København (14,368 villas)  
**Learning:** Creative workarounds for API limitations

---

## 🐛 BUG FIXES & ROOT CAUSES

### 1. Missing Prices (Oct 7, 2025)
**Symptom:** All 3,683 cases had NULL prices  
**Root Cause:** `case_data.get('price')` but API uses `priceCash`  
**Fix:** Changed to `case_data.get('priceCash')`  
**Lesson:** Never assume field names, always check API response

### 2. Zip Filtering Broken (Oct 6, 2025)
**Symptom:** Zip code filter had no effect  
**Root Cause:** Used `zipCode` (singular) parameter  
**Fix:** Changed to `zipCodes` (plural)  
**Lesson:** API documentation may be incomplete/wrong

### 3. No Images Imported
**Symptom:** case_images table stayed empty  
**Root Cause:** Expected `size` as "600x400" string, but it's `{width: 600, height: 400}` object  
**Fix:** Parse `source.get('size', {}).get('width')` and `.get('height')`  
**Lesson:** API responses can have nested structures

### 4. 10K Limit Hit
**Symptom:** København missing 4,368 properties  
**Root Cause:** API hard limit of 200 pages × 50 = 10,000  
**Fix:** Auto-subdivide by zip codes  
**Lesson:** Pagination limits are real, plan for workarounds

---

## 📊 DATA QUALITY INSIGHTS

### Coverage Statistics
- **Coordinates:** 100% (all properties have lat/lon)
- **Prices:** 100% for active cases (0% for old cases)
- **Images:** 96% have at least one image
- **Descriptions:** 96% have title (realtor-dependent)
- **Building details:** 95% have year built
- **Transaction history:** 81% have at least one sale

### Data Quirks
- **Energy labels** - Many NULL (not required pre-2010)
- **Room counts** - Sometimes missing for old properties
- **Basement area** - Often 0, not NULL (means no basement)
- **Year renovated** - Sparse data (many never renovated)
- **Property numbers** - Sometimes duplicated (subdivided lots)

### API Behavior
- **Deleted listings return 404** - Handle gracefully
- **Modified dates** - Can use for incremental updates
- **Image URLs** - Stable (UUID-based)
- **Realtor info** - Changes when listing changes hands
- **Price history** - Only for current case, not all-time

---

## 🎯 BEST PRACTICES DISCOVERED

### Import Strategy
1. **Start with test import** (100 properties) to verify setup
2. **Use parallel processing** for production imports
3. **Monitor progress** with logging and counters
4. **Handle errors gracefully** (retry, log, continue)
5. **Verify data quality** after import (run verification script)

### Update Strategy
1. **Daily updates for active listings** - Most important for users
2. **Weekly full refresh** - Catch edge cases
3. **Monthly cleanup** - Keep database optimized
4. **Rate limiting** - Respect API, avoid bans
5. **Incremental updates** - Only re-import what changed

### Database Management
1. **Regular backups** - Parquet exports for safety
2. **Schema migrations** - Add columns with ALTER TABLE (not DROP)
3. **Transaction management** - Commit in batches, not per-record
4. **Index strategically** - Foreign keys and frequently queried fields
5. **Monitor size** - Database will grow, plan for it

### Code Organization
1. **Separate concerns** - Import, update, web app in different files
2. **Reusable functions** - import_cases() used by multiple scripts
3. **Clear naming** - Function names describe what they do
4. **Document decisions** - Comments explain *why*, not *what*
5. **Version control** - Git for tracking changes

---

## 💡 KEY TAKEAWAYS

### For Future LLM Agents:
1. **Check actual API responses** - Don't trust documentation alone
2. **Test with small dataset first** - Catch issues early
3. **Monitor long-running processes** - Progress bars save sanity
4. **Plan for scale** - What works for 100 won't work for 100K
5. **Keep it simple** - Complexity grows fast, fight it

### For Future Development:
1. **Image storage decision was right** - URLs work perfectly
2. **Normalized schema was right** - Flexibility pays off
3. **Parallel processing essential** - Sequential is too slow
4. **Update strategy works** - Daily + weekly + monthly is good balance
5. **Documentation matters** - This file will save hours later

---

## 🔮 FUTURE CONSIDERATIONS

### Potential Improvements:
- **Webhooks** - If Boligsiden offers them, use instead of polling
- **Caching** - Store API metadata to reduce unnecessary calls
- **Change detection** - Compare modified dates before full re-import
- **Database optimization** - Consider merging one-to-one tables
- **Full-text search** - PostgreSQL FTS for descriptions
- **Geographic queries** - PostGIS for radius searches

### Known Limitations:
- **External dependency** - Boligsiden API availability
- **Image dependency** - CDN URLs could break
- **Rate limits** - Unknown exact limits
- **API changes** - Field names could change
- **Historical data** - Limited to what API provides

---

**This document captures hard-won knowledge. Future you (or future LLM) will thank you for writing it down!**
