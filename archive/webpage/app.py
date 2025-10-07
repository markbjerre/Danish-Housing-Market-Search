from flask import Flask, render_template, jsonify, request
import sys
from pathlib import Path
import pandas as pd

# Add the project root to Python path
PROJECT_ROOT = Path(__file__).parents[1]
sys.path.append(str(PROJECT_ROOT))

app = Flask(__name__)

# Lazy import to avoid database connection on module load
def get_database():
    from src.database import db
    return db

def get_models():
    from src.db_models import PropertyDB, PropertyScoreDB
    return PropertyDB, PropertyScoreDB

def get_scorer():
    from src.scoring import PropertyScorer
    return PropertyScorer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/properties')
def get_properties():
    # Get filter parameters
    min_price = request.args.get('min_price', type=float, default=0)
    max_price = request.args.get('max_price', type=float, default=float('inf'))
    property_type = request.args.get('property_type', default=None)
    min_size = request.args.get('min_size', type=float, default=0)
    municipality = request.args.get('municipality', default=None)

    # Get database and models
    db = get_database()
    PropertyDB, PropertyScoreDB = get_models()
    
    # Create database session
    session = db.get_session()
    
    try:
        # Build query with LEFT JOIN to show properties even without scores
        # Also limit results for performance (100 properties at a time)
        limit = request.args.get('limit', type=int, default=100)
        
        query = session.query(PropertyDB, PropertyScoreDB)\
            .outerjoin(PropertyScoreDB, PropertyDB.id == PropertyScoreDB.property_id)\
            .filter(PropertyDB.price >= min_price)
        
        if max_price != float('inf'):
            query = query.filter(PropertyDB.price <= max_price)
        if property_type:
            query = query.filter(PropertyDB.property_type == property_type)
        if min_size > 0:
            query = query.filter(PropertyDB.square_meters >= min_size)
        if municipality:
            query = query.filter(PropertyDB.municipality == municipality)
        
        # Apply limit and execute query
        query = query.limit(limit)
        
        # Execute query and convert to list of dicts
        properties = []
        for prop, score in query.all():
            properties.append({
                'id': prop.id,
                'address': prop.address,
                'price': prop.price if prop.price else 0,
                'square_meters': prop.square_meters if prop.square_meters else 0,
                'property_type': prop.property_type,
                'municipality': prop.municipality,
                'rooms': prop.rooms,
                'year_built': prop.year_built,
                'total_score': score.total_score if score else 0,
                'price_score': score.price_score if score else 0,
                'size_score': score.size_score if score else 0,
                'location_score': score.location_score if score else 0,
                'age_score': score.age_score if score else 0,
                'floor_score': score.floor_score if score else 0,
                'days_market_score': score.days_market_score if score else 0
            })
        
        return jsonify(properties)
    
    finally:
        session.close()

@app.route('/api/municipalities')
def get_municipalities():
    db = get_database()
    PropertyDB, _ = get_models()
    session = db.get_session()
    try:
        municipalities = session.query(PropertyDB.municipality)\
            .distinct()\
            .order_by(PropertyDB.municipality)\
            .all()
        return jsonify([m[0] for m in municipalities if m[0]])
    finally:
        session.close()

@app.route('/api/property-types')
def get_property_types():
    db = get_database()
    PropertyDB, _ = get_models()
    session = db.get_session()
    try:
        types = session.query(PropertyDB.property_type)\
            .distinct()\
            .order_by(PropertyDB.property_type)\
            .all()
        return jsonify([t[0] for t in types if t[0]])
    finally:
        session.close()

@app.route('/api/scoring-weights', methods=['GET', 'POST'])
def scoring_weights():
    scorer = get_scorer()
    if request.method == 'POST':
        weights = request.get_json()
        scorer.update_weights(weights)
        return jsonify({'status': 'success'})
    else:
        return jsonify(scorer.weights)

if __name__ == '__main__':
    app.run(debug=True)
