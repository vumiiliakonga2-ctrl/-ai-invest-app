from supabase import create_client
import os
from datetime import datetime, timedelta
import uuid
import smtplib
from email.message import EmailMessage
from email_utils import send_verification_code
import requests

API_KEY = 'ZRWVXEE-83K45AK-K6BYMA9-ZQ55CJN'
def log_nowpayments_transaction(user_email, order_id, amount, currency, status, raw_data):
    supabase.table('nowpayments_logs').insert({
        "id": str(uuid.uuid4()),
        "user_email": user_email,
        "order_id": order_id,
        "amount": amount,
        "currency": currency,
        "status": status,
        "raw_data": raw_data
    }).execute()
def get_all_nowpayments_logs():
    response = supabase.table('nowpayments_logs').select('*').order('created_at', desc=True).execute()
    return response.data


def create_nowpayments_invoice(amount, currency, order_id):
    url = "https://api.nowpayments.io/v1/invoice"
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": currency.lower(),
        "order_id": order_id,
        "ipn_callback_url": "https://your-domain.com/ipn-handler"
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()

def get_referral_badge(ref_count):
    if ref_count >= 50:
        return {"label": "🏆 Legend", "class": "bg-warning text-dark"}
    elif ref_count >= 20:
        return {"label": "🔥 Pro", "class": "bg-danger"}
    elif ref_count >= 10:
        return {"label": "💼 Ambassador", "class": "bg-info"}
    elif ref_count >= 5:
        return {"label": "🌟 Influencer", "class": "bg-primary"}
    elif ref_count >= 1:
        return {"label": "🎉 Starter", "class": "bg-success"}
    else:
        return {"label": "🔒 No Badge Yet", "class": "bg-secondary"}


def get_total_invested_by_user(email):
    response = supabase.table("investments").select("amount").eq("email", email).execute()
    amounts = [row['amount'] for row in response.data]
    return sum(amounts)
def get_user_by_referral_code(code):
    response = supabase.table("users").select("*").eq("referral_code", code).single().execute()
    return response.data

def get_referrals_for_user(referral_code):
    response = supabase.table("users").select("*").eq("referred_by", referral_code).execute()
    return response.data

def send_verification_email(email, code):
    msg = EmailMessage()
    msg['Subject'] = 'Your Verification Code - AI Crypto App'
    msg['From'] = 'vumiiliakonga2@gmail.com'
    msg['To'] = to_email

    msg.set_content(f'''
    Hello,

    Your verification code is: {code}

    Enter this code in the app to verify your email address.

    Regards,
    AI Crypto App Team
    ''')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login('vumiiliakonga2@gmail.com', 'uswi tjdv kzdg gjwz')  # use App Password here
            server.send_message(msg)
            print("Verification email sent successfully.")
    except Exception as e:
        print(f"Email sending failed: {e}")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

### === USER & WALLET ===
def reject_withdrawal_request(withdraw_id):
    update_withdraw_status(withdraw_id, "rejected")
def update_wallet(email, new_wallet):
    supabase.table("users").update({"wallet": new_wallet}).eq("email", email).execute()

def get_all_withdrawals(email):
    result = supabase.table("withdraw_requests").select("*").eq("email", email).eq("status", "approved").execute()
    return result.data if result.data else []

def add_user(email, password, referred_by=None):
    from werkzeug.security import generate_password_hash
    hashed_password = generate_password_hash(password)

    referral_code = str(uuid.uuid4())[:8]

    user_data = {
        'email': email,
        'password': hashed_password,
        'wallet': {'available': 0.0, 'locked': 0.0},
        'referral_code': referral_code,
        'referred_by': referred_by
    }

    supabase.table("users").insert(user_data).execute()

def get_user_by_email(email):
    try:
        response = supabase.table('users').select("*").eq("email", email).single().execute()
        return response.data
    except Exception as e:
        print("Error fetching user:", e)
        return None

def get_all_users():
    result = supabase.table("users").select("*").execute()
    return result.data if result.data else []

def get_user_wallet(email):
    user = get_user_by_email(email)
    if not user or "wallet" not in user:
        return 0.0
    return float(user["wallet"].get("available", 0.0))

def update_wallet_balance(email, amount, tx_type):
    user = get_user_by_email(email)
    if not user or "wallet" not in user:
        return
    wallet = user["wallet"]
    if tx_type == "deposit":
        wallet["available"] += amount
    elif tx_type == "withdraw":
        wallet["available"] -= amount
    elif tx_type == "invest":
        wallet["available"] -= amount
        wallet["locked"] += amount
    elif tx_type == "earn":
        wallet["available"] += amount
    elif tx_type == "unlock":
        wallet["locked"] -= amount
        wallet["available"] += amount
    supabase.table("users").update({"wallet": wallet}).eq("email", email).execute()

### === KYC ===

def save_kyc(email, file_path):
    supabase.table("kyc").insert({"email": email, "file_path": file_path}).execute()

### === DEPOSITS ===

def add_deposit_request(email, amount, method):
    supabase.table("deposit_requests").insert({
        "id": str(uuid.uuid4()),
        "email": email,
        "amount": amount,
        "method": method,
        "status": "pending",
        "timestamp": datetime.utcnow().isoformat()
    }).execute()

def get_pending_deposits():
    result = supabase.table("deposit_requests").select("*").eq("status", "pending").execute()
    return result.data if result.data else []

def get_all_deposits(email):
    result = supabase.table("deposit_requests").select("*").eq("email", email).eq("status", "approved").execute()
    return result.data if result.data else []
def approve_deposit(deposit_id):
    result = supabase.table("deposit_requests").select("*").eq("id", deposit_id).single().execute()
    deposit = result.data

    if not deposit or deposit["status"] != "pending":
        return  # Exit if already approved/rejected or doesn't exist

    # ✅ Credit wallet
    update_wallet_balance(deposit["email"], float(deposit["amount"]), "deposit")

    # ✅ Record transaction
    add_transaction(deposit["email"], "deposit", float(deposit["amount"]))

    # ✅ Update status to approved
    supabase.table("deposit_requests").update({"status": "approved"}).eq("id", deposit_id).execute()


def reject_deposit(deposit_id):
    supabase.table("deposit_requests").update({"status": "rejected"}).eq("id", deposit_id).execute()

### === WITHDRAWALS ===

def add_withdraw_request(email, amount, address):
    supabase.table("withdraw_requests").insert({
        "id": str(uuid.uuid4()),
        "email": email,
        "amount": amount,
        "address": address,
        "status": "pending",
        "timestamp": datetime.utcnow().isoformat()
    }).execute()

def get_pending_withdrawals():
    result = supabase.table("withdraw_requests").select("*").eq("status", "pending").execute()
    return result.data if result.data else []

def get_withdraw_by_id(withdraw_id):
    result = supabase.table("withdraw_requests").select("*").eq("id", withdraw_id).single().execute()
    return result.data if result.data else None

def update_withdraw_status(withdraw_id, status):
    supabase.table("withdraw_requests").update({"status": status}).eq("id", withdraw_id).execute()

def reject_withdrawal(withdraw_id):
    update_withdraw_status(withdraw_id, "rejected")

def approve_withdrawal_request(withdraw_id):
    withdraw = get_withdraw_by_id(withdraw_id)
    if not withdraw or withdraw["status"] != "pending":
        return

    amount = float(withdraw["amount"])
    email = withdraw["email"]
    user = get_user_by_email(email)
    if not user or float(user["wallet"].get("available", 0)) < amount:
        return

    update_wallet_balance(email, amount, "withdraw")
    add_transaction(email, "withdraw", amount)
    update_withdraw_status(withdraw_id, "approved")

### === TRANSACTIONS ===

def add_transaction(email, tx_type, amount):
    supabase.table("transactions").insert({
        "email": email,
        "tx_type": tx_type,
        "amount": amount,
        "timestamp": datetime.utcnow().isoformat()
    }).execute()

def get_user_transactions(email):
    result = supabase.table("transactions").select("*").eq("email", email).order("timestamp", desc=True).execute()
    return result.data if result.data else []

### === INVESTMENTS ===

def get_locked_assets(email):
    user = get_user_by_email(email)
    return float(user["wallet"].get("locked", 0)) if user and "wallet" in user else 0.0

def get_locked_investments(email):
    result = supabase.table("user_investments").select("*").eq("user_email", email).eq("status", "active").execute()
    return result.data if result.data else []

def process_user_earnings(email):
    result = supabase.table("user_investments").select("*").eq("user_email", email).eq("status", "active").execute()
    investments = result.data if result.data else []

    for inv in investments:
        last_paid = datetime.fromisoformat(inv["last_paid"])
        now = datetime.utcnow()
        days_passed = (now - last_paid).days

        if days_passed > 0:
            daily_return = float(inv["daily_return"])
            amount = float(inv["amount"])
            earnings = amount * (daily_return / 100) * days_passed
            update_wallet_balance(email, earnings, "earn")
            add_transaction(email, "earn", earnings)
            supabase.table("user_investments").update({
                "last_paid": now.isoformat()
            }).eq("id", inv["id"]).execute()

def unlock_investments(email):
    now = datetime.utcnow()
    result = supabase.table("user_investments").select("*").eq("user_email", email).eq("status", "active").execute()
    investments = result.data if result.data else []

    for inv in investments:
        if datetime.fromisoformat(inv["unlock_date"]) <= now:
            update_wallet_balance(email, float(inv["amount"]), "unlock")
            supabase.table("user_investments").update({"status": "unlocked"}).eq("id", inv["id"]).execute()
            add_transaction(email, "unlock", float(inv["amount"]))

### === VIP LOGIC ===
def get_vip_from_deposit(total_deposit):
    vip = 0
    percent = 0
    max_vip = 15

    for level in range(1, max_vip + 1):
        min_amount = 12 + (level - 1) * 77
        max_amount = 88 + (level - 1) * 300

        if min_amount <= total_deposit <= max_amount:
            vip = level
            percent = 15 + (level - 1)
            if vip >= 6:
                percent = 16  # cap at 16% for VIP 6 and 7
            break
        elif total_deposit > max_amount:
            vip = level
            percent = 15 + (level - 1)
            if vip >= 6:
                percent = 16
        else:
            break

    return {"vip": vip, "percent": percent}

def generate_all_plans(unlocked_vip):
    plans = []
    for vip in range(1, 8):
        min_amount = 12 + (vip - 1) * 77
        max_amount = 88 + (vip - 1) * 300
        percent = 15 + (vip - 1)
        if vip >= 6:
            percent = 16
        plans.append({
            "vip": vip,
            "min": min_amount,
            "max": max_amount,
            "percent": percent,
            "locked": vip > unlocked_vip
        })
    return plans
