from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import add_user, get_user_by_email, save_kyc
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
from database import get_user_transactions, add_transaction, update_wallet_balance
from database import (
    get_all_users, get_all_deposits, get_all_withdrawals,
    approve_withdrawal_request, reject_withdrawal_request
)
from database import get_withdraw_by_id, get_user_by_email, update_withdraw_status, update_wallet_balance, add_transaction

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
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Please provide both email and password.", "error")
            return redirect(url_for('register'))

        if get_user_by_email(email):
            flash("An account with that email already exists.", "error")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        try:
            add_user(email, hashed_password)
            flash("Registered successfully. Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            app.logger.error(f"Registration error for {email}: {e}")
            flash("Unexpected error. Please try again later.", "error")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)

        if user and check_password_hash(user['password'], password):
            session['email'] = email
            if email == 'vumiiliakonga2@gmail.com':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", "error")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    user = get_user_by_email(session['email'])

    if user:
        email = user['email']
        wallet = user['wallet'] if user['wallet'] else "0 USDT"
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
    wallet_balance = user['wallet'] if user and user['wallet'] else "0 USDT"
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
    from database import add_withdraw_request

    email = session['email']
    amount = float(request.form['amount'])
    address = request.form['address']
    password = request.form['password']

    user = get_user_by_email(email)
    if not user or not check_password_hash(user['password'], password):
        flash("Invalid password", "danger")
        return redirect(url_for('withdraw_request'))

    current_balance = float(get_user_wallet(email))
    if amount > current_balance:
        flash("Insufficient balance", "danger")
        return redirect(url_for('withdraw_request'))

    add_withdraw_request(email, amount, address)
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
    if 'email' not in session or session['email'] != 'vumiiliakonga2@gmail.com':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    from database import get_pending_deposits, get_pending_withdrawals
    deposits = get_pending_deposits()
    withdrawals = get_pending_withdrawals()

    return render_template('admin.html', deposits=deposits, withdrawals=withdrawals)
@app.route('/admin/approve-deposit/<string:deposit_id>')
def approve_deposit_route(deposit_id):
    from database import approve_deposit
    approve_deposit(deposit_id)
    flash("Deposit approved", "success")
    return redirect(url_for('admin'))

@app.route('/admin/reject-deposit/<string:deposit_id>')
def reject_deposit_route(deposit_id):
    from database import reject_deposit
    reject_deposit(deposit_id)
    flash("Deposit rejected", "warning")
    return redirect(url_for('admin'))

@app.route('/admin/approve-withdraw/<withdraw_id>')
def approve_withdrawal_route(withdraw_id):
    withdraw = get_withdraw_by_id(withdraw_id)
    if not withdraw:
        flash("Withdrawal not found", "danger")
        return redirect(url_for('admin'))

    if withdraw["status"] != "pending":
        flash("Already processed", "info")
        return redirect(url_for('admin'))

    amount = withdraw["amount"]
    if amount <= 0:
        flash("Invalid amount", "danger")
        return redirect(url_for('admin'))

    user = get_user_by_email(withdraw["email"])
    if user["wallet"] < amount:
        flash("Insufficient user balance", "danger")
        return redirect(url_for('admin'))

    update_withdraw_status(withdraw_id, "approved")
    update_wallet_balance(user["email"], -amount)
    add_transaction(user["email"], "withdrawal", amount)

    flash("Withdrawal approved", "success")
    return redirect(url_for('admin'))  # ✅ THIS LINE IS MANDATORY

@app.route('/admin/reject-withdraw/<withdraw_id>')
def reject_withdrawal_route(withdraw_id):
    from database import reject_withdrawal
    reject_withdrawal(withdraw_id)
    flash("Withdrawal rejected", "warning")
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
