# Project: Danish Housing Market Search

## Type
Data platform

## Entry points
| Action | Command |
|--------|---------|
| **Main entry** | `webapp/app.py` (Flask, PostgreSQL) |
| **Run locally** | `./scripts/start_local_dev.sh` (Linux/Mac) or `scripts\start_local_dev.bat` (Windows), or `python webapp/app.py` with .env |
| **Run tests** | `./scripts/test.sh` or `npm test` (Playwright) |

## Project Description
Production system for analyzing the Danish housing market. Imports, stores, and analyzes villa properties from the Boligsiden API across 36 municipalities within 60km of Copenhagen. PostgreSQL database with 228K+ properties, Flask web interface, and portable file-based system for offline access.

## Tech Stack
- **Frontend**: Flask + Jinja2 templates, Bootstrap
- **Backend**: Python 3.x, Flask
- **Database**: PostgreSQL (primary) + Parquet files (portable backup)
- **Data Processing**: Pandas, NumPy
- **API**: Boligsiden API (villa property data)

## Code Conventions
- PEP 8, type hints on all function signatures, Google-style docstrings on public functions
- `snake_case` variables/files, `UPPER_SNAKE_CASE` constants, `CapitalCase` classes
- Vectorized Pandas over Python loops; SQL joins over N+1 queries
- Archive unused files to `archive/`; keep docs to README.md, TODO.md, claude.md only

## Project Structure
```
Danish-Housing-Market-Search/
├── portable/               # File-based system (no DB required)
├── scripts/                # Import and utility scripts (incl. test.sh, start_local_dev)
│   ├── import_copenhagen_area.py   # Main importer (20 parallel workers)
│   ├── import_api_data.py          # API data fetcher
│   ├── refresh_listings.py         # Daily/weekly refresh
│   └── backup_database.py          # Export to Parquet
├── src/                    # Core source
│   ├── db_models_new.py    # SQLAlchemy ORM (14 tables)
│   ├── scoring/factors.py  # Property scoring logic
│   └── api_handler.py      # Boligsiden API client
├── webapp/                 # Flask web application
│   └── app.py             # Main Flask app (PostgreSQL)
├── docs/                   # Project documentation (INDEX.md)
├── tests/                  # Diagnostic and discovery scripts
├── utils/                  # Shared utilities
└── .env                    # DB credentials (DO NOT COMMIT)
```

## Critical API Learnings
- Use `priceCash` not `price`; `zipCodes` (plural) not `zipCode`
- 10K pagination limit, so large municipalities need zip code subdivision
- Rate limit: stay under 10 req/s
- `cases[]` only appear when `isOnMarket=true`
- Search endpoint (`/search/addresses`) returns full payload incl. `cases`, so **no separate detail call needed for active listings**
- `isOnMarket=true` search param is **ignored by API**, it always returns all villas

## Database State (Feb 2026)
- 228K+ total properties (villas only), 1,932 active listings
- 14 normalized tables, 388K+ historical transactions
- Parquet backups: ~87.6 MB compressed

### Database Architecture
- **PostgreSQL** runs on homelab (Docker on Seagate 8TB), port **5434**, user `housing`, db `housing_db`
- **VPS webapp** connects to homelab DB via Tailscale (`100.83.229.69:5434`)
- **Homelab Tailscale IP**: `100.83.229.69` (hostname: `dobbybrain`)
- **VPS Tailscale IP**: `100.77.253.18` (hostname: `srv1070976`)
- DB is NOT on the VPS, which saves VPS disk space, single source of truth on homelab

## Instructions for Claude

### Testing & Commits
- Test locally before pushing (scripts/start_local_dev.sh or scripts\start_local_dev.bat); build complete features then commit (no micro-commits)
- Pragmatic testing: catch obvious issues, don't over-engineer test coverage

### Code Quality
- Challenge assumptions; ask for clarity on vague instructions
- Simple over complex; archive aggressively; minimize file proliferation
- Production mindset: edge cases, error handling, data integrity

## Missing Data (Fields Available in API but Not Stored)

### Added Feb 2026:
- ✅ `cases[].realEstate`: `downPayment`, `grossMortgage`, `netMortgage` → `down_payment`, `gross_mortgage`, `net_mortgage`
- ✅ `cases[].daysListed.days` → `days_listed`
- ❌ `cases[].realtor`, excluded (not needed)

### Medium value (not yet added):
- `cases[].numberOfRooms/Bathrooms/Floors/Toilets` (more reliable than building-level data)
- `casePrice` at top-level property (avoids join for current asking price)
- `property.hasMultipleCases` (boolean)

## Refresh Script (`scripts/refresh_listings.py`)

Two-phase refresh:
- **Phase 1** (`--skip-discovery`): Detail API for all `is_on_market=True` → updates data, marks sold. Fast (~2 min).
- **Phase 2** (default): Also pages search API per municipality to find NEW listings. Slow (~1-2 hrs).

```bash
python3 scripts/refresh_listings.py --skip-discovery    # Daily (fast)
python3 scripts/refresh_listings.py                     # Weekly (full)
python3 scripts/refresh_listings.py --municipality Holbæk
python3 scripts/refresh_listings.py --dry-run --municipality Gentofte
```

**Key lessons:**
- `ALL_MUNICIPALITIES` list must stay in sync with DB, or missing ones accumulate stale listings silently
- Average days-on-market is 160 to 320 days, so most Oct 2025 listings are genuinely still active
- Properties can be sold+relisted with new `case_id`, and refresh correctly adds new case alongside old

## Future Plans
- 🔄 Automated daily/weekly refresh scheduler (cron jobs)
- 🔄 Advanced filtering and search UI improvements
- 🔄 Property detail pages with full image galleries
- 🔄 Market analytics dashboard for price trends
- 🔄 Price prediction models using historical data
- 🔄 Email alerts for new listings matching saved searches

## Environment Setup

### Local development (homelab)
```bash
# Start PostgreSQL (Docker, Seagate 8TB)
cd ~/homelab/apps/housing-db && docker compose up -d
# DB at localhost:5434

# Run web app
cd ~/projects/Danish-Housing-Market-Search
python webapp/app.py
# http://127.0.0.1:5000
```

**.env (local):**
```
DB_HOST=localhost
DB_PORT=5434
DB_NAME=housing_db
DB_USER=housing
DATABASE_URL=postgresql://housing:changeme@localhost:5434/housing_db
```

### Production (VPS → homelab DB via Tailscale)
```bash
# SSH into VPS
ssh root@srv1070976

# Housing webapp: Docker container, auto-restarting
# Connects to homelab DB over Tailscale (100.83.229.69:5434)
# Traefik routes: https://ai-vaerksted.cloud/housing
```

**VPS .env (at `/root/.env`):**
```
DB_HOST=100.83.229.69
DB_PORT=5434
DB_NAME=housing_db
DB_USER=housing
```

**VPS docker-compose** at `/root/docker-compose.yml`. The housing service is `ai-vaerksted-housing`.

## Database Schema (14 Tables)
- **Core**: properties_new, main_buildings, registrations
- **Listings**: cases, case_images, price_changes, days_on_market
- **Geographic**: municipalities, provinces, cities, zip_codes, roads, places

## Architecture

### Data Pipeline
```
Boligsiden API (228K+ properties)
         ↓
Import Scripts (20 parallel workers, run on homelab)
         ↓
PostgreSQL (homelab, Seagate 8TB, Docker port 5434)
    ↙                    ↘                    ↘
Daily Refresh     Weekly Refresh        Parquet Export
(~45 min)         (~2-3 hrs)           (87.6 MB backup)
                                             ↓
         ↓                            Portable System
    Tailscale VPN (100.83.229.69)
         ↓
    VPS Flask App (Docker, gunicorn)
         ↓
    Traefik reverse proxy
         ↓
    https://ai-vaerksted.cloud/housing
```

### Web Application Components
- **Search Interface**: Filter by municipality, price, size, rooms, year, status
- **Results Page**: Sortable list with pagination (50 per page)
- **Property Details**: Full property information with images
- **Statistics**: Market analytics dashboard (see docs/STATISTICS_PLAN.md)

## Subsystem: Copenhagen apartment monitor (`kbh/`)

A second, independent system living in `kbh/`. It watches **apartments** in
København and Frederiksberg between 5 and 10 mio. kr., scores them, has Claude
read each listing, and pushes the good ones to Telegram.

It shares nothing with the villa pipeline above except the repo. Own SQLite
store at `kbh/data/kbh.sqlite3`, own config, own Flask app on port 5001. It does
not touch PostgreSQL. Changing anything in `src/`, `webapp/` or `scripts/` has no
effect on it, and the reverse holds.

```bash
python -m kbh.pipeline run      # fetch, score, verdicts, alerts
python -m kbh.webapp.app        # UI on port 5001
python -m kbh.bot               # interactive Telegram bot
```

Full documentation, including API findings that **correct** several of the
"Critical API Learnings" above, is in [kbh/README.md](kbh/README.md). In
particular: `/search/cases` returns the full payload so no detail call is needed,
`municipalities` accepts only one name at a time, and `hasBalcony` is unreliable.

## Documentation
See [docs/INDEX.md](docs/INDEX.md). Do not create new docs without updating INDEX.

## Related Documentation
- **Database Schema Details**: See `docs/DATABASE_SCHEMA.md` for complete 14-table structure and field definitions
- **Project Summary**: See `docs/PROJECT_SUMMARY.md` for high-level technical overview
- **Update Strategy**: See `docs/UPDATE_SCHEDULE.md` for refresh timing and data freshness details
- **File Organization**: See `docs/PROJECT_STRUCTURE.md` for folder structure explanation
- **Statistics Plan**: See `docs/STATISTICS_PLAN.md` for housing market statistics feature
