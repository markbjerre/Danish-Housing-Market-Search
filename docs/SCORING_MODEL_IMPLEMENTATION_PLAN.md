# Property Scoring Model - Implementation Plan

**Created:** December 2024  
**Status:** Planning  
**Priority:** High  
**Estimated Time:** 20-25 days (basic version), ongoing for advanced features

---

## Executive Summary

This plan outlines how to implement the comprehensive property scoring model described in `SCORING_MODEL_TODO.md`. The scoring system will rank properties based on weighted factors representing value, quality, location, and potential, enabling users to find their ideal property based on customizable preferences.

### Current State
- ✅ Basic `scoring.py` exists with simple implementation
- ✅ Database has all required fields (120+ fields across 14 tables)
- ✅ Webapp has `/score-calculator` route (placeholder)
- ✅ Frontend preset buttons marked as done (needs backend integration)
- ❌ Full scoring algorithm not implemented
- ❌ API endpoints not implemented
- ❌ Preset profiles not implemented

### Target State
- Complete scoring algorithm with all factors from TODO
- API endpoints for scoring calculations
- Preset user profiles (Value Hunter, Luxury Seeker, etc.)
- Base filter parameters (Dream Home, Value Deal, Investment Opportunity)
- Frontend integration with visual breakdowns
- Validation and testing framework

---

## Phase-by-Phase Implementation Plan

### Phase 1: Research & Analysis ⏳
**Duration:** 2-3 days  
**Dependencies:** Database access

#### Tasks

**1.1 Market Analysis**
- [ ] Query database to analyze price per m² distribution across municipalities
  - SQL query: `SELECT municipality, AVG(latest_valuation/living_area) FROM properties_new JOIN municipalities GROUP BY municipality`
  - Export results to CSV for analysis
  - Create histogram/box plots per municipality
- [ ] Identify price outliers (good deals vs overpriced)
  - Calculate z-scores: `(price_per_sqm - mean) / std_dev`
  - Flag properties >2 std dev below mean as "good deals"
  - Flag properties >2 std dev above mean as "overpriced"
- [ ] Study correlation between renovation year and price
  - Join `main_buildings.year_renovated` with `properties_new.latest_valuation`
  - Calculate correlation coefficient
  - Visualize scatter plot (renovation year vs price per m²)
- [ ] Analyze energy label impact on pricing
  - Group by energy_label, calculate median price per m²
  - Compare A vs G labels
- [ ] Research basement area value contribution
  - Properties with basement vs without basement price comparison
  - Basement area correlation with total price
- [ ] Study plot size vs price correlation
  - Use `additional_buildings` or external plot size data if available
  - Calculate correlation if plot data exists

**Deliverables:**
- `scripts/analysis/market_analysis.py` - Analysis scripts
- `docs/analysis/market_insights.md` - Findings document
- CSV exports of analysis results

**Files to Create:**
```
scripts/
  analysis/
    market_analysis.py
    correlation_analysis.py
    export_analysis_results.py
docs/
  analysis/
    market_insights.md
data/
  analysis/
    price_per_sqm_by_municipality.csv
    renovation_correlation.csv
    energy_label_impact.csv
```

---

**1.2 Feature Importance**
- [ ] Calculate correlation matrix for all numeric features
  - Features: living_area, basement_area, number_of_rooms, number_of_bathrooms, year_built, year_renovated, energy_label (numeric), distance_to_copenhagen, municipality_tax, etc.
  - Use pandas correlation matrix
  - Visualize with heatmap
- [ ] Identify most impactful features on property value
  - Multiple linear regression: `price ~ living_area + basement_area + bathrooms + ...`
  - Extract feature coefficients (importance)
- [ ] Study feature combinations
  - Large basement + recent renovation → price premium?
  - Good energy label + close distance → higher value?
- [ ] Analyze geographic clustering patterns
  - Cluster by municipality + zip_code
  - Identify high-value vs low-value clusters

**Deliverables:**
- `scripts/analysis/feature_importance.py`
- Correlation matrix heatmap visualization
- Feature importance ranking

**Files to Create:**
```
scripts/
  analysis/
    feature_importance.py
    regression_analysis.py
docs/
  analysis/
    feature_importance_report.md
data/
  analysis/
    correlation_matrix.csv
    feature_importance_ranking.csv
```

---

**1.3 User Preferences Survey**
- [ ] Define target user personas
  - Families: Space, schools, plot size
  - Investors: Price per m², renovation potential
  - Retirees: Single floor, low maintenance
  - Young professionals: Location, price, modern
- [ ] Document persona characteristics
- [ ] Create initial weight suggestions per persona

**Deliverables:**
- `docs/user_personas.md`

---

### Phase 2: Scoring Algorithm Development 🎯
**Duration:** 3-5 days  
**Dependencies:** Phase 1 complete, analysis insights

#### Tasks

**2.1 Create Enhanced Scoring Module**

Replace the basic `src/scoring.py` with comprehensive implementation:

**Files to Modify:**
- `src/scoring.py` - Complete rewrite

**Files to Create:**
- `src/scoring/factors.py` - Individual scoring factor functions
- `src/scoring/normalization.py` - Normalization utilities
- `src/scoring/presets.py` - Preset weight configurations
- `src/scoring/filters.py` - Base filter implementations

**2.1.1 Normalize Features (0-10 scale)**

Implement each scoring factor:

**Price per m²** (Lower is better)
- [ ] Function: `calculate_price_score(property, municipality_stats)`
- [ ] Calculate municipality-specific benchmarks from Phase 1 analysis
- [ ] Formula: `score = 10 - ((price_per_sqm - min) / (max - min)) * 10`
- [ ] Add premium adjustment for luxury areas (Gentofte, Frederiksberg) - multiplier 1.2x

**Implementation:**
```python
# src/scoring/factors.py
def calculate_price_per_sqm_score(property, municipality_avg, municipality_min, municipality_max, is_luxury_area=False):
    price_per_sqm = property.latest_valuation / property.living_area
    normalized = 10 - ((price_per_sqm - municipality_min) / (municipality_max - municipality_min)) * 10
    if is_luxury_area:
        normalized *= 1.2  # Premium areas get bonus
    return max(0, min(10, normalized))
```

**Living Area** (Larger is better, with diminishing returns)
- [ ] Function: `calculate_living_area_score(area)`
- [ ] Small: 0-100 m² → linear 0-5 points
- [ ] Medium: 100-200 m² → linear 5-8 points
- [ ] Large: 200-300+ m² → logarithmic 8-10 points

**Distance to Copenhagen** (Closer is better)
- [ ] Function: `calculate_distance_score(lat, lon)`
- [ ] Calculate distance using Haversine formula
- [ ] Copenhagen center: lat 55.6761, lon 12.5683
- [ ] 0-10 km: 10 points
- [ ] 10-20 km: 8 points
- [ ] 20-30 km: 6 points
- [ ] 30-40 km: 4 points
- [ ] 40-60 km: 2 points

**Basement Area**
- [ ] Function: `calculate_basement_score(basement_area)`
- [ ] No basement: 0 points
- [ ] 50-100 m²: 3-5 points (linear)
- [ ] 100-150 m²: 5-7 points (linear)
- [ ] 150+ m²: 7-10 points (diminishing returns)

**Plot Size**
- [ ] Function: `calculate_plot_score(plot_size)` 
- [ ] Note: May need to derive from additional_buildings or external source
- [ ] 0-400 m²: 0-3 points
- [ ] 400-800 m²: 3-7 points
- [ ] 800-1200 m²: 7-9 points
- [ ] 1200+ m²: 9-10 points

**Bathrooms**
- [ ] Function: `calculate_bathroom_score(num_bathrooms)`
- [ ] 1 bathroom: 0 points
- [ ] 2 bathrooms: 5 points
- [ ] 3 bathrooms: 8 points
- [ ] 4+ bathrooms: 10 points

**Renovation Year** (More recent is better)
- [ ] Function: `calculate_renovation_score(year_renovated)`
- [ ] Use `main_buildings.year_renovated` or `main_buildings.year_built` if no renovation
- [ ] Not renovated: 0 points
- [ ] Before 2000: 2 points
- [ ] 2000-2010: 4 points
- [ ] 2010-2015: 6 points
- [ ] 2015-2020: 8 points
- [ ] 2020+: 10 points

**Energy Label**
- [ ] Function: `calculate_energy_label_score(energy_label)`
- [ ] A: 10 points, B: 8, C: 6, D: 4, E: 2, F/G: 0

**Additional Factors** (Phase 2 stretch goals)
- [ ] Number of rooms score
- [ ] Number of floors score (2 floors optimal)
- [ ] Year built (historical value vs modern)
- [ ] External wall material (brick > concrete > wood)
- [ ] Heating type (district > heat pump > oil)
- [ ] Roof material (tile > metal > tarpaper)
- [ ] Municipality tax rates (lower is better)
- [ ] School availability (from municipalities.number_of_schools)
- [ ] Days on market (from cases table)

**2.1.2 Weighted Scoring Formula**

Implement main scoring class:

```python
# src/scoring.py
class PropertyScorer:
    def __init__(self, weights=None, preset=None):
        if preset:
            self.weights = PRESETS[preset]
        else:
            self.weights = weights or DEFAULT_WEIGHTS
    
    def score_property(self, property, municipality_stats, distance_to_cph):
        # Calculate all factor scores
        scores = {
            'price_per_sqm': calculate_price_per_sqm_score(...),
            'living_area': calculate_living_area_score(...),
            'distance': calculate_distance_score(...),
            'basement': calculate_basement_score(...),
            'plot': calculate_plot_score(...),
            'bathrooms': calculate_bathroom_score(...),
            'renovation': calculate_renovation_score(...),
            'energy': calculate_energy_label_score(...),
        }
        
        # Weighted average
        weighted_sum = sum(scores[k] * self.weights[k] for k in scores)
        total_weight = sum(self.weights.values())
        
        return {
            'final_score': (weighted_sum / total_weight) * 10,  # 0-100 scale
            'factor_scores': scores,
            'weights': self.weights
        }
```

**Default Weights:**
```python
DEFAULT_WEIGHTS = {
    'price_per_sqm': 5,
    'living_area': 5,
    'distance': 5,
    'basement_area': 3,
    'plot_size': 4,
    'bathrooms': 4,
    'renovation_year': 4,
    'energy_label': 3,
}
```

**2.1.3 Preset Profiles**

Create `src/scoring/presets.py`:

```python
PRESETS = {
    'value_hunter': {
        'price_per_sqm': 10,
        'living_area': 6,
        'distance': 3,
        'energy': 5,
        'basement_area': 2,
        'plot_size': 2,
        'bathrooms': 2,
        'renovation_year': 3,
    },
    'luxury_seeker': {...},
    'location_first': {...},
    'family_oriented': {...},
    'eco_conscious': {...},
}
```

**Deliverables:**
- Complete `src/scoring.py` implementation
- All factor calculation functions
- Preset configurations
- Unit tests for each factor

**Files Structure:**
```
src/
  scoring/
    __init__.py
    factors.py          # Individual scoring factors
    normalization.py    # Normalization utilities
    presets.py          # Preset weight configurations
    filters.py          # Base filter implementations
  scoring.py            # Main PropertyScorer class
tests/
  test_scoring.py       # Unit tests
```

---

### Phase 3: Base Filter Parameters 🔍
**Duration:** 1-2 days  
**Dependencies:** Phase 2 complete

#### Tasks

**3.1 Implement Filter Functions**

Create `src/scoring/filters.py`:

**3.1.1 "Dream Home" Filters**
- [ ] Function: `filter_dream_home(properties)`
- [ ] Living Area: ≥ 150 m²
- [ ] Bathrooms: ≥ 2
- [ ] Energy Label: C or better
- [ ] Distance to Copenhagen: ≤ 30 km
- [ ] Price per m²: ≤ municipality average × 1.2
- [ ] Renovation: After 2010 OR Year Built after 2005

**3.1.2 "Value Deal" Filters**
- [ ] Function: `filter_value_deals(properties, municipality_stats)`
- [ ] Price per m²: < municipality average × 0.85
- [ ] Living Area: ≥ 100 m²
- [ ] Not on market > 180 days (from cases)
- [ ] At least 1 recent registration (within 10 years)

**3.1.3 "Investment Opportunity" Filters**
- [ ] Function: `filter_investment_opportunities(properties, municipality_stats)`
- [ ] Price per m²: < municipality average × 0.80
- [ ] Living Area: ≥ 120 m²
- [ ] Renovation year: Before 2015 (room for value-add)
- [ ] Energy Label: D or worse (potential for upgrade)
- [ ] Distance: ≤ 40 km

**Deliverables:**
- `src/scoring/filters.py` with all three filter functions
- Tests for each filter

---

### Phase 4: Implementation 💻
**Duration:** 5-7 days  
**Dependencies:** Phase 2 & 3 complete

#### Tasks

**4.1 Backend API Endpoints**

Modify `webapp/app.py` to add scoring endpoints:

**4.1.1 `/api/score` - Calculate score for single property**
- [ ] Endpoint: `@app.route('/api/score', methods=['POST'])`
- [ ] Input: `{property_id, weights?, preset?}`
- [ ] Output: `{final_score, factor_scores, weights_used}`
- [ ] Fetch property from database with all relationships
- [ ] Calculate municipality statistics
- [ ] Calculate distance to Copenhagen
- [ ] Call PropertyScorer.score_property()
- [ ] Return JSON response

**4.1.2 `/api/score/batch` - Calculate scores for multiple properties**
- [ ] Endpoint: `@app.route('/api/score/batch', methods=['POST'])`
- [ ] Input: `{property_ids: [...], weights?, preset?}`
- [ ] Batch fetch properties
- [ ] Pre-calculate municipality stats once
- [ ] Parallelize scoring calculations
- [ ] Return sorted list by score (descending)
- [ ] Include pagination support

**4.1.3 `/api/score/presets` - Return preset weight configurations**
- [ ] Endpoint: `@app.route('/api/score/presets', methods=['GET'])`
- [ ] Return all preset configurations
- [ ] Include descriptions for each preset

**4.1.4 `/api/score/filters` - Apply base filters before scoring**
- [ ] Endpoint: `@app.route('/api/score/filters', methods=['POST'])`
- [ ] Input: `{filter_type: 'dream_home'|'value_deal'|'investment', weights?, preset?}`
- [ ] Apply filter function
- [ ] Score filtered properties
- [ ] Return results

**4.1.5 Database Helper Functions**

Create `src/scoring/database_helpers.py`:
- [ ] `get_property_with_relations(property_id)` - Fetch property with all related data
- [ ] `get_municipality_stats(municipality_name)` - Calculate avg/min/max price per m²
- [ ] `calculate_distance_to_copenhagen(lat, lon)` - Haversine distance calculation
- [ ] `get_properties_batch(property_ids)` - Batch fetch with eager loading

**4.2 Frontend Features**

Modify `webapp/templates/score_calculator.html`:

- [ ] Visual score breakdown charts (bar chart showing factor scores)
- [ ] Compare mode (2-3 properties side-by-side) - NEW FEATURE
- [ ] Save custom weight profiles to localStorage
- [ ] Export scored property list to CSV

**Files to Modify:**
- `webapp/app.py` - Add API endpoints
- `webapp/templates/score_calculator.html` - Enhance UI
- Create `webapp/static/js/score_calculator.js` for frontend logic

**4.3 Database Optimizations**

- [ ] Add optional computed score column to `properties_new` table (for caching)
  - Migration: `ALTER TABLE properties_new ADD COLUMN cached_score FLOAT;`
  - Create index: `CREATE INDEX idx_cached_score ON properties_new(cached_score);`
- [ ] Create indexes on frequently filtered fields
  - `CREATE INDEX idx_energy_label ON properties_new(energy_label);`
  - `CREATE INDEX idx_living_area ON properties_new(living_area);`
  - `CREATE INDEX idx_is_on_market ON properties_new(is_on_market);`
- [ ] Create table for user-saved scoring profiles (optional, future)
  - Table: `user_scoring_profiles(id, user_id, name, weights_json)`

**Deliverables:**
- Complete API endpoints
- Enhanced frontend
- Database optimizations
- API documentation

**Files Structure:**
```
webapp/
  app.py                      # Add scoring endpoints
  templates/
    score_calculator.html     # Enhanced UI
  static/
    js/
      score_calculator.js     # Frontend logic
src/
  scoring/
    database_helpers.py       # DB query helpers
scripts/
  migrations/
    add_score_caching.py      # Optional migration
```

---

### Phase 5: Validation & Tuning 🧪
**Duration:** 2-3 days  
**Dependencies:** Phase 4 complete

#### Tasks

**5.1 Testing**

- [ ] Create `tests/test_scoring_comprehensive.py`
- [ ] Test with 1000 random properties from database
- [ ] Verify score distribution (should be roughly bell curve)
- [ ] Check for edge cases:
  - Missing data (NULL values)
  - Outliers (extremely high/low prices)
  - Properties without main_building data
  - Properties without municipality data
- [ ] Validate against expert opinions (if available)
  - Compare top 10 scored properties with manual assessment

**5.2 Calibration**

- [ ] Adjust weight ranges if scores cluster too tightly
- [ ] Fine-tune normalization functions based on real data distribution
- [ ] Adjust preset weights based on Phase 1 analysis insights
- [ ] Ensure scoring feels intuitive (high scores = desirable properties)

**5.3 A/B Testing Framework**

- [ ] Create script to test different preset configurations
- [ ] Gather sample user feedback (if possible)
- [ ] Document iteration process

**Deliverables:**
- Comprehensive test suite
- Calibration report
- Test results documentation

---

### Phase 6: Advanced Features 🚀
**Duration:** 10+ days (ongoing)  
**Dependencies:** Phase 5 complete

#### Tasks

**6.1 Machine Learning Integration**
- [ ] Train ML model on historical sale prices (registrations table)
- [ ] Predict fair market value based on features
- [ ] Compare ML predictions with manual scoring
- [ ] Hybrid approach: ML + weighted scoring

**6.2 Neighborhood Analytics**
- [ ] Calculate neighborhood desirability scores
- [ ] Factor in crime rates, schools, amenities (external data)
- [ ] Add public transit accessibility score
- [ ] Include walkability metrics

**6.3 Market Trends**
- [ ] Track price per m² trends over time (using registrations)
- [ ] Identify "hot" vs "cold" neighborhoods
- [ ] Predict price appreciation potential
- [ ] Alert users to newly listed properties matching their profile

**Note:** Phase 6 is for future enhancement. Focus on Phases 1-5 first.

---

## Implementation Order & Priority

### Must-Have (MVP)
1. ✅ Phase 2.1: Core scoring factors (price, area, distance, basement, bathrooms, renovation, energy)
2. ✅ Phase 2.2: Weighted scoring formula
3. ✅ Phase 2.3: Preset profiles
4. ✅ Phase 4.1: Basic API endpoints (`/api/score`, `/api/score/batch`, `/api/score/presets`)
5. ✅ Phase 4.2: Frontend integration (existing route, connect to backend)

### Should-Have
6. Phase 3: Base filter parameters
7. Phase 4.1: Filter endpoints
8. Phase 5: Validation & testing

### Nice-to-Have
9. Phase 1: Comprehensive analysis (can be done in parallel)
10. Phase 4.3: Database caching
11. Phase 6: Advanced features

---

## Technical Requirements

### Dependencies to Add
```python
# requirements.txt additions
geopy>=2.3.0  # For distance calculations (Haversine)
scipy>=1.10.0  # For statistical analysis (optional, Phase 1)
matplotlib>=3.7.0  # For visualizations (Phase 1)
seaborn>=0.12.0  # For correlation heatmaps (Phase 1)
```

### Database Queries Needed

**Municipality Statistics:**
```sql
SELECT 
    m.name,
    AVG(p.latest_valuation / NULLIF(p.living_area, 0)) as avg_price_per_sqm,
    MIN(p.latest_valuation / NULLIF(p.living_area, 0)) as min_price_per_sqm,
    MAX(p.latest_valuation / NULLIF(p.living_area, 0)) as max_price_per_sqm,
    COUNT(*) as property_count
FROM properties_new p
JOIN municipalities m ON p.id = m.property_id
WHERE p.living_area > 0 AND p.latest_valuation > 0
GROUP BY m.name;
```

**Property with All Relations:**
```sql
SELECT p.*, mb.*, m.*, c.*
FROM properties_new p
LEFT JOIN main_buildings mb ON p.id = mb.property_id
LEFT JOIN municipalities m ON p.id = m.property_id
LEFT JOIN cases c ON p.id = c.property_id
WHERE p.id = ?
```

---

## Success Metrics

- [ ] 80%+ of top-scored properties align with user expectations
- [ ] Score calculator used by 50%+ of site visitors
- [ ] Average session time increases by 30%+
- [ ] User satisfaction rating ≥ 4.5/5 for scoring feature (when available)

---

## Risks & Mitigations

### Risk 1: Missing Data
**Issue:** Some properties may lack basement_area, plot_size, renovation_year  
**Mitigation:** Use sensible defaults (0 for missing areas, year_built if no renovation_year)

### Risk 2: Performance with Large Datasets
**Issue:** Scoring 228K+ properties may be slow  
**Mitigation:** 
- Implement caching (Phase 4.3)
- Use batch processing with pagination
- Consider background job queue for full database scoring

### Risk 3: Distance Calculation Overhead
**Issue:** Haversine calculation for every property  
**Mitigation:**
- Pre-calculate distance to Copenhagen during import
- Add `distance_to_copenhagen` column to `properties_new` table
- Update on property insert/update

---

## Next Steps

1. **Immediate:** Start with Phase 2 (Scoring Algorithm) - this is the core functionality
2. **Parallel:** Run Phase 1 analysis scripts to gather insights
3. **Follow-up:** Implement Phase 4 API endpoints to expose scoring
4. **Integration:** Connect frontend to backend APIs
5. **Validation:** Phase 5 testing before production

---

## Notes

- Start with simple linear scoring, iterate to logarithmic/exponential if needed
- Keep scoring transparent - users should understand why a property scores high/low
- Allow full customization - users know their priorities best
- Monitor for gaming/manipulation of scores
- Consider adding "hidden gem" algorithm for undervalued properties
