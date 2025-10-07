# Copenhagen Greater Metropolitan Area Municipalities
# Based on known municipalities within ~60km radius of Copenhagen City Hall

# These municipalities are definitively within the Copenhagen metropolitan area
COPENHAGEN_AREA_MUNICIPALITIES = [
    # Capital Region of Denmark (Region Hovedstaden) - Core Copenhagen
    'København',           # Copenhagen (0 km - center)
    'Frederiksberg',       # Inside Copenhagen (~2 km)
    'Tårnby',             # Amager, Copenhagen Airport (~8 km)
    'Dragør',             # Southeast Amager (~12 km)
    'Hvidovre',           # Southwest Copenhagen (~7 km)
    'Brøndby',            # Southwest (~8 km)
    'Vallensbæk',         # Southwest (~12 km)
    'Ishøj',              # Southwest (~15 km)
    'Albertslund',        # West (~12 km)
    'Glostrup',           # West (~10 km)
    'Rødovre',            # West (~8 km)
    'Herlev',             # Northwest (~10 km)
    'Gladsaxe',           # North (~8 km)
    'Gentofte',           # North (~8 km)
    'Lyngby-Taarbæk',     # North (~12 km)
    'Ballerup',           # Northwest (~15 km)
    'Furesø',             # Northwest (~20 km)
    'Egedal',             # Northwest (~25 km)
    'Rudersdal',          # North (~15 km)
    'Hørsholm',           # North (~20 km)
    'Fredensborg',        # North (~30 km)
    'Allerød',            # Northwest (~25 km)
    'Hillerød',           # Northwest (~30 km)
    'Høje-Taastrup',      # West (~15 km)
    'Greve',              # Southwest (~20 km)
    'Solrød',             # Southwest (~25 km)
    'Køge',               # South (~35 km)
    'Roskilde',           # West (~30 km)
    'Lejre',              # West (~40 km)
    
    # Region Zealand (Region Sjælland) - Within 60km
    'Stevns',             # South (~50 km)
    'Ringsted',           # Southwest (~55 km)
    'Faxe',               # South (~55 km)
    
    # These might be slightly over 60km but included for completeness
    'Gribskov',           # North (~45-60 km depending on area)
    'Halsnæs',            # Northwest (~50 km)
    'Frederikssund',      # Northwest (~30 km)
]

# For API queries - join with commas
MUNICIPALITIES_PARAM = ','.join(COPENHAGEN_AREA_MUNICIPALITIES)

if __name__ == '__main__':
    print("Copenhagen Greater Metropolitan Area Municipalities")
    print("=" * 80)
    print()
    print(f"Total municipalities: {len(COPENHAGEN_AREA_MUNICIPALITIES)}")
    print()
    print("Municipalities list:")
    for i, muni in enumerate(COPENHAGEN_AREA_MUNICIPALITIES, 1):
        print(f"  {i:2}. {muni}")
    print()
    print("=" * 80)
    print("For API Query:")
    print("=" * 80)
    print()
    print(f"municipalities_param = '{MUNICIPALITIES_PARAM}'")
    print()
    print("Or in Python:")
    print(f"MUNICIPALITIES = {COPENHAGEN_AREA_MUNICIPALITIES}")
