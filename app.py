from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import init_db, add_user, get_user_by_email, save_kyc
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Init DB
init_db()

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
       
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        try:
            add_user(email, hashed_password)
            flash("Registered successfully. Please login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            print("Registration error:", e)
            flash("User already exists or database error.", "error")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)
        if user and check_password_hash(user[2], password):
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", "error")
            return redirect(url_for('login'))
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
            flash("KYC submitted successfully!", "success")
            return redirect(url_for('dashboard'))
    return render_template('kyc.html')

@app.route('/referral')
def referral():
    return render_template('referral.html')

@app.route('/markets')
def markets():
    return render_template('markets.html')

@app.route('/quantify')
def quantify():
    return render_template('quantify.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
