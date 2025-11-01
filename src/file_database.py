"""
File-Based Data Access Layer
Replaces SQLAlchemy/PostgreSQL with Pandas/Parquet for portable deployment.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from typing import Dict, List, Optional, Any
import os
import sys

def safe_print(text: str):
    """Print text safely, handling Unicode encoding issues on Windows"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace common emojis with ASCII alternatives for Windows console
        text_safe = (text
            .replace('📁', '[FOLDER]')
            .replace('📊', '[CHART]')
            .replace('📋', '[CLIPBOARD]')
            .replace('📅', '[CALENDAR]')
            .replace('🔄', '[REFRESH]')
            .replace('✅', '[OK]')
            .replace('❌', '[ERROR]')
            .replace('⚠️', '[WARNING]')
            .replace('🚀', '[ROCKET]')
            .replace('🏘️', '[HOUSES]')
            .replace('🌐', '[GLOBE]'))
        print(text_safe)

class FileBasedDatabase:
    """
    Drop-in replacement for the database layer using Parquet files.
    Provides similar interface to SQLAlchemy but uses pandas for queries.
    """
    
    def __init__(self, data_dir: str = "data/backups"):
        self.data_dir = Path(data_dir)
        self.tables = {}
        self.manifest = None
        self._load_manifest()
        self._load_tables()
    
    def _load_manifest(self):
        """Load export manifest to understand data structure"""
        manifest_files = list(self.data_dir.glob("*/export_manifest.json"))
        if not manifest_files:
            raise FileNotFoundError(f"No export manifest found in {self.data_dir}")
        
        # Use the most recent export
        latest_manifest = max(manifest_files, key=lambda x: x.stat().st_mtime)
        self.export_dir = latest_manifest.parent
        
        with open(latest_manifest) as f:
            self.manifest = json.load(f)
        
        safe_print(f"📁 Loading data from: {self.export_dir}")
        safe_print(f"📊 Export date: {self.manifest['export_date']}")
        safe_print(f"📋 Tables: {len(self.manifest['tables'])}")
    
    def _load_tables(self):
        """Load all Parquet files into memory as DataFrames"""
        safe_print("🔄 Loading tables into memory...")
        
        for table_info in self.manifest['tables']:
            table_name = table_info['table']
            file_path = self.export_dir / f"{table_name}.parquet"
            
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    self.tables[table_name] = df
                    safe_print(f"   ✅ {table_name}: {len(df):,} rows")
                except Exception as e:
                    safe_print(f"   ❌ Error loading {table_name}: {e}")
            else:
                safe_print(f"   ⚠️  Missing: {file_path}")
        
        safe_print(f"✅ Loaded {len(self.tables)} tables")
    
    def get_table(self, table_name: str) -> pd.DataFrame:
        """Get a table as a pandas DataFrame"""
        if table_name not in self.tables:
            raise KeyError(f"Table '{table_name}' not found")
        return self.tables[table_name].copy()
    
    def search_properties(self, filters: Dict[str, Any], sort_by: str = 'latest_valuation', 
                         page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """
        Search properties with filters - main function for webapp
        Returns dict with properties, total count, and pagination info
        """
        
        # Start with properties table
        properties = self.get_table('properties_new')
        
        # Join with related tables for complete data
        properties = self._join_property_data(properties)
        
        # Apply filters
        properties = self._apply_filters(properties, filters)
        
        # Get total count before pagination
        total = len(properties)
        
        # Apply sorting
        properties = self._apply_sorting(properties, sort_by)
        
        # Apply pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_properties = properties.iloc[start_idx:end_idx]
        
        # Calculate area average price per sqm if municipality filter applied
        area_avg_price_per_sqm = self._calculate_area_average(
            properties, filters.get('municipality')
        )
        
        # Format results
        results = self._format_properties(page_properties)
        
        return {
            'properties': results,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'area_avg_price_per_sqm': area_avg_price_per_sqm
        }
    
    def _join_property_data(self, properties: pd.DataFrame) -> pd.DataFrame:
        """Join properties with related tables to get complete data"""
        
        # Join with municipalities
        if 'municipalities' in self.tables:
            municipalities = self.get_table('municipalities')
            properties = properties.merge(
                municipalities.add_suffix('_muni'), 
                left_on='id', right_on='property_id_muni', 
                how='left'
            )
        
        # Join with main buildings
        if 'main_buildings' in self.tables:
            buildings = self.get_table('main_buildings')
            properties = properties.merge(
                buildings.add_suffix('_building'), 
                left_on='id', right_on='property_id_building',
                how='left'
            )
        
        # Join with cases for price information
        if 'cases' in self.tables:
            cases = self.get_table('cases')
            # Get latest case per property (most recent by created_date)
            latest_cases = cases.sort_values('created_date').groupby('property_id').last().reset_index()
            properties = properties.merge(
                latest_cases.add_suffix('_case'),
                left_on='id', right_on='property_id_case',
                how='left'
            )
        
        return properties
    
    def _apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply search filters to the dataframe"""
        
        # Municipality filter
        if filters.get('municipality') and filters['municipality'] != 'all':
            df = df[df['name_muni'] == filters['municipality']]
        
        # Price filters (use case price if available, otherwise latest_valuation)
        price_column = 'current_price_case' if 'current_price_case' in df.columns else 'latest_valuation'
        
        if filters.get('min_price'):
            df = df[df[price_column] >= filters['min_price']]
        if filters.get('max_price'):
            df = df[df[price_column] <= filters['max_price']]
        
        # Area filters
        if filters.get('min_area'):
            df = df[df['living_area'] >= filters['min_area']]
        if filters.get('max_area'):
            df = df[df['living_area'] <= filters['max_area']]
        
        # Room filters (from buildings table)
        if filters.get('min_rooms'):
            df = df[df['number_of_rooms_building'] >= filters['min_rooms']]
        if filters.get('max_rooms'):
            df = df[df['number_of_rooms_building'] <= filters['max_rooms']]
        
        # Year built filters
        if filters.get('min_year'):
            df = df[df['year_built_building'] >= filters['min_year']]
        if filters.get('max_year'):
            df = df[df['year_built_building'] <= filters['max_year']]
        
        # On market filter
        if filters.get('on_market') is not None:
            on_market_bool = filters['on_market'].lower() == 'true' if isinstance(filters['on_market'], str) else filters['on_market']
            df = df[df['is_on_market'] == on_market_bool]
        
        return df
    
    def _apply_sorting(self, df: pd.DataFrame, sort_by: str) -> pd.DataFrame:
        """Apply sorting to the dataframe"""
        
        # Determine price column
        price_column = 'current_price_case' if 'current_price_case' in df.columns else 'latest_valuation'
        
        if sort_by == 'price_asc':
            df = df.sort_values(price_column, ascending=True, na_position='last')
        elif sort_by == 'price_desc':
            df = df.sort_values(price_column, ascending=False, na_position='last')
        elif sort_by == 'size_desc':
            df = df.sort_values('living_area', ascending=False, na_position='last')
        elif sort_by == 'year_desc':
            df = df.sort_values('year_built_building', ascending=False, na_position='last')
        elif sort_by == 'price_per_sqm_asc':
            # Calculate price per sqm
            df['price_per_sqm'] = df[price_column] / df['living_area']
            df = df.sort_values('price_per_sqm', ascending=True, na_position='last')
        else:  # default to price_desc
            df = df.sort_values(price_column, ascending=False, na_position='last')
        
        return df
    
    def _calculate_area_average(self, df: pd.DataFrame, municipality: str) -> Dict[str, float]:
        """Calculate average price per sqm for a municipality"""
        area_avg = {}
        
        if municipality and municipality != 'all':
            # Filter for on-market properties in the municipality
            price_column = 'current_price_case' if 'current_price_case' in df.columns else 'latest_valuation'
            
            filtered = df[
                (df['name_muni'] == municipality) &
                (df['is_on_market'] == True) &
                (df[price_column].notna()) &
                (df['living_area'].notna()) &
                (df['living_area'] > 0)
            ]
            
            if len(filtered) > 0:
                avg_price_per_sqm = (filtered[price_column] / filtered['living_area']).mean()
                area_avg[municipality] = round(avg_price_per_sqm, 2)
        
        return area_avg
    
    def _format_properties(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Format property data for JSON response"""
        results = []
        
        # Determine price column
        price_column = 'current_price_case' if 'current_price_case' in df.columns else 'latest_valuation'
        
        for _, row in df.iterrows():
            # Calculate price per sqm
            price_per_sqm = None
            if pd.notna(row[price_column]) and pd.notna(row['living_area']) and row['living_area'] > 0:
                price_per_sqm = round(row[price_column] / row['living_area'], 2)
            
            # Format property data
            prop_data = {
                'id': row['id'],
                'address': f"{row.get('road_name', '')} {row.get('house_number', '')}".strip(),
                'city': row.get('city_name', 'N/A'),
                'zip_code': row.get('zip_code', 'N/A'),
                'municipality': row.get('name_muni', 'N/A'),
                'price': row.get(price_column),
                'living_area': row.get('living_area'),
                'price_per_sqm': price_per_sqm,
                'rooms': row.get('number_of_rooms_building'),
                'year_built': row.get('year_built_building'),
                'energy_label': row.get('energy_label'),
                'is_on_market': row.get('is_on_market', False),
                'latitude': row.get('latitude'),
                'longitude': row.get('longitude'),
                'days_on_market': row.get('days_on_market_current_case'),
                'realtor_names': []  # Simplified for now
            }
            
            results.append(prop_data)
        
        return results
    
    def get_municipalities(self) -> List[str]:
        """Get list of all municipalities for dropdown"""
        if 'municipalities' in self.tables:
            municipalities = self.tables['municipalities']['name'].unique()
            return sorted([m for m in municipalities if pd.notna(m)])
        return []
    
    def get_property_by_id(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed property information by ID"""
        properties = self.get_table('properties_new')
        prop = properties[properties['id'] == property_id]
        
        if prop.empty:
            return None
        
        # Join with related data
        prop_with_data = self._join_property_data(prop)
        
        if prop_with_data.empty:
            return None
        
        # Format single property
        formatted = self._format_properties(prop_with_data)
        return formatted[0] if formatted else None

# Global instance for the webapp
file_db = None

def init_file_database(data_dir: str = None):
    """Initialize the file-based database"""
    global file_db
    
    if data_dir is None:
        # Look for data directory
        possible_dirs = [
            "data/backups",
            "../data/backups", 
            "backups",
            "."
        ]
        
        for dir_path in possible_dirs:
            if Path(dir_path).exists():
                data_dir = dir_path
                break
    
    if data_dir is None:
        raise FileNotFoundError("No backup data directory found. Run backup_database.py first.")
    
    file_db = FileBasedDatabase(data_dir)
    return file_db