# Floor Plan (Plantegninger) Scraper - Complete Guide

## 📋 Overview

This scraper automatically downloads floor plans from Boligsiden.dk property pages. It handles:
- ✅ Dynamic JavaScript content
- ✅ Multiple real estate agent layouts
- ✅ Different button/link patterns for "Plantegninger"
- ✅ Both images and PDFs
- ✅ Batch processing from your database
- ✅ Error handling and retry logic
- ✅ Progress tracking and logging

## 🎯 Is This Possible?

**YES**, but with these considerations:

### ✅ Feasible Aspects:
1. **Selenium automation** can handle JavaScript-heavy sites
2. **Pattern matching** can find floor plans across different agent sites
3. **Batch processing** works for large datasets (your 361K properties)
4. **Error handling** manages failed requests gracefully

### ⚠️ Challenges:
1. **Different layouts** - Each real estate agent may structure pages differently
2. **Rate limiting** - Scraping too fast may get you blocked
3. **Dynamic content** - Some sites load content via AJAX/fetch
4. **Legal considerations** - Check Boligsiden's Terms of Service
5. **Time** - Scraping 361K properties at 3 seconds each = ~300 hours

### 🚫 Limitations:
- Cannot handle CAPTCHA automatically
- May miss floor plans behind authentication
- Cannot access expired/sold listings
- Image quality depends on source

## 📦 Installation

### Step 1: Install Dependencies

```powershell
pip install selenium pillow webdriver-manager
```

Or use the requirements file:
```powershell
pip install -r requirements.txt
```

### Step 2: Install ChromeDriver

**Option A: Automatic (Recommended)**
The script uses `webdriver-manager` to auto-download ChromeDriver.

**Option B: Manual**
1. Download ChromeDriver: https://chromedriver.chromium.org/
2. Add to PATH or place in project folder

### Step 3: Verify Installation

```powershell
python -c "from selenium import webdriver; print('Selenium OK')"
```

## 🧪 Testing

### Test 1: Single Property

```powershell
python test_floor_plan_scraper.py
```

This runs an interactive test where you can choose to test:
1. A single property (you specify the URL)
2. Multiple properties from your CSV file

### Test 2: From CSV (Automatic)

```powershell
python test_floor_plan_scraper.py csv
```

This tests on the first 3 properties from your example CSV.

**What to look for:**
- Browser opens (if not headless)
- Page loads
- Script attempts to find "Plantegninger" button
- Screenshots saved to `floor_plans_test/`
- Images downloaded (if found)

## 🚀 Usage

### Basic Usage: Scrape from Database

```powershell
# Scrape 10 properties (default)
python scrape_floor_plans_advanced.py

# Scrape 50 properties
python scrape_floor_plans_advanced.py --limit 50

# Scrape in headless mode (no visible browser)
python scrape_floor_plans_advanced.py --limit 100 --headless

# Skip first 1000, scrape next 100
python scrape_floor_plans_advanced.py --limit 100 --offset 1000

# Custom download folder
python scrape_floor_plans_advanced.py --folder my_floor_plans
```

### Advanced Usage: Python Script

```python
from scrape_floor_plans_advanced import AdvancedFloorPlanScraper

# Create scraper
scraper = AdvancedFloorPlanScraper(
    download_folder="floor_plans",
    headless=True  # Run in background
)

try:
    # Option 1: Scrape from database
    results = scraper.scrape_from_database(limit=50, offset=0)
    
    # Option 2: Scrape specific properties
    properties = [
        ("property-id-1", "https://www.boligsiden.dk/addresses/property-id-1"),
        ("property-id-2", "https://www.boligsiden.dk/addresses/property-id-2"),
    ]
    
    for prop_id, url in properties:
        result = scraper.scrape_property(prop_id, url)
        print(f"{prop_id}: {len(result['floor_plans'])} floor plans")

finally:
    scraper.close()
```

## 📁 Output Structure

```
floor_plans/
├── {property_id}_floorplan_00.jpg
├── {property_id}_floorplan_01.jpg
├── {property_id}_page_screenshot.png
├── scraping_results_20241004_143022.json
└── ...
```

### Output Files:
- **Floor plans**: `{property_id}_floorplan_{index}.{jpg|png|pdf}`
- **Screenshots**: `{property_id}_page_screenshot.png` (for debugging)
- **Results JSON**: Contains metadata about scraping session

### JSON Result Format:
```json
{
  "property_id": "abc-123",
  "url": "https://www.boligsiden.dk/addresses/abc-123",
  "timestamp": "2024-10-04T14:30:22",
  "success": true,
  "floor_plans": [
    {
      "filename": "abc-123_floorplan_00.jpg",
      "filepath": "C:\\...\\floor_plans\\abc-123_floorplan_00.jpg",
      "size": 245678,
      "url": "https://...",
      "extension": "jpg"
    }
  ],
  "error": null
}
```

## 🔧 How It Works

### 1. Pattern Matching Strategy

The scraper tries multiple strategies to find floor plans:

**Strategy 1: Click "Plantegninger" button**
- Searches for buttons/links with text "plantegning"
- Case-insensitive matching
- Multiple XPath patterns

**Strategy 2: Direct image search**
- Looks for images with "plantegning" in src/alt
- Checks for "floor" in attributes
- Filters out small images (icons)

**Strategy 3: Modal/Lightbox detection**
- Checks for images in popups
- Looks in gallery containers
- Searches common CSS classes

**Strategy 4: PDF detection**
- Finds PDF links with "plantegning" text

### 2. Download Process

```
1. Load property page → Wait 3 seconds
2. Take screenshot (for debugging)
3. Try to click plantegning button
4. Extract all image URLs using patterns
5. Filter images (size, quality)
6. Download each image with retry logic
7. Save metadata to JSON
8. Move to next property
```

### 3. Retry Logic

- 3 attempts per download
- 2-second delay between retries
- 3-second delay between properties (politeness)

## ⚙️ Configuration

### Modify Search Patterns

Edit `PLANTEGNING_PATTERNS` in `scrape_floor_plans_advanced.py`:

```python
PLANTEGNING_PATTERNS = [
    "//button[contains(text(), 'YOUR_PATTERN')]",
    # Add more patterns
]
```

### Adjust Timing

```python
scraper = AdvancedFloorPlanScraper(...)

# In scrape_property method:
time.sleep(3)  # Change page load wait time

# Between properties:
time.sleep(3)  # Change politeness delay
```

### Change Image Filtering

```python
# In extract_images method:
if int(width) < 100 or int(height) < 100:  # Adjust minimum size
    continue
```

## 📊 Batch Processing Large Datasets

For your 361,232 properties:

### Approach 1: Batches of 1000

```powershell
# Windows PowerShell script
for ($i=0; $i -lt 362000; $i+=1000) {
    python scrape_floor_plans_advanced.py --limit 1000 --offset $i --headless
    Start-Sleep -Seconds 60  # 1 minute break between batches
}
```

### Approach 2: Parallel Processing

```python
# Run multiple scrapers in parallel (careful with rate limits!)
from multiprocessing import Process

def scrape_batch(offset, limit):
    scraper = AdvancedFloorPlanScraper(
        download_folder=f"floor_plans_batch_{offset}",
        headless=True
    )
    scraper.scrape_from_database(limit=limit, offset=offset)
    scraper.close()

# Run 4 parallel batches
processes = []
for i in range(0, 4000, 1000):
    p = Process(target=scrape_batch, args=(i, 1000))
    processes.append(p)
    p.start()

for p in processes:
    p.join()
```

**⚠️ Warning**: Parallel scraping may get you IP-banned. Use with caution.

## 🐛 Troubleshooting

### Issue: ChromeDriver not found
**Solution**: 
```powershell
pip install webdriver-manager
```
The script will auto-download the correct version.

### Issue: No floor plans found
**Possible causes**:
1. Property page doesn't have floor plans
2. Different layout not covered by patterns
3. JavaScript not fully loaded

**Solution**: Run without `--headless` to see what's happening

### Issue: Browser opens but closes immediately
**Cause**: Error in script before scraping starts

**Solution**: Check logs in `floor_plan_scraper.log`

### Issue: Downloads are corrupted
**Cause**: Network issues or wrong content type

**Solution**: Check file extensions and URLs in JSON results

### Issue: Script is too slow
**Solutions**:
1. Increase timeout: `WebDriverWait(self.driver, 5)`  # Reduce from 10
2. Reduce sleep times: `time.sleep(1)`  # Instead of 3
3. Use `--headless` flag

### Issue: Getting blocked/banned
**Solutions**:
1. Increase delays between requests
2. Use rotating proxies
3. Add random delays: `time.sleep(random.uniform(2, 5))`
4. Respect robots.txt

## 📜 Legal Considerations

### ⚠️ Important:
1. **Check Terms of Service**: Boligsiden.dk may prohibit scraping
2. **Respect robots.txt**: `https://www.boligsiden.dk/robots.txt`
3. **Rate limiting**: Don't overload their servers
4. **Copyright**: Floor plans may be copyrighted by agents/owners
5. **Personal use**: This tool is for research/personal use

### Best Practices:
- ✅ Add delays between requests (3+ seconds)
- ✅ Use a realistic User-Agent
- ✅ Scrape during off-peak hours
- ✅ Store data locally, don't republish
- ✅ Handle errors gracefully
- ❌ Don't run 24/7 without breaks
- ❌ Don't use multiple IPs to evade blocks
- ❌ Don't republish scraped images

## 🎓 Next Steps

### 1. Test First
```powershell
python test_floor_plan_scraper.py
```

### 2. Small Batch
```powershell
python scrape_floor_plans_advanced.py --limit 10
```

### 3. Review Results
Check `floor_plans/` folder and JSON file

### 4. Adjust Patterns
If success rate is low, add more patterns

### 5. Scale Up
Once working well, increase limit gradually

## 📚 Alternative Approaches

If scraping proves difficult:

### Option 1: API Access
Contact Boligsiden.dk for official API access

### Option 2: Manual Collection
Download floor plans manually for properties of interest

### Option 3: Boligsidens Export
Check if they offer data export services

### Option 4: Third-party Services
Use commercial property data providers

## 🔗 Resources

- **Selenium Docs**: https://selenium-python.readthedocs.io/
- **XPath Tutorial**: https://www.w3schools.com/xml/xpath_intro.asp
- **CSS Selectors**: https://www.w3schools.com/cssref/css_selectors.php
- **ChromeDriver**: https://chromedriver.chromium.org/

## 💡 Tips for Success

1. **Start small**: Test on 10-20 properties first
2. **Monitor success rate**: Aim for >70%
3. **Check logs**: `floor_plan_scraper.log` has details
4. **Use screenshots**: Debug issues visually
5. **Be patient**: 361K properties takes time
6. **Save progress**: JSON files track what's done
7. **Resume capability**: Use `--offset` to skip completed

## 📞 Support

If you encounter issues:
1. Check `floor_plan_scraper.log`
2. Look at page screenshots in output folder
3. Run without `--headless` to see browser
4. Review JSON results for error messages
5. Adjust patterns based on actual HTML structure

---

**Created**: October 2024
**Version**: 1.0
**Author**: GitHub Copilot
