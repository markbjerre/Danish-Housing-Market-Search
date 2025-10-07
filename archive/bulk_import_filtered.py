"""
Bulk import with filtering:
1. Only properties with is_on_market = True
2. Only properties within 60km of Copenhagen
"""

import os
import sys
import json
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from math import radians, cos, sin, asin, sqrt
from datetime import datetime
import argparse

# Load environment
load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db_models_new import Base
from import_api_data import (
    import_property, import_main_building, import_additional_buildings,
    import_registrations, import_municipality, import_province,
    import_road, import_zip, import_city, import_place, import_days_on_market,
    safe_get
)

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'housing_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Copenhagen coordinates (City Hall Square)
CPH_LAT = 55.6761
CPH_LON = 12.5683
MAX_DISTANCE_KM = 60


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km"""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return c * 6371  # Earth radius in km


def passes_filters(api_data):
    """
    Check if property passes both filters:
    1. is_on_market = True
    2. Within 60km of Copenhagen
    """
    # Filter 1: Must be on market
    is_on_market = safe_get(api_data, 'isOnMarket')
    if not is_on_market:
        return False, "not_on_market"
    
    # Filter 2: Must be within 60km
    lat = safe_get(api_data, 'latitude')
    lon = safe_get(api_data, 'longitude')
    
    if lat is None or lon is None:
        return False, "no_coordinates"
    
    distance = haversine_distance(CPH_LAT, CPH_LON, lat, lon)
    if distance > MAX_DISTANCE_KM:
        return False, f"too_far_{distance:.1f}km"
    
    return True, f"pass_{distance:.1f}km"


def import_property_with_filters(property_id, api_data, session):
    """Import a single property if it passes filters"""
    # Check filters
    passes, reason = passes_filters(api_data)
    
    if not passes:
        return False, reason
    
    try:
        # Import property
        property_obj = import_property(api_data)
        session.add(property_obj)
        
        # Buildings
        main_building = import_main_building(property_id, safe_get(api_data, 'buildings'))
        if main_building:
            session.add(main_building)
        
        for additional_building in import_additional_buildings(property_id, safe_get(api_data, 'buildings')):
            session.add(additional_building)
        
        # Registrations
        for registration in import_registrations(property_id, safe_get(api_data, 'registrations')):
            session.add(registration)
        
        # Related entities
        municipality = import_municipality(property_id, safe_get(api_data, 'municipality'))
        if municipality:
            session.add(municipality)
        
        province = import_province(property_id, safe_get(api_data, 'province'))
        if province:
            session.add(province)
        
        road = import_road(property_id, safe_get(api_data, 'road'))
        if road:
            session.add(road)
        
        zip_obj = import_zip(property_id, safe_get(api_data, 'zip'))
        if zip_obj:
            session.add(zip_obj)
        
        city = import_city(property_id, safe_get(api_data, 'city'))
        if city:
            session.add(city)
        
        place = import_place(property_id, safe_get(api_data, 'place'))
        if place:
            session.add(place)
        
        days_on_market = import_days_on_market(property_id, safe_get(api_data, 'daysOnMarket'))
        if days_on_market:
            session.add(days_on_market)
        
        session.commit()
        return True, "imported"
        
    except Exception as e:
        session.rollback()
        return False, f"error: {str(e)[:50]}"


def bulk_import_from_csv(csv_path, limit=None, dry_run=False):
    """
    Import properties from CSV, applying filters
    
    Args:
        csv_path: Path to properties.csv file
        limit: Maximum number of properties to process (None = all)
        dry_run: If True, only check filters without importing
    """
    import csv
    
    session = Session()
    
    print("=" * 80)
    print("BULK IMPORT WITH FILTERS")
    print("=" * 80)
    print()
    print(f"Filters:")
    print(f"  1. is_on_market = True")
    print(f"  2. Within {MAX_DISTANCE_KM}km of Copenhagen (55.6761°N, 12.5683°E)")
    print()
    
    if dry_run:
        print("DRY RUN MODE - No data will be imported")
        print()
    
    # Statistics
    stats = {
        'total': 0,
        'imported': 0,
        'not_on_market': 0,
        'no_coordinates': 0,
        'too_far': 0,
        'errors': 0
    }
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            stats['total'] += 1
            
            if limit and stats['total'] > limit:
                break
            
            property_id = row.get('property_id')
            
            if not property_id:
                continue
            
            # Fetch from API
            try:
                url = f"https://api.boligsiden.dk/addresses/{property_id}"
                response = requests.get(url, timeout=10)
                
                if response.status_code != 200:
                    stats['errors'] += 1
                    if stats['total'] % 100 == 0:
                        print(f"Progress: {stats['total']} processed, {stats['imported']} imported")
                    continue
                
                api_data = response.json()
                
                if dry_run:
                    # Just check filters
                    passes, reason = passes_filters(api_data)
                    if passes:
                        stats['imported'] += 1
                    elif reason == "not_on_market":
                        stats['not_on_market'] += 1
                    elif reason == "no_coordinates":
                        stats['no_coordinates'] += 1
                    elif reason.startswith("too_far"):
                        stats['too_far'] += 1
                else:
                    # Actually import
                    success, reason = import_property_with_filters(property_id, api_data, session)
                    
                    if success:
                        stats['imported'] += 1
                    elif reason == "not_on_market":
                        stats['not_on_market'] += 1
                    elif reason == "no_coordinates":
                        stats['no_coordinates'] += 1
                    elif reason.startswith("too_far"):
                        stats['too_far'] += 1
                    elif reason.startswith("error"):
                        stats['errors'] += 1
                
                # Progress update
                if stats['total'] % 100 == 0:
                    print(f"Progress: {stats['total']} processed, {stats['imported']} passed filters")
                
            except Exception as e:
                stats['errors'] += 1
                if stats['total'] % 100 == 0:
                    print(f"Progress: {stats['total']} processed, {stats['imported']} imported")
    
    # Final report
    print()
    print("=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print()
    print(f"Total properties processed:     {stats['total']:>8}")
    print(f"Passed filters & imported:      {stats['imported']:>8} ({stats['imported']/stats['total']*100:.1f}%)")
    print()
    print("Filtered out:")
    print(f"  Not on market:                {stats['not_on_market']:>8} ({stats['not_on_market']/stats['total']*100:.1f}%)")
    print(f"  Too far (>{MAX_DISTANCE_KM}km):         {stats['too_far']:>8} ({stats['too_far']/stats['total']*100:.1f}%)")
    print(f"  No coordinates:               {stats['no_coordinates']:>8} ({stats['no_coordinates']/stats['total']*100:.1f}%)")
    print(f"  Errors:                       {stats['errors']:>8} ({stats['errors']/stats['total']*100:.1f}%)")
    print()
    
    session.close()


def main():
    parser = argparse.ArgumentParser(description='Bulk import with filters')
    parser.add_argument('--csv', default='data/properties.csv', help='Path to CSV file')
    parser.add_argument('--limit', type=int, help='Maximum number of properties to process')
    parser.add_argument('--dry-run', action='store_true', help='Check filters without importing')
    
    args = parser.parse_args()
    
    bulk_import_from_csv(args.csv, limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
