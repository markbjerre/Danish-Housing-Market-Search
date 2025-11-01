# Scoring Model Implementation - Quick Start Guide

## Overview

This is a plan to implement the **Property Scoring Model** - the biggest TODO item in the project. The scoring system will rank properties based on weighted factors (price, location, size, quality, etc.) with customizable user preferences.

**Estimated Time:** 20-25 days for basic version  
**Current Status:** Planning complete, ready to implement  
**Priority:** High

---

## The Problem

Users need a way to find properties that match their priorities:
- Value hunters want best price per m²
- Luxury seekers want premium features
- Families want space and schools
- Investors want renovation potential

Currently, users must manually filter and compare properties. The scoring model automates this.

---

## The Solution

A weighted scoring algorithm that:
1. Scores properties on 8+ factors (0-10 each)
2. Applies user-defined weights (or preset profiles)
3. Returns ranked list with score breakdowns
4. Provides filter presets (Dream Home, Value Deal, Investment)

---

## Implementation Strategy

### Option A: Start with MVP (Recommended)
**Focus:** Get core functionality working first

**Week 1:** Core Scoring (Phase 2)
- Implement 5-6 core factors: price_per_sqm, living_area, distance, bathrooms, renovation, energy
- Create PropertyScorer class with weighted formula
- Add 3-5 preset profiles

**Week 2:** API Integration (Phase 4)
- Build `/api/score` endpoint for single property
- Build `/api/score/batch` for multiple properties
- Build `/api/score/presets` for preset configurations
- Connect frontend to backend

**Week 3:** Filters & Testing (Phase 3 & 5)
- Add base filter functions (Dream Home, Value Deal, Investment)
- Comprehensive testing with real data
- Calibration and tuning

**Result:** Fully functional scoring system users can start using

---

### Option B: Research-First Approach
**Focus:** Deep analysis before implementation

**Week 1:** Market Analysis (Phase 1)
- Analyze price distributions per municipality
- Study correlations (renovation vs price, energy vs price)
- Calculate feature importance
- Document insights

**Week 2-3:** Implementation based on research findings
- Use analysis insights to calibrate scoring
- Implement algorithm with data-driven weights

**Result:** More accurate scoring, but delayed delivery

---

## Recommended Approach: Hybrid

**Start with MVP (Option A) while running analysis in parallel (Option B)**

1. **Day 1-2:** Implement basic scoring factors with reasonable defaults
2. **Day 3-5:** Build API endpoints and frontend integration
3. **Day 6-7:** Deploy MVP and gather user feedback
4. **Ongoing:** Run Phase 1 analysis scripts in background
5. **Week 2-3:** Refine weights and add filters based on analysis + feedback

---

## Key Files to Create/Modify

### New Files
```
src/scoring/
  __init__.py
  factors.py              # Individual scoring functions
  presets.py              # Preset weight configurations
  filters.py              # Base filter functions
  database_helpers.py     # DB query utilities

scripts/analysis/
  market_analysis.py      # Phase 1 analysis
  feature_importance.py   # Correlation analysis

tests/
  test_scoring.py         # Unit tests
  test_scoring_comprehensive.py  # Integration tests
```

### Files to Modify
```
src/scoring.py           # Complete rewrite - main PropertyScorer class
webapp/app.py            # Add scoring API endpoints
webapp/templates/score_calculator.html  # Connect to backend
requirements.txt         # Add geopy for distance calculations
```

---

## Critical Implementation Details

### 1. Distance Calculation
**Need:** Calculate distance from each property to Copenhagen center
**Solution:** 
- Use Haversine formula (geopy library)
- Or pre-calculate during import (add `distance_to_copenhagen` column)
- Copenhagen center: lat 55.6761, lon 12.5683

### 2. Municipality Statistics
**Need:** Average/min/max price per m² per municipality
**Solution:**
- Query: `SELECT municipality, AVG(price/living_area) FROM properties_new JOIN municipalities GROUP BY municipality`
- Cache results (update weekly/monthly)
- Use for price_per_sqm normalization

### 3. Missing Data Handling
**Problem:** Some properties lack basement_area, renovation_year, plot_size
**Solution:**
- Default to 0 for missing areas
- Use `year_built` if `year_renovated` is NULL
- Skip factors with no data (don't penalize property)

### 4. Performance
**Challenge:** Scoring 228K+ properties
**Solution:**
- Batch API endpoints with pagination (max 1000 per request)
- Optional: Add `cached_score` column for pre-computed scores
- Background jobs for full database scoring

---

## Quick Implementation Checklist

### Core Scoring (MVP)
- [ ] Rewrite `src/scoring.py` with PropertyScorer class
- [ ] Implement 6 core factors:
  - [ ] Price per m² (municipality-normalized)
  - [ ] Living area (diminishing returns)
  - [ ] Distance to Copenhagen
  - [ ] Basement area
  - [ ] Number of bathrooms
  - [ ] Renovation year
  - [ ] Energy label
- [ ] Create 5 preset profiles (presets.py)
- [ ] Write unit tests for each factor

### API Endpoints
- [ ] `/api/score` - Single property scoring
- [ ] `/api/score/batch` - Multiple properties (with pagination)
- [ ] `/api/score/presets` - List preset configurations
- [ ] Error handling for missing data

### Frontend Integration
- [ ] Connect score calculator page to `/api/score` endpoint
- [ ] Display final score and factor breakdown
- [ ] Add preset buttons that call API with preset names
- [ ] Weight sliders update scores in real-time

### Testing & Validation
- [ ] Test with 100 random properties
- [ ] Verify score distribution (should span 0-100)
- [ ] Check edge cases (missing data, outliers)
- [ ] Manual validation: top 10 scored properties make sense?

---

## Success Criteria

✅ **MVP Complete When:**
1. User can select a preset profile
2. API returns scored properties ranked by score
3. Frontend displays score breakdown
4. Scores are intuitive (high = desirable)

✅ **Full Implementation Complete When:**
1. All 8+ factors implemented
2. All preset profiles working
3. Filter functions available
4. Comprehensive test suite passing
5. Performance acceptable (<2s for 100 properties)

---

## Next Action Items

1. **Review this plan** - Confirm approach and priorities
2. **Set up development environment** - Install geopy, create scoring/ directory
3. **Start with core factors** - Implement price_per_sqm, living_area, distance first
4. **Test incrementally** - Don't wait for full implementation to test
5. **Iterate based on feedback** - Get MVP working, then refine

---

## Questions to Answer Before Starting

1. **Distance calculation:** Pre-calculate during import or calculate on-the-fly?
   - **Recommendation:** Pre-calculate (add column during import)

2. **Municipality stats:** Calculate on-the-fly or cache?
   - **Recommendation:** Cache (update weekly via cron job)

3. **Score caching:** Store computed scores in database?
   - **Recommendation:** Optional optimization (Phase 4.3), not required for MVP

4. **Frontend priorities:** Which features are must-have vs nice-to-have?
   - **Must-have:** Score display, preset buttons, weight sliders
   - **Nice-to-have:** Visual breakdown charts, compare mode

---

## Related Documentation

- **Full Plan:** `docs/SCORING_MODEL_IMPLEMENTATION_PLAN.md`
- **Original TODO:** `archive/SCORING_MODEL_TODO.md`
- **Database Schema:** `docs/DATABASE_SCHEMA.md`
- **Current Scoring Code:** `src/scoring.py` (basic implementation exists)
