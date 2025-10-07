"""
Quick Floor Plan Scraper Test

This script tests the scraper on 3 properties from your database.
Simple and straightforward - just run it!
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from scrape_floor_plans_advanced import AdvancedFloorPlanScraper
from src.database import db
from src.db_models import PropertyDB

def main():
    print("🧪 Testing Floor Plan Scraper")
    print("="*60)
    print("This will test scraping on 3 properties from your database")
    print("Browser will open (not headless) so you can see what happens")
    print("="*60 + "\n")
    
    # Get 3 properties from database
    session = db.get_session()
    properties = session.query(PropertyDB).limit(3).all()
    
    print(f"Selected {len(properties)} properties:\n")
    for i, prop in enumerate(properties, 1):
        print(f"{i}. {prop.id}")
        print(f"   Type: {prop.property_type if prop.property_type else 'N/A'}")
        print(f"   City: {prop.city if prop.city else 'N/A'}")
        print()
    
    session.close()
    
    # Create scraper (NOT headless so you can see it)
    print("Starting browser...\n")
    scraper = AdvancedFloorPlanScraper(
        download_folder="floor_plans_test",
        headless=False  # You'll see the browser
    )
    
    try:
        for i, prop in enumerate(properties, 1):
            print(f"\n{'='*60}")
            print(f"Testing {i}/{len(properties)}: {prop.id}")
            print(f"{'='*60}")
            
            url = f"https://www.boligsiden.dk/addresses/{prop.id}"
            result = scraper.scrape_property(prop.id, url)
            
            if result['success']:
                print(f"✅ SUCCESS! Downloaded {len(result['floor_plans'])} floor plan(s)")
                for fp in result['floor_plans']:
                    print(f"   📄 {fp['filename']}")
            else:
                print(f"⚠️  No floor plans found")
                if result['error']:
                    print(f"   Error: {result['error']}")
        
        # Summary
        scraper.print_summary()
        
        print("\n" + "="*60)
        print("🎉 TEST COMPLETE!")
        print("="*60)
        print(f"Check the 'floor_plans_test' folder for results")
        print(f"Screenshots and images are saved there")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        scraper.close()
        print("\n👋 Browser closed")

if __name__ == "__main__":
    main()
