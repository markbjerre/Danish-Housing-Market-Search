# Project: Danish Housing Market Search

## Project Description
A sophisticated, production-ready system for analyzing the Danish housing market. Imports, stores, and analyzes villa properties from the Boligsiden API across 36 municipalities within 60km of Copenhagen. Features include a PostgreSQL database with 228,594 properties, a Flask web interface for searching and filtering, and a portable file-based system for offline access on any computer.

## Tech Stack
- **Frontend**: Flask with Jinja2 templates, HTML/CSS, Bootstrap
- **Backend**: Python 3.x, Flask web framework
- **Database**: PostgreSQL (primary production) + Parquet files (portable backup)
- **Data Processing**: Pandas, NumPy for data manipulation and analysis
- **API Integration**: Boligsiden API (villa property data)
- **Data Formats**: Parquet (columnar compression), CSV exports
- **Testing**: pytest (recommended for future unit tests)

## Code Conventions
- 4-space indentation (Python PEP 8 standard)
- `snake_case` for variables, functions, and file names
- `UPPER_SNAKE_CASE` for constants
- `CapitalCase` for class names
- Type hints for all function signatures
- Google-style docstrings for all public functions
- Comments explaining complex logic and API quirks
- Error handling with try/except for API calls and database operations

## Project Structure
```
Danish-Housing-Market-Search/
├── portable/                          # Complete no-database system
│   ├── app_portable.py               # File-based Flask application
│   ├── file_database.py              # Pandas database replacement layer
│   ├── requirements_portable.txt     # Minimal dependencies
│   ├── data/                         # Parquet backups (87.6 MB)
│   └── templates/                    # Jinja2 HTML templates
├── scripts/                          # All utility and import scripts
│   ├── import_copenhagen_area.py     # Main data importer (20 parallel workers)
│   ├── import_api_data.py            # Direct API data fetcher
│   ├── backup_database.py            # Full export to Parquet format
│   └── periodic_updates.py           # Daily/weekly refresh logic
├── src/                              # Core source code
│   ├── database.py                   # PostgreSQL connection & session mgmt
│   ├── db_models_new.py              # SQLAlchemy ORM models (14 tables)
│   ├── file_database.py              # Pandas-based query replacement
│   ├── api_handler.py                # Boligsiden API client wrapper
│   └── config.py                     # Configuration & environment loading
├── webapp/                           # Flask web application
│   ├── app.py                        # Main Flask app (PostgreSQL version)
│   ├── app_portable.py               # Portable Flask app (file-based)
│   └── templates/                    # Jinja2 HTML templates
├── docs/                             # Complete project documentation
│   ├── DATABASE_SCHEMA.md            # 14-table schema with field definitions
│   ├── PROJECT_SUMMARY.md            # High-level project overview
│   ├── UPDATE_SCHEDULE.md            # Data refresh strategy and timing
│   └── PROJECT_STRUCTURE.md          # File organization and conventions
├── data/                             # Data files and backups
│   └── backups/                      # Timestamped Parquet exports
├── archive/                          # Old/unused files (70+ historical files)
├── .env                              # Database credentials (DO NOT COMMIT)
├── .gitignore                        # Comprehensive ignore rules (280+ lines)
├── requirements.txt                  # Full dependency list
├── requirements_portable.txt         # Minimal portable dependencies
├── README.md                         # Project overview and quick start
└── claude.md                         # This file - project context for Claude
```

## Important Notes

### Critical API Learnings
- **Field names matter**: Use `priceCash` NOT `price`, `zipCodes` (plural) NOT `zipCode`
- **10K pagination limit**: Large municipalities require zip code-based subdivision strategy
- **Rate limiting**: Stay under 10 requests/second to avoid API bans
- **Nested structures**: Image objects are `{width: 600, height: 400}` not plain strings
- **Store URLs not files**: Boligsiden CDN is reliable; saves 180GB+ of storage vs local files

### Database Architecture
- **14 normalized tables** for flexibility and complex querying
- **228,594 total properties** (villas only)
- **3,623 active listings** with complete price and image data
- **35,402 image URLs** stored as CDN references
- **388,113 historical transactions** in registrations table
- **Parquet backups**: ~87.6 MB compressed vs several GB uncompressed PostgreSQL

### Performance Characteristics
- **Import speed**: 20-30 properties/second with 20 parallel workers
- **Full import time**: 2-3 hours for all municipalities
- **Daily refresh**: 30-45 minutes for active listings only
- **Weekly refresh**: 2-3 hours for complete database rescan
- **Portable app**: Data loads in memory in seconds, queries are instant

### Data Update Strategy
- **Daily**: Refresh active listings only (30-45 minutes)
- **Weekly**: Full database refresh scanning all municipalities (2-3 hours)
- **Monthly**: Database cleanup, optimization, and statistics update
- **Backup**: Weekly automatic Parquet exports for disaster recovery and portability

## Instructions for Claude

When working on this project, please:

- **Challenge assumptions**: Question if the user's approach might have issues or if there's better logic available
- **Ask for clarity**: Request elaboration when instructions are vague or where context could provide significant additional value
- **Strive for simplicity**: Prefer simple solutions over complex ones; prevent unnecessary file proliferation
- **Archive aggressively**: Move unused files to `archive/`, delete empty folders, consolidate test scripts
- **Minimize documentation**: Keep docs in `README.md`, `TODO.md`, and `claude.md` only; use folder-specific `claude.md` only for complex directories
- **Type everything**: Always include Python type hints for all function parameters and return values
- **Optimize performance**: Prioritize performance improvements, especially for operations on 200K+ property datasets
- **Follow existing patterns**: Use established error handling, database query patterns, and API integration approaches
- **Document public functions**: Include comprehensive docstrings for all public functions and classes
- **Pandas over raw Python**: Use vectorized operations for data manipulation when possible (avoid loops)
- **SQL efficiency**: Optimize database queries; avoid N+1 problems; use proper joins and indexing
- **Production mindset**: Treat this as production code; consider edge cases, error handling, and data integrity

## Known Issues
- None currently - system is production-ready and stable

## Future Plans
- ✅ Database backup system complete
- ✅ Portable file-based system complete  
- ✅ Project folder reorganization complete
- 🔄 **Next Priority**: Implement automated daily/weekly refresh via Windows Task Scheduler
- 🔄 Advanced filtering and search UI improvements
- 🔄 Property detail pages with full image galleries
- 🔄 Market analytics dashboard for price trends
- 🔄 Price prediction models using historical data
- 🔄 Email alerts for new listings matching saved searches

## Environment Setup

### Local Development (with PostgreSQL)
```bash
# Navigate to project directory
cd "Danish Housing Market Search"

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate          # Windows
source venv/bin/activate          # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file with database credentials
# DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/housing_db

# Ensure PostgreSQL is running on localhost:5432

# Start the web application
python webapp/app.py
# Local: http://127.0.0.1:5000
# Production: https://ai-vaerksted.cloud/housing
```

### Portable System (No Database Required)
```bash
# Navigate to portable directory
cd portable

# Install minimal dependencies
pip install -r requirements_portable.txt

# Run the portable app
python app_portable.py
# Local: http://127.0.0.1:5000
# Production: https://ai-vaerksted.cloud/housing
```

### Environment Variables (.env)
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/housing_db
FLASK_ENV=development
FLASK_DEBUG=True
API_BASE_URL=https://www.boligsiden.dk
API_RATE_LIMIT=10  # requests per second
MAX_WORKERS=20     # parallel import workers
```

## Architecture

### Data Pipeline
```
Boligsiden API (228K+ properties)
         ↓
Import Scripts (20 parallel workers)
         ↓
PostgreSQL Database (14 tables, 2.6M rows)
    ↙                                    ↘
Daily Refresh         Weekly Refresh     ↓ Weekly Backup
(Active listings)     (Full rescan)   Parquet Export (87.6 MB)
    ↓                     ↓                  ↓
   ~45 min            ~2-3 hours      Portable System
                                      (No DB needed)
         ↓                              ↙
    PostgreSQL ←————→ Flask Web App ←——┘
                   
         ↓
    User Browser
    • Local Dev: http://127.0.0.1:5000
    • Production: https://ai-vaerksted.cloud/housing
```
```

### Database Schema (14 Tables)
- **Core Property Data**: properties_new, buildings, registrations
- **Listing & Market**: cases, case_images, price_changes, days_on_market
- **Geographic**: municipalities, provinces, cities, zip_codes, roads, places

### Web Application Components
- **Search Interface**: Filter by municipality, price, size, rooms, year, status
- **Results Page**: Sortable list with pagination (50 per page)
- **Property Details**: Full property information with images
- **Data Info**: Database statistics and export information

## Related Documentation
- **Database Schema Details**: See `docs/DATABASE_SCHEMA.md` for complete 14-table structure and field definitions
- **Project Summary**: See `docs/PROJECT_SUMMARY.md` for high-level technical overview  
- **Update Strategy**: See `docs/UPDATE_SCHEDULE.md` for refresh timing and data freshness details
- **File Organization**: See `docs/PROJECT_STRUCTURE.md` for folder structure explanation
