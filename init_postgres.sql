-- Tabulka pro uživatele
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

-- Tabulka pro odběrná místa
CREATE TABLE IF NOT EXISTS odberna_mista (
    id SERIAL PRIMARY KEY,
    id_mista TEXT NOT NULL,
    popis TEXT
);
