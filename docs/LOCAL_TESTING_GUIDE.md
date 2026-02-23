# Local Testing Guide

## Quick Setup for Testing Search Fixes

### Option 1: Use Local Database (Fastest)
If you have PostgreSQL running locally with the housing database:

```bash
# Navigate to project
cd "Danish Housing Market Search"

# Create virtual environment (if not exists)
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Create .env file with local database
echo DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/housing_db > .env

# Start Flask app
cd webapp
python app.py

# Access at http://localhost:5000
```

### Option 2: Use Portable Version (No Database)
Quick testing without setting up PostgreSQL locally:

```bash
cd portable

pip install -r requirements_portable.txt

python app_portable.py

# Access at http://localhost:5000
```

## Testing Checklist

### Search Fixes
- [ ] Text search on home page (from /housing) works normally
- [ ] Search page filters work (municipality, price range, etc.)
- [ ] Text search respects **market status filter** (should show ~3,600 on-market, not 7,000)
- [ ] Text search with "Copenhagen" returns reasonable count
- [ ] Sort dropdown works (price asc/desc, size, etc.)
- [ ] Municipality filter applied in text search

### What Changed
1. **Backend**: Added `is_on_market` filter to `/api/text-search` endpoint
2. **Frontend**: Text search now passes `municipality` and `on_market` parameters
3. **Result**: Should see ~3,600 on-market properties instead of 7,000

## Testing Results to Log
When testing locally, please note:
- Total properties found with text search
- With market status filter enabled vs disabled
- Sort order working/not working
- Any errors in browser console (F12)

## When Ready for Production
Once all testing passes locally, commit and we'll deploy once with all fixes.
