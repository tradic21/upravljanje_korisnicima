# upravljanje_korisnicima
1. Postavljanje virtualnog okruženja
   - python3 -m venv venv_flask
   - source venv_flask/bin/activate
2. Instalacija ovisnosti
   - pip install -r requirements.txt
3. Postavljanje PostgreSQL baze podataka
   - Potreban je PostgreSQL: https://www.postgresql.org/download/
   - Kreirati bazu podataka: CREATE DATABASE tbp_projekt_probni;
   - Postaviti korisnika i lozinku baze podataka:
     CREATE USER myuser WITH ENCRYPTED PASSWORD 'mypassword';
     GRANT ALL PRIVILEGES ON DATABASE tbp_projekt_probni TO myuser;
     - Napomena: Zamijeni myuser i mypassword vlastitim korisničkim podacima.)
     - **Zamijeniti user i passwor s odgovarajućim podacima unutar upravljanje_korsnicima.py**
      def get_db_connection():
       conn = psycopg2.connect(
           host="localhost",
           database="tbp_projekt_probni",
           user="tea",
           password="1234"
       )
   - Uvoz dump datoteke u bazu: preuzeti tbp_projekt_probni.dump iz GitHub repozitorija
     pg_restore -U tea -d tbp_projekt_probni -1 tbp_projekt_probni.dump
4. Pokretanje aplikacije
   - python3 upravljanje_korisnicima.py
   - Aplikacija će biti dostupna na: http://127.0.0.1:5000
5. Pristup aplikaciji
   - Početna stranica: http://127.0.0.1:5000
   - Prijava: http://127.0.0.1:5000/login-page
   - Registracija: http://127.0.0.1:5000/register-page
   - Dashboard: http://127.0.0.1:5000/dashboard/{user_id}

