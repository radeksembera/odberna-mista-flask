import os
import psycopg2

# Načti SQL ze souboru
with open("init_postgres.sql", "r", encoding="utf-8") as f:
    sql = f.read()

# Připojení k databázi z proměnné prostředí
DATABASE_URL = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Spusť SQL skript
cur.execute(sql)
conn.commit()

cur.close()
conn.close()

print("✅ Tabulky byly vytvořeny v PostgreSQL.")
