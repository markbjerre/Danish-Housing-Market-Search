import sys
sys.path.append('.')
from src.database import db
from src.db_models_new import Property, Municipality
from sqlalchemy import func

s = db.get_session()

total = s.query(Property).count()
print(f'=== Import Status ===')
print(f'Total Properties: {total:,}\n')

print('\nBreakdown by Municipality:')
# Get municipality info through the relationship
muni_data = s.query(Municipality.name, func.count(Property.id)).join(
    Property.municipality_info
).group_by(Municipality.name).order_by(func.count(Property.id).desc()).all()

for name, count in muni_data:
    print(f'  {name}: {count:,}')

s.close()
