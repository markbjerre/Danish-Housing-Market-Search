# Danish Housing Market Search - Portable Version

**Complete Danish housing data analysis without requiring PostgreSQL!**

## 📊 What's Included

- **228,594 properties** across 36 municipalities near Copenhagen
- **3,623 active listings** with current prices and images
- **35,402 property images** (URLs to professional CDN)
- **388,113 historical transactions** for price analysis
- **Complete search and filtering** - identical to the full version

## 🚀 Quick Setup (Work Laptop)

### Step 1: Install Python Dependencies
```bash
pip install -r requirements_portable.txt
```

### Step 2: Start the Website
```bash
cd webapp
python app_portable.py
```

### Step 3: Open in Browser

**Development (Local):**  
Visit: **http://127.0.0.1:5000**

**Production (Deployed):**  
Visit: **https://ai-vaerksted.cloud/housing**

## 📁 Files Structure

```
Danish-Housing-Market-Search-Portable/
├── webapp/
│   ├── app_portable.py          # Main web application
│   └── templates/               # HTML pages
├── src/
│   └── file_database.py         # File-based database layer
├── data/
│   └── backups/
│       └── full_export_*/       # Your exported data (87.6 MB)
├── requirements_portable.txt    # Minimal dependencies
└── README_PORTABLE.md          # This file
```

## 🎯 Features Available

### Search & Filter
- ✅ **Municipality filter** - All 36 areas available
- ✅ **Price range** - Min/max price filtering
- ✅ **Size filter** - Living area in square meters
- ✅ **Rooms filter** - Number of rooms
- ✅ **Year built** - Construction year range
- ✅ **Market status** - On market vs. sold properties

### Sorting Options
- ✅ **Price** - Highest to lowest, lowest to highest
- ✅ **Size** - Largest properties first
- ✅ **Year built** - Newest properties first
- ✅ **Price per m²** - Best value properties

### Data Views
- ✅ **Property listings** - 50 properties per page
- ✅ **Detailed information** - Address, size, price, year built
- ✅ **Municipality averages** - Price per m² by area
- ✅ **Database statistics** - Complete data overview

## 💡 How It Works

### No Database Required
Instead of PostgreSQL, this version uses:
- **Parquet files** - Compressed, efficient data storage
- **Pandas** - Fast in-memory data processing
- **Flask** - Simple web framework

### Performance
- **Memory-based** - All data loaded for instant searches
- **Fast filtering** - Pandas vectorized operations
- **Local files** - No network dependencies

### Data Integrity
- **Complete export** - Every property and detail preserved
- **Type safety** - All data types maintained (dates, numbers, text)
- **Relationships** - Property-building-case relationships intact

## 🔍 Usage Examples

### Find Expensive Villas in Gentofte
1. Go to `/search`
2. Select "Gentofte" from municipality dropdown
3. Set price minimum to 15,000,000 DKK
4. Sort by "Price (highest first)"

### Find Good Value Properties
1. Set max price to 8,000,000 DKK
2. Set min area to 150 m²
3. Sort by "Price per m² (lowest first)"

### Browse New Construction
1. Set year built minimum to 2015
2. Sort by "Year built (newest first)"

## 📊 Database Information

**Export Details:**
- **Export date:** October 7, 2025
- **Total rows:** 2,599,160 across 13 tables
- **File size:** 87.6 MB (compressed from GBs)
- **Export time:** 60 seconds

**Table Breakdown:**
- **properties_new:** 228,594 rows (44.5 MB) - Main property data
- **registrations:** 388,113 rows (10.4 MB) - Sale history
- **main_buildings:** 228,177 rows (4.3 MB) - Building details
- **case_images:** 35,402 rows (3.0 MB) - Property images
- **cases:** 3,623 rows (2.5 MB) - Active listings
- **9 other tables** - Geographic and reference data

## 🛠️ Troubleshooting

### Website Won't Start
```bash
# Check if Python is installed
python --version

# Install dependencies
pip install flask pandas pyarrow

# Try running directly
cd webapp
python app_portable.py
```

### No Data Showing
- Ensure `data/backups/full_export_*/` folder exists
- Check that Parquet files are present
- Look for error messages in terminal

### Slow Performance
- First search might be slower (loading data)
- Subsequent searches should be instant
- Consider reducing data if memory is limited

### Port Already in Use
If port 5000 is busy, edit `app_portable.py`:
```python
app.run(debug=True, host='127.0.0.1', port=5001)  # Change to 5001
```

## 📞 Support

This is a complete, standalone version of the Danish Housing Market Search system. It contains the same data and features as the full PostgreSQL version but requires only Python and a few packages.

**Key Benefits:**
- ✅ **No database installation** required
- ✅ **Portable** - copy to any computer
- ✅ **Fast** - all data in memory
- ✅ **Complete** - every property and detail included
- ✅ **Up-to-date** - exported from latest database

---

**Built with ❤️ for portable housing market analysis**