import numpy as np
from typing import List, Dict
from datetime import datetime
from .models import Property

class PropertyScorer:
    def __init__(self):
        # Scoring weights (must sum to 1.0)
        self.weights = {
            'price_per_sqm': 0.35,    # Price compared to area average
            'size': 0.15,             # Size compared to property type average
            'age': 0.10,              # Building age and condition
            'location': 0.25,         # Location quality (based on area prices)
            'floor': 0.05,            # Floor level (for apartments)
            'days_on_market': 0.10    # How long the property has been listed
        }
        
        # Location premium zones (approximate values for demonstration)
        self.premium_locations = {
            'København K': 1.3,    # Central Copenhagen premium
            'Frederiksberg': 1.2,  # Frederiksberg premium
            'Hellerup': 1.25,     # Hellerup premium
            'Charlottenlund': 1.2, # Charlottenlund premium
            'København Ø': 1.15    # Østerbro premium
        }
        
        # Ideal floor preferences (for apartments)
        self.floor_preferences = {
            0: 0.7,   # Ground floor (less desirable)
            1: 0.9,   # 1st floor
            2: 1.0,   # 2nd floor (optimal)
            3: 0.95,  # 3rd floor
            4: 0.85,  # 4th floor
            5: 0.8    # 5th floor and above
        }

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """Update the scoring weights with new values"""
        # Normalize the weights to sum to 1.0
        total = sum(new_weights.values())
        if total > 0:
            self.weights = {key: value / total for key, value in new_weights.items()}
        
    def calculate_price_score(self, property: Property, comparable_properties: List[Property]) -> float:
        """Score based on price per square meter compared to similar properties in the area"""
        # Calculate average price per sqm for similar properties in the area
        similar_properties = [
            p for p in comparable_properties 
            if p.property_type == property.property_type
            and abs(p.square_meters - property.square_meters) <= 30  # Within 30m² range
        ]
        
        if not similar_properties:
            return 0.5  # Default score if no comparables found
            
        avg_price_per_sqm = np.mean([p.price / p.square_meters for p in similar_properties])
        property_price_per_sqm = property.price / property.square_meters
        
        # Higher score for properties below average price
        ratio = avg_price_per_sqm / property_price_per_sqm
        return min(1.0, max(0.0, ratio - 0.5))  # Normalize to 0-1 range

    def calculate_size_score(self, property: Property, comparable_properties: List[Property]) -> float:
        """Score based on size compared to similar properties"""
        similar_type_properties = [p for p in comparable_properties if p.property_type == property.property_type]
        if not similar_type_properties:
            return 0.5
            
        avg_size = np.mean([p.square_meters for p in similar_type_properties])
        size_ratio = property.square_meters / avg_size
        return min(1.0, max(0.0, (size_ratio - 0.5) / 1.5))

    def calculate_age_score(self, property: Property) -> float:
        """Score based on building age with consideration for renovation potential"""
        if not property.year_built:
            return 0.5
            
        current_year = datetime.now().year
        age = current_year - property.year_built
        
        # Properties between 50-100 years old might have renovation potential
        if 50 <= age <= 100:
            return 0.7  # Good renovation potential
        elif age < 30:
            return 0.9  # Newer buildings
        elif age > 100:
            return 0.4  # Very old buildings
        else:
            return 0.6  # Middle-aged buildings

    def calculate_location_score(self, property: Property) -> float:
        """Score based on location premium zones"""
        for area, premium in self.premium_locations.items():
            if area in property.address:
                return min(1.0, premium / 1.3)  # Normalize by highest premium
        return 0.5  # Default score for non-premium locations

    def calculate_floor_score(self, property: Property) -> float:
        """Score based on floor level for apartments"""
        if property.property_type != 'Apartment' or property.floor is None:
            return 0.5
            
        floor = min(5, property.floor)  # Cap at 5th floor
        return self.floor_preferences.get(floor, 0.7)

    def calculate_days_on_market_score(self, property: Property) -> float:
        """Score based on how long the property has been on the market"""
        # property.listing_date is already a datetime object
        days_on_market = (datetime.now() - property.listing_date).days
        
        if days_on_market < 0:  # Future listing date
            return 0.5
        elif days_on_market < 7:  # New listing
            return 0.9
        elif days_on_market < 30:  # Recent listing
            return 0.7
        elif days_on_market < 90:  # Standard listing time
            return 0.5
        else:  # Long time on market
            return 0.3

    def score_property(self, property: Property, comparable_properties: List[Property]) -> float:
        """Calculate overall score for a property"""
        scores = {
            'price_per_sqm': self.calculate_price_score(property, comparable_properties),
            'size': self.calculate_size_score(property, comparable_properties),
            'age': self.calculate_age_score(property),
            'location': self.calculate_location_score(property),
            'floor': self.calculate_floor_score(property),
            'days_on_market': self.calculate_days_on_market_score(property)
        }
        
        # Calculate weighted average
        weighted_score = sum(scores[key] * self.weights[key] for key in scores)
        
        # Convert to 0-100 scale
        return round(weighted_score * 100, 1)