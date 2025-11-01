"""
Re-import only case data (with new fields and images) for existing properties
This updates case information without touching the property record itself
"""

import os
import sys
import requests
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src directory to path (go up one level from scripts/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db_models_new import Case, CaseImage

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'housing_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Import the function
sys.path.insert(0, os.path.dirname(__file__))
from import_api_data import import_cases, safe_get

def reimport_cases_only(property_id):
    """Fetch API data and update only case information (including images)"""
    
    # Fetch from API
    url = f"https://api.boligsiden.dk/addresses/{property_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        api_data = response.json()
    except Exception as e:
        print(f"❌ Error fetching {property_id}: {e}")
        return False
    
    session = Session()
    try:
        # Delete existing cases for this property (cascade will delete images)
        existing_cases = session.query(Case).filter(Case.property_id == property_id).all()
        if existing_cases:
            for case in existing_cases:
                session.delete(case)
            # Commit deletion before importing new ones
            session.commit()
        
        # Import new cases with all fields
        cases_data = safe_get(api_data, 'cases')
        if cases_data:
            for case in import_cases(property_id, cases_data):
                session.add(case)
        
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error re-importing cases for {property_id}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def test_single_property():
    """Test re-import of single property case data"""
    
    property_id = "0a3f50a3-1a8a-32b8-e044-0003ba298018"
    
    print("=" * 80)
    print("TEST CASE RE-IMPORT - SINGLE PROPERTY")
    print("=" * 80)
    print()
    print(f"Property ID: {property_id}")
    print(f"Address: Vårbuen 28, 2750 Ballerup")
    print()
    
    # Re-import cases
    print("Re-importing case data from API...")
    success = reimport_cases_only(property_id)
    
    if not success:
        print("❌ Re-import failed!")
        return
    
    print("✅ Re-import completed")
    print()
    
    # Verify the data
    session = Session()
    try:
        # Get the case
        case = session.query(Case).filter(Case.property_id == property_id).first()
        
        if not case:
            print("❌ No case found after import!")
            return
        
        print("=" * 80)
        print("VERIFICATION RESULTS")
        print("=" * 80)
        print()
        
        # Core fields
        print("📋 CORE FIELDS:")
        print(f"  Case ID: {case.case_id}")
        print(f"  Status: {case.status}")
        print(f"  Current Price: {case.current_price:,.0f} kr" if case.current_price else "  Current Price: None ❌")
        print(f"  Original Price: {case.original_price:,.0f} kr" if case.original_price else "  Original Price: None")
        print()
        
        # NEW fields - Pricing
        print("💰 PRICING FIELDS (NEW):")
        print(f"  Price Change %: {case.price_change_percentage}%" if case.price_change_percentage else "  Price Change %: None")
        print(f"  Per Area Price: {case.per_area_price:,.0f} kr/m²" if case.per_area_price else "  Per Area Price: None")
        print(f"  Monthly Expense: {case.monthly_expense:,.0f} kr" if case.monthly_expense else "  Monthly Expense: None")
        print()
        
        # NEW fields - Property details
        print("🏠 PROPERTY DETAILS (NEW):")
        print(f"  Lot Area: {case.lot_area:,.0f} m²" if case.lot_area else "  Lot Area: None")
        print(f"  Basement Area: {case.basement_area:,.0f} m²" if case.basement_area else "  Basement Area: None")
        print(f"  Year Built: {case.year_built}" if case.year_built else "  Year Built: None")
        print()
        
        # NEW fields - Description
        print("📝 DESCRIPTION (NEW):")
        if case.description_title:
            print(f"  Title: {case.description_title[:60]}...")
        else:
            print("  Title: None")
        
        if case.description_body:
            print(f"  Body Length: {len(case.description_body)} chars")
            # Show first 100 chars
            print(f"  Preview: {case.description_body[:100]}...")
        else:
            print("  Body: None")
        print()
        
        # NEW fields - URLs
        print("🔗 URLS & IDS (NEW):")
        print(f"  Case URL: {case.case_url}" if case.case_url else "  Case URL: None")
        print(f"  Provider Case ID: {case.provider_case_id}" if case.provider_case_id else "  Provider Case ID: None")
        print()
        
        # NEW fields - Features
        print("✨ FEATURES (NEW):")
        print(f"  Has Balcony: {case.has_balcony}" if case.has_balcony is not None else "  Has Balcony: None")
        print(f"  Has Terrace: {case.has_terrace}" if case.has_terrace is not None else "  Has Terrace: None")
        print(f"  Has Elevator: {case.has_elevator}" if case.has_elevator is not None else "  Has Elevator: None")
        print(f"  Highlighted: {case.highlighted}" if case.highlighted is not None else "  Highlighted: None")
        print(f"  Distinction: {case.distinction}" if case.distinction else "  Distinction: None")
        print()
        
        # Images
        print("📸 IMAGES:")
        images = session.query(CaseImage).filter(CaseImage.case_id == case.id).order_by(CaseImage.sort_order, CaseImage.width).all()
        
        if not images:
            print("  ❌ No images found!")
        else:
            print(f"  ✅ Found {len(images)} image records")
            print()
            
            # Group by sort_order to show image pairs (600x400 and 1440x960)
            images_by_order = {}
            for img in images:
                if img.sort_order not in images_by_order:
                    images_by_order[img.sort_order] = []
                images_by_order[img.sort_order].append(img)
            
            for sort_order in sorted(images_by_order.keys()):
                imgs = images_by_order[sort_order]
                print(f"  Image {sort_order + 1}:")
                print(f"    Default: {imgs[0].is_default}")
                if imgs[0].alt_text:
                    print(f"    Alt Text: {imgs[0].alt_text[:50]}...")
                else:
                    print("    Alt Text: None")
                for img in imgs:
                    print(f"    • {img.width}x{img.height}: {img.image_url}")
                print()
        
        # Summary
        print("=" * 80)
        print("✅ VERIFICATION COMPLETE")
        print("=" * 80)
        print()
        print("Summary:")
        print(f"  • Core price field (priceCash): {'✅ FIXED' if case.current_price else '❌ STILL NULL'}")
        print(f"  • New pricing fields: {'✅' if case.per_area_price or case.monthly_expense else '⚠️ Some missing'}")
        print(f"  • New property fields: {'✅' if case.lot_area or case.basement_area else '⚠️ Some missing'}")
        print(f"  • Description fields: {'✅' if case.description_title else '⚠️ Missing'}")
        print(f"  • URL fields: {'✅' if case.case_url else '⚠️ Missing'}")
        print(f"  • Feature flags: {'✅' if case.has_balcony is not None else '⚠️ Some missing'}")
        print(f"  • Images: {'✅' if images else '❌ MISSING'} ({len(images)} records)")
        print()
        
        if case.current_price and images:
            print("🎉 SUCCESS! All critical features working!")
            print()
            print("Ready to proceed with full re-import of all 3,683 cases.")
        else:
            print("⚠️ WARNING: Some issues detected. Review above before proceeding.")
        print()
        
    finally:
        session.close()


if __name__ == "__main__":
    test_single_property()
