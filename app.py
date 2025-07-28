from flask import Flask, render_template, request, redirect, url_for, session
from database import init_db, add_user, get_user_by_email, save_kyc
import os
from flask_sqlalchemy import SQLAlchemy
from models import db, User

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        wallet = request.form['wallet']
        password = request.form['password']
        add_user(email, password, wallet)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)
        if user and user[2] == password:
            session['email'] = email
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', email=session['email'])

@app.route('/kyc', methods=['GET', 'POST'])
def kyc():
    if 'email' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files['kycfile']
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            save_kyc(session['email'], filepath)
            return "KYC Uploaded!"
    return render_template('kyc.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # You can change the filename
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
