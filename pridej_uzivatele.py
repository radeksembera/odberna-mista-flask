import sqlite3
from werkzeug.security import generate_password_hash

# Připojení k databázi
conn = sqlite3.connect("odberna_mista_login.db")
cursor = conn.cursor()

# Zadání uživatelů
uzivatele = [
    ("radek", generate_password_hash("Evi872flx")),
    ("josef", generate_password_hash("partizan1")),
]

# Vložení do tabulky
for jmeno, hash in uzivatele:
    cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (jmeno, hash))

conn.commit()
conn.close()

print("✅ Uživatelská jména byla přidána.")

import sqlite3
from werkzeug.security import generate_password_hash

# Připojení k databázi
conn = sqlite3.connect("odberna_mista_login.db")
cursor = conn.cursor()

# Zadání uživatelů
uzivatele = [
    ("radek", generate_password_hash("Evi872flx")),
    ("josef", generate_password_hash("partizan1")),
]

# Vložení do tabulky
for jmeno, hash in uzivatele:
    cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (jmeno, hash))

conn.commit()
conn.close()

print("✅ Uživatelská jména byla přidána.")
