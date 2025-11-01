#!/usr/bin/env python3
"""
Database Backup and Export Script
Exports all 14 tables to Parquet format for portable, file-based storage.

Usage:
    python backup_database.py --export     # Export to Parquet files
    python backup_database.py --info       # Show database statistics
    python backup_database.py --test       # Test export with small sample
"""

import os
import sys
import argparse
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add src to path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.database import db
    from src.db_models_new import *
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    from database import db
    from db_models_new import *

def get_table_info():
    """Get information about all tables and their row counts"""
    session = db.get_session()
    
    tables = {
        'properties_new': Property,
        'main_buildings': MainBuilding,
        'additional_buildings': AdditionalBuilding,
        'registrations': Registration,
        'municipalities': Municipality,
        'provinces': Province,
        'cities': City,
        'zip_codes': Zip,
        'roads': Road,
        'places': Place,
        'cases': Case,
        'case_images': CaseImage,
        'price_changes': PriceChange,
        'days_on_market': DaysOnMarket
    }
    
    info = {}
    total_rows = 0
    
    print("\n📊 Database Table Statistics:")
    print("=" * 50)
    
    for table_name, model_class in tables.items():
        try:
            count = session.query(model_class).count()
            info[table_name] = count
            total_rows += count
            print(f"{table_name:20} {count:>10,} rows")
        except Exception as e:
            print(f"{table_name:20} {'ERROR':>10} - {str(e)}")
            info[table_name] = 0
    
    print("=" * 50)
    print(f"{'TOTAL':20} {total_rows:>10,} rows")
    
    session.close()
    return info

def export_table_to_parquet(table_name, model_class, output_dir, limit=None):
    """Export a single table to Parquet format"""
    session = db.get_session()
    
    try:
        # Build query
        query = session.query(model_class)
        if limit:
            query = query.limit(limit)
        
        # Get total count
        total_count = session.query(model_class).count()
        export_count = min(total_count, limit) if limit else total_count
        
        print(f"📦 Exporting {table_name}: {export_count:,} rows", end="")
        if limit and limit < total_count:
            print(f" (limited from {total_count:,})")
        else:
            print()
        
        # Execute query and get all results
        results = query.all()
        
        if not results:
            print(f"   ⚠️  No data in {table_name}")
            return None
        
        # Convert to list of dictionaries
        data = []
        for row in results:
            row_dict = {}
            for column in row.__table__.columns:
                value = getattr(row, column.name)
                # Handle special data types
                if hasattr(value, 'isoformat'):  # datetime objects
                    value = value.isoformat()
                row_dict[column.name] = value
            data.append(row_dict)
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Export to Parquet
        parquet_file = output_dir / f"{table_name}.parquet"
        df.to_parquet(parquet_file, index=False, engine='pyarrow')
        
        # Get file size
        file_size = parquet_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"   ✅ Saved: {parquet_file.name} ({file_size_mb:.1f} MB)")
        
        return {
            'table': table_name,
            'rows': len(data),
            'file_size_mb': file_size_mb,
            'file_path': str(parquet_file)
        }
        
    except Exception as e:
        print(f"   ❌ Error exporting {table_name}: {str(e)}")
        return None
    finally:
        session.close()

def export_all_tables(output_dir, limit=None):
    """Export all tables to Parquet format"""
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define all tables in logical order
    tables = [
        ('properties_new', Property),
        ('municipalities', Municipality),
        ('provinces', Province),
        ('cities', City),
        ('zip_codes', Zip),
        ('roads', Road),
        ('places', Place),
        ('main_buildings', MainBuilding),
        ('additional_buildings', AdditionalBuilding),
        ('registrations', Registration),
        ('cases', Case),
        ('case_images', CaseImage),
        ('price_changes', PriceChange),
        ('days_on_market', DaysOnMarket)
    ]
    
    print(f"\n🚀 Starting export to: {output_dir.absolute()}")
    if limit:
        print(f"📊 Limit: {limit:,} rows per table (test mode)")
    
    start_time = datetime.now()
    export_results = []
    
    # Export each table
    for table_name, model_class in tables:
        result = export_table_to_parquet(table_name, model_class, output_dir, limit)
        if result:
            export_results.append(result)
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    total_rows = sum(r['rows'] for r in export_results)
    total_size_mb = sum(r['file_size_mb'] for r in export_results)
    
    print(f"\n✅ Export Complete!")
    print(f"📊 Total: {total_rows:,} rows across {len(export_results)} tables")
    print(f"💾 Size: {total_size_mb:.1f} MB")
    print(f"⏱️  Duration: {duration:.1f} seconds")
    
    # Create export manifest
    manifest = {
        'export_date': datetime.now().isoformat(),
        'total_rows': total_rows,
        'total_size_mb': round(total_size_mb, 1),
        'duration_seconds': round(duration, 1),
        'tables': export_results,
        'test_mode': limit is not None,
        'limit_per_table': limit
    }
    
    manifest_file = output_dir / 'export_manifest.json'
    import json
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"📝 Manifest: {manifest_file.name}")
    
    return manifest

def main():
    parser = argparse.ArgumentParser(description='Database backup and export tool')
    parser.add_argument('--export', action='store_true', 
                       help='Export all tables to Parquet format')
    parser.add_argument('--info', action='store_true',
                       help='Show database table statistics')
    parser.add_argument('--test', action='store_true',
                       help='Test export with limited rows (1000 per table)')
    parser.add_argument('--output', default='data/backups',
                       help='Output directory for Parquet files (default: data/backups)')
    parser.add_argument('--limit', type=int,
                       help='Limit rows per table (for testing)')
    
    args = parser.parse_args()
    
    if args.info:
        get_table_info()
    
    elif args.export or args.test:
        limit = args.limit
        if args.test and not limit:
            limit = 1000  # Default test limit
        
        # Create timestamped output directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if limit:
            output_dir = Path(args.output) / f"test_export_{timestamp}"
        else:
            output_dir = Path(args.output) / f"full_export_{timestamp}"
        
        try:
            manifest = export_all_tables(output_dir, limit)
            
            if not limit:  # Full export
                print(f"\n🎉 Full database exported successfully!")
                print(f"📁 Location: {output_dir.absolute()}")
                print(f"📋 Use these files with the file-based webapp variant")
                
        except Exception as e:
            print(f"\n❌ Export failed: {str(e)}")
            sys.exit(1)
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()