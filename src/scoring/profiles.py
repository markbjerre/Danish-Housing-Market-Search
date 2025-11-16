"""
Property Scoring Profiles - Persona-Based Weight Configurations

Provides predefined weight configurations for different buyer personas.
Each persona emphasizes different scoring factors based on priorities.

Author: Claude Code
Created: November 14, 2025
"""

from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class PersonaManager:
    """
    Manages predefined scoring personas with custom weight distributions.

    Provides 4 personas representing different buyer priorities:
    - Space Conscious: Prioritizes size and location
    - Price Conscious: Focuses on value and market trends
    - Location Conscious: Emphasizes location and market activity
    - Condition & Investment: Prioritizes condition and appreciation potential

    All weights sum to 1.0 (100%) for normalization.
    """

    PERSONAS: Dict[str, Dict[str, float]] = {
        'space_conscious': {
            'size_optimality': 0.25,
            'age_condition': 0.20,
            'location_premium': 0.15,
            'market_velocity': 0.12,
            'price_per_sqm': 0.15,
            'price_trend': 0.08,
            'floor_desirability': 0.03,
            'transaction_volume': 0.02,
        },
        'price_conscious': {
            'price_per_sqm': 0.30,
            'price_trend': 0.25,
            'market_velocity': 0.15,
            'location_premium': 0.12,
            'transaction_volume': 0.10,
            'age_condition': 0.05,
            'size_optimality': 0.02,
            'floor_desirability': 0.01,
        },
        'location_conscious': {
            'location_premium': 0.35,
            'market_velocity': 0.15,
            'transaction_volume': 0.15,
            'age_condition': 0.12,
            'price_per_sqm': 0.12,
            'size_optimality': 0.08,
            'price_trend': 0.02,
            'floor_desirability': 0.01,
        },
        'condition_investment': {
            'age_condition': 0.25,
            'location_premium': 0.20,
            'market_velocity': 0.20,
            'price_trend': 0.15,
            'size_optimality': 0.10,
            'price_per_sqm': 0.08,
            'transaction_volume': 0.01,
            'floor_desirability': 0.01,
        },
    }

    @staticmethod
    def get_persona_weights(persona_name: str) -> Optional[Dict[str, float]]:
        """
        Retrieve weight configuration for a specific persona.

        Args:
            persona_name: Name of the persona (e.g., 'price_conscious')

        Returns:
            Dictionary mapping factor names to weights (sum to 1.0),
            or None if persona not found

        Raises:
            ValueError: If persona name is invalid
        """
        persona_name_lower = persona_name.lower().strip()

        if persona_name_lower not in PersonaManager.PERSONAS:
            valid = ', '.join(PersonaManager.PERSONAS.keys())
            raise ValueError(
                f"Unknown persona '{persona_name}'. "
                f"Valid personas: {valid}"
            )

        weights = PersonaManager.PERSONAS[persona_name_lower]

        # Validate weights
        PersonaManager.validate_weights(weights)

        return weights.copy()

    @staticmethod
    def list_personas() -> List[str]:
        """
        Get list of available persona names.

        Returns:
            List of persona names available
        """
        return list(PersonaManager.PERSONAS.keys())

    @staticmethod
    def validate_weights(weights_dict: Dict[str, float]) -> bool:
        """
        Validate that weights sum to 1.0 within tolerance.

        Args:
            weights_dict: Dictionary of factor weights

        Returns:
            True if valid (weights sum to 1.0 +/- 0.001)

        Raises:
            ValueError: If weights don't sum to approximately 1.0
        """
        if not weights_dict:
            raise ValueError("Weights dictionary cannot be empty")

        total = sum(weights_dict.values())
        tolerance = 0.001

        if abs(total - 1.0) > tolerance:
            raise ValueError(
                f"Weights must sum to 1.0, got {total:.4f}. "
                f"Difference: {abs(total - 1.0):.4f}"
            )

        return True

    @staticmethod
    def get_persona_description(persona_name: str) -> str:
        """
        Get human-readable description of a persona's priorities.

        Args:
            persona_name: Name of the persona

        Returns:
            Description of the persona's characteristics
        """
        descriptions = {
            'space_conscious': (
                'Prioritizes living space and comfort. Values size optimality (25%) and '
                'property condition (20%). Seeks good locations (15%) with balanced pricing. '
                'Ideal for growing families or those needing room.'
            ),
            'price_conscious': (
                'Focuses on value for money. Emphasizes price per sqm (30%) and market '
                'trends (25%) to find bargains. Trades location premium and size for lower costs. '
                'Ideal for investors seeking undervalued properties.'
            ),
            'location_conscious': (
                'Location is paramount. Prioritizes location premium (35%) and market '
                'activity (30%). Accepts higher prices for desirable areas. '
                'Ideal for those prioritizing neighborhood and lifestyle.'
            ),
            'condition_investment': (
                'Balanced approach for investment-minded buyers. Values property condition (25%), '
                'location (20%), market momentum (20%), and price trends (15%). '
                'Ideal for those seeking appreciation potential in good areas.'
            ),
        }

        return descriptions.get(
            persona_name.lower().strip(),
            'Unknown persona'
        )

    @staticmethod
    def compare_personas(persona1: str, persona2: str) -> Dict[str, Dict[str, float]]:
        """
        Compare weight distributions between two personas.

        Useful for understanding differences in scoring priorities.

        Args:
            persona1: First persona name
            persona2: Second persona name

        Returns:
            Dictionary showing weights for both personas and differences

        Raises:
            ValueError: If either persona name is invalid
        """
        try:
            weights1 = PersonaManager.get_persona_weights(persona1)
            weights2 = PersonaManager.get_persona_weights(persona2)
        except ValueError as e:
            raise ValueError(f"Invalid persona in comparison: {str(e)}")

        # Get all factors
        all_factors = set(weights1.keys()) | set(weights2.keys())

        comparison = {
            'persona1': {factor: weights1.get(factor, 0.0) for factor in all_factors},
            'persona2': {factor: weights2.get(factor, 0.0) for factor in all_factors},
            'difference': {}
        }

        # Calculate differences (persona1 - persona2)
        for factor in all_factors:
            diff = weights1.get(factor, 0.0) - weights2.get(factor, 0.0)
            comparison['difference'][factor] = round(diff, 4)

        return comparison

    @staticmethod
    def get_most_important_factors(
        persona_name: str,
        top_n: int = 3
    ) -> List[tuple]:
        """
        Get the most important factors for a persona.

        Args:
            persona_name: Name of the persona
            top_n: Number of top factors to return (default: 3)

        Returns:
            List of tuples (factor_name, weight) sorted by weight descending

        Raises:
            ValueError: If persona name is invalid or top_n is invalid
        """
        if top_n < 1:
            raise ValueError("top_n must be at least 1")

        weights = PersonaManager.get_persona_weights(persona_name)

        # Sort by weight descending
        sorted_factors = sorted(
            weights.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return sorted_factors[:top_n]
