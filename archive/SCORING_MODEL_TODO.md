# Property Scoring Model - Development TODO

**Created:** October 5, 2025  
**Status:** Planning Phase  
**Priority:** Medium

---

## Overview

Develop a comprehensive scoring algorithm to rank properties based on weighted factors that represent value, quality, location, and potential.

---

## Phase 1: Research & Analysis ⏳

### 1.1 Market Analysis
- [ ] Analyze price per m² distribution across municipalities
- [ ] Identify price outliers (good deals vs overpriced)
- [ ] Study correlation between renovation year and price
- [ ] Analyze energy label impact on pricing
- [ ] Research basement area value contribution
- [ ] Study plot size vs price correlation

### 1.2 Feature Importance
- [ ] Calculate correlation matrix for all numeric features
- [ ] Identify most impactful features on property value
- [ ] Study feature combinations (e.g., large basement + recent renovation)
- [ ] Analyze geographic clustering patterns

### 1.3 User Preferences Survey
- [ ] Define target user personas (families, investors, retirees, etc.)
- [ ] Determine importance weights for each persona
- [ ] Create preset profiles for each persona type

---

## Phase 2: Scoring Algorithm Development 🎯

### 2.1 Normalize Features (0-10 scale)

**Price per m²** (Lower is better)
- [ ] Calculate municipality-specific benchmarks
- [ ] Define formula: `score = 10 - ((price_per_sqm - min) / (max - min)) * 10`
- [ ] Add premium adjustment for luxury areas (Gentofte, Frederiksberg)

**Living Area** (Larger is better, with diminishing returns)
- [ ] Small: 0-100 m² (linear 0-5 points)
- [ ] Medium: 100-200 m² (linear 5-8 points)
- [ ] Large: 200-300+ m² (logarithmic 8-10 points)

**Distance to Copenhagen** (Closer is better)
- [ ] 0-10 km: 10 points (city center)
- [ ] 10-20 km: 8 points (inner suburbs)
- [ ] 20-30 km: 6 points (middle suburbs)
- [ ] 30-40 km: 4 points (outer suburbs)
- [ ] 40-60 km: 2 points (distant)

**Basement Area**
- [ ] No basement: 0 points
- [ ] 50-100 m²: 3-5 points
- [ ] 100-150 m²: 5-7 points
- [ ] 150+ m²: 7-10 points

**Plot Size**
- [ ] 0-400 m²: 0-3 points (small)
- [ ] 400-800 m²: 3-7 points (medium)
- [ ] 800-1200 m²: 7-9 points (large)
- [ ] 1200+ m²: 9-10 points (very large)

**Bathrooms**
- [ ] 1 bathroom: 0 points
- [ ] 2 bathrooms: 5 points
- [ ] 3 bathrooms: 8 points
- [ ] 4+ bathrooms: 10 points

**Renovation Year** (More recent is better)
- [ ] Not renovated: 0 points
- [ ] Before 2000: 2 points
- [ ] 2000-2010: 4 points
- [ ] 2010-2015: 6 points
- [ ] 2015-2020: 8 points
- [ ] 2020+: 10 points

**Energy Label**
- [ ] A: 10 points
- [ ] B: 8 points
- [ ] C: 6 points
- [ ] D: 4 points
- [ ] E: 2 points
- [ ] F/G: 0 points

**Additional Factors to Consider:**
- [ ] Number of rooms (more is better, but watch for odd layouts)
- [ ] Number of floors (2 floors often preferred over 1 or 3+)
- [ ] Year built (historical value vs modern construction)
- [ ] External wall material (brick > concrete > wood)
- [ ] Heating type (district heating > heat pump > oil)
- [ ] Roof material (tile > metal > tarpaper)
- [ ] Municipality tax rates (lower is better)
- [ ] School availability (more schools = family-friendly)
- [ ] Days on market (longer = more negotiation potential)

### 2.2 Weighted Scoring Formula

**Base Formula:**
```
Final Score = Σ(Feature_Score_i × Weight_i) / Σ(Weight_i) × 100
```

**Default Weights (Balanced Profile):**
- Price per m²: 5/10
- Living Area: 5/10
- Distance to Copenhagen: 5/10
- Basement Area: 3/10
- Plot Size: 4/10
- Bathrooms: 4/10
- Renovation Year: 4/10
- Energy Label: 3/10

**Preset Profiles:**

1. **Value Hunter** (Focus: Best deal)
   - Price per m²: 10/10 ⭐
   - Area: 6/10
   - Distance: 3/10
   - Energy: 5/10
   - Others: 2-3/10

2. **Luxury Seeker** (Focus: Premium features)
   - Price per m²: 2/10
   - Area: 9/10 ⭐
   - Bathrooms: 9/10 ⭐
   - Basement: 7/10
   - Plot: 8/10
   - Renovation: 8/10 ⭐
   - Distance: 8/10

3. **Location First** (Focus: Proximity to city)
   - Distance: 10/10 ⭐
   - Price per m²: 4/10
   - Area: 5/10
   - Bathrooms: 5/10
   - Renovation: 5/10
   - Energy: 4/10

4. **Family Oriented** (Focus: Space & schools)
   - Area: 9/10 ⭐
   - Plot: 8/10 ⭐
   - Bathrooms: 7/10
   - Rooms: 8/10
   - Schools (municipality): 6/10
   - Distance: 5/10
   - Price per m²: 5/10

5. **Eco-Conscious** (Focus: Sustainability)
   - Energy Label: 10/10 ⭐
   - Renovation Year: 8/10 ⭐
   - Heating Type: 7/10
   - Price per m²: 6/10
   - Distance (public transit): 7/10

---

## Phase 3: Base Filter Parameters 🔍

### 3.1 "Dream Home" Filters

**Minimum Requirements for Top-Tier Properties:**
- [ ] Living Area: ≥ 150 m²
- [ ] Bathrooms: ≥ 2
- [ ] Energy Label: C or better
- [ ] Distance to Copenhagen: ≤ 30 km
- [ ] Price per m²: ≤ municipality average × 1.2
- [ ] Renovation: After 2010 OR Year Built after 2005

### 3.2 "Value Deal" Filters

**Best Bargains (underpriced properties):**
- [ ] Price per m²: < municipality average × 0.85
- [ ] Living Area: ≥ 100 m²
- [ ] Not on market > 180 days (avoid problem properties)
- [ ] At least 1 recent registration (within 10 years)

### 3.3 "Investment Opportunity" Filters

**Properties with potential:**
- [ ] Price per m²: < municipality average × 0.80
- [ ] Living Area: ≥ 120 m²
- [ ] Renovation year: Before 2015 (room for value-add)
- [ ] Energy Label: D or worse (potential for upgrade)
- [ ] Distance: ≤ 40 km (still accessible)

---

## Phase 4: Implementation 💻

### 4.1 Backend API Endpoints
- [ ] `/api/score` - Calculate score for single property
- [ ] `/api/score/batch` - Calculate scores for multiple properties
- [ ] `/api/score/presets` - Return preset weight configurations
- [ ] `/api/score/filters` - Apply base filters before scoring

### 4.2 Frontend Features
- [x] Score calculator page with weight sliders
- [x] Preset buttons for quick configuration
- [ ] Visual score breakdown charts
- [ ] Compare mode (2-3 properties side-by-side)
- [ ] Save custom weight profiles
- [ ] Export scored property list to CSV

### 4.3 Database Optimizations
- [ ] Add computed score column (optional, for caching)
- [ ] Create indexes on frequently filtered fields
- [ ] Store user-saved scoring profiles

---

## Phase 5: Validation & Tuning 🧪

### 5.1 Testing
- [ ] Test with 1000 random properties
- [ ] Verify score distribution (should be roughly bell curve)
- [ ] Check for edge cases (missing data, outliers)
- [ ] Validate against expert opinions (realtors, agents)

### 5.2 Calibration
- [ ] Adjust weight ranges if scores cluster too tightly
- [ ] Fine-tune normalization functions
- [ ] Ensure scoring feels intuitive to users

### 5.3 A/B Testing
- [ ] Test different preset configurations
- [ ] Gather user feedback on scoring accuracy
- [ ] Iterate based on real usage patterns

---

## Phase 6: Advanced Features 🚀

### 6.1 Machine Learning Integration
- [ ] Train ML model on historical sale prices
- [ ] Predict fair market value based on features
- [ ] Compare ML predictions with manual scoring
- [ ] Hybrid approach: ML + weighted scoring

### 6.2 Neighborhood Analytics
- [ ] Calculate neighborhood desirability scores
- [ ] Factor in crime rates, schools, amenities
- [ ] Add public transit accessibility score
- [ ] Include walkability metrics

### 6.3 Market Trends
- [ ] Track price per m² trends over time
- [ ] Identify "hot" vs "cold" neighborhoods
- [ ] Predict price appreciation potential
- [ ] Alert users to newly listed properties matching their profile

---

## Success Metrics 📊

- [ ] 80%+ of top-scored properties align with user expectations
- [ ] Score calculator used by 50%+ of site visitors
- [ ] Average session time increases by 30%+
- [ ] User satisfaction rating ≥ 4.5/5 for scoring feature

---

## Resources Needed

- **Data:** All 84,469 properties with complete field data ✓
- **Tools:** Python, NumPy, Pandas for analysis
- **Validation:** Access to recent sale data for comparison
- **Expertise:** Realtor consultation for weight validation

---

## Timeline Estimate

- Phase 1 (Research): 2-3 days
- Phase 2 (Algorithm): 3-5 days
- Phase 3 (Filters): 1-2 days
- Phase 4 (Implementation): 5-7 days
- Phase 5 (Validation): 2-3 days
- Phase 6 (Advanced): 10+ days (ongoing)

**Total:** ~20-25 days for basic version, ongoing for advanced features

---

## Notes

- Start with simple linear scoring, iterate to logarithmic/exponential if needed
- Keep scoring transparent - users should understand why a property scores high/low
- Allow full customization - users know their priorities best
- Monitor for gaming/manipulation of scores
- Consider adding "hidden gem" algorithm for undervalued properties
