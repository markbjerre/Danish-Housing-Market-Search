"""Property data processing utilities for Boligsiden scraper"""
from typing import Dict, Any, Optional
from datetime import datetime

def get_bool_value(data: dict, key: str) -> bool:
    """Extract boolean value with proper default"""
    val = data.get(key)
    return bool(val) if val is not None else False

def get_nested_value(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary value"""
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key, default)
        if data is None:
            return default
    return data

def extract_registration_data(registrations: list) -> Dict[str, Any]:
    """Extract latest registration data from list"""
    if not registrations:
        return {}
    # Sort by date descending
    sorted_regs = sorted(registrations, 
                        key=lambda x: x.get('date', ''), 
                        reverse=True)
    latest = sorted_regs[0] if sorted_regs else {}
    return {
        'latest_registration_date': latest.get('date'),
        'latest_registration_amount': latest.get('amount'),
        'latest_registration_type': latest.get('type'),
        'price_per_sqm': latest.get('perAreaPrice')
    }

def extract_property_data(address_data: dict) -> Dict[str, Any]:
    """Extract comprehensive property data from API response"""
    # Get primary building data
    buildings = address_data.get('buildings', [{}])
    building_data = buildings[0] if buildings else {}
    
    # Get registration data
    reg_data = extract_registration_data(address_data.get('registrations', []))
    
    # Get nested municipality data
    municipality = address_data.get('municipality', {})
    
    # Extract coordinates
    coordinates = address_data.get('coordinates', {})
    
    return {
        # Basic Identification
        'id': address_data.get('addressID'),
        'address': address_data.get('address'),
        'property_type': address_data.get('addressType'),
        
        # Location Details
        'municipality': get_nested_value(address_data, 'municipality', 'name'),
        'city': get_nested_value(address_data, 'city', 'name'),
        'zip_code': address_data.get('zipCode'),
        'latitude': coordinates.get('lat'),
        'longitude': coordinates.get('lon'),
        'road_name': address_data.get('roadName'),
        'house_number': address_data.get('houseNumber'),
        'floor': address_data.get('floor'),
        'door': address_data.get('door'),
        
        # Property Characteristics
        'price': reg_data.get('latest_registration_amount'),
        'price_per_sqm': reg_data.get('price_per_sqm'),
        'square_meters': address_data.get('weightedArea'),
        'housing_area': building_data.get('housingArea'),
        'total_area': building_data.get('totalArea'),
        'basement_area': building_data.get('basementArea'),
        'rooms': building_data.get('numberOfRooms'),
        'number_of_floors': building_data.get('numberOfFloors'),
        'number_of_bathrooms': building_data.get('numberOfBathrooms'),
        'number_of_toilets': building_data.get('numberOfToilets'),
        
        # Building Details
        'year_built': building_data.get('yearBuilt'),
        'year_renovated': building_data.get('yearRenovated'),
        'heating_type': building_data.get('heatingInstallation'),
        'building_type': building_data.get('buildingName'),
        'external_wall_material': building_data.get('externalWallMaterial'),
        'roofing_material': building_data.get('roofingMaterial'),
        'kitchen_condition': building_data.get('kitchenCondition'),
        'bathroom_condition': building_data.get('bathroomCondition'),
        'energy_label': address_data.get('energyLabel'),
        
        # Additional Features
        'has_garage': get_bool_value(building_data, 'hasGarage'),
        'has_basement': bool(building_data.get('basementArea')),
        'has_elevator': get_bool_value(building_data, 'hasElevator'),
        'supplementary_heating': building_data.get('supplementaryHeating'),
        
        # Dates and Status
        'listing_date': reg_data.get('latest_registration_date'),
        'last_modified_date': address_data.get('lastModified'),
        
        # Municipality Data
        'municipality_code': municipality.get('municipalityCode'),
        'council_tax_percentage': municipality.get('councilTaxPercentage'),
        'church_tax_percentage': municipality.get('churchTaxPercentage'),
        'land_value_tax_level': municipality.get('landValueTaxLevelPerThousand')
    }
