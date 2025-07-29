from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import add_user, get_user_by_email, save_kyc
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
from database import get_user_transactions, get_user_by_email
from database import add_transaction, update_wallet_balance
app = Flask(__name__)
app.secret_key = 'supersecretkey'
fake_withdrawals = [
    {"user": "j***@gmail.com", "amount": "50 USDT", "time": "just now"},
    {"user": "a***@yahoo.com", "amount": "120 USDT", "time": "2 mins ago"},
    {"user": "m***@proton.me", "amount": "200 USDT", "time": "5 mins ago"},
    {"user": "s***@hotmail.com", "amount": "75 USDT", "time": "8 mins ago"},
    {"user": "r***@gmail.com", "amount": "340 USDT", "time": "10 mins ago"},
]


UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email =( request.form['email'])
       
        password = (request.form['password'])
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

        print("LOGIN DEBUG: email =", email)
        print("User from DB:", user)

        if user:
            print("Stored hashed password:", user[2])
            print("Password entered:", password)
            print("Password match:", check_password_hash(user[2], password))

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
    
    user = get_user_by_email(session['email'])  # (id, email, password, wallet)

    if user:
        email = user[1]
        wallet = user[3] if user[3] else "0 USDT"
    else:
        email = session['email']
        wallet = "0 USDT"

    random.shuffle(fake_withdrawals)
    
    return render_template('dashboard.html', email=email, wallet=wallet, withdrawals=fake_withdrawals)
@app.route('/wallet', methods=['GET'])
def wallet_page():
    if 'email' not in session:
        return redirect(url_for('login'))

    user = get_user_by_email(session['email'])
    wallet_balance = user[3] if user and user[3] else "0 USDT"

    transactions = get_user_transactions(session['email'])

    return render_template('wallet.html', email=session['email'], wallet=wallet_balance, transactions=transactions)

@app.route('/deposit', methods=['GET'])
def deposit_page():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('deposit.html', email=session['email'])
@app.route('/submit-deposit', methods=['POST'])
def submit_deposit():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']
    amount = float(request.form['amount'])
    method = request.form['method']

    from database import add_deposit_request
    add_deposit_request(email, amount, method)

    flash("Deposit request submitted for admin review", "success")
    return redirect(url_for('wallet_page'))


@app.route('/withdraw-request', methods=['GET'])
def withdraw_request():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('withdraw_request.html', email=session['email'])
@app.route('/submit-withdraw-request', methods=['POST'])
def submit_withdraw_request():
    if 'email' not in session:
        return redirect(url_for('login'))

    from database import get_user_wallet
    email = session['email']
    amount = float(request.form['amount'])
    address = request.form['address']
    password = request.form['password']

    user = get_user_by_email(email)
    if not user or not check_password_hash(user[2], password):
        flash("Invalid password", "danger")
        return redirect(url_for('withdraw_request'))

    current_balance = float(get_user_wallet(email))
    if amount > current_balance:
        flash("Insufficient balance", "danger")
        return redirect(url_for('withdraw_request'))

    # Save pending request
    from database import add_withdraw_request
    add_withdraw_request(email, amount,address)

    flash("Withdrawal request sent for admin approval", "success")
    return redirect(url_for('wallet_page'))

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
