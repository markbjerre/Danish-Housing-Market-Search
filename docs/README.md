# Danish Housing Market Analysis# Danish Housing Market Analysis



**Comprehensive system for importing and analyzing Danish property data.****Production-ready system for importing and analyzing Danish property data from the Boligsiden API.**



📊 **228,594 properties** | 🏠 **3,623 active listings** | 📸 **35,402 images** | 💰 **100% price coverage**📊 **Status:** 228,594 properties imported | 3,683 listings tracked | Web interface live



------



## 🚀 Quick Start## 🚀 Quick Start



### 1. Setup### **1. Setup Environment**

```bash```bash

# Create virtual environment# Create virtual environment

python -m venv .venvpython -m venv venv

.venv\Scripts\activate.\venv\Scripts\activate



# Install dependencies# Install dependencies

pip install -r requirements.txtpip install -r requirements.txt

```

# Configure database (.env file)

DB_HOST=localhost### **2. Configure Database**

DB_PORT=5432Set up PostgreSQL and create `.env` file:

DB_NAME=housing_db```bash

DB_USER=postgresDATABASE_URL=postgresql://username:password@localhost/housing_db

DB_PASSWORD=your_password```

```

### **3. Start Web Application**

### 2. Start Web Interface```bash

```bashcd webapp

cd webapppython app.py

python app.py```

```Visit: http://127.0.0.1:5000

Visit: **http://127.0.0.1:5000**

---

---

## 📥 Data Import

## 📥 Import Data

### **Full Import** (2-3 hours, 228K properties)

### Full Import (2-3 hours)```bash

```bashpython import_copenhagen_area.py --parallel --workers 20

python import_copenhagen_area.py --parallel --workers 20```

```

### **Test Import** (10 seconds, 100 properties)

### Test Import (10 seconds)```bash

```bashpython import_copenhagen_area.py --limit 100 --parallel

python import_copenhagen_area.py --limit 100 --parallel```

```

### **Clear Database**

### Update Active Listings```bash

```bashpython reset_db.py

python periodic_updates.py --refresh-active```

```

---

---

## 📊 Current Database

## 📊 What's In The Database?

- **Properties:** 228,594 villas

- **228,594 villas** across 36 municipalities- **Municipalities:** 36 (within 60km of Copenhagen)

- **3,623 active listings** with current prices- **Cases:** 3,683 listings with dates

- **35,402 property images** (stored as URLs)- **Tables:** 13 (normalized schema)

- **388,113 historical transactions**- **Fields:** 120+ per property

- **100% price coverage** for active listings

- **96% description coverage**---



**Coverage area:** 36 municipalities within 60km of Copenhagen## 🎯 Features



---✅ **Web Interface** - Search, filter, sort properties  

✅ **Parallel Import** - 20-30 properties/second  

## 🎯 Key Features✅ **Auto Duplicate Detection** - Skips existing properties  

✅ **Listing Tracking** - Dates, price changes, status  

✅ **Parallel Import** - 20-30 properties/second  ✅ **Comprehensive Data** - Buildings, taxes, registrations  

✅ **Web Interface** - Search, filter, sort properties  ✅ **No 10K Limit** - Zip code subdivision for large municipalities  

✅ **Price Tracking** - Current prices, changes, history  ✅ **Critical Bug Fixes** - zipCodes parameter, pagination issues

✅ **Image Management** - 10 images per listing  

✅ **Auto Updates** - Daily/weekly refresh system  ---

✅ **Smart Filtering** - Municipality, price, size, more  

## 📁 Project Structure

---

```

## 📁 Project Structurehousing_project/

├── import_copenhagen_area.py      # Main import script

```├── import_api_data.py             # Database functions

housing_project/├── reset_db.py                    # Clear database

├── import_copenhagen_area.py    # Main import (parallel, 20 workers)├── requirements.txt               # Dependencies

├── import_api_data.py           # Core import functions├── municipalities_within_60km.json

├── periodic_updates.py          # Daily/weekly updates│

├── reset_db.py                  # Clear database├── src/                           # Database models & logic

├── backup_database.py           # Export to Parquet│   ├── db_models_new.py          # 13-table schema

├── requirements.txt│   ├── database.py               # Connection management

├── .env                         # Database credentials (create this)│   └── ...

││

├── src/                         # Database models├── webapp/                        # Flask web interface

│   ├── db_models_new.py        # 14 table definitions│   ├── app.py                    # Backend server

│   └── database.py             # Connection management│   └── templates/                # HTML templates

││

├── webapp/                      # Flask web interface├── tests/                         # (cleaned up)

│   ├── app.py                  # Main server├── archive/                       # Old code/docs

│   └── templates/              # HTML pages│

│└── Documentation:

├── scripts/                     # Utility scripts    ├── README.md                  # This file

├── docs/                        # Additional documentation    ├── PROJECT_SUMMARY.md         # Project overview

└── archive/                     # Old files    ├── DATABASE_SCHEMA.md         # Complete schema

```    └── PROJECT_KNOWLEDGE.md       # Technical details

```

---

---

## 💻 Common Commands

## 📚 Documentation

```bash

# Start web interface- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Overview, quick start, status

cd webapp && python app.py- **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - 13 tables, 120+ fields  

- **[PROJECT_KNOWLEDGE.md](PROJECT_KNOWLEDGE.md)** - API docs, bug fixes, optimizations

# Full import (all 36 municipalities)

python import_copenhagen_area.py --parallel --workers 20---



# Daily update (refresh active listings + discover new)## ⚡ Performance

python periodic_updates.py --daily

| Mode | Workers | Speed | Time (228K props) |

# Weekly update (full refresh)|------|---------|-------|-------------------|

python periodic_updates.py --refresh-all| Sequential | 1 | 0.5-1/s | 60+ hours |

| Parallel | 20 | 20-30/s | 2-3 hours ⭐ |

# Clear database

python reset_db.py**Production Setup:** 20 workers = **2-3 hours** for full import



# Backup to Parquet---

python backup_database.py --export

## 🎯 Common Commands

# Check status

python verify_import.py```bash

```# Start web interface

cd webapp && python app.py

---

# Full import (all 36 municipalities)

## 📚 Documentationpython import_copenhagen_area.py --parallel --workers 20



- **[README.md](README.md)** - This file (quick start)# Test import (100 properties in 5 seconds)

- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Complete overview (for LLMs)python import_copenhagen_area.py --limit 100 --parallel

- **[PROJECT_LEARNINGS.md](PROJECT_LEARNINGS.md)** - Technical insights

- **[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)** - All 14 tables explained# Clear database completely

- **[UPDATE_SCHEDULE.md](UPDATE_SCHEDULE.md)** - Update procedurespython reset_db.py



---# Check property count

python -c "from src.database import db; from src.db_models_new import Property; s=db.get_session(); print(f'Properties: {s.query(Property).count()}'); s.close()"

## ⚡ Performance```



| Operation | Duration | Speed |---

|-----------|----------|-------|

| Full import (228K) | 2-3 hours | 20-30/sec |## 🗄️ Database Schema

| Daily update (3.6K) | 30-45 min | 10/sec |

| Single property | 0.5-1 sec | 1-2/sec |**13 normalized tables:**

- `properties_new` - Main property data

---- `buildings` - Building details  

- `registrations` - Sale history

## 🎓 Key Learnings- `cases` - Listing history with dates

- `price_changes` - Price reductions

- **API uses `priceCash` not `price`** - Critical bug fix- `municipalities`, `provinces`, `roads`, `zip_codes`, `cities`, `places`

- **Use `zipCodes` (plural)** - Singular doesn't work- `days_on_market` - Market timing

- **10K pagination limit** - Auto-subdivide by zip code

- **Store URLs not files** - 5MB vs 180GB for images**See DATABASE_SCHEMA.md for complete field documentation**

- **20 workers optimal** - Balance speed vs resources

---

See **PROJECT_LEARNINGS.md** for complete insights.

## 📊 Data Source

---

**Boligsiden API (api.boligsiden.dk)**

## 🔄 Update Strategy- **Coverage:** 36 municipalities within 60km of Copenhagen

- **Filter:** Villa properties only (97% data reduction)

**Daily:** Refresh active listings + discover new properties (60-75 min)  - **Import:** 228,594 properties successfully imported

**Weekly:** Full database refresh (2-3 hours)  - **Cases:** 3,683 listings with dates and price changes

**Monthly:** Database cleanup and optimization (15 min)

---

See **UPDATE_SCHEDULE.md** for automation setup.

## � Known Issues

---

**Price Display (In Progress):**

## 🗄️ Database Schema- Some properties show "N/A" for price in web interface

- Database has cases data but needs webapp update

**14 tables organized into 4 groups:**- Solution: Join cases table and use current_price field



1. **Core Property Data** - properties_new, buildings, registrations---

2. **Listing & Market** - cases, price_changes, images, days_on_market

3. **Geographic** - municipalities, provinces, cities, zip_codes, roads, places## 🎯 Next Steps

4. **Tracking** - Import timestamps, status

1. ✅ Documentation consolidated (3 MD files)

See **DATABASE_SCHEMA.md** for complete field listings.2. ⏳ Fix N/A price display in webapp

3. ⏳ Increase properties per page (20 → 50)

---4. ⏳ Add scoring system for property valuation

5. ⏳ Add price range and area filters

## 🛠️ Tech Stack

---

- **Python 3.13** - Core language

- **PostgreSQL** - Database (14 tables, 120+ fields)## 📞 Troubleshooting

- **SQLAlchemy** - ORM

- **Flask** - Web framework**Import Issues:**

- **Parquet** - Backup format- See PROJECT_KNOWLEDGE.md for critical bug fixes

- **Boligsiden API** - Data source- Must use `zipCodes` (plural), not `zipCode`

- API limited to 10,000 per query (auto-subdivides)

---

**Database Issues:**

## 📝 Environment Setup- Use `reset_db.py` to clear and recreate tables

- Check PostgreSQL connection in `.env` file

Create `.env` file in project root:

**Web Interface:**

```bash- Ensure Flask server running: `cd webapp && python app.py`

DB_HOST=localhost- Default port: http://127.0.0.1:5000

DB_PORT=5432- Complete API documentation

DB_NAME=housing_db- Database schema details

DB_USER=postgres- Import system architecture

DB_PASSWORD=your_secure_password_here- Performance optimization guide

```- Troubleshooting common issues



Never commit `.env` to git! (It's in `.gitignore`)---



---**Built with:** Python, SQLAlchemy, PostgreSQL, ThreadPoolExecutor  

**Last Updated:** October 5, 2025  

## 🚦 Current Status**Status:** ✅ Production Ready


**Last Major Update:** October 7, 2025

✅ **Production Ready**
- All 228,594 properties imported
- Price bug fixed (100% coverage)
- Images working (35,402 stored)
- Web interface live
- Update system documented

**TODO List:**

✅ **COMPLETED:**
1. ✅ Update .gitignore (280+ lines protecting sensitive data)
2. ✅ Consolidate documentation (70+ files → 4 core docs)

🔄 **IN PROGRESS:**
3. ⏳ Reorganize file structure
   - Create `scripts/`, `docs/`, `logs/`, `data/` folders
   - Move import/update scripts to appropriate locations
   - Update import paths in all Python files

📋 **PLANNED:**
4. ⏳ Create database backup system
   - Build `backup_database.py` with `--export` and `--import`
   - Export all 14 tables to Parquet format
   - Test backup/restore cycle
   
5. ⏳ Create `periodic_updates.py` script
   - `--daily`: Refresh active + discover new (60-75 min) -- daily
   - `--refresh-active`: Update 3.6K active listings -- daily
   - `--discover-new`: Scan for new properties -- weekly 
   - `--refresh-all`: Full database refresh -- monthly
   - `--cleanup`: Database optimization -- monthly
   
6. ⏳ Add data browser to webpage
   - `/browse` route with sortable/filterable table
   - Show: price, area, location, days_on_market, images
   - Pagination (50 per page), result counts
   
7. ⏳ Enhance webpage with property details
   - `/property/<id>` route for full property view
   - Image gallery (35K images available)
   - Price history chart, realtor info, map

---

## 🤝 For LLM Agents

**Getting Started with This Project:**

If you're an LLM helping with this project, read these files in order:

1. **PROJECT_SUMMARY.md** (REQUIRED - read first)
   - Complete project overview
   - Architecture (14 tables, 120+ fields)
   - Key scripts and dependencies
   - Critical bugs fixed (4 major issues)
   - Performance metrics

2. **PROJECT_LEARNINGS.md** (REQUIRED - read second)
   - API discoveries (`priceCash` not `price`, etc.)
   - Architecture decisions (why we store URLs not files)
   - Performance optimizations (parallel, batching)
   - Bug fixes with root causes
   - Best practices

3. **DATABASE_SCHEMA.md** (reference as needed)
   - 14-table structure with all fields
   - Query examples
   - Relationships between tables

4. **README.md** (human-friendly, optional)
   - Quick start commands
   - Common operations

**Current Focus:** Next TODO is #3 (reorganize file structure)

---

## 📞 Need Help?

**Documentation:**
- Quick questions → This README
- Complete overview → PROJECT_SUMMARY.md
- Technical details → PROJECT_LEARNINGS.md
- Database structure → DATABASE_SCHEMA.md

**Common Issues:**
- Import fails → Check .env file and database connection
- Slow imports → Use `--parallel --workers 20`
- Missing prices → Run `verify_import.py` to check
- Web app won't start → Check port 5000 isn't in use

---

**Built with ❤️ for analyzing the Danish housing market**
