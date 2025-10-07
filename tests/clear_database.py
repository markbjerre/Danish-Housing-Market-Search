"""
Clear all data from properties_new and related tables
USE WITH CAUTION - This deletes all data!
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import db
from db_models_new import Base, Property

print("=" * 60)
print("⚠️  DATABASE CLEAR UTILITY")
print("=" * 60)
print("\nThis will DELETE ALL DATA from:")
print("  - properties_new")
print("  - buildings")
print("  - registrations")
print("  - municipalities")
print("  - cases (NEW)")
print("  - price_changes (NEW)")
print("  - ... and all related tables")
print("\n" + "=" * 60)

response = input("\nAre you SURE you want to clear the database? (type 'YES' to confirm): ")

if response != "YES":
    print("\n❌ Cancelled - no data was deleted")
    sys.exit(0)

print("\n🗑️  Clearing database...")

session = db.get_session()

try:
    # Get count before deletion
    count = session.query(Property).count()
    print(f"   Found {count:,} properties to delete")
    
    # Delete all properties (cascade will handle related tables)
    deleted = session.query(Property).delete()
    session.commit()
    
    print(f"   ✅ Deleted {deleted:,} properties and all related data")
    print("\n✅ Database cleared successfully!")
    
except Exception as e:
    session.rollback()
    print(f"\n❌ Error: {e}")
finally:
    session.close()
