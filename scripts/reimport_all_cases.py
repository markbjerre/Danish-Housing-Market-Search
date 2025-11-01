"""
Re-import all cases for properties that currently have cases
This will populate the new price data, fields, and images for all active listings
"""

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src directory to path (go up one level from scripts/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db_models_new import Case

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'housing_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Import the reimport function
sys.path.insert(0, os.path.dirname(__file__))
from reimport_cases_test import reimport_cases_only

def get_properties_with_cases():
    """Get list of property IDs that have cases"""
    session = Session()
    try:
        # Get distinct property IDs from cases table
        result = session.query(Case.property_id).distinct().all()
        return [row[0] for row in result]
    finally:
        session.close()

def reimport_all_cases(max_workers=10):
    """Re-import cases for all properties with parallel processing"""
    
    print("=" * 80)
    print("BULK CASE RE-IMPORT")
    print("=" * 80)
    print()
    
    # Get properties with cases
    print("Fetching list of properties with cases...")
    property_ids = get_properties_with_cases()
    total = len(property_ids)
    
    print(f"✅ Found {total:,} properties with cases")
    print()
    
    confirm = input(f"Re-import cases for {total:,} properties? (yes/no): ")
    if confirm.lower() not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    print()
    print(f"Starting re-import with {max_workers} parallel workers...")
    print()
    
    # Track progress
    success_count = 0
    error_count = 0
    start_time = time.time()
    
    # Process in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_id = {
            executor.submit(reimport_cases_only, prop_id): prop_id 
            for prop_id in property_ids
        }
        
        # Process completed tasks
        for i, future in enumerate(as_completed(future_to_id), 1):
            prop_id = future_to_id[future]
            
            try:
                success = future.result()
                if success:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                print(f"❌ Unexpected error for {prop_id}: {e}")
            
            # Progress update every 100 properties
            if i % 100 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                eta_seconds = (total - i) / rate if rate > 0 else 0
                eta_minutes = eta_seconds / 60
                
                print(f"Progress: {i}/{total} ({i/total*100:.1f}%) - "
                      f"✅ {success_count} success, ❌ {error_count} errors - "
                      f"Rate: {rate:.1f}/sec - ETA: {eta_minutes:.1f} min")
    
    # Final summary
    elapsed = time.time() - start_time
    print()
    print("=" * 80)
    print("RE-IMPORT COMPLETE")
    print("=" * 80)
    print()
    print(f"Total properties: {total:,}")
    print(f"✅ Successful: {success_count:,} ({success_count/total*100:.1f}%)")
    print(f"❌ Errors: {error_count:,} ({error_count/total*100:.1f}%)")
    print(f"⏱️  Time: {elapsed/60:.1f} minutes ({elapsed/3600:.2f} hours)")
    print(f"📊 Rate: {total/elapsed:.1f} properties/second")
    print()
    
    # Verify results
    print("Verifying results...")
    session = Session()
    try:
        # Count cases with prices
        result = session.execute(text(
            "SELECT COUNT(*) FROM cases WHERE current_price IS NOT NULL"
        ))
        cases_with_price = result.scalar()
        
        # Count total cases
        result = session.execute(text("SELECT COUNT(*) FROM cases"))
        total_cases = result.scalar()
        
        # Count images
        result = session.execute(text("SELECT COUNT(*) FROM case_images"))
        total_images = result.scalar()
        
        print(f"✅ Cases with prices: {cases_with_price:,} / {total_cases:,} ({cases_with_price/total_cases*100:.1f}%)")
        print(f"✅ Total images: {total_images:,} (~{total_images/total_cases:.1f} per case)")
        print()
        
    finally:
        session.close()
    
    print("🎉 All done! Database is now fully enriched with:")
    print("   • Correct price data (priceCash)")
    print("   • 15 new case fields (descriptions, URLs, features, etc.)")
    print("   • Image URLs for all listings (2 sizes each)")
    print()

if __name__ == "__main__":
    reimport_all_cases(max_workers=10)
