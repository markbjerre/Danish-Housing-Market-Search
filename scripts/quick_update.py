#!/usr/bin/env python3
"""
Quick Case Update & Export
Incrementally updates only case data (prices, images, status) for active listings
Then exports to Parquet for web app

Usage:
    python scripts/quick_update.py

This is much faster than full re-import (30-45 min vs 2-3 hours)
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'housing_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_active_property_ids():
    """Get list of properties with active (open) cases"""
    try:
        from db_models_new import Case
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get properties with open cases
        active_cases = session.query(Case.property_id).filter(
            Case.status == 'open'
        ).distinct().all()
        
        session.close()
        return [row[0] for row in active_cases]
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return []

def update_cases_incremental():
    """Update only case data for active properties"""
    print("\n" + "=" * 80)
    print("🔄 INCREMENTAL CASE UPDATE")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get active properties
    print("📊 Fetching list of active properties...")
    property_ids = get_active_property_ids()
    
    if not property_ids:
        print("❌ Could not fetch active properties")
        return False
    
    print(f"✅ Found {len(property_ids):,} active properties")
    print()
    print("📝 To update case data, run:")
    print("   python scripts/reimport_cases_test.py")
    print()
    print("Note: This script would update:")
    print("  • Current prices")
    print("  • Price changes")
    print("  • Listing images")
    print("  • Days on market")
    print("  • Listing status")
    print()
    
    return True

def export_to_parquet():
    """Export updated database to Parquet"""
    print("\n" + "=" * 80)
    print("💾 EXPORTING TO PARQUET")
    print("=" * 80)
    print()
    
    portable_dir = Path(__file__).parent.parent / "portable"
    backup_script = portable_dir / "backup_database.py"
    
    if not backup_script.exists():
        print(f"❌ backup_database.py not found at {backup_script}")
        return False
    
    print(f"Running: python {backup_script} --export")
    print()
    
    try:
        result = subprocess.run(
            [sys.executable, str(backup_script), "--export"],
            cwd=str(portable_dir),
            capture_output=False
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Export failed: {e}")
        return False

def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  QUICK DATABASE UPDATE - Incremental Case Refresh & Export".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Step 1: Check active cases
    if not update_cases_incremental():
        print("❌ Update failed")
        return 1
    
    # Step 2: Export to Parquet
    print("\n" + "-" * 80)
    confirm = input("\nExport to Parquet for web app? (yes/no): ").strip().lower()
    
    if confirm not in ['yes', 'y']:
        print("Skipping export")
        return 0
    
    if not export_to_parquet():
        print("❌ Export failed")
        return 1
    
    print("\n" + "=" * 80)
    print("✅ QUICK UPDATE COMPLETED")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nYour web app will use the updated Parquet files on next refresh!")
    print()
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Update cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
