from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sys
sys.path.append('..')
from src.database import db
from src.db_models_new import Property, MainBuilding, Municipality, Registration, Province, Case
from sqlalchemy import func, or_, and_, String

app = Flask(__name__)

@app.route('/')
def index():
    """Landing page"""
    return render_template('home.html')

@app.route('/search')
def search_page():
    """Search page with filters"""
    # Get municipalities for filter dropdown
    session = db.get_session()
    municipalities = session.query(Municipality.name).distinct().order_by(Municipality.name).all()
    municipalities = [m[0] for m in municipalities]
    session.close()
    
    return render_template('index.html', municipalities=municipalities)

@app.route('/score-calculator')
def score_calculator():
    """Score calculator page for ranking properties"""
    # Get municipalities for filter dropdown
    session = db.get_session()
    municipalities = session.query(Municipality.name).distinct().order_by(Municipality.name).all()
    municipalities = [m[0] for m in municipalities]
    session.close()
    
    return render_template('score_calculator.html', municipalities=municipalities)

@app.route('/api/search')
def search():
    """Search properties with filters"""
    session = db.get_session()
    
    # Get filter parameters
    municipality = request.args.get('municipality')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    min_area = request.args.get('min_area', type=float)
    max_area = request.args.get('max_area', type=float)
    min_rooms = request.args.get('min_rooms', type=int)
    max_rooms = request.args.get('max_rooms', type=int)
    min_year = request.args.get('min_year', type=int)
    max_year = request.args.get('max_year', type=int)
    on_market = request.args.get('on_market')  # 'true', 'false', or None
    realtor = request.args.get('realtor')
    min_days_on_market = request.args.get('min_days_on_market', type=int)
    max_days_on_market = request.args.get('max_days_on_market', type=int)
    sort_by = request.args.get('sort_by', 'price_desc')  # Default sort
    page = request.args.get('page', 1, type=int)
    per_page = 50  # Increased from 20 to 50
    
    # Build query
    query = session.query(Property).join(Property.municipality_info)
    
    # By default, only show properties on market (active listings)
    # User can override with on_market=false to see off-market properties
    if on_market is None:
        # Default: only show properties currently on market
        query = query.filter(Property.is_on_market == True)
        # Also filter to only properties that have cases with prices
        query = query.join(Property.cases).filter(Case.current_price != None)
    else:
        # User explicitly set the filter
        query = query.filter(Property.is_on_market == (on_market.lower() == 'true'))
        # Still filter for properties with price data when available
        if on_market.lower() == 'true':
            query = query.join(Property.cases).filter(Case.current_price != None)
    
    # Apply filters
    if municipality and municipality != 'all':
        query = query.filter(Municipality.name == municipality)
    
    if min_price:
        query = query.filter(Property.latest_valuation >= min_price)
    if max_price:
        query = query.filter(Property.latest_valuation <= max_price)
    
    if min_area:
        query = query.filter(Property.living_area >= min_area)
    if max_area:
        query = query.filter(Property.living_area <= max_area)
    
    # Join with MainBuilding for rooms and year filters
    if min_rooms or max_rooms or min_year or max_year:
        query = query.join(Property.main_building)
        
        if min_rooms:
            query = query.filter(MainBuilding.number_of_rooms >= min_rooms)
        if max_rooms:
            query = query.filter(MainBuilding.number_of_rooms <= max_rooms)
        
        if min_year:
            query = query.filter(MainBuilding.year_built >= min_year)
        if max_year:
            query = query.filter(MainBuilding.year_built <= max_year)
    
    # Get total count
    total = query.distinct().count()
    
    # Apply sorting
    if sort_by == 'price_asc':
        query = query.order_by(Property.latest_valuation.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Property.latest_valuation.desc())
    elif sort_by == 'size_desc':
        query = query.order_by(Property.living_area.desc())
    elif sort_by == 'year_desc':
        if 'main_building' not in [str(m) for m in query.column_descriptions]:
            query = query.join(Property.main_building)
        query = query.order_by(MainBuilding.year_built.desc().nullslast())
    elif sort_by == 'price_per_sqm_asc':
        query = query.order_by((Property.latest_valuation / Property.living_area).asc())
    else:  # default to price_desc
        query = query.order_by(Property.latest_valuation.desc())
    
    # Paginate
    properties = query.distinct().offset((page - 1) * per_page).limit(per_page).all()
    
    # Calculate area average price per m² (only for on-market properties)
    area_avg_price_per_sqm = {}
    if municipality and municipality != 'all':
        avg_query = session.query(func.avg(Property.latest_valuation / Property.living_area)).join(
            Property.municipality_info
        ).filter(
            Municipality.name == municipality,
            Property.is_on_market == True,
            Property.latest_valuation.isnot(None),
            Property.living_area.isnot(None),
            Property.living_area > 0
        ).scalar()
        if avg_query:
            area_avg_price_per_sqm[municipality] = round(avg_query, 2)
    
    # Format results
    results = []
    for prop in properties:
        # Get building info
        building = prop.main_building
        municipality_obj = prop.municipality_info
        municipality_name = municipality_obj.name if municipality_obj else 'N/A'
        
        # Get current listing price from most recent case
        current_price = None
        if prop.cases:
            # Get the most recent case (assuming cases are ordered)
            latest_case = sorted(prop.cases, key=lambda c: c.created_date or datetime.min, reverse=True)[0]
            current_price = latest_case.current_price
        
        # Calculate price per m²
        price_per_sqm = None
        if current_price and prop.living_area and prop.living_area > 0:
            price_per_sqm = round(current_price / prop.living_area, 2)
        
        # Get days on market
        days_on_market_obj = prop.days_on_market_info
        days_on_market = None
        realtor_names = []
        if days_on_market_obj:
            # Calculate total days (this is simplified - actual calculation may vary)
            if hasattr(days_on_market_obj, 'realtors') and days_on_market_obj.realtors:
                try:
                    realtor_list = days_on_market_obj.realtors if isinstance(days_on_market_obj.realtors, list) else []
                    realtor_names = [r.get('name', '') for r in realtor_list if isinstance(r, dict)]
                except:
                    realtor_names = []
        
        results.append({
            'id': prop.id,
            'address': f"{prop.road_name} {prop.house_number}",
            'city': prop.city_name,
            'zip_code': prop.zip_code,
            'municipality': municipality_name,
            'price': current_price,
            'living_area': prop.living_area,
            'price_per_sqm': price_per_sqm,
            'area_avg_price_per_sqm': area_avg_price_per_sqm.get(municipality_name),
            'rooms': building.number_of_rooms if building else None,
            'year_built': building.year_built if building else None,
            'energy_label': prop.energy_label,
            'latitude': prop.latitude,
            'longitude': prop.longitude,
            'on_market': prop.is_on_market,
            'slug': prop.slug,
            'realtors': realtor_names,
            'days_on_market': days_on_market
        })
    
    session.close()
    
    return jsonify({
        'results': results,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@app.route('/api/text-search')
def text_search():
    """Search properties by text (address, city, municipality)"""
    try:
        session = db.get_session()
        
        # Get search query
        query_text = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        if not query_text or len(query_text) < 2:
            session.close()
            return jsonify({
                'success': False,
                'error': 'Search query must be at least 2 characters',
                'results': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0
            }), 400
        
        # Build search query - search across multiple fields
        # Cast zip_code to string for text comparison
        search_filter = or_(
            Property.road_name.ilike(f'%{query_text}%'),
            Property.city_name.ilike(f'%{query_text}%'),
            Property.place_name.ilike(f'%{query_text}%'),
            Municipality.name.ilike(f'%{query_text}%'),
            func.cast(Property.zip_code, String).ilike(f'%{query_text}%'),
        )
        
        query = session.query(Property).join(Property.municipality_info).filter(search_filter)
        
        # Get total count
        total = query.count()
        
        # Default sort by price descending
        query = query.order_by(Property.latest_valuation.desc())
        
        # Paginate
        properties = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Format results
        results = []
        for prop in properties:
            results.append({
                'id': prop.id,
                'address': f"{prop.road_name} {prop.house_number}",
                'city': prop.city_name,
                'zip_code': prop.zip_code,
                'municipality': prop.municipality_info.name if prop.municipality_info else None,
                'price': prop.latest_valuation,
                'area': prop.living_area,
                'slug': prop.slug,
                'is_on_market': prop.is_on_market,
            })
        
        session.close()
        
        return jsonify({
            'success': True,
            'results': results,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Search error: {str(e)}'
        }), 500

@app.route('/api/property/<property_id>')
def api_property_detail(property_id):
    """API endpoint for detailed property information"""
    session = db.get_session()
    try:
        prop = session.query(Property).filter(Property.id == property_id).first()
        
        if not prop:
            return jsonify({'error': 'Property not found'}), 404
        
        # Get all related data
        building = prop.main_building
        municipality = prop.municipality_info
        registrations = prop.registrations or []
        
        # Format detailed response
        result = {
            # Basic info
            'id': str(prop.id),
            'address': f"{prop.road_name or ''} {prop.house_number or ''}".strip(),
            'door': prop.door,
            'floor': prop.floor,
            'city': prop.city_name,
            'zip_code': prop.zip_code,
            'place_name': prop.place_name,
            
            # Property details
            'living_area': float(prop.living_area) if prop.living_area else None,
            'weighted_area': float(prop.weighted_area) if prop.weighted_area else None,
            'latest_valuation': float(prop.latest_valuation) if prop.latest_valuation else None,
            'property_number': prop.property_number,
            'energy_label': prop.energy_label,
            'on_market': prop.is_on_market,
            
            # Location
            'latitude': float(prop.latitude) if prop.latitude else None,
            'longitude': float(prop.longitude) if prop.longitude else None,
            
            # Municipality info
            'municipality': {
                'name': municipality.name if municipality else None,
                'code': municipality.municipality_code if municipality else None,
            } if municipality else None,
            
            # Main building
            'main_building': {
                'year_built': building.year_built if building else None,
                'year_renovated': building.year_renovated if building else None,
                'number_of_rooms': building.number_of_rooms if building else None,
                'number_of_bathrooms': building.number_of_bathrooms if building else None,
                'total_area': float(building.total_area) if building and building.total_area else None,
            } if building else None,
            
            # Registration history (last 5 transactions)
            'registrations': [
                {
                    'date': r.date.isoformat() if r.date else None,
                    'amount': float(r.amount) if r.amount else None,
                    'area': float(r.area) if r.area else None,
                    'type': r.type,
                } for r in sorted(registrations, key=lambda x: x.date or '', reverse=True)[:5]
            ] if registrations else [],
            
            # Technical identifiers
            'slug': prop.slug,
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Error fetching property: {str(e)}'}), 500
    finally:
        session.close()

@app.route('/property/<property_id>')
def property_detail(property_id):
    """Get detailed information for a specific property"""
    session = db.get_session()
    
    prop = session.query(Property).filter(Property.id == property_id).first()
    
    if not prop:
        session.close()
        return jsonify({'error': 'Property not found'}), 404
    
    # Get all related data
    building = prop.main_building
    municipality = prop.municipality_info
    province = prop.province_info
    registrations = prop.registrations
    additional_buildings = prop.additional_buildings
    
    # Format detailed response
    result = {
        # Basic info
        'id': prop.id,
        'address': f"{prop.road_name} {prop.house_number}",
        'door': prop.door,
        'floor': prop.floor,
        'city': prop.city_name,
        'zip_code': prop.zip_code,
        'place_name': prop.place_name,
        
        # Property details
        'living_area': prop.living_area,
        'weighted_area': prop.weighted_area,
        'latest_valuation': prop.latest_valuation,
        'property_number': prop.property_number,
        'energy_label': prop.energy_label,
        'on_market': prop.is_on_market,
        
        # Location
        'latitude': prop.latitude,
        'longitude': prop.longitude,
        
        # Municipality info
        'municipality': {
            'name': municipality.name if municipality else None,
            'code': municipality.municipality_code if municipality else None,
            'population': municipality.population if municipality else None,
            'church_tax': municipality.church_tax_percentage if municipality else None,
            'council_tax': municipality.council_tax_percentage if municipality else None,
            'number_of_schools': municipality.number_of_schools if municipality else None,
        } if municipality else None,
        
        # Province info
        'province': {
            'name': province.name if province else None,
            'code': province.province_code if province else None,
        } if province else None,
        
        # Main building
        'main_building': {
            'year_built': building.year_built if building else None,
            'year_renovated': building.year_renovated if building else None,
            'building_name': building.building_name if building else None,
            'number_of_floors': building.number_of_floors if building else None,
            'number_of_rooms': building.number_of_rooms if building else None,
            'number_of_bathrooms': building.number_of_bathrooms if building else None,
            'number_of_toilets': building.number_of_toilets if building else None,
            'housing_area': building.housing_area if building else None,
            'business_area': building.business_area if building else None,
            'basement_area': building.basement_area if building else None,
            'total_area': building.total_area if building else None,
            'external_wall_material': building.external_wall_material if building else None,
            'roofing_material': building.roofing_material if building else None,
            'heating_installation': building.heating_installation if building else None,
            'supplementary_heating': building.supplementary_heating if building else None,
            'kitchen_condition': building.kitchen_condition if building else None,
            'bathroom_condition': building.bathroom_condition if building else None,
            'toilet_condition': building.toilet_condition if building else None,
        } if building else None,
        
        # Additional buildings
        'additional_buildings': [
            {
                'building_name': b.building_name,
                'building_number': b.building_number,
                'year_built': b.year_built,
                'total_area': b.total_area,
            } for b in additional_buildings
        ] if additional_buildings else [],
        
        # Registration history
        'registrations': [
            {
                'date': r.date,
                'amount': r.amount,
                'area': r.area,
                'type': r.type,
            } for r in sorted(registrations, key=lambda x: x.date, reverse=True)
        ] if registrations else [],
        
        # Technical identifiers
        'gstkvhx': prop.gstkvhx,
        'entry_address_id': prop.entry_address_id,
        'slug': prop.slug,
    }
    
    session.close()
    
    return jsonify(result)

@app.route('/stats')
def stats():
    """Get database statistics"""
    session = db.get_session()
    
    total_properties = session.query(Property).count()
    
    # Properties by municipality
    by_municipality = session.query(
        Municipality.name,
        func.count(Property.id)
    ).join(Property.municipality_info).group_by(Municipality.name).order_by(func.count(Property.id).desc()).all()
    
    # Price statistics
    price_stats = session.query(
        func.avg(Property.latest_valuation),
        func.min(Property.latest_valuation),
        func.max(Property.latest_valuation)
    ).filter(Property.latest_valuation.isnot(None)).first()
    
    # Area statistics
    area_stats = session.query(
        func.avg(Property.living_area),
        func.min(Property.living_area),
        func.max(Property.living_area)
    ).filter(Property.living_area.isnot(None)).first()
    
    session.close()
    
    return jsonify({
        'total_properties': total_properties,
        'by_municipality': [{'name': m[0], 'count': m[1]} for m in by_municipality],
        'price_stats': {
            'avg': price_stats[0],
            'min': price_stats[1],
            'max': price_stats[2],
        } if price_stats else None,
        'area_stats': {
            'avg': area_stats[0],
            'min': area_stats[1],
            'max': area_stats[2],
        } if area_stats else None,
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
