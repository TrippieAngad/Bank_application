from flask import Flask, request, render_template, session, redirect, url_for, jsonify
import psycopg2
import os
from dotenv import load_env

app = Flask(__name__)
app.secret_key = os.urandom(24)


class Bankdb: # create a data base class to handle database sessions, sql queries
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("DB_HOST"), #using environment variables to mask database info
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                port=os.getenv("DB_PORT", 5432)  
            )
            self.cur = self.conn.cursor()
        except psycopg2.Error as e:
            print("Error connecting to database:", e)
            self.conn = None
            self.cur = None

    def fetch_user(self, username):
        self.cur.execute(
            'SELECT customer_id, first_name, last_name, job_description, username, password '
            'FROM public."customers" WHERE username=%s',
            (username,)
        )
        return self.cur.fetchone()

    def update_user(self, username, first_name, last_name, job_description):
        self.cur.execute(
            'UPDATE public."customers" SET first_name=%s, last_name=%s, job_description=%s '
            'WHERE username=%s',
            (first_name, last_name, job_description, username)
        )
        self.conn.commit()

    def register_account_creds(self, username, password, first_name, last_name, job_description):
        self.cur.execute(
            'INSERT INTO public."customers" (username, password, first_name, last_name, job_description) '
            'VALUES (%s, %s, %s, %s, %s)',
            (username, password, first_name, last_name, job_description)
        )
        self.conn.commit()

    def close(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

# ---------- endpoints ----------
@app.route('/', methods=['GET']) # home page
def home():
    return render_template('login.html')


@app.route('/login', methods=['POST']) #login endpoint and 
def login():
    data = request.get_json()
    if not data:
        return jsonify(error="Invalid JSON"), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify(error="Missing credentials"), 400

    db = Bankdb()
    if db.conn is None:
        return jsonify(error="Database connection failed"), 500

    user = db.fetch_user(username)
    if user is None:
        db.close()
        return jsonify(error="User not found"), 401

    username_db = user[4]
    password_db = user[5]

    if username == username_db and password == password_db:
        session['current_user'] = username
        db.close()
        return jsonify(success=True, redirect_url=url_for('profile'))

    db.close()
    return jsonify(error="Invalid username or password"), 401

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'current_user' not in session:
        return redirect(url_for('home'))

    username = session['current_user']
    db = Bankdb()

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        job_description = request.form.get('job_description')
        db.update_user(username, first_name, last_name, job_description)

    user_data = db.fetch_user(username)
    db.close()
    return render_template('profile.html', user=user_data)

@app.route('/logout')
def logout():
    session.pop('current_user', None)
    return redirect(url_for('home'))