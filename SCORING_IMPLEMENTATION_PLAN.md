# Property Scoring System - Implementation Plan

## 📋 Executive Summary

This document outlines the complete implementation plan for a sophisticated property scoring system that evaluates 228,594+ properties across multiple factors. The system is designed in 3 tiers:

- **TIER 1 (MVP)**: 8 core factors - **PHASE 1-3 (1-2 weeks)**
- **TIER 2 (Advanced)**: 4 additional factors - **PHASE 4-5 (weeks 2-3)**  
- **TIER 3 (Premium)**: ML-ready features for future optimization

---

## 🎯 Scoring Factors - TIER 1 MVP (8 Factors)

### Factor 1: Price per m² Value (20% weight)
- **Goal**: Identify undervalued properties
- **Calculation**: Compare property price/m² to municipal average
- **Scoring**: 20%+ below market = 100pts, at market = 80pts, 20%+ above = 0pts
- **Data**: `properties.price_per_sqm`, municipality aggregates

### Factor 2: Size Optimality (12% weight)
- **Goal**: Prefer "Goldilocks" properties (sweet spot 80-120m²)
- **Calculation**: Gaussian curve centered at 100m²
- **Scoring**: 100m² = 100pts, tapers off toward extremes
- **Data**: `properties.living_area`

### Factor 3: Age & Condition (15% weight)
- **Goal**: Prefer newer or recently renovated
- **Calculation**: Effective age = max(year_built, last_renovated)
- **Scoring**: Newer = higher (0 points at 125+ years)
- **Data**: `properties.year_built`, renovation date

### Factor 4: Location Premium (18% weight)
- **Goal**: Assess municipality & postal code desirability
- **Calculation**: Combine population size + postal code income
- **Scoring**: Copenhagen with high income = 100pts
- **Data**: Municipality population, postal code income

### Factor 5: Market Velocity (10% weight)
- **Goal**: Properties selling faster than average = higher score
- **Calculation**: Days on market vs municipal average
- **Scoring**: Below average = 100pts, linear penalty for longer sales
- **Data**: `properties.days_on_market`, market aggregates

### Factor 6: Price Trend (15% weight)
- **Goal**: Identify bargains where price growth lags market
- **Calculation**: 3-year price change vs market trend
- **Scoring**: Lagging market = higher score (100), ahead = lower (0)
- **Data**: `price_history` table, market trend data

### Factor 7: Floor Desirability (5% weight)
- **Goal**: Prefer ground to 3rd floor
- **Calculation**: Fixed scoring by floor level
- **Scoring**: Floors 1-3 = 100, ground = 70, high floors penalized
- **Data**: `properties.floor`

### Factor 8: Transaction Volume (5% weight)
- **Goal**: More sales = better liquidity
- **Calculation**: Annual sales count in postal code
- **Scoring**: Active market (50+ sales/year) = 100pts
- **Data**: `price_history` aggregated by postal code

**Total TIER 1 Weight: 100%**

---

## 📊 Architecture Overview

```
Property → Filter Aggregates → Calculate Factors → Normalize (0-100) 
         → Weight Sum → Composite Score → Percentile Rank → Display
```

Database stores pre-calculated scores for fast retrieval and pagination.

---

## 🗄️ Database Changes Required

### New Tables

```sql
CREATE TABLE property_scores (
    property_id VARCHAR(50) PRIMARY KEY,
    composite_score DECIMAL(5,2),
    percentile_rank DECIMAL(5,2),
    -- Individual factor scores
    price_per_sqm_score DECIMAL(5,2),
    size_score DECIMAL(5,2),
    age_score DECIMAL(5,2),
    location_score DECIMAL(5,2),
    velocity_score DECIMAL(5,2),
    trend_score DECIMAL(5,2),
    floor_score DECIMAL(5,2),
    volume_score DECIMAL(5,2),
    -- Metadata
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tier_version VARCHAR(10) DEFAULT 'TIER1_MVP',
    INDEX idx_composite_score (composite_score DESC),
    INDEX idx_percentile (percentile_rank DESC)
);

CREATE TABLE market_aggregates (
    municipality_code VARCHAR(10) PRIMARY KEY,
    avg_price_per_sqm DECIMAL(10,2),
    avg_days_on_market DECIMAL(6,2),
    avg_3yr_price_change_pct DECIMAL(6,2),
    total_transactions_last_year INT,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE postal_aggregates (
    postal_code VARCHAR(10) PRIMARY KEY,
    avg_price_per_sqm DECIMAL(10,2),
    transaction_count_last_year INT,
    avg_income DECIMAL(10,2),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### New Indexes

```sql
CREATE INDEX idx_properties_price_sqm ON properties(price_per_sqm);
CREATE INDEX idx_properties_size ON properties(living_area);
CREATE INDEX idx_properties_year ON properties(year_built);
CREATE INDEX idx_price_history_property ON price_history(property_id, transaction_date DESC);
CREATE INDEX idx_price_history_postal ON price_history(postal_code, transaction_date DESC);
```

---

## 🔌 API Endpoints

### 1. Get Property Score
```
GET /api/property/<property_id>/score

Response:
{
  "property_id": "12345",
  "composite_score": 85.5,
  "percentile_rank": 92.3,
  "factor_breakdown": {
    "price_per_sqm_value": {score: 92, weight: 0.20, ...},
    "size_optimality": {score: 88, weight: 0.12, ...},
    // ... other factors
  },
  "interpretation": "Top 8% - excellent value with good fundamentals"
}
```

### 2. Enhanced Search with Scoring
```
GET /api/search?min_score=75&sort_by=score_desc

New parameters:
- min_score: Filter by minimum score (0-100)
- max_score: Filter by maximum score
- sort_by: Add 'score_asc', 'score_desc'
- score_profile: 'value' (default), 'investment', etc. [TIER 2]

Response includes:
- Each property's composite_score and percentile
- Score distribution stats (min, max, avg, percentiles)
```

### 3. Batch Score Calculation (Admin)
```
POST /api/admin/calculate-scores

Body: {property_ids?: [...], tier: 'TIER1_MVP', force_recalculate: false}

Returns: {total: 228594, calculated: 228594, duration_seconds: 145.3}
```

---

## 🎨 Frontend Components

### Search Results Enhancement
- Add score badges to property cards (Excellent/Great/Good/Fair)
- "Top Scored Properties" featured section at top
- Score filter slider (min/max)
- Sort by score option
- Score distribution visualization

### Property Detail Page
- **Score Card** (prominent):
  - Large score display (85.5)
  - Badge indicator (Great Value, etc.)
  - Percentile rank (Top 15%)
  
- **Factor Breakdown**:
  - 8 factors with individual scores
  - Visual bars showing each factor contribution
  - Human-readable interpretation for each factor
  
- **Comparison Section**:
  - This property score vs neighborhood average
  - This property score vs city average
  
- **Actions**:
  - Save property button
  - Compare to similar button

### Interactive Score Calculator [TIER 2]
- Slider controls for weight adjustment
- Real-time score recalculation
- Save custom profile

---

## 📅 Implementation Timeline

### Phase 1: Core Scoring Engine (Days 1-7)

**Day 1-2: Database Setup**
- [ ] Create property_scores table
- [ ] Create market_aggregates and postal_aggregates tables
- [ ] Add indexes
- [ ] Write migration scripts
- [ ] Pre-calculate municipal aggregates

**Day 3-4: Scoring Logic**
- [ ] Create `/backend/scoring/` module
- [ ] Implement 8 factor classes
- [ ] Write normalization functions
- [ ] Implement composite score calculation
- [ ] Implement percentile ranking
- [ ] Unit tests for each factor (20+ test cases)

**Day 5-6: Batch Processing**
- [ ] Create batch scoring script
- [ ] Calculate scores for all 228K properties
- [ ] Implement incremental update logic
- [ ] Performance optimization (<1ms per property)
- [ ] Caching strategy

**Day 7: Validation**
- [ ] Verify score distribution (expect bell curve 40-80)
- [ ] Manual spot-check 20 properties
- [ ] Edge case testing (NULLs, outliers)
- [ ] Performance benchmarks

**Deliverables:**
- `backend/scoring/calculator.py`
- `backend/scoring/factors.py`
- `backend/scoring/aggregates.py`
- `scripts/calculate_scores.py`
- `tests/test_scoring.py`
- Fully populated `property_scores` table

---

### Phase 2: API Integration (Days 8-12)

**Day 8-9: API Endpoints**
- [ ] `/api/property/<id>/score` endpoint
- [ ] Enhanced `/api/search` with score fields
- [ ] Add score filtering & sorting params
- [ ] Score distribution in responses
- [ ] Integration tests

**Day 10-11: Performance Optimization**
- [ ] Query optimization (EXPLAIN ANALYZE)
- [ ] Result caching
- [ ] Monitor response times (<200ms p95)

**Day 12: Testing**
- [ ] Postman collection (15+ test cases)
- [ ] Load testing (100 concurrent users)
- [ ] Error handling verification

**Deliverables:**
- `backend/api/score_routes.py`
- Enhanced `backend/api/search.py`
- API documentation
- Postman test collection

---

### Phase 3: Frontend Display (Days 13-16)

**Day 13-14: Search Results**
- [ ] Score badges in property cards
- [ ] Top scored properties featured section
- [ ] Score filter slider
- [ ] Sort by score option
- [ ] Score visualization (bars, badges)

**Day 15: Property Detail Page**
- [ ] Score card component
- [ ] Factor breakdown visualization
- [ ] Comparison section
- [ ] Responsive design

**Day 16: Polish**
- [ ] UX review
- [ ] Cross-browser testing
- [ ] Mobile responsiveness
- [ ] Performance (lazy loading)

**Deliverables:**
- `frontend/components/ScoreCard.js`
- `frontend/components/ScoreBadge.js`
- `frontend/components/ScoreFilter.js`
- Updated search results page
- Updated property detail page
- CSS/styling for scores

---

### Phase 4: Score Profiles (Days 17-20)

- [ ] Define 4 profiles: Value, Investment, Family, Luxury
- [ ] Profile-specific weight adjustments
- [ ] Profile selector UI
- [ ] Documentation

---

### Phase 5: Advanced Features (Days 21-30)

- [ ] TIER 2 factors (4 additional)
- [ ] Interactive weight calculator
- [ ] Email alerts for high-scoring new listings
- [ ] Analytics & monitoring
- [ ] A/B testing framework

---

## ✅ Success Criteria

### Technical
- Score calculation: **<1ms per property**
- API response time: **<200ms p95**
- Batch processing: **Complete 228K in <5 minutes**
- Data completeness: **>90% of properties have all factors**

### Score Quality
- Distribution: **Mean 55-60, StdDev 15-20** (normal)
- Top 10% threshold: **Score >= 78**
- Expert validation: **80%+ agreement** with real estate professionals

### User Engagement
- Click-through increase: **30%+ on high-scored properties**
- Score filter usage: **50%+ of searches** within 4 weeks
- User error reports: **<5%**
- Session time increase: **20%+**

---

## 🚀 Getting Started

### Immediate Next Steps:
1. Review & approve scoring factors
2. Confirm weight allocations
3. Create database migration environment
4. Set up test data
5. Start Phase 1 implementation

### Questions to Resolve:
- Data availability (energy ratings, renovation dates, etc.)?
- Weight validation (A/B testing needed)?
- Gradual rollout or full launch?
- External validation (real estate experts)?

---

## 📎 File References

**Complete detailed plan with code examples:**
- Scoring factor implementations (3 full examples)
- API endpoint specifications with response schemas
- Frontend component designs with HTML mockups
- Performance test cases
- Risk assessment matrix
- Comprehensive testing strategy

See attached SCORING_SYSTEM_DETAILED_PLAN.md for complete code samples and technical specifications.

---

**Status**: Ready for implementation approval
**Estimated Duration**: 3 weeks (Phase 1-5)
**MVP Duration**: 1-2 weeks (Phase 1-3)
**Team Size**: 1 full-stack developer
**Risk Level**: Low (uses existing data, no external dependencies)

