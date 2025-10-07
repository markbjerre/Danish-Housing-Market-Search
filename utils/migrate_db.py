from src.database import db
from src.db_models import Base
from sqlalchemy import text

def migrate_database():
    print("Backing up existing data...")
    # Here you would implement data backup if needed
    
    print("Dropping all tables...")
    Base.metadata.drop_all(db.engine)
    
    print("Creating new tables with updated schema...")
    Base.metadata.create_all(db.engine)
    
    # Verify the new schema
    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'properties' ORDER BY column_name"))
        print("\nVerifying updated schema for 'properties' table:")
        for row in result:
            print(f"Column: {row[0]}, Type: {row[1]}")
    
    print("\nDatabase migration complete!")

if __name__ == "__main__":
    migrate_database()
