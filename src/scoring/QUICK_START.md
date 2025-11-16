# Scoring System - Quick Start Guide

Fast reference for common scoring tasks.

## Basic Imports

```python
from src.scoring import (
    CompositeScorer,           # Main scoring engine
    PersonaManager,            # Persona weight configurations
    ScoreInterpretation,       # Score interpretation and badges
    ScorePercentileCalculator, # Percentile ranking
    AggregateCalculator,       # Market statistics
)
```

## Common Tasks

### 1. Score a Single Property

```python
from src.scoring import CompositeScorer
from src.database import db

session = db.get_session()
scorer = CompositeScorer(session)

# Score one property
result = scorer.calculate_property_score(property_obj)

print(f"Score: {result['composite_score']}/100")
print(f"Percentile: {result['percentile_rank']}%")
```

### 2. Score Multiple Properties

```python
scorer = CompositeScorer(session)

# Batch scoring (efficient)
results = scorer.batch_score_properties(property_list)

# Get statistics
stats = scorer.get_summary_statistics()
print(f"Average score: {stats['mean']}")
print(f"Best: {stats['max']}, Worst: {stats['min']}")
```

### 3. Get Persona Weights

```python
from src.scoring import PersonaManager

# List available personas
personas = PersonaManager.list_personas()
# ['space_conscious', 'price_conscious', 'location_conscious', 'condition_investment']

# Get weights for specific persona
weights = PersonaManager.get_persona_weights('price_conscious')
# {
#   'price_per_sqm': 0.30,
#   'price_trend': 0.25,
#   ...
# }

# Get description
description = PersonaManager.get_persona_description('price_conscious')
print(description)
```

### 4. Interpret a Score

```python
from src.scoring import ScoreInterpretation

# Get badge/classification
badge = ScoreInterpretation.get_badge(85.5)
print(f"{badge['label']} {badge['emoji']}")  # Very Good ★★★★

# Get full interpretation
interpretation = ScoreInterpretation.get_interpretation(85.5, percentile=78.5)
print(interpretation)
# Output: "Top 25% - Very Good: Strong property..."

# Get improvement suggestions
suggestions = ScoreInterpretation.get_improvement_suggestions(
    score=65.0,
    factor_scores=result['factors']
)
for suggestion in suggestions:
    print(f"  - {suggestion}")
```

### 5. Calculate Percentiles

```python
from src.scoring import ScorePercentileCalculator

# Get all scores first
scores = [result['composite_score'] for result in results]

# Calculate percentile mapping
percentile_map = ScorePercentileCalculator.calculate_percentiles(scores)

# Get percentile for specific score
percentile = ScorePercentileCalculator.get_percentile_rank(75.0, percentile_map)
print(f"Score 75 is in {percentile}th percentile")
```

### 6. Compare Personas

```python
comparison = PersonaManager.compare_personas('price_conscious', 'location_conscious')

print("Price Conscious vs Location Conscious:")
for factor in comparison['difference']:
    diff = comparison['difference'][factor]
    if diff > 0:
        print(f"  {factor}: +{diff:.2%} (Price favors this)")
    elif diff < 0:
        print(f"  {factor}: {diff:.2%} (Location favors this)")
```

## Score Ranges

| Range | Badge | Emoji | Meaning |
|-------|-------|-------|---------|
| 90-100 | Excellent | ★★★★★ | Outstanding property with exceptional value |
| 80-89 | Very Good | ★★★★ | Strong property with good value proposition |
| 70-79 | Good | ★★★ | Solid property with reasonable value |
| 60-69 | Fair | ★★ | Average property; may have trade-offs |
| 0-59 | Poor | ★ | Below-average property; significant drawbacks |

## Persona Profiles

### Space Conscious
- **Best for:** Growing families, those needing room
- **Top factors:** Size Optimality (25%), Age/Condition (20%), Location (15%)

### Price Conscious
- **Best for:** Investors seeking undervalued properties
- **Top factors:** Price/Sqm (30%), Price Trend (25%), Market Activity (15%)

### Location Conscious
- **Best for:** Those prioritizing neighborhood
- **Top factors:** Location (35%), Market Activity (30%), Price (12%)

### Condition & Investment
- **Best for:** Seeking appreciation potential
- **Top factors:** Condition (25%), Location (20%), Market Momentum (20%)

## Data Quality

Scores include confidence metrics:

```python
result = scorer.calculate_property_score(property_obj)

quality = result['data_quality']
print(f"Confidence: {quality['confidence']*100:.0f}%")
print(f"Missing fields: {quality['missing_fields']}")

# High confidence (>0.8) = reliable score
# Missing fields penalize confidence
```

## Error Handling

```python
from src.scoring import PersonaManager

try:
    weights = PersonaManager.get_persona_weights('invalid_name')
except ValueError as e:
    print(f"Error: {e}")
    # Use default weights instead

try:
    PersonaManager.validate_weights(invalid_dict)
except ValueError as e:
    print(f"Invalid weights: {e}")
```

## Performance Tips

1. **Batch scoring is faster**
   ```python
   # Good: One aggregates calculation for all
   results = scorer.batch_score_properties(all_properties)

   # Avoid: Calculate aggregates separately for each
   for prop in properties:
       result = scorer.calculate_property_score(prop)
   ```

2. **Reset scorer between batches**
   ```python
   scorer = CompositeScorer(session)
   results1 = scorer.batch_score_properties(batch1)
   scorer.reset()
   results2 = scorer.batch_score_properties(batch2)
   ```

3. **Percentile calculation is expensive**
   - Only calculate once after all scores
   - Reuse percentile_map for multiple lookups

## Complete Example

```python
from src.scoring import (
    CompositeScorer,
    PersonaManager,
    ScoreInterpretation,
    ScorePercentileCalculator
)
from src.database import db

session = db.get_session()

# 1. Score properties
scorer = CompositeScorer(session)
results = scorer.batch_score_properties(property_list)

# 2. Calculate percentiles
scores = [r['composite_score'] for r in results]
percentile_map = ScorePercentileCalculator.calculate_percentiles(scores)

# 3. Display results
for result in sorted(results, key=lambda x: x['composite_score'], reverse=True)[:5]:
    score = result['composite_score']
    percentile = ScorePercentileCalculator.get_percentile_rank(score, percentile_map)

    badge = ScoreInterpretation.get_badge(score)
    interpretation = ScoreInterpretation.get_interpretation(score, percentile)

    print(f"\nProperty {result['property_id']}")
    print(f"  {badge['label']} {badge['emoji']} - Score {score}/100")
    print(f"  {interpretation}")
```

## Testing Your Implementation

```python
# Quick validation
from src.scoring import PersonaManager, ScoreInterpretation

# Test 1: All personas have valid weights
for persona in PersonaManager.list_personas():
    weights = PersonaManager.get_persona_weights(persona)
    assert sum(weights.values()) == 1.0, f"{persona} weights invalid"

# Test 2: All score ranges covered
for score in [0, 25, 50, 75, 100]:
    badge = ScoreInterpretation.get_badge(score)
    assert badge is not None, f"No badge for score {score}"

print("All tests passed!")
```

## Need Help?

- See `README.md` for detailed documentation
- Check `factors.py` for individual factor algorithms
- Review `calculator.py` for scoring orchestration
- Look at existing tests in project for examples
