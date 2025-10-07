# File Overview

**Last Updated:** October 6, 2025  
**Purpose:** Quick reference guide to all active project files

---

## 📁 Root Directory

### Core Scripts
- **`import_api_data.py`** - Import single properties or JSON files, create database tables
- **`import_copenhagen_area.py`** - Main bulk import script for all 36 municipalities with parallel processing

### Configuration
- **`.env`** - Database credentials and environment variables
- **`requirements.txt`** - Python dependencies

### Data Files
- **`municipalities_within_60km.json`** - List of 36 municipalities within 60km of Copenhagen

---

## 📚 Documentation

### Current Documentation
- **`README.md`** - Project overview and getting started guide
- **`PROJECT_KNOWLEDGE.md`** - Comprehensive knowledge base (API, database, import system, optimizations)
- **`DATABASE_SCHEMA.md`** - Complete database schema with all 13 tables
- **`IMPORT_FILTERS_AND_FIX.md`** - 10,000 limit fix and zip code subdivision solution
- **`HIDDEN_PROPERTIES_SOLUTION.md`** - How to find properties not in search results via HTML extraction
- **`MISSING_FIELDS_ANALYSIS.md`** - Cases array structure and missing field documentation
- **`SCORING_MODEL_TODO.md`** - Future scoring system requirements
- **`FILE_OVERVIEW.md`** - This file

---

## 💾 Source Code (`src/`)

### Database Models
- **`db_models_new.py`** - Current schema with 13 tables (properties, buildings, cases, price_changes, etc.)
- **`db_models.py`** - Old schema (deprecated, kept for reference)
- **`database.py`** - Database connection and session management

### Core Modules
- **`init_db.py`** - Database initialization
- **`data_loader.py`** - Data loading utilities
- **`data_processing.py`** - Data processing and transformation
- **`property_data.py`** - Property data models
- **`scoring.py`** - Scoring algorithm (in development)
- **`models.py`** - Additional data models
- **`main.py`** - Main application entry point

---

## 🧪 Tests (`tests/`)

### Property Search Tests
- **`find_bomhusstraede.py`** - Multiple strategies to find Bomhusstræde 5
- **`find_villa_bomhus.py`** - Villa-specific search with size filtering
- **`find_bomhus_all_types.py`** - All property types search
- **`find_by_size_and_code.py`** - Search by size and gstkvhx code
- **`find_by_gstkvhx.py`** - Direct gstkvhx code search
- **`list_albertslund_roads.py`** - Enumerate all roads in Albertslund
- **`search_degnebakken.py`** - Search for Degnebakken 24

### API Investigation Tests
- **`test_slug_api.py`** - Test if slug can be used as API filter (result: no)
- **`test_status_filter.py`** - Test market status filtering capabilities (result: sold=false works)
- **`test_offering_endpoint.py`** - Test offering API endpoints (result: all 404)
- **`test_html_uuids.py`** - **SUCCESS!** Extract UUIDs from HTML and test against API
- **`debug_api_response.py`** - Analyze API response structure

### Data Analysis Tests
- **`analyze_full_property_json.py`** - Identify missing fields in schema
- **`analyze_page_source.py`** - Extract UUIDs from HTML page source
- **`check_property_sale_date.py`** - Fetch and display listing date from cases[]
- **`explain_slug_vs_id.py`** - Documentation of slug vs UUID difference
- **`find_hidden_properties_solution.py`** - Solution documentation script
- **`verify_searchable.py`** - Verify if property is in search results
- **`fetch_property.py`** - Simple property data fetcher

### Municipality Analysis Tests
- **`analyze_filters.py`** - Test API filter combinations
- **`analyze_municipalities_efficient.py`** - Efficient municipality analysis
- **`analyze_municipality_distances.py`** - Calculate distances from Copenhagen
- **`analyze_on_market_rate.py`** - Calculate on-market percentage
- **`check_api_market_status.py`** - Check if API returns market status
- **`check_floor_plan_availability.py`** - Check floor plan image availability
- **`check_json.py`** - JSON validation utility
- **`check_property_sale_date.py`** - Check sale/listing dates
- **`check_urls.py`** - URL validation utility

---

## 🌐 Web Application (`webapp/`)

### Backend
- **`app.py`** - Flask server with property search API, sort-by functionality

### Templates
- **`templates/home.html`** - Modern animated landing page (Lovable.dev inspired)
- **`templates/index.html`** - Property search interface with filters and sorting

### Static Assets
- **`static/`** - CSS, JavaScript, images

---

## 📊 Data (`data/`)

### Processed Data
- **`properties.csv`** - Exported property data
- **`sql/`** - SQL queries and exports

---

## 📓 Notebooks (`notebooks/`)

- **`database_analysis.ipynb`** - Database analysis and queries
- **`scoring_analysis.ipynb`** - Scoring model development

---

## 🗄️ Archive (`archive/`)

### Old Documentation
- **`API_ANALYSIS.md`** - Initial API exploration
- **`CLEANUP_SUMMARY.md`** - Previous cleanup notes
- **`DATABASE_EXPANSION_SUMMARY.md`** - Schema expansion notes
- **`FLOOR_PLAN_SCRAPER_GUIDE.md`** - Floor plan scraper documentation
- **`IMPORT_OPTIMIZATION_GUIDE.md`** - Import optimization strategies
- **`PARALLEL_IMPORT_OPTIMIZATIONS.md`** - Parallel processing notes
- **`TOOL_COMPARISON.md`** - Tool comparison analysis
- **`IMPORT_FILTER_ANALYSIS.md`** - Filter analysis (superseded by IMPORT_FILTERS_AND_FIX.md)

### Old Scripts
- **`scrape_floor_plans.py`** - Basic floor plan scraper
- **`scrape_floor_plans_advanced.py`** - Advanced floor plan scraper
- **`import_from_api_search.py`** - Old import script
- **`bulk_import_filtered.py`** - Old bulk import
- **`import_with_cascading_filters.py`** - Old cascading filter import
- **`copenhagen_municipalities.py`** - Municipality discovery script

### Old Data
- **`api_sample_data_20251004_211357.json`** - Sample API response
- **`offering_response.json`** - Offering endpoint response
- **`hidden_props_output.txt`** - Hidden properties investigation output
- **`property_analysis_output.txt`** - Property analysis output

---

## 🛠️ Utilities (`utils/`)

Various utility scripts and helper functions for data processing and analysis.

---

## 🚫 Ignored/System Files

- **`venv/`** - Python virtual environment
- **`__pycache__/`** - Python bytecode cache
- **`.gitignore`** - Git ignore rules
- **`housing_scraper/`** - Old scraper (not actively used)
- **`webpage/`** - Old webpage files (superseded by webapp/)

---

## 📝 Key File Relationships

```
import_copenhagen_area.py
    ↓ imports
import_api_data.py (import functions)
    ↓ uses
src/db_models_new.py (13 tables)
    ↓ connects to
PostgreSQL (housing_db)
    ↓ queried by
webapp/app.py (Flask API)
    ↓ serves
webapp/templates/*.html (UI)
```

---

## 🎯 Most Important Files

1. **`import_copenhagen_area.py`** - Main import script
2. **`src/db_models_new.py`** - Database schema
3. **`import_api_data.py`** - Import functions
4. **`webapp/app.py`** - Web application
5. **`PROJECT_KNOWLEDGE.md`** - Complete documentation
6. **`DATABASE_SCHEMA.md`** - Schema reference

---

**Created:** October 6, 2025  
**Purpose:** Quick navigation and file understanding
