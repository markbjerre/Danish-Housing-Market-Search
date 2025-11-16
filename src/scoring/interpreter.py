"""
Score Interpretation and Percentile Ranking

Provides interpretation of property scores with badges, descriptions,
and percentile ranking functionality.

Author: Claude Code
Created: November 14, 2025
"""

from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class ScorePercentileCalculator:
    """
    Calculates and maps property scores to percentile rankings.

    Provides percentile analysis to show how a property ranks
    relative to the market.
    """

    @staticmethod
    def calculate_percentiles(scores: List[float]) -> Dict[float, float]:
        """
        Calculate percentile mapping for all scores.

        Creates a dictionary mapping each unique score to its percentile rank.
        Percentile = (count of scores below this score / total scores) * 100

        Args:
            scores: List of composite scores (0-100)

        Returns:
            Dictionary mapping score -> percentile rank (0-100)

        Raises:
            ValueError: If scores list is empty or invalid
        """
        if not scores:
            raise ValueError("Scores list cannot be empty")

        if len(scores) < 2:
            logger.warning("Only 1 score provided; percentile ranking may be unreliable")

        # Remove duplicates and sort
        unique_scores = sorted(set(scores))
        total_count = len(scores)

        percentile_map = {}

        for score in unique_scores:
            try:
                # Count scores strictly below this score
                below_count = sum(1 for s in scores if s < score)
                percentile = (below_count / total_count) * 100.0
                percentile_map[score] = round(percentile, 1)
            except ZeroDivisionError:
                logger.warning(f"Division by zero for score {score}")
                percentile_map[score] = 50.0

        return percentile_map

    @staticmethod
    def get_percentile_rank(score: float, percentile_map: Dict[float, float]) -> float:
        """
        Get percentile rank for a specific score using precomputed map.

        Args:
            score: The composite score to look up (0-100)
            percentile_map: Dictionary from calculate_percentiles()

        Returns:
            Percentile rank (0-100), or 50 if score not found

        Raises:
            ValueError: If percentile_map is empty
        """
        if not percentile_map:
            raise ValueError("Percentile map cannot be empty")

        if score in percentile_map:
            return percentile_map[score]

        # Find closest scores and interpolate
        scores = sorted(percentile_map.keys())

        if score < scores[0]:
            return 0.0
        if score > scores[-1]:
            return 100.0

        # Find bracketing scores
        for i in range(len(scores) - 1):
            if scores[i] <= score <= scores[i + 1]:
                # Linear interpolation
                s1, s2 = scores[i], scores[i + 1]
                p1, p2 = percentile_map[s1], percentile_map[s2]

                if s2 == s1:
                    return p1

                # Interpolate percentile
                percentile = p1 + (score - s1) * (p2 - p1) / (s2 - s1)
                return round(percentile, 1)

        return 50.0


class ScoreInterpretation:
    """
    Interprets property scores with badges and descriptions.

    Maps numeric scores (0-100) to qualitative categories and provides
    human-readable interpretation of what a score means.
    """

    BADGES: Dict[str, Dict[str, Any]] = {
        'excellent': {
            'min': 90,
            'max': 100,
            'label': 'Excellent',
            'color': '#27AE60',  # Green
            'emoji': '★★★★★',
            'description': 'Outstanding property with exceptional value'
        },
        'very_good': {
            'min': 80,
            'max': 89,
            'label': 'Very Good',
            'color': '#52BE80',  # Light green
            'emoji': '★★★★',
            'description': 'Strong property with good value proposition'
        },
        'good': {
            'min': 70,
            'max': 79,
            'label': 'Good',
            'color': '#F39C12',  # Orange
            'emoji': '★★★',
            'description': 'Solid property with reasonable value'
        },
        'fair': {
            'min': 60,
            'max': 69,
            'label': 'Fair',
            'color': '#E67E22',  # Dark orange
            'emoji': '★★',
            'description': 'Average property; may have trade-offs'
        },
        'poor': {
            'min': 0,
            'max': 59,
            'label': 'Poor',
            'color': '#E74C3C',  # Red
            'emoji': '★',
            'description': 'Below-average property; significant drawbacks'
        },
    }

    @staticmethod
    def get_badge(score: float) -> Dict[str, Any]:
        """
        Get badge information for a score.

        Args:
            score: Composite score (0-100)

        Returns:
            Dictionary with badge label, color, emoji, and description

        Raises:
            ValueError: If score is outside 0-100 range
        """
        if not 0 <= score <= 100:
            raise ValueError(f"Score must be between 0-100, got {score}")

        for badge_data in ScoreInterpretation.BADGES.values():
            if badge_data['min'] <= score <= badge_data['max']:
                return badge_data.copy()

        # Fallback (should not reach here)
        return ScoreInterpretation.BADGES['fair']

    @staticmethod
    def get_interpretation(score: float, percentile: Optional[float] = None) -> str:
        """
        Get human-readable interpretation of a score.

        Combines score level with percentile rank (if available) to provide
        context about how the property ranks relative to market.

        Args:
            score: Composite score (0-100)
            percentile: Percentile rank (0-100), optional

        Returns:
            Human-readable interpretation string

        Raises:
            ValueError: If score is invalid
        """
        if not 0 <= score <= 100:
            raise ValueError(f"Score must be between 0-100, got {score}")

        badge = ScoreInterpretation.get_badge(score)

        if percentile is not None:
            if not 0 <= percentile <= 100:
                raise ValueError(f"Percentile must be between 0-100, got {percentile}")

            if percentile >= 90:
                rank = "Top 10%"
            elif percentile >= 75:
                rank = "Top 25%"
            elif percentile >= 50:
                rank = "Top 50%"
            elif percentile >= 25:
                rank = "Below median"
            else:
                rank = "Bottom 25%"

            return (
                f"{rank} - {badge['label']}: {badge['description']} "
                f"(Score: {score}, Percentile: {percentile:.1f}%)"
            )
        else:
            return (
                f"{badge['label']}: {badge['description']} "
                f"(Score: {score})"
            )

    @staticmethod
    def get_score_range_description(min_score: float, max_score: float) -> Dict[str, Any]:
        """
        Get description of a range of scores.

        Useful for explaining what properties fall into a particular score band.

        Args:
            min_score: Minimum score in range (0-100)
            max_score: Maximum score in range (0-100)

        Returns:
            Dictionary with label and description

        Raises:
            ValueError: If score range is invalid
        """
        if not (0 <= min_score <= 100 and 0 <= max_score <= 100):
            raise ValueError("Scores must be between 0-100")

        if min_score > max_score:
            raise ValueError("min_score cannot be greater than max_score")

        # Determine which badges overlap with this range
        matching_badges = []

        for badge_name, badge_data in ScoreInterpretation.BADGES.items():
            # Check for overlap
            if not (max_score < badge_data['min'] or min_score > badge_data['max']):
                matching_badges.append(badge_data)

        if not matching_badges:
            return {
                'range': f"{min_score}-{max_score}",
                'label': 'Unknown',
                'description': 'No properties in this score range'
            }

        if len(matching_badges) == 1:
            badge = matching_badges[0]
            return {
                'range': f"{min_score}-{max_score}",
                'label': badge.get('label', 'Unknown'),
                'color': badge.get('color', ''),
                'description': badge.get('description', '')
            }

        # Multiple badges - return combined view
        labels = [b.get('label', 'Unknown') for b in matching_badges]
        return {
            'range': f"{min_score}-{max_score}",
            'label': ' / '.join(labels),
            'description': f"Properties spanning {', '.join(labels)} categories"
        }

    @staticmethod
    def get_improvement_suggestions(
        score: float,
        factor_scores: Optional[Dict[str, float]] = None
    ) -> List[str]:
        """
        Get suggestions for improving a property's score.

        Based on which factors are lowest, provides actionable suggestions.

        Args:
            score: Current composite score
            factor_scores: Optional dict of factor_name -> score for detailed analysis

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        if score >= 90:
            suggestions.append("Property is already in excellent condition!")
            return suggestions

        if score >= 70:
            suggestions.append("Property is above average. Minor improvements could boost appeal.")
        else:
            suggestions.append("Property has several improvement opportunities.")

        # If factor scores available, identify weak areas
        if factor_scores:
            weak_factors = {
                name: score for name, score in factor_scores.items()
                if score < 60
            }

            if weak_factors:
                suggestions.append("\nLargest improvement opportunities:")

                # Sort by lowest score
                for factor, factor_score in sorted(
                    weak_factors.items(),
                    key=lambda x: x[1]
                ):
                    if factor == 'age_condition':
                        suggestions.append(
                            f"- Consider renovations to improve building condition (current: {factor_score:.0f}/100)"
                        )
                    elif factor == 'price_per_sqm':
                        suggestions.append(
                            f"- Price may be above market average; consider adjustment (current: {factor_score:.0f}/100)"
                        )
                    elif factor == 'location_premium':
                        suggestions.append(
                            f"- Location has limited premium appeal; highlight unique attributes (current: {factor_score:.0f}/100)"
                        )
                    elif factor == 'market_velocity':
                        suggestions.append(
                            f"- Property is taking longer to sell; may need marketing boost (current: {factor_score:.0f}/100)"
                        )
                    elif factor == 'price_trend':
                        suggestions.append(
                            f"- Price appreciation is lagging market; verify pricing strategy (current: {factor_score:.0f}/100)"
                        )

        return suggestions
