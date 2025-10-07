"""
Comprehensive Exploratory Data Analysis (EDA) for Danish Housing Database
Created: October 7, 2025
Purpose: Deep understanding of actual data, edge cases, and patterns
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import func, distinct, case, and_, or_
from src.database import db
from src.db_models_new import (
    Property, MainBuilding, AdditionalBuilding, Registration,
    Municipality, Province, Road, Zip, City, Place, DaysOnMarket, Case, PriceChange
)
import pandas as pd
import json
from datetime import datetime
from collections import Counter

print("="*80)
print("COMPREHENSIVE EDA - DANISH HOUSING DATABASE")
print("="*80)
print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Establish database connection
session = db.get_session()

# ============================================================================
# SECTION 1: OVERVIEW & COUNTS
# ============================================================================
print("\n" + "="*80)
print("SECTION 1: DATABASE OVERVIEW & TABLE COUNTS")
print("="*80)

tables_info = {
    'Properties': Property,
    'Main Buildings': MainBuilding,
    'Additional Buildings': AdditionalBuilding,
    'Registrations': Registration,
    'Cases (Listings)': Case,
    'Price Changes': PriceChange,
    'Municipalities': Municipality,
    'Provinces': Province,
    'Roads': Road,
    'Zip Codes': Zip,
    'Cities': City,
    'Places': Place,
    'Days on Market': DaysOnMarket
}

for name, model in tables_info.items():
    count = session.query(model).count()
    print(f"   {name:<25} {count:>10,}")

# ============================================================================
# SECTION 2: PROPERTIES - CORE STATISTICS
# ============================================================================
print("\n" + "="*80)
print("SECTION 2: PROPERTY CORE STATISTICS")
print("="*80)

# Basic counts
total_properties = session.query(Property).count()
print(f"\n📊 Total Properties: {total_properties:,}")

# Address types
print("\n📍 Address Types Distribution:")
address_types = session.query(
    Property.address_type,
    func.count(Property.id)
).group_by(Property.address_type).all()
for addr_type, count in sorted(address_types, key=lambda x: x[1], reverse=True):
    pct = (count / total_properties) * 100
    print(f"   {addr_type or 'NULL':<30} {count:>8,} ({pct:>5.2f}%)")

# Living area statistics
print("\n📏 Living Area Statistics (sqm):")
area_stats = session.query(
    func.min(Property.living_area),
    func.max(Property.living_area),
    func.avg(Property.living_area),
    func.percentile_cont(0.5).within_group(Property.living_area),
    func.percentile_cont(0.25).within_group(Property.living_area),
    func.percentile_cont(0.75).within_group(Property.living_area)
).filter(Property.living_area.isnot(None)).first()

if area_stats[0]:
    print(f"   Minimum:    {area_stats[0]:>10,.1f} sqm")
    print(f"   25th %ile:  {area_stats[4]:>10,.1f} sqm")
    print(f"   Median:     {area_stats[3]:>10,.1f} sqm")
    print(f"   Mean:       {area_stats[2]:>10,.1f} sqm")
    print(f"   75th %ile:  {area_stats[5]:>10,.1f} sqm")
    print(f"   Maximum:    {area_stats[1]:>10,.1f} sqm")

# Count properties with/without living area
properties_with_area = session.query(Property).filter(Property.living_area.isnot(None)).count()
properties_without_area = total_properties - properties_with_area
print(f"   With area:  {properties_with_area:>10,} ({(properties_with_area/total_properties)*100:.1f}%)")
print(f"   Without:    {properties_without_area:>10,} ({(properties_without_area/total_properties)*100:.1f}%)")

# Valuation statistics
print("\n💰 Latest Valuation Statistics (DKK):")
valuation_stats = session.query(
    func.min(Property.latest_valuation),
    func.max(Property.latest_valuation),
    func.avg(Property.latest_valuation),
    func.percentile_cont(0.5).within_group(Property.latest_valuation),
    func.percentile_cont(0.25).within_group(Property.latest_valuation),
    func.percentile_cont(0.75).within_group(Property.latest_valuation)
).filter(Property.latest_valuation.isnot(None)).first()

if valuation_stats[0]:
    print(f"   Minimum:    {valuation_stats[0]:>15,.0f} kr")
    print(f"   25th %ile:  {valuation_stats[4]:>15,.0f} kr")
    print(f"   Median:     {valuation_stats[3]:>15,.0f} kr")
    print(f"   Mean:       {valuation_stats[2]:>15,.0f} kr")
    print(f"   75th %ile:  {valuation_stats[5]:>15,.0f} kr")
    print(f"   Maximum:    {valuation_stats[1]:>15,.0f} kr")

properties_with_valuation = session.query(Property).filter(Property.latest_valuation.isnot(None)).count()
properties_without_valuation = total_properties - properties_with_valuation
print(f"   With valuation:  {properties_with_valuation:>10,} ({(properties_with_valuation/total_properties)*100:.1f}%)")
print(f"   Without:         {properties_without_valuation:>10,} ({(properties_without_valuation/total_properties)*100:.1f}%)")

# Market status
print("\n🏪 Market Status:")
on_market = session.query(Property).filter(Property.is_on_market == True).count()
off_market = session.query(Property).filter(Property.is_on_market == False).count()
null_market = session.query(Property).filter(Property.is_on_market.is_(None)).count()
print(f"   On Market:   {on_market:>10,} ({(on_market/total_properties)*100:.2f}%)")
print(f"   Off Market:  {off_market:>10,} ({(off_market/total_properties)*100:.2f}%)")
print(f"   NULL:        {null_market:>10,} ({(null_market/total_properties)*100:.2f}%)")

# Public status
print("\n🔓 Public Listing Status:")
is_public = session.query(Property).filter(Property.is_public == True).count()
not_public = session.query(Property).filter(Property.is_public == False).count()
null_public = session.query(Property).filter(Property.is_public.is_(None)).count()
print(f"   Public:      {is_public:>10,} ({(is_public/total_properties)*100:.2f}%)")
print(f"   Not Public:  {not_public:>10,} ({(not_public/total_properties)*100:.2f}%)")
print(f"   NULL:        {null_public:>10,} ({(null_public/total_properties)*100:.2f}%)")

# Energy labels
print("\n⚡ Energy Labels Distribution:")
energy_labels = session.query(
    Property.energy_label,
    func.count(Property.id)
).group_by(Property.energy_label).order_by(func.count(Property.id).desc()).all()

for label, count in energy_labels[:15]:  # Top 15
    pct = (count / total_properties) * 100
    print(f"   {str(label or 'NULL'):<10} {count:>10,} ({pct:>5.2f}%)")

# ============================================================================
# SECTION 3: BUILDINGS ANALYSIS
# ============================================================================
print("\n" + "="*80)
print("SECTION 3: BUILDINGS ANALYSIS")
print("="*80)

# Main buildings
total_main_buildings = session.query(MainBuilding).count()
print(f"\n🏠 Main Buildings: {total_main_buildings:,}")

# Properties with/without main building
props_with_main = session.query(Property).filter(Property.main_building.has()).count()
props_without_main = total_properties - props_with_main
print(f"   Properties with main building:    {props_with_main:>10,} ({(props_with_main/total_properties)*100:.1f}%)")
print(f"   Properties without main building: {props_without_main:>10,} ({(props_without_main/total_properties)*100:.1f}%)")

# Building names
print("\n🏗️ Main Building Types:")
building_names = session.query(
    MainBuilding.building_name,
    func.count(MainBuilding.id)
).group_by(MainBuilding.building_name).order_by(func.count(MainBuilding.id).desc()).all()

for name, count in building_names[:10]:
    pct = (count / total_main_buildings) * 100
    print(f"   {(name or 'NULL')[:50]:<52} {count:>8,} ({pct:>5.2f}%)")

# Year built statistics
print("\n📅 Year Built Statistics:")
year_stats = session.query(
    func.min(MainBuilding.year_built),
    func.max(MainBuilding.year_built),
    func.avg(MainBuilding.year_built),
    func.percentile_cont(0.5).within_group(MainBuilding.year_built)
).filter(MainBuilding.year_built.isnot(None)).first()

if year_stats[0]:
    print(f"   Oldest:     {int(year_stats[0])} (Age: {2025 - int(year_stats[0])} years)")
    print(f"   Newest:     {int(year_stats[1])} (Age: {2025 - int(year_stats[1])} years)")
    print(f"   Median:     {int(year_stats[3])} (Age: {2025 - int(year_stats[3])} years)")
    print(f"   Mean:       {int(year_stats[2])} (Age: {2025 - int(year_stats[2])} years)")

# Age distribution
print("\n🕰️ Building Age Distribution:")
age_ranges = [
    ("0-10 years (2015+)", 2015, 2025),
    ("11-25 years (2000-2014)", 2000, 2014),
    ("26-50 years (1975-1999)", 1975, 1999),
    ("51-75 years (1950-1974)", 1950, 1974),
    ("76-100 years (1925-1949)", 1925, 1949),
    ("101-150 years (1875-1924)", 1875, 1924),
    ("151+ years (pre-1875)", 0, 1874)
]

for label, min_year, max_year in age_ranges:
    count = session.query(MainBuilding).filter(
        MainBuilding.year_built.between(min_year, max_year)
    ).count()
    pct = (count / total_main_buildings) * 100
    print(f"   {label:<30} {count:>8,} ({pct:>5.2f}%)")

# Room statistics
print("\n🚪 Room Statistics:")
room_stats = session.query(
    func.min(MainBuilding.number_of_rooms),
    func.max(MainBuilding.number_of_rooms),
    func.avg(MainBuilding.number_of_rooms),
    func.percentile_cont(0.5).within_group(MainBuilding.number_of_rooms)
).filter(MainBuilding.number_of_rooms.isnot(None)).first()

if room_stats[0]:
    print(f"   Minimum:    {int(room_stats[0]):>5} rooms")
    print(f"   Maximum:    {int(room_stats[1]):>5} rooms")
    print(f"   Median:     {room_stats[3]:>5.1f} rooms")
    print(f"   Mean:       {room_stats[2]:>5.1f} rooms")

# Bathroom/toilet statistics
print("\n🚿 Bathrooms & Toilets:")
bath_stats = session.query(
    func.avg(MainBuilding.number_of_bathrooms),
    func.avg(MainBuilding.number_of_toilets),
    func.avg(MainBuilding.number_of_kitchens)
).first()

if bath_stats[0]:
    print(f"   Average Bathrooms: {bath_stats[0]:>5.2f}")
if bath_stats[1]:
    print(f"   Average Toilets:   {bath_stats[1]:>5.2f}")
if bath_stats[2]:
    print(f"   Average Kitchens:  {bath_stats[2]:>5.2f}")

# Additional buildings
total_additional = session.query(AdditionalBuilding).count()
print(f"\n🏚️ Additional Buildings: {total_additional:,}")

# Properties with additional buildings
props_with_additional = session.query(Property).filter(
    Property.additional_buildings.any()
).count()
print(f"   Properties with additional buildings: {props_with_additional:>10,} ({(props_with_additional/total_properties)*100:.1f}%)")

# Additional building types
print("\n🔨 Additional Building Types:")
add_building_names = session.query(
    AdditionalBuilding.building_name,
    func.count(AdditionalBuilding.id)
).group_by(AdditionalBuilding.building_name).order_by(func.count(AdditionalBuilding.id).desc()).all()

for name, count in add_building_names[:15]:
    pct = (count / total_additional) * 100 if total_additional > 0 else 0
    print(f"   {(name or 'NULL')[:40]:<42} {count:>8,} ({pct:>5.2f}%)")

# ============================================================================
# SECTION 4: CASES & LISTINGS ANALYSIS
# ============================================================================
print("\n" + "="*80)
print("SECTION 4: CASES & LISTINGS ANALYSIS")
print("="*80)

total_cases = session.query(Case).count()
print(f"\n📋 Total Cases (Listings): {total_cases:,}")

# Properties with cases
props_with_cases = session.query(Property).filter(Property.cases.any()).count()
print(f"   Properties with cases:    {props_with_cases:>10,} ({(props_with_cases/total_properties)*100:.2f}%)")
print(f"   Properties without cases: {total_properties - props_with_cases:>10,} ({((total_properties - props_with_cases)/total_properties)*100:.2f}%)")

# Case status distribution
print("\n📊 Case Status Distribution:")
case_statuses = session.query(
    Case.status,
    func.count(Case.id)
).group_by(Case.status).order_by(func.count(Case.id).desc()).all()

for status, count in case_statuses:
    pct = (count / total_cases) * 100 if total_cases > 0 else 0
    print(f"   {str(status or 'NULL'):<20} {count:>8,} ({pct:>5.2f}%)")

# Current price statistics
print("\n💵 Current Price Statistics (from Cases):")
price_stats = session.query(
    func.min(Case.current_price),
    func.max(Case.current_price),
    func.avg(Case.current_price),
    func.percentile_cont(0.5).within_group(Case.current_price),
    func.percentile_cont(0.25).within_group(Case.current_price),
    func.percentile_cont(0.75).within_group(Case.current_price)
).filter(Case.current_price.isnot(None)).first()

if price_stats[0]:
    print(f"   Minimum:    {price_stats[0]:>15,.0f} kr")
    print(f"   25th %ile:  {price_stats[4]:>15,.0f} kr")
    print(f"   Median:     {price_stats[3]:>15,.0f} kr")
    print(f"   Mean:       {price_stats[2]:>15,.0f} kr")
    print(f"   75th %ile:  {price_stats[5]:>15,.0f} kr")
    print(f"   Maximum:    {price_stats[1]:>15,.0f} kr")

# Original vs current price analysis
print("\n📉 Price Changes Analysis:")
cases_with_both_prices = session.query(Case).filter(
    and_(Case.original_price.isnot(None), Case.current_price.isnot(None))
).count()
print(f"   Cases with both original & current price: {cases_with_both_prices:,}")

# Price reductions
price_reductions = session.query(Case).filter(
    and_(
        Case.original_price.isnot(None),
        Case.current_price.isnot(None),
        Case.current_price < Case.original_price
    )
).count()
pct_reduced = (price_reductions / cases_with_both_prices * 100) if cases_with_both_prices > 0 else 0
print(f"   Cases with price reductions:              {price_reductions:>8,} ({pct_reduced:.2f}%)")

# Price increases (unusual but possible)
price_increases = session.query(Case).filter(
    and_(
        Case.original_price.isnot(None),
        Case.current_price.isnot(None),
        Case.current_price > Case.original_price
    )
).count()
pct_increased = (price_increases / cases_with_both_prices * 100) if cases_with_both_prices > 0 else 0
print(f"   Cases with price increases:               {price_increases:>8,} ({pct_increased:.2f}%)")

# Price changes table
total_price_changes = session.query(PriceChange).count()
print(f"\n💱 Price Change Records: {total_price_changes:,}")

# Cases with price changes
cases_with_price_changes = session.query(Case).filter(Case.price_changes.any()).count()
print(f"   Cases with price change history: {cases_with_price_changes:>8,}")

# ============================================================================
# SECTION 5: REGISTRATIONS & SALE HISTORY
# ============================================================================
print("\n" + "="*80)
print("SECTION 5: REGISTRATIONS & SALE HISTORY")
print("="*80)

total_registrations = session.query(Registration).count()
print(f"\n📜 Total Registration Records: {total_registrations:,}")

# Properties with registrations
props_with_regs = session.query(Property).filter(Property.registrations.any()).count()
print(f"   Properties with sale history:    {props_with_regs:>10,} ({(props_with_regs/total_properties)*100:.1f}%)")
print(f"   Properties without sale history: {total_properties - props_with_regs:>10,} ({((total_properties - props_with_regs)/total_properties)*100:.1f}%)")

# Average registrations per property
avg_regs = total_registrations / props_with_regs if props_with_regs > 0 else 0
print(f"   Average registrations per property (with history): {avg_regs:.2f}")

# Transaction types
print("\n🏷️ Transaction Types:")
transaction_types = session.query(
    Registration.type,
    func.count(Registration.id)
).group_by(Registration.type).order_by(func.count(Registration.id).desc()).all()

for trans_type, count in transaction_types:
    pct = (count / total_registrations) * 100 if total_registrations > 0 else 0
    print(f"   {str(trans_type or 'NULL'):<20} {count:>10,} ({pct:>5.2f}%)")

# Sale price statistics
print("\n💰 Sale Price Statistics (from Registrations):")
sale_price_stats = session.query(
    func.min(Registration.amount),
    func.max(Registration.amount),
    func.avg(Registration.amount),
    func.percentile_cont(0.5).within_group(Registration.amount)
).filter(Registration.amount.isnot(None)).first()

if sale_price_stats[0]:
    print(f"   Minimum:    {sale_price_stats[0]:>15,.0f} kr")
    print(f"   Maximum:    {sale_price_stats[1]:>15,.0f} kr")
    print(f"   Median:     {sale_price_stats[3]:>15,.0f} kr")
    print(f"   Mean:       {sale_price_stats[2]:>15,.0f} kr")

# Price per sqm statistics
print("\n💵 Price Per Square Meter (from Registrations):")
per_sqm_stats = session.query(
    func.min(Registration.per_area_price),
    func.max(Registration.per_area_price),
    func.avg(Registration.per_area_price),
    func.percentile_cont(0.5).within_group(Registration.per_area_price)
).filter(Registration.per_area_price.isnot(None)).first()

if per_sqm_stats[0]:
    print(f"   Minimum:    {per_sqm_stats[0]:>10,.0f} kr/sqm")
    print(f"   Maximum:    {per_sqm_stats[1]:>10,.0f} kr/sqm")
    print(f"   Median:     {per_sqm_stats[3]:>10,.0f} kr/sqm")
    print(f"   Mean:       {per_sqm_stats[2]:>10,.0f} kr/sqm")

# ============================================================================
# SECTION 6: GEOGRAPHIC ANALYSIS
# ============================================================================
print("\n" + "="*80)
print("SECTION 6: GEOGRAPHIC DISTRIBUTION")
print("="*80)

# Municipalities
total_municipalities = session.query(func.count(func.distinct(Municipality.municipality_code))).scalar()
print(f"\n🗺️ Unique Municipalities: {total_municipalities}")

print("\n📊 Top 20 Municipalities by Property Count:")
muni_counts = session.query(
    Municipality.name,
    func.count(Property.id)
).join(Property, Property.id == Municipality.property_id
).group_by(Municipality.name
).order_by(func.count(Property.id).desc()
).limit(20).all()

for name, count in muni_counts:
    pct = (count / total_properties) * 100
    print(f"   {(name or 'NULL'):<30} {count:>8,} ({pct:>5.2f}%)")

# Zip codes
total_zip_codes = session.query(func.count(func.distinct(Property.zip_code))).filter(
    Property.zip_code.isnot(None)
).scalar()
print(f"\n📮 Unique Zip Codes: {total_zip_codes}")

print("\n📊 Top 15 Zip Codes by Property Count:")
zip_counts = session.query(
    Property.zip_code,
    func.count(Property.id)
).filter(Property.zip_code.isnot(None)
).group_by(Property.zip_code
).order_by(func.count(Property.id).desc()
).limit(15).all()

for zip_code, count in zip_counts:
    pct = (count / total_properties) * 100
    print(f"   {zip_code}  {count:>10,} ({pct:>5.2f}%)")

# Cities
total_cities = session.query(func.count(func.distinct(Property.city_name))).filter(
    Property.city_name.isnot(None)
).scalar()
print(f"\n🏙️ Unique Cities: {total_cities}")

print("\n📊 Top 15 Cities by Property Count:")
city_counts = session.query(
    Property.city_name,
    func.count(Property.id)
).filter(Property.city_name.isnot(None)
).group_by(Property.city_name
).order_by(func.count(Property.id).desc()
).limit(15).all()

for city, count in city_counts:
    pct = (count / total_properties) * 100
    print(f"   {(city or 'NULL'):<30} {count:>8,} ({pct:>5.2f}%)")

# ============================================================================
# SECTION 7: EDGE CASES & DATA QUALITY
# ============================================================================
print("\n" + "="*80)
print("SECTION 7: EDGE CASES & DATA QUALITY ISSUES")
print("="*80)

print("\n⚠️ OUTLIERS & ANOMALIES:")

# Extremely large properties
print("\n🏰 Extremely Large Properties (>1000 sqm):")
large_props = session.query(Property).filter(Property.living_area > 1000).order_by(Property.living_area.desc()).limit(10).all()
for prop in large_props:
    muni = session.query(Municipality.name).filter(Municipality.property_id == prop.id).scalar()
    print(f"   {prop.living_area:>6.0f} sqm | {prop.city_name or 'Unknown':<20} | {muni or 'Unknown':<20} | {prop.address_type or 'Unknown'}")

# Extremely small properties
print("\n🏠 Extremely Small Properties (<50 sqm):")
small_props = session.query(Property).filter(
    and_(Property.living_area.isnot(None), Property.living_area < 50)
).order_by(Property.living_area).limit(10).all()
for prop in small_props:
    muni = session.query(Municipality.name).filter(Municipality.property_id == prop.id).scalar()
    print(f"   {prop.living_area:>6.1f} sqm | {prop.city_name or 'Unknown':<20} | {muni or 'Unknown':<20} | {prop.address_type or 'Unknown'}")

# Very old buildings
print("\n🏛️ Oldest Buildings (pre-1850):")
old_buildings = session.query(Property, MainBuilding).join(
    MainBuilding, Property.id == MainBuilding.property_id
).filter(MainBuilding.year_built < 1850).order_by(MainBuilding.year_built).limit(10).all()

for prop, building in old_buildings:
    age = 2025 - building.year_built
    muni = session.query(Municipality.name).filter(Municipality.property_id == prop.id).scalar()
    print(f"   {building.year_built} ({age} yrs) | {prop.city_name or 'Unknown':<20} | {muni or 'Unknown':<20}")

# Very new buildings
print("\n🆕 Newest Buildings (2020+):")
new_buildings = session.query(Property, MainBuilding).join(
    MainBuilding, Property.id == MainBuilding.property_id
).filter(MainBuilding.year_built >= 2020).order_by(MainBuilding.year_built.desc()).limit(10).all()

for prop, building in new_buildings:
    age = 2025 - building.year_built
    muni = session.query(Municipality.name).filter(Municipality.property_id == prop.id).scalar()
    print(f"   {building.year_built} ({age} yrs) | {prop.city_name or 'Unknown':<20} | {muni or 'Unknown':<20}")

# Extremely expensive properties
print("\n💎 Most Expensive Properties (Valuation):")
expensive_props = session.query(Property).filter(
    Property.latest_valuation.isnot(None)
).order_by(Property.latest_valuation.desc()).limit(10).all()

for prop in expensive_props:
    muni = session.query(Municipality.name).filter(Municipality.property_id == prop.id).scalar()
    print(f"   {prop.latest_valuation:>15,.0f} kr | {prop.living_area or 0:>6.0f} sqm | {prop.city_name or 'Unknown':<15} | {muni or 'Unknown':<15}")

# Extremely cheap properties
print("\n💵 Least Expensive Properties (Valuation):")
cheap_props = session.query(Property).filter(
    and_(Property.latest_valuation.isnot(None), Property.latest_valuation > 0)
).order_by(Property.latest_valuation).limit(10).all()

for prop in cheap_props:
    muni = session.query(Municipality.name).filter(Municipality.property_id == prop.id).scalar()
    print(f"   {prop.latest_valuation:>15,.0f} kr | {prop.living_area or 0:>6.0f} sqm | {prop.city_name or 'Unknown':<15} | {muni or 'Unknown':<15}")

# Many rooms
print("\n🚪 Properties with Many Rooms (>15):")
many_rooms = session.query(Property, MainBuilding).join(
    MainBuilding, Property.id == MainBuilding.property_id
).filter(MainBuilding.number_of_rooms > 15).order_by(MainBuilding.number_of_rooms.desc()).limit(10).all()

for prop, building in many_rooms:
    muni = session.query(Municipality.name).filter(Municipality.property_id == prop.id).scalar()
    print(f"   {building.number_of_rooms:>2} rooms | {prop.living_area or 0:>6.0f} sqm | {prop.city_name or 'Unknown':<15} | {muni or 'Unknown':<15}")

# Missing critical data
print("\n❌ MISSING DATA SUMMARY:")
print(f"   Properties without living area:    {properties_without_area:>10,} ({(properties_without_area/total_properties)*100:.2f}%)")
print(f"   Properties without valuation:      {properties_without_valuation:>10,} ({(properties_without_valuation/total_properties)*100:.2f}%)")
print(f"   Properties without main building:  {props_without_main:>10,} ({(props_without_main/total_properties)*100:.2f}%)")
print(f"   Properties without sale history:   {total_properties - props_with_regs:>10,} ({((total_properties - props_with_regs)/total_properties)*100:.2f}%)")
print(f"   Properties without cases:          {total_properties - props_with_cases:>10,} ({((total_properties - props_with_cases)/total_properties)*100:.2f}%)")

# Properties with multiple registrations (active trading)
print("\n🔄 Most Traded Properties (>10 sales):")
frequently_sold = session.query(
    Property.id,
    Property.address,
    Property.city_name,
    func.count(Registration.id).label('sale_count')
).join(Registration, Property.id == Registration.property_id
).group_by(Property.id, Property.address, Property.city_name
).having(func.count(Registration.id) > 10
).order_by(func.count(Registration.id).desc()
).limit(10).all()

for prop_id, address, city, sale_count in frequently_sold:
    print(f"   {sale_count:>2} sales | {address or 'Unknown':<40} | {city or 'Unknown':<20}")

# ============================================================================
# SECTION 8: COORDINATE & LOCATION DATA QUALITY
# ============================================================================
print("\n" + "="*80)
print("SECTION 8: COORDINATE & LOCATION DATA QUALITY")
print("="*80)

# Coordinate availability
props_with_coords = session.query(Property).filter(
    and_(Property.latitude.isnot(None), Property.longitude.isnot(None))
).count()
props_without_coords = total_properties - props_with_coords

print(f"\n📍 Coordinate Data:")
print(f"   Properties with coordinates:    {props_with_coords:>10,} ({(props_with_coords/total_properties)*100:.2f}%)")
print(f"   Properties without coordinates: {props_without_coords:>10,} ({(props_without_coords/total_properties)*100:.2f}%)")

# Coordinate type distribution
print("\n🗺️ Coordinate Type Distribution:")
coord_types = session.query(
    Property.coordinate_type,
    func.count(Property.id)
).group_by(Property.coordinate_type).all()

for coord_type, count in coord_types:
    pct = (count / total_properties) * 100
    print(f"   {str(coord_type or 'NULL'):<20} {count:>10,} ({pct:>5.2f}%)")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("SUMMARY: KEY INSIGHTS")
print("="*80)

print(f"""
✅ DATABASE COMPLETENESS:
   - Total Properties: {total_properties:,}
   - With Living Area: {(properties_with_area/total_properties)*100:.1f}%
   - With Valuation: {(properties_with_valuation/total_properties)*100:.1f}%
   - With Main Building: {(props_with_main/total_properties)*100:.1f}%
   - With Sale History: {(props_with_regs/total_properties)*100:.1f}%
   - With Active Listings: {(props_with_cases/total_properties)*100:.2f}%

📊 PROPERTY CHARACTERISTICS:
   - Median Living Area: {area_stats[3] if area_stats[0] else 0:.0f} sqm
   - Median Valuation: {valuation_stats[3] if valuation_stats[0] else 0:,.0f} kr
   - Median Building Age: {2025 - int(year_stats[3]) if year_stats[0] else 0} years
   - Average Rooms: {room_stats[2] if room_stats[0] else 0:.1f}

🏪 MARKET STATUS:
   - Currently On Market: {(on_market/total_properties)*100:.2f}%
   - Active Cases: {total_cases:,}
   - Properties with Listings: {(props_with_cases/total_properties)*100:.2f}%

🗺️ GEOGRAPHIC COVERAGE:
   - Municipalities: {total_municipalities}
   - Zip Codes: {total_zip_codes}
   - Cities: {total_cities}

📜 TRANSACTION HISTORY:
   - Total Sale Records: {total_registrations:,}
   - Average Sales per Property: {avg_regs:.2f}
   - Median Sale Price: {sale_price_stats[3] if sale_price_stats[0] else 0:,.0f} kr
""")

print("="*80)
print("EDA COMPLETED SUCCESSFULLY")
print("="*80)
print(f"Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Close session
session.close()
