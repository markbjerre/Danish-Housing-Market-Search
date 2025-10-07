"""
Enhanced Database Models - Captures ALL fields from Boligsiden API
Created: October 4, 2025
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Property(Base):
    """Main property table - core information"""
    __tablename__ = 'properties_new'

    # Primary identification
    id = Column(String, primary_key=True)  # addressID
    address = Column(String)
    address_type = Column(String)  # villa, condo, etc.
    
    # Location
    road_name = Column(String)
    house_number = Column(String)
    door = Column(String)
    floor = Column(String)
    city_name = Column(String)
    zip_code = Column(Integer)
    place_name = Column(String)  # e.g., "Hf. Sundbyvester"
    
    # Coordinates
    latitude = Column(Float)
    longitude = Column(Float)
    coordinate_type = Column(String)  # EPSG4326
    
    # Property details
    living_area = Column(Float)
    weighted_area = Column(Float)
    latest_valuation = Column(Float)
    property_number = Column(Integer)
    
    # Status flags
    is_on_market = Column(Boolean)
    is_public = Column(Boolean)
    allow_new_valuation_info = Column(Boolean)
    
    # Energy
    energy_label = Column(String)
    
    # IDs and codes
    entry_address_id = Column(String)
    gstkvhx = Column(String)  # Government property code
    
    # URLs and slugs
    slug = Column(String)
    slug_address = Column(String)
    api_href = Column(String)
    
    # BFE Numbers (stored as JSON array)
    bfe_numbers = Column(JSON, nullable=True)
    
    # Latest sold case description
    latest_sold_case_title = Column(Text)
    latest_sold_case_body = Column(Text)
    latest_sold_case_date = Column(DateTime)
    
    # Boligsiden specific info
    boligsiden_latest_sold_area = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    main_building = relationship("MainBuilding", back_populates="property", uselist=False, cascade="all, delete-orphan")
    additional_buildings = relationship("AdditionalBuilding", back_populates="property", cascade="all, delete-orphan")
    registrations = relationship("Registration", back_populates="property", cascade="all, delete-orphan")
    municipality_info = relationship("Municipality", back_populates="property", uselist=False, cascade="all, delete-orphan")
    province_info = relationship("Province", back_populates="property", uselist=False, cascade="all, delete-orphan")
    road_info = relationship("Road", back_populates="property", uselist=False, cascade="all, delete-orphan")
    zip_info = relationship("Zip", back_populates="property", uselist=False, cascade="all, delete-orphan")
    city_info = relationship("City", back_populates="property", uselist=False, cascade="all, delete-orphan")
    place_info = relationship("Place", back_populates="property", uselist=False, cascade="all, delete-orphan")
    days_on_market_info = relationship("DaysOnMarket", back_populates="property", uselist=False, cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="property", cascade="all, delete-orphan")


class MainBuilding(Base):
    """Main building/house information - one per property"""
    __tablename__ = 'main_buildings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String, ForeignKey('properties_new.id'), unique=True, nullable=False)
    
    # Building identification
    building_name = Column(String)  # "Fritliggende enfamilieshus (parcelhus)"
    building_number = Column(String)
    
    # Areas
    housing_area = Column(Float)
    total_area = Column(Float)
    basement_area = Column(Float)
    business_area = Column(Float)
    other_area = Column(Float)
    
    # Rooms and facilities (only main building has this detail)
    number_of_rooms = Column(Integer)
    number_of_floors = Column(Integer)
    number_of_bathrooms = Column(Integer)
    number_of_kitchens = Column(Integer)
    number_of_toilets = Column(Integer)
    
    # Conditions (only main building has this detail)
    bathroom_condition = Column(String)
    kitchen_condition = Column(String)
    toilet_condition = Column(String)
    
    # Materials
    external_wall_material = Column(String)
    supplementary_external_wall_material = Column(String)
    roofing_material = Column(String)
    supplementary_roofing_material = Column(String)
    
    # Heating
    heating_installation = Column(String)
    supplementary_heating = Column(String)
    
    # Years
    year_built = Column(Integer)
    year_renovated = Column(Integer)
    
    # Asbestos warning
    asbestos_containing_material = Column(String)
    
    # Relationship
    property = relationship("Property", back_populates="main_building")


class AdditionalBuilding(Base):
    """Additional buildings - garages, carports, sheds, etc."""
    __tablename__ = 'additional_buildings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String, ForeignKey('properties_new.id'), nullable=False)
    
    # Building identification
    building_name = Column(String)  # "Garage", "Carport", "Udhus", etc.
    building_number = Column(String)
    
    # Basic info (most additional buildings only have this)
    total_area = Column(Float)
    year_built = Column(Integer)
    
    # Materials
    external_wall_material = Column(String)
    supplementary_external_wall_material = Column(String)
    roofing_material = Column(String)
    supplementary_roofing_material = Column(String)
    
    # Heating (rarely present for additional buildings)
    heating_installation = Column(String)
    
    # Relationship
    property = relationship("Property", back_populates="additional_buildings")


class Registration(Base):
    """Sale/transaction registrations - multiple per property"""
    __tablename__ = 'registrations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String, ForeignKey('properties_new.id'), nullable=False)
    
    # Registration details
    registration_id = Column(String, unique=True)  # UUID from API
    amount = Column(Float)
    date = Column(DateTime)
    type = Column(String)  # normal, family, auction, other
    
    # Areas at time of sale
    area = Column(Float)
    living_area = Column(Float)
    
    # Pricing
    per_area_price = Column(Float)  # kr per sqm
    
    # Location codes
    municipality_code = Column(Integer)
    property_number = Column(Integer)
    
    # Relationship
    property = relationship("Property", back_populates="registrations")


class Municipality(Base):
    """Municipality information"""
    __tablename__ = 'municipalities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String, ForeignKey('properties_new.id'), unique=True, nullable=False)
    
    municipality_code = Column(Integer)
    name = Column(String)
    slug = Column(String)
    
    # Tax rates
    church_tax_percentage = Column(Float)
    council_tax_percentage = Column(Float)
    land_value_tax_level_per_thousand = Column(Float)
    
    # Statistics
    number_of_schools = Column(Integer)
    population = Column(Integer)
    
    # Relationship
    property = relationship("Property", back_populates="municipality_info")


class Province(Base):
    """Province/region information"""
    __tablename__ = 'provinces'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String, ForeignKey('properties_new.id'), unique=True, nullable=False)
    
    name = Column(String)
    province_code = Column(String)  # e.g., "DK011"
    region_code = Column(Integer)
    slug = Column(String)
    
    # Relationship
    property = relationship("Property", back_populates="province_info")


class Road(Base):
    """Road information"""
    __tablename__ = 'roads'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String, ForeignKey('properties_new.id'), unique=True, nullable=False)
    
    name = Column(String)
    road_code = Column(Integer)
    road_id = Column(String)  # UUID
    slug = Column(String)
    municipality_code = Column(Integer)
    
    # Relationship
    property = relationship("Property", back_populates="road_info")


class Zip(Base):
    """Zip code information"""
    __tablename__ = 'zip_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String, ForeignKey('properties_new.id'), unique=True, nullable=False)
    
    zip_code = Column(Integer)
    name = Column(String)
    slug = Column(String)
    group = Column(Integer)  # Some zip codes have groups (e.g., 1000 group for København K)
    
    # Relationship
    property = relationship("Property", back_populates="zip_info")


class City(Base):
    """City information"""
    __tablename__ = 'cities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String, ForeignKey('properties_new.id'), unique=True, nullable=False)
    
    name = Column(String)
    slug = Column(String)
    
    # Relationship
    property = relationship("Property", back_populates="city_info")


class Place(Base):
    """Place information (e.g., neighborhood, subdivision)"""
    __tablename__ = 'places'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String, ForeignKey('properties_new.id'), unique=True, nullable=False)
    
    place_id = Column(Integer)
    name = Column(String)
    slug = Column(String)
    
    # Bounding box coordinates
    bbox_min_lon = Column(Float)
    bbox_min_lat = Column(Float)
    bbox_max_lon = Column(Float)
    bbox_max_lat = Column(Float)
    
    # Center coordinates
    latitude = Column(Float)
    longitude = Column(Float)
    coordinate_type = Column(String)
    
    # Relationship
    property = relationship("Property", back_populates="place_info")


class DaysOnMarket(Base):
    """Days on market tracking"""
    __tablename__ = 'days_on_market'

    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String, ForeignKey('properties_new.id'), unique=True, nullable=False)
    
    # Realtors info stored as JSON (can be empty array or list of realtor objects)
    realtors = Column(JSON)
    
    # Relationship
    property = relationship("Property", back_populates="days_on_market_info")


class Case(Base):
    """Property listing cases - tracks each time property goes on/off market"""
    __tablename__ = 'cases'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(String, ForeignKey('properties_new.id'), nullable=False)
    
    # Case identification
    case_id = Column(String, unique=True, nullable=False)  # UUID from API
    status = Column(String)  # "open", "sold", "withdrawn"
    
    # Pricing
    current_price = Column(Float)
    original_price = Column(Float)
    price_change_percentage = Column(Float)  # NEW: Percentage change from original price
    per_area_price = Column(Float)  # NEW: Price per square meter
    monthly_expense = Column(Float)  # NEW: Monthly ownership costs
    
    # Dates
    created_date = Column(DateTime)  # When listing was created (offered for sale)
    modified_date = Column(DateTime)
    sold_date = Column(DateTime)
    
    # Market tracking
    days_on_market_current = Column(Integer)
    days_on_market_total = Column(Integer)
    
    # Property characteristics (from case data)
    lot_area = Column(Float)  # NEW: Lot/land area in sqm
    basement_area = Column(Float)  # NEW: Basement area in sqm
    year_built = Column(Integer)  # NEW: Construction year (duplicates property, but from case)
    
    # Description
    description_title = Column(String)  # NEW: Marketing title
    description_body = Column(Text)  # NEW: Full listing description
    
    # URLs and IDs
    case_url = Column(String)  # NEW: Direct URL to listing on Boligsiden
    provider_case_id = Column(String)  # NEW: External provider's case ID
    
    # Features
    has_balcony = Column(Boolean)  # NEW: Has balcony
    has_terrace = Column(Boolean)  # NEW: Has terrace
    has_elevator = Column(Boolean)  # NEW: Has elevator
    
    # Marketing
    highlighted = Column(Boolean)  # NEW: Premium/highlighted listing
    distinction = Column(String)  # NEW: Special distinction/badge
    
    # Realtor info for this case (JSON array)
    realtors_info = Column(JSON)
    
    # Timestamps
    imported_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    property = relationship("Property", back_populates="cases")
    price_changes = relationship("PriceChange", back_populates="case", cascade="all, delete-orphan")
    images = relationship("CaseImage", back_populates="case", cascade="all, delete-orphan")  # NEW


class PriceChange(Base):
    """Price change history for each case"""
    __tablename__ = 'price_changes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False)
    
    # Change details
    change_date = Column(DateTime)
    old_price = Column(Float)
    new_price = Column(Float)
    price_change_amount = Column(Float)  # Negative for reduction
    
    # Timestamps
    imported_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    case = relationship("Case", back_populates="price_changes")


class CaseImage(Base):
    """Images for property listings - stores URLs to Boligsiden CDN"""
    __tablename__ = 'case_images'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey('cases.id', ondelete='CASCADE'), nullable=False)
    
    # Image details
    image_url = Column(String, nullable=False)  # URL to image on Boligsiden CDN
    width = Column(Integer, nullable=False)  # Image width in pixels
    height = Column(Integer, nullable=False)  # Image height in pixels
    
    # Organization
    is_default = Column(Boolean, default=False)  # Primary image for listing
    sort_order = Column(Integer, default=0)  # Display order
    alt_text = Column(String)  # Accessibility description
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    case = relationship("Case", back_populates="images")


# Summary: New schema captures ALL API fields across 14 tables:
# 1. Property (main table) - 30+ core fields
# 2. Building - Multiple buildings per property with full details
# 3. Registration - Complete sale history
# 4. Municipality - Tax rates and statistics
# 5. Province - Regional information
# 6. Road - Road details and codes
# 7. Zip - Zip code information
# 8. City - City name and slug
# 9. Place - Neighborhood/subdivision with bbox
# 10. DaysOnMarket - Market tracking
# 11. Case - Listing cases with status and dates
# 12. PriceChange - Price change history per case
