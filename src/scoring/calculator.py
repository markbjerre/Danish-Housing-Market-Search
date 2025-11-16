"""
Property Scoring Calculator - Phase 1 Main Engine

Orchestrates the scoring system by calculating individual factor scores,
applying weights, and producing composite scores with percentile rankings.

Author: Claude Code
Created: November 14, 2025
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging
import statistics

from .factors import (
    PricePerSqmFactor,
    SizeOptimalityFactor,
    AgeConditionFactor,
    LocationPremiumFactor,
    MarketVelocityFactor,
    PriceTrendFactor,
    FloorDesirabilityFactor,
    TransactionVolumeFactor,
)
from .aggregates import AggregateCalculator

logger = logging.getLogger(__name__)


class CompositeScorer:
    """
    Main scoring engine for property valuation.

    Calculates all 8 scoring factors, applies weights (totaling 100%),
    and produces composite scores with percentile rankings.

    Factor weights (must sum to 1.0):
    - Price Per Sqm: 20%
    - Size Optimality: 12%
    - Age Condition: 15%
    - Location Premium: 18%
    - Market Velocity: 10%
    - Price Trend: 15%
    - Floor Desirability: 5%
    - Transaction Volume: 5%
    """

    FACTORS = [
        ('price_per_sqm', PricePerSqmFactor, 0.20),
        ('size_optimality', SizeOptimalityFactor, 0.12),
        ('age_condition', AgeConditionFactor, 0.15),
        ('location_premium', LocationPremiumFactor, 0.18),
        ('market_velocity', MarketVelocityFactor, 0.10),
        ('price_trend', PriceTrendFactor, 0.15),
        ('floor_desirability', FloorDesirabilityFactor, 0.05),
        ('transaction_volume', TransactionVolumeFactor, 0.05),
    ]

    FACTOR_DESCRIPTIONS = {
        'price_per_sqm': 'Price relative to municipal average',
        'size_optimality': 'Property size fit (100 sqm optimal)',
        'age_condition': 'Building age and condition',
        'location_premium': 'Geographic location desirability',
        'market_velocity': 'Days on market vs. area average',
        'price_trend': '3-year price appreciation trend',
        'floor_desirability': 'Floor level preference (apartments)',
        'transaction_volume': 'Market activity in postal code',
    }

    def __init__(self, session: Session):
        """
        Initialize scorer with database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.aggregate_calculator = AggregateCalculator(session)
        self._all_composite_scores: List[float] = []
        self._aggregates: Optional[Dict[str, Any]] = None

    def calculate_property_score(
        self,
        property_obj: Any,
        include_percentile: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate complete scoring result for a single property.

        Args:
            property_obj: Property ORM object to score
            include_percentile: Whether to calculate percentile rank (requires other scores)

        Returns:
            Scoring result dictionary with structure:
            {
                'property_id': str,
                'composite_score': float (0-100),
                'percentile_rank': float (0-100) if calculated,
                'factors': {
                    'factor_name': {
                        'score': float (0-100),
                        'weight': float (0.0-1.0),
                        'description': str,
                        'weighted_contribution': float
                    },
                    ...
                },
                'calculated_at': datetime,
                'data_quality': {
                    'missing_fields': List[str],
                    'confidence': float (0-1)
                }
            }

        Raises:
            ValueError: If property object is invalid
            Exception: If database query fails
        """
        try:
            # Validate property object
            if not property_obj or not hasattr(property_obj, 'id'):
                raise ValueError("Invalid property object: missing id attribute")

            # Ensure aggregates are calculated
            if self._aggregates is None:
                self._aggregates = self.aggregate_calculator.calculate_all_aggregates()

            # Get municipal and postal aggregates for this property
            municipal_aggs = self._get_property_aggregates(property_obj)

            # Calculate all factor scores
            factor_scores = self._calculate_all_factors(property_obj, municipal_aggs)

            # Calculate composite score (weighted sum)
            composite_score = self._calculate_composite_score(factor_scores)

            # Track for percentile calculation
            self._all_composite_scores.append(composite_score)

            # Build results dictionary
            result = {
                'property_id': property_obj.id,
                'composite_score': round(composite_score, 1),
                'percentile_rank': None,  # Set later if requested
                'factors': self._format_factor_results(factor_scores),
                'calculated_at': datetime.now(),
                'data_quality': self._assess_data_quality(property_obj),
            }

            # Calculate percentile if requested
            if include_percentile:
                result['percentile_rank'] = self._calculate_percentile(
                    composite_score,
                    self._all_composite_scores
                )

            return result

        except Exception as e:
            logger.error(f"Error scoring property {property_obj.id}: {str(e)}")
            raise

    def _get_property_aggregates(self, property_obj: Any) -> Dict[str, Any]:
        """
        Get relevant aggregates for a property's municipality and postal code.

        Args:
            property_obj: Property ORM object

        Returns:
            Dictionary with municipal and postal level aggregates
        """
        aggregates = {}

        try:
            # Get municipality name
            if (hasattr(property_obj, 'municipality_info') and
                property_obj.municipality_info and
                hasattr(property_obj.municipality_info, 'name')):
                muni_name = property_obj.municipality_info.name
                aggregates.update(
                    self._aggregates.get('municipal', {}).get(muni_name, {})
                )

            # Get postal code aggregates
            if hasattr(property_obj, 'zip_code') and property_obj.zip_code:
                postal_aggs = self._aggregates.get('postal_code_aggregates', {})
                aggregates.update(
                    postal_aggs.get(str(property_obj.zip_code), {})
                )

            # Add postal_code_aggregates for transaction volume factor
            aggregates['postal_code_aggregates'] = (
                self._aggregates.get('postal_code_aggregates', {})
            )

        except Exception as e:
            logger.warning(f"Error getting aggregates for property: {str(e)}")

        return aggregates

    def _calculate_all_factors(
        self,
        property_obj: Any,
        aggregates: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate scores for all 8 factors.

        Args:
            property_obj: Property ORM object
            aggregates: Market aggregate data

        Returns:
            Dictionary mapping factor_name to score (0-100)
        """
        factor_scores = {}

        for factor_name, factor_class, weight in self.FACTORS:
            try:
                score = factor_class.calculate(property_obj, aggregates)
                factor_scores[factor_name] = max(0.0, min(100.0, score))
            except Exception as e:
                logger.warning(f"Error calculating {factor_name}: {str(e)}")
                factor_scores[factor_name] = 50.0  # Neutral default on error

        return factor_scores

    def _calculate_composite_score(self, factor_scores: Dict[str, float]) -> float:
        """
        Calculate weighted composite score from individual factors.

        Args:
            factor_scores: Dictionary of factor_name -> score (0-100)

        Returns:
            Weighted composite score (0-100)
        """
        total_score = 0.0

        for factor_name, factor_class, weight in self.FACTORS:
            score = factor_scores.get(factor_name, 50.0)
            total_score += score * weight

        return round(total_score, 1)

    def _format_factor_results(self, factor_scores: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """
        Format factor scores into detailed result structure.

        Args:
            factor_scores: Dictionary of factor_name -> score (0-100)

        Returns:
            Formatted dictionary with score, weight, description, and contribution
        """
        formatted = {}

        for factor_name, factor_class, weight in self.FACTORS:
            score = factor_scores.get(factor_name, 50.0)
            weighted_contribution = score * weight

            formatted[factor_name] = {
                'score': round(score, 1),
                'weight': weight,
                'description': self.FACTOR_DESCRIPTIONS.get(
                    factor_name,
                    'Unknown factor'
                ),
                'weighted_contribution': round(weighted_contribution, 2),
            }

        return formatted

    def _calculate_percentile(
        self,
        score: float,
        all_scores: List[float]
    ) -> float:
        """
        Calculate percentile rank for a score within population.

        Args:
            score: Individual property score
            all_scores: List of all scores calculated in session

        Returns:
            Percentile rank (0-100), with 0 = lowest, 100 = highest
        """
        if not all_scores or len(all_scores) < 2:
            return 50.0  # Default if insufficient data

        try:
            # Count scores below this score
            scores_below = sum(1 for s in all_scores if s < score)
            percentile = (scores_below / len(all_scores)) * 100
            return round(percentile, 1)

        except Exception as e:
            logger.warning(f"Error calculating percentile: {str(e)}")
            return 50.0

    def _assess_data_quality(self, property_obj: Any) -> Dict[str, Any]:
        """
        Assess data completeness and confidence for a property.

        Args:
            property_obj: Property ORM object

        Returns:
            Dictionary with missing_fields list and confidence score (0-1)
        """
        missing_fields = []
        total_fields = 0

        # Check critical fields for scoring
        critical_fields = [
            'living_area',
            'zip_code',
            'municipality_info',
            'main_building',
            'cases',
            'registrations',
        ]

        for field in critical_fields:
            total_fields += 1
            if not hasattr(property_obj, field):
                missing_fields.append(field)
            else:
                value = getattr(property_obj, field, None)
                if value is None or (isinstance(value, list) and len(value) == 0):
                    missing_fields.append(field)

        # Calculate confidence (0-1): how many fields are present
        confidence = 1.0 - (len(missing_fields) / total_fields)

        return {
            'missing_fields': missing_fields,
            'confidence': round(confidence, 2),
        }

    def batch_score_properties(
        self,
        properties: List[Any],
        batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Score multiple properties efficiently.

        Args:
            properties: List of Property ORM objects
            batch_size: Number of properties to score before clearing memory

        Returns:
            List of scoring result dictionaries
        """
        results = []

        try:
            # Calculate aggregates once for efficiency
            if self._aggregates is None:
                logger.info("Calculating market aggregates...")
                self._aggregates = self.aggregate_calculator.calculate_all_aggregates()

            # Score each property
            for idx, prop in enumerate(properties):
                try:
                    score_result = self.calculate_property_score(
                        prop,
                        include_percentile=False  # Calculate after all scores
                    )
                    results.append(score_result)

                    # Log progress
                    if (idx + 1) % batch_size == 0:
                        logger.info(f"Scored {idx + 1}/{len(properties)} properties")

                except Exception as e:
                    logger.error(f"Error scoring property {idx}: {str(e)}")
                    continue

            # Calculate percentiles for all scores after batch processing
            logger.info("Calculating percentile ranks...")
            for result in results:
                composite = result['composite_score']
                result['percentile_rank'] = self._calculate_percentile(
                    composite,
                    self._all_composite_scores
                )

            logger.info(f"Successfully scored {len(results)}/{len(properties)} properties")
            return results

        except Exception as e:
            logger.error(f"Error in batch scoring: {str(e)}")
            raise

    def reset(self) -> None:
        """Reset scorer state between batch runs."""
        self._all_composite_scores = []
        self._aggregates = None
        logger.info("Scorer reset")

    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Get summary statistics of all scores calculated in session.

        Returns:
            Dictionary with min, max, mean, median, stdev scores
        """
        if not self._all_composite_scores:
            return {}

        scores = self._all_composite_scores

        return {
            'count': len(scores),
            'min': round(min(scores), 1),
            'max': round(max(scores), 1),
            'mean': round(statistics.mean(scores), 1),
            'median': round(statistics.median(scores), 1),
            'stdev': round(statistics.stdev(scores), 1) if len(scores) > 1 else 0.0,
        }
