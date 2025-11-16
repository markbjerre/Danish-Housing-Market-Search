"""
Scoring API Integration Module

Provides functions to integrate the scoring system into Flask API endpoints.
Handles score calculation, filtering, and response formatting.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def calculate_aggregates(session) -> Dict[str, Any]:
    """
    Calculate market aggregates for scoring comparisons.

    Args:
        session: SQLAlchemy session

    Returns:
        Dict with municipal and postal code aggregates
    """
    try:
        from src.db_models_new import Property, Municipality, Case, Registration
        from sqlalchemy import func

        aggregates = {
            'municipal': {},
            'postal': {}
        }

        # Calculate municipal aggregates
        municipalities = session.query(Municipality).all()
        for muni in municipalities:
            muni_code = muni.municipality_code

            # Avg price per sqm (from active cases)
            avg_price_sqm = session.query(
                func.avg(Case.current_price / Property.living_area)
            ).join(Property).filter(
                Property.municipality_info.has(Municipality.municipality_code == muni_code),
                Property.is_on_market == True,
                Case.current_price.isnot(None),
                Property.living_area.isnot(None),
                Property.living_area > 0
            ).scalar() or 0

            # Avg days on market
            avg_days = session.query(
                func.avg(Case.days_on_market_current)
            ).join(Property).filter(
                Property.municipality_info.has(Municipality.municipality_code == muni_code),
                Property.is_on_market == True,
                Case.days_on_market_current.isnot(None)
            ).scalar() or 30

            # Transaction count last year
            transaction_count = session.query(func.count(Registration.id)).filter(
                Registration.municipality_code == muni_code
            ).scalar() or 0

            aggregates['municipal'][muni_code] = {
                'avg_price_per_sqm': avg_price_sqm,
                'avg_days_on_market': avg_days,
                'avg_3yr_trend_pct': 5.0,  # Default assumption
                'transaction_count_last_year': transaction_count
            }

        # Calculate postal aggregates
        postal_codes = session.query(Property.zip_code).distinct().all()
        for (zip_code,) in postal_codes:
            if not zip_code:
                continue

            zip_str = str(zip_code)

            # Avg price per sqm in this postal code
            avg_price_sqm = session.query(
                func.avg(Case.current_price / Property.living_area)
            ).join(Property).filter(
                Property.zip_code == zip_code,
                Property.is_on_market == True,
                Case.current_price.isnot(None),
                Property.living_area.isnot(None),
                Property.living_area > 0
            ).scalar() or 0

            # Transaction count
            transaction_count = session.query(func.count(Registration.id)).filter(
                Registration.municipality_code == zip_code  # Assuming zip_code in registration
            ).scalar() or 0

            aggregates['postal'][zip_str] = {
                'avg_price_per_sqm': avg_price_sqm,
                'transaction_count_last_year': transaction_count,
                'avg_income': None  # Optional - would need external data
            }

        return aggregates

    except Exception as e:
        logger.error(f"Error calculating aggregates: {e}")
        return {'municipal': {}, 'postal': {}}


def calculate_property_score(
    property_obj: Any,
    session: Any,
    aggregates: Dict[str, Any],
    persona: str = 'space_conscious'
) -> Optional[Dict[str, Any]]:
    """
    Calculate score for a single property.

    Args:
        property_obj: Property ORM object
        session: SQLAlchemy session
        aggregates: Pre-calculated market aggregates
        persona: Which persona weights to use

    Returns:
        Dict with score details or None if calculation fails
    """
    try:
        from src.scoring import PropertyScorer, PersonaManager, ScoreInterpretation

        # Get persona weights
        try:
            weights = PersonaManager.get_persona_weights(persona)
        except ValueError:
            # Default to space conscious if persona not found
            weights = PersonaManager.get_persona_weights('space_conscious')

        # Create scorer with persona weights
        scorer = PropertyScorer(weights)

        # Calculate score
        score_result = scorer.calculate_score(property_obj, session, aggregates)

        if not score_result:
            return None

        # Get badge and interpretation
        composite_score = score_result.get('composite_score', 50)
        badge = ScoreInterpretation.get_badge(composite_score)

        return {
            'composite_score': composite_score,
            'badge': badge,
            'factor_breakdown': score_result.get('factors_breakdown', {}),
            'interpretation': ScoreInterpretation.get_interpretation(composite_score, 50)  # Percentile would be calculated separately
        }

    except Exception as e:
        logger.error(f"Error calculating score for property {property_obj.id}: {e}")
        return None


def add_scores_to_results(
    results: List[Dict],
    properties: List[Any],
    session: Any,
    aggregates: Dict[str, Any],
    persona: str = 'space_conscious'
) -> List[Dict]:
    """
    Add scores to search results.

    Args:
        results: List of property result dicts
        properties: List of Property ORM objects
        session: SQLAlchemy session
        aggregates: Pre-calculated aggregates
        persona: Persona to use for scoring

    Returns:
        Results list with scores added
    """
    scores_by_id = {}

    # Calculate scores for each property
    for prop in properties:
        score_data = calculate_property_score(prop, session, aggregates, persona)
        if score_data:
            scores_by_id[prop.id] = score_data

    # Add scores to results
    for result in results:
        prop_id = result.get('id')
        if prop_id in scores_by_id:
            score_data = scores_by_id[prop_id]
            result['score'] = score_data.get('composite_score')
            result['score_badge'] = score_data.get('badge')
            result['score_breakdown'] = score_data.get('factor_breakdown')
            result['score_interpretation'] = score_data.get('interpretation')
        else:
            # Neutral score if calculation failed
            result['score'] = 50
            result['score_badge'] = ScoreInterpretation.get_badge(50)
            result['score_breakdown'] = {}
            result['score_interpretation'] = 'Score calculation unavailable'

    return results


def get_personas_list() -> List[Dict]:
    """
    Get list of available scoring personas.

    Returns:
        List of persona dicts with metadata
    """
    from src.scoring import PersonaManager

    personas = []

    persona_metadata = {
        'space_conscious': {
            'name': 'Space Conscious',
            'description': 'Prioritizes size, location, and property condition',
            'keywords': ['family', 'large', 'spacious', 'location']
        },
        'price_conscious': {
            'name': 'Price Conscious',
            'description': 'Focuses on value, price efficiency, and market trends',
            'keywords': ['value', 'bargain', 'investment', 'trend']
        },
        'location_conscious': {
            'name': 'Location Conscious',
            'description': 'Emphasizes location, neighborhood, and market activity',
            'keywords': ['location', 'neighborhood', 'urban', 'active']
        },
        'condition_investment': {
            'name': 'Condition & Investment',
            'description': 'Values property condition, appreciation potential, and market strength',
            'keywords': ['quality', 'investment', 'condition', 'appreciation']
        }
    }

    for persona_id in PersonaManager.PERSONAS.keys():
        metadata = persona_metadata.get(persona_id, {})
        weights = PersonaManager.PERSONAS[persona_id]

        personas.append({
            'id': persona_id,
            'name': metadata.get('name', persona_id),
            'description': metadata.get('description', ''),
            'weights': weights,
            'keywords': metadata.get('keywords', [])
        })

    return personas
