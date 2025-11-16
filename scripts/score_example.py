#!/usr/bin/env python3
"""
Property Scoring System - Usage Examples

Demonstrates how to use the Phase 1 scoring system for scoring individual
and batch properties.

Author: Claude Code
Created: November 14, 2025

Usage:
    python scripts/score_example.py

    Or in your own code:
    from scripts.score_example import score_single_property, score_municipality
"""

import sys
import logging
from typing import List, Dict, Any
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import db
from src.db_models_new import Property, Municipality
from src.scoring import CompositeScorer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def score_single_property(property_id: str) -> Dict[str, Any]:
    """
    Score a single property by its ID.

    Args:
        property_id: Property ID to score

    Returns:
        Scoring result dictionary with all factors and composite score
    """
    session = db.get_session()

    try:
        # Get property
        prop = session.query(Property).filter_by(id=property_id).first()
        if not prop:
            logger.error(f"Property {property_id} not found")
            return {}

        # Initialize scorer
        scorer = CompositeScorer(session)

        # Score property
        result = scorer.calculate_property_score(prop)

        # Print results
        print("\n" + "="*70)
        print(f"PROPERTY SCORE: {prop.address}")
        print("="*70)
        print(f"Property ID: {result['property_id']}")
        print(f"Composite Score: {result['composite_score']}/100")
        print(f"Percentile Rank: {result['percentile_rank']}%")
        print(f"Data Quality: {result['data_quality']['confidence']:.0%} "
              f"({len(result['data_quality']['missing_fields'])} missing fields)")

        print("\nFACTOR BREAKDOWN:")
        print("-" * 70)
        print(f"{'Factor':<25} {'Score':<10} {'Weight':<10} {'Contribution':<15}")
        print("-" * 70)

        for factor_name, details in result['factors'].items():
            print(f"{factor_name:<25} {details['score']:>6.1f}/100 "
                  f"{details['weight']:>8.0%} {details['weighted_contribution']:>12.2f}")

        print("-" * 70)
        print(f"{'TOTAL':<25} {result['composite_score']:>6.1f}/100 "
              f"{'100.0%':>8} {result['composite_score']:>12.2f}")
        print("="*70 + "\n")

        return result

    finally:
        session.close()


def score_municipality(municipality_name: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Score all properties in a municipality.

    Args:
        municipality_name: Name of municipality (e.g., 'København')
        limit: Maximum number of properties to score

    Returns:
        List of scoring result dictionaries
    """
    session = db.get_session()

    try:
        logger.info(f"Loading properties from {municipality_name}...")

        # Get properties in municipality
        properties = session.query(Property).join(
            Municipality
        ).filter(
            Municipality.name == municipality_name
        ).limit(limit).all()

        if not properties:
            logger.error(f"No properties found in {municipality_name}")
            return []

        logger.info(f"Loaded {len(properties)} properties")

        # Initialize scorer
        scorer = CompositeScorer(session)

        # Batch score
        logger.info("Scoring properties...")
        results = scorer.batch_score_properties(properties)

        # Print summary
        stats = scorer.get_summary_statistics()

        print("\n" + "="*70)
        print(f"MUNICIPALITY SCORING SUMMARY: {municipality_name}")
        print("="*70)
        print(f"Properties Scored: {stats['count']}")
        print(f"Score Range: {stats['min']} - {stats['max']}")
        print(f"Average Score: {stats['mean']}")
        print(f"Median Score: {stats['median']}")
        print(f"Std Deviation: {stats['stdev']}")
        print("="*70)

        # Show top 10
        print("\nTOP 10 PROPERTIES:")
        print("-" * 70)
        print(f"{'Rank':<6} {'Score':<10} {'Percentile':<12} {'Property ID':<20}")
        print("-" * 70)

        sorted_results = sorted(
            results,
            key=lambda r: r['composite_score'],
            reverse=True
        )

        for i, result in enumerate(sorted_results[:10], 1):
            print(f"{i:<6} {result['composite_score']:>6.1f}/100 "
                  f"{result['percentile_rank']:>8.1f}% {result['property_id']:<20}")

        print("="*70 + "\n")

        return results

    finally:
        session.close()


def compare_properties(property_ids: List[str]) -> None:
    """
    Compare multiple properties side-by-side.

    Args:
        property_ids: List of property IDs to compare
    """
    session = db.get_session()

    try:
        # Get properties
        properties = session.query(Property).filter(
            Property.id.in_(property_ids)
        ).all()

        if not properties:
            logger.error("No properties found")
            return

        # Initialize scorer
        scorer = CompositeScorer(session)

        # Score all
        results = []
        for prop in properties:
            result = scorer.calculate_property_score(prop, include_percentile=False)
            results.append((prop.address, result))

        # Update percentiles
        all_scores = [r[1]['composite_score'] for r in results]
        for _, result in results:
            composite = result['composite_score']
            result['percentile_rank'] = scorer._calculate_percentile(composite, all_scores)

        # Print comparison
        print("\n" + "="*100)
        print("PROPERTY COMPARISON")
        print("="*100)

        # Header
        print(f"{'Address':<30} {'Score':<10} {'Percentile':<12} {'Confidence':<12}")
        print("-" * 100)

        for address, result in sorted(results, key=lambda x: x[1]['composite_score'], reverse=True):
            confidence = result['data_quality']['confidence']
            print(f"{address:<30} {result['composite_score']:>6.1f}/100 "
                  f"{result['percentile_rank']:>8.1f}% {confidence:>8.0%}")

        # Factor comparison
        print("\n" + "="*100)
        print("FACTOR COMPARISON")
        print("="*100)

        factors = [
            'price_per_sqm', 'size_optimality', 'age_condition',
            'location_premium', 'market_velocity', 'price_trend',
            'floor_desirability', 'transaction_volume'
        ]

        for factor in factors:
            print(f"\n{factor.upper().replace('_', ' ')}:")
            print("-" * 60)
            print(f"{'Address':<30} {'Score':<10} {'Contribution':<15}")
            print("-" * 60)

            for address, result in sorted(results, key=lambda x: x[1]['factors'][factor]['score'], reverse=True):
                score = result['factors'][factor]['score']
                contrib = result['factors'][factor]['weighted_contribution']
                print(f"{address:<30} {score:>6.1f}/100 {contrib:>12.2f}")

        print("="*100 + "\n")

    finally:
        session.close()


def export_scores_to_json(municipality_name: str, output_file: str, limit: int = 100) -> None:
    """
    Export municipality scores to JSON file.

    Args:
        municipality_name: Name of municipality to score
        output_file: Output JSON file path
        limit: Maximum number of properties
    """
    import json

    logger.info(f"Exporting scores for {municipality_name} to {output_file}...")

    results = score_municipality(municipality_name, limit=limit)

    # Convert datetime objects to strings
    for result in results:
        result['calculated_at'] = result['calculated_at'].isoformat()

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Exported {len(results)} scores to {output_file}")


def main() -> None:
    """Main example runner."""

    print("\n" + "="*70)
    print("PROPERTY SCORING SYSTEM - PHASE 1 EXAMPLES")
    print("="*70)

    # Example 1: Score a single property
    print("\n[Example 1] Scoring single property...")
    print("-" * 70)
    session = db.get_session()
    try:
        # Get first property as example
        example_prop = session.query(Property).first()
        if example_prop:
            score_single_property(example_prop.id)
        else:
            print("No properties found in database")
    finally:
        session.close()

    # Example 2: Score municipality
    print("\n[Example 2] Scoring Copenhagen properties...")
    print("-" * 70)
    results = score_municipality('København', limit=50)

    # Example 3: Compare properties
    if len(results) >= 3:
        print("\n[Example 3] Comparing top 3 properties...")
        print("-" * 70)
        top_ids = [r['property_id'] for r in sorted(
            results,
            key=lambda r: r['composite_score'],
            reverse=True
        )[:3]]
        compare_properties(top_ids)

    print("\n" + "="*70)
    print("Examples complete!")
    print("="*70 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        sys.exit(1)
