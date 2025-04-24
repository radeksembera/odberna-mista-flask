import sqlite3
from werkzeug.security import generate_password_hash

# Připojení k databázi (vytvoří nový soubor)
conn = sqlite3.connect("odberna_mista_login.db")
cursor = conn.cursor()

# Vytvoření tabulky uživatelů
cursor.execute("DROP TABLE IF EXISTS users;")
cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        password_hash TEXT NOT NULL
    );
""")
# Vložení výchozího uživatele admin/admin
hashed_password = generate_password_hash("admin")
cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ("admin", hashed_password))

# Vytvoření tabulky odběrných míst
cursor.execute("DROP TABLE IF EXISTS odberna_mista;")
cursor.execute("""
    CREATE TABLE odberna_mista (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_mista TEXT NOT NULL,
        popis TEXT NOT NULL
    );
""")

conn.commit()
conn.close()

print("✅ Databáze s uživatelem 'admin' byla vytvořena.")
