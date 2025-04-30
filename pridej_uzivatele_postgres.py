import os
import psycopg2
from werkzeug.security import generate_password_hash

# Zadej údaje nového uživatele
username = "admin"
password = "tajneheslo123"  # libovolné heslo

# Vytvoření hash hesla
hashed_password = generate_password_hash(password)

# Připojení k databázi PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Vložení do tabulky users
cur.execute(
    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
    (username, hashed_password)
)

conn.commit()
cur.close()
conn.close()

print(f"✅ Uživatel '{username}' byl úspěšně přidán.")
