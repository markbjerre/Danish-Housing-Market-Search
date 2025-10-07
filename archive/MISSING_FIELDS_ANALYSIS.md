# Analysis of MISSING FIELDS from Degnebakken 24 Response

Based on the successful API response we received, here are the KEY FIELDS we're NOT capturing:

## 🆕 CRITICAL MISSING FIELD: `cases` array

The `cases` array contains the **actual listing/offering information** including:

### Structure:
```json
{
  "cases": [
    {
      "caseID": "f2687747-0bd7-4ded-aa4c-8dc123b9e624",
      "status": "open",
      "price": 2995000,
      "created": "2025-03-22T...",
      "modified": "2025-06-...",
      "timeOnMarket": {
        "current": {
          "days": 189
        },
        "total": {
          "days": 189,
          "realtors": [
            {
              "days": 189,
              "realtorId": "e09560ae-906d-486c-b2ba-a57e1e06f211",
              "realtorName": "EDC Poul Erik Bech"
            }
          ]
        }
      },
      "priceChanges": [
        {
          "created": "2025-06-...",
          "newPrice": 2995000,
          "priceChange": -150000
        },
        {
          "created": "2025-05-...",
          "newPrice": 3145000,
          "priceChange": -100000
        }
      ],
      "realtor": {
        ... extensive realtor info ...
      }
    }
  ]
}
```

### Fields in `cases` array:
1. **caseID** - The offering/case UUID (this is the `udbud` parameter!)
2. **status** - "open", "sold", "withdrawn", etc.
3. **price** - Current asking price
4. **created** - When the listing was created (THE ANSWER TO YOUR QUESTION!)
5. **modified** - Last modification date
6. **timeOnMarket** - Detailed time tracking:
   - **current.days** - Days on market currently
   - **total.days** - Total days on market
   - **total.realtors[]** - Days with each realtor
7. **priceChanges[]** - Full price change history:
   - **created** - When the price changed
   - **newPrice** - New price after change
   - **priceChange** - Amount of change (+/-)
8. **realtor** - Comprehensive realtor information:
   - name, address, contact, logo
   - ratings, reviews, statistics
   - sales percentages by area/type

## Current Schema vs Actual API Response

### ✅ Fields We're Capturing:
- addressID, addressType
- roadName, houseNumber, zipCode, cityName
- livingArea, weightedArea, plotArea
- latestValuation, energyLabel
- isOnMarket, isPublic
- coordinates (lat, lon)
- buildings[] array (full details)
- registrations[] array (sale history)
- municipality, province, road, zip, city
- daysOnMarket.realtors[] (but this is EMPTY for active listings!)

### ❌ Fields We're MISSING:
1. **cases[]** - The entire listing/offering data (CRITICAL!)
   - Listing creation date
   - Current days on market (accurate)
   - Price change history
   - Realtor assignment history
   - Case/offering status

2. **boligsidenInfo** (partially captured):
   - We have: latestOfferedPrice, latestSoldPrice, latestSoldArea
   - But this appears in API response for on-market properties

3. **Individual case fields that should be in a new table**:
   - Case status
   - Price history with dates
   - Time on market tracking
   - Realtor rotation history

## 🔧 Required Schema Changes

### New Table: `cases` (or `offerings`)

```python
class Case(Base):
    __tablename__ = 'cases'
    
    id = Column(Integer, primary_key=True)
    property_id = Column(String, ForeignKey('properties_new.id'))
    
    # Case identification
    case_id = Column(String, unique=True)  # The offering UUID
    status = Column(String)  # open, sold, withdrawn
    
    # Pricing
    current_price = Column(Integer)
    original_price = Column(Integer)
    
    # Dates
    created_date = Column(DateTime)  # WHEN LISTED!
    modified_date = Column(DateTime)
    sold_date = Column(DateTime, nullable=True)
    
    # Time on market
    days_on_market_current = Column(Integer)
    days_on_market_total = Column(Integer)
    
    # Realtor
    primary_realtor_id = Column(String)
    primary_realtor_name = Column(String)
    
    # Relationships
    property = relationship('Property', back_populates='cases')
    price_changes = relationship('PriceChange', back_populates='case')
    realtor_history = relationship('CaseRealtorHistory', back_populates='case')
```

### New Table: `price_changes`

```python
class PriceChange(Base):
    __tablename__ = 'price_changes'
    
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('cases.id'))
    
    change_date = Column(DateTime)
    old_price = Column(Integer)
    new_price = Column(Integer)
    price_change_amount = Column(Integer)  # Can be negative
    
    case = relationship('Case', back_populates='price_changes')
```

### New Table: `case_realtor_history`

```python
class CaseRealtorHistory(Base):
    __tablename__ = 'case_realtor_history'
    
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('cases.id'))
    
    realtor_id = Column(String)
    realtor_name = Column(String)
    days_with_realtor = Column(Integer)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    case = relationship('Case', back_populates='realtor_history')
```

## 📊 Why This Matters

1. **Listing Date**: You asked "when it was offered on sale" - this is in `cases[0].created`!
2. **Accurate Days on Market**: The `cases[].timeOnMarket` has the real data
3. **Price History**: Track all price drops/increases with dates
4. **Market Analysis**: Understand property lifecycle and pricing strategies
5. **Realtor Performance**: Track which realtors handled which listings

## 🎯 The Key Discovery

The **`daysOnMarket.realtors[]`** field we currently capture is **EMPTY for active listings**!

The REAL data is in **`cases[].timeOnMarket.total.realtors[]`**

This explains why we haven't been seeing listing dates - we're looking at the wrong field!

## Summary of Action Items

1. ✅ Add `cases` table to schema
2. ✅ Add `price_changes` table to schema  
3. ✅ Add `case_realtor_history` table to schema
4. ✅ Update import script to parse `cases[]` array
5. ✅ Update web interface to show:
   - Listing date (`cases[0].created`)
   - Days on market (`cases[0].timeOnMarket.current.days`)
   - Price history (`cases[0].priceChanges[]`)
6. ⚠️  Note: The `cases[]` array appears for **on-market properties** but not necessarily for sold properties

## Field Mapping

| What You Want | Where It Is | Current Schema |
|---------------|-------------|----------------|
| Listing date | `cases[0].created` | ❌ Not captured |
| Days on market | `cases[0].timeOnMarket.current.days` | ❌ Not captured (empty field) |
| Price changes | `cases[0].priceChanges[]` | ❌ Not captured |
| Current price | `cases[0].price` | ❌ Not captured |
| Case status | `cases[0].status` | ❌ Not captured |
| Offering ID | `cases[0].caseID` | ❌ Not captured |
| Realtor time | `cases[0].timeOnMarket.total.realtors[]` | ❌ Not captured |
