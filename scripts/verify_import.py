"""Quick verification of re-import completion"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

print("=" * 60)
print("RE-IMPORT VERIFICATION")
print("=" * 60)

with engine.connect() as conn:
    # Total cases
    total = conn.execute(text('SELECT COUNT(*) FROM cases')).scalar()
    print(f"\n📊 Total Cases: {total:,}")
    
    # Cases with prices
    with_price = conn.execute(text(
        'SELECT COUNT(*) FROM cases WHERE current_price IS NOT NULL'
    )).scalar()
    print(f"💰 With Prices: {with_price:,} ({with_price/total*100:.1f}%)")
    
    # Cases with descriptions
    with_desc = conn.execute(text(
        'SELECT COUNT(*) FROM cases WHERE description_title IS NOT NULL'
    )).scalar()
    print(f"📝 With Descriptions: {with_desc:,} ({with_desc/total*100:.1f}%)")
    
    # Cases with new fields
    with_expense = conn.execute(text(
        'SELECT COUNT(*) FROM cases WHERE monthly_expense IS NOT NULL'
    )).scalar()
    print(f"🏠 With Monthly Expense: {with_expense:,} ({with_expense/total*100:.1f}%)")
    
    # Total images
    images = conn.execute(text('SELECT COUNT(*) FROM case_images')).scalar()
    print(f"📸 Total Images: {images:,} ({images/total:.1f} per case)")
    
    # Active cases
    active = conn.execute(text(
        "SELECT COUNT(*) FROM cases WHERE status = 'open'"
    )).scalar()
    print(f"✅ Active Cases: {active:,}")
    
    print("\n" + "=" * 60)
    if with_price > 0 and images > 0:
        print("✅ RE-IMPORT SUCCESSFUL!")
    else:
        print("⚠️ RE-IMPORT MAY HAVE ISSUES")
    print("=" * 60)
