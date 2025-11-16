# Danish Housing Market Search - Codebase Scout Report

**Date:** November 14, 2025  
**Scope:** Database schema, API endpoints, frontend templates, data availability for scoring  
**Status:** Production-ready with comprehensive infrastructure for property analysis

---

## 1. DATABASE SCHEMA FOR PROPERTIES

### Core Property Table: `properties_new`
**File Location:** `/mnt/c/Users/Mark\ BJ/Desktop/Code\ Projects/Danish\ Housing\ Market\ Search/src/db_models_new.py` (lines 14-86)

**Primary Fields Available:**

#### Location & Identification
- `id` (String, PK) - addressID from API
- `address` (String) - Full address
- `road_name` (String) - Street name
- `house_number` (String)
- `door` (String) - Door designation (tv, th, etc.)
- `floor` (String) - Floor level
- `city_name` (String)
- `zip_code` (Integer)
- `place_name` (String) - Neighborhood/subdivision
- `latitude` (Float), `longitude` (Float) - Exact coordinates
- `coordinate_type` (String) - EPSG4326

#### Property Metrics (KEY FOR SCORING)
- `living_area` (Float) - Primary usable area in m²
- `weighted_area` (Float) - Alternative area metric
- `latest_valuation` (Float) - Most recent property valuation (DKK)
- `property_number` (Integer) - Government property ID
- `energy_label` (String) - Energy efficiency rating

#### Status & Flags
- `is_on_market` (Boolean) - Currently for sale or sold
- `is_public` (Boolean) - Public listing
- `allow_new_valuation_info` (Boolean)

#### Administrative
- `entry_address_id` (String) - Alternative API ID
- `gstkvhx` (String) - Government property code
- `slug` (String), `slug_address` (String) - URL-friendly identifiers
- `api_href` (String) - Boligsiden API reference
- `bfe_numbers` (JSON) - Array of property codes

#### Sales History
- `latest_sold_case_title` (Text)
- `latest_sold_case_body` (Text)
- `latest_sold_case_date` (DateTime)
- `boligsiden_latest_sold_area` (Float)

#### Timestamps
- `created_at` (DateTime)
- `updated_at` (DateTime)

### Related Tables for Comprehensive Property Data

#### `main_buildings` Table
**Purpose:** Building-specific data (one per property)

**Critical for Scoring:**
- `number_of_rooms` (Integer) - ESSENTIAL for property valuation
- `number_of_bathrooms` (Integer)
- `number_of_kitchens` (Integer)
- `number_of_toilets` (Integer)
- `number_of_floors` (Integer)
- `year_built` (Integer) - ESSENTIAL for age scoring
- `year_renovated` (Integer) - Renovation status

**Areas:**
- `housing_area` (Float) - Living space
- `total_area` (Float) - Total property area
- `basement_area` (Float)
- `business_area` (Float)
- `other_area` (Float)

**Conditions & Materials:**
- `bathroom_condition`, `kitchen_condition`, `toilet_condition` (String)
- `external_wall_material`, `roofing_material` (String)
- `heating_installation`, `supplementary_heating` (String)
- `asbestos_containing_material` (String) - Safety flag

#### `cases` Table
**Purpose:** Track listing history and pricing changes

**Critical for Scoring:**
- `current_price` (Float) - Current asking price (DKK)
- `original_price` (Float) - Original asking price
- `price_change_percentage` (Float) - Price reduction/increase
- `per_area_price` (Float) - DKK per m² - PRE-CALCULATED
- `monthly_expense` (Float) - Estimated monthly costs
- `created_date` (DateTime) - When listing started
- `sold_date` (DateTime) - Sale completion date
- `days_on_market_current` (Integer) - Days in current listing
- `days_on_market_total` (Integer) - Total time on market - ESSENTIAL for negotiation scoring
- `status` (String) - "open", "sold", "withdrawn"

#### `registrations` Table
**Purpose:** Historical sale records and price history

**For Historical Analysis:**
- `amount` (Float) - Sale price
- `date` (DateTime) - Sale date
- `per_area_price` (Float) - Price per m² at sale
- `type` (String) - "normal", "family", "auction", "other"
- `area` (Float) - Living area at time of sale
- `living_area` (Float) - Living area at sale

#### `municipality` Table
**Purpose:** Geographic & demographic data for location scoring

**For Location Scoring:**
- `name` (String) - Municipality name
- `municipality_code` (Integer)
- `church_tax_percentage` (Float) - Annual tax burden
- `council_tax_percentage` (Float) - Annual tax burden
- `land_value_tax_level_per_thousand` (Float) - Tax metric
- `population` (Integer) - Demographics
- `number_of_schools` (Integer) - Amenity score

#### `province` Table
**Purpose:** Regional information

- `name` (String) - Province/region
- `province_code` (String) - e.g., "DK011"

#### `zip_codes`, `cities`, `places`, `roads` Tables
**Purpose:** Hierarchical location data

#### `days_on_market` Table
**Purpose:** Realtor information

- `realtors` (JSON) - Array of realtor objects with names

---

## 2. CURRENT API ENDPOINTS

### File Location
**Main:** `/mnt/c/Users/Mark\ BJ/Desktop/Code\ Projects/Danish\ Housing\ Market\ Search/webapp/app.py` (743 lines)

### `/api/search` Endpoint (Lines 38-253)
**Method:** GET  
**Purpose:** Advanced property search with extensive filtering and sorting

**Request Parameters:**
```
Query Parameters:
- municipality: str (optional) - Filter by municipality name
- min_price, max_price: float - Price range (DKK)
- min_area, max_area: float - Living area range (m²)
- min_rooms, max_rooms: int - Room count range
- min_year, max_year: int - Year built range
- on_market: 'true'/'false' - Filter by market status (default: true)
- realtor: str - Filter by realtor (currently implemented but not fully utilized)
- min_days_on_market, max_days_on_market: int - Days on market range
- sort_by: str - ['price_asc', 'price_desc', 'size_desc', 'year_desc', 'price_per_sqm_asc']
- page: int - Page number (1-based)
- per_page: 50 (fixed, increased from 20)
```

**Response Format:**
```json
{
  "results": [
    {
      "id": "property_id",
      "address": "Road Name House Number",
      "city": "City Name",
      "zip_code": 1234,
      "municipality": "Municipality Name",
      "price": 3500000.0,                    // From most recent case.current_price
      "living_area": 125.5,
      "price_per_sqm": 27856.50,             // Calculated from current_price / living_area
      "area_avg_price_per_sqm": 28000.00,    // Municipality average
      "rooms": 5,
      "year_built": 1985,
      "energy_label": "D",
      "latitude": 55.7123,
      "longitude": 12.5456,
      "on_market": true,
      "slug": "property-slug",
      "realtors": ["Realtor Name"],
      "days_on_market": 45
    }
  ],
  "total": 1234,
  "page": 1,
  "per_page": 50,
  "total_pages": 25
}
```

**Implementation Details:**
- Uses SQLAlchemy ORM with complex query building
- Handles price filters via Case subquery to avoid duplicates
- Uses window functions (ROW_NUMBER) to get most recent case per property
- Applies DISTINCT to Property.id to prevent duplicate results
- Database-level sorting for efficiency
- Pagination at database level (OFFSET/LIMIT)

### `/api/text-search` Endpoint (Lines 255-487)
**Method:** GET  
**Purpose:** Full-text search across address, city, municipality fields with all filters from /api/search

**Request Parameters:**
```
Query Parameters:
- q: str - Search query (minimum 2 characters)
- All parameters from /api/search (municipality, price range, area, etc.)
- page, sort_by - Same as /api/search
```

**Search Fields:**
- `Property.road_name` (ILIKE - case insensitive)
- `Property.city_name` (ILIKE)
- `Property.place_name` (ILIKE)
- `Municipality.name` (ILIKE)
- `Property.zip_code` (cast to String, ILIKE)

**Response Format:** Identical to /api/search

**Key Implementation:**
- Minimum query length check (2 characters)
- Error handling for search failures
- Supports combining text search with all standard filters
- Same pagination and sorting as /api/search

### `/api/property/<property_id>` Endpoint (Lines 489-561)
**Method:** GET  
**Purpose:** Get detailed information for a single property (JSON API)

**Response Example:**
```json
{
  "id": "property_id",
  "address": "Road Name House Number",
  "door": "tv",
  "floor": "1",
  "city": "Copenhagen",
  "zip_code": 2100,
  "municipality": {
    "name": "Copenhagen",
    "code": 101,
    "population": 644000,
    "church_tax": 0.825,
    "council_tax": 23.3,
    "number_of_schools": 45
  },
  "main_building": {
    "year_built": 1985,
    "year_renovated": 2010,
    "number_of_rooms": 5,
    "number_of_bathrooms": 2,
    "total_area": 200.0
  },
  "living_area": 125.5,
  "latest_valuation": 3500000.0,
  "energy_label": "D",
  "on_market": true,
  "registrations": [
    {
      "date": "2020-05-15",
      "amount": 3100000.0,
      "area": 125.5,
      "type": "normal"
    }
  ],
  "latitude": 55.7123,
  "longitude": 12.5456
}
```

### `/property/<property_id>` Endpoint (Lines 563-670)
**Method:** GET  
**Purpose:** Detailed property information (HTMLified JSON)

**Returns:** Enhanced version of API endpoint with additional fields

### `/stats` Endpoint (Lines 672-714)
**Method:** GET  
**Purpose:** Database statistics and aggregations

**Response:**
```json
{
  "total_properties": 228594,
  "by_municipality": [
    {
      "name": "Copenhagen",
      "count": 45230
    }
  ],
  "price_stats": {
    "avg": 3450000.0,
    "min": 500000.0,
    "max": 25000000.0
  },
  "area_stats": {
    "avg": 145.5,
    "min": 25.0,
    "max": 850.0
  }
}
```

### Other Routes
- `/` - Landing page
- `/search` - Search page with filter controls
- `/score-calculator` - Interactive property scoring interface

---

## 3. FRONTEND TEMPLATES

### File Locations
Base: `/mnt/c/Users/Mark\ BJ/Desktop/Code\ Projects/Danish\ Housing\ Market\ Search/webapp/templates/`

#### `index.html` (Search Results)
**Purpose:** Main search interface with results display

**Key Features:**
- Text search input field (minimum 2 characters)
- Advanced filters panel:
  - Municipality dropdown
  - Price range (min/max sliders)
  - Area range (min/max)
  - Rooms range
  - Year built range
  - Market status toggle (On Market / Sold / All)
  - Realtor filter
  - Days on market range
- Sort options:
  - Price descending (default)
  - Price ascending
  - Size descending
  - Year descending
  - Price per m² ascending
- Results display:
  - Address, location info
  - Price with area average comparison
  - Price per m² calculation
  - Room/bathroom counts
  - Year built
  - Energy label
  - Map integration (Leaflet)
- Pagination controls
- Export options

#### `score_calculator.html`
**Purpose:** Interactive property scoring with adjustable weights

**Key Features:**
- Weight sliders for 6 scoring factors:
  1. Price per m² (default 35%)
  2. Size (15%)
  3. Age (10%)
  4. Location (25%)
  5. Floor level (5%)
  6. Days on market (10%)
- Preset weight profiles
- Real-time weight adjustment
- Property selection and scoring display
- Visual score representation

#### `home.html`
**Purpose:** Landing page

#### `data_info.html`
**Purpose:** Database information and statistics

---

## 4. DATA AVAILABLE FOR SCORING

### Directly Available Fields

#### Price Data (EXCELLENT for scoring)
- `latest_valuation` - Current property valuation (float, DKK)
- `Case.current_price` - Current asking price
- `Case.original_price` - Original asking price
- `Case.price_change_percentage` - How much price has changed
- `Case.per_area_price` - PRE-CALCULATED price per m²
- `Registration.amount` - Historical sale prices
- `Registration.per_area_price` - Historical price per m²
- **Area Averages:** Available from `/api/search` responses via `area_avg_price_per_sqm`

#### Size/Area Data (EXCELLENT)
- `living_area` - Primary metric for valuation
- `weighted_area` - Alternative metric
- `MainBuilding.housing_area`
- `MainBuilding.total_area`
- `MainBuilding.basement_area`
- `MainBuilding.business_area`
- Historical areas from `Registration.area` and `Registration.living_area`

#### Property Condition (GOOD)
- `MainBuilding.year_built` - Building age
- `MainBuilding.year_renovated` - Renovation status (can calc age since renovation)
- `MainBuilding.bathroom_condition` - Qualitative
- `MainBuilding.kitchen_condition` - Qualitative
- `MainBuilding.toilet_condition` - Qualitative
- `MainBuilding.external_wall_material` - Quality indicator
- `MainBuilding.roofing_material` - Quality/age indicator
- `MainBuilding.heating_installation` - Heating type (efficiency metric)
- `MainBuilding.asbestos_containing_material` - Safety flag

#### Rooms & Layout (GOOD)
- `MainBuilding.number_of_rooms` - Total rooms
- `MainBuilding.number_of_bathrooms` - Bathroom count
- `MainBuilding.number_of_kitchens` - Kitchen count
- `MainBuilding.number_of_toilets` - Toilet count
- `MainBuilding.number_of_floors` - Building height
- `Property.floor` - Specific floor level (for apartments)

#### Location Data (EXCELLENT)
- Geographic coordinates: `latitude`, `longitude`
- Municipality with demographics:
  - `Municipality.population`
  - `Municipality.number_of_schools`
  - `Municipality.church_tax_percentage`
  - `Municipality.council_tax_percentage`
  - `Municipality.land_value_tax_level_per_thousand`
- City, zip code, neighborhood (place_name)
- Province information
- **Area Price Averages:** Can calculate from filtered results

#### Market Timing (EXCELLENT)
- `Case.created_date` - When listing started
- `Case.sold_date` - When property was sold
- `Case.days_on_market_current` - Days in current listing
- `Case.days_on_market_total` - Total time on market (PERFECT for negotiation)
- `Property.latest_sold_case_date` - Last sale date

#### Ownership Costs (AVAILABLE)
- `Case.monthly_expense` - Pre-calculated monthly costs
- Municipality tax percentages allow calculating:
  - Church tax (kr/year)
  - Council tax (kr/year)
  - Land value tax

#### Sales History (EXCELLENT for trend analysis)
- `Registration` table has complete transaction history:
  - Sale dates, amounts, areas
  - Can calculate price trends over time
  - Can identify seasonal patterns
  - Can calc price per m² trends

### Calculated/Derived Data NOT in Database (Must Compute)
These calculations are performed at query time in the API:

1. **Price per m²:** `current_price / living_area`
2. **Area Average Price per m²:** Average of all on-market properties in municipality
3. **Price vs Area Average:** `property_price_per_sqm - area_average`
4. **Days on Market:** Calculated from case.created_date if not in days_on_market_current
5. **Property Age:** `current_year - year_built`
6. **Years Since Renovation:** `current_year - year_renovated`
7. **Percentage Below/Above Area Average:** `(property_price - avg_price) / avg_price * 100`

---

## 5. EXISTING SCORING SYSTEM

### Current Implementation
**File Location:** `/mnt/c/Users/Mark\ BJ/Desktop/Code\ Projects/Danish\ Housing\ Market\ Search/src/scoring.py` (137 lines)

### PropertyScorer Class

**Scoring Factors (6 metrics with adjustable weights):**

1. **price_per_sqm** (35% weight default)
   - Compares property to similar properties (within 30m² size range)
   - Calculation: `avg_price_per_sqm / property_price_per_sqm` (ratio)
   - Normalized to 0-1 range
   - Higher score = better value

2. **size** (15% weight)
   - Compares to average size for property type
   - Calculation: `property_size / avg_size` ratio
   - Normalized to 0-1 range
   - Larger properties preferred

3. **age** (10% weight)
   - Scoring based on building age:
     - Less than 30 years: 0.9 (preferred)
     - 50-100 years: 0.7 (renovation potential)
     - 100+ years: 0.4 (older)
     - Otherwise: 0.6 (mid-range)
   - Binary scoring (no comparables needed)

4. **location** (25% weight)
   - Hardcoded premium zones:
     - København K: 1.3x premium
     - Frederiksberg: 1.2x
     - Hellerup: 1.25x
     - Charlottenlund: 1.2x
     - København Ø: 1.15x
   - Others: 0.5 (default)
   - Issue: Only works for address string matching (not geospatial)

5. **floor** (5% weight)
   - Only applies to apartments
   - 2nd floor optimal (1.0)
   - 1st/3rd floor near-optimal (0.9-0.95)
   - Ground floor: 0.7 (less desirable)
   - Upper floors: 0.8-0.85

6. **days_on_market** (10% weight)
   - Based on listing duration:
     - <7 days: 0.9 (hot property)
     - 7-30 days: 0.7 (recent)
     - 30-90 days: 0.5 (standard)
     - 90+ days: 0.3 (long listing = less desirable)

**Final Scoring:**
- Weighted average of all 6 factors
- Multiplied by 100 to convert to 0-100 scale
- Rounded to 1 decimal place

### Customization Method
`PropertyScorer.update_weights(new_weights: Dict[str, float])`
- Takes dictionary of factor: weight pairs
- Auto-normalizes to sum to 1.0
- Used in `/score-calculator` page

### Issues with Current System
1. **Location scoring is basic:** String matching on address, not using coordinates
2. **No municipality-level factors:** Doesn't use population, schools, tax rates
3. **Limited historical data usage:** Only uses current listing date
4. **No price trend analysis:** Could use registration history
5. **Premium zones hardcoded:** Not flexible or data-driven
6. **Floor preference only for apartments:** Could apply to villas differently

---

## 6. RESPONSE FORMATS & DATA FLOW

### Search Results JSON Structure
```json
{
  "results": [
    {
      "id": "unique_property_id",
      "address": "Street Number",
      "city": "City Name",
      "zip_code": 2100,
      "municipality": "Copenhagen",
      "price": 3500000,              // From Case.current_price
      "living_area": 125.5,          // From Property.living_area
      "price_per_sqm": 27857,        // Calculated: price/living_area
      "area_avg_price_per_sqm": 28000,  // Municipality average
      "rooms": 5,                    // From MainBuilding.number_of_rooms
      "year_built": 1985,            // From MainBuilding.year_built
      "energy_label": "D",           // From Property.energy_label
      "latitude": 55.71,
      "longitude": 12.54,
      "on_market": true,             // From Property.is_on_market
      "slug": "property-slug",
      "realtors": ["Realtor Name"],
      "days_on_market": 45
    }
  ],
  "total": 1234,                     // Total matching properties
  "page": 1,
  "per_page": 50,
  "total_pages": 25
}
```

### Data Volume
- **228,594 total properties** in database
- **~3,623 active listings** (on_market = true with valid prices)
- **388,113 historical transactions** in registrations table
- **51 municipalities** within coverage area
- **Database size:** ~2.6M rows across 14 tables

---

## 7. KEY TECHNICAL CHARACTERISTICS

### Query Patterns
1. **Filtering:** Uses WHERE clauses with AND/OR combinations
2. **Pagination:** OFFSET/LIMIT at database level (page 1 = 0-49, page 2 = 50-99, etc.)
3. **Sorting:** 
   - Price: Uses window functions to get most recent case
   - Size: ORDER BY living_area
   - Year: ORDER BY year_built (with NULL handling)
   - Price per m²: Calculated (latest_valuation / living_area)
4. **Joins:** 
   - Property ← MainBuilding (one-to-one)
   - Property ← Case (one-to-many, needs GROUP BY or DISTINCT)
   - Property ← Municipality (one-to-one)
5. **Aggregations:** 
   - AVG price per m² by municipality
   - COUNT properties by municipality
   - MIN/MAX prices and areas

### Performance Considerations
- **Index recommendation:** Indexes on Property.is_on_market, Case.created_date, living_area
- **N+1 problem:** Avoided by using ORM relationships in single queries
- **Large result sets:** Handled by DISTINCT(Property.id) to prevent duplicates from joins
- **Pagination efficiency:** Database-level OFFSET/LIMIT prevents loading all rows

---

## 8. DATA FIELDS SUMMARY TABLE

| Category | Field | Type | For Scoring | Notes |
|----------|-------|------|-------------|-------|
| **Location** | latitude, longitude | Float | YES | Geospatial scoring |
| | municipality | String | YES | Demographics available |
| | city_name, zip_code | String | YES | Geographic hierarchy |
| **Price** | latest_valuation | Float | YES | Primary valuation |
| | Case.current_price | Float | YES | Current asking price |
| | Case.original_price | Float | YES | Price history |
| | price_change_percentage | Float | YES | Negotiation room |
| **Size** | living_area | Float | YES | Primary metric |
| | weighted_area | Float | YES | Alternative metric |
| | total_area (building) | Float | YES | Total property |
| **Building** | year_built | Integer | YES | Age/condition |
| | year_renovated | Integer | YES | Recent updates |
| | rooms, bathrooms | Integer | YES | Property value |
| | number_of_floors | Integer | YES | Building height |
| **Condition** | kitchen_condition | String | MAYBE | Qualitative data |
| | bathroom_condition | String | MAYBE | Qualitative data |
| | external_wall_material | String | MAYBE | Quality indicator |
| | heating_installation | String | MAYBE | Efficiency |
| **Market** | is_on_market | Boolean | YES | Listing status |
| | days_on_market_total | Integer | YES | How long listed |
| | created_date | DateTime | YES | Listing start |
| | sold_date | DateTime | YES | Sale completion |
| **History** | Registration.amount | Float | YES | Historical prices |
| | Registration.date | DateTime | YES | Sale dates |
| **Demographics** | population, schools | Integer | YES | Location value |
| | tax percentages | Float | YES | Cost of ownership |

---

## CONCLUSION

The system is well-architected with:
- **Complete database schema** capturing 100+ property attributes
- **Sophisticated API endpoints** with advanced filtering and pagination
- **Existing scoring infrastructure** with adjustable weights
- **Rich data availability** for multiple scoring dimensions
- **Production-ready implementation** with proper error handling and database optimization

**Key Strengths for Enhancement:**
- Registrations table provides complete transaction history
- Municipality data includes demographics and tax info
- Multiple area metrics available (living_area, weighted_area, total_area)
- Days on market data excellent for timing/negotiation scoring
- Pre-calculated fields (price_per_sqm, monthly_expense) available

**Opportunities for Advanced Scoring:**
- Geospatial-based location scoring (use coordinates)
- Trend analysis from registration history
- Cost-of-ownership calculations from tax data
- Market momentum (new listings vs old)
- Neighborhood amenity scoring (schools, demographic shifts)
- Renovation ROI calculations (year_renovated vs price premium)

