# Danish Housing Market Search - Development Guide

## Project Overview

**Type**: Full-Stack Python Flask + Data Analysis  
**Status**: Production with data import pipeline  
**Live URL**: https://ai-vaerksted.cloud/housing  
**Repo**: `/Danish Housing Market Search`

### Key Stats
- 228K+ properties in database
- PostgreSQL + Parquet backups
- Advanced search filters
- Scoring system for properties

### Architecture
```
src/
├── main.py                  # Flask app
├── database.py             # SQLAlchemy setup
├── db_models.py            # ORM models
├── data_loader.py          # Data import
├── property_data.py        # API logic
└── scoring/                # Scoring engine
    ├── calculator.py
    ├── factors.py
    ├── profiles.py
    └── interpreter.py

webapp/
├── app.py                  # Web server
├── templates/              # HTML templates
└── scoring_api.py          # Scoring endpoints

scripts/
├── import_api_data.py      # Boligsiden scraper
├── scheduler.py            # Periodic updates
└── init_production_db.py   # Database init
```

---

## Development Stack

| Component | Tech | Details |
|-----------|------|---------|
| **Backend** | Python 3.11, Flask | Port 8003 |
| **Database** | PostgreSQL, SQLAlchemy | Local dev DB |
| **Data** | Boligsiden API, Parquet | Import pipeline |
| **Scoring** | Custom algorithm | 100+ scoring factors |
| **Testing** | pytest, Playwright | E2E & unit tests |

---

## Quick Start

### Docker
```bash
docker-compose -f docker-compose.dev.yml up housing-backend
# http://localhost:8003
```

### Local Development
```bash
cd "Danish Housing Market Search"
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask run
```

### Environment Setup
```env
FLASK_ENV=development
FLASK_DEBUG=1
DATABASE_URL=sqlite:////app/data/housing.db
```

---

## Agent Strategies

### For Feature Development
**fullstack-developer**:
- Add search filters
- Create scoring endpoints
- Implement data import scripts

### For Data Pipeline
**fullstack-developer**:
- Enhance Boligsiden scraper
- Optimize database queries
- Add data validation

### For Testing
**fullstack-developer**:
- Write integration tests
- Test scoring system
- Validate data imports

---

## Key APIs

```
GET /health                           # Health check
GET /api/properties?filters=...       # Search with filters
GET /api/properties/<id>/score        # Get property score
GET /api/municipalities               # Municipality list
GET /api/scoring-analysis?ticker=META # Scoring breakdown
```

---

## Database

### Import Data
```bash
# Quick import (small sample)
python scripts/import_api_data.py --quick

# Full import
python scripts/import_api_data.py --full

# Scheduled updates
python scripts/scheduler.py
```

### Backup/Restore
```bash
# Export to Parquet
python scripts/update_parquet_from_api.py

# View data
python utils/view_database.py
```

---

## Troubleshooting

### Database Errors
```bash
# Reset database
python utils/reset_tables.py

# Check database
python utils/view_database.py

# Check import status
python utils/check_import_status.py
```

### API Issues
```bash
# Test endpoint
curl http://localhost:8003/health

# View Flask logs
docker logs housing-backend-dev
```

---

## Code Conventions

- 4-space indentation (PEP 8)
- Type hints required
- Google-style docstrings
- Snake_case functions/variables

---

## Useful Commands

```bash
# Database
python scripts/init_production_db.py
python scripts/clear_db.py
python scripts/reset_db.py

# Testing
pytest tests/
pytest tests/test_search_filters.py -v

# Docker
docker-compose -f docker-compose.dev.yml up
docker logs housing-backend-dev -f
```

---

## Next Steps

1. Optimize search performance (add indexes)
2. Enhance scoring algorithm
3. Add recommendation engine
4. Implement price prediction
5. Add map view integration
