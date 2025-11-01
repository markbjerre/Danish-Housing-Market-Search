"""
File-Based Flask Web Application
Portable version that works with Parquet files instead of PostgreSQL.

Usage:
    python app_portable.py
    
Requirements:
    - Parquet export files in data/backups/ directory
    - Run backup_database.py first to create the files
"""

from flask import Flask, render_template, request, jsonify
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append('src')
sys.path.append('../src')

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

try:
    from src.file_database import init_file_database, file_db
except ImportError:
    from file_database import init_file_database, file_db

app = Flask(__name__)

# Initialize file-based database
try:
    file_db = init_file_database()
    safe_print("✅ File-based database initialized successfully")
except Exception as e:
    safe_print(f"❌ Failed to initialize file database: {e}")
    safe_print("📋 Make sure to run: python backup_database.py --export")
    sys.exit(1)

@app.route('/')
def index():
    """Landing page"""
    return render_template('home.html')

@app.route('/search')
def search_page():
    """Search page with filters"""
    # Get municipalities for filter dropdown
    municipalities = file_db.get_municipalities()
    return render_template('index.html', municipalities=municipalities)

@app.route('/score-calculator')
def score_calculator():
    """Score calculator page for ranking properties"""
    # Get municipalities for filter dropdown
    municipalities = file_db.get_municipalities()
    return render_template('score_calculator.html', municipalities=municipalities)

@app.route('/api/search')
def search():
    """Search properties with filters"""
    
    # Get filter parameters
    filters = {
        'municipality': request.args.get('municipality'),
        'min_price': request.args.get('min_price', type=float),
        'max_price': request.args.get('max_price', type=float),
        'min_area': request.args.get('min_area', type=float),
        'max_area': request.args.get('max_area', type=float),
        'min_rooms': request.args.get('min_rooms', type=int),
        'max_rooms': request.args.get('max_rooms', type=int),
        'min_year': request.args.get('min_year', type=int),
        'max_year': request.args.get('max_year', type=int),
        'on_market': request.args.get('on_market'),
        'realtor': request.args.get('realtor'),
        'min_days_on_market': request.args.get('min_days_on_market', type=int),
        'max_days_on_market': request.args.get('max_days_on_market', type=int)
    }
    
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    # Get pagination parameters
    sort_by = request.args.get('sort_by', 'price_desc')
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    try:
        # Search using file database
        results = file_db.search_properties(
            filters=filters,
            sort_by=sort_by,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'properties': results['properties'],
            'total': results['total'],
            'page': results['page'],
            'per_page': results['per_page'],
            'total_pages': results['total_pages'],
            'area_avg_price_per_sqm': results['area_avg_price_per_sqm']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/property/<property_id>')
def get_property(property_id):
    """Get detailed property information"""
    try:
        property_data = file_db.get_property_by_id(property_id)
        
        if property_data:
            return jsonify({
                'success': True,
                'property': property_data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Property not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    try:
        stats = {
            'total_properties': len(file_db.get_table('properties_new')),
            'municipalities': len(file_db.get_municipalities()),
            'export_date': file_db.manifest['export_date'],
            'tables_loaded': len(file_db.tables)
        }
        
        # Add table counts
        table_counts = {}
        for table_name, df in file_db.tables.items():
            table_counts[table_name] = len(df)
        
        stats['table_counts'] = table_counts
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/data-info')
def data_info():
    """Data information page"""
    try:
        stats = {
            'total_properties': len(file_db.get_table('properties_new')),
            'municipalities': len(file_db.get_municipalities()),
            'export_date': file_db.manifest['export_date'],
            'tables_loaded': len(file_db.tables),
            'export_dir': str(file_db.export_dir),
            'total_size_mb': file_db.manifest.get('total_size_mb', 'Unknown')
        }
        
        # Table information
        table_info = []
        for table_name, df in file_db.tables.items():
            table_info.append({
                'name': table_name,
                'rows': len(df),
                'columns': len(df.columns)
            })
        
        return render_template('data_info.html', stats=stats, tables=table_info)
        
    except Exception as e:
        return render_template('error.html', error=str(e))

if __name__ == '__main__':
    safe_print("\n🚀 Starting Portable Danish Housing Search")
    safe_print("=" * 50)
    safe_print(f"📊 Properties: {len(file_db.get_table('properties_new')):,}")
    safe_print(f"🏘️  Municipalities: {len(file_db.get_municipalities())}")
    safe_print(f"📁 Data from: {file_db.export_dir}")
    safe_print(f"📅 Export date: {file_db.manifest['export_date']}")
    safe_print("=" * 50)
    safe_print("🌐 Starting server at: http://127.0.0.1:5000")
    safe_print("📋 Routes available:")
    safe_print("   /          - Home page")
    safe_print("   /search    - Property search")
    safe_print("   /data-info - Data statistics")
    safe_print("=" * 50)
    
    app.run(debug=True, host='127.0.0.1', port=5000)