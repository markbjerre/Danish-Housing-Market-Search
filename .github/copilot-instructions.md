# Copilot Instructions for Danish Housing Market Search

## Project Overview
Production system analyzing 228K+ Danish villa properties. Dual architecture: **PostgreSQL backend** (`webapp/app.py`) for full features, **file-based portable system** (`portable/app_portable.py`) for offline use. Data imported from Boligsiden API across 36 municipalities within 60km of Copenhagen.

**🌐 Production URL**: https://ai-vaerksted.cloud/housing  
**📦 VPS Location**: `/opt/ai-vaerksted/Danish-Housing-Market-Search/`  
**🐳 Docker Container**: `ai-vaerksted-housing`  
**🗄️ Database**: PostgreSQL 15 (`housing-db` container)

## Critical Architecture Patterns

### Dual System Architecture
- **Primary**: PostgreSQL with SQLAlchemy ORM (`src/db_models_new.py` - 14 normalized tables)
- **Portable**: Pandas/Parquet replacement (`src/file_database.py` - identical query interface)
- **Key pattern**: Both systems share same query patterns; abstracting to interface enables easy switching
- **When modifying queries**: Update both `webapp/app.py` (PostgreSQL) and `portable/app_portable.py` (file-based)

### Boligsiden API Integration
- **Critical field names** (API uses exact case):
  - `priceCash` NOT `price`
  - `zipCodes` (plural) NOT `zipCode`  
  - Nested: `images[{width: 600, height: 400}]` NOT flat strings
- **10K pagination limit**: Large municipalities (Copenhagen, Aarhus) require zip code subdivision strategy
- **Rate limiting**: Keep requests ≤10/sec; implement exponential backoff in `import_copenhagen_area.py`
- **Store URLs not files**: CDN is reliable; avoids 180GB+ storage overhead

### Data Pipeline & Performance
- **Import speed**: 20-30 properties/sec with `ThreadPoolExecutor(max_workers=20)` in `scripts/import_copenhagen_area.py`
- **Full import**: 2-3 hours all municipalities; **daily refresh**: 30-45 min (active listings only)
- **Parquet compression**: ~87.6 MB compressed vs several GB uncompressed database
- **Portable app**: In-memory data loads in seconds, queries instant

## Code Patterns & Conventions

### Database Models & Sessions
```python
# Always use context manager for sessions to prevent leaks
session = db.get_session()
try:
    properties = session.query(Property).filter(Property.is_on_market == True).all()
    # Process data
finally:
    session.close()

# OR use Flask blueprint pattern with implicit cleanup
```

### Query Performance
- **Avoid N+1 problems**: Use `.join()` with `relationship` objects, not sequential queries
- **Leverage relationships**: `Property.municipality_info`, `Property.registrations` defined in models
- **Index-friendly**: Common filters: `is_on_market`, `zip_code`, `municipality.name`
- **Example pattern** (`src/webapp/app.py` lines 45-80):
  ```python
  query = session.query(Property).join(Property.municipality_info)
  if municipality: 
      query = query.filter(Municipality.name == municipality)
  ```

### Type Hints & Documentation
- **All functions**: Type hints for parameters and return values (PEP 484)
- **Public functions**: Google-style docstrings (3-line minimum)
- **Complex logic**: Inline comments explaining "why" not "what"
- **Example** from `import_copenhagen_area.py`:
  ```python
  def parse_property_response(raw_data: Dict[str, Any]) -> Property:
      """Extract and validate property from API response.
      
      Args:
          raw_data: JSON response from Boligsiden API
          
      Returns:
          SQLAlchemy Property object with validated fields
      """
  ```

### Error Handling Patterns
- **API calls**: Exponential backoff + max retries (see `import_copenhagen_area.py`)
- **Database**: Session cleanup on exception; rollback partial writes
- **Missing data**: Use `.get()` with defaults; never assume nested API fields exist

## File Organization & Conventions

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `src/` | Core logic | `db_models_new.py` (14 ORM tables), `database.py` (PostgreSQL session), `file_database.py` (Parquet queries) |
| `webapp/` | Flask web app | `app.py` (PostgreSQL), `app_portable.py` (file-based), `templates/` (Jinja2) |
| `portable/` | Offline system | Symlink/copy of portable files + data backups |
| `scripts/` | Data pipeline | `import_copenhagen_area.py` (main importer, 20 workers), `quick_update.py` (daily refresh) |
| `tests/` | Validation | Currently exploratory; pytest recommended for future unit tests |
| `archive/` | Historical | 70+ old files; move unused code here aggressively |

## Development Workflows

### Local Setup (PostgreSQL)
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
# Create .env: DATABASE_URL=postgresql://postgres:PASSWORD@localhost:5432/housing_db
python webapp/app.py  # http://127.0.0.1:5000
```

### Portable System (No Database)
```bash
cd portable
pip install -r requirements_portable.txt
python app_portable.py  # http://127.0.0.1:5000
```

### Import New Data
```bash
# Full import (2-3 hours, ~228K properties)
python scripts/import_copenhagen_area.py

# Daily refresh (30-45 min, active listings only)
python scripts/quick_update.py
```

### Backup to Parquet
```bash
python scripts/backup_database.py  # Creates timestamped export_YYYYMMDD_HHMMSS/
```

## Common Tasks & Anti-Patterns

| Task | ✅ Do This | ❌ Don't |
|------|----------|---------|
| **Add filter** | Update both `app.py` AND `app_portable.py` query builders | Filter only in PostgreSQL; portable system breaks |
| **Store media** | Save CDN URLs as strings in `JSON` field | Download and store files locally (180GB overhead) |
| **Handle missing API fields** | Use `.get(key, default)` on dicts | Direct key access; crashes on API schema changes |
| **Import optimization** | Use `ThreadPoolExecutor` with 20 workers (proven rate) | Sequential imports (takes 10x longer) |
| **Test changes** | Run on portable system first (faster iteration) | Always full DB cycle (slower feedback) |

## Known Gotchas

1. **API pagination**: Boligsiden caps results at 10K per query. Zip code subdivision mandatory for large municipalities.
2. **Nullable nested fields**: `images`, `cases`, `registrations` may be empty lists. Check `len()` before indexing.
3. **Windows encoding**: `file_database.py` includes `safe_print()` to handle Unicode in console (replace emojis with ASCII).
4. **Session closure**: PostgreSQL connections must close to prevent pool exhaustion during long imports.
5. **Parquet datetime**: Stored as UTC; convert to timezone-aware Python datetime when needed.

## When to Reach Out

- **API integration changes**: Verify field names against latest Boligsiden docs; implement in both importers
- **Query performance**: Profile with `.explain()` on new filters; add indices if needed
- **Data schema expansion**: Update `db_models_new.py`, then `backup_database.py`, then portable app
- **Cross-system consistency**: Any PostgreSQL change must have equivalent Parquet/file-based version

## References

- **Architecture**: `claude.md` (project overview), `docs/DATABASE_SCHEMA.md` (14-table design)
- **Import logic**: `scripts/import_copenhagen_area.py` (main implementation with API quirks)
- **Web interface**: `webapp/app.py` (search/filter endpoints), `webapp/templates/` (UI)
- **Portable layer**: `src/file_database.py` (Pandas query implementation)
