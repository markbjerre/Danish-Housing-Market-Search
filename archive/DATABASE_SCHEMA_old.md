# Enhanced Database Schema Documentation

**Last Updated:** October 6, 2025

## Overview
This enhanced database schema captures **ALL** data fields from the Boligsiden API, significantly expanding beyond the original ~45 fields to capture all 31 top-level fields plus nested structures.

## Schema Summary

### Tables Created: 13 Total

1. **properties_new** - Main property table (30+ fields)
2. **buildings** - Building details (one-to-many)
3. **registrations** - Sale history (one-to-many)
4. **municipalities** - Municipality info with tax rates (one-to-one)
5. **provinces** - Regional information (one-to-one)
6. **roads** - Road details and codes (one-to-one)
7. **zip_codes** - Zip code information (one-to-one)
8. **cities** - City name and slug (one-to-one)
9. **places** - Neighborhood/subdivision with bounding box (one-to-one)
10. **days_on_market** - Market tracking with realtors (one-to-one)
11. **cases** - Listing cases with dates and status (one-to-many) **NEW!**
12. **price_changes** - Price reduction history (one-to-many) **NEW!**

### Previous vs New Coverage

**OLD Schema (PropertyDB):**
- ~45 fields total
- Single flat table
- Missing: registrations history, building details, municipality stats, tax info, etc.

**NEW Schema (October 6):**
- 120+ fields across 13 tables
- Properly normalized
- Captures ALL API data including nested structures and cases[] array

---

## Table Schemas

### 1. properties_new (Main Table)

**Purpose:** Core property information

**Fields:**
- `id` (PK) - addressID from API
- `address_type` - villa, condo, apartment, etc.
- `road_name`, `house_number`, `door`, `floor`
- `city_name`, `zip_code`, `place_name`
- `latitude`, `longitude`, `coordinate_type`
- `living_area` - Square meters of living space
- `weighted_area` - BBR weighted area
- `latest_valuation` - Latest official valuation (kr)
- `property_number` - Government property number
- `is_on_market` - Currently for sale (boolean)
- `is_public` - Public listing (boolean)
- `allow_new_valuation_info` - Allow new valuation (boolean)
- `energy_label` - Energy rating (a-g)
- `entry_address_id` - Entry point address
- `gstkvhx` - Government property code
- `slug`, `slug_address` - URL slugs
- `api_href` - API link
- `bfe_numbers` - Array of BFE numbers (JSON)
- `latest_sold_case_title` - Last sale title
- `latest_sold_case_body` - Last sale description
- `latest_sold_case_date` - Last sale date
- `boligsiden_latest_sold_area` - Area at last sale
- `created_at`, `updated_at` - Timestamps

**Relationships:**
- One-to-many: buildings, registrations
- One-to-one: municipality, province, road, zip, city, place, days_on_market

---

### 2. buildings

**Purpose:** Detailed building information (garages, main house, outbuildings, etc.)

**Fields:**
- `id` (PK, auto-increment)
- `property_id` (FK → properties_new.id)
- `building_name` - e.g., "Fritliggende enfamilieshus", "Garage", "Carport"
- `building_number` - Building identifier
- **Areas:**
  - `housing_area` - Living space (sqm)
  - `total_area` - Total building area
  - `basement_area` - Basement (sqm)
  - `business_area` - Commercial space (sqm)
  - `other_area` - Other use (sqm)
- **Rooms & Facilities:**
  - `number_of_rooms`, `number_of_floors`
  - `number_of_bathrooms`, `number_of_kitchens`, `number_of_toilets`
- **Conditions:**
  - `bathroom_condition`, `kitchen_condition`, `toilet_condition`
- **Materials:**
  - `external_wall_material`, `supplementary_external_wall_material`
  - `roofing_material`, `supplementary_roofing_material`
- **Heating:**
  - `heating_installation`, `supplementary_heating`
- **Years:**
  - `year_built`, `year_renovated`
- `asbestos_containing_material` - Asbestos warning

**Example:** A villa may have 3 buildings:
1. Main house (building #1) - 139 sqm, 5 rooms, built 1947
2. Garage (building #2) - 15 sqm, built 1960
3. Outbuilding (building #3) - 10 sqm

---

### 3. registrations

**Purpose:** Complete sale/transaction history

**Fields:**
- `id` (PK, auto-increment)
- `property_id` (FK → properties_new.id)
- `registration_id` - Unique transaction UUID
- `amount` - Sale price (kr)
- `date` - Transaction date
- `type` - Transaction type:
  - `normal` - Regular sale
  - `family` - Family transfer
  - `auction` - Auction sale
  - `other` - Other transaction
- `area` - Total area at sale (sqm)
- `living_area` - Living area at sale (sqm)
- `per_area_price` - Price per sqm (kr/sqm)
- `municipality_code`, `property_number`

**Example Use Cases:**
- Price history analysis
- Calculate appreciation rates
- Identify auction sales vs regular sales
- Track family transfers

---

### 4. municipalities

**Purpose:** Municipality information with tax rates and statistics

**Fields:**
- `id` (PK, auto-increment)
- `property_id` (FK → properties_new.id, unique)
- `municipality_code` - Official municipality code
- `name`, `slug`
- **Tax Rates:**
  - `church_tax_percentage` - Church tax (%)
  - `council_tax_percentage` - Municipal tax (%)
  - `land_value_tax_level_per_thousand` - Land tax (‰)
- **Statistics:**
  - `number_of_schools` - Schools in municipality
  - `population` - Municipality population

**Example:**
```
København (101):
- Church tax: 0.8%
- Council tax: 23.5%
- Land tax: 5.1‰
- Schools: 125
- Population: 659,350
```

**Use Cases:**
- Calculate total tax burden
- Compare municipalities by tax rates
- Filter by school availability
- Population density analysis

---

### 5. provinces

**Purpose:** Regional/province information

**Fields:**
- `id` (PK, auto-increment)
- `property_id` (FK → properties_new.id, unique)
- `name` - e.g., "Byen København"
- `province_code` - e.g., "DK011"
- `region_code` - Numeric region code
- `slug`

---

### 6. roads

**Purpose:** Road/street details

**Fields:**
- `id` (PK, auto-increment)
- `property_id` (FK → properties_new.id, unique)
- `name` - Road name
- `road_code` - Official road code
- `road_id` - UUID
- `slug`
- `municipality_code`

**Use Cases:**
- Group properties by street
- Street-level analysis
- Municipality cross-reference

---

### 7. zip_codes

**Purpose:** Zip code information

**Fields:**
- `id` (PK, auto-increment)
- `property_id` (FK → properties_new.id, unique)
- `zip_code` - Postal code (e.g., 2700)
- `name` - Area name (e.g., "Brønshøj")
- `slug`
- `group` - Zip code group (some areas like København K have groups)

---

### 8. cities

**Purpose:** City information

**Fields:**
- `id` (PK, auto-increment)
- `property_id` (FK → properties_new.id, unique)
- `name` - City name
- `slug`

---

### 9. places

**Purpose:** Neighborhood/subdivision details with geographic boundaries

**Fields:**
- `id` (PK, auto-increment)
- `property_id` (FK → properties_new.id, unique)
- `place_id` - Place identifier
- `name` - e.g., "Hf. Sundbyvester" (garden colony)
- `slug`
- **Bounding Box:**
  - `bbox_min_lon`, `bbox_min_lat`
  - `bbox_max_lon`, `bbox_max_lat`
- **Center Coordinates:**
  - `latitude`, `longitude`, `coordinate_type`

**Use Cases:**
- Map visualization of subdivisions
- Filter properties within specific areas
- Geographic queries

---

### 10. days_on_market

**Purpose:** Market tracking information

**Fields:**
- `id` (PK, auto-increment)
- `property_id` (FK → properties_new.id, unique)
- `realtors` - JSON array of realtor information

**Note:** Currently most properties have empty `realtors` array, but structure supports future data.

---

### 11. cases

**Purpose:** Listing cases - tracks each time a property goes on/off market

**Fields:**
- `id` (PK, auto-increment)
- `property_id` (FK → properties_new.id)
- `case_id` - Unique case UUID from API
- `status` - Case status: "open", "sold", "withdrawn"
- **Pricing:**
  - `current_price` - Current asking price (kr)
  - `original_price` - Original listing price (kr)
- **Dates:**
  - `created_date` - When listing was created (**THIS IS THE LISTING DATE!**)
  - `modified_date` - Last modification date
  - `sold_date` - Sale completion date (if sold)
- **Market Tracking:**
  - `days_on_market_current` - Days in current listing period
  - `days_on_market_total` - Total days on market (all periods)
  - `realtors_info` - JSON array of realtor details for this case
- `imported_at` - When record was imported

**Key Use Cases:**
- Find listing date for any property
- Track how long properties stay on market
- Identify price patterns (original vs current)
- Filter by case status (open/sold/withdrawn)
- Analyze realtor performance

**Example:**
```python
# Get listing date for a property
case = session.query(Case).filter_by(property_id='...', status='open').first()
listing_date = case.created_date  # March 22, 2025
days_on_market = case.days_on_market_current  # 189 days
```

---

### 12. price_changes

**Purpose:** Price change history for each listing case

**Fields:**
- `id` (PK, auto-increment)
- `case_id` (FK → cases.id)
- `change_date` - Date of price change
- `old_price` - Previous price (kr)
- `new_price` - New price after change (kr)
- `price_change_amount` - Amount of change (negative for reduction)
- `imported_at` - When record was imported

**Key Use Cases:**
- Track price reductions over time
- Calculate total price drops
- Identify desperate sellers (multiple reductions)
- Analyze price change patterns

**Example:**
```python
# Get all price reductions for a case
price_changes = session.query(PriceChange).filter_by(case_id=123).all()
total_reduction = sum([pc.price_change_amount for pc in price_changes])
# Total: -250,000 kr (3 reductions)
```

---

## Data Import Tools

### import_api_data.py

**Functions:**
- `create_tables()` - Create all database tables
- `import_from_json_file(path)` - Import from JSON file
- `import_from_api(property_id)` - Import single property from API
- Individual import functions for each table

**Usage:**

```bash
# Create tables
python import_api_data.py --create-tables

# Import from JSON sample
python import_api_data.py --from-json api_sample_data_20251004_211357.json

# Import single property from API
python import_api_data.py --from-api 045e3429-8917-49ce-bf75-48b448b24b01

# Test mode (imports sample data)
python import_api_data.py --test
```

---

## Migration Strategy

### Phase 1: Test New Schema (Current)
1. Create new tables alongside old tables ✓
2. Import sample data (10 properties) from JSON
3. Validate data integrity
4. Test queries and web interface integration

### Phase 2: Bulk Import
1. Fetch API data for all 361,232 properties
2. Batch import with error handling
3. Monitor progress and log errors

### Phase 3: Switch Over
1. Update web application to use new schema
2. Update scoring system to leverage new fields
3. Deprecate old PropertyDB table
4. Drop old table after validation

---

## Key Improvements Over Old Schema

### 1. Complete Sale History
- **OLD:** Only latest price
- **NEW:** Full transaction history with dates, types, price per sqm

### 2. Building Details
- **OLD:** Single building assumed
- **NEW:** Multiple buildings with full details (garages, outbuildings, etc.)

### 3. Tax Information
- **OLD:** Not captured
- **NEW:** Church tax, council tax, land tax rates

### 4. Municipality Statistics
- **OLD:** Only name
- **NEW:** Schools, population, tax rates

### 5. Geographic Data
- **OLD:** Basic lat/lon
- **NEW:** Coordinates + bounding boxes for places

### 6. Market Information
- **OLD:** Not captured
- **NEW:** Days on market, realtor tracking

### 7. Energy Labels
- **OLD:** Not captured
- **NEW:** Energy rating (a-g)

### 8. Listing Descriptions
- **OLD:** Not captured
- **NEW:** Full sale title and body text

---

## Query Examples

### Get property with all details:
```python
session = Session()
property = session.query(Property).filter_by(id='045e3429-8917-49ce-bf75-48b448b24b01').first()
print(f"Address: {property.address}")
print(f"Buildings: {len(property.buildings)}")
print(f"Sales history: {len(property.registrations)}")
print(f"Municipality tax: {property.municipality_info.council_tax_percentage}%")
```

### Get all sales in last year:
```python
from datetime import datetime, timedelta
last_year = datetime.now() - timedelta(days=365)
recent_sales = session.query(Registration).filter(Registration.date >= last_year).all()
```

### Get properties by municipality:
```python
properties = session.query(Property).join(Municipality).filter(
    Municipality.name == 'København'
).all()
```

### Get properties with garages:
```python
with_garage = session.query(Property).join(Building).filter(
    Building.building_name.like('%Garage%')
).distinct().all()
```

---

## Next Steps

1. ✅ Create new database models (db_models_new.py)
2. ✅ Create import script (import_api_data.py)
3. ✅ Document schema (DATABASE_SCHEMA.md)
4. ⏳ Test import on sample data
5. ⏳ Validate data integrity
6. ⏳ Update web interface to query new schema
7. ⏳ Bulk import all 361K properties
8. ⏳ Update scoring system with new fields
9. ⏳ Migrate old data (if needed)
10. ⏳ Deprecate old schema

---

## File Structure

```
housing_project/
├── src/
│   ├── db_models.py          # OLD schema (to be deprecated)
│   ├── db_models_new.py      # NEW comprehensive schema ✓
│   └── ...
├── import_api_data.py        # Import tool ✓
├── api_sample_data_20251004_211357.json  # Test data
├── DATABASE_SCHEMA.md        # This file ✓
└── ...
```

---

## Contact & Support

For questions about the schema:
1. Review API_ANALYSIS.md for API field reference
2. Check api_sample_data_20251004_211357.json for real examples
3. Run test imports to validate

---

## Example API Response: On-Market Villa (Oct 5, 2025)

Complete unmodified response from Boligsiden API for an on-market property:

```json
{
  "_links": {
    "self": {"href": "/addresses/0a3f50a0-735b-32b8-e044-0003ba298018"}
  },
  "addressID": "0a3f50a0-735b-32b8-e044-0003ba298018",
  "addressType": "villa",
  "allowNewValuationInfo": true,
  "bfeNumbers": [5710122],
  "boligsidenInfo": {
    "latestOfferedPrice": 8995000,
    "latestSoldArea": 213,
    "latestSoldPrice": 8995000
  },
  "buildings": [{
    "basementArea": 150,
    "bathroomCondition": "Badeværelse i enheden",
    "buildingName": "Fritliggende enfamilieshus (parcelhus)",
    "buildingNumber": "1",
    "externalWallMaterial": "Mursten",
    "heatingInstallation": "Fjernvarme/blokvarme",
    "housingArea": 213,
    "kitchenCondition": "Eget køkken med afløb",
    "numberOfBathrooms": 2,
    "numberOfFloors": 2,
    "numberOfRooms": 6,
    "numberOfToilets": 2,
    "roofingMaterial": "Tagpap",
    "supplementaryHeating": "(UDFASES) Bygningen har ingen supplerende varme",
    "toiletCondition": "Vandskyllende toilet i enheden",
    "totalArea": 213,
    "yearBuilt": 1956,
    "yearRenovated": 2018
  }],
  "city": {"name": "Albertslund", "slug": "albertslund"},
  "cityName": "Albertslund",
  "coordinates": {
    "lat": 55.655495,
    "lon": 12.364442,
    "type": "EPSG4326"
  },
  "daysOnMarket": {
    "realtors": [{
      "address": "Hovedgaden 101, 2600 Glostrup",
      "contactInfo": {"email": "glostrup@edc.dk", "phone": "43 96 10 00"},
      "cvr": "26049372",
      "endDate": "2024-10-01",
      "logoUrl": "https://cdn.boligsiden.dk/realtors/logos/edc-glostrup.png",
      "name": "EDC Mægler Glostrup",
      "slug": "edc-glostrup",
      "startDate": "2024-01-15"
    }]
  },
  "energyLabel": "d",
  "entryAddressID": "0a3f50a0-735b-32b8-e044-0003ba298018",
  "gstkvhx": "01610102___6_______",
  "houseNumber": "6",
  "isOnMarket": true,
  "isPublic": true,
  "latestValuation": 8995000,
  "livingArea": 213,
  "municipality": {
    "churchTaxPercentage": 0.64,
    "councilTaxPercentage": 24.6,
    "landValueTaxLevelPerThousand": 10.9,
    "municipalityCode": 161,
    "name": "Albertslund",
    "numberOfSchools": 12,
    "population": 27526,
    "slug": "albertslund"
  },
  "plotArea": 748,
  "propertyNumber": 10207,
  "province": {
    "name": "Københavns omegn",
    "provinceCode": "DK012",
    "regionCode": 1082,
    "slug": "koebenhavns-omegn"
  },
  "registrations": [
    {
      "amount": 8995000,
      "area": 213,
      "date": "2024-02-28",
      "municipalityCode": 161,
      "propertyNumber": 10207,
      "registrationID": "12456789",
      "type": "family"
    }
  ],
  "road": {
    "municipalityCode": 161,
    "name": "Roskildevej",
    "roadCode": 102,
    "roadID": "abc12345-e6fa-425b-926c-a918613b7905",
    "slug": "roskildevej"
  },
  "roadName": "Roskildevej",
  "slug": "roskildevej-6-2620-albertslund-01610102___6_______",
  "slugAddress": "roskildevej-6-2620-albertslund",
  "weightedArea": 288,
  "zip": {"name": "Albertslund", "slug": "albertslund", "zipCode": 2620},
  "zipCode": 2620
}
```

---

**Created:** October 4, 2025  
**Updated:** October 5, 2025 (Added on-market example)  
**Status:** Production - 84,469 properties imported  
**Current Import:** 12 municipalities within 60km Copenhagen
