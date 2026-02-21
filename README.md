# Danish Housing Market Search

A production-ready system for analyzing the Danish housing market. Imports, stores, and analyzes villa properties from the Boligsiden API across 36 municipalities within 60 km of Copenhagen.

**🌐 Production**: https://ai-vaerksted.cloud/housing

---

## Features

- **228,000+ properties** — villas across the greater Copenhagen area
- **Full-text & filter search** — municipality, price, size, rooms, year built, market status
- **Property scoring** — 8-factor composite score with persona-based weights
- **Dual architecture** — PostgreSQL backend for full features, file-based portable system for offline use
- **Daily/weekly data refresh** — automated imports via Boligsiden API

---

## Quick Start

### Option A: Portable System (no database required)

```bash
cd portable
pip install -r requirements_portable.txt
python app_portable.py
# Open http://127.0.0.1:5000
```

### Option B: Full PostgreSQL System

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env with your database credentials
echo "DATABASE_URL=postgresql://postgres:PASSWORD@localhost:5432/housing_db" > .env

# 3. Start the web app
python webapp/app.py
# Open http://127.0.0.1:5000
```

### Import Data

```bash
# Full import (~2-3 hours, 228K properties)
python scripts/import_copenhagen_area.py

# Daily refresh (~30-45 min, active listings only)
python scripts/quick_update.py
```

---

## Project Structure

```
Danish-Housing-Market-Search/
├── webapp/          # Flask web application (PostgreSQL + portable variants)
├── portable/        # Self-contained file-based system (Parquet data)
├── src/             # Core source code (ORM models, database, scoring engine)
│   └── scoring/     # 8-factor property scoring system with persona profiles
├── scripts/         # Data import and maintenance scripts
├── tests/           # Test suite
└── docs/            # Additional documentation
```

---

## Scoring System

Properties are ranked using 8 weighted factors:

| Factor | Default Weight |
|--------|---------------|
| Price per sqm vs. municipal average | 20% |
| Location premium | 18% |
| Age & condition | 15% |
| Price trend (3-year) | 15% |
| Size optimality (Gaussian, centered at 100 m²) | 12% |
| Market velocity (days on market) | 10% |
| Transaction volume | 5% |
| Floor desirability | 5% |

Four buyer personas (`space_conscious`, `price_conscious`, `location_conscious`, `condition_investment`) re-weight these factors to match different priorities.

---

## Documentation

| File | Contents |
|------|----------|
| `docs/DATABASE_SCHEMA.md` | 14-table PostgreSQL schema |
| `docs/PROJECT_SUMMARY.md` | Technical overview |
| `docs/UPDATE_SCHEDULE.md` | Data refresh strategy |
| `src/scoring/README.md` | Scoring system API reference |
| `CI_CD_GUIDE.md` | CI/CD pipeline guide |
| `DEPLOYMENT_CONFIG.md` | Docker / VPS deployment |
| `LOCAL_TESTING_GUIDE.md` | Local development & testing |

---

## Tech Stack

- **Backend**: Python 3.x, Flask
- **Database**: PostgreSQL 15 (primary) + Parquet files (portable)
- **ORM**: SQLAlchemy
- **Data processing**: Pandas, NumPy
- **Frontend**: Jinja2 templates, Bootstrap
- **Containerization**: Docker / Docker Compose
