from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Property:
    id: int
    address: str
    price: float
    square_meters: float
    property_type: str
    latitude: float
    longitude: float
    listing_date: datetime
    rooms: Optional[int] = None
    year_built: Optional[int] = None
    floor: Optional[int] = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'address': self.address,
            'price': self.price,
            'square_meters': self.square_meters,
            'price_per_sqm': self.price / self.square_meters,
            'property_type': self.property_type,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'listing_date': self.listing_date.isoformat(),
            'rooms': self.rooms,
            'year_built': self.year_built,
            'floor': self.floor
        }