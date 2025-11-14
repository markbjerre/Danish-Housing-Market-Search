from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sys
sys.path.append('..')
from src.database import db
from src.db_models_new import Property, MainBuilding, Municipality, Registration, Province, Case
from sqlalchemy import func, or_, and_, String, distinct

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
        # Default: only show properties currently on market with valid prices
        query = query.filter(Property.is_on_market == True)
        # Filter for properties with at least one case that has a current price
        query = query.filter(Property.cases.any(Case.current_price.isnot(None)))
    else:
        # User explicitly set the filter
        query = query.filter(Property.is_on_market == (on_market.lower() == 'true'))
    
    # Apply filters
    if municipality and municipality != 'all':
        query = query.filter(Municipality.name == municipality)

    # Apply price filters to current_price from cases (not latest_valuation)
    # This ensures returned prices match the filter criteria
    if min_price or max_price:
        # Use subquery to avoid duplicate rows from case join
        case_subquery = session.query(Case.property_id).filter(
            Case.property_id == Property.id
        )
        if min_price:
            case_subquery = case_subquery.filter(Case.current_price >= min_price)
        if max_price:
            case_subquery = case_subquery.filter(Case.current_price <= max_price)

        query = query.filter(case_subquery.exists())
    
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
    total = query.count()
    
    # Apply sorting
    if sort_by == 'price_asc':
        # Sort by latest_valuation as a proxy for listing price
        # (current_price is calculated post-query from most recent case)
        query = query.order_by(Property.latest_valuation.asc())
    elif sort_by == 'price_desc':
        # Sort by latest_valuation as a proxy for listing price
        # (current_price is calculated post-query from most recent case)
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
        # Sort by latest_valuation as a proxy for listing price
        # (current_price is calculated post-query from most recent case)
        query = query.order_by(Property.latest_valuation.desc())

    # Paginate
    properties = query.offset((page - 1) * per_page).limit(per_page).all()

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

    # Re-sort results by price if price sorting was requested (since current_price is calculated post-query)
    if sort_by in ['price_asc', 'price_desc']:
        results.sort(key=lambda r: r['price'] if r['price'] is not None else -1, reverse=(sort_by == 'price_desc'))
    
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
        sort_by = request.args.get('sort_by', 'price_desc')  # Sort parameter
        per_page = 50

        # Get ALL filter parameters (same as regular /api/search)
        on_market = request.args.get('on_market')  # 'true', 'false', or None
        municipality = request.args.get('municipality')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        min_area = request.args.get('min_area', type=float)
        max_area = request.args.get('max_area', type=float)
        min_rooms = request.args.get('min_rooms', type=int)
        max_rooms = request.args.get('max_rooms', type=int)
        min_year = request.args.get('min_year', type=int)
        max_year = request.args.get('max_year', type=int)
        realtor = request.args.get('realtor')
        min_days_on_market = request.args.get('min_days_on_market', type=int)
        max_days_on_market = request.args.get('max_days_on_market', type=int)

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

        # Apply market status filter
        if on_market is None or on_market == '':
            # Default or "All Properties" selected: only show properties currently on market
            query = query.filter(Property.is_on_market == True)
        elif on_market.lower() == 'true':
            # "On Market Only" selected
            query = query.filter(Property.is_on_market == True)
        elif on_market.lower() == 'false':
            # "Sold Properties" selected
            query = query.filter(Property.is_on_market == False)

        # Apply municipality filter if provided
        if municipality and municipality != 'all':
            query = query.filter(Municipality.name == municipality)

        # Apply price filters to current_price from cases (not latest_valuation)
        # This ensures returned prices match the filter criteria
        if min_price or max_price:
            # Use subquery to avoid duplicate rows from case join
            case_subquery = session.query(Case.property_id).filter(
                Case.property_id == Property.id
            )
            if min_price:
                case_subquery = case_subquery.filter(Case.current_price >= min_price)
            if max_price:
                case_subquery = case_subquery.filter(Case.current_price <= max_price)

            query = query.filter(case_subquery.exists())

        # Apply area filters
        if min_area:
            query = query.filter(Property.living_area >= min_area)
        if max_area:
            query = query.filter(Property.living_area <= max_area)

        # Apply room and year filters (requires join with MainBuilding)
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

        # Get total before pagination
        total = query.count()

        # Apply sorting
        if sort_by == 'price_asc':
            query = query.order_by(Property.latest_valuation.asc())
        elif sort_by == 'price_desc':
            query = query.order_by(Property.latest_valuation.desc())
        elif sort_by == 'size_desc':
            query = query.order_by(Property.living_area.desc())
        else:  # default
            query = query.order_by(Property.latest_valuation.desc())

        # Paginate
        properties = query.offset((page - 1) * per_page).limit(per_page).all()

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
                latest_case = sorted(prop.cases, key=lambda c: c.created_date or datetime.min, reverse=True)[0]
                current_price = latest_case.current_price

            # Calculate price per m²
            price_per_sqm = None
            if current_price and prop.living_area and prop.living_area > 0:
                price_per_sqm = round(current_price / prop.living_area, 2)

            results.append({
                'id': prop.id,
                'address': f"{prop.road_name} {prop.house_number}",
                'city': prop.city_name,
                'zip_code': prop.zip_code,
                'municipality': municipality_name,
                'price': current_price,
                'living_area': prop.living_area,
                'price_per_sqm': price_per_sqm,
                'rooms': building.number_of_rooms if building else None,
                'year_built': building.year_built if building else None,
                'energy_label': prop.energy_label,
                'latitude': prop.latitude,
                'longitude': prop.longitude,
                'on_market': prop.is_on_market,
                'slug': prop.slug
            })

        # Re-sort results by price if price sorting was requested
        if sort_by in ['price_asc', 'price_desc']:
            results.sort(key=lambda r: r['price'] if r['price'] is not None else -1, reverse=(sort_by == 'price_desc'))

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
        session.close()
        return jsonify({
            'success': False,
            'error': str(e),
            'results': [],
            'total': 0,
            'page': 1,
            'per_page': 50,
            'total_pages': 0
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
