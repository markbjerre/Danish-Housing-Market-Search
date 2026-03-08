from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Load 1Password env before other config
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from load_1password_env import load_1password_env
load_1password_env(Path(__file__).resolve().parents[1])

# Try relative import first, fallback to absolute
try:
    from .db_models_new import Base
except ImportError:
    from db_models_new import Base

# Load environment variables
load_dotenv()

class Database:
    def __init__(self):
        # Get database connection parameters individually
        self.db_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'housing_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        if not self.db_params['password']:
            raise ValueError("DB_PASSWORD environment variable not set")
            
        # Create connection URL
        url = f"postgresql://{self.db_params['user']}:{self.db_params['password']}@{self.db_params['host']}:{self.db_params['port']}/{self.db_params['database']}"
        self.engine = create_engine(url)
        self.Session = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        """Get a new database session"""
        return self.Session()

# Create a singleton instance
db = Database()