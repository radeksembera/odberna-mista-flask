
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

INSERT INTO users (username, password_hash)
VALUES ('admin', 'scrypt:32768:8:1$hQVEVJSdw8hkbkip$0356ff3e5318f8e8469584e89d5b29615fd51015dc1cd3dd8a0fe0c62da044ef613f04f9febbd15fd0616db656c3a189577eab7f890422b1be0b70d31e00118a');

DROP TABLE IF EXISTS odberna_mista;
CREATE TABLE odberna_mista (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_mista TEXT NOT NULL,
    popis TEXT NOT NULL
);
