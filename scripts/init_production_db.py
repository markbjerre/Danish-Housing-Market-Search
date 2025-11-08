#!/usr/bin/env python3
"""
Initialize Production Database Schema
Creates all tables based on db_models_new.py schema
"""

import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import db
from db_models_new import Base

def init_database():
    """Initialize all database tables"""
    print("🔧 Initializing Production Database...")
    print(f"📊 Database: {db.db_params['database']}")
    print(f"🏠 Host: {db.db_params['host']}")
    
    try:
        # Create all tables from Base metadata
        print("\n📝 Creating tables from schema...")
        Base.metadata.create_all(db.engine)
        
        # Get list of created tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        print(f"\n✅ Successfully created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   - {table}")
            
        print("\n🎉 Database initialization complete!")
        print("\n📌 Next steps:")
        print("   1. Run import_copenhagen_area.py to populate data")
        print("   2. Or restore from Parquet backup using restore_from_parquet.py")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        raise

if __name__ == "__main__":
    init_database()
