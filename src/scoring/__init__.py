"""
Property Scoring System - Phase 1

Complete implementation of 8-factor property scoring system for Danish housing market.

Provides:
- CompositeScorer: Main scoring orchestrator
- PropertyScorer: Simplified scoring interface with persona support
- 8 Scoring factors with normalized 0-100 scales
- Market aggregate calculator for municipal and postal code statistics
- Persona-based weight configurations
- Score interpretation with badges and percentiles
- Batch processing with percentile ranking
- Data quality assessment

Usage (CompositeScorer):
    from src.scoring import CompositeScorer
    from src.database import db

    session = db.get_session()
    scorer = CompositeScorer(session)
    score = scorer.calculate_property_score(property_obj)
    print(f"Score: {score['composite_score']}, Percentile: {score['percentile_rank']}")

Usage (PersonaManager):
    from src.scoring import PersonaManager

    weights = PersonaManager.get_persona_weights('price_conscious')
    personas = PersonaManager.list_personas()

Usage (ScoreInterpretation):
    from src.scoring import ScoreInterpretation

    badge = ScoreInterpretation.get_badge(85.5)
    description = ScoreInterpretation.get_interpretation(85.5, percentile=78.5)

Author: Claude Code
Created: November 14, 2025
"""

from .calculator import CompositeScorer
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
from .profiles import PersonaManager
from .interpreter import ScorePercentileCalculator, ScoreInterpretation

__all__ = [
    'CompositeScorer',
    'AggregateCalculator',
    'PersonaManager',
    'ScorePercentileCalculator',
    'ScoreInterpretation',
    'PricePerSqmFactor',
    'SizeOptimalityFactor',
    'AgeConditionFactor',
    'LocationPremiumFactor',
    'MarketVelocityFactor',
    'PriceTrendFactor',
    'FloorDesirabilityFactor',
    'TransactionVolumeFactor',
]

__version__ = '1.1.0'
__author__ = 'Claude Code'
__phase__ = 'Phase 1 (Days 1-7): Core 8-factor implementation + Phase 2: Personas and Interpretation'
