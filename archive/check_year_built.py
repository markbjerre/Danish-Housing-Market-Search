"""Check year_built values in the database"""
from src.database import Session
from src.db_models_new import MainBuilding, Property
from sqlalchemy import func, distinct

session = Session()

# Get sample of year_built values
print("\n=== Year Built Sample ===")
sample = session.query(
    MainBuilding.year_built, 
    func.count(MainBuilding.id).label('count')
).group_by(MainBuilding.year_built).order_by(func.count(MainBuilding.id).desc()).limit(20).all()

for year, count in sample:
    print(f"{year}: {count} properties")

# Check if all are 2025
total = session.query(MainBuilding).count()
year_2025 = session.query(MainBuilding).filter(MainBuilding.year_built == 2025).count()

print(f"\n=== Summary ===")
print(f"Total buildings: {total}")
print(f"Buildings with year_built = 2025: {year_2025}")
print(f"Percentage: {(year_2025/total)*100:.1f}%")

# Check a specific property
print("\n=== Sample Property ===")
prop = session.query(Property).first()
if prop and prop.building:
    print(f"Property ID: {prop.id}")
    print(f"Address: {prop.address}")
    print(f"Year Built: {prop.building.year_built}")

session.close()
