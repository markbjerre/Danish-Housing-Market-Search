"""
Drop and recreate all database tables
USE WITH CAUTION - This deletes all data!
"""
import import_api_data
from src.db_models_new import Base

print("=" * 60)
print("⚠️  DATABASE DROP & RECREATE UTILITY")
print("=" * 60)
print("\nThis will:")
print("  1. DROP all tables (properties_new, cases, price_changes, etc.)")
print("  2. RECREATE all tables (fresh, empty)")
print("\nAll data will be PERMANENTLY DELETED!")
print("\n" + "=" * 60)

response = input("\nAre you SURE? (type 'YES' to confirm): ")

if response != "YES":
    print("\n❌ Cancelled - no changes made")
    exit(0)

print("\n🗑️  Dropping all tables...")

try:
    # Drop all tables
    Base.metadata.drop_all(import_api_data.engine)
    print("   ✅ All tables dropped")
    
    # Recreate all tables
    print("\n🏗️  Recreating all tables...")
    Base.metadata.create_all(import_api_data.engine)
    print("   ✅ All tables recreated")
    
    print("\n✅ Database reset successfully!")
    print("\nYou can now run the import to get fresh data:")
    print("   python import_copenhagen_area.py --parallel --workers 12")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
