from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import psycopg2.extras
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "tajny_klic"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
    return conn

@app.route("/")
def index():
    if not session.get("user_id"):
        return redirect("/login")
    return redirect("/objekty")

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
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect("/admin/users")
            else:
                return redirect("/objekty")

        return render_template("login.html", error="Neplatné přihlašovací údaje.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/profil", methods=["GET", "POST"])
def profil():
    if not session.get("user_id"):
        return redirect("/login")
    
    conn = get_db_connection()
    cur = conn.cursor()
    user_id = session["user_id"]

    if request.method == "POST":
        sro = request.form["sro"]
        adr1 = request.form["adr1"]
        adr2 = request.form["adr2"]
        ico = request.form["ico"]
        dic = request.form["dic"]
        zapis = request.form["zapis"]
        banka = request.form["banka"]
        ucet = request.form["ucet"]
        swift = request.form["swift"]
        iban = request.form["iban"]

        cur.execute("""
            UPDATE users SET 
                sro=%s, adr1=%s, adr2=%s, ico=%s, dic=%s, zapis=%s, 
                banka=%s, ucet=%s, swift=%s, iban=%s
            WHERE id=%s
        """, (sro, adr1, adr2, ico, dic, zapis, banka, ucet, swift, iban, user_id))
        conn.commit()

    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    conn.close()
    return render_template("profil.html", user=user)

@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    if not session.get("user_id"):
        return redirect("/login")
    
    if session.get("role") != "admin":
        return "Nepovolený přístup", 403

    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        new_username = request.form["username"]
        new_password = request.form["password"]
        new_role = request.form["role"]

        password_hash = generate_password_hash(new_password)

        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (new_username, password_hash, new_role)
        )
        conn.commit()

    cur.execute("SELECT id, username, role FROM users ORDER BY id")
    users = cur.fetchall()
    conn.close()

    return render_template("admin_users.html", users=users)

@app.route("/objekty")
def objekty():
    if not session.get("user_id"):
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM objekty_fakturace WHERE user_id = %s", (session["user_id"],))
    objekty = cur.fetchall()
    conn.close()
    return render_template("objekty.html", objekty=objekty)

@app.route("/objekty/novy", methods=["GET", "POST"])
def pridat_objekt():
    if not session.get("user_id"):
        return redirect("/login")

    if request.method == "POST":
        user_id = session["user_id"]
        nazev = request.form["nazev"]
        adresa = request.form["adresa"]
        misto = request.form["misto"]
        stredisko = request.form["stredisko"]
        stredisko_mail = request.form["stredisko_mail"]
        distribuce = request.form["distribuce"]
        poznamka = request.form["poznamka"]

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO objekty_fakturace (user_id, nazev, adresa, misto, stredisko, stredisko_mail, distribuce, poznamka)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, nazev, adresa, misto, stredisko, stredisko_mail, distribuce, poznamka))
        conn.commit()
        conn.close()
        return redirect("/objekty")

    return render_template("objekty_novy.html")

@app.route("/objekty/<int:objekt_id>/mista", methods=["GET", "POST"])
def odberna_mista_objekt(objekt_id):
    if not session.get("user_id"):
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM objekty_fakturace WHERE id = %s AND user_id = %s", (objekt_id, session["user_id"]))
    objekt = cur.fetchone()

    if not objekt:
        conn.close()
        return "Nepovolený přístup", 403

    if request.method == "POST":
        id_mista = request.form["id_mista"]
        popis = request.form["popis"]
        cur.execute(
            "INSERT INTO odberna_mista (id_mista, popis, objekt_id) VALUES (%s, %s, %s)",
            (id_mista, popis, objekt_id)
        )
        conn.commit()

    cur.execute("SELECT * FROM odberna_mista WHERE objekt_id = %s ORDER BY id", (objekt_id,))
    mista = cur.fetchall()
    conn.close()

    return render_template("odberna_mista.html", objekt=objekt, mista=mista)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)

from flask import make_response
from weasyprint import HTML

@app.route("/objekty/<int:objekt_id>/mista/pdf")
def tisk_odbernych_mist(objekt_id):
    if not session.get("user_id"):
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM objekty_fakturace WHERE id = %s AND user_id = %s", (objekt_id, session["user_id"]))
    objekt = cur.fetchone()

    if not objekt:
        conn.close()
        return "Nepovolený přístup", 403

    cur.execute("SELECT * FROM odberna_mista WHERE objekt_id = %s ORDER BY id", (objekt_id,))
    mista = cur.fetchall()
    conn.close()

    html = render_template("odberna_mista_pdf.html", objekt=objekt, mista=mista)
    pdf = HTML(string=html).write_pdf()

    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename=odberna_mista.pdf"
    return response
