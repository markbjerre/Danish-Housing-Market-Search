"""
Property Scoring Factors - Phase 1 Implementation

Implements 8 individual scoring factors for the Danish housing market.
Each factor normalizes to 0-100 scale with proper NULL handling.

Author: Claude Code
Created: November 14, 2025
"""

import math
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

# Type aliases for clarity
Score = float  # 0-100 normalized
PropertyAggregate = Dict[str, Any]


class PricePerSqmFactor:
    """
    Factor 1: Price Per Square Meter (20% weight)

    Compares property's price per sqm to municipal average.
    - 20%+ below market = 100 pts (excellent value)
    - At market average = 80 pts
    - 20%+ above market = 0 pts

    Returns 50 (neutral) if data is missing.
    """

    WEIGHT: float = 0.20
    BELOW_MARKET_THRESHOLD: float = 0.80  # 20% below average
    ABOVE_MARKET_THRESHOLD: float = 1.20  # 20% above average

    @staticmethod
    def calculate(property_obj: Any, aggregates: PropertyAggregate) -> Score:
        """
        Calculate price per sqm factor score.

        Args:
            property_obj: Property ORM object
            aggregates: Dictionary with 'avg_price_per_sqm' key

        Returns:
            Score 0-100, or 50 if data missing
        """
        # Handle NULL values
        if (not hasattr(property_obj, 'living_area') or
            property_obj.living_area is None or
            property_obj.living_area <= 0):
            return 50.0

        # Get most recent case with price
        if not hasattr(property_obj, 'cases') or not property_obj.cases:
            return 50.0

        most_recent_case = max(
            property_obj.cases,
            key=lambda c: c.created_date if c.created_date else datetime.min
        )

        if (not most_recent_case.current_price or
            most_recent_case.current_price <= 0):
            return 50.0

        # Calculate property's price per sqm
        property_price_per_sqm = most_recent_case.current_price / property_obj.living_area

        # Get municipal average
        municipal_avg = aggregates.get('avg_price_per_sqm')
        if not municipal_avg or municipal_avg <= 0:
            return 50.0

        # Calculate ratio
        ratio = property_price_per_sqm / municipal_avg

        # Scoring logic:
        # ratio < 0.80 (below market) = 100
        # ratio = 1.00 (at market) = 80
        # ratio > 1.20 (above market) = 0

        if ratio <= PricePerSqmFactor.BELOW_MARKET_THRESHOLD:
            return 100.0
        elif ratio >= PricePerSqmFactor.ABOVE_MARKET_THRESHOLD:
            return 0.0
        else:
            # Linear interpolation between thresholds
            # Between 0.80 and 1.20: calculate linear score
            range_diff = (PricePerSqmFactor.ABOVE_MARKET_THRESHOLD -
                         PricePerSqmFactor.BELOW_MARKET_THRESHOLD)
            ratio_in_range = ratio - PricePerSqmFactor.BELOW_MARKET_THRESHOLD
            normalized = ratio_in_range / range_diff  # 0 to 1

            # Invert: lower ratio = higher score
            score = 100.0 - (normalized * 100.0)
            return max(0.0, min(100.0, score))


class SizeOptimalityFactor:
    """
    Factor 2: Size Optimality (12% weight)

    Gaussian distribution centered at 100 sqm.
    Uses formula: 100 * exp(-(size-100)^2 / 400)

    - 100 sqm = 100 pts
    - Tapers to extremes (very small/large = lower score)
    - Returns 50 (neutral) if living_area is NULL
    """

    WEIGHT: float = 0.12
    OPTIMAL_SIZE: float = 100.0  # sqm
    GAUSSIAN_SIGMA_SQ: float = 400.0  # Controls curve width

    @staticmethod
    def calculate(property_obj: Any, aggregates: PropertyAggregate) -> Score:
        """
        Calculate size optimality factor using Gaussian curve.

        Args:
            property_obj: Property ORM object
            aggregates: Not used for this factor

        Returns:
            Score 0-100, or 50 if data missing
        """
        # Handle NULL values
        if (not hasattr(property_obj, 'living_area') or
            property_obj.living_area is None or
            property_obj.living_area <= 0):
            return 50.0

        size = property_obj.living_area

        # Gaussian formula: 100 * exp(-(x-100)^2 / 400)
        exponent = -((size - SizeOptimalityFactor.OPTIMAL_SIZE) ** 2) / \
                   SizeOptimalityFactor.GAUSSIAN_SIGMA_SQ
        score = 100.0 * math.exp(exponent)

        return max(0.0, min(100.0, score))


class AgeConditionFactor:
    """
    Factor 3: Age Condition (15% weight)

    Linear scale based on effective age (most recent of year_built or year_renovated).
    - 0 years old (2024) = 100 pts
    - 125+ years old = 0 pts
    - Linear interpolation between

    Returns 50 (neutral) if year data is missing.
    """

    WEIGHT: float = 0.15
    CURRENT_YEAR: int = 2024
    MAX_AGE_YEARS: int = 125

    @staticmethod
    def calculate(property_obj: Any, aggregates: PropertyAggregate) -> Score:
        """
        Calculate age condition factor with linear scoring.

        Args:
            property_obj: Property ORM object with main_building
            aggregates: Not used for this factor

        Returns:
            Score 0-100, or 50 if data missing
        """
        # Handle NULL values
        if (not hasattr(property_obj, 'main_building') or
            property_obj.main_building is None):
            return 50.0

        main_building = property_obj.main_building

        # Get effective age: most recent of year_built or year_renovated
        year_built = main_building.year_built if hasattr(main_building, 'year_built') else None
        year_renovated = main_building.year_renovated if hasattr(main_building, 'year_renovated') else None

        # If neither exists, return neutral
        if year_built is None and year_renovated is None:
            return 50.0

        # Use the most recent (highest) year
        effective_year = max(year for year in [year_built, year_renovated]
                            if year is not None)

        if effective_year > AgeConditionFactor.CURRENT_YEAR:
            return 50.0  # Invalid data

        # Calculate age
        age = AgeConditionFactor.CURRENT_YEAR - effective_year

        # Linear scoring: 0 at age 0, 0 at age 125+
        if age >= AgeConditionFactor.MAX_AGE_YEARS:
            return 0.0
        else:
            # Linear: 100 at age 0, 0 at age 125
            score = 100.0 * (1.0 - age / AgeConditionFactor.MAX_AGE_YEARS)
            return max(0.0, min(100.0, score))


class LocationPremiumFactor:
    """
    Factor 4: Location Premium (18% weight)

    Combines municipality tier and income level.
    Municipal tiers:
    - Copenhagen = 100 pts
    - Greater Copenhagen = 85 pts
    - Other major cities = 70 pts
    - Other areas = 40 pts

    Adjusts based on income data if available.
    Returns 40 (neutral rural) if municipality data missing.
    """

    WEIGHT: float = 0.18
    MUNICIPALITY_TIERS = {
        'København': 100,
        'Frederiksberg': 90,
        'Gentofte': 85,
        'Glostrup': 85,
        'Høje-Taastrup': 85,
        'Lyngby-Taarbæk': 85,
        'Rødovre': 85,
        'Hvidovre': 85,
        'Vallensbaek': 85,
        'Ishøj': 85,
        # Other major cities
        'Aarhus': 70,
        'Aalborg': 70,
        'Odense': 70,
        'Randers': 70,
    }

    @staticmethod
    def calculate(property_obj: Any, aggregates: PropertyAggregate) -> Score:
        """
        Calculate location premium factor.

        Args:
            property_obj: Property ORM object with municipality_info
            aggregates: Optional 'avg_income' for location boost

        Returns:
            Score 0-100, or 40 if data missing
        """
        # Handle NULL values
        if (not hasattr(property_obj, 'municipality_info') or
            property_obj.municipality_info is None):
            return 40.0

        municipality = property_obj.municipality_info
        muni_name = municipality.name if hasattr(municipality, 'name') else None

        if not muni_name:
            return 40.0

        # Get base score from tier
        base_score = LocationPremiumFactor.MUNICIPALITY_TIERS.get(muni_name, 40)

        # Optional: boost based on population if available
        population = municipality.population if hasattr(municipality, 'population') else None
        if population and population > 100000:
            # Boost for large municipalities
            base_score = min(100.0, base_score * 1.1)

        return max(0.0, min(100.0, float(base_score)))


class MarketVelocityFactor:
    """
    Factor 5: Market Velocity (10% weight)

    Days on market compared to municipal average.
    - Below average = 100 pts (fast-moving market)
    - Linear penalty for longer sales
    - Returns 50 (neutral) if case data missing
    """

    WEIGHT: float = 0.10

    @staticmethod
    def calculate(property_obj: Any, aggregates: PropertyAggregate) -> Score:
        """
        Calculate market velocity factor.

        Args:
            property_obj: Property ORM object with cases
            aggregates: Dictionary with 'avg_days_on_market' key

        Returns:
            Score 0-100, or 50 if data missing
        """
        # Handle NULL values
        if not hasattr(property_obj, 'cases') or not property_obj.cases:
            return 50.0

        # Get most recent case
        most_recent_case = max(
            property_obj.cases,
            key=lambda c: c.created_date if c.created_date else datetime.min
        )

        if (not hasattr(most_recent_case, 'days_on_market_current') or
            most_recent_case.days_on_market_current is None):
            return 50.0

        property_days = most_recent_case.days_on_market_current

        # Get municipal average
        municipal_avg = aggregates.get('avg_days_on_market')
        if not municipal_avg or municipal_avg <= 0:
            return 50.0

        # Scoring: below average is good (faster sale)
        # At average = 50 pts, below = higher, above = lower
        ratio = property_days / municipal_avg

        # Linear scoring: 100 at ratio 0.5, 50 at ratio 1.0, 0 at ratio 2.0+
        if ratio <= 0.5:
            return 100.0
        elif ratio >= 2.0:
            return 0.0
        else:
            # Linear between 0.5 and 2.0
            # At 1.0: should be 50
            score = 100.0 * (2.0 - ratio) / 1.5
            return max(0.0, min(100.0, score))


class PriceTrendFactor:
    """
    Factor 6: Price Trend (15% weight)

    Compares 3-year price trend to municipal average.
    - Lagging market (bargain appreciation) = 100 pts
    - Ahead of market (overheated) = 0 pts
    - Uses registration history for trend calculation
    - Returns 50 (neutral) if <3 years history
    """

    WEIGHT: float = 0.15
    TREND_YEARS: int = 3

    @staticmethod
    def calculate(property_obj: Any, aggregates: PropertyAggregate) -> Score:
        """
        Calculate price trend factor.

        Args:
            property_obj: Property ORM object with registrations
            aggregates: Dictionary with 'avg_3yr_trend_pct' key

        Returns:
            Score 0-100, or 50 if insufficient data
        """
        # Handle NULL values
        if not hasattr(property_obj, 'registrations') or not property_obj.registrations:
            return 50.0

        registrations = property_obj.registrations
        if len(registrations) < 2:
            return 50.0

        # Sort by date
        sorted_regs = sorted(
            registrations,
            key=lambda r: r.date if r.date else datetime.min
        )

        now = datetime.now()
        three_years_ago = datetime(now.year - PriceTrendFactor.TREND_YEARS, now.month, now.day)

        # Get registrations from last 3 years
        recent_regs = [r for r in sorted_regs if r.date and r.date >= three_years_ago]

        if len(recent_regs) < 2:
            return 50.0  # Not enough data for 3-year trend

        # Calculate price trend for this property
        oldest_price = recent_regs[0].amount
        newest_price = recent_regs[-1].amount

        if not oldest_price or oldest_price <= 0:
            return 50.0

        property_trend_pct = ((newest_price - oldest_price) / oldest_price) * 100

        # Get municipal trend
        municipal_trend = aggregates.get('avg_3yr_trend_pct', 0)

        # Scoring: below municipal trend (lagging) = high score
        # Trend difference: -ve is good (lagging), +ve is bad (ahead)
        trend_diff = property_trend_pct - municipal_trend

        # Linear scoring: 100 at -20%, 50 at 0%, 0 at +20%
        if trend_diff <= -20:
            return 100.0
        elif trend_diff >= 20:
            return 0.0
        else:
            # Linear between -20 and +20
            score = 100.0 * (1.0 - (trend_diff + 20) / 40)
            return max(0.0, min(100.0, score))


class FloorDesirabilityFactor:
    """
    Factor 7: Floor Desirability (5% weight)

    Fixed scoring by floor level (mainly for apartments).
    - Floors 1-3 = 100 pts
    - Ground floor = 70 pts
    - Floor 4+ = declining penalty
    - Houses (no floor specified) = 80 pts
    """

    WEIGHT: float = 0.05

    @staticmethod
    def calculate(property_obj: Any, aggregates: PropertyAggregate) -> Score:
        """
        Calculate floor desirability factor.

        Args:
            property_obj: Property ORM object with floor
            aggregates: Not used for this factor

        Returns:
            Score 0-100, or 80 if floor data missing
        """
        # Handle NULL or missing floor
        if not hasattr(property_obj, 'floor') or property_obj.floor is None:
            return 80.0  # Houses without floor designation get neutral/good score

        try:
            # Try to convert floor to int (might be string)
            floor = int(property_obj.floor) if isinstance(property_obj.floor, str) else property_obj.floor
        except (ValueError, TypeError):
            return 80.0

        # Scoring by floor
        if floor == 0:  # Ground floor
            return 70.0
        elif 1 <= floor <= 3:  # 1st to 3rd floor
            return 100.0
        elif floor == 4:
            return 85.0
        elif floor == 5:
            return 80.0
        elif floor == 6:
            return 75.0
        elif floor == 7:
            return 70.0
        else:  # 8+ floors
            return 60.0


class TransactionVolumeFactor:
    """
    Factor 8: Transaction Volume (5% weight)

    Annual sales count in postal code (from registrations).
    - Active market (50+ sales/year) = 100 pts
    - Linear decline to 0 at very inactive markets
    - Uses registration dates to count last 12 months
    - Returns 50 (neutral) if insufficient data
    """

    WEIGHT: float = 0.05
    ACTIVE_THRESHOLD: int = 50  # Sales per year

    @staticmethod
    def calculate(property_obj: Any, aggregates: PropertyAggregate) -> Score:
        """
        Calculate transaction volume factor.

        Args:
            property_obj: Property ORM object
            aggregates: Dictionary with postal code transaction counts

        Returns:
            Score 0-100, or 50 if data missing
        """
        # Get postal code or zip code
        zip_code = None
        if hasattr(property_obj, 'zip_code') and property_obj.zip_code:
            zip_code = property_obj.zip_code
        elif hasattr(property_obj, 'zip_info') and property_obj.zip_info:
            zip_code = property_obj.zip_info.zip_code if hasattr(property_obj.zip_info, 'zip_code') else None

        if not zip_code:
            return 50.0

        # Get transaction count from aggregates
        postal_aggregates = aggregates.get('postal_code_aggregates', {})
        postal_data = postal_aggregates.get(str(zip_code), {})
        annual_transactions = postal_data.get('annual_transactions', 0)

        if annual_transactions <= 0:
            return 50.0

        # Scoring: 100 at 50+ transactions, 0 at 0 transactions
        if annual_transactions >= TransactionVolumeFactor.ACTIVE_THRESHOLD:
            return 100.0
        else:
            # Linear: 0 at 0, 100 at 50
            score = (annual_transactions / TransactionVolumeFactor.ACTIVE_THRESHOLD) * 100.0
            return max(0.0, min(100.0, score))
