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
        
        print(f"📁 Loading data from: {self.export_dir}")
        print(f"📊 Export date: {self.manifest['export_date']}")
        print(f"📋 Tables: {len(self.manifest['tables'])}")
    
    def _load_tables(self):
        """Load all Parquet files into memory as DataFrames"""
        print("🔄 Loading tables into memory...")
        
        for table_info in self.manifest['tables']:
            table_name = table_info['table']
            file_path = self.export_dir / f"{table_name}.parquet"
            
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    self.tables[table_name] = df
                    print(f"   ✅ {table_name}: {len(df):,} rows")
                except Exception as e:
                    print(f"   ❌ Error loading {table_name}: {e}")
            else:
                print(f"   ⚠️  Missing: {file_path}")
        
        print(f"✅ Loaded {len(self.tables)} tables")
    
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
        
        # Determine price column
        price_column = 'current_price_case' if 'current_price_case' in df.columns else 'latest_valuation'
        
        # ALWAYS filter out properties with no price (N/A)
        df = df[df[price_column].notna()]
        
        # Municipality filter
        if filters.get('municipality') and filters['municipality'] != 'all':
            df = df[df['name_muni'] == filters['municipality']]
        
        # Price filters (use case price if available, otherwise latest_valuation)
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
        import numpy as np
        results = []
        
        # Determine price column
        price_column = 'current_price_case' if 'current_price_case' in df.columns else 'latest_valuation'
        
        for _, row in df.iterrows():
            # Calculate price per sqm
            price_per_sqm = None
            if pd.notna(row[price_column]) and pd.notna(row['living_area']) and row['living_area'] > 0:
                price_per_sqm = round(row[price_column] / row['living_area'], 2)
            
            # Helper function to convert NaN to None for JSON serialization
            def safe_value(val):
                if pd.isna(val) or (isinstance(val, float) and np.isnan(val)):
                    return None
                if isinstance(val, (np.integer, np.floating)):
                    return float(val) if isinstance(val, np.floating) else int(val)
                if isinstance(val, (np.bool_, bool)):
                    return bool(val)
                return val
            
            # Format property data
            prop_data = {
                'id': safe_value(row.get('id')),
                'address': f"{safe_value(row.get('road_name', '')) or ''} {safe_value(row.get('house_number', '')) or ''}".strip(),
                'city': safe_value(row.get('city_name')) or 'N/A',
                'zip_code': safe_value(row.get('zip_code')) or 'N/A',
                'municipality': safe_value(row.get('name_muni')) or 'N/A',
                'price': safe_value(row.get(price_column)),
                'living_area': safe_value(row.get('living_area')),
                'price_per_sqm': price_per_sqm,
                'rooms': safe_value(row.get('number_of_rooms_building')),
                'year_built': safe_value(row.get('year_built_building')),
                'energy_label': safe_value(row.get('energy_label')),
                'is_on_market': safe_value(row.get('is_on_market', False)),
                'latitude': safe_value(row.get('latitude')),
                'longitude': safe_value(row.get('longitude')),
                'days_on_market': safe_value(row.get('days_on_market_current_case')),
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
    
    def get_detailed_property_by_id(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive detailed property information including all related data"""
        try:
            properties = self.get_table('properties_new')
            prop = properties[properties['id'] == property_id]
            
            if prop.empty:
                return None
            
            # Start building comprehensive data
            row = prop.iloc[0]
            price_column = 'current_price_case' if 'current_price_case' in prop.columns else 'latest_valuation'
            
            def safe_value(val):
                if pd.isna(val) or (isinstance(val, float) and np.isnan(val)):
                    return None
                if isinstance(val, (np.integer, np.floating)):
                    return float(val) if isinstance(val, np.floating) else int(val)
                if isinstance(val, (np.bool_, bool)):
                    return bool(val)
                return val
            
            # Basic property info
            detailed_data = {
                'id': safe_value(row.get('id')),
                'address': f"{safe_value(row.get('road_name', '')) or ''} {safe_value(row.get('house_number', '')) or ''}".strip(),
                'city': safe_value(row.get('city_name')) or 'N/A',
                'zip_code': safe_value(row.get('zip_code')) or 'N/A',
                'municipality': safe_value(row.get('name_muni')) or 'N/A',
                'price': safe_value(row.get(price_column)),
                'living_area': safe_value(row.get('living_area')),
                'price_per_sqm': None,
                'rooms': safe_value(row.get('number_of_rooms_building')),
                'year_built': safe_value(row.get('year_built_building')),
                'energy_label': safe_value(row.get('energy_label')),
                'is_on_market': safe_value(row.get('is_on_market', False)),
                'latitude': safe_value(row.get('latitude')),
                'longitude': safe_value(row.get('longitude')),
                'days_on_market': safe_value(row.get('days_on_market_current_case')),
            }
            
            # Calculate price per sqm
            if detailed_data['price'] and detailed_data['living_area'] and detailed_data['living_area'] > 0:
                detailed_data['price_per_sqm'] = round(detailed_data['price'] / detailed_data['living_area'], 2)
            
            # Main building details
            try:
                if 'main_buildings' in self.tables:
                    main_building_id = safe_value(row.get('property_id_building'))
                    if main_building_id:
                        building = self.tables['main_buildings'][self.tables['main_buildings']['id'] == main_building_id]
                        if not building.empty:
                            b_row = building.iloc[0]
                            detailed_data['main_building'] = {
                                'building_name': safe_value(b_row.get('type_building')),
                                'year_built': safe_value(b_row.get('year_built')),
                                'year_renovated': safe_value(b_row.get('year_renovated')),
                                'number_of_floors': safe_value(b_row.get('number_of_floors')),
                                'number_of_rooms': safe_value(b_row.get('number_of_rooms')),
                                'number_of_bathrooms': safe_value(b_row.get('number_of_bathrooms')),
                                'number_of_toilets': safe_value(b_row.get('number_of_toilets')),
                                'housing_area': safe_value(b_row.get('housing_area')),
                                'basement_area': safe_value(b_row.get('basement_area')),
                                'total_area': safe_value(b_row.get('total_area')),
                                'external_wall_material': safe_value(b_row.get('external_wall_material')),
                                'roofing_material': safe_value(b_row.get('roofing_material')),
                                'heating_installation': safe_value(b_row.get('heating_installation')),
                                'supplementary_heating': safe_value(b_row.get('supplementary_heating')),
                                'kitchen_condition': safe_value(b_row.get('kitchen_condition')),
                                'bathroom_condition': safe_value(b_row.get('bathroom_condition')),
                            }
            except Exception as e:
                print(f"Error getting building details: {e}")
            
            # Registration history
            registrations = []
            try:
                if 'registrations' in self.tables:
                    reg_data = self.tables['registrations'][self.tables['registrations']['property_id'] == safe_value(row.get('id'))]
                    if not reg_data.empty:
                        # Sort by available date column (try multiple names)
                        date_col = None
                        for col in ['date_registration', 'date', 'created_date', 'registration_date']:
                            if col in reg_data.columns:
                                date_col = col
                                break
                        
                        if date_col:
                            reg_data = reg_data.sort_values(date_col, ascending=False).head(10)
                            for _, reg_row in reg_data.iterrows():
                                amount_col = None
                                for col in ['amount', 'price', 'value']:
                                    if col in reg_row.index and pd.notna(reg_row.get(col)):
                                        amount_col = col
                                        break
                                
                                type_col = None
                                for col in ['type_transaction', 'transaction_type', 'type']:
                                    if col in reg_row.index and pd.notna(reg_row.get(col)):
                                        type_col = col
                                        break
                                
                                registrations.append({
                                    'date': str(safe_value(reg_row.get(date_col)))[:10] if reg_row.get(date_col) else 'N/A',
                                    'amount': safe_value(reg_row.get(amount_col)) if amount_col else None,
                                    'type': safe_value(reg_row.get(type_col)) if type_col else 'Transaction',
                                })
            except Exception as e:
                print(f"Error getting registrations: {e}")
            
            detailed_data['registrations'] = registrations
            
            # Municipality details
            try:
                if 'municipalities' in self.tables:
                    muni_data = self.tables['municipalities'][self.tables['municipalities']['name'] == detailed_data['municipality']]
                    if not muni_data.empty:
                        m_row = muni_data.iloc[0]
                        detailed_data['municipality_info'] = {
                            'name': safe_value(m_row.get('name')),
                            'population': safe_value(m_row.get('population')),
                            'council_tax': safe_value(m_row.get('council_tax')),
                            'church_tax': safe_value(m_row.get('church_tax')),
                            'number_of_schools': safe_value(m_row.get('number_of_schools')),
                        }
            except Exception as e:
                print(f"Error getting municipality info: {e}")
            
            # Case/listing information
            try:
                if 'cases' in self.tables:
                    case_data = self.tables['cases'][self.tables['cases']['property_id'] == safe_value(row.get('id'))]
                    if not case_data.empty:
                        # Get most recent case
                        case_data = case_data.sort_values('created_date', ascending=False)
                        c_row = case_data.iloc[0]
                        detailed_data['case_info'] = {
                            'listing_date': str(safe_value(c_row.get('created_date')))[:10] if c_row.get('created_date') else 'N/A',
                            'current_price': safe_value(c_row.get('current_price')),
                            'previous_price': safe_value(c_row.get('previous_price')),
                            'status': safe_value(c_row.get('status')),
                        }
            except Exception as e:
                print(f"Error getting case info: {e}")
            
            return detailed_data
        except Exception as e:
            print(f"Error in get_detailed_property_by_id: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def text_search(self, query: str) -> pd.DataFrame:
        """
        Perform free-text search across address, city, municipality, and other relevant fields.
        Uses vectorized pandas string operations for efficiency.
        """
        if not query or len(query.strip()) < 2:
            return pd.DataFrame()
        
        # Start with properties table
        df = self.get_table('properties_new').copy()
        
        # Join with related tables for complete data
        df = self._join_property_data(df)
        
        # Prepare search string - case insensitive
        search_term = query.strip().lower()
        
        # Search across multiple columns - creates boolean masks efficiently
        search_masks = []
        
        # Address components
        if 'road_name' in df.columns:
            search_masks.append(df['road_name'].fillna('').str.lower().str.contains(search_term, na=False))
        if 'city_name' in df.columns:
            search_masks.append(df['city_name'].fillna('').str.lower().str.contains(search_term, na=False))
        if 'name_muni' in df.columns:
            search_masks.append(df['name_muni'].fillna('').str.lower().str.contains(search_term, na=False))
        if 'zip_code' in df.columns:
            search_masks.append(df['zip_code'].fillna('').astype(str).str.lower().str.contains(search_term, na=False))
        
        # Combine masks with OR operation
        if search_masks:
            combined_mask = search_masks[0]
            for mask in search_masks[1:]:
                combined_mask = combined_mask | mask
            df = df[combined_mask]
        else:
            return pd.DataFrame()
        
        # Filter out properties with no price (N/A)
        price_column = 'current_price_case' if 'current_price_case' in df.columns else 'latest_valuation'
        df = df[df[price_column].notna()]
        
        return df

# Global instance for the webapp
file_db = None

def init_file_database(data_dir: str = None):
    """Initialize the file-based database"""
    global file_db
    
    if data_dir is None:
        # Look for data directory
        possible_dirs = [
            "../data/backups",  # From portable/ to data/backups
            "data/backups",     # From root
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