from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import add_user, get_user_by_email, save_kyc
from werkzeug.security import generate_password_hash, check_password_hash
import os
from database import get_vip_from_deposit, generate_all_plans
from datetime import datetime, timedelta
from database import update_wallet
from datetime import datetime, timezone  # make sure this is at the top of your app.py

import random
from database import get_user_transactions, add_transaction, update_wallet_balance
from database import (
    get_all_users, get_all_deposits, get_all_withdrawals,
    approve_withdrawal_request, reject_withdrawal_request
)
from database import get_withdraw_by_id, get_user_by_email, update_withdraw_status, update_wallet_balance, add_transaction
from database import get_user_by_email, process_user_earnings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
from datetime import datetime, timedelta
from email_utils import send_verification_code


EMAIL_SENDER = "vumiiliakonga2@gmail.com"
EMAIL_PASSWORD = "uswi tjdv kzdg gjwz"  # Use Gmail App Password, not your real password

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
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)


@app.route('/confirm_investment', methods=['POST'])
def confirm_investment():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']
    user = get_user_by_email(email)

    if not user:
        flash("User not found", "danger")
        return redirect(url_for('invest'))

    try:
        amount = float(request.form['amount'])
        vip = int(request.form['vip'])
        percent = float(request.form['percent'])
    except:
        flash("Invalid input", "danger")
        return redirect(url_for('invest'))

    # ✅ Recalculate total deposit and unlocked VIP
    deposits = get_all_deposits(email)
    total_deposit = sum(float(d["amount"]) for d in deposits) if deposits else 0.0
    unlocked_vip = get_vip_from_deposit(total_deposit)['vip']

    if vip > unlocked_vip:
        flash(f"VIP {vip} is locked. Your current VIP level is {unlocked_vip}.", "warning")
        return redirect(url_for('invest'))

    # ✅ Validate plan and range
    all_plans = generate_all_plans(unlocked_vip)
    selected_plan = next((p for p in all_plans if p['vip'] == vip), None)

    if not selected_plan:
        flash("Invalid plan selected", "danger")
        return redirect(url_for('invest'))

    if not (selected_plan['min'] <= amount <= selected_plan['max']):
        flash(f"Amount must be between ${selected_plan['min']} and ${selected_plan['max']} for VIP {vip}", "warning")
        return redirect(url_for('invest'))

    # ✅ Always use FRESH wallet
    user = get_user_by_email(email)  # Refetch fresh data
    wallet = user.get("wallet", {"available": 0, "locked": 0})
    available = float(wallet.get("available", 0))
    locked = float(wallet.get("locked", 0))

    if amount > available:
        flash("Insufficient available balance", "danger")
        return redirect(url_for('wallet_page'))

    # ✅ Move amount from available to locked
    new_wallet = {
        "available": round(available - amount, 2),
        "locked": round(locked + amount, 2)
    }

    # Optional: safety check (can be removed in prod)
    if round(available + locked, 2) != round(new_wallet["available"] + new_wallet["locked"], 2):
        flash("Wallet error. Please try again.", "danger")
        return redirect(url_for('wallet_page'))

    update_wallet(email, new_wallet)

    # ✅ Insert investment record
    start_date = datetime.utcnow()
    unlock_date = start_date + timedelta(days=90)

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']

        user = get_user_by_email(email)
        if user:
            flash("Email already registered", "danger")
            return redirect(url_for('register'))

        add_user(email, password)

        # Generate code and save
        code = f"{random.randint(100000, 999999)}"
        expires = datetime.utcnow() + timedelta(minutes=10)

        supabase.table('email_verifications').upsert({
            "email": email,
            "code": code,
            "expires_at": expires.isoformat()
        }).execute()

        send_verification_code(email, code)

        session['pending_email'] = email
        return redirect(url_for('verify_code_page'))

    return render_template('register.html')

@app.route('/verify-code', methods=['GET', 'POST'])
def verify_code_page():
    if 'pending_email' not in session:
        return redirect(url_for('login'))

    email = session['pending_email']

    if request.method == 'POST':
        code = request.form['code']

        # ✅ Check code match
        response = supabase.table("email_verifications").select("*").eq("email", email).eq("code", code).execute()
        record = response.data[0] if response.data else None

        if not record:
            flash("Invalid verification code", "danger")
            return redirect(url_for('verify_code_page'))

        # ✅ Convert to timezone-aware datetime
        expires_at = datetime.fromisoformat(record['expires_at'].replace('Z', '+00:00'))

        if datetime.now(timezone.utc) > expires_at:
            flash("Code expired", "danger")
            return redirect(url_for('verify_code_page'))

        # ✅ Success: mark user as verified
        supabase.table("users").update({"is_verified": True}).eq("email", email).execute()
        supabase.table("email_verifications").delete().eq("email", email).execute()
        session.pop("pending_email")

        flash("Email verified successfully! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template("verify_code.html", email=email)

        

def send_verification_code(email, code):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your AI Invest Verification Code"
    msg["From"] = EMAIL_SENDER
    msg["To"] = email

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
      <h2>Welcome to AI Invest!</h2>
      <p>Use the following code to verify your email address:</p>
      <h1 style="color: #007bff;">{code}</h1>
      <p>This code will expire in 10 minutes.</p>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, email, msg.as_string())
    except Exception as e:
        print("Error sending email:", e)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)

        if not user['is_verified']:
            flash("Please verify your email before logging in.", "warning")
            return redirect(url_for('login'))

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

    if not user:
        flash("User not found", "danger")
        return redirect(url_for('login'))

    # ✅ Require email verification
    if not user.get("is_verified", False):
        flash("Please verify your email before accessing your dashboard.", "warning")
        return redirect(url_for('login'))

    email = user['email']
    wallet = user['wallet'] if user['wallet'] else "0 USDT"

    # ✅ Process their daily earnings here
    process_user_earnings(email)

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
    unlocked_vip = vip_info['vip'] if total_deposit > 0 else 0

    plans = generate_all_plans(unlocked_vip)
    user = get_user_by_email(email)

    vip_colors = {
        1: {"bg": "#fff8dc", "border": "#ffd700", "text": "#b8860b", "button_bg": "#ffcc00", "button_text": "Invest Now"},
        2: {"bg": "#e6f0ff", "border": "#3399ff", "text": "#003366", "button_bg": "#3399ff", "button_text": "Invest Now"},
        3: {"bg": "#f3e6ff", "border": "#9933ff", "text": "#6600cc", "button_bg": "#9933ff", "button_text": "Invest Now"},
        4: {"bg": "#ffe6f0", "border": "#ff66b2", "text": "#cc0066", "button_bg": "#ff66b2", "button_text": "Invest Now"},
        5: {"bg": "#fff0e6", "border": "#ff9933", "text": "#cc6600", "button_bg": "#ff9933", "button_text": "Invest Now"},
        6: {"bg": "#e6ffe6", "border": "#33cc33", "text": "#006600", "button_bg": "#33cc33", "button_text": "Invest Now"},
        7: {"bg": "#ffe6e6", "border": "#ff3333", "text": "#990000", "button_bg": "#ff3333", "button_text": "Invest Now"},
    }

    # ✅ Mark each plan with whether it's currently investable
    for plan in plans:
        colors = vip_colors.get(plan["vip"], {
            "bg": "#f1f1f1", "border": "#ccc", "text": "#666", "button_bg": "#999", "button_text": "Invest"
        })
        plan.update(colors)

        plan["is_current_vip"] = (plan["vip"] == unlocked_vip)

    return render_template("investment.html", plans=plans, email=email, wallet=user['wallet'])


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
