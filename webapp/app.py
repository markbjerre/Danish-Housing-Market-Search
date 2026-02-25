from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime
import sys
import logging

sys.path.append('..')
from src.database import db
from src.db_models_new import Property, MainBuilding, Municipality, Registration, Province, Case
from sqlalchemy import func, or_, and_, String, distinct
try:
    from .statistics_queries import (
        get_data_as_of,
        get_row_counts,
        get_market_overview,
        get_price_trends,
        get_sales_volume,
        get_kommune_summary,
        get_weekly_summary,
    )
except ImportError:
    from statistics_queries import (
        get_data_as_of,
        get_row_counts,
        get_market_overview,
        get_price_trends,
        get_sales_volume,
        get_kommune_summary,
        get_weekly_summary,
    )
from src.scoring import (
    CompositeScorer,
    PersonaManager,
    ScorePercentileCalculator,
    ScoreInterpretation,
    AggregateCalculator
)

logger = logging.getLogger(__name__)

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
    """Search properties with filters and optional scoring"""
    session = db.get_session()

    try:
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

        # Phase 2: Scoring parameters
        min_score = request.args.get('min_score', type=float)
        max_score = request.args.get('max_score', type=float)
        persona = request.args.get('persona', 'balanced')  # Default persona for scoring
    
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

        # Apply distinct to avoid duplicate properties from filter subqueries
        query = query.distinct(Property.id)

        # For price sorting, we need to join with the most recent Case for each property
        # Use a subquery to get only the most recent case per property (by created_date)
        if sort_by in ['price_asc', 'price_desc', 'score_asc', 'score_desc'] or sort_by is None or sort_by == '':
            from sqlalchemy import func as sql_func

            # Subquery to find the most recent case per property
            # Using GROUP BY with MAX to get only one case per property
            recent_case_subquery = session.query(
                Case.property_id,
                Case.current_price,
                sql_func.max(Case.created_date).over(partition_by=Case.property_id).label('max_date'),
                sql_func.row_number().over(
                    partition_by=Case.property_id,
                    order_by=Case.created_date.desc()
                ).label('rn')
            ).subquery()

            # Filter to only the most recent case (row_number = 1)
            recent_cases = session.query(recent_case_subquery).filter(
                recent_case_subquery.c.rn == 1
            ).subquery()

            # LEFT JOIN with the recent cases to preserve properties without cases
            query = query.outerjoin(recent_cases, Property.id == recent_cases.c.property_id)

            # Apply distinct again AFTER the join to eliminate duplicate rows from the join
            query = query.distinct(Property.id)

            # Sort by price (score sorting happens in-memory after calculation)
            if sort_by == 'price_asc':
                query = query.order_by(recent_cases.c.current_price.asc(), Property.id.asc())
            else:  # price_desc or default or score sorts
                # NULL prices go to the end
                query = query.order_by(recent_cases.c.current_price.desc().nullslast(), Property.id.asc())

            # Get total count before pagination
            total = query.count()

            # Apply pagination at database level
            properties = query.offset((page - 1) * per_page).limit(per_page).all()
        else:
            # Get total count first
            total = query.count()

            # Apply sorting at database level for non-price sorts
            if sort_by == 'size_desc':
                query = query.order_by(Property.living_area.desc(), Property.id.asc())
            elif sort_by == 'year_desc':
                if 'main_building' not in [str(m) for m in query.column_descriptions]:
                    query = query.join(Property.main_building)
                query = query.order_by(MainBuilding.year_built.desc().nullslast(), Property.id.asc())
            elif sort_by == 'price_per_sqm_asc':
                query = query.order_by((Property.latest_valuation / Property.living_area).asc(), Property.id.asc())

            # Apply pagination at database level
            properties = query.offset((page - 1) * per_page).limit(per_page).all()

        # Calculate area average price per mÂ² (only for on-market properties)
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

        # Phase 2: Initialize scoring if persona-based sorting or scoring filters are requested
        aggregates = None
        scorer = None
        all_scores_for_percentile = []

        if sort_by in ['score_asc', 'score_desc'] or min_score is not None or max_score is not None:
            try:
                # Calculate aggregates ONCE for efficiency
                scorer = CompositeScorer(session)
                aggregates = scorer.aggregate_calculator.calculate_all_aggregates()
                logger.info(f"Scoring initialized with persona: {persona}")
            except Exception as e:
                logger.warning(f"Failed to initialize scoring: {str(e)}")
                scorer = None
                aggregates = None

        # Format results with optional scoring
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

            # Calculate price per mÂ²
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

            result_item = {
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
            }

            # Phase 2: Calculate scoring if needed
            if scorer and aggregates:
                try:
                    # Calculate score using PersonaManager weights if persona specified
                    score_result = scorer.calculate_property_score(prop, include_percentile=False)

                    if score_result:
                        composite_score = score_result.get('composite_score', 50.0)
                        all_scores_for_percentile.append(composite_score)

                        # Get badge information
                        badge = ScoreInterpretation.get_badge(composite_score)

                        result_item.update({
                            'composite_score': composite_score,
                            'score_badge': badge['badge'] if badge else None,
                            'score_badge_label': badge['label'] if badge else 'Unknown',
                            'score_badge_color': badge['color'] if badge else '#999999',
                        })
                except Exception as e:
                    logger.warning(f"Failed to score property {prop.id}: {str(e)}")
                    # Return neutral score on error
                    result_item.update({
                        'composite_score': 50.0,
                        'score_badge': 'fair',
                        'score_badge_label': 'Fair',
                        'score_badge_color': '#E67E22',
                    })

            results.append(result_item)

        # Phase 2: Apply score-based filtering AFTER all scores are calculated
        if min_score is not None or max_score is not None:
            results = [r for r in results
                      if ((min_score is None or r.get('composite_score', 50) >= min_score) and
                          (max_score is None or r.get('composite_score', 50) <= max_score))]
            total = len(results)

        # Phase 2: Apply score-based sorting AFTER all scores are calculated
        if sort_by == 'score_desc' and all_scores_for_percentile:
            # Calculate percentiles for all results
            percentile_map = ScorePercentileCalculator.calculate_percentiles(all_scores_for_percentile)

            # Add percentile to results
            for result in results:
                score = result.get('composite_score', 50.0)
                percentile = percentile_map.get(score, 50.0)
                result['percentile_rank'] = percentile

            # Sort by score descending
            results.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

        elif sort_by == 'score_asc' and all_scores_for_percentile:
            # Calculate percentiles for all results
            percentile_map = ScorePercentileCalculator.calculate_percentiles(all_scores_for_percentile)

            # Add percentile to results
            for result in results:
                score = result.get('composite_score', 50.0)
                percentile = percentile_map.get(score, 50.0)
                result['percentile_rank'] = percentile

            # Sort by score ascending
            results.sort(key=lambda x: x.get('composite_score', 0))

        session.close()

        return jsonify({
            'results': results,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })

    except Exception as e:
        session.close()
        logger.error(f"Search error: {str(e)}")
        return jsonify({
            'error': f'Search error: {str(e)}',
            'results': [],
            'total': 0,
            'page': 1,
            'per_page': per_page,
            'total_pages': 0
        }), 500

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

        # Apply distinct to avoid duplicate properties from filter subqueries
        query = query.distinct(Property.id)

        # For price sorting, join with the most recent Case for each property
        if sort_by in ['price_asc', 'price_desc'] or sort_by is None or sort_by == '':
            sort_by_price = True
            from sqlalchemy import func as sql_func

            # Subquery to find the most recent case per property
            recent_case_subquery = session.query(
                Case.property_id,
                Case.current_price,
                sql_func.row_number().over(
                    partition_by=Case.property_id,
                    order_by=Case.created_date.desc()
                ).label('rn')
            ).subquery()

            # Filter to only the most recent case (row_number = 1)
            recent_cases = session.query(recent_case_subquery).filter(
                recent_case_subquery.c.rn == 1
            ).subquery()

            # LEFT JOIN with the recent cases to preserve properties without cases
            query = query.outerjoin(recent_cases, Property.id == recent_cases.c.property_id)

            # Apply distinct again AFTER the join to eliminate duplicate rows from the join
            query = query.distinct(Property.id)

            # Sort by price with Property.id as secondary sort for deterministic ordering
            if sort_by == 'price_asc':
                query = query.order_by(recent_cases.c.current_price.asc(), Property.id.asc())
            else:  # price_desc or default
                # NULL prices go to the end
                query = query.order_by(recent_cases.c.current_price.desc().nullslast(), Property.id.asc())

            # Get total count before pagination
            total = query.count()

            # Apply pagination at database level
            properties = query.offset((page - 1) * per_page).limit(per_page).all()
        else:
            sort_by_price = False
            # Get total count first
            total = query.count()

            # Apply sorting at database level for non-price sorts
            if sort_by == 'size_desc':
                query = query.order_by(Property.living_area.desc(), Property.id.asc())
            elif sort_by == 'year_desc':
                # Only join if we haven't already (for room/year filters)
                if not any(str(entity.key[0]) == 'main_building' for entity in query.column_descriptions if hasattr(entity, 'key')):
                    query = query.join(Property.main_building)
                query = query.order_by(MainBuilding.year_built.desc().nullslast(), Property.id.asc())
            elif sort_by == 'price_per_sqm_asc':
                query = query.order_by((Property.latest_valuation / Property.living_area).asc(), Property.id.asc())

            # Apply pagination at database level
            properties = query.offset((page - 1) * per_page).limit(per_page).all()

        # Calculate area average price per mÂ² for the municipality
        area_avg_price_per_sqm = {}
        if properties:
            municipality_names = set(p.municipality_info.name for p in properties if p.municipality_info)
            for mun_name in municipality_names:
                avg_query = session.query(func.avg(Property.latest_valuation / Property.living_area)).join(
                    Property.municipality_info
                ).filter(
                    Municipality.name == mun_name,
                    Property.is_on_market == True,
                    Property.latest_valuation.isnot(None),
                    Property.living_area.isnot(None),
                    Property.living_area > 0
                ).scalar()
                if avg_query:
                    area_avg_price_per_sqm[mun_name] = round(avg_query, 2)

        # Format results
        results = []
        for prop in properties:
            # Get building info
            building = prop.main_building
            municipality_obj = prop.municipality_info
            municipality_name = municipality_obj.name if municipality_obj else 'N/A'

            # Use latest_valuation as price (consistent with /api/search)
            price = prop.latest_valuation

            # Calculate price per mÂ²
            price_per_sqm = None
            if price and prop.living_area and prop.living_area > 0:
                price_per_sqm = round(price / prop.living_area, 2)

            results.append({
                'id': prop.id,
                'address': f"{prop.road_name} {prop.house_number}",
                'city': prop.city_name,
                'zip_code': prop.zip_code,
                'municipality': municipality_name,
                'price': price,
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
                'realtors': [],
                'days_on_market': None,
                'image_url': None
            })

        # No need to re-sort - database handles sorting by current_price now

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

@app.route('/api/personas')
def api_personas():
    """Get list of available scoring personas"""
    try:
        personas_list = PersonaManager.list_personas()
        personas_data = []

        for persona_name in personas_list:
            try:
                weights = PersonaManager.get_persona_weights(persona_name)
                description = PersonaManager.get_persona_description(persona_name)

                personas_data.append({
                    'id': persona_name,
                    'name': ' '.join(word.capitalize() for word in persona_name.split('_')),
                    'description': description,
                    'weights': weights
                })
            except Exception as e:
                logger.warning(f"Failed to load persona {persona_name}: {str(e)}")

        return jsonify({
            'success': True,
            'personas': personas_data
        })

    except Exception as e:
        logger.error(f"Error fetching personas: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error fetching personas: {str(e)}'
        }), 500


@app.route('/api/property/<property_id>/score')
def api_property_score(property_id: str):
    """Get detailed score breakdown for a specific property"""
    session = db.get_session()

    try:
        # Get persona from query parameters
        persona = request.args.get('persona', 'balanced')

        # Fetch property
        prop = session.query(Property).filter(Property.id == property_id).first()

        if not prop:
            return jsonify({
                'success': False,
                'error': 'Property not found'
            }), 404

        # Initialize scorer
        scorer = CompositeScorer(session)
        aggregates = scorer.aggregate_calculator.calculate_all_aggregates()

        # Calculate score
        score_result = scorer.calculate_property_score(prop, include_percentile=False)

        if not score_result:
            return jsonify({
                'success': False,
                'error': 'Failed to calculate property score'
            }), 500

        composite_score = score_result.get('composite_score', 50.0)

        # Get badge information
        badge = ScoreInterpretation.get_badge(composite_score)

        # Get property data for response
        building = prop.main_building
        municipality_obj = prop.municipality_info
        municipality_name = municipality_obj.name if municipality_obj else 'N/A'

        # Get current price
        current_price = None
        if prop.cases:
            latest_case = sorted(prop.cases, key=lambda c: c.created_date or datetime.min, reverse=True)[0]
            current_price = latest_case.current_price

        # Get municipality average score for comparison
        municipal_avg_score = None
        if municipality_obj:
            try:
                # Query all properties in municipality to calculate average score
                muni_properties = session.query(Property).filter(
                    Property.municipality_id == municipality_obj.id
                ).limit(100).all()  # Limit for performance

                if muni_properties:
                    muni_scores = []
                    for muni_prop in muni_properties:
                        try:
                            muni_score_result = scorer.calculate_property_score(
                                muni_prop,
                                include_percentile=False
                            )
                            if muni_score_result:
                                muni_scores.append(muni_score_result.get('composite_score', 50.0))
                        except:
                            pass

                    if muni_scores:
                        municipal_avg_score = round(sum(muni_scores) / len(muni_scores), 1)
            except Exception as e:
                logger.warning(f"Failed to calculate municipal average: {str(e)}")

        # Calculate percentile by comparing to other on-market properties
        try:
            # Query all on-market properties for percentile
            all_on_market = session.query(Property).filter(
                Property.is_on_market == True
            ).limit(1000).all()  # Limit for performance

            if all_on_market:
                all_scores = []
                for on_mkt_prop in all_on_market:
                    try:
                        mkt_score_result = scorer.calculate_property_score(
                            on_mkt_prop,
                            include_percentile=False
                        )
                        if mkt_score_result:
                            all_scores.append(mkt_score_result.get('composite_score', 50.0))
                    except:
                        pass

                if all_scores:
                    percentile_map = ScorePercentileCalculator.calculate_percentiles(all_scores)
                    percentile_rank = percentile_map.get(composite_score, 50.0)
                else:
                    percentile_rank = 50.0
            else:
                percentile_rank = 50.0
        except Exception as e:
            logger.warning(f"Failed to calculate percentile: {str(e)}")
            percentile_rank = 50.0

        # Format factor breakdown
        factors_breakdown = {}
        if 'factors' in score_result:
            for factor_name, factor_data in score_result['factors'].items():
                factors_breakdown[factor_name] = {
                    'score': factor_data.get('score', 0),
                    'weight': factor_data.get('weight', 0),
                    'contribution': round(
                        factor_data.get('score', 0) * factor_data.get('weight', 0),
                        2
                    ),
                    'explanation': factor_data.get('description', '')
                }

        # Build response
        response = {
            'success': True,
            'property_id': str(prop.id),
            'address': f"{prop.road_name} {prop.house_number}",
            'municipality': municipality_name,
            'price': current_price,
            'living_area': prop.living_area,
            'composite_score': composite_score,
            'percentile_rank': percentile_rank,
            'badge': {
                'label': badge['label'] if badge else 'Unknown',
                'color': badge['color'] if badge else '#999999',
                'badge': badge['badge'] if badge else 'unknown',
                'emoji': badge.get('emoji', '')
            },
            'interpretation': ScoreInterpretation.get_interpretation(
                composite_score,
                percentile=percentile_rank
            ) if hasattr(ScoreInterpretation, 'get_interpretation') else f"Score {composite_score}",
            'factor_breakdown': factors_breakdown,
            'comparison': {
                'municipal_avg_score': municipal_avg_score,
                'municipal_percentile': percentile_rank,
                'description': f"{round(percentile_rank)}% of on-market properties score lower"
            }
        }

        session.close()
        return jsonify(response)

    except Exception as e:
        session.close()
        logger.error(f"Error calculating property score: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error calculating score: {str(e)}'
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


# ---------------------------------------------------------------------------
# Statistics (housing market analytics)
# ---------------------------------------------------------------------------

def _statistics_db_error(e: Exception):
    """Return 503 when DB unavailable."""
    return jsonify({'ok': False, 'error': 'Database unavailable', 'detail': str(e)}), 503


@app.route('/statistics')
def statistics_page():
    """Statistics dashboard page."""
    try:
        session = db.get_session()
        municipalities = session.query(Municipality.name).distinct().order_by(Municipality.name).all()
        municipalities = [m[0] for m in municipalities]
        session.close()
        return render_template('statistics.html', municipalities=municipalities)
    except Exception:
        return render_template('statistics.html', municipalities=[], db_error='Database connection failed.'), 503


@app.route('/api/statistics/health')
def api_statistics_health():
    """Health check for statistics API. Returns ok, data_as_of, row_counts."""
    session = None
    try:
        session = db.get_session()
        data_as_of = get_data_as_of(session)
        counts = get_row_counts(session)
        return jsonify({
            'ok': True,
            'data_as_of': data_as_of.isoformat() if data_as_of else None,
            'row_counts': counts,
            'schema_version': 1,
        })
    except Exception:
        return jsonify({'ok': False, 'error': 'Database unavailable', 'row_counts': None}), 503
    finally:
        if session:
            try:
                session.close()
            except Exception:
                pass


@app.route('/api/statistics/market-overview')
def api_statistics_market_overview():
    """Market overview: active listings, sold this month, avg sqm price."""
    try:
        session = db.get_session()
        try:
            data = get_market_overview(session)
            data_as_of = get_data_as_of(session)
            resp = jsonify({
                'schema_version': 1,
                'data_as_of': data_as_of.isoformat() if data_as_of else None,
                **data,
            })
            resp.headers['Cache-Control'] = 'max-age=300'
            return resp
        finally:
            session.close()
    except Exception as e:
        return _statistics_db_error(e)


@app.route('/api/statistics/price-trends')
def api_statistics_price_trends():
    """Price trends over time. Params: municipality, period (month|quarter|year), months (default 12)."""
    municipality = request.args.get('municipality')
    period = request.args.get('period', 'month')
    if period not in ('month', 'quarter', 'year'):
        period = 'month'
    months = min(24, max(1, request.args.get('months', 12, type=int)))

    try:
        session = db.get_session()
        try:
            data = get_price_trends(session, municipality=municipality, period=period, months=months)
            data_as_of = get_data_as_of(session)
            return jsonify({
                'schema_version': 1,
                'data_as_of': data_as_of.isoformat() if data_as_of else None,
                'data': data,
            })
        finally:
            session.close()
    except Exception as e:
        return _statistics_db_error(e)


@app.route('/api/statistics/sales-volume')
def api_statistics_sales_volume():
    """Sales volume over time. Params: municipality, months (default 12)."""
    municipality = request.args.get('municipality')
    months = min(24, max(1, request.args.get('months', 12, type=int)))

    try:
        session = db.get_session()
        try:
            data = get_sales_volume(session, municipality=municipality, months=months)
            data_as_of = get_data_as_of(session)
            return jsonify({
                'schema_version': 1,
                'data_as_of': data_as_of.isoformat() if data_as_of else None,
                'data': data,
            })
        finally:
            session.close()
    except Exception as e:
        return _statistics_db_error(e)


@app.route('/api/statistics/kommune-summary')
def api_statistics_kommune_summary():
    """Per-kommune summary. Params: municipality (optional filter)."""
    municipality = request.args.get('municipality')

    try:
        session = db.get_session()
        try:
            data = get_kommune_summary(session, municipality=municipality)
            data_as_of = get_data_as_of(session)
            resp = jsonify({
                'schema_version': 1,
                'data_as_of': data_as_of.isoformat() if data_as_of else None,
                'data': data,
            })
            resp.headers['Cache-Control'] = 'max-age=300'
            return resp
        finally:
            session.close()
    except Exception as e:
        return _statistics_db_error(e)


@app.route('/api/statistics/weekly-summary')
def api_statistics_weekly_summary():
    """Compact weekly digest for OpenClaw. Params: format=text|json (default text)."""
    fmt = request.args.get('format', 'text').lower()
    if fmt not in ('text', 'json'):
        fmt = 'text'

    try:
        session = db.get_session()
        try:
            data = get_weekly_summary(session)
            data_as_of = get_data_as_of(session)
            from datetime import date
            today = date.today()
            iso_week = today.isocalendar()
            period = f"{iso_week[0]}-W{iso_week[1]:02d}"

            payload = {
                'period': period,
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'data_as_of': str(data_as_of.date()) if data_as_of else None,
                'summary': data,
            }

            if fmt == 'text':
                s = payload['summary']
                yoy_val = s.get('sqm_price_yoy_pct')
                yoy = f"+{yoy_val}%" if yoy_val is not None and yoy_val >= 0 else f"{yoy_val}%" if yoy_val is not None else "—"
                lines = [
                    f"Housing Weekly ({period})",
                    f"Active: {s.get('active_listings', 0):,} | Sold (7d): {s.get('sold_last_7_days', 0):,} | Avg kr/sqm: {s.get('avg_sqm_price_national', 0):,.0f} ({yoy} YoY)",
                    f"Top sales: {', '.join(s.get('top_3_kommuner_by_sales', []) or ['—'])}",
                    f"Lowest prices: {', '.join(s.get('bottom_3_kommuner_by_price', []) or ['—'])}",
                ]
                return Response('\n'.join(lines), mimetype='text/plain')
            return jsonify(payload)
        finally:
            session.close()
    except Exception as e:
        if fmt == 'text':
            return Response("Database unavailable\n", mimetype='text/plain'), 503
        return _statistics_db_error(e)


# ---------------------------------------------------------------------------
# Legacy /stats (kept for compatibility)
# ---------------------------------------------------------------------------

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
    app.run(debug=True, host='0.0.0.0', port=5000)
