# Housing Market Statistics — Evaluation & Implementation Plan

**Created:** February 2026  
**Status:** Implemented (see docs/IMPLEMENTATION_SUMMARY.md)  
**Purpose:** Evaluate current implementation, suggest statistics, and plan the statistics feature

---

## 1. Current Implementation Evaluation

### Strengths

- **Rich data:** 228K properties, 388K historical transactions (registrations), 3.6K active listings
- **Schema supports analytics:** `registrations` (date, amount, per_area_price, municipality_code), `cases` (status, sold_date, current_price, created_date), `price_changes`, `main_buildings` (living_area, year_built)
- **Geographic coverage:** 36 municipalities, municipality_code on registrations
- **Transaction types:** normal/family/auction/other for filtering
- **Basic stats endpoint:** `/stats` returns total properties, by_municipality, price_stats, area_stats

### Issues & Gaps

| Issue | Impact | Priority |
|-------|--------|----------|
| **Price stats use `latest_valuation`** | Not market prices; excludes active listing prices. Should use `cases.current_price` for listings and `registrations.amount` for sold. | High |
| **No date indexes** | `registrations.date`, `cases.sold_date`, `cases.created_date`, `price_changes.change_date` unindexed → slow time-series queries | High |
| **No statistics UI** | `/stats` returns JSON only; no dashboard, charts, or visualizations | High |
| **No time-series API** | No endpoints for price trends, sales volume by period, YoY comparisons | High |
| **No municipality-level stats** | Cannot compare municipalities (avg sqm price, sales count, price change) | High |
| **No pre-aggregation** | All stats computed on-the-fly; heavy queries on 388K registrations | Medium |
| **app.py vs app_FIXED.py** | Two app variants; `/api/stats` only in app_FIXED. Consolidate or clarify which is production | Medium |
| **Merge conflict in CLAUDE.md** | Unresolved `<<<<<<< HEAD` / `>>>>>>>` blocks | Low |

---

## 2. Suggested Statistics

### Tier 1 — Core (implement first)

| Statistic | Description | Data source | Granularity |
|-----------|-------------|-------------|-------------|
| **Sqm price over time** | Median/avg kr per sqm by month | `registrations` (per_area_price, living_area) | National, municipality |
| **Houses sold** | Count of sales per period | `registrations` (type='normal'), `cases` (status='sold') | Month, quarter, year |
| **Kommune summary** | Per-municipality overview | Aggregations | Municipality |
| **Avg sqm price (current)** | Current market: listings + recent sales | `cases.current_price` / `living_area`, `registrations` | Municipality |
| **Sqm price change YoY** | % change in sqm price vs same period last year | `registrations` | Municipality |
| **Avg sqm in villas** | Mean living area by municipality | `properties_new.living_area`, `main_buildings.housing_area` | Municipality |

### Tier 2 — Enhanced

| Statistic | Description | Data source |
|-----------|-------------|-------------|
| **Days on market** | Median/avg days to sell | `cases.days_on_market_total`, `sold_date - created_date` |
| **Price reductions** | % of listings with price cuts, avg reduction | `price_changes`, `cases` |
| **Listings vs sales** | New listings vs sold per month | `cases.created_date`, `cases.sold_date` |
| **Price distribution** | P10, P25, P50, P75, P90 by municipality | `registrations.amount`, `cases.current_price` |
| **Transaction type mix** | % normal vs family vs auction | `registrations.type` |
| **Year built distribution** | Median year built, share built after 1990 | `main_buildings.year_built` |

### Tier 3 — Advanced

| Statistic | Description |
|-----------|-------------|
| **Zip code heatmap** | Sqm price by zip within municipality |
| **Price vs area scatter** | Relationship between size and price |
| **Energy label distribution** | Share by label (a–g) per municipality |
| **Market velocity** | Sales per month / active listings (turnover rate) |

---

## 3. Critical Review

### Correctness Risks

| Risk | Why it matters | Mitigation |
|------|----------------|------------|
| **registrations vs cases for "sold"** | Registrations = official land registry; cases.sold = Boligsiden listing closed. Counts can differ. | Document which source each stat uses; prefer registrations for historical sales (authoritative). |
| **per_area_price vs computed** | API may provide per_area_price; we can compute amount/living_area. Inconsistency skews trends. | Validate: if both exist, use per_area_price; else compute. Add sanity check (e.g. 10k–200k kr/sqm). |
| **Null/missing municipality_code** | Registrations without municipality_code break kommune aggregations. | Count nulls; exclude from kommune stats; log if >1%. |
| **Date range edge cases** | Empty periods (no sales) vs zero vs null. | Return explicit zeros for periods with no data; document date semantics. |
| **Double-counting** | One property, multiple registrations (e.g. 2 sales in same month). | Count transactions, not properties; document in API response. |

### Missing Infrastructure

| Gap | Impact | Add in |
|-----|--------|--------|
| **Health check for statistics** | No way to verify stats API is healthy before UI depends on it | Phase 1 |
| **Import completion verification** | Refresh/import can fail silently; stale data produces wrong stats | Phase 1 |
| **Data freshness metadata** | UI cannot show "data as of X"; users may trust stale data | Phase 2 |
| **Rate limiting on stats API** | Heavy aggregation queries could be abused | Phase 2 |
| **OpenClaw-friendly summary** | No lightweight endpoint for weekly digest; would need to scrape full DB | Phase 4 |

### Hardening Opportunities

- **Idempotent index creation** — Use `IF NOT EXISTS` or check before create
- **Query timeouts** — Set SQLAlchemy statement timeout (e.g. 30s) to avoid hung requests
- **Input validation** — Reject invalid date ranges, municipality names, period values
- **Audit logging** — Log stats API calls (endpoint, params, duration) for debugging
- **Graceful degradation** — If one stat fails, return partial response with error flag

---

## 4. Data Integrity & Scrape Controls

### Import/Refresh Verification

Add post-import checks that run after `refresh_listings.py` and `import_copenhagen_area.py`:

| Check | Pass criteria | Action on fail |
|-------|---------------|----------------|
| **Row counts** | registrations, cases, properties within expected bounds | Log warning; optional: write to `data_quality_log` |
| **Date coverage** | Latest registration date within last 30 days | Alert; stats may be stale |
| **Municipality coverage** | All 36 municipalities have ≥1 property | Log missing |
| **Price sanity** | No registration with amount < 10k or > 500M | Flag outliers |
| **Orphan check** | No case without property_id, no registration without property_id | Log |

**Implementation:** `scripts/verify_import_integrity.py` — run as final step in import/refresh; exit 1 on critical failures.

### API Scrape Controls (for stats endpoints)

| Control | Purpose |
|---------|---------|
| **Cache headers** | `Cache-Control: max-age=300` for overview/summary (5 min) to reduce load |
| **Date range limits** | Max 24 months for trends; reject invalid `from`/`to` |
| **Pagination** | kommune-summary returns all; price-trends limited to 100 points |
| **Response schema version** | Include `schema_version: 1` for future compatibility |

---

## 5. OpenClaw Integration

### Weekly Summary Endpoint

**Purpose:** OpenClaw (or cron) fetches a compact weekly digest without querying the full database.

**Endpoint:** `GET /api/statistics/weekly-summary`

**Query params:** `format=text` (default) or `format=json`

**Returns (compact JSON):**

```json
{
  "period": "2026-W08",
  "generated_at": "2026-02-25T12:00:00Z",
  "data_as_of": "2026-02-24",
  "summary": {
    "active_listings": 3623,
    "sold_last_7_days": 42,
    "avg_sqm_price_national": 45230,
    "sqm_price_yoy_pct": 3.2,
    "top_3_kommuner_by_sales": ["København", "Frederiksberg", "Gentofte"],
    "bottom_3_kommuner_by_price": ["Holbæk", "Faxe", "Stevns"]
  }
}
```

**Text format (for WhatsApp/Telegram):**

```
Housing Weekly (2026-W08)
Active: 3,623 | Sold (7d): 42 | Avg kr/sqm: 45,230 (+3.2% YoY)
Top sales: København, Frederiksberg, Gentofte
Lowest prices: Holbæk, Faxe, Stevns
```

**Implementation:** Single optimized query; pre-aggregate if needed. Response < 2KB.

**OpenClaw skill/cron:** Weekly (e.g. Monday 8:00) — `curl https://ai-vaerksted.cloud/housing/api/statistics/weekly-summary?format=text` → include in morning digest or standalone message.

---

## 6. Phased Implementation Plan

### Phase 0: Prerequisites (before statistics work)

| Task | Deliverable |
|------|-------------|
| Resolve CLAUDE.md merge conflict | Clean CLAUDE.md |
| Consolidate app.py vs app_FIXED.py | Single production app |
| Document which app is deployed | README/CLAUDE update |

### Phase 1: Infrastructure & Hardening

| Task | Details |
|------|---------|
| **1.1 Indexes** | `scripts/add_statistics_indexes.py` — idempotent (IF NOT EXISTS). Indexes: `registrations(date)`, `registrations(municipality_code, date)`, `registrations(type)`, `cases(sold_date)`, `cases(created_date)`, `cases(status)`, `price_changes(change_date)` |
| **1.2 Import verification** | `scripts/verify_import_integrity.py` — row counts, date coverage, sanity checks |
| **1.3 Stats health** | `GET /api/statistics/health` — returns `ok`, `data_as_of`, `row_counts` (lightweight) |
| **1.4 Query timeout** | SQLAlchemy `connect_args` or per-query timeout (e.g. 30s) |

**Exit criteria:** Indexes applied; verify script passes; health endpoint returns 200.

### Phase 2: Statistics API

| Task | Details |
|------|---------|
| **2.1 Endpoints** | price-trends, sales-volume, kommune-summary, market-overview |
| **2.2 Input validation** | Date range, municipality, period enum |
| **2.3 Data quality** | Filter type='normal'; handle nulls; document semantics |
| **2.4 Cache headers** | 5 min for overview/summary |
| **2.5 Data freshness** | Include `data_as_of` (max registration date) in responses |

**Exit criteria:** All endpoints return valid JSON; test with `tests/test_statistics_api.py`.

### Phase 3: Testing & Validation

| Task | Details |
|------|---------|
| **3.1 Unit tests** | Test aggregation logic with fixture data (small DB or mocks) |
| **3.2 Integration tests** | Hit live API; assert schema, non-null required fields, sane value ranges |
| **3.3 Correctness tests** | Spot-check: manual SQL vs API for one municipality, one month |
| **3.4 Performance** | Assert price-trends (12 months, 1 kommune) < 2s |
| **3.5 Edge cases** | Empty municipality, future dates, invalid params → 400 |

**Test file:** `tests/test_statistics_api.py` — extend `test_api_endpoints.py` pattern.

**Correctness checklist:**
- [ ] registrations count for "København" Jan 2025 matches manual SQL
- [ ] avg_sqm_price within 5% of manual calculation
- [ ] YoY % uses same period last year (not rolling)
- [ ] Empty period returns `{"data": [], "count": 0}` not error

### Phase 4: OpenClaw Integration

| Task | Details |
|------|---------|
| **4.1 Weekly summary endpoint** | `GET /api/statistics/weekly-summary` |
| **4.2 Text + JSON formats** | `format=text` for messaging, `format=json` for parsing |
| **4.3 OpenClaw skill** | New skill or extend morning-update to fetch housing summary |
| **4.4 Cron (optional)** | Weekly job to cache summary; or fetch on-demand |

**Exit criteria:** `curl .../weekly-summary?format=text` returns readable digest.

### Phase 5: Display (Web UI)

| Task | Details |
|------|---------|
| **5.1 Route** | `/statistics` → `statistics.html` |
| **5.2 Nav** | Add link from home, search page |
| **5.3 Sections** | Market overview (KPIs), Price trends (chart), Sales volume (chart), Kommune table |
| **5.4 Chart.js** | Line + bar charts; responsive |
| **5.5 Loading/error states** | Spinner; "Data unavailable" on API failure |
| **5.6 Data freshness** | Show "Data as of YYYY-MM-DD" on page |

**Exit criteria:** Statistics page loads; charts render; mobile-responsive.

### Phase 6: Optimization (optional, later)

- Materialized views for monthly aggregations
- Redis/in-memory cache for heavy queries
- Background precompute job

---

## 7. File Changes Summary

| File | Change |
|------|--------|
| `scripts/add_statistics_indexes.py` | New — idempotent index creation |
| `scripts/verify_import_integrity.py` | New — post-import data quality checks |
| `webapp/app.py` | Add `/statistics`, `/api/statistics/*`, `/api/statistics/health`, `/api/statistics/weekly-summary` |
| `webapp/templates/statistics.html` | New — dashboard |
| `webapp/static/js/statistics.js` | New — charts, API calls |
| `webapp/templates/home.html` | Add Statistics nav link |
| `tests/test_statistics_api.py` | New — health, overview, trends, kommune, weekly-summary, page load |
| `docs/INDEX.md` | Add STATISTICS_PLAN.md |

---

## 8. Dependencies

- No new Python packages (Flask, SQLAlchemy)
- Chart.js (CDN)
- Existing Bootstrap

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Slow queries | Indexes first; timeout; optional materialized views |
| Sparse price_changes | Use registrations for history |
| registrations vs cases mismatch | Document; prefer registrations for sales |
| Stale data | data_as_of in responses; verify script in import pipeline |
| OpenClaw overload | Weekly summary is single small response |

---

## 10. Success Criteria

- [x] Phase 0: Single app, clean CLAUDE.md
- [x] Phase 1: Indexes, verify script, health endpoint
- [x] Phase 2: All stats endpoints return valid data
- [x] Phase 3: test_statistics_api.py passes; correctness spot-check done
- [x] Phase 4: weekly-summary returns compact digest
- [x] Phase 5: Statistics page with charts, data freshness displayed

---

## 11. Future Next Step: Move Housing DB to Homelab

**Planned:** Move housing-db fully to homelab (192.168.0.252). Currently production DB is on VPS. Homelab would host the DB; housing app on VPS would connect via Tailscale or SSH tunnel. Benefits: centralize data on homelab, reduce VPS storage, align with Finnish DB pattern.
