
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "tajny_klic"
DATABASE = 'odberna_mista_login.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    if not session.get("user_id"):
        return redirect("/login")
    conn = get_db_connection()
    mista = conn.execute("SELECT * FROM odberna_mista").fetchall()
    conn.close()
    return render_template("index.html", mista=mista)

@app.route("/add", methods=["POST"])
def add():
    if not session.get("user_id"):
        return redirect("/login")
    id_mista = request.form["id_mista"]
    popis = request.form["popis"]
    conn = get_db_connection()
    conn.execute("INSERT INTO odberna_mista (id_mista, popis) VALUES (?, ?)", (id_mista, popis))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("user_id"):
        return redirect("/login")
    conn = get_db_connection()
    conn.execute("DELETE FROM odberna_mista WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
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
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
