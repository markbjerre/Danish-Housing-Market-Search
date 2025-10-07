import pandas as pd
import geopandas as gpd
from pathlib import Path
from typing import Optional, List, Union
from datetime import datetime
from .models import Property

class DataLoader:
    def __init__(self, data_dir: str = "../data"):
        self.data_dir = Path(data_dir)
        self.properties_file = self.data_dir / "properties.parquet.gzip"
    
    def save_properties(self, properties: List[Property]) -> None:
        """Save properties to a compressed parquet file"""
        df = pd.DataFrame([prop.__dict__ for prop in properties])
        df.to_parquet(self.properties_file, compression='gzip')
    
    def load_properties(self, filename: Union[str, None] = None) -> List[Property]:
        """Load property data from a CSV file"""
        df = pd.read_csv(self.data_dir / filename)
        properties = []
        
        for _, row in df.iterrows():
            property = Property(
                id=row['id'],
                address=row['address'],
                price=row['price'],
                square_meters=row['square_meters'],
                property_type=row['property_type'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                listing_date=pd.to_datetime(row['listing_date']),
                rooms=row.get('rooms'),
                year_built=row.get('year_built'),
                floor=row.get('floor')
            )
            properties.append(property)
        
        return properties
    
    def create_geodataframe(self, properties: list[Property]) -> gpd.GeoDataFrame:
        """Convert properties to a GeoDataFrame for spatial analysis"""
        df = pd.DataFrame([p.to_dict() for p in properties])
        return gpd.GeoDataFrame(
            df, 
            geometry=gpd.points_from_xy(df.longitude, df.latitude),
            crs="EPSG:4326"
        )