"""
Import API data into new comprehensive database schema
Handles all API fields and nested structures
"""

import sys
import os
import json
import requests
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src directory to path (go up one level since we're in scripts/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db_models_new import (
    Base, Property, MainBuilding, AdditionalBuilding, Registration, Municipality, 
    Province, Road, Zip, City, Place, DaysOnMarket, Case, PriceChange, CaseImage
)

# Database connection from environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'housing_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD environment variable not set")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def parse_date(date_str):
    """Convert date string to datetime object"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None


def safe_get(data, key, default=None):
    """Safely get value from dict"""
    return data.get(key, default) if data else default


def import_property(api_data):
    """Import a single property with all nested data"""
    
    # Main property
    property_obj = Property(
        id=safe_get(api_data, 'addressID'),
        address_type=safe_get(api_data, 'addressType'),
        road_name=safe_get(api_data, 'roadName'),
        house_number=safe_get(api_data, 'houseNumber'),
        city_name=safe_get(api_data, 'cityName'),
        zip_code=safe_get(api_data, 'zipCode'),
        place_name=safe_get(api_data, 'placeName'),
        
        # Coordinates
        latitude=safe_get(safe_get(api_data, 'coordinates'), 'lat'),
        longitude=safe_get(safe_get(api_data, 'coordinates'), 'lon'),
        coordinate_type=safe_get(safe_get(api_data, 'coordinates'), 'type'),
        
        # Areas and valuation
        living_area=safe_get(api_data, 'livingArea'),
        weighted_area=safe_get(api_data, 'weightedArea'),
        latest_valuation=safe_get(api_data, 'latestValuation'),
        property_number=safe_get(api_data, 'propertyNumber'),
        
        # Status
        is_on_market=safe_get(api_data, 'isOnMarket'),
        is_public=safe_get(api_data, 'isPublic'),
        allow_new_valuation_info=safe_get(api_data, 'allowNewValuationInfo'),
        
        # Energy
        energy_label=safe_get(api_data, 'energyLabel'),
        
        # IDs
        entry_address_id=safe_get(api_data, 'entryAddressID'),
        gstkvhx=safe_get(api_data, 'gstkvhx'),
        
        # Slugs
        slug=safe_get(api_data, 'slug'),
        slug_address=safe_get(api_data, 'slugAddress'),
        api_href=safe_get(safe_get(safe_get(api_data, '_links'), 'self'), 'href'),
        
        # Arrays
        bfe_numbers=safe_get(api_data, 'bfeNumbers'),
        
        # Latest sold case
        latest_sold_case_title=safe_get(safe_get(api_data, 'latestSoldCaseDescription'), 'title'),
        latest_sold_case_body=safe_get(safe_get(api_data, 'latestSoldCaseDescription'), 'body'),
        latest_sold_case_date=parse_date(safe_get(safe_get(api_data, 'latestSoldCaseDescription'), 'date')),
        
        # Boligsiden info
        boligsiden_latest_sold_area=safe_get(safe_get(api_data, 'boligsidenInfo'), 'latestSoldArea')
    )
    
    # Full address construction
    address_parts = [property_obj.road_name, property_obj.house_number]
    if property_obj.city_name and property_obj.zip_code:
        address_parts.append(f"{property_obj.zip_code} {property_obj.city_name}")
    property_obj.address = " ".join([p for p in address_parts if p])
    
    return property_obj


def import_main_building(property_id, buildings_data):
    """Import main building (first building in array)"""
    if not buildings_data or len(buildings_data) == 0:
        return None
    
    # First building is always the main building
    bldg = buildings_data[0]
    
    main_building = MainBuilding(
        property_id=property_id,
        building_name=safe_get(bldg, 'buildingName'),
        building_number=safe_get(bldg, 'buildingNumber'),
        
        # Areas
        housing_area=safe_get(bldg, 'housingArea'),
        total_area=safe_get(bldg, 'totalArea'),
        basement_area=safe_get(bldg, 'basementArea'),
        business_area=safe_get(bldg, 'businessArea'),
        other_area=safe_get(bldg, 'otherArea'),
        
        # Rooms (only main building has these)
        number_of_rooms=safe_get(bldg, 'numberOfRooms'),
        number_of_floors=safe_get(bldg, 'numberOfFloors'),
        number_of_bathrooms=safe_get(bldg, 'numberOfBathrooms'),
        number_of_kitchens=safe_get(bldg, 'numberOfKitchens'),
        number_of_toilets=safe_get(bldg, 'numberOfToilets'),
        
        # Conditions (only main building has these)
        bathroom_condition=safe_get(bldg, 'bathroomCondition'),
        kitchen_condition=safe_get(bldg, 'kitchenCondition'),
        toilet_condition=safe_get(bldg, 'toiletCondition'),
        
        # Materials
        external_wall_material=safe_get(bldg, 'externalWallMaterial'),
        supplementary_external_wall_material=safe_get(bldg, 'supplementaryExternalWallMaterial'),
        roofing_material=safe_get(bldg, 'roofingMaterial'),
        supplementary_roofing_material=safe_get(bldg, 'supplementaryRoofingMaterial'),
        
        # Heating
        heating_installation=safe_get(bldg, 'heatingInstallation'),
        supplementary_heating=safe_get(bldg, 'supplementaryHeating'),
        
        # Years
        year_built=safe_get(bldg, 'yearBuilt'),
        year_renovated=safe_get(bldg, 'yearRenovated'),
        
        # Asbestos
        asbestos_containing_material=safe_get(bldg, 'asbestosContainingMaterial')
    )
    
    return main_building


def import_additional_buildings(property_id, buildings_data):
    """Import additional buildings (garages, carports, sheds, etc.)"""
    if not buildings_data or len(buildings_data) <= 1:
        return []
    
    additional_building_objs = []
    
    # Skip first building (main building), process the rest
    for bldg in buildings_data[1:]:
        additional_building = AdditionalBuilding(
            property_id=property_id,
            building_name=safe_get(bldg, 'buildingName'),
            building_number=safe_get(bldg, 'buildingNumber'),
            
            # Basic info
            total_area=safe_get(bldg, 'totalArea'),
            year_built=safe_get(bldg, 'yearBuilt'),
            
            # Materials
            external_wall_material=safe_get(bldg, 'externalWallMaterial'),
            supplementary_external_wall_material=safe_get(bldg, 'supplementaryExternalWallMaterial'),
            roofing_material=safe_get(bldg, 'roofingMaterial'),
            supplementary_roofing_material=safe_get(bldg, 'supplementaryRoofingMaterial'),
            
            # Heating (rarely present)
            heating_installation=safe_get(bldg, 'heatingInstallation')
        )
        additional_building_objs.append(additional_building)
    
    return additional_building_objs


def import_registrations(property_id, registrations_data):
    """Import all sale registrations for a property"""
    if not registrations_data:
        return []
    
    registration_objs = []
    for reg in registrations_data:
        registration = Registration(
            property_id=property_id,
            registration_id=safe_get(reg, 'registrationID'),
            amount=safe_get(reg, 'amount'),
            date=parse_date(safe_get(reg, 'date')),
            type=safe_get(reg, 'type'),
            area=safe_get(reg, 'area'),
            living_area=safe_get(reg, 'livingArea'),
            per_area_price=safe_get(reg, 'perAreaPrice'),
            municipality_code=safe_get(reg, 'municipalityCode'),
            property_number=safe_get(reg, 'propertyNumber')
        )
        registration_objs.append(registration)
    
    return registration_objs


def import_municipality(property_id, municipality_data):
    """Import municipality information"""
    if not municipality_data:
        return None
    
    return Municipality(
        property_id=property_id,
        municipality_code=safe_get(municipality_data, 'municipalityCode'),
        name=safe_get(municipality_data, 'name'),
        slug=safe_get(municipality_data, 'slug'),
        church_tax_percentage=safe_get(municipality_data, 'churchTaxPercentage'),
        council_tax_percentage=safe_get(municipality_data, 'councilTaxPercentage'),
        land_value_tax_level_per_thousand=safe_get(municipality_data, 'landValueTaxLevelPerThousand'),
        number_of_schools=safe_get(municipality_data, 'numberOfSchools'),
        population=safe_get(municipality_data, 'population')
    )


def import_province(property_id, province_data):
    """Import province information"""
    if not province_data:
        return None
    
    return Province(
        property_id=property_id,
        name=safe_get(province_data, 'name'),
        province_code=safe_get(province_data, 'provinceCode'),
        region_code=safe_get(province_data, 'regionCode'),
        slug=safe_get(province_data, 'slug')
    )


def import_road(property_id, road_data):
    """Import road information"""
    if not road_data:
        return None
    
    return Road(
        property_id=property_id,
        name=safe_get(road_data, 'name'),
        road_code=safe_get(road_data, 'roadCode'),
        road_id=safe_get(road_data, 'roadID'),
        slug=safe_get(road_data, 'slug'),
        municipality_code=safe_get(road_data, 'municipalityCode')
    )


def import_zip(property_id, zip_data):
    """Import zip code information"""
    if not zip_data:
        return None
    
    return Zip(
        property_id=property_id,
        zip_code=safe_get(zip_data, 'zipCode'),
        name=safe_get(zip_data, 'name'),
        slug=safe_get(zip_data, 'slug'),
        group=safe_get(zip_data, 'group')
    )


def import_city(property_id, city_data):
    """Import city information"""
    if not city_data:
        return None
    
    return City(
        property_id=property_id,
        name=safe_get(city_data, 'name'),
        slug=safe_get(city_data, 'slug')
    )


def import_place(property_id, place_data):
    """Import place information"""
    if not place_data:
        return None
    
    bbox = safe_get(place_data, 'bbox', [])
    coords = safe_get(place_data, 'coordinates', {})
    
    return Place(
        property_id=property_id,
        place_id=safe_get(place_data, 'id'),
        name=safe_get(place_data, 'name'),
        slug=safe_get(place_data, 'slug'),
        bbox_min_lon=bbox[0] if len(bbox) >= 4 else None,
        bbox_min_lat=bbox[1] if len(bbox) >= 4 else None,
        bbox_max_lon=bbox[2] if len(bbox) >= 4 else None,
        bbox_max_lat=bbox[3] if len(bbox) >= 4 else None,
        latitude=safe_get(coords, 'lat'),
        longitude=safe_get(coords, 'lon'),
        coordinate_type=safe_get(coords, 'type')
    )


def import_days_on_market(property_id, days_on_market_data):
    """Import days on market information"""
    if not days_on_market_data:
        return None
    
    return DaysOnMarket(
        property_id=property_id,
        realtors=safe_get(days_on_market_data, 'realtors', [])
    )


def import_cases(property_id, cases_data):
    """Import cases (listing history) for a property"""
    if not cases_data:
        return []
    
    cases = []
    for case_data in cases_data:
        # Parse dates
        created = case_data.get('created')
        modified = case_data.get('modified')
        sold = case_data.get('sold')
        
        if created:
            created = datetime.fromisoformat(created.replace('Z', '+00:00'))
        if modified:
            modified = datetime.fromisoformat(modified.replace('Z', '+00:00'))
        if sold:
            sold = datetime.fromisoformat(sold.replace('Z', '+00:00'))
        
        # Get time on market
        time_on_market = case_data.get('timeOnMarket', {})
        current_tom = time_on_market.get('current', {})
        total_tom = time_on_market.get('total', {})
        
        case = Case(
            property_id=property_id,
            case_id=case_data.get('caseID'),
            status=case_data.get('status'),
            current_price=case_data.get('priceCash'),  # FIXED: API uses 'priceCash' not 'price'
            original_price=case_data.get('originalPrice'),
            price_change_percentage=case_data.get('priceChangePercentage'),
            per_area_price=case_data.get('perAreaPrice'),
            monthly_expense=case_data.get('monthlyExpense'),
            created_date=created,
            modified_date=modified,
            sold_date=sold,
            days_on_market_current=current_tom.get('days'),
            days_on_market_total=total_tom.get('days'),
            lot_area=case_data.get('lotArea'),
            basement_area=case_data.get('basementArea'),
            year_built=case_data.get('yearBuilt'),
            description_title=case_data.get('descriptionTitle'),
            description_body=case_data.get('descriptionBody'),
            case_url=case_data.get('caseUrl'),
            provider_case_id=case_data.get('providerCaseID'),
            has_balcony=case_data.get('hasBalcony'),
            has_terrace=case_data.get('hasTerrace'),
            has_elevator=case_data.get('hasElevator'),
            highlighted=case_data.get('highlighted'),
            distinction=case_data.get('distinction'),
            realtors_info=total_tom.get('realtors', [])
        )
        
        # Import price changes for this case
        price_changes_data = case_data.get('priceChanges', [])
        for pc_data in price_changes_data:
            change_date = pc_data.get('created')
            if change_date:
                change_date = datetime.fromisoformat(change_date.replace('Z', '+00:00'))
            
            price_change = PriceChange(
                change_date=change_date,
                old_price=pc_data.get('oldPrice'),
                new_price=pc_data.get('newPrice'),
                price_change_amount=pc_data.get('priceChange')
            )
            case.price_changes.append(price_change)
        
        # Import images for this case
        images_data = case_data.get('images', [])
        for idx, image_data in enumerate(images_data):
            # Get image sources (different sizes)
            image_sources = image_data.get('imageSources', [])
            
            # We'll store two key sizes:
            # 1. 600x400 for property cards/thumbnails
            # 2. 1440x960 for detail view/gallery
            
            url_600x400 = None
            url_1440x960 = None
            alt_text = None
            
            for source in image_sources:
                # Size is an object with width/height, not a string
                size_obj = source.get('size', {})
                width = size_obj.get('width')
                height = size_obj.get('height')
                
                # Get alt text from first source
                if not alt_text:
                    alt_text = source.get('alt')
                
                # Check for our target sizes
                if width == 600 and height == 400:
                    url_600x400 = source.get('url')
                elif width == 1440 and height == 960:
                    url_1440x960 = source.get('url')
            
            # Create image records for both sizes
            if url_600x400:
                case_image_thumb = CaseImage(
                    image_url=url_600x400,
                    width=600,
                    height=400,
                    is_default=(idx == 0),  # First image is default
                    sort_order=idx,
                    alt_text=alt_text
                )
                case.images.append(case_image_thumb)
            
            if url_1440x960:
                case_image_full = CaseImage(
                    image_url=url_1440x960,
                    width=1440,
                    height=960,
                    is_default=(idx == 0),  # First image is default
                    sort_order=idx,
                    alt_text=alt_text
                )
                case.images.append(case_image_full)
        
        cases.append(case)
    
    return cases


def import_from_api(property_id):
    """Fetch property data from API and import to database"""
    
    # Fetch from API
    url = f"https://api.boligsiden.dk/addresses/{property_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        api_data = response.json()
    except Exception as e:
        print(f"Error fetching {property_id}: {e}")
        return False
    
    # Import to database
    session = Session()
    try:
        # Main property
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
        
        # Cases and price changes
        for case in import_cases(property_id, safe_get(api_data, 'cases')):
            session.add(case)
        
        session.commit()
        print(f"✓ Imported {property_id}")
        return True
        
    except Exception as e:
        session.rollback()
        print(f"✗ Error importing {property_id}: {e}")
        return False
    finally:
        session.close()


def import_from_json_file(json_path):
    """Import properties from JSON file (like api_sample_data_20251004_211357.json)"""
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    success_count = 0
    error_count = 0
    
    session = Session()
    
    for item in data:
        api_data = item.get('api')
        if not api_data:
            continue
        
        property_id = item.get('property_id')
        
        try:
            # Main property
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
            print(f"✓ Imported {property_id}")
            success_count += 1
            
        except Exception as e:
            session.rollback()
            print(f"✗ Error importing {property_id}: {e}")
            error_count += 1
    
    session.close()
    
    print(f"\nImport complete: {success_count} succeeded, {error_count} failed")


def create_tables():
    """Create all tables in the database"""
    print("Creating database tables...")
    Base.metadata.create_all(engine)
    print("✓ Tables created successfully")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Import property data from API or JSON file')
    parser.add_argument('--create-tables', action='store_true', help='Create database tables')
    parser.add_argument('--from-json', type=str, help='Import from JSON file path')
    parser.add_argument('--from-api', type=str, help='Import single property ID from API')
    parser.add_argument('--test', action='store_true', help='Test import on sample data')
    
    args = parser.parse_args()
    
    if args.create_tables:
        create_tables()
    
    if args.from_json:
        import_from_json_file(args.from_json)
    
    if args.from_api:
        import_from_api(args.from_api)
    
    if args.test:
        print("Testing import on sample data...")
        import_from_json_file('api_sample_data_20251004_211357.json')
