# Danish Housing Market Analysis

**Production-ready system for importing and analyzing Danish property data from the Boligsiden API.**

📊 **Status:** 228,594 properties imported | 3,683 listings tracked | Web interface live

---

## 🚀 Quick Start

### **1. Setup Environment**
```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Configure Database**
Set up PostgreSQL and create `.env` file:
```bash
DATABASE_URL=postgresql://username:password@localhost/housing_db
```

### **3. Start Web Application**
```bash
cd webapp
python app.py
```
Visit: http://127.0.0.1:5000

---

## 📥 Data Import

### **Full Import** (2-3 hours, 228K properties)
```bash
python import_copenhagen_area.py --parallel --workers 20
```

### **Test Import** (10 seconds, 100 properties)
```bash
python import_copenhagen_area.py --limit 100 --parallel
```

### **Clear Database**
```bash
python reset_db.py
```

---

## 📊 Current Database

- **Properties:** 228,594 villas
- **Municipalities:** 36 (within 60km of Copenhagen)
- **Cases:** 3,683 listings with dates
- **Tables:** 13 (normalized schema)
- **Fields:** 120+ per property

---

## 🎯 Features

✅ **Web Interface** - Search, filter, sort properties  
✅ **Parallel Import** - 20-30 properties/second  
✅ **Auto Duplicate Detection** - Skips existing properties  
✅ **Listing Tracking** - Dates, price changes, status  
✅ **Comprehensive Data** - Buildings, taxes, registrations  
✅ **No 10K Limit** - Zip code subdivision for large municipalities  
✅ **Critical Bug Fixes** - zipCodes parameter, pagination issues

---

## 📁 Project Structure

```
housing_project/
├── import_copenhagen_area.py      # Main import script
├── import_api_data.py             # Database functions
├── reset_db.py                    # Clear database
├── requirements.txt               # Dependencies
├── municipalities_within_60km.json
│
├── src/                           # Database models & logic
│   ├── db_models_new.py          # 13-table schema
│   ├── database.py               # Connection management
│   └── ...
│
├── webapp/                        # Flask web interface
│   ├── app.py                    # Backend server
│   └── templates/                # HTML templates
│
├── tests/                         # (cleaned up)
├── archive/                       # Old code/docs
│
└── Documentation:
    ├── README.md                  # This file
    ├── PROJECT_SUMMARY.md         # Project overview
    ├── DATABASE_SCHEMA.md         # Complete schema
    └── PROJECT_KNOWLEDGE.md       # Technical details
```

---

## 📚 Documentation

- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Overview, quick start, status
- **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - 13 tables, 120+ fields  
- **[PROJECT_KNOWLEDGE.md](PROJECT_KNOWLEDGE.md)** - API docs, bug fixes, optimizations

---

## ⚡ Performance

| Mode | Workers | Speed | Time (228K props) |
|------|---------|-------|-------------------|
| Sequential | 1 | 0.5-1/s | 60+ hours |
| Parallel | 20 | 20-30/s | 2-3 hours ⭐ |

**Production Setup:** 20 workers = **2-3 hours** for full import

---

## 🎯 Common Commands

```bash
# Start web interface
cd webapp && python app.py

# Full import (all 36 municipalities)
python import_copenhagen_area.py --parallel --workers 20

# Test import (100 properties in 5 seconds)
python import_copenhagen_area.py --limit 100 --parallel

# Clear database completely
python reset_db.py

# Check property count
python -c "from src.database import db; from src.db_models_new import Property; s=db.get_session(); print(f'Properties: {s.query(Property).count()}'); s.close()"
```

---

## 🗄️ Database Schema

**13 normalized tables:**
- `properties_new` - Main property data
- `buildings` - Building details  
- `registrations` - Sale history
- `cases` - Listing history with dates
- `price_changes` - Price reductions
- `municipalities`, `provinces`, `roads`, `zip_codes`, `cities`, `places`
- `days_on_market` - Market timing

**See DATABASE_SCHEMA.md for complete field documentation**

---

## 📊 Data Source

**Boligsiden API (api.boligsiden.dk)**
- **Coverage:** 36 municipalities within 60km of Copenhagen
- **Filter:** Villa properties only (97% data reduction)
- **Import:** 228,594 properties successfully imported
- **Cases:** 3,683 listings with dates and price changes

---

## � Known Issues

**Price Display (In Progress):**
- Some properties show "N/A" for price in web interface
- Database has cases data but needs webapp update
- Solution: Join cases table and use current_price field

---

## 🎯 Next Steps

1. ✅ Documentation consolidated (3 MD files)
2. ⏳ Fix N/A price display in webapp
3. ⏳ Increase properties per page (20 → 50)
4. ⏳ Add scoring system for property valuation
5. ⏳ Add price range and area filters

---

## 📞 Troubleshooting

**Import Issues:**
- See PROJECT_KNOWLEDGE.md for critical bug fixes
- Must use `zipCodes` (plural), not `zipCode`
- API limited to 10,000 per query (auto-subdivides)

**Database Issues:**
- Use `reset_db.py` to clear and recreate tables
- Check PostgreSQL connection in `.env` file

**Web Interface:**
- Ensure Flask server running: `cd webapp && python app.py`
- Default port: http://127.0.0.1:5000
- Complete API documentation
- Database schema details
- Import system architecture
- Performance optimization guide
- Troubleshooting common issues

---

**Built with:** Python, SQLAlchemy, PostgreSQL, ThreadPoolExecutor  
**Last Updated:** October 5, 2025  
**Status:** ✅ Production Ready
