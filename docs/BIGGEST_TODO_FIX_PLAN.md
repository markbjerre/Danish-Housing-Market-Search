# Biggest TODO Fix Plan - Property Scoring Model

**Date:** December 2024  
**Status:** Planning Complete ✅

---

## Identification

After analyzing the codebase, the **Property Scoring Model** is clearly the biggest TODO item:

### Evidence:
1. **Comprehensive Scope:** 6 phases, 20-25 days estimated work
2. **Documentation:** Detailed TODO in `archive/SCORING_MODEL_TODO.md` (299 lines)
3. **Impact:** Core feature that will transform user experience
4. **Current State:** Basic implementation exists but doesn't match requirements

### Comparison with Other TODOs:
- **File reorganization:** Already mostly done (scripts/, docs/ exist)
- **Database backup:** Simpler task (1-2 days)
- **Periodic updates:** Medium complexity (3-5 days)
- **Webpage enhancements:** Medium complexity (3-5 days)
- **Scoring Model:** High complexity (20-25 days), most comprehensive

---

## Current State Analysis

### What Exists:
✅ `src/scoring.py` - Basic scoring class (simple implementation)  
✅ `webapp/app.py` - Has `/score-calculator` route (placeholder)  
✅ `webapp/templates/score_calculator.html` - Frontend exists (preset buttons marked done)  
✅ Database schema - All required fields available (120+ fields across 14 tables)  
✅ Documentation - Detailed TODO list in archive folder  

### What's Missing:
❌ Comprehensive scoring algorithm matching TODO requirements  
❌ API endpoints (`/api/score`, `/api/score/batch`, etc.)  
❌ Preset profiles (Value Hunter, Luxury Seeker, etc.)  
❌ Base filter functions (Dream Home, Value Deal, Investment)  
❌ Database helpers for scoring calculations  
❌ Frontend-backend integration  
❌ Testing and validation framework  

---

## Implementation Plan Overview

### Phase 1: Research & Analysis (2-3 days)
- Market analysis (price distributions, correlations)
- Feature importance calculation
- User persona definition

**Priority:** Medium (can be done in parallel)

### Phase 2: Scoring Algorithm (3-5 days) ⭐ **START HERE**
- Implement 8+ scoring factors (price, area, distance, basement, bathrooms, renovation, energy, etc.)
- Create PropertyScorer class with weighted formula
- Implement preset profiles (5 presets)
- Unit tests

**Priority:** HIGH - Core functionality

### Phase 3: Base Filters (1-2 days)
- Dream Home filters
- Value Deal filters
- Investment Opportunity filters

**Priority:** Medium

### Phase 4: API & Integration (5-7 days) ⭐ **CRITICAL**
- Build `/api/score` endpoints
- Database helper functions
- Frontend integration
- Database optimizations (indexes, caching)

**Priority:** HIGH - Exposes functionality

### Phase 5: Validation (2-3 days)
- Comprehensive testing
- Calibration and tuning
- Edge case handling

**Priority:** High - Quality assurance

### Phase 6: Advanced Features (10+ days, ongoing)
- ML integration
- Neighborhood analytics
- Market trends

**Priority:** Low - Future enhancement

---

## Recommended Implementation Strategy

### MVP Approach (Fastest to Value)

**Week 1: Core Algorithm**
1. Day 1-2: Implement 6 core factors (price, area, distance, bathrooms, renovation, energy)
2. Day 3: Create PropertyScorer class and preset profiles
3. Day 4-5: Unit tests and basic validation

**Week 2: API & Frontend**
4. Day 6-7: Build `/api/score` and `/api/score/batch` endpoints
5. Day 8-9: Database helpers (municipality stats, distance calculation)
6. Day 10: Frontend integration and testing

**Week 3: Polish & Deploy**
7. Day 11-12: Add filter functions
8. Day 13-14: Comprehensive testing with real data
9. Day 15: Deployment and documentation

**Result:** Fully functional scoring system

---

## Key Technical Decisions

### 1. Distance Calculation
**Decision:** Pre-calculate during import (add `distance_to_copenhagen` column)  
**Rationale:** Avoids runtime overhead, distance doesn't change  
**Action:** Add migration script to calculate for existing properties

### 2. Municipality Statistics
**Decision:** Cache in database table or calculate on-demand with caching  
**Rationale:** Stats change slowly, can be updated weekly  
**Action:** Create helper function that caches results

### 3. Scoring Performance
**Decision:** Batch API with pagination, optional caching column  
**Rationale:** Can't score 228K properties at once  
**Action:** Limit batch size to 1000, add pagination

### 4. Missing Data Handling
**Decision:** Graceful defaults, don't penalize for missing data  
**Rationale:** Not all properties have all fields  
**Action:** Use sensible defaults (0 for areas, year_built if no renovation)

---

## File Structure After Implementation

```
src/
  scoring/
    __init__.py
    factors.py              # Individual scoring functions
    presets.py              # Preset weight configurations
    filters.py              # Base filter functions
    database_helpers.py     # DB query utilities
  scoring.py                # Main PropertyScorer class (rewritten)

webapp/
  app.py                    # Add scoring API endpoints
  templates/
    score_calculator.html   # Enhanced with backend integration
  static/
    js/
      score_calculator.js   # Frontend logic

scripts/
  analysis/                 # Phase 1 analysis scripts
    market_analysis.py
    feature_importance.py
  migrations/
    add_distance_to_copenhagen.py  # Migration for distance column

tests/
  test_scoring.py           # Unit tests
  test_scoring_comprehensive.py   # Integration tests

docs/
  SCORING_MODEL_IMPLEMENTATION_PLAN.md  # Detailed plan
  SCORING_QUICK_START.md                # Quick reference
  BIGGEST_TODO_FIX_PLAN.md              # This document
```

---

## Success Metrics

### Technical Metrics
- [ ] All 8+ scoring factors implemented and tested
- [ ] API endpoints return results in <2 seconds for 100 properties
- [ ] Unit test coverage >80%
- [ ] Handles edge cases gracefully (missing data, outliers)

### User Experience Metrics
- [ ] Score calculator page fully functional
- [ ] Users can select presets and see results
- [ ] Score breakdown is transparent and understandable
- [ ] Top-scored properties align with expectations

### Business Metrics (Future)
- [ ] 50%+ of visitors use score calculator
- [ ] Average session time increases 30%+
- [ ] User satisfaction ≥4.5/5

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing data in properties | High | Use defaults, skip factors gracefully |
| Performance with 228K properties | Medium | Batch processing, pagination, caching |
| Distance calculation overhead | Medium | Pre-calculate during import |
| Scoring feels inaccurate | High | Calibration with real data, user feedback |
| Complex implementation delays delivery | Medium | MVP first, iterate based on feedback |

---

## Dependencies

### Required Libraries
```python
geopy>=2.3.0  # Distance calculations (Haversine)
```

### Optional (for Phase 1 analysis)
```python
scipy>=1.10.0
matplotlib>=3.7.0
seaborn>=0.12.0
pandas>=2.0.0  # Should already be in requirements
```

### Database Requirements
- All existing tables and fields (✅ already available)
- May need: New column `distance_to_copenhagen` (migration)
- May need: Indexes on scoring-related fields (optimization)

---

## Next Steps

1. ✅ **Planning Complete** - Documentation created
2. ⏳ **Review & Approve** - Confirm approach and priorities
3. ⏳ **Start Implementation** - Begin with Phase 2 (Core Algorithm)
4. ⏳ **Iterate & Test** - Get MVP working, then refine
5. ⏳ **Deploy & Monitor** - Release and gather feedback

---

## Related Documents

- **Detailed Plan:** `docs/SCORING_MODEL_IMPLEMENTATION_PLAN.md` - Complete phase-by-phase breakdown
- **Quick Start:** `docs/SCORING_QUICK_START.md` - Quick reference and implementation checklist
- **Original TODO:** `archive/SCORING_MODEL_TODO.md` - Original requirements
- **Database Schema:** `docs/DATABASE_SCHEMA.md` - Available fields reference
- **Current Code:** `src/scoring.py` - Basic implementation to replace

---

## Conclusion

The Property Scoring Model is the biggest and most impactful TODO in the project. This plan provides:

✅ Clear identification of the biggest TODO  
✅ Comprehensive implementation strategy  
✅ Phase-by-phase breakdown with priorities  
✅ Risk mitigation strategies  
✅ Technical decision framework  
✅ Success metrics  

**Ready to begin implementation starting with Phase 2 (Core Scoring Algorithm).**
