from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Create base class for declarative models
Base = declarative_base()

class PropertyDB(Base):
    __tablename__ = 'properties'

    # Basic Identification
    id = Column(String, primary_key=True)  # UUID-style addressID from API
    address = Column(String)
    property_type = Column(String)  # villa, condo, terraced house, etc.
    
    # Location Details
    municipality = Column(String)
    city = Column(String)
    zip_code = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    road_name = Column(String)
    house_number = Column(String)
    floor = Column(Integer)
    door = Column(String)  # tv, th, etc.
    
    # Property Characteristics
    price = Column(Float)
    price_per_sqm = Column(Float)
    square_meters = Column(Float)
    housing_area = Column(Float)  # From buildings.housingArea
    total_area = Column(Float)   # From buildings.totalArea
    basement_area = Column(Float)  # From buildings.basementArea
    rooms = Column(Integer)
    number_of_floors = Column(Integer)
    number_of_bathrooms = Column(Integer)
    number_of_toilets = Column(Integer)
    
    # Building Details
    year_built = Column(Integer)
    year_renovated = Column(Integer)
    heating_type = Column(String)  # From buildings.heatingInstallation
    building_type = Column(String)  # From buildings.buildingName
    external_wall_material = Column(String)
    roofing_material = Column(String)
    kitchen_condition = Column(String)
    bathroom_condition = Column(String)
    energy_label = Column(String)
    
    # Additional Features
    has_garage = Column(String)
    has_basement = Column(String)
    has_elevator = Column(String)
    supplementary_heating = Column(String)
    
    # Dates and Status
    listing_date = Column(DateTime)
    last_modified_date = Column(DateTime)
    
    # Municipality Data
    municipality_code = Column(Integer)
    council_tax_percentage = Column(Float)
    church_tax_percentage = Column(Float)
    land_value_tax_level = Column(Float)
    
    # Relationships
    scores = relationship("PropertyScoreDB", back_populates="property")

class PropertyScoreDB(Base):
    __tablename__ = 'property_scores'

    id = Column(Integer, primary_key=True)
    property_id = Column(String, ForeignKey('properties.id'))  # Changed to String to match PropertyDB.id
    price_score = Column(Float)
    size_score = Column(Float)
    age_score = Column(Float)
    location_score = Column(Float)
    floor_score = Column(Float)
    days_market_score = Column(Float)
    total_score = Column(Float)
    property = relationship("PropertyDB", back_populates="scores")
