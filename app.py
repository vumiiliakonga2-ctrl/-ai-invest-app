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
from database import get_user_by_email, process_user_earnings
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
    
    # Get user details
    user = get_user_by_email(session['email'])

    if user:
        email = user['email']
        wallet = user['wallet'] if user['wallet'] else "0 USDT"

        # ✅ Process their daily earnings here
        process_user_earnings(email)

    else:
        email = session['email']
        wallet = "0 USDT"

    random.shuffle(fake_withdrawals)
    
    return render_template('dashboard.html', email=email, wallet=wallet, withdrawals=fake_withdrawals)



@app.route('/wallet', methods=['GET'])
def wallet_page():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']
    user = get_user_by_email(email)
    wallet_balance = user['wallet'] if user and user['wallet'] else "0 USDT"
    transactions = get_user_transactions(email)

    from database import get_locked_assets, get_locked_investments
    locked_balance = get_locked_assets(email)
    locked_details = get_locked_investments(email)

    return render_template(
        'wallet.html',
        email=email,
        wallet=wallet_balance,
        transactions=transactions,
        locked_balance=locked_balance,
        locked_details=locked_details
    )

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

    from database import get_user_wallet, add_withdraw_request

    email = session['email']
    amount = float(request.form['amount'])
    address = request.form['address']
    password = request.form['password']

    user = get_user_by_email(email)
    if not user or not check_password_hash(user['password'], password):
        flash("Invalid password", "danger")
        return redirect(url_for('withdraw_request'))

    # ✅ Block negative or zero amounts
    if amount <= 0:
        flash("Amount must be greater than zero", "danger")
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
    update_wallet_balance(user["email"], amount, "withdraw")
    add_transaction(user["email"], "withdraw", amount)

    flash("Withdrawal approved", "success")
    return redirect(url_for('admin'))  # ✅ THIS LINE IS MANDATORY

@app.route('/admin/reject-withdraw/<withdraw_id>')
def reject_withdrawal_route(withdraw_id):
    from database import reject_withdrawal
    reject_withdrawal(withdraw_id)
    flash("Withdrawal rejected", "warning")
    return redirect(url_for('admin'))
@app.route('/invest')
def invest():
    if 'email' not in session:
        return redirect(url_for('login'))

    from database import get_all_deposits, get_vip_from_deposit, generate_all_plans, get_user_by_email

    email = session['email']
    deposits = get_all_deposits(email)
    total_deposit = sum(float(d["amount"]) for d in deposits) if deposits else 0.0

    vip_info = get_vip_from_deposit(total_deposit)
    unlocked_vip = vip_info['vip'] if vip_info else 1

    plans = generate_all_plans(unlocked_vip)
    user = get_user_by_email(email)

    vip_colors = {
        1: "bg-yellow-100 border-yellow-400",
        2: "bg-blue-100 border-blue-400",
        3: "bg-purple-100 border-purple-400",
        4: "bg-pink-100 border-pink-400",
        5: "bg-orange-100 border-orange-400",
        6: "bg-teal-100 border-teal-400",
        7: "bg-red-100 border-red-400"
    }

    for plan in plans:
        plan["color"] = vip_colors.get(plan["vip"], "bg-gray-100 border-gray-400")

    return render_template("investment.html", plans=plans, email=email, wallet=user['wallet'])

@app.route('/confirm_investment', methods=['POST'])
def confirm_investment():
    email = session['email']
    amount = float(request.form['amount'])
    vip = int(request.form['vip'])
    percent = float(request.form['percent'])

    start_date = datetime.utcnow()
    unlock_date = start_date + timedelta(days=90)

    update_wallet_balance(email, -amount)
    supabase.table('user_investments').insert({
        "user_email": email,
        "amount": amount,
        "vip_level": vip,
        "daily_return": percent,
        "start_date": start_date.isoformat(),
        "unlock_date": unlock_date.isoformat(),
        "last_paid": start_date.isoformat(),
        "status": "active"
    }).execute()

    flash("Investment confirmed. Capital and earnings locked for 90 days.", "success")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
