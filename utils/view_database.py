"""
View database schema and sample data
"""
from src.database import db
from src.db_models import PropertyDB, PropertyScoreDB
import pandas as pd

# Get session
session = db.get_session()

print("=" * 80)
print("PROPERTY DATABASE SCHEMA")
print("=" * 80)

# Show all columns
print("\n📊 PropertyDB Columns:\n")
for i, col in enumerate(PropertyDB.__table__.columns, 1):
    print(f"{i:2}. {col.name:30} {str(col.type):20}")

# Get sample data
print("\n" + "=" * 80)
print("SAMPLE PROPERTIES (First 3)")
print("=" * 80)

props = session.query(PropertyDB).limit(3).all()

for i, prop in enumerate(props, 1):
    print(f"\n🏠 Property #{i}")
    print(f"   ID: {prop.id}")
    print(f"   Address: {prop.address}")
    print(f"   Price: {prop.price:,} kr" if prop.price else "   Price: N/A")
    print(f"   Size: {prop.square_meters} m²" if prop.square_meters else "   Size: N/A")
    print(f"   Type: {prop.property_type}")
    print(f"   Municipality: {prop.municipality}")
    print(f"   City: {prop.city}")
    print(f"   Zip: {prop.zip_code}")
    print(f"   Rooms: {prop.rooms}")
    print(f"   Bathrooms: {prop.number_of_bathrooms}")
    print(f"   Year Built: {prop.year_built}")
    print(f"   Year Renovated: {prop.year_renovated}")
    print(f"   Heating: {prop.heating_type}")
    print(f"   Location: ({prop.latitude}, {prop.longitude})")

# Statistics
print("\n" + "=" * 80)
print("DATABASE STATISTICS")
print("=" * 80)

total_props = session.query(PropertyDB).count()
total_scores = session.query(PropertyScoreDB).count()

print(f"\n📈 Total Properties: {total_props:,}")
print(f"📊 Total Scores: {total_scores:,}")
print(f"⚠️  Properties without scores: {total_props - total_scores:,}")

# Property type breakdown
from sqlalchemy import func
print("\n🏘️  Property Types:")
types = session.query(PropertyDB.property_type, func.count(PropertyDB.id))\
    .group_by(PropertyDB.property_type)\
    .all()
for ptype, count in types:
    print(f"   {ptype}: {count:,}")

# Municipality breakdown (top 10)
print("\n🗺️  Top 10 Municipalities:")
municipalities = session.query(PropertyDB.municipality, func.count(PropertyDB.id))\
    .group_by(PropertyDB.municipality)\
    .order_by(func.count(PropertyDB.id).desc())\
    .limit(10)\
    .all()
for muni, count in municipalities:
    print(f"   {muni}: {count:,}")

# Price statistics
print("\n💰 Price Statistics:")
avg_price = session.query(func.avg(PropertyDB.price)).scalar()
min_price = session.query(func.min(PropertyDB.price)).scalar()
max_price = session.query(func.max(PropertyDB.price)).scalar()
print(f"   Average: {avg_price:,.0f} kr" if avg_price else "   Average: N/A")
print(f"   Minimum: {min_price:,.0f} kr" if min_price else "   Minimum: N/A")
print(f"   Maximum: {max_price:,.0f} kr" if max_price else "   Maximum: N/A")

session.close()

print("\n" + "=" * 80)
