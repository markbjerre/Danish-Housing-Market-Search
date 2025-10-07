"""
Drop and recreate all database tables
"""

import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
import sys

# Load environment
load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db_models_new import Base

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'housing_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

print("Dropping all tables...")
from sqlalchemy import text
with engine.connect() as conn:
    # Drop tables with CASCADE to handle old dependencies
    tables = ['days_on_market', 'places', 'cities', 'zip_codes', 'roads', 
              'provinces', 'municipalities', 'registrations', 
              'additional_buildings', 'main_buildings', 'buildings', 'properties_new']
    for table in tables:
        conn.execute(text(f'DROP TABLE IF EXISTS {table} CASCADE'))
    conn.commit()
print("✓ Tables dropped")

print("\nCreating tables with new schema...")
Base.metadata.create_all(engine)
print("✓ Tables created")

print("\n✓ Database reset complete - ready for fresh import")
