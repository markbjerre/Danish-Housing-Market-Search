import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Set up absolute paths
PROJECT_ROOT = Path("C:/Users/Mark BJ/Desktop/Code/housing_project")
SRC_DIR = PROJECT_ROOT / "src"

# Add the src directory to the Python path
sys.path.append(str(SRC_DIR))

from database import db
from db_models import PropertyDB, PropertyScoreDB, Base
from models import Property
from scoring import PropertyScorer

def init_database():
    """Initialize the database and load initial data"""
    print("Creating database tables...")
    
    # Drop and recreate all tables
    Base.metadata.drop_all(db.engine)
    Base.metadata.create_all(db.engine)
    
    data_file = PROJECT_ROOT / 'data' / 'properties.csv'
    print(f"Loading initial data from {data_file}...")
    df = pd.read_csv(data_file)
    
    session = db.get_session()
    scorer = PropertyScorer()
    
    try:
        # Add properties
        print("Adding properties to database...")
        for _, row in df.iterrows():
            # Create Property object for scoring
            prop = Property(
                id=row['id'],
                address=row['address'],
                price=row['price'],
                square_meters=row['square_meters'],
                property_type=row['property_type'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                listing_date=datetime.strptime(row['listing_date'], '%Y-%m-%d'),
                rooms=row['rooms'],
                year_built=row['year_built'],
                floor=row['floor']
            )
            
            # Create PropertyDB object for database
            db_prop = PropertyDB(
                id=prop.id,
                address=prop.address,
                price=prop.price,
                square_meters=prop.square_meters,
                property_type=prop.property_type,
                latitude=prop.latitude,
                longitude=prop.longitude,
                listing_date=prop.listing_date,
                rooms=prop.rooms,
                year_built=prop.year_built,
                floor=prop.floor
            )
            session.add(db_prop)
        
        # Commit properties first to get their IDs
        session.commit()
        
        # Calculate and add scores
        print("Calculating and adding property scores...")
        properties = [Property(**{
            'id': p.id,
            'address': p.address,
            'price': p.price,
            'square_meters': p.square_meters,
            'property_type': p.property_type,
            'latitude': p.latitude,
            'longitude': p.longitude,
            'listing_date': p.listing_date,
            'rooms': p.rooms,
            'year_built': p.year_built,
            'floor': p.floor
        }) for p in session.query(PropertyDB).all()]
        
        for prop in properties:
            # Calculate scores and convert NumPy float64 to Python float
            price_score = float(scorer.calculate_price_score(prop, properties) * 100)
            size_score = float(scorer.calculate_size_score(prop, properties) * 100)
            age_score = float(scorer.calculate_age_score(prop) * 100)
            location_score = float(scorer.calculate_location_score(prop) * 100)
            floor_score = float(scorer.calculate_floor_score(prop) * 100)
            days_market_score = float(scorer.calculate_days_on_market_score(prop) * 100)
            total_score = float(scorer.score_property(prop, properties))
            
            # Create score record
            score = PropertyScoreDB(
                property_id=prop.id,
                price_score=price_score,
                size_score=size_score,
                age_score=age_score,
                location_score=location_score,
                floor_score=floor_score,
                days_market_score=days_market_score,
                total_score=total_score
            )
            session.add(score)
        
        session.commit()
        print("Database initialization complete!")
        
    except Exception as e:
        print(f"Error during database initialization: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    init_database()
