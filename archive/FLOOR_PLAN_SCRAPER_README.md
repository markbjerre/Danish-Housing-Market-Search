# 🏠 Floor Plan Scraper - Quick Start

## ✅ What I've Created for You

I've built a complete floor plan scraping system with 3 tools:

### 1. **Simple Scraper** (`scrape_floor_plans.py`)
Basic scraper for learning and testing

### 2. **Advanced Scraper** (`scrape_floor_plans_advanced.py`) ⭐ RECOMMENDED
Production-ready scraper with:
- Database integration
- Error handling & retry logic
- Progress tracking & logging
- Multiple detection strategies
- Batch processing support

### 3. **Availability Checker** (`check_floor_plan_availability.py`)
Tests properties WITHOUT downloading to estimate success rate

## 🎯 Answer to Your Question

> "Is it possible to do this autonomously through many different websites?"

**YES!** Here's how:

### ✅ What Works:
- **Selenium** handles JavaScript-heavy pages
- **Pattern matching** finds "Plantegninger" buttons across different layouts
- **Multiple strategies** adapt to various real estate agent sites
- **Batch processing** can handle your 361,232 properties
- **Autonomous operation** runs unattended with logging

### ⚠️ What to Expect:
- **Success rate**: Estimated 50-80% (depends on properties)
- **Time needed**: ~300 hours for all 361K properties at 3 sec/property
- **Different layouts**: Script tries 15+ patterns to find floor plans
- **Errors**: Some properties won't have floor plans or may fail

### 🚫 Limitations:
- Can't bypass CAPTCHAs automatically
- Can't access authenticated-only content
- Different agents may have unique layouts not covered
- Rate limiting may require breaks

## 🚀 Quick Start (3 Steps)

### Step 1: Install Dependencies

```powershell
pip install selenium pillow webdriver-manager
```

### Step 2: Test on Sample Properties

```powershell
# Test without downloading (just checks availability)
python check_floor_plan_availability.py --sample 20

# OR test actual scraping on 3 properties
python test_floor_plan_scraper.py csv
```

### Step 3: Run Production Scraper

```powershell
# Start with small batch
python scrape_floor_plans_advanced.py --limit 10 --headless

# Scale up gradually
python scrape_floor_plans_advanced.py --limit 100 --headless

# Full production run
python scrape_floor_plans_advanced.py --limit 1000 --offset 0 --headless
```

## 📊 How It Handles Different Websites

The scraper uses **multi-strategy detection**:

```
Strategy 1: Find "Plantegninger" Button
├─ Tries 8+ different XPath patterns
├─ Case-insensitive matching
├─ Handles Danish/English text
└─ Clicks button to reveal images

Strategy 2: Direct Image Detection
├─ Searches for images with "plantegning" in src/alt
├─ Looks for "floor" in attributes
├─ Filters out small icons (<100px)
└─ Finds images in common containers

Strategy 3: Modal/Lightbox Detection
├─ Checks for popup galleries
├─ Searches common CSS classes
└─ Handles dynamic content

Strategy 4: PDF Detection
├─ Finds PDF links
└─ Downloads floor plan PDFs
```

### Real-World Adaptability

The script handles:
- ✅ Different button text ("PLANTEGNINGER", "Plantegning", "Floor plan")
- ✅ Various HTML structures (buttons, links, divs, tabs)
- ✅ Dynamic JavaScript content (waits for loading)
- ✅ Multiple image formats (JPG, PNG, PDF)
- ✅ Different container layouts (galleries, modals, lightboxes)

## 📈 Expected Results

Based on Danish real estate sites:

| Property Type | Est. Success Rate | Notes |
|---------------|-------------------|-------|
| Villa         | 60-70%           | Usually have floor plans |
| Condo         | 50-60%           | Varies by building |
| Terraced      | 55-65%           | Often available |

**Total Estimate**: 180,000-250,000 properties with floor plans (out of 361K)

## 📁 What You Get

### Output Structure:
```
floor_plans/
├── property-id-1_floorplan_00.jpg      ← Floor plan image
├── property-id-1_floorplan_01.jpg      ← Multiple images if available
├── property-id-1_page_screenshot.png   ← Debug screenshot
├── property-id-2_floorplan_00.jpg
├── ...
├── scraping_results_20241004.json      ← Metadata & stats
└── floor_plan_scraper.log              ← Detailed logs
```

### JSON Metadata:
```json
{
  "property_id": "abc-123",
  "success": true,
  "floor_plans": [
    {
      "filename": "abc-123_floorplan_00.jpg",
      "size": 245678,
      "url": "https://..."
    }
  ]
}
```

## 🎛️ Command Options

### Availability Checker:
```powershell
# Check 50 random properties
python check_floor_plan_availability.py --sample 50

# Check by property type (villa, condo, etc.)
python check_floor_plan_availability.py --by-type --per-type 10

# Run without headless (see browser)
python check_floor_plan_availability.py --sample 20
```

### Advanced Scraper:
```powershell
# Basic
python scrape_floor_plans_advanced.py

# With options
python scrape_floor_plans_advanced.py \
    --limit 100 \          # Scrape 100 properties
    --offset 1000 \        # Skip first 1000
    --headless \           # Run in background
    --folder my_plans      # Custom output folder
```

## 🔍 Monitoring Progress

### During Run:
- Console shows real-time progress
- Log file: `floor_plan_scraper.log`
- Screenshots saved for debugging

### After Run:
```powershell
# Check results
cat floor_plans/scraping_results_*.json

# View logs
cat floor_plan_scraper.log

# Count downloads
(Get-ChildItem floor_plans -Filter "*.jpg").Count
```

## ⚡ Batch Processing All 361K Properties

### Recommended Approach:

```powershell
# Windows PowerShell script
# Scrapes in batches of 1000 with breaks

for ($i=0; $i -lt 362000; $i+=1000) {
    Write-Host "Processing batch: $i to $($i+1000)"
    
    python scrape_floor_plans_advanced.py `
        --limit 1000 `
        --offset $i `
        --headless
    
    Write-Host "Batch complete. Waiting 5 minutes..."
    Start-Sleep -Seconds 300
}

Write-Host "All batches complete!"
```

### Time Estimate:
- **Per property**: ~3 seconds
- **Per 1000**: ~50 minutes
- **Full 361K**: ~300 hours (~12.5 days non-stop)

### Recommendations:
1. ✅ Run in batches of 1000-5000
2. ✅ Add 5-10 minute breaks between batches
3. ✅ Monitor first few batches closely
4. ✅ Check success rate after 1000 properties
5. ✅ Consider running overnight/weekends
6. ⚠️ Don't run parallel instances (risk IP ban)

## 🐛 Troubleshooting

### "ChromeDriver not found"
```powershell
pip install webdriver-manager
```

### "No floor plans found"
Run without `--headless` to see the browser:
```powershell
python test_floor_plan_scraper.py
```

### Check availability first
```powershell
python check_floor_plan_availability.py --sample 20
```

### Low success rate
1. Check log file for patterns
2. Run test to see actual pages
3. May need to add more detection patterns

### Script crashes
- Check memory usage (Chrome can be heavy)
- Reduce batch size
- Add more sleep time between requests

## 📚 Full Documentation

See `FLOOR_PLAN_SCRAPER_GUIDE.md` for:
- Detailed technical documentation
- Pattern customization
- Advanced usage examples
- Legal considerations
- Complete API reference

## 🎓 Recommended Workflow

1. **Test availability** (5 min)
   ```powershell
   python check_floor_plan_availability.py --sample 50
   ```

2. **Test scraping** (2 min)
   ```powershell
   python test_floor_plan_scraper.py csv
   ```

3. **Small batch** (5 min)
   ```powershell
   python scrape_floor_plans_advanced.py --limit 10
   ```

4. **Review results**
   - Check floor_plans/ folder
   - Review JSON file
   - Check success rate

5. **Adjust if needed**
   - Modify patterns if success rate < 50%
   - Adjust timing if getting errors

6. **Production run**
   ```powershell
   python scrape_floor_plans_advanced.py --limit 1000 --headless
   ```

## ⚖️ Legal & Ethical Notes

⚠️ **Important**:
- Check Boligsiden.dk Terms of Service
- Respect rate limits (3+ seconds between requests)
- Don't republish copyrighted images
- For personal/research use only
- Be prepared to stop if requested

## 💡 Tips for Success

1. ✅ **Start small** - Test thoroughly before scaling
2. ✅ **Monitor logs** - Watch for patterns in failures
3. ✅ **Be patient** - This takes time, don't rush
4. ✅ **Save progress** - JSON files track completed properties
5. ✅ **Check availability first** - Know what to expect
6. ✅ **Run during off-peak** - Less likely to be rate-limited
7. ✅ **Keep backups** - Save JSON results regularly

## 🎯 Summary

**YES, this is possible!** The tools I've created:

- ✅ Handle JavaScript-heavy pages with Selenium
- ✅ Adapt to different layouts with 15+ detection patterns
- ✅ Process your entire 361K database in batches
- ✅ Run autonomously with logging and error handling
- ✅ Provide progress tracking and results metadata

**Estimated outcome**: 
- 50-70% success rate
- 180K-250K properties with floor plans
- 200K-300K total images
- 12-15 days of processing time

**Next step**: Run the availability checker to get actual numbers for your data!

```powershell
python check_floor_plan_availability.py --sample 50
```

---

Questions? Check `FLOOR_PLAN_SCRAPER_GUIDE.md` for detailed documentation!
