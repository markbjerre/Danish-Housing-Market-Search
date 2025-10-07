from urllib.parse import quote_plus

password = input("Enter your PostgreSQL password: ")
encoded_password = quote_plus(password)
print(f"\nYour encoded password is: {encoded_password}")
print(f"\nUse this in your DATABASE_URL:")
print(f"DATABASE_URL=postgresql://postgres:{encoded_password}@localhost:5432/housing_db")
