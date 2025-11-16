"""
Property Scoring Aggregates - Market Statistics Calculator

Pre-calculates market aggregates for scoring factors.
Computes municipal and postal code level statistics for normalization.

Author: Claude Code
Created: November 14, 2025
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import logging

logger = logging.getLogger(__name__)


class AggregateCalculator:
    """
    Calculates and caches market aggregates for scoring normalization.

    Provides methods to compute:
    - Municipal-level averages (price per sqm, days on market, trends)
    - Postal code level statistics (transaction volume, price averages)
    """

    def __init__(self, session: Session):
        """
        Initialize calculator with database session.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self._municipal_cache: Dict[str, Dict[str, Any]] = {}
        self._postal_cache: Dict[str, Dict[str, Any]] = {}
        self._calculated = False

    def calculate_all_aggregates(self) -> Dict[str, Any]:
        """
        Calculate all market aggregates in one call.

        Returns:
            Dictionary with 'municipal' and 'postal_code_aggregates' keys
        """
        try:
            municipal_aggs = self.calculate_municipal_aggregates()
            postal_aggs = self.calculate_postal_aggregates()

            result = {
                'municipal': municipal_aggs,
                'postal_code_aggregates': postal_aggs,
                'calculated_at': datetime.now(),
            }

            self._calculated = True
            logger.info(f"Calculated aggregates for {len(municipal_aggs)} municipalities "
                       f"and {len(postal_aggs)} postal codes")
            return result

        except Exception as e:
            logger.error(f"Error calculating aggregates: {str(e)}")
            raise

    def calculate_municipal_aggregates(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate municipal-level market statistics.

        Returns per-municipality:
        - avg_price_per_sqm: Average price per square meter
        - avg_days_on_market: Average days listings stay on market
        - avg_3yr_trend_pct: 3-year price appreciation percentage
        - total_transactions: Total sales in period
        - active_listings: Current active listings

        Returns:
            Dict[municipality_name] = {
                'avg_price_per_sqm': float,
                'avg_days_on_market': float,
                'avg_3yr_trend_pct': float,
                'total_transactions': int,
                'active_listings': int
            }
        """
        try:
            # Import here to avoid circular imports
            from db_models_new import Property, Case, Registration, Municipality

            aggregates = {}

            # Get all unique municipalities with properties
            municipalities = self.session.query(Municipality).all()

            for muni in municipalities:
                try:
                    muni_name = muni.name if muni.name else 'Unknown'

                    # Get all properties in this municipality
                    properties = self.session.query(Property).filter(
                        Property.municipality_info.has(Municipality.id == muni.id)
                    ).all()

                    if not properties:
                        continue

                    # Calculate price per sqm average
                    avg_price_per_sqm = self._calculate_avg_price_per_sqm(properties)

                    # Calculate average days on market
                    avg_days = self._calculate_avg_days_on_market(properties)

                    # Calculate 3-year price trend
                    trend_pct = self._calculate_3yr_trend(properties)

                    # Count transactions
                    total_transactions = self._count_transactions(properties)

                    # Count active listings
                    active_count = self._count_active_listings(properties)

                    aggregates[muni_name] = {
                        'avg_price_per_sqm': avg_price_per_sqm,
                        'avg_days_on_market': avg_days,
                        'avg_3yr_trend_pct': trend_pct,
                        'total_transactions': total_transactions,
                        'active_listings': active_count,
                    }

                except Exception as e:
                    logger.warning(f"Error processing municipality {muni_name}: {str(e)}")
                    continue

            self._municipal_cache = aggregates
            return aggregates

        except Exception as e:
            logger.error(f"Error in calculate_municipal_aggregates: {str(e)}")
            return {}

    def calculate_postal_aggregates(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate postal code level statistics.

        Returns per-postal code:
        - avg_price_per_sqm: Average price per square meter
        - annual_transactions: Sales in last 12 months
        - active_listings: Current active listings

        Returns:
            Dict[zip_code] = {
                'avg_price_per_sqm': float,
                'annual_transactions': int,
                'active_listings': int
            }
        """
        try:
            from db_models_new import Property, Case, Registration

            aggregates = {}

            # Get all unique zip codes with properties
            zip_codes = self.session.query(Property.zip_code).distinct().all()

            for (zip_code,) in zip_codes:
                if not zip_code:
                    continue

                try:
                    zip_key = str(zip_code)

                    # Get all properties with this zip code
                    properties = self.session.query(Property).filter(
                        Property.zip_code == zip_code
                    ).all()

                    if not properties:
                        continue

                    # Calculate averages
                    avg_price_per_sqm = self._calculate_avg_price_per_sqm(properties)

                    # Count transactions in last 12 months
                    annual_txn = self._count_transactions_last_12m(properties)

                    # Count active listings
                    active_count = self._count_active_listings(properties)

                    aggregates[zip_key] = {
                        'avg_price_per_sqm': avg_price_per_sqm,
                        'annual_transactions': annual_txn,
                        'active_listings': active_count,
                    }

                except Exception as e:
                    logger.warning(f"Error processing zip code {zip_code}: {str(e)}")
                    continue

            self._postal_cache = aggregates
            return aggregates

        except Exception as e:
            logger.error(f"Error in calculate_postal_aggregates: {str(e)}")
            return {}

    def _calculate_avg_price_per_sqm(self, properties: List) -> float:
        """
        Calculate average price per square meter for property list.

        Args:
            properties: List of Property objects

        Returns:
            Average price per sqm, or 0 if no valid data
        """
        prices = []

        for prop in properties:
            if (not prop.living_area or prop.living_area <= 0 or
                not prop.cases or len(prop.cases) == 0):
                continue

            # Get most recent case with price
            try:
                most_recent = max(
                    prop.cases,
                    key=lambda c: c.created_date if c.created_date else datetime.min
                )

                if most_recent.current_price and most_recent.current_price > 0:
                    price_per_sqm = most_recent.current_price / prop.living_area
                    prices.append(price_per_sqm)
            except (ValueError, AttributeError):
                continue

        if not prices:
            return 0.0

        return sum(prices) / len(prices)

    def _calculate_avg_days_on_market(self, properties: List) -> float:
        """
        Calculate average days on market for property list.

        Args:
            properties: List of Property objects

        Returns:
            Average days on market, or 0 if no valid data
        """
        days_list = []

        for prop in properties:
            if not prop.cases or len(prop.cases) == 0:
                continue

            try:
                # Get most recent case
                most_recent = max(
                    prop.cases,
                    key=lambda c: c.created_date if c.created_date else datetime.min
                )

                if (hasattr(most_recent, 'days_on_market_current') and
                    most_recent.days_on_market_current and
                    most_recent.days_on_market_current > 0):
                    days_list.append(most_recent.days_on_market_current)
            except (ValueError, AttributeError):
                continue

        if not days_list:
            return 0.0

        return sum(days_list) / len(days_list)

    def _calculate_3yr_trend(self, properties: List) -> float:
        """
        Calculate 3-year average price trend for property list.

        Uses registration history to determine appreciation over last 3 years.

        Args:
            properties: List of Property objects

        Returns:
            Average percentage change, or 0 if insufficient data
        """
        trends = []
        three_years_ago = datetime.now() - timedelta(days=365 * 3)

        for prop in properties:
            if not prop.registrations or len(prop.registrations) < 2:
                continue

            try:
                # Get registrations from last 3 years
                recent_regs = [r for r in prop.registrations
                             if r.date and r.date >= three_years_ago]

                if len(recent_regs) < 2:
                    continue

                # Sort by date
                recent_regs.sort(key=lambda r: r.date)

                # Calculate trend
                oldest_price = recent_regs[0].amount
                newest_price = recent_regs[-1].amount

                if oldest_price and oldest_price > 0:
                    trend_pct = ((newest_price - oldest_price) / oldest_price) * 100
                    trends.append(trend_pct)

            except (ValueError, AttributeError, ZeroDivisionError):
                continue

        if not trends:
            return 0.0

        return sum(trends) / len(trends)

    def _count_transactions(self, properties: List) -> int:
        """
        Count total transactions for property list.

        Args:
            properties: List of Property objects

        Returns:
            Total transaction count
        """
        total = 0
        for prop in properties:
            if prop.registrations:
                total += len(prop.registrations)
        return total

    def _count_transactions_last_12m(self, properties: List) -> int:
        """
        Count transactions in last 12 months for property list.

        Args:
            properties: List of Property objects

        Returns:
            Transaction count from last 12 months
        """
        count = 0
        one_year_ago = datetime.now() - timedelta(days=365)

        for prop in properties:
            if not prop.registrations:
                continue

            for reg in prop.registrations:
                if reg.date and reg.date >= one_year_ago:
                    count += 1

        return count

    def _count_active_listings(self, properties: List) -> int:
        """
        Count currently active listings for property list.

        Args:
            properties: List of Property objects

        Returns:
            Count of active listings
        """
        count = 0
        for prop in properties:
            if prop.is_on_market:
                count += 1
        return count

    def get_municipal_aggregate(self, municipality_name: str) -> Dict[str, Any]:
        """
        Retrieve cached municipal aggregate for a specific municipality.

        Args:
            municipality_name: Name of municipality

        Returns:
            Dictionary with aggregate data, or empty dict if not found
        """
        if not self._calculated:
            logger.warning("Aggregates not yet calculated. Call calculate_all_aggregates() first.")
            return {}

        return self._municipal_cache.get(municipality_name, {})

    def get_postal_aggregate(self, zip_code: int) -> Dict[str, Any]:
        """
        Retrieve cached postal code aggregate.

        Args:
            zip_code: ZIP code as integer

        Returns:
            Dictionary with aggregate data, or empty dict if not found
        """
        if not self._calculated:
            logger.warning("Aggregates not yet calculated. Call calculate_all_aggregates() first.")
            return {}

        return self._postal_cache.get(str(zip_code), {})
