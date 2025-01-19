from flask import Flask, request, jsonify, render_template, redirect, Response
import time
import json
from urllib.parse import quote
import psycopg2

# Inicijalizacija Flask aplikacije
app = Flask(__name__)

# Funkcija za spajanje na bazu podataka
def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="tbp_projekt_probni",
        user="tea",
        password="1234"
    )
    return conn

# Ruta za prikaz stranice za prijavu
@app.route('/login-page', methods=['GET'])
def login_page():
    return render_template('login.html')

# Ruta za autentifikaciju korisnika
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    lozinka = request.form.get('lozinka')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT provjeri_korisnika(%s, %s);", (email, lozinka))
        valid = cursor.fetchone()[0]

        if not valid:
            return jsonify({"error": "Neispravni podaci za prijavu."}), 401

        cursor.execute("SELECT id FROM korisnici WHERE email = %s;", (email,))
        korisnik_id = cursor.fetchone()[0]

        cursor.execute("SELECT zapocni_sesiju(%s);", (korisnik_id,))
        session_token = cursor.fetchone()[0]
        conn.commit()

    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()

    response = redirect(f'/dashboard/{korisnik_id}')
    response.set_cookie('session_token', session_token)
    return response

# Ruta za prikaz stranice za registraciju
@app.route('/register-page', methods=['GET'])
def register_page():
    return render_template('register.html')

# Ruta za registraciju korisnika
@app.route('/register', methods=['POST'])
def register():
    data = request.form  
    korisnicko_ime = data.get('korisnicko_ime')
    email = data.get('email')
    lozinka = data.get('lozinka')
    tip_korisnika = 'Klijent'

    if not korisnicko_ime or not email or not lozinka or not tip_korisnika:
        return jsonify({"error": "Sva polja su obavezna."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT registriraj_korisnika(%s, %s, %s, %s);",
            (korisnicko_ime, email, lozinka, tip_korisnika)
        )
        conn.commit()

        cursor.execute("SELECT id FROM korisnici WHERE email = %s;", (email,))
        korisnik_id = cursor.fetchone()[0]

        cursor.execute("SELECT zapocni_sesiju(%s);", (korisnik_id,))
        session_token = cursor.fetchone()[0]
        conn.commit()

    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500
    finally:
        conn.close()

    response = redirect(f'/dashboard/{korisnik_id}')
    response.set_cookie('session_token', session_token)
    return response

# Ruta za dashboard
@app.route('/dashboard/<int:korisnik_id>', methods=['GET'])
def dashboard(korisnik_id):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return jsonify({"error": "Nema aktivne sesije."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM dohvati_prijavljenog_korisnika(%s);", (session_token,))
        korisnik = cursor.fetchone()

        if not korisnik:
            return jsonify({"error": "Sesija nije aktivna."}), 403

        prijavljeni_korisnik_id, prijavljeni_tip_korisnika = korisnik


        cursor.execute("SELECT korisnicko_ime FROM korisnici WHERE id = %s;", (prijavljeni_korisnik_id,))
        korisnicko_ime = cursor.fetchone()[0]


        if prijavljeni_tip_korisnika == 'Administrator':

            cursor.execute("SELECT * FROM dohvat_podataka_dashboard(%s);", (prijavljeni_korisnik_id,))
            data = cursor.fetchall()

            return render_template(
                'dashboard.html',
                data=data,
                prijavljeni_tip_korisnika=prijavljeni_tip_korisnika,
                korisnicko_ime=korisnicko_ime
            )
        
        elif prijavljeni_tip_korisnika in ['Zaposlenik', 'Klijent']:
            cursor.execute("SELECT * FROM knjige;")
            books = cursor.fetchall()

            return render_template(
                'books.html',
                books=books,
                prijavljeni_tip_korisnika=prijavljeni_tip_korisnika,
                korisnicko_ime=korisnicko_ime
            )

    except psycopg2.Error as e:
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()

    

# Ruta za pregled korisnika
@app.route('/view/<int:user_id>', methods=['GET'])
def view_user(user_id):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return jsonify({"error": "Nema aktivne sesije."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM dohvati_prijavljenog_korisnika(%s);", (session_token,))
        korisnik = cursor.fetchone()

        if not korisnik:
            return jsonify({"error": "Sesija nije aktivna."}), 403

        prijavljeni_korisnik_id, prijavljeni_tip_korisnika = korisnik

        cursor.execute("SELECT dohvati_korisnika_meta(%s);", (user_id,))
        user_result = cursor.fetchone()

        if not user_result:
            return jsonify({"error": "Korisnik ne postoji ili nema dostupnih podataka."}), 404

        user = user_result[0]
        meta = user.get('meta')

    except psycopg2.Error as e:
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()

    return render_template('view_user.html', user=user, meta=meta, prijavljeni_korisnik_id=prijavljeni_korisnik_id)

# Ruta za prikaz stranice za dodavanje korisnika
@app.route('/add-user-page', methods=['GET'])
def add_user_page():
    session_token = request.cookies.get('session_token')
    if not session_token:
        return jsonify({"error": "Nema aktivne sesije."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, tip_korisnika FROM dohvati_prijavljenog_korisnika(%s);", (session_token,))
        korisnik = cursor.fetchone()

        if not korisnik:
            return jsonify({"error": "Sesija nije aktivna."}), 403

        prijavljeni_korisnik_id, prijavljeni_tip_korisnika = korisnik

        if prijavljeni_tip_korisnika != 'Administrator':
            return jsonify({"error": "Nemate ovlasti za dodavanje korisnika."}), 403

        cursor.execute("SELECT unnest(enum_range(NULL::user_type));")
        user_types = [row[0] for row in cursor.fetchall()]

    except psycopg2.Error as e:
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()

    return render_template(
        'add_user.html',
        user_types=user_types,
        prijavljeni_korisnik_id=prijavljeni_korisnik_id
    )

# Ruta za obradu podataka s forme
@app.route('/add-user', methods=['POST'])
def add_user():
    session_token = request.cookies.get('session_token')
    if not session_token:
        return jsonify({"error": "Nema aktivne sesije."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, tip_korisnika FROM dohvati_prijavljenog_korisnika(%s);", (session_token,))
        korisnik = cursor.fetchone()

        if not korisnik:
            return jsonify({"error": "Sesija nije aktivna."}), 403

        korisnik_id, tip_korisnika = korisnik

        if tip_korisnika != 'Administrator':
            return jsonify({"error": "Nemate ovlasti za dodavanje korisnika."}), 403

        data = request.form
        korisnicko_ime = data.get('korisnicko_ime')
        email = data.get('email')
        lozinka = data.get('lozinka')
        tip_korisnika = data.get('tip_korisnika')  

        if not korisnicko_ime or not email or not lozinka or not tip_korisnika:
            return jsonify({"error": "Sva polja su obavezna."}), 400

        cursor.execute(
            "SELECT registriraj_korisnika(%s, %s, %s, %s);",
            (korisnicko_ime, email, lozinka, tip_korisnika)
        )
        conn.commit()

    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()

    return redirect(f'/dashboard/{korisnik_id}')



# Ruta za prikaz stranice za uređivanje
@app.route('/edit/<int:user_id>', methods=['GET'])
def edit_user(user_id):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return jsonify({"error": "Nema aktivne sesije."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM dohvati_prijavljenog_korisnika(%s);", (session_token,))
        korisnik = cursor.fetchone()

        if not korisnik:
            return jsonify({"error": "Sesija nije aktivna."}), 403

        prijavljeni_korisnik_id, prijavljeni_tip_korisnika = korisnik

        cursor.execute("SELECT dohvati_korisnika_meta(%s);", (user_id,))
        user_result = cursor.fetchone()

        if not user_result:
            return jsonify({"error": "Korisnik ne postoji."}), 404

        user = user_result[0]  

        if 'meta' not in user or user['meta'] is None:
            user['meta'] = {
                "ime": "",
                "prezime": "",
                "adresa": "",
                "telefon": "",
                "grad": "",
                "drzava": ""
            }

        cursor.execute("SELECT unnest(enum_range(NULL::user_type));")
        user_types = [row[0] for row in cursor.fetchall()]

    except psycopg2.Error as e:
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()

    return render_template(
        'edit_user.html',
        user=user,
        user_types=user_types,
        prijavljeni_korisnik_id=prijavljeni_korisnik_id,
        prijavljeni_tip_korisnika=prijavljeni_tip_korisnika
    )




# Ruta za ažuriranje korisnika
@app.route('/update-user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return jsonify({"error": "Nema aktivne sesije."}), 403

    data = request.form
    korisnicko_ime = data.get('korisnicko_ime')
    email = data.get('email')
    lozinka = data.get('lozinka')
    tip_korisnika = data.get('tip_korisnika')
    ime = data.get('ime')
    prezime = data.get('prezime')
    adresa = data.get('adresa')
    telefon = data.get('telefon')
    grad = data.get('grad')
    drzava = data.get('drzava')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM dohvati_prijavljenog_korisnika(%s);", (session_token,))
        korisnik = cursor.fetchone()

        if not korisnik:
            return jsonify({"error": "Sesija nije aktivna."}), 403

        prijavljeni_korisnik_id, prijavljeni_tip_korisnika = korisnik

        cursor.execute(
            "SELECT uredi_korisnika(%s, %s, %s, %s, %s, ROW(%s, %s, %s, %s, %s, %s)::meta_podaci);",
            (user_id, korisnicko_ime, email, lozinka, tip_korisnika, ime, prezime, adresa, telefon, grad, drzava)
        )
        success = cursor.fetchone()[0]
        conn.commit()

        if not success:
            return jsonify({"error": "Ažuriranje nije uspjelo."}), 400

    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()

    return redirect(f'/dashboard/{prijavljeni_korisnik_id}')


#Dodavanje rute za brisanje korisnika
@app.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    session_token = request.cookies.get('session_token') 
    if not session_token:
        return jsonify({"error": "Nema aktivne sesije."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT dohvati_prijavljenog_korisnika(%s);", (session_token,))
        korisnik = cursor.fetchone()

        if not korisnik:
            return jsonify({"error": "Sesija nije aktivna."}), 403

        prijavljeni_korisnik_id = korisnik[0]

        cursor.execute("SELECT obrisi_korisnika(%s);", (user_id,))
        success = cursor.fetchone()[0]
        conn.commit()

        if not success:
            return jsonify({"error": "Brisanje nije uspjelo. Korisnik ne postoji."}), 404

    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()

    return jsonify({"success": True, "message": "Korisnik je uspješno obrisan."})


#ruta za stranicu profila
@app.route('/profile', methods=['GET'])
def profile():
    session_token = request.cookies.get('session_token')
    if not session_token:
        return jsonify({"error": "Nema aktivne sesije."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM dohvati_prijavljenog_korisnika(%s);", (session_token,))
        korisnik = cursor.fetchone()

        if not korisnik:
            return jsonify({"error": "Sesija nije aktivna ili token nije valjan."}), 403

        korisnik_id, tip_korisnika = korisnik  

        cursor.execute("SELECT * FROM dohvati_profil_korisnika(%s);", (korisnik_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Podaci o korisniku nisu pronađeni."}), 404

        user_data = {
            "id": korisnik_id,
            "korisnicko_ime": user[0],
            "email": user[1],
            "tip_korisnika": user[2],  
        }
        cursor.execute("SELECT COUNT(*) FROM profilne_slike WHERE korisnik_id = %s;", (korisnik_id,))
        has_profile_picture = cursor.fetchone()[0] > 0  


    except psycopg2.Error as e:
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()

    return render_template(
        'profile.html',
        user=user_data,
        has_profile_picture=has_profile_picture,
        timestamp=int(time.time())  
    )




#Upload profilne slike
@app.route('/upload-profile-picture', methods=['POST'])
def upload_profile_picture():
    if 'file' not in request.files:
        return jsonify({"error": "Datoteka nije poslana."}), 400

    file = request.files['file']
    korisnik_id = request.form.get('korisnik_id')

    if not korisnik_id or not file:
        return jsonify({"error": "Korisnik ID ili datoteka nisu navedeni."}), 400

    file_data = file.read()
    content_type = file.content_type

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT dodaj_profilnu_sliku(%s, %s, %s, %s);
        """, (korisnik_id, f"Profilna slika za korisnika {korisnik_id}", content_type, psycopg2.Binary(file_data)))
        conn.commit()
        print("Slika uspješno spremljena u bazu.")

        return redirect(f'/profile?timestamp={int(time.time())}')

    except psycopg2.Error as e:
        conn.rollback()
        print(f"Greška baze podataka: {e.pgerror}")
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()



#Dohvat profilne slike
@app.route('/profile-picture/<int:user_id>', methods=['GET'])
def get_profile_picture(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT slika, tip
            FROM profilne_slike
            WHERE korisnik_id = %s
            ORDER BY id DESC
            LIMIT 1;
        """, (user_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "Profilna slika nije pronađena."}), 404

        image_data, content_type = result

        return Response(image_data, mimetype=content_type)

    except psycopg2.Error as e:
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()



#Brisanje profilne slike
@app.route('/delete-profile-picture/<int:user_id>', methods=['POST'])
def delete_profile_picture(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id FROM profilne_slike
            WHERE korisnik_id = %s
            ORDER BY id DESC
            LIMIT 1;
        """, (user_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "Profilna slika nije pronađena."}), 404

        cursor.execute("""
            DELETE FROM profilne_slike
            WHERE korisnik_id = %s
            AND id = %s;
        """, (user_id, result[0]))
        conn.commit()

        return redirect(f'/profile?timestamp={int(time.time())}')

    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()




# Prikaz forme za dodavanje knjiga
@app.route('/add-book-page', methods=['GET'])
def add_book_page():
    session_token = request.cookies.get('session_token')
    if not session_token:
        return jsonify({"error": "Nema aktivne sesije."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT tip_korisnika FROM dohvati_prijavljenog_korisnika(%s);", (session_token,))
        prijavljeni_tip_korisnika = cursor.fetchone()[0]

        if prijavljeni_tip_korisnika != 'Zaposlenik':
            return jsonify({"error": "Nemate ovlasti za dodavanje knjiga."}), 403

    except psycopg2.Error as e:
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()

    return render_template('add_book.html')

# Obrada unosa knjiga
@app.route('/add-book', methods=['POST'])
def add_book():
    naslov = request.form.get('naslov')
    autor = request.form.get('autor')
    godina = request.form.get('godina')
    zanr = request.form.get('zanr')
    file = request.files.get('datoteka')  

    if not naslov or not autor or not godina or not zanr or not file:
        return jsonify({"error": "Sva polja, uključujući datoteku, su obavezna."}), 400

    session_token = request.cookies.get('session_token')
    if not session_token:
        return jsonify({"error": "Sesija nije aktivna."}), 403

    try:
        file_data = file.read()
        content_type = file.content_type

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, tip_korisnika FROM dohvati_prijavljenog_korisnika(%s);", (session_token,))
        korisnik = cursor.fetchone()
        if not korisnik or korisnik[1] != 'Zaposlenik':
            return jsonify({"error": "Samo zaposlenici mogu dodavati knjige."}), 403

        zaposlenik_id = korisnik[0]

        cursor.execute("""
            SELECT dodaj_knjigu(%s, %s, %s, %s, %s, %s);
        """, (naslov, autor, godina, zanr, psycopg2.Binary(file_data), zaposlenik_id))

        success = cursor.fetchone()[0]
        if not success:
            raise psycopg2.Error("Dodavanje knjige nije uspjelo.")

        conn.commit()
        return redirect(f'/dashboard/{zaposlenik_id}')

    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()




# Ruta za brisanje knjige
@app.route('/delete-book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    session_token = request.cookies.get('session_token')
    if not session_token:
        return jsonify({"error": "Nema aktivne sesije."}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, tip_korisnika FROM dohvati_prijavljenog_korisnika(%s);", (session_token,))
        korisnik = cursor.fetchone()
        if not korisnik or korisnik[1] != 'Zaposlenik':
            return jsonify({"error": "Nemate ovlasti za brisanje knjiga."}), 403

        cursor.execute("SELECT obrisi_knjigu(%s);", (book_id,))
        success = cursor.fetchone()[0]

        if not success:
            return jsonify({"error": "Knjiga nije pronađena."}), 404
        
        conn.commit()
        return jsonify({"success": True, "message": "Knjiga je uspješno obrisana."})

    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()




# Ruta za preuzimanje datoteke knjige
@app.route('/download-book/<int:book_id>', methods=['GET'])
def download_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT datoteka, naslov FROM knjige WHERE id = %s;", (book_id,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"error": "Datoteka nije pronađena."}), 404

        file_data, naslov = result

        content_type = "text/plain"

        filename = f"{naslov}.txt"
        encoded_filename = quote(filename)

        return Response(
            file_data,
            mimetype=content_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )

    except psycopg2.Error as e:
        return jsonify({"error": f"Greška baze podataka: {e.pgerror}"}), 500

    finally:
        conn.close()




#odjava
@app.route('/logout', methods=['GET'])
def logout():
    response = redirect('/')  
    response.delete_cookie('session_token')  
    return response

@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')


if __name__ == '__main__':
    app.run(debug=True)
