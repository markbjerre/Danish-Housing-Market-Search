# 🔍 Tool Comparison Guide

## Which Tool Should You Use?

| Feature | Availability Checker | Test Scraper | Simple Scraper | Advanced Scraper ⭐ |
|---------|---------------------|--------------|----------------|---------------------|
| **Purpose** | Estimate success rate | Validate setup | Learn/experiment | Production use |
| **Downloads images** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Database integration** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Batch processing** | ✅ Yes | ❌ No | ⚠️ Limited | ✅ Full |
| **Error handling** | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic | ✅ Advanced |
| **Retry logic** | ❌ No | ❌ No | ❌ No | ✅ Yes (3x) |
| **Progress tracking** | ⚠️ Basic | ⚠️ Basic | ⚠️ Basic | ✅ Detailed |
| **Logging** | ⚠️ Console | ⚠️ Console | ⚠️ Console | ✅ File + Console |
| **JSON results** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Screenshots** | ❌ No | ⚠️ Optional | ❌ No | ✅ Yes |
| **Resume capability** | ❌ No | ❌ No | ❌ No | ✅ Yes (--offset) |
| **Detection patterns** | ~5 | ~5 | ~5 | 15+ |
| **Headless mode** | ✅ Optional | ✅ Optional | ✅ Optional | ✅ Recommended |
| **Speed** | ⚡⚡⚡ Fast | ⚡⚡ Medium | ⚡⚡ Medium | ⚡⚡ Medium |
| **Complexity** | Simple | Simple | Simple | Advanced |
| **Best for** | Initial assessment | Testing setup | Learning | Production |

---

## 🎯 Decision Tree

```
START: What do you want to do?
  │
  ├─► "Just check if properties have floor plans"
  │   └─► Use: check_floor_plan_availability.py
  │       Command: python check_floor_plan_availability.py --sample 50
  │
  ├─► "Test if the scraper works at all"
  │   └─► Use: test_floor_plan_scraper.py
  │       Command: python test_floor_plan_scraper.py csv
  │
  ├─► "Learn how the scraping works"
  │   └─► Use: scrape_floor_plans.py
  │       Read the code, modify patterns, experiment
  │
  └─► "Download floor plans from many properties"
      └─► Use: scrape_floor_plans_advanced.py ⭐
          Command: python scrape_floor_plans_advanced.py --limit 1000 --headless
```

---

## 📋 Recommended Workflow

### Phase 1: Assessment (5 minutes)
```powershell
# Estimate success rate on 50 random properties
python check_floor_plan_availability.py --sample 50
```

**Expected output:**
- `floor_plan_availability_check.csv` with results
- Console summary showing % with floor plans
- Estimated total for full database

**Decision point:**
- ✅ If >50% success rate → Proceed to Phase 2
- ⚠️ If 30-50% → May need pattern adjustments
- ❌ If <30% → Review log, may need custom patterns

---

### Phase 2: Validation (5 minutes)
```powershell
# Test actual downloads on 3 properties
python test_floor_plan_scraper.py csv
```

**Expected output:**
- `floor_plans_test/` folder with downloads
- Console showing what was found
- Visual confirmation in browser (if not headless)

**Decision point:**
- ✅ Files downloaded → Proceed to Phase 3
- ⚠️ Some files downloaded → Check logs, may be OK
- ❌ No files downloaded → Debug with visible browser

---

### Phase 3: Small Batch (30 minutes)
```powershell
# Download from 50 properties
python scrape_floor_plans_advanced.py --limit 50 --headless
```

**Expected output:**
- `floor_plans/` folder with images
- `scraping_results_*.json` with metadata
- `floor_plan_scraper.log` with details

**Check:**
- Success rate matches Phase 1 estimate?
- Image quality good?
- Any common errors in log?

**Decision point:**
- ✅ Success rate >50%, images good → Scale up
- ⚠️ Success rate 30-50% → May need adjustments
- ❌ Success rate <30% → Review patterns

---

### Phase 4: Medium Batch (2 hours)
```powershell
# Download from 500 properties
python scrape_floor_plans_advanced.py --limit 500 --headless
```

**Monitor:**
- Check progress every 30 minutes
- Review logs for consistent errors
- Verify image quality on samples

**Decision point:**
- ✅ Stable performance → Proceed to production
- ⚠️ Occasional errors → Acceptable, continue
- ❌ Many errors → Investigate before scaling

---

### Phase 5: Production (Days/Weeks)
```powershell
# Process in batches of 1000
for ($i=0; $i -lt 362000; $i+=1000) {
    python scrape_floor_plans_advanced.py --limit 1000 --offset $i --headless
    Start-Sleep -Seconds 300
}
```

**Monitor:**
- Check JSON results after each batch
- Monitor disk space (images can be large)
- Track cumulative success rate
- Review logs for new error patterns

---

## 🎓 Tool Details

### 1. Availability Checker
**File:** `check_floor_plan_availability.py`

**Purpose:** Quick reconnaissance without downloading

**Use when:**
- ✅ Starting a new project
- ✅ Want to estimate total downloads
- ✅ Testing new detection patterns
- ✅ Analyzing by property type

**Don't use when:**
- ❌ You want actual images
- ❌ Need detailed metadata

**Output:**
- CSV file with availability stats
- Console summary with percentages

**Example usage:**
```powershell
# Random sample
python check_floor_plan_availability.py --sample 100

# By property type
python check_floor_plan_availability.py --by-type --per-type 20

# Visible browser (to see what it finds)
python check_floor_plan_availability.py --sample 20
```

---

### 2. Test Scraper
**File:** `test_floor_plan_scraper.py`

**Purpose:** Interactive testing and validation

**Use when:**
- ✅ First time running
- ✅ Validating setup
- ✅ Debugging issues
- ✅ Want to see browser in action

**Don't use when:**
- ❌ Processing many properties
- ❌ Need production features

**Output:**
- `floor_plans_test/` folder
- Visual feedback in browser
- Console messages

**Example usage:**
```powershell
# Interactive mode (choose option)
python test_floor_plan_scraper.py

# Automatic mode (from CSV)
python test_floor_plan_scraper.py csv
```

---

### 3. Simple Scraper
**File:** `scrape_floor_plans.py`

**Purpose:** Educational, simple code to understand

**Use when:**
- ✅ Learning how it works
- ✅ Want to modify code
- ✅ Experimenting with patterns
- ✅ Building custom version

**Don't use when:**
- ❌ Need production reliability
- ❌ Processing large batches
- ❌ Need resume capability

**Output:**
- `floor_plans/` folder
- Basic console output

**Example usage:**
```python
from scrape_floor_plans import FloorPlanScraper

scraper = FloorPlanScraper()
properties = [("id1", "url1"), ("id2", "url2")]
scraper.scrape_multiple_properties(properties)
scraper.close()
```

---

### 4. Advanced Scraper ⭐
**File:** `scrape_floor_plans_advanced.py`

**Purpose:** Production-ready, feature-complete

**Use when:**
- ✅ Processing many properties
- ✅ Need reliability
- ✅ Want detailed logs
- ✅ Need to resume jobs
- ✅ Production deployment

**Don't use when:**
- ❌ Just testing (use test scraper)
- ❌ Learning (use simple scraper)

**Output:**
- `floor_plans/` folder with images
- JSON results with metadata
- Detailed log file
- Debug screenshots

**Example usage:**
```powershell
# Basic
python scrape_floor_plans_advanced.py

# Full options
python scrape_floor_plans_advanced.py \
    --limit 1000 \
    --offset 5000 \
    --headless \
    --folder custom_folder
```

**Advanced Python usage:**
```python
from scrape_floor_plans_advanced import AdvancedFloorPlanScraper

scraper = AdvancedFloorPlanScraper(
    download_folder="floor_plans",
    headless=True
)

try:
    # From database
    results = scraper.scrape_from_database(limit=100, offset=0)
    
    # Or specific properties
    result = scraper.scrape_property(
        property_id="abc-123",
        property_url="https://..."
    )
    
    # Check results
    print(f"Success: {result['success']}")
    print(f"Images: {len(result['floor_plans'])}")
    
finally:
    scraper.close()
```

---

## 🚀 Quick Command Reference

### Availability Checker
```powershell
# Basic check
python check_floor_plan_availability.py --sample 50

# By property type
python check_floor_plan_availability.py --by-type

# Large sample
python check_floor_plan_availability.py --sample 200 --headless
```

### Test Scraper
```powershell
# Interactive
python test_floor_plan_scraper.py

# Automatic (from CSV)
python test_floor_plan_scraper.py csv
```

### Advanced Scraper
```powershell
# Development
python scrape_floor_plans_advanced.py --limit 10

# Small batch
python scrape_floor_plans_advanced.py --limit 100 --headless

# Production
python scrape_floor_plans_advanced.py --limit 1000 --offset 0 --headless

# Resume from property 5000
python scrape_floor_plans_advanced.py --limit 1000 --offset 5000 --headless

# Custom folder
python scrape_floor_plans_advanced.py --folder my_floor_plans --limit 100
```

---

## 🎯 Performance Comparison

| Tool | Speed per Property | Memory Usage | Best Batch Size |
|------|-------------------|--------------|-----------------|
| Availability Checker | ~2 sec | Low | 100-500 |
| Test Scraper | ~3 sec | Medium | 1-10 |
| Simple Scraper | ~3 sec | Medium | 10-100 |
| Advanced Scraper | ~3 sec | Medium-High | 100-5000 |

**Notes:**
- Speed varies by page complexity
- Memory increases with batch size
- Headless mode saves ~20-30% memory

---

## 💡 Tips

### For First-Time Users:
1. Start with availability checker
2. Then test scraper
3. Small batch with advanced scraper
4. Scale up gradually

### For Production Use:
1. Use only advanced scraper
2. Run in headless mode
3. Process in batches of 1000
4. Monitor logs regularly
5. Keep JSON results safe

### For Debugging:
1. Use test scraper without headless
2. Check page screenshots
3. Review log files
4. Try availability checker first

### For Custom Patterns:
1. Start with simple scraper
2. Modify detection patterns
3. Test with test scraper
4. Port to advanced scraper

---

## 📊 Feature Matrix

| Feature | Checker | Test | Simple | Advanced |
|---------|---------|------|--------|----------|
| Multi-pattern detection | ⚠️ 5 | ⚠️ 5 | ⚠️ 5 | ✅ 15+ |
| Auto ChromeDriver | ✅ | ✅ | ✅ | ✅ |
| Retry on failure | ❌ | ❌ | ❌ | ✅ 3x |
| Progress percentage | ❌ | ❌ | ❌ | ✅ |
| JSON metadata | ❌ | ❌ | ❌ | ✅ |
| Log file | ❌ | ❌ | ❌ | ✅ |
| Screenshots | ❌ | ⚠️ | ❌ | ✅ |
| Resume capability | ❌ | ❌ | ❌ | ✅ |
| CSV export | ✅ | ❌ | ❌ | ⚠️ Via JSON |
| Database integration | ✅ | ✅ | ✅ | ✅ |
| Batch processing | ✅ | ❌ | ⚠️ | ✅ |
| Error recovery | ❌ | ❌ | ❌ | ✅ |
| Statistics | ✅ | ⚠️ | ❌ | ✅ |

Legend:
- ✅ Full support
- ⚠️ Partial/basic support
- ❌ Not available

---

## 🎓 Summary

**Quick Assessment:** → Availability Checker
**Testing Setup:** → Test Scraper  
**Learning/Experimenting:** → Simple Scraper
**Production Use:** → Advanced Scraper ⭐

**Recommended path:**
1. Availability Checker (5 min)
2. Test Scraper (5 min)
3. Advanced Scraper small batch (30 min)
4. Advanced Scraper production (hours/days)

---

**Questions? See:**
- Quick Start: `FLOOR_PLAN_SCRAPER_README.md`
- Full Guide: `FLOOR_PLAN_SCRAPER_GUIDE.md`
- Architecture: `SYSTEM_ARCHITECTURE.txt`
- Summary: `FLOOR_PLAN_SOLUTION_SUMMARY.md`
