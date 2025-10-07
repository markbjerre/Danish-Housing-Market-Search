"""
Investigate Cases Table Structure and Price Data
Purpose: Understand how prices are stored in the cases table
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import func, inspect
from src.database import db
from src.db_models_new import Property, Case
import json

print("="*80)
print("INVESTIGATING CASES TABLE STRUCTURE")
print("="*80)

session = db.get_session()

# Get total counts
total_cases = session.query(Case).count()
total_properties = session.query(Property).count()
props_with_cases = session.query(Property).filter(Property.cases.any()).count()

print(f"\n📊 Overview:")
print(f"   Total Cases: {total_cases:,}")
print(f"   Total Properties: {total_properties:,}")
print(f"   Properties with Cases: {props_with_cases:,}")
print(f"   Cases per Property (avg): {total_cases/props_with_cases if props_with_cases > 0 else 0:.2f}")

# Get inspector to see actual table columns
inspector = inspect(db.engine)
columns = inspector.get_columns('cases')

print(f"\n📋 Cases Table Columns ({len(columns)} total):")
for col in columns:
    print(f"   - {col['name']:<30} {str(col['type']):<20} {'NULL' if col['nullable'] else 'NOT NULL'}")

# Sample a few cases with actual data
print("\n" + "="*80)
print("SAMPLE CASE RECORDS (First 10)")
print("="*80)

sample_cases = session.query(Case).limit(10).all()

for i, case in enumerate(sample_cases, 1):
    print(f"\n🔍 Case #{i}:")
    print(f"   ID: {case.id}")
    print(f"   Case ID: {case.case_id}")
    print(f"   Property ID: {case.property_id}")
    print(f"   Status: {case.status}")
    print(f"   Current Price: {case.current_price}")
    print(f"   Original Price: {case.original_price}")
    print(f"   Created Date: {case.created_date}")
    print(f"   Modified Date: {case.modified_date}")
    print(f"   Days on Market (Current): {case.days_on_market_current}")
    print(f"   Days on Market (Total): {case.days_on_market_total}")
    if case.realtors_info:
        print(f"   Realtors Info: {case.realtors_info if isinstance(case.realtors_info, str) else json.dumps(case.realtors_info, indent=6)}")

# Check properties with multiple cases
print("\n" + "="*80)
print("PROPERTIES WITH MULTIPLE CASES")
print("="*80)

multi_case_props = session.query(
    Property.id,
    Property.address,
    func.count(Case.id).label('case_count')
).join(Case, Property.id == Case.property_id
).group_by(Property.id, Property.address
).having(func.count(Case.id) > 1
).order_by(func.count(Case.id).desc()
).limit(10).all()

print(f"\nFound {len(multi_case_props)} properties with multiple cases:")
for prop_id, address, count in multi_case_props:
    print(f"\n   Property: {address}")
    print(f"   Cases: {count}")
    
    # Get all cases for this property
    cases = session.query(Case).filter(Case.property_id == prop_id).order_by(Case.created_date).all()
    for j, case in enumerate(cases, 1):
        print(f"      Case {j}: Status={case.status}, Original={case.original_price}, Current={case.current_price}, Created={case.created_date}")

# Check if there are any cases with price data
print("\n" + "="*80)
print("CHECKING FOR PRICE DATA")
print("="*80)

cases_with_current_price = session.query(Case).filter(Case.current_price.isnot(None)).count()
cases_with_original_price = session.query(Case).filter(Case.original_price.isnot(None)).count()

print(f"\n💰 Price Data Availability:")
print(f"   Cases with Current Price: {cases_with_current_price:,} ({(cases_with_current_price/total_cases)*100:.2f}%)")
print(f"   Cases with Original Price: {cases_with_original_price:,} ({(cases_with_original_price/total_cases)*100:.2f}%)")

if cases_with_current_price > 0:
    print("\n✅ PRICE DATA EXISTS! Sampling cases with prices:")
    cases_with_prices = session.query(Case).filter(Case.current_price.isnot(None)).limit(10).all()
    for case in cases_with_prices:
        print(f"   Case {case.case_id[:8]}... - Current: {case.current_price:,.0f} kr, Original: {case.original_price:,.0f if case.original_price else 'N/A'} kr")
else:
    print("\n❌ NO PRICE DATA FOUND in current_price or original_price fields")

# Let's check the raw API data structure by looking at a property with cases
print("\n" + "="*80)
print("EXAMINING RAW PROPERTY DATA STRUCTURE")
print("="*80)

# Get a property with a case
prop_with_case = session.query(Property).filter(Property.cases.any()).first()

if prop_with_case:
    print(f"\n📦 Property: {prop_with_case.address}")
    print(f"   Property ID: {prop_with_case.id}")
    print(f"   Is On Market: {prop_with_case.is_on_market}")
    print(f"   Latest Valuation: {prop_with_case.latest_valuation:,.0f if prop_with_case.latest_valuation else 'N/A'} kr")
    
    print(f"\n   Cases for this property ({len(prop_with_case.cases)}):")
    for case in prop_with_case.cases:
        print(f"\n      Case ID: {case.case_id}")
        print(f"      Status: {case.status}")
        print(f"      Current Price: {case.current_price}")
        print(f"      Original Price: {case.original_price}")
        print(f"      Created: {case.created_date}")
        print(f"      Days on Market: {case.days_on_market_current}")
        
        # Check if realtor info contains price data
        if case.realtors_info:
            print(f"      Realtors Info Type: {type(case.realtors_info)}")
            if isinstance(case.realtors_info, list):
                print(f"      Realtors Info: {json.dumps(case.realtors_info[:1] if case.realtors_info else [], indent=10)}")
            else:
                print(f"      Realtors Info: {case.realtors_info}")

# Check if we need to look at the import script to see how cases are being imported
print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)

if cases_with_current_price == 0:
    print("""
⚠️ NO PRICE DATA FOUND IN CASES TABLE

This means the import script (import_api_data.py) is not capturing price data from the API.

Next steps:
1. Check the API response structure for cases/listings
2. Update import_api_data.py to extract price fields correctly
3. Re-import data or update existing records

The price data might be in the API response under fields like:
- case['price']
- case['currentPrice']
- case['originalPrice']  
- case['cashPrice']
- case['listingPrice']
""")
else:
    print(f"""
✅ PRICE DATA EXISTS: {cases_with_current_price:,} cases have prices

The data is already in the database. The EDA script may need updating to properly
query and display this information.
""")

session.close()

print("\n" + "="*80)
print("INVESTIGATION COMPLETE")
print("="*80)
