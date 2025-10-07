# 🎒 Portable Danish Housing Market Search

**Self-contained version that works without PostgreSQL**

## 📁 What's in this folder

- `backup_database.py` - Export your PostgreSQL data to Parquet files
- `app_portable.py` - Flask web application that runs on Parquet files  
- `file_database.py` - Pandas-based database layer (replaces PostgreSQL)
- `create_deployment_package.py` - Creates ZIP package for easy transfer
- `requirements_portable.txt` - Minimal dependencies
- `templates/` - HTML templates for the web interface

## 🚀 Quick Start

### 1. Export your data
```bash
cd portable
python backup_database.py --export
```

### 2. Run the portable website
```bash
python app_portable.py
```

### 3. Open in browser
Visit: http://127.0.0.1:5000

## 📦 For Work Laptop

### Create deployment package:
```bash
python create_deployment_package.py
```

This creates a ZIP file you can transfer to any computer.

## 💡 How it works

- **backup_database.py** exports all 14 database tables to compressed Parquet files
- **file_database.py** provides the same interface as PostgreSQL but uses pandas
- **app_portable.py** is identical to the main webapp but uses file storage
- Data loads entirely into memory for fast querying
- No database installation required

## 📊 Performance

- **Export**: ~1 minute for 228K properties  
- **File size**: ~87 MB (compressed from GBs)
- **Load time**: ~5 seconds to load all data into memory
- **Query speed**: Instant (in-memory pandas operations)

## 🎯 Perfect for

- Work laptops without database access
- Demos and presentations  
- Sharing with colleagues
- Offline analysis
- Development on different machines

---

**All 228,594 properties with complete search functionality, zero database required!**