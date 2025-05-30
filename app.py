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

    # Získáme objekt a ověříme vlastnictví
    cur.execute("SELECT * FROM objekty_fakturace WHERE id = %s AND user_id = %s", (objekt_id, session["user_id"]))
    objekt = cur.fetchone()
    if not objekt:
        conn.close()
        return "Nepovolený přístup", 403

    if request.method == "POST":
        # Funkce pro převod prázdného na None
        def get_value(name): return request.form.get(name) or None

        # Zpracování zálohy
        cur.execute("DELETE FROM zalohy_info WHERE objekt_id = %s", (objekt_id,))
        cur.execute("""
            INSERT INTO zalohy_info (objekt_id, cislo_zalohy, konst_symbol, vs, obdobi, splatnost, forma_uhrady, vystaveni, castka_zalohy)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            objekt_id,
            get_value("cislo_zalohy"),
            get_value("konst_symbol_zal"),
            get_value("vs_zal"),
            get_value("obdobi"),
            get_value("splatnost"),
            get_value("forma_uhrady"),
            get_value("vystaveni"),
            get_value("castka_zalohy")
        ))

        # Zpracování faktury
        cur.execute("DELETE FROM faktura_info WHERE objekt_id = %s", (objekt_id,))
        cur.execute("""
            INSERT INTO faktura_info (objekt_id, cislo_faktury, konst_symbol, vs, splatnost, vystaveni, zdanitelne_plneni, forma_uhrady, popis, dph, od_date, do_date, header1, header2)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            objekt_id,
            get_value("cislo_faktury"),
            get_value("konst_symbol"),
            get_value("vs"),
            get_value("splatnost_f"),
            get_value("vystaveni"),
            get_value("zdanitelne_plneni"),
            get_value("forma_uhrady_f"),
            get_value("popis"),
            get_value("dph"),
            get_value("od_date"),
            get_value("do_date"),
            get_value("header1"),
            get_value("header2")
        ))

        conn.commit()

    # Načti data pro zobrazení
    cur.execute("SELECT * FROM zalohy_info WHERE objekt_id = %s", (objekt_id,))
    zal = cur.fetchone()

    cur.execute("SELECT * FROM faktura_info WHERE objekt_id = %s", (objekt_id,))
    fak = cur.fetchone()

    conn.close()

    return render_template("fakturace.html", objekt=objekt, zal=zal, fak=fak)


from werkzeug.utils import secure_filename
import pandas as pd

@app.route("/objekty/<int:objekt_id>/ceny-distribuce", methods=["GET", "POST"])
def ceny_distribuce(objekt_id):
    if not session.get("user_id"):
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    # Kontrola vlastnictví objektu
    cur.execute("SELECT * FROM objekty_fakturace WHERE id = %s AND user_id = %s", (objekt_id, session["user_id"]))
    objekt = cur.fetchone()
    if not objekt:
        conn.close()
        return "Nepovolený přístup", 403

    if request.method == "POST":
        file = request.files["excel_file"]
        if file and file.filename.endswith((".xls", ".xlsx")):
            filename = secure_filename(file.filename)
            df = pd.read_excel(file)
            df = df.fillna(0)

            # Odstranit předchozí záznamy
            cur.execute("DELETE FROM ceny_distribuce WHERE objekt_id = %s", (objekt_id,))

            for _, row in df.iterrows():
                cur.execute("""
                    INSERT INTO ceny_distribuce (
                        objekt_id, distribuce, sazba, jistic, platba_jistic,
                        distribuce_vt, distribuce_nt, systemove_sluzby,
                        poze_jistic, poze_spotreba, nesitova_infrastruktura, dan_elektrina
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    objekt_id,
                    row["Distribuce"], row["Sazba"], row["Jistič"], row["Platba jistič [Kč/měsíc]"],
                    row["Distribuce VT [Kč/MWh]"], row["Distribuce NT [Kč/MWh]"],
                    row["Systémové služby [Kč/MWh]"], row["POZE jistič [Kč/měsíc]"],
                    row["POZE spotřeba [Kč/MWh]"], row["NeSÍTOVÁ inf. [Kč/MWh]"], row["Daň elektřina [Kč/MWh]"]
                ))
            conn.commit()

    # Načtení tabulky pro objekt
    cur.execute("SELECT * FROM ceny_distribuce WHERE objekt_id = %s", (objekt_id,))
    ceny = cur.fetchall()
    conn.close()

    return render_template("ceny_distribuce.html", objekt=objekt, ceny=ceny)




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
