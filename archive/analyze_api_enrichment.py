"""
Comprehensive Analysis of API Response Data
Purpose: Identify all fields available for database enrichment
"""

import json

print("="*80)
print("API RESPONSE DATA ENRICHMENT ANALYSIS")
print("="*80)

with open('C:/Users/Mark BJ/Desktop/Code/api_test_response.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("\n" + "="*80)
print("CURRENTLY MISSING FIELDS THAT COULD ENRICH DATABASE")
print("="*80)

# Track what we're capturing vs what's available
print("\n📋 TOP-LEVEL PROPERTY FIELDS:")
print("\nCurrently NOT captured:")

missing_top_level = {
    'casePrice': '4995000 kr - CRITICAL for current listings!',
    'door': 'Apartment door number',
    'floor': 'Floor number for apartments',
}

for field, description in missing_top_level.items():
    value = data.get(field)
    print(f"   ❌ {field}: {value} - {description}")

# Check the cases array for additional fields
print("\n" + "="*80)
print("CASE OBJECT ENRICHMENT OPPORTUNITIES")
print("="*80)

case = data['cases'][0] if data.get('cases') else {}

case_missing_fields = {
    'priceCash': f"{case.get('priceCash')} kr - MAIN LISTING PRICE",
    'priceChangePercentage': f"{case.get('priceChangePercentage')}% - Price change indicator",
    'perAreaPrice': f"{case.get('perAreaPrice')} kr/sqm - Price per square meter",
    'monthlyExpense': f"{case.get('monthlyExpense')} kr - Monthly ownership costs",
    'lotArea': f"{case.get('lotArea')} sqm - Land/lot size",
    'basementArea': f"{case.get('basementArea')} sqm - Basement area",
    'hasBalcony': f"{case.get('hasBalcony')} - Has balcony",
    'hasTerrace': f"{case.get('hasTerrace')} - Has terrace",
    'hasElevator': f"{case.get('hasElevator')} - Has elevator",
    'highlighted': f"{case.get('highlighted')} - Featured listing",
    'descriptionTitle': f"Listing title/headline",
    'descriptionBody': f"Full listing description ({len(str(case.get('descriptionBody', '')))} chars)",
    'caseUrl': f"Direct URL to listing page",
    'providerCaseID': f"External provider case ID",
    'yearBuilt': f"{case.get('yearBuilt')} - Year built (in case object)",
    'realEstate': f"Mortgage/financing info (downPayment, grossMortgage, netMortgage)",
    'realtor': f"Complete realtor information",
    'images': f"{len(case.get('images', []))} images available",
    'defaultImage': f"Default/primary image",
    'utilitiesConnectionFee': f"Utilities fee information",
}

print("\nCurrently NOT captured in Case table:")
for field, description in case_missing_fields.items():
    print(f"   ❌ {field}: {description}")

# IMAGE DATA - VERY IMPORTANT!
print("\n" + "="*80)
print("IMAGE DATA STRUCTURE (CRITICAL FOR WEB APP)")
print("="*80)

images = case.get('images', [])
print(f"\n📸 Total Images Available: {len(images)}")

if images:
    print("\nFirst Image Structure:")
    first_image = images[0]
    print(json.dumps(first_image, indent=2))
    
    print("\nImage Sizes Available:")
    for img_source in first_image.get('imageSources', []):
        size = img_source.get('size', {})
        url = img_source.get('url', '')
        print(f"   - {size.get('width')}x{size.get('height')} : {url[:100]}...")

# Default/Primary Image
default_image = case.get('defaultImage', {})
if default_image:
    print("\n🖼️ Default Image (Primary):")
    print(json.dumps(default_image, indent=2))

# REALTOR DATA
print("\n" + "="*80)
print("REALTOR DATA (RICH INFORMATION)")
print("="*80)

realtor = case.get('realtor', {})
if realtor:
    print("\nRealtor Fields Available:")
    print(f"   - Name: {realtor.get('name')}")
    print(f"   - Phone: {realtor.get('contactInformation', {}).get('phone')}")
    print(f"   - Email: {realtor.get('contactInformation', {}).get('email')}")
    print(f"   - CVR: {realtor.get('contactInformation', {}).get('cvr')}")
    print(f"   - Number of Employees: {realtor.get('numberOfEmployees')}")
    print(f"   - Number of Realtors: {realtor.get('numberOfRealtors')}")
    print(f"   - Preferred: {realtor.get('preferred')}")
    print(f"   - Seller Rating: {realtor.get('rating', {}).get('seller', {}).get('score')}/10 (based on {realtor.get('rating', {}).get('seller', {}).get('basis')} reviews)")
    print(f"   - Buyer Rating: {realtor.get('rating', {}).get('buyer', {}).get('score')}/10 (based on {realtor.get('rating', {}).get('buyer', {}).get('basis')} reviews)")
    print(f"   - Broadcast: {realtor.get('broadcast', {}).get('percentage')}% (target: {realtor.get('broadcast', {}).get('target')}%)")
    print(f"   - Description: {len(realtor.get('descriptionBody', ''))} chars")
    print(f"   - Logo Image: {len(realtor.get('image', {}).get('imageSources', []))} sizes available")

# FINANCING DATA
print("\n" + "="*80)
print("FINANCING DATA (MORTGAGE INFORMATION)")
print("="*80)

real_estate = case.get('realEstate', {})
if real_estate:
    print("\nFinancing Information:")
    print(f"   - Down Payment: {real_estate.get('downPayment'):,} kr")
    print(f"   - Gross Mortgage: {real_estate.get('grossMortgage'):,} kr/month")
    print(f"   - Net Mortgage: {real_estate.get('netMortgage'):,} kr/month")
    print(f"\n   💡 Total Monthly Cost: {case.get('monthlyExpense'):,} kr (mortgage + utilities/taxes)")

# Check for coordinates in case
print("\n" + "="*80)
print("COORDINATES (Check if different from property-level)")
print("="*80)

case_coords = case.get('coordinates', {})
prop_coords = data.get('coordinates', {})
print(f"\nProperty-level coords: {prop_coords}")
print(f"Case-level coords: {case_coords}")
print(f"Are they the same? {case_coords == prop_coords}")

# ADDRESS IN CASE
print("\n" + "="*80)
print("ADDRESS DATA IN CASE OBJECT")
print("="*80)

case_address = case.get('address', {})
print(f"\n⚠️ Case object contains FULL address data (nested)")
print(f"   This is a duplicate of the top-level address")
print(f"   No need to store separately - already have property-level data")

print("\n" + "="*80)
print("RECOMMENDATION: NEW DATABASE FIELDS TO ADD")
print("="*80)

print("""
🎯 HIGH PRIORITY (Critical for functionality):

1. Case Table Additions:
   ✅ priceCash (FLOAT) - Primary listing price [CRITICAL!]
   ✅ priceChangePercentage (FLOAT) - Price change %
   ✅ perAreaPrice (FLOAT) - Price per sqm for this listing
   ✅ monthlyExpense (INTEGER) - Total monthly cost
   ✅ lotArea (FLOAT) - Land/lot size
   ✅ basementArea (FLOAT) - Basement area
   ✅ descriptionTitle (TEXT) - Listing headline
   ✅ descriptionBody (TEXT) - Full listing description
   ✅ caseUrl (TEXT) - Direct listing URL
   ✅ providerCaseID (TEXT) - External case ID
   ✅ hasBalcony (BOOLEAN)
   ✅ hasTerrace (BOOLEAN)
   ✅ hasElevator (BOOLEAN)
   ✅ highlighted (BOOLEAN) - Featured listing

2. NEW Images Table (one-to-many with Case):
   - case_id (FK)
   - image_url (TEXT)
   - width (INTEGER)
   - height (INTEGER)
   - is_default (BOOLEAN)
   - sort_order (INTEGER)

3. NEW Realtor Table (one-to-one with Case):
   - case_id (FK)
   - realtor_id (TEXT)
   - name (TEXT)
   - phone (TEXT)
   - email (TEXT)
   - cvr (TEXT)
   - number_of_employees (INTEGER)
   - number_of_realtors (INTEGER)
   - preferred (BOOLEAN)
   - seller_rating_score (FLOAT)
   - seller_rating_basis (INTEGER)
   - buyer_rating_score (FLOAT)
   - buyer_rating_basis (INTEGER)
   - broadcast_percentage (FLOAT)
   - description_body (TEXT)
   - logo_url (TEXT)

4. NEW Financing Table (one-to-one with Case):
   - case_id (FK)
   - down_payment (INTEGER)
   - gross_mortgage (INTEGER)
   - net_mortgage (INTEGER)

5. Property Table Additions:
   ✅ door (TEXT) - Apartment door
   ✅ floor (TEXT) - Floor number

📊 MEDIUM PRIORITY (Enhancements):

1. Utilities Connection Fee
2. Broadcast target percentages
3. Detailed realtor ratings breakdown

❌ SKIP (Duplicates/Unnecessary):
- address data in case object (already have at property level)
- coordinates in case object (same as property level)
""")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
