"""
Update database schema to add new Case fields and CaseImage table
Run this before re-importing case data
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from db_models_new import Base, CaseImage

# Database connection
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'housing_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

def update_schema():
    """Add new columns to cases table and create case_images table"""
    
    print("=" * 80)
    print("DATABASE SCHEMA UPDATE")
    print("=" * 80)
    print()
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            print("Step 1: Adding new columns to cases table...")
            
            # Add new columns to cases table
            new_columns = [
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS price_change_percentage FLOAT",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS per_area_price FLOAT",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS monthly_expense FLOAT",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS lot_area FLOAT",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS basement_area FLOAT",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS year_built INTEGER",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS description_title VARCHAR",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS description_body TEXT",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS case_url VARCHAR",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS provider_case_id VARCHAR",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS has_balcony BOOLEAN",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS has_terrace BOOLEAN",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS has_elevator BOOLEAN",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS highlighted BOOLEAN",
                "ALTER TABLE cases ADD COLUMN IF NOT EXISTS distinction VARCHAR"
            ]
            
            for i, sql in enumerate(new_columns, 1):
                print(f"  {i}/{len(new_columns)}: {sql.split('ADD COLUMN IF NOT EXISTS')[1].split()[0]}")
                conn.execute(text(sql))
            
            print("✅ Added 15 new columns to cases table")
            print()
            
            print("Step 2: Creating case_images table...")
            
            # Create case_images table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS case_images (
                id SERIAL PRIMARY KEY,
                case_id INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
                image_url VARCHAR NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                is_default BOOLEAN DEFAULT FALSE,
                sort_order INTEGER DEFAULT 0,
                alt_text VARCHAR,
                created_at TIMESTAMP DEFAULT NOW()
            )
            """
            conn.execute(text(create_table_sql))
            print("✅ Created case_images table")
            print()
            
            print("Step 3: Creating indexes...")
            
            # Create indexes for performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_case_images_case_id ON case_images(case_id)",
                "CREATE INDEX IF NOT EXISTS idx_case_images_default ON case_images(is_default) WHERE is_default = TRUE"
            ]
            
            for sql in indexes:
                conn.execute(text(sql))
            
            print("✅ Created indexes on case_images table")
            print()
            
            # Commit transaction
            trans.commit()
            
            print("=" * 80)
            print("✅ SCHEMA UPDATE COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print()
            print("Summary:")
            print("  • Added 15 new fields to cases table")
            print("  • Created case_images table with 9 fields")
            print("  • Created 2 indexes for performance")
            print()
            print("Next steps:")
            print("  1. Test import with single property")
            print("  2. Re-import all cases to populate new data")
            print()
            
        except Exception as e:
            trans.rollback()
            print(f"❌ ERROR: {e}")
            print("Schema update rolled back")
            raise

if __name__ == "__main__":
    update_schema()
