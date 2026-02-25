# Implementation Summary — Statistics Feature (Feb 2026)

**Purpose:** Handoff document for agents. What was built, what remains, how to run it.

---

## What Was Implemented

### 1. Statistics API (`webapp/app.py`, `webapp/statistics_queries.py`)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/statistics/health` | Health check: ok, data_as_of, row_counts. Returns 503 when DB unavailable. |
| `GET /api/statistics/market-overview` | Active listings, sold this month, avg kr/m² (national). Cache 5 min. |
| `GET /api/statistics/price-trends` | Time series: avg kr/m² by month. Params: municipality, period, months. |
| `GET /api/statistics/sales-volume` | Time series: houses sold per month. Params: municipality, months. |
| `GET /api/statistics/kommune-summary` | Per-kommune: sales, avg price, YoY %, avg m². Cache 5 min. |
| `GET /api/statistics/weekly-summary` | Compact digest for OpenClaw. Params: format=text\|json. |

**Data source:** `registrations` (type='normal'), `cases`, `properties_new`, `municipalities`. Joins via property_id.

### 2. Statistics Dashboard (`webapp/templates/statistics.html`)

- Route: `/statistics`
- KPI cards: active listings, sold this month, avg kr/m²
- Chart.js: price trends (line), sales volume (bar)
- Kommune comparison table
- Nav links added to home, search, score-calculator

### 3. Scripts

| Script | Purpose |
|--------|---------|
| `scripts/add_statistics_indexes.py` | Idempotent index creation for registrations, cases, price_changes. Run once after deploy. |
| `scripts/verify_import_integrity.py` | Post-import checks: row counts, date coverage, municipality coverage, price sanity. |

### 4. Fixes Applied

- **Duplicate routes:** Removed duplicate `api_personas` and `property_score` (caused AssertionError).
- **CLAUDE.md:** Resolved merge conflict; set app entry to `app.py` (was app_FIXED.py).
- **Archived:** `docs/CLAUDE_TEMPLATE.md` → `archive/CLAUDE_TEMPLATE.md`.
- **Error handling:** Statistics endpoints return 503 (not 500) when DB unavailable.

### 5. Tests (`tests/test_statistics_api.py`)

- Tests accept 200 (DB up) or 503 (DB down).
- Run: `API_BASE_URL=http://127.0.0.1:5001 python tests/test_statistics_api.py`
- Production: `API_BASE_URL=https://ai-vaerksted.cloud HOUSING_BASE=/housing python tests/test_statistics_api.py`

---

## Database Location

- **Production:** housing-db runs on **VPS** (72.61.179.126) as Docker container, internal to ai-vaerksted stack.
- **Homelab:** housing-db can run on homelab (192.168.0.252) at `~/homelab/apps/housing-db`, port 5434, for local dev.

---

## Future Next Step: Move Housing DB to Homelab

**Planned:** Move housing-db fully to homelab (192.168.0.252). Currently production DB is on VPS. Homelab would host the DB; housing app on VPS would connect via Tailscale or SSH tunnel. Benefits: centralize data on homelab, reduce VPS storage, align with Finnish DB pattern.

---

## Deployment Checklist (for next agent)

1. Deploy to VPS: rebuild ai-vaerksted-housing, restart.
2. Run indexes: `python scripts/add_statistics_indexes.py` (inside container or with DB access).
3. Verify: `curl https://ai-vaerksted.cloud/housing/api/statistics/health`
4. OpenClaw: `curl https://ai-vaerksted.cloud/housing/api/statistics/weekly-summary?format=text`

---

## Files Changed (commit af64e4e)

- `webapp/app.py` — Statistics routes, error handling, duplicate route removal
- `webapp/statistics_queries.py` — New: query helpers
- `webapp/templates/statistics.html` — New: dashboard
- `webapp/templates/home.html`, `index.html`, `score_calculator.html` — Nav links
- `scripts/add_statistics_indexes.py` — New
- `scripts/verify_import_integrity.py` — New
- `tests/test_statistics_api.py` — New
- `docs/STATISTICS_PLAN.md` — New: full plan
- `docs/INDEX.md` — Added STATISTICS_PLAN
- `claude.md` — Merge conflict resolved, app entry point
- `archive/CLAUDE_TEMPLATE.md` — Moved from docs/
