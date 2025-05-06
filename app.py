from flask import Flask, render_template, request, redirect, url_for, session, make_response
import psycopg2
import psycopg2.extras
import os
from werkzeug.security import generate_password_hash, check_password_hash
from weasyprint import HTML

app = Flask(__name__)
app.secret_key = "tajny_klic"

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)

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
            return redirect("/admin/users" if user["role"] == "admin" else "/objekty")
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
        fields = ["sro", "adr1", "adr2", "ico", "dic", "zapis", "banka", "ucet", "swift", "iban"]
        values = [request.form[field] for field in fields]
        cur.execute(f"""
            UPDATE users SET {', '.join(f"{field}=%s" for field in fields)}
            WHERE id=%s
        """, (*values, user_id))
        conn.commit()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    conn.close()
    return render_template("profil.html", user=user)

@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    if not session.get("user_id") or session.get("role") != "admin":
        return redirect("/login")
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == "POST":
        username = request.form["username"]
        password_hash = generate_password_hash(request.form["password"])
        role = request.form["role"]
        cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)", (username, password_hash, role))
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
        fields = ["nazev", "adresa", "misto", "stredisko", "stredisko_mail", "distribuce", "poznamka"]
        values = [request.form[field] for field in fields]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO objekty_fakturace (user_id, {', '.join(fields)})
            VALUES (%s, {', '.join(['%s'] * len(fields))})
        """, (session["user_id"], *values))
        conn.commit()
        conn.close()
        return redirect("/objekty")
    return render_template("objekty_novy.html")

@app.route("/objekty/<int:objekt_id>/mista", methods=["GET", "POST"], endpoint="pridat_misto")
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
        cur.execute(
            "INSERT INTO odberna_mista (id_mista, popis, objekt_id) VALUES (%s, %s, %s)",
            (request.form["id_mista"], request.form["popis"], objekt_id)
        )
        conn.commit()
    cur.execute("SELECT * FROM odberna_mista WHERE objekt_id = %s ORDER BY id", (objekt_id,))
    mista = cur.fetchall()
    conn.close()
    return render_template("odberna_mista.html", objekt=objekt, mista=mista)

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

@app.route("/objekty/<int:objekt_id>/fakturace", methods=["GET", "POST"])
def fakturace_objekt(objekt_id):
    if not session.get("user_id"):
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    # Získání objektu
    cur.execute("SELECT * FROM objekty_fakturace WHERE id = %s AND user_id = %s", (objekt_id, session["user_id"]))
    objekt = cur.fetchone()
    if not objekt:
        conn.close()
        return "Nepovolený přístup", 403

    if request.method == "POST":
        # Uložení zálohové faktury
        cur.execute("""
            INSERT INTO zalohy_info (objekt_id, cislo_zalohy, konst_symbol, vs, obdobi, splatnost, vystaveni, forma_uhrady, castka_zalohy)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (objekt_id) DO UPDATE
            SET cislo_zalohy = EXCLUDED.cislo_zalohy,
                konst_symbol = EXCLUDED.konst_symbol,
                vs = EXCLUDED.vs,
                obdobi = EXCLUDED.obdobi,
                splatnost = EXCLUDED.splatnost,
                vystaveni = EXCLUDED.vystaveni,
                forma_uhrady = EXCLUDED.forma_uhrady,
                castka_zalohy = EXCLUDED.castka_zalohy
        """, (
            objekt_id,
            request.form.get("cislo_zalohy"),
            request.form.get("konst_symbol"),
            request.form.get("vs"),
            request.form.get("obdobi"),
            request.form.get("splatnost"),
            request.form.get("vystaveni"),
            request.form.get("forma_uhrady"),
            request.form.get("castka_zalohy")
        ))

        # Uložení faktury
        cur.execute("""
            INSERT INTO faktura_info (objekt_id, cislo_faktury, konst_symbol, vs, splatnost, vystaveni, zdanitelne_plneni, forma_uhrady, popis, dph, od_data, do_data, header1, header2)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (objekt_id) DO UPDATE
            SET cislo_faktury = EXCLUDED.cislo_faktury,
                konst_symbol = EXCLUDED.konst_symbol,
                vs = EXCLUDED.vs,
                splatnost = EXCLUDED.splatnost,
                vystaveni = EXCLUDED.vystaveni,
                zdanitelne_plneni = EXCLUDED.zdanitelne_plneni,
                forma_uhrady = EXCLUDED.forma_uhrady,
                popis = EXCLUDED.popis,
                dph = EXCLUDED.dph,
                od_data = EXCLUDED.od_data,
                do_data = EXCLUDED.do_data,
                header1 = EXCLUDED.header1,
                header2 = EXCLUDED.header2
        """, (
            objekt_id,
            request.form.get("cislo_faktury"),
            request.form.get("konst_symbol_f"),
            request.form.get("vs_f"),
            request.form.get("splatnost_f"),
            request.form.get("vystaveni_f"),
            request.form.get("zdanitelne_plneni"),
            request.form.get("forma_uhrady_f"),
            request.form.get("popis"),
            request.form.get("dph"),
            request.form.get("od_data"),
            request.form.get("do_data"),
            request.form.get("header1"),
            request.form.get("header2")
        ))

        conn.commit()

    # Získání dat pro zobrazení
    cur.execute("SELECT * FROM zalohy_info WHERE objekt_id = %s", (objekt_id,))
    zal = cur.fetchone()

    cur.execute("SELECT * FROM faktura_info WHERE objekt_id = %s", (objekt_id,))
    fak = cur.fetchone()

    conn.close()

    return render_template("fakturace.html", objekt=objekt, zal=zal, fak=fak)




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
