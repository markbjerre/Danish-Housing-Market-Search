"""
Get a property ID from database that has a case, then fetch from API
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import db
from src.db_models_new import Property, Case

session = db.get_session()

# Get a property with a case
prop_with_case = session.query(Property).filter(Property.cases.any()).first()

print(f"Property ID: {prop_with_case.id}")
print(f"Address: {prop_with_case.address}")
print(f"Number of cases: {len(prop_with_case.cases)}")

# Save the property ID to use in the next test
with open('test_property_id.txt', 'w') as f:
    f.write(prop_with_case.id)

print(f"\n✅ Saved property ID to test_property_id.txt")
print(f"   Use this ID to test API: {prop_with_case.id}")

session.close()
