# Database Import Optimizations

## Performance Improvements Implemented

### 1. API-Level Filtering (HUGE improvement)
**Before:** Fetching all properties and filtering client-side
**After:** Using `municipalities` API parameter to let the server filter
**Impact:** ~100x faster for initial property discovery

```python
params = {
    'municipalities': 'København,Frederiksberg,Gentofte,...',  # Server filters!
    'sold': 'false',
    'per_page': '50'
}
```

### 2. Bulk Existence Checks (10-100x faster)
**Before:** Checking if each property exists one-by-one
```python
for property_id in property_ids:
    existing = session.query(Property).filter(Property.address_id == property_id).first()
```

**After:** Bulk query with `IN` clause
```python
chunk = property_ids[0:1000]
existing = session.query(Property.address_id).filter(Property.address_id.in_(chunk)).all()
```

**Impact:** Single query instead of thousands

### 3. Batch Commits (5-10x faster)
**Before:** Committing after every property
```python
session.add(property)
session.commit()  # SLOW!
```

**After:** Batch commits every 100 properties
```python
session.add(property)
if count % 100 == 0:
    session.flush()   # Write to DB
    session.commit()  # Commit transaction
```

**Impact:** Reduces transaction overhead significantly

### 4. Connection Pooling
SQLAlchemy automatically uses connection pooling, which reuses database connections
instead of creating new ones for each query.

### 5. Reduced Rate Limiting
Since we're more efficient, we can reduce delays:
- Before: 0.3s between requests
- After: 0.2s (or even 0.1s if API allows)

## Expected Performance

### Without Optimizations:
- Discovery: 30-60 minutes for 10,000 properties (filtering all 3.9M)
- Existence checks: 10-30 seconds per 1,000 properties
- Imports: 5-10 per minute (with commits)
- **Total: ~30 hours for 10,000 properties**

### With Optimizations:
- Discovery: 2-5 minutes (API filters ~50k to target municipalities)
- Existence checks: 1-2 seconds for 10,000 properties (bulk)
- Imports: 30-60 per minute (batch commits)
- **Total: ~3-5 hours for 10,000 properties**

## Additional Optimization Options

### If still too slow, consider:

1. **Parallel Processing**
   - Fetch property details in parallel (5-10 concurrent requests)
   - Use `concurrent.futures.ThreadPoolExecutor`
   - Could achieve 100-200 properties/minute

2. **Bulk Insert Mappings**
   ```python
   # Instead of session.add() one by one:
   property_dicts = [...]
   session.bulk_insert_mappings(Property, property_dicts)
   ```
   - 2-3x faster than add()
   - But harder to handle relationships

3. **Database Indexing**
   - Ensure `address_id` has an index (PRIMARY KEY)
   - Add indexes on frequently queried fields
   - `CREATE INDEX idx_municipality ON properties(municipality_id);`

4. **PostgreSQL COPY Command**
   - Fastest possible import
   - Prepare CSV files, then use COPY
   - Can import 100k+ rows per second
   - But requires more preprocessing

## Current Configuration

- **Batch size:** 100 properties per commit
- **Rate limit:** 0.2s between API requests
- **Chunk size:** 1000 for bulk existence checks
- **API page size:** 50 properties per page

## Usage

```bash
# Dry run to test
python import_copenhagen_area.py --dry-run --limit 100

# Import first 1000 properties
python import_copenhagen_area.py --limit 1000

# Import all (could be 50k-100k properties)
python import_copenhagen_area.py

# Adjust batch size if needed
python import_copenhagen_area.py --batch-size 200
```

## Monitoring Progress

The script shows progress every 50 properties and commits every batch:
```
Page 10: Found 45 properties (total: 483)
   [50/1000] Imported 50, Skipped 0, Errors 0
   💾 Committed batch of 100 properties (total: 100)
   [100/1000] Imported 100, Skipped 0, Errors 0
```

## Troubleshooting

If imports are slow:
1. Check network latency to API (ping times)
2. Check database connection (local vs remote)
3. Monitor PostgreSQL load (`pg_stat_activity`)
4. Consider increasing batch size (--batch-size 200)
5. Consider parallel processing (requires code changes)

If memory issues:
1. Reduce batch size (--batch-size 50)
2. Process in smaller chunks (--limit 5000, repeat)
3. Add periodic `session.expunge_all()` to clear cache
