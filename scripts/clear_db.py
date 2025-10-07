"""
Clear all data from properties_new and related tables
USE WITH CAUTION - This deletes all data!
"""
import import_api_data
from src.db_models_new import Property

print("=" * 60)
print("⚠️  DATABASE CLEAR UTILITY")
print("=" * 60)
print("\nThis will DELETE ALL DATA from:")
print("  - properties_new (84,469 records)")
print("  - buildings")
print("  - registrations")
print("  - municipalities")
print("  - cases")
print("  - price_changes")
print("  - ... and all related tables")
print("\n" + "=" * 60)

response = input("\nAre you SURE you want to clear the database? (type 'YES' to confirm): ")

if response != "YES":
    print("\n❌ Cancelled - no data was deleted")
    exit(0)

print("\n🗑️  Clearing database...")

session = import_api_data.Session()

try:
    # Get count before deletion
    count = session.query(Property).count()
    print(f"   Found {count:,} properties to delete")
    
    # Delete all properties (cascade will handle related tables)
    deleted = session.query(Property).delete()
    session.commit()
    
    print(f"   ✅ Deleted {deleted:,} properties and all related data")
    print("\n✅ Database cleared successfully!")
    print("\nYou can now run the import to get fresh data with cases and price_changes:")
    print("   python import_copenhagen_area.py --parallel --workers 12")
    
except Exception as e:
    session.rollback()
    print(f"\n❌ Error: {e}")
finally:
    session.close()
