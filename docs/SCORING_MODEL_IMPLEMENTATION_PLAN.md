# Property Scoring Model - Implementation Plan

**Created:** 2025-11-01  
**Status:** Planning  
**Priority:** HIGH  
**Estimated Duration:** 20-25 days for MVP

---

## Executive Summary

The Property Scoring Model is the biggest outstanding TODO in the project. It will transform the housing analysis system from a simple data browser into an intelligent property recommendation engine. This document provides a concrete, actionable plan to implement the scoring system in phases.

**Why This is the Biggest TODO:**
- Most complex feature (6 phases, 100+ sub-tasks)
- Longest timeline (20-25 days estimated)
- Highest user value (intelligent property rankings)
- Foundation for future ML/AI features
- Currently 0% complete

---

## Current State Assessment

### ✅ What We Have
- **228,594 properties** with comprehensive data
- **14 normalized database tables** with 120+ fields
- **100% price coverage** for active listings (3,623 cases)
- **Geographic data** (36 municipalities, distances calculated)
- **Historical data** (388,113 transactions)
- **Web interface** (Flask app with basic search)

### ❌ What We're Missing
- No intelligent property ranking system
- No personalized recommendations
- No "value deal" or "dream home" filters
- No way to compare properties objectively
- Users must manually evaluate each property

---

## Implementation Strategy

### Phase 1: Research & Data Analysis (Days 1-3)

**Goal:** Understand our data and establish scoring benchmarks

#### 1.1 Create Analysis Script (`scripts/analyze_scoring_factors.py`)
```python
# Analyze price per m² by municipality
# Calculate feature correlations
# Identify outliers and data quality issues
# Generate normalization ranges for each feature
```

**Key Analyses:**
- [ ] Price per m² distribution (min, max, mean, median) per municipality
- [ ] Living area distribution and optimal ranges
- [ ] Distance from Copenhagen impact on pricing
- [ ] Correlation matrix for all numeric features
- [ ] Energy label frequency and price impact
- [ ] Renovation year vs price correlation
- [ ] Identify top 10 most important features

**Deliverables:**
- `data/scoring_analysis_report.json` - Statistical benchmarks
- `docs/SCORING_DATA_ANALYSIS.md` - Human-readable insights
- Decision on which features to include in MVP

---

### Phase 2: Core Scoring Algorithm (Days 4-8)

**Goal:** Build the mathematical foundation for property scoring

#### 2.1 Create Scoring Module (`src/scoring.py`)

**Core Components:**

1. **Feature Normalizers** (0-10 scale)
```python
def normalize_price_per_sqm(price_per_sqm, municipality_avg, municipality_stddev):
    """Lower is better, with municipality-specific context"""
    pass

def normalize_living_area(area_sqm):
    """Larger is better with diminishing returns"""
    pass

def normalize_distance_to_copenhagen(distance_km):
    """Closer is better"""
    pass

def normalize_energy_label(label):
    """A=10, B=8, C=6, D=4, E=2, F/G=0"""
    pass

# Add 5+ more normalizers...
```

2. **Weighted Scoring Engine**
```python
class PropertyScorer:
    def __init__(self, weights=None):
        self.weights = weights or self.get_default_weights()
    
    def score_property(self, property_data):
        """Calculate final score (0-100) for a single property"""
        pass
    
    def score_batch(self, properties):
        """Efficiently score multiple properties"""
        pass
    
    def get_score_breakdown(self, property_data):
        """Return score + breakdown by feature"""
        pass
```

3. **Preset Weight Profiles**
```python
PRESETS = {
    'balanced': {...},
    'value_hunter': {...},
    'luxury_seeker': {...},
    'location_first': {...},
    'family_oriented': {...},
    'eco_conscious': {...}
}
```

**Deliverables:**
- `src/scoring.py` - Complete scoring module
- Unit tests in `tests/test_scoring.py`
- Documentation with examples

---

### Phase 3: Database Integration (Days 9-11)

**Goal:** Enable efficient scoring queries at scale

#### 3.1 Database Enhancements

1. **Add Computed Fields** (optional caching)
```sql
ALTER TABLE properties_new ADD COLUMN cached_score_balanced NUMERIC(5,2);
ALTER TABLE properties_new ADD COLUMN cached_score_timestamp TIMESTAMP;
```

2. **Create Scoring Views**
```sql
CREATE VIEW properties_for_scoring AS
SELECT 
    p.property_id,
    p.living_area,
    p.plot_size,
    p.year_built,
    p.year_renovated,
    p.energy_label,
    c.current_price,
    c.days_on_market,
    m.name as municipality,
    -- Calculate distance to Copenhagen
    -- Add all fields needed for scoring
FROM properties_new p
LEFT JOIN cases c ON p.property_id = c.property_id
LEFT JOIN municipalities m ON p.municipality_id = m.municipality_id;
```

3. **Optimize Indexes**
```sql
CREATE INDEX idx_properties_score_fields ON properties_new(living_area, plot_size, energy_label);
CREATE INDEX idx_cases_price ON cases(current_price, days_on_market);
```

#### 3.2 Create Scoring Service (`src/scoring_service.py`)
```python
class ScoringService:
    """High-level service for scoring properties with DB integration"""
    
    def score_property_by_id(self, property_id, weights=None):
        """Score a single property by ID"""
        pass
    
    def score_all_active_listings(self, weights=None):
        """Score all 3,623 active listings"""
        pass
    
    def get_top_properties(self, limit=100, weights=None, filters=None):
        """Get highest-scored properties with optional filters"""
        pass
    
    def update_cached_scores(self):
        """Recalculate and cache scores for all properties"""
        pass
```

**Deliverables:**
- Database migration script
- `src/scoring_service.py`
- Performance benchmarks (score 3,623 properties in < 5 seconds)

---

### Phase 4: REST API Endpoints (Days 12-14)

**Goal:** Expose scoring functionality via HTTP API

#### 4.1 API Routes (`webapp/app.py` or new `webapp/api_scoring.py`)

```python
@app.route('/api/score/property/<property_id>', methods=['GET', 'POST'])
def score_single_property(property_id):
    """
    GET: Use default balanced weights
    POST: Accept custom weights in JSON body
    
    Response: {
        "property_id": "...",
        "total_score": 82.5,
        "breakdown": {
            "price_per_sqm": {"score": 8.2, "weight": 5},
            "living_area": {"score": 7.5, "weight": 5},
            ...
        },
        "ranking": "Top 15% in municipality"
    }
    """
    pass

@app.route('/api/score/batch', methods=['POST'])
def score_batch_properties():
    """
    Score multiple properties at once
    POST body: {
        "property_ids": [...],
        "weights": {...}
    }
    """
    pass

@app.route('/api/score/presets', methods=['GET'])
def get_presets():
    """Return all available weight presets"""
    return jsonify(PRESETS)

@app.route('/api/score/top', methods=['GET', 'POST'])
def get_top_scored_properties():
    """
    Get top N properties by score
    Query params: ?limit=100&preset=value_hunter
    POST body: Custom weights + filters
    """
    pass

@app.route('/api/score/filters', methods=['GET'])
def get_available_filters():
    """Return metadata about available filters"""
    pass
```

**Deliverables:**
- 5 new API endpoints
- API documentation (OpenAPI/Swagger)
- Integration tests

---

### Phase 5: Frontend Interface (Days 15-19)

**Goal:** Build user-friendly scoring interface

#### 5.1 New Pages/Components

1. **Score Calculator Page** (`/score-calculator`)
   - [ ] Weight sliders for all 8+ features
   - [ ] Preset buttons (6 profiles)
   - [ ] Real-time score preview
   - [ ] Save custom profiles (localStorage)
   - [ ] Reset to defaults button

2. **Enhanced Property List** (`/browse`)
   - [ ] Add "Score" column to property table
   - [ ] Sort by score (default view)
   - [ ] Filter by minimum score
   - [ ] Show score badge with color coding:
     - 🟢 Green: 80-100 (Excellent)
     - 🟡 Yellow: 60-79 (Good)
     - 🟠 Orange: 40-59 (Fair)
     - 🔴 Red: 0-39 (Poor)

3. **Property Detail Page** (`/property/<id>`)
   - [ ] Score breakdown radar chart
   - [ ] Score comparison to similar properties
   - [ ] Feature-by-feature explanation
   - [ ] "What if" calculator (adjust features to see score impact)

4. **Compare Properties Page** (`/compare`)
   - [ ] Side-by-side comparison of 2-3 properties
   - [ ] Visual score breakdown comparison
   - [ ] Highlight strengths/weaknesses
   - [ ] Export comparison to PDF

5. **Top Picks Page** (`/top-picks`)
   - [ ] Preset-based filtered lists
   - [ ] "Value Deals" - Best price per m²
   - [ ] "Dream Homes" - High-quality properties
   - [ ] "Investment Opportunities" - Renovation potential
   - [ ] Saved searches with custom weights

#### 5.2 UI/UX Enhancements
```html
<!-- Score Badge Component -->
<div class="score-badge score-excellent">
    <span class="score-value">87.5</span>
    <span class="score-label">Excellent Match</span>
</div>

<!-- Weight Slider Component -->
<div class="weight-slider">
    <label>Price per m²</label>
    <input type="range" min="0" max="10" value="5" />
    <span class="weight-value">5/10</span>
</div>
```

**Deliverables:**
- 5 new frontend pages
- Reusable React/Vue components (if using frameworks)
- Responsive design (mobile-friendly)
- CSS styling and animations

---

### Phase 6: Testing & Validation (Days 20-22)

**Goal:** Ensure accuracy and reliability

#### 6.1 Statistical Validation
- [ ] Test with 1,000 random properties
- [ ] Verify score distribution (should be bell curve-ish)
- [ ] Check for edge cases (missing data, extreme values)
- [ ] Validate against manual expert ratings (if available)

#### 6.2 User Acceptance Testing
- [ ] Test all 6 presets with real users
- [ ] Gather feedback on score "reasonableness"
- [ ] A/B test different weight configurations
- [ ] Iterate based on feedback

#### 6.3 Performance Testing
- [ ] Benchmark scoring speed (target: 1000 props/sec)
- [ ] Test API response times under load
- [ ] Optimize database queries if needed
- [ ] Add caching layer if necessary

#### 6.4 Documentation
- [ ] User guide: "How Property Scoring Works"
- [ ] Developer guide: "Extending the Scoring System"
- [ ] FAQ: Common questions about scores
- [ ] Changelog: Track weight adjustments over time

**Deliverables:**
- Test suite with 100+ test cases
- Performance benchmark report
- User documentation
- Developer documentation

---

## Technical Architecture

### Component Diagram
```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Flask)                     │
│  /score-calculator  /browse  /property/<id>  /compare   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTP/JSON
                     │
┌────────────────────▼────────────────────────────────────┐
│                   API Layer (Flask)                      │
│  /api/score/*   /api/score/batch   /api/score/presets  │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Python calls
                     │
┌────────────────────▼────────────────────────────────────┐
│              Scoring Service (scoring_service.py)        │
│  - Fetch property data from DB                          │
│  - Call scoring engine                                   │
│  - Cache results                                         │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
┌────────▼──────────┐   ┌───────▼──────────┐
│ Scoring Engine    │   │   Database       │
│ (scoring.py)      │   │   (PostgreSQL)   │
│ - Normalizers     │   │ - Properties     │
│ - Weight calc     │   │ - Cases          │
│ - Presets         │   │ - Municipalities │
└───────────────────┘   └──────────────────┘
```

### Data Flow
1. User adjusts weights in UI
2. Frontend sends POST to `/api/score/batch` with property IDs + weights
3. API calls `ScoringService.score_properties(ids, weights)`
4. Service fetches property data from DB
5. Service calls `PropertyScorer.score_batch(properties, weights)`
6. Scorer normalizes each feature (0-10 scale)
7. Scorer applies weights and calculates final score
8. API returns JSON with scores + breakdowns
9. Frontend updates UI with colored badges and charts

---

## Risk Mitigation

### Risk 1: Scores Don't "Feel Right" to Users
**Mitigation:**
- Start with simple, transparent algorithm
- Allow full customization via weight sliders
- Provide clear explanations for each score
- Iterate based on user feedback
- A/B test different weight configurations

### Risk 2: Performance Issues with Large Dataset
**Mitigation:**
- Use database views for efficient queries
- Implement caching layer (Redis or in-DB)
- Batch processing for bulk operations
- Pre-compute scores for active listings nightly
- Lazy loading for on-demand scoring

### Risk 3: Missing/Incomplete Data
**Mitigation:**
- Handle NULL values gracefully (use defaults)
- Show data completeness percentage in UI
- Adjust weights automatically for missing features
- Document impact of missing data on scores

### Risk 4: Scoring Criteria Change Over Time
**Mitigation:**
- Make weights easily configurable (JSON files)
- Version scoring algorithms (v1, v2, etc.)
- Log all weight changes with dates
- Allow users to "freeze" a scoring profile

---

## Success Metrics

### Quantitative Metrics
- [ ] **Adoption:** 60%+ of users interact with scoring features
- [ ] **Performance:** Score 1000 properties in < 2 seconds
- [ ] **Accuracy:** Top 20% scored properties align with user expectations (survey)
- [ ] **Engagement:** 30%+ increase in time spent on site
- [ ] **Retention:** 20%+ increase in return visits

### Qualitative Metrics
- [ ] User feedback rating ≥ 4.5/5 stars
- [ ] Positive user testimonials about score usefulness
- [ ] Reduced support questions about "which property to choose"
- [ ] Increased trust in recommendations

---

## MVP vs Full Version

### MVP (Days 1-22) - Ship This First
- ✅ 8 core features (price, area, distance, basement, plot, bathrooms, renovation, energy)
- ✅ 5 preset profiles
- ✅ Basic weight customization
- ✅ Score display on property list
- ✅ Simple score breakdown
- ✅ REST API endpoints

### Future Enhancements (Days 23+)
- 🔮 Machine learning predictions
- 🔮 Neighborhood desirability scores
- 🔮 School quality integration
- 🔮 Crime rate analysis
- 🔮 Public transit accessibility
- 🔮 Market trend predictions
- 🔮 Price appreciation forecasts
- 🔮 Collaborative filtering (users who liked X also liked Y)

---

## Resource Requirements

### Development
- **Time:** 20-22 days for MVP
- **Skills:** Python, SQL, Flask, JavaScript, HTML/CSS
- **Tools:** PostgreSQL, SQLAlchemy, pandas, matplotlib (for analysis)

### Infrastructure
- **Database:** Add ~5 MB for cached scores (negligible)
- **CPU:** Scoring is compute-light (~0.1ms per property)
- **Memory:** Can score 10,000 properties in < 100 MB RAM

### Testing
- **Data:** Use existing 228,594 properties
- **Users:** 5-10 beta testers for initial feedback
- **Time:** 3 days for validation and iteration

---

## Implementation Checklist

### Week 1: Foundation
- [ ] Day 1: Analyze data distributions, create benchmarks
- [ ] Day 2: Build feature normalizers (8 core features)
- [ ] Day 3: Create weighted scoring engine
- [ ] Day 4: Write unit tests for all normalizers
- [ ] Day 5: Test scoring on 1000 sample properties

### Week 2: Integration
- [ ] Day 6: Create database migration for caching
- [ ] Day 7: Build ScoringService class
- [ ] Day 8: Optimize database queries and indexes
- [ ] Day 9: Create API endpoints (/api/score/*)
- [ ] Day 10: Write API tests and documentation

### Week 3: User Interface
- [ ] Day 11: Build score calculator page
- [ ] Day 12: Add score column to property list
- [ ] Day 13: Create property detail score breakdown
- [ ] Day 14: Build comparison page (side-by-side)
- [ ] Day 15: Create "Top Picks" preset pages

### Week 4: Polish & Launch
- [ ] Day 16: CSS styling and responsive design
- [ ] Day 17: Statistical validation (1000 properties)
- [ ] Day 18: User acceptance testing (beta)
- [ ] Day 19: Fix bugs and iterate on feedback
- [ ] Day 20: Write user documentation
- [ ] Day 21: Write developer documentation
- [ ] Day 22: Deploy to production 🚀

---

## Next Steps

### Immediate Actions (Today)
1. **Review and approve this plan** with stakeholders
2. **Set up development branch:** `git checkout -b feature/property-scoring`
3. **Create initial files:**
   - `scripts/analyze_scoring_factors.py`
   - `src/scoring.py`
   - `tests/test_scoring.py`

### Start with Quick Win (Day 1)
- Run data analysis on existing properties
- Generate `data/scoring_benchmarks.json`
- Validate that we have sufficient data quality for scoring

### Week 1 Goal
- Complete Phase 1 & 2 (Research + Core Algorithm)
- Have a working scoring engine that can score any property
- Demonstrate scoring on 100 sample properties

---

## Conclusion

The Property Scoring Model is indeed the biggest TODO in this project, but it's also the most valuable feature we can build. This plan provides a concrete, step-by-step roadmap to implement it in 20-22 days.

**Key Success Factors:**
1. Start with thorough data analysis (don't guess at weights)
2. Build modular, testable code (easy to iterate)
3. Ship MVP quickly, then iterate based on feedback
4. Focus on user experience (transparent, customizable, fast)
5. Document everything (for future maintenance)

**Ready to start?** Begin with Phase 1 data analysis tomorrow morning. 🚀

---

**Document Status:** Ready for implementation  
**Next Review:** After Phase 1 completion  
**Owner:** Development team  
**Last Updated:** 2025-11-01
