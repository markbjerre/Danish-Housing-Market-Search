# Periodic Database Update Strategy

**Created:** October 7, 2025  
**Purpose:** Keep database synchronized with Boligsiden API for market changes

---

## Overview

Two-pronged approach for maintaining data freshness:
1. **Discovery**: Find new properties that enter the market
2. **Refresh**: Update existing properties for changes (price, status, images, etc.)

---

## 🔍 PART 1: DISCOVERY - Finding New Properties

### Strategy Options

#### Option A: Geographic Scan (RECOMMENDED) ✅
**Method:** Periodically scan our 36 municipalities for new listings

**Pros:**
- Comprehensive coverage of target area
- Can use existing `import_copenhagen_area.py` logic
- Finds ALL new properties in our geographic scope
- No reliance on search filters

**Cons:**
- API intensive (need to search each municipality)
- May find properties we already have

**Implementation:**
```python
def discover_new_properties():
    """Scan municipalities for new properties not in database"""
    
    # Load our 36 target municipalities
    municipalities = load_municipalities_within_60km()
    
    new_properties = []
    
    for muni in municipalities:
        # Search API for properties in this municipality
        api_results = search_api_by_municipality(muni['code'])
        
        for result in api_results:
            property_id = result['addressID']
            
            # Check if already in database
            if not exists_in_db(property_id):
                new_properties.append(property_id)
    
    return new_properties
```

**Frequency:** Daily or every 12 hours

---

#### Option B: Active Listings Filter
**Method:** Query API for properties with `isOnMarket=true`

**Pros:**
- Directly targets active listings
- Fewer API calls
- Fast execution

**Cons:**
- May miss properties if filter not reliable
- Still need to check each result against database

**Implementation:**
```python
def discover_active_listings():
    """Find all active listings in target area"""
    
    # API call with filters
    results = api_search(
        address_types=['villa'],
        municipalities=OUR_36_MUNICIPALITIES,
        is_on_market=True
    )
    
    new_ids = []
    for prop in results:
        if not exists_in_db(prop['addressID']):
            new_ids.append(prop['addressID'])
    
    return new_ids
```

**Frequency:** Daily

---

#### Option C: Hybrid Approach
**Method:** Quick check for active listings + periodic full scan

**Schedule:**
- **Daily:** Check for `isOnMarket=true` properties (fast)
- **Weekly:** Full geographic scan to catch anything missed (comprehensive)

---

## 🔄 PART 2: REFRESH - Updating Existing Properties

### What Can Change?

1. **Case Status Changes:**
   - Price reductions/increases
   - Listing withdrawn (status changed to 'withdrawn')
   - Property sold (status changed to 'sold')
   - New case created (property re-listed)

2. **Property Details:**
   - Renovations (year_renovated, building conditions)
   - New registrations (sale transactions)
   - Energy label updates
   - Latest valuation changes

3. **Case Enrichment:**
   - Description updates
   - Image changes/additions
   - Realtor changes
   - Days on market increases

4. **Market Data:**
   - Municipality tax rates
   - Population changes

### Strategy Options

#### Option A: Update All Active Cases (RECOMMENDED) ✅
**Method:** Re-fetch API data for all properties with open cases

**Pros:**
- Keeps active listings fresh
- Catches price changes immediately
- Updates days on market
- Low volume (~3,683 properties currently)

**Cons:**
- Ignores sold properties (may want historical updates)
- ~3,700 API calls per run

**Implementation:**
```python
def refresh_active_cases():
    """Update all properties with open/active cases"""
    
    # Query database for properties with active cases
    active_properties = session.query(Property).join(Case).filter(
        Case.status.in_(['open', 'active'])
    ).all()
    
    print(f"Refreshing {len(active_properties)} properties with active cases...")
    
    updated = 0
    errors = 0
    
    for prop in active_properties:
        try:
            # Re-import from API (will update existing data)
            reimport_property_cases(prop.id)
            updated += 1
            
            # Rate limiting
            time.sleep(0.1)  # 10 requests/second
            
        except Exception as e:
            print(f"Error updating {prop.id}: {e}")
            errors += 1
    
    return updated, errors
```

**Frequency:** Daily for pricing, weekly for everything else

---

#### Option B: Selective Updates Based on Age
**Method:** Update properties based on how long since last update

**Pros:**
- Intelligent prioritization
- Reduces API load
- Fresh data where it matters

**Cons:**
- More complex logic
- May miss sudden changes

**Implementation:**
```python
def refresh_by_age():
    """Update properties based on staleness"""
    
    now = datetime.now()
    
    # Priority 1: Active cases not updated in 24 hours
    priority_1 = session.query(Property).join(Case).filter(
        Case.status == 'open',
        Case.imported_at < now - timedelta(hours=24)
    ).all()
    
    # Priority 2: Recently sold (within 30 days) not updated in 7 days
    priority_2 = session.query(Property).join(Case).filter(
        Case.status == 'sold',
        Case.sold_date > now - timedelta(days=30),
        Case.imported_at < now - timedelta(days=7)
    ).all()
    
    # Priority 3: All others not updated in 30 days
    priority_3 = session.query(Property).filter(
        Property.imported_at < now - timedelta(days=30)
    ).limit(1000).all()  # Batch limit
    
    # Update in priority order
    for prop in priority_1 + priority_2 + priority_3:
        reimport_property_cases(prop.id)
```

**Frequency:** Continuous (run daily, processes different properties each time)

---

#### Option C: Event-Driven Updates
**Method:** Monitor for specific triggers that indicate changes

**Triggers:**
- User views a property (refresh on-demand)
- Property shows in search results (background refresh)
- Scheduled high-priority updates (active listings)

**Pros:**
- Minimal API usage
- Data fresh when viewed
- User-centric

**Cons:**
- Requires more infrastructure
- May have stale data in search results

---

## 🎯 RECOMMENDED IMPLEMENTATION

### Phase 1: Basic Periodic Updates (IMMEDIATE)

**Daily Discovery Scan** (runs at 6 AM):
```python
def daily_discovery():
    """Find and import new properties"""
    
    # Scan for new properties in our 36 municipalities
    new_property_ids = discover_new_properties()
    
    print(f"Found {len(new_property_ids)} new properties")
    
    # Import each new property
    for property_id in new_property_ids:
        import_from_api(property_id)
```

**Daily Active Case Refresh** (runs at 2 PM):
```python
def daily_active_refresh():
    """Update all active listings"""
    
    # Get properties with open cases
    active_property_ids = get_properties_with_status('open')
    
    print(f"Refreshing {len(active_property_ids)} active listings...")
    
    # Re-import cases for each property
    for property_id in active_property_ids:
        reimport_property_cases(property_id)
        time.sleep(0.1)  # Rate limiting
```

**Frequency:**
- New property discovery: **Daily at 6 AM**
- Active case refresh: **Daily at 2 PM**
- Full database refresh: **Weekly on Sunday at 3 AM**

---

### Phase 2: Smart Updates (FUTURE)

**Incremental Updates:**
- Track `modified_date` from API
- Only re-import if API `modified_date` > database `imported_at`
- Saves ~80% of API calls

**Change Detection:**
```python
def needs_update(property_id):
    """Check if property needs updating"""
    
    # Quick API call to get metadata only
    api_metadata = get_api_metadata(property_id)
    db_record = get_db_record(property_id)
    
    # Compare modification dates
    if api_metadata['modified'] > db_record.imported_at:
        return True
    
    # Check case status changes
    if api_metadata['caseStatus'] != db_record.case_status:
        return True
    
    return False
```

**Webhooks (if available):**
- Subscribe to Boligsiden events (price changes, new listings)
- Real-time updates instead of polling

---

## 📊 MONITORING & OPTIMIZATION

### Metrics to Track

1. **Discovery Effectiveness:**
   - New properties found per scan
   - False positives (already in DB)
   - Coverage gaps

2. **Refresh Performance:**
   - Properties updated per run
   - API errors/timeouts
   - Average update duration
   - Data staleness (max age)

3. **API Usage:**
   - Total calls per day
   - Rate limit hits
   - Cost (if API is paid)

### Optimization Strategies

1. **Batch Processing:**
   - Update 100 properties at a time
   - Parallel requests (5-10 concurrent)
   - Exponential backoff on errors

2. **Smart Scheduling:**
   - Avoid peak hours (evenings)
   - Spread updates throughout day
   - Priority queue for user-requested updates

3. **Caching:**
   - Store API metadata (modified dates)
   - Quick staleness checks without full import
   - Reduce redundant updates

---

## 🔧 ADDITIONAL CONSIDERATIONS

### Data Integrity

1. **Conflict Resolution:**
   - What if case status changes from 'open' to 'sold'?
   - Keep history or overwrite?
   - **Solution:** Update existing case, don't create duplicate

2. **Deleted Listings:**
   - What if API returns 404?
   - Mark as 'deleted' or remove from DB?
   - **Solution:** Add `is_deleted` flag, keep data for historical analysis

3. **Price Change History:**
   - Already tracked in `price_changes` table ✅
   - Make sure to preserve when updating

### Error Handling

1. **API Failures:**
   - Retry logic (3 attempts)
   - Log failed property IDs
   - Re-attempt in next cycle

2. **Partial Updates:**
   - Transaction management (all or nothing)
   - Rollback on error
   - Mark update timestamp only on success

3. **Rate Limiting:**
   - Respect API limits
   - Queue-based processing
   - Automatic throttling

---

## 🚀 IMPLEMENTATION CHECKLIST

### Immediate (Next Steps):

- [ ] Create `periodic_updates.py` script
- [ ] Implement `discover_new_properties()` function
- [ ] Implement `refresh_active_cases()` function
- [ ] Add `reimport_property_cases()` helper (update without full re-import)
- [ ] Test update logic on single property
- [ ] Add logging for monitoring
- [ ] Schedule with cron/Task Scheduler

### Short-term (Next 2 Weeks):

- [ ] Add update timestamp tracking (`last_updated_at`)
- [ ] Implement age-based refresh priority
- [ ] Create update status dashboard
- [ ] Add error tracking and alerting
- [ ] Optimize API call batching

### Long-term (Next Month):

- [ ] Implement incremental update logic
- [ ] Add change detection before full re-import
- [ ] Create webhook handlers (if available)
- [ ] Build update analytics dashboard
- [ ] Performance optimization based on metrics

---

## 📋 EXAMPLE: COMPLETE UPDATE SCRIPT

```python
"""
periodic_updates.py - Automated database maintenance
Run daily via cron/Task Scheduler
"""

import time
from datetime import datetime, timedelta
from sqlalchemy import func
from import_api_data import import_from_api
from reimport_cases import reimport_property_cases

def discover_new_properties():
    """Scan for new properties in target municipalities"""
    # Implementation here
    pass

def refresh_active_cases():
    """Update all properties with active listings"""
    session = Session()
    
    # Get properties with open cases
    active_properties = session.query(Property.id).join(Case).filter(
        Case.status == 'open'
    ).distinct().all()
    
    property_ids = [p[0] for p in active_properties]
    
    print(f"[{datetime.now()}] Refreshing {len(property_ids)} active properties...")
    
    success = 0
    errors = 0
    
    for property_id in property_ids:
        try:
            reimport_property_cases(property_id)
            success += 1
            time.sleep(0.1)  # Rate limiting: 10 req/sec
        except Exception as e:
            print(f"Error updating {property_id}: {e}")
            errors += 1
    
    print(f"[{datetime.now()}] Complete: {success} updated, {errors} errors")
    session.close()
    
    return success, errors

def main():
    """Run daily update cycle"""
    
    print("="*80)
    print(f"PERIODIC UPDATE - {datetime.now()}")
    print("="*80)
    
    # Step 1: Discover new properties
    print("\n1. DISCOVERY: Scanning for new properties...")
    new_ids = discover_new_properties()
    print(f"   Found {len(new_ids)} new properties")
    
    # Import new properties
    for property_id in new_ids:
        import_from_api(property_id)
    
    # Step 2: Refresh active cases
    print("\n2. REFRESH: Updating active listings...")
    success, errors = refresh_active_cases()
    
    # Summary
    print("\n" + "="*80)
    print("UPDATE COMPLETE")
    print("="*80)
    print(f"New properties imported: {len(new_ids)}")
    print(f"Active cases updated: {success}")
    print(f"Errors encountered: {errors}")
    print("="*80)

if __name__ == "__main__":
    main()
```

---

## 🎯 FINAL RECOMMENDATION

**Start Simple, Scale Smart:**

1. **Week 1:** Daily refresh of active cases (3,683 properties)
2. **Week 2:** Add daily discovery scan for new properties
3. **Week 3:** Implement smart age-based updates
4. **Week 4:** Add monitoring and optimize based on metrics

This keeps your database fresh without overwhelming the API or your infrastructure.

**Next Action:** Create `periodic_updates.py` with basic daily refresh logic?
