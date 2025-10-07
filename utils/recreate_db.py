from src.database import db
from src.db_models import Base
from sqlalchemy import text

def recreate_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(db.engine)
    
    # Make sure to dispose of the engine to close all connections
    db.engine.dispose()
    
    print("Creating all tables...")
    Base.metadata.create_all(db.engine)
    
    # Verify tables were created with correct schema
    with db.engine.connect() as conn:
        result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'properties'"))
        print("\nTable schema for 'properties':")
        for row in result:
            print(f"Column: {row[0]}, Type: {row[1]}")
            
    print("\nDatabase recreation complete!")

if __name__ == "__main__":
    recreate_database()