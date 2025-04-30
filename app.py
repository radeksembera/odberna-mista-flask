from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import psycopg2.extras
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "tajny_klic"

# Získáme URL připojení z Renderu
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
    return conn

@app.route("/")
def index():
    if not session.get("user_id"):
        return redirect("/login")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM odberna_mista")
    mista = cur.fetchall()
    conn.close()
    return render_template("index.html", mista=mista)

@app.route("/add", methods=["POST"])
def add():
    if not session.get("user_id"):
        return redirect("/login")
    id_mista = request.form["id_mista"]
    popis = request.form["popis"]
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO odberna_mista (id_mista, popis) VALUES (%s, %s)", (id_mista, popis))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("user_id"):
        return redirect("/login")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM odberna_mista WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")
        else:
            return render_template("login.html", error="Neplatné přihlašovací údaje.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
