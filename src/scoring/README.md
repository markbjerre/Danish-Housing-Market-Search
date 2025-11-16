# Property Scoring System

Complete 8-factor scoring system for analyzing Danish housing market properties. Provides normalized scores (0-100), percentile rankings, and persona-based weight configurations for different buyer types.

## Overview

The scoring system evaluates properties across 8 weighted factors:

| Factor | Weight | Description |
|--------|--------|-------------|
| Price Per Sqm | 20% | Property price relative to municipal average |
| Age Condition | 15% | Building age and condition based on year built/renovated |
| Location Premium | 18% | Geographic desirability (Copenhagen, major cities, etc.) |
| Price Trend | 15% | 3-year price appreciation relative to market |
| Market Velocity | 10% | Days on market compared to area average |
| Size Optimality | 12% | Gaussian distribution centered at 100 sqm |
| Transaction Volume | 5% | Market activity in postal code area |
| Floor Desirability | 5% | Floor level preference (apartments) |

**Total Weight: 100%**

All factors normalize to 0-100 scale with intelligent handling of missing data (defaults to 50 = neutral).

## Module Files

### factors.py
Individual scoring factor implementations.

**Classes:**
- `PricePerSqmFactor` - Compares property price per sqm to municipal average
- `SizeOptimalityFactor` - Gaussian curve centered at 100 sqm
- `AgeConditionFactor` - Linear scale 0-125 years
- `LocationPremiumFactor` - Municipality tiers with income adjustment
- `MarketVelocityFactor` - Days on market comparison
- `PriceTrendFactor` - 3-year appreciation trend
- `FloorDesirabilityFactor` - Floor level scoring
- `TransactionVolumeFactor` - Postal code activity level

**Key Method:** `calculate(property_obj, aggregates) -> float`

### calculator.py
Main scoring orchestrator that combines all factors.

**Class: CompositeScorer**

```python
from src.scoring import CompositeScorer
from src.database import db

session = db.get_session()
scorer = CompositeScorer(session)

# Score a single property
result = scorer.calculate_property_score(property_obj)
print(f"Score: {result['composite_score']}/100")
print(f"Percentile: {result['percentile_rank']}%")

# Score multiple properties efficiently
results = scorer.batch_score_properties(property_list)

# Get summary statistics
stats = scorer.get_summary_statistics()
print(f"Average score: {stats['mean']}")
```

**Key Methods:**
- `calculate_property_score(property_obj, include_percentile=True)` - Calculate score with detailed breakdown
- `batch_score_properties(properties, batch_size=100)` - Efficient batch processing
- `get_summary_statistics()` - Market-wide stats
- `reset()` - Reset scorer state between batches

### aggregates.py
Pre-calculated market statistics for factor normalization.

**Class: AggregateCalculator**

```python
from src.scoring import AggregateCalculator

calc = AggregateCalculator(session)
aggregates = calc.calculate_all_aggregates()

# Returns structure:
# {
#   'municipal': {
#     'municipality_name': {
#       'avg_price_per_sqm': float,
#       'avg_days_on_market': float,
#       'avg_3yr_trend_pct': float,
#       'total_transactions': int,
#       'active_listings': int
#     }
#   },
#   'postal_code_aggregates': {
#     'postal_code': {
#       'avg_price_per_sqm': float,
#       'annual_transactions': int,
#       'active_listings': int
#     }
#   }
# }
```

**Key Methods:**
- `calculate_all_aggregates()` - Calculate municipal and postal aggregates
- `calculate_municipal_aggregates()` - Municipal level only
- `calculate_postal_aggregates()` - Postal code level only

### profiles.py
Predefined persona configurations with different weight distributions.

**Class: PersonaManager**

```python
from src.scoring import PersonaManager

# Get available personas
personas = PersonaManager.list_personas()
# ['space_conscious', 'price_conscious', 'location_conscious', 'condition_investment']

# Get weights for a persona
weights = PersonaManager.get_persona_weights('price_conscious')
# {
#   'price_per_sqm': 0.30,
#   'price_trend': 0.25,
#   'market_velocity': 0.15,
#   'location_premium': 0.12,
#   'transaction_volume': 0.10,
#   'age_condition': 0.05,
#   'size_optimality': 0.02,
#   'floor_desirability': 0.01
# }

# Get persona description
desc = PersonaManager.get_persona_description('location_conscious')

# Compare two personas
comparison = PersonaManager.compare_personas('price_conscious', 'location_conscious')

# Get top 3 factors for persona
top_factors = PersonaManager.get_most_important_factors('space_conscious', top_n=3)
```

**Personas:**

1. **Space Conscious** - Prioritizes living space and comfort
   - Size Optimality: 25% | Age Condition: 20% | Location: 15%

2. **Price Conscious** - Focuses on value and market trends
   - Price/Sqm: 30% | Price Trend: 25% | Market Activity: 15%

3. **Location Conscious** - Emphasizes location and neighborhood
   - Location: 35% | Market Activity: 30% | Price: 12%

4. **Condition & Investment** - Seeks appreciation potential
   - Age/Condition: 25% | Location: 20% | Market Momentum: 20%

**Key Methods:**
- `list_personas()` - Get available persona names
- `get_persona_weights(persona_name)` - Get weight dictionary
- `get_persona_description(persona_name)` - Human-readable description
- `validate_weights(weights_dict)` - Ensure weights sum to 1.0
- `compare_personas(persona1, persona2)` - Compare two personas
- `get_most_important_factors(persona_name, top_n=3)` - Top factors for persona

### interpreter.py
Score interpretation and percentile ranking utilities.

**Class: ScorePercentileCalculator**

```python
from src.scoring import ScorePercentileCalculator

scores = [45.0, 55.0, 65.0, 75.0, 85.0, 95.0]

# Calculate percentile map
percentile_map = ScorePercentileCalculator.calculate_percentiles(scores)

# Get percentile for specific score
percentile = ScorePercentileCalculator.get_percentile_rank(75.0, percentile_map)
# 50.0 (median)
```

**Class: ScoreInterpretation**

```python
from src.scoring import ScoreInterpretation

# Get badge for score
badge = ScoreInterpretation.get_badge(85.5)
# {
#   'min': 80,
#   'max': 89,
#   'label': 'Very Good',
#   'color': '#52BE80',
#   'emoji': '★★★★',
#   'description': 'Strong property with good value proposition'
# }

# Get human-readable interpretation
interpretation = ScoreInterpretation.get_interpretation(85.5, percentile=78.5)
# "Top 25% - Very Good: Strong property with good value proposition (Score: 85.5, Percentile: 78.5%)"

# Get description of score range
range_desc = ScoreInterpretation.get_score_range_description(70, 90)
# {'range': '70-90', 'label': 'Excellent / Very Good / Good', ...}

# Get improvement suggestions
suggestions = ScoreInterpretation.get_improvement_suggestions(75.0)
# ['Property is above average. Minor improvements could boost appeal.', ...]
```

**Score Badges:**
- **Excellent** (90-100): Outstanding property with exceptional value
- **Very Good** (80-89): Strong property with good value proposition
- **Good** (70-79): Solid property with reasonable value
- **Fair** (60-69): Average property; may have trade-offs
- **Poor** (0-59): Below-average property; significant drawbacks

## Complete Usage Example

```python
from src.scoring import (
    CompositeScorer,
    PersonaManager,
    ScoreInterpretation,
    AggregateCalculator
)
from src.database import db

# Initialize database session
session = db.get_session()

# Create scorer
scorer = CompositeScorer(session)

# Score all properties in a municipality
properties = session.query(Property).filter(
    Property.municipality_info.has(Municipality.name == 'København')
).limit(100).all()

scores = scorer.batch_score_properties(properties)

# Filter to top 10 properties
top_10 = sorted(scores, key=lambda x: x['composite_score'], reverse=True)[:10]

# Display results with interpretation
for i, score_result in enumerate(top_10, 1):
    score = score_result['composite_score']
    percentile = score_result['percentile_rank']

    badge = ScoreInterpretation.get_badge(score)
    interpretation = ScoreInterpretation.get_interpretation(score, percentile)

    print(f"{i}. Property {score_result['property_id']}")
    print(f"   Score: {score}/100 {badge['emoji']}")
    print(f"   {interpretation}")
    print()

# Get market statistics
stats = scorer.get_summary_statistics()
print(f"Market average: {stats['mean']}/100")
print(f"Score range: {stats['min']}-{stats['max']}")
```

## Type Hints and Data Structures

All functions include complete type hints. Key types:

```python
# Score result structure
{
    'property_id': str,
    'composite_score': float,  # 0-100
    'percentile_rank': float,  # 0-100
    'factors': {
        'factor_name': {
            'score': float,              # 0-100
            'weight': float,             # 0.0-1.0
            'description': str,
            'weighted_contribution': float
        }
    },
    'calculated_at': datetime,
    'data_quality': {
        'missing_fields': List[str],
        'confidence': float              # 0.0-1.0
    }
}

# Badge structure
{
    'min': int,           # Min score for badge
    'max': int,           # Max score for badge
    'label': str,         # e.g., 'Very Good'
    'color': str,         # Hex color code
    'emoji': str,         # Visual representation
    'description': str    # Human-readable description
}
```

## Error Handling

All functions include robust error handling:

```python
from src.scoring import PersonaManager

try:
    weights = PersonaManager.get_persona_weights('invalid_persona')
except ValueError as e:
    print(f"Invalid persona: {e}")

try:
    PersonaManager.validate_weights({'factor': 0.5})  # Sum != 1.0
except ValueError as e:
    print(f"Invalid weights: {e}")
```

## Performance Considerations

- **Single property:** ~10-50ms depending on data completeness
- **Batch (100 properties):** ~1-5s (aggregates calculated once)
- **Percentile ranking:** O(n log n) for n properties
- **Memory:** Aggregates cached in scorer instance

## Data Requirements

Properties must include:

- `living_area` (sqm)
- `zip_code`
- `cases` (relationship with current_price, created_date, days_on_market_current)
- `registrations` (relationship with amount, date)
- `municipality_info` (relationship with name)
- `main_building` (relationship with year_built, year_renovated)
- `floor` (optional)
- `is_on_market` (boolean)

Missing fields gracefully default to 50 (neutral score).

## Testing

```bash
cd /path/to/Danish-Housing-Market-Search

# Run basic tests
python3 -c "
from src.scoring import PersonaManager, ScoreInterpretation
personas = PersonaManager.list_personas()
badge = ScoreInterpretation.get_badge(85.5)
print('Tests passed!')
"
```

## Future Enhancements

- Real estate transaction history analysis
- Predictive price estimation using ML models
- Custom weight profiles for specific investor types
- Integration with external market data sources
- Score caching with Redis
- REST API for remote scoring

## Architecture Notes

The scoring system is designed for:

1. **Modularity**: Each factor is independent and reusable
2. **Extensibility**: Easy to add new factors (just inherit from base)
3. **Performance**: Aggregates calculated once, reused for all properties
4. **Flexibility**: Persona-based weights without code changes
5. **Robustness**: Graceful handling of missing/invalid data
6. **Interpretability**: Clear explanation of scores and factors
