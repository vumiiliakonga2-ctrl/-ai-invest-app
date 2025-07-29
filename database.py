from supabase import create_client, Client
from datetime import datetime
import os
from datetime import datetime, timedelta
# Load Supabase URL and Key from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ────────────────────────────────
# USER MANAGEMENT
# ────────────────────────────────
def get_total_deposit(email):
    deposits = get_all_deposits(email)
    return sum(float(d["amount"]) for d in deposits) if deposits else 0.0

def get_vip_level_from_deposit(total):
    if total < 89:
        return 1
    elif 89 <= total <= 289:
        return 2
    elif 290 <= total <= 589:
        return 3
    elif 590 <= total <= 889:
        return 4
    elif 890 <= total <= 1689:
        return 5
    # ... and so on

def add_to_wallet(email, amount):
    user = supabase.table("users").select("wallet").eq("email", email).single().execute().data
    current_balance = float(user["wallet"]) if user and user["wallet"] else 0.0
    new_balance = current_balance + amount

    supabase.table("users").update({"wallet": new_balance}).eq("email", email).execute()

    # Optional: log it to transactions table
    supabase.table("transactions").insert({
        "user_email": email,
        "type": "earning",
        "amount": round(amount, 2),
        "date": datetime.utcnow().isoformat()
    }).execute()

def process_user_earnings(email):
    today = datetime.utcnow()
    investments = supabase.table("user_investments") \
        .select("*") \
        .eq("user_email", email) \
        .eq("status", "active") \
        .execute().data

    for inv in investments:
        unlock_date = datetime.fromisoformat(inv["unlock_date"])
        if unlock_date < today:
            # Mark as expired
            supabase.table("user_investments") \
                .update({"status": "expired"}) \
                .eq("id", inv["id"]).execute()
            continue

        last_paid = datetime.fromisoformat(inv["last_paid"])
        if (today - last_paid).days >= 1:
            # Credit daily earning
            earning = (inv["amount"] * inv["daily_return"]) / 100
            add_to_wallet(inv["user_email"], earning)

            # Update last_paid
            supabase.table("user_investments") \
                .update({"last_paid": today.isoformat()}) \
                .eq("id", inv["id"]).execute()

def get_locked_assets(email):
    result = supabase.table("user_investments").select("amount").eq("user_email", email).eq("status", "active").execute()
    return sum(row["amount"] for row in result.data)

def get_locked_investments(email):
    return supabase.table("user_investments").select("amount", "unlock_date").eq("user_email", email).eq("status", "active").execute().data

def get_vip_from_deposit(amount):
    vip = 1
    percent = 15
    start = 12
    stop = 88
    increment = 0

    while stop <= 100000:
        if start <= amount <= stop:
            return {"vip": vip, "percent": percent, "min": start, "max": stop}

        if vip == 1:
            increment = 201
        elif vip in [2, 3, 4]:
            increment = 300
        elif vip in [5, 6]:
            increment = 800
        else:
            increment = 1200

        start = stop + 1
        stop += increment
        percent += 1
        vip += 1

    return None
def generate_all_plans(unlocked_vip):
    plans = []
    vip = 1
    percent = 15
    start = 12
    stop = 88
    increment = 0

    while stop <= 100000:
        unlocked = vip == unlocked_vip
        plans.append({
            "vip": vip,
            "percent": percent,
            "min": start,
            "max": stop,
            "unlocked": unlocked
        })

        if vip == 1:
            increment = 201
        elif vip in [2, 3, 4]:
            increment = 300
        elif vip in [5, 6]:
            increment = 800
        else:
            increment = 1200

        start = stop + 1
        stop += increment
        percent += 1
        vip += 1

    return plans

def get_withdraw_by_id(withdraw_id):
    response = supabase.table("withdrawals").select("*").eq("id", withdraw_id).single().execute()
    if response.data:
        return response.data
    else:
        return None
def get_withdraw_by_id(withdraw_id):
    response = supabase.table("withdraw_requests").select("*").eq("id", withdraw_id).single().execute()
    return response.data if response.data else None

def update_withdraw_status(withdraw_id, new_status):
    return supabase.table("withdraw_requests").update({"status": new_status}).eq("id", withdraw_id).execute()

def approve_withdrawal_request(withdraw_id):
    supabase.table("withdrawals").update({"status": "approved"}).eq("id", withdraw_id).execute()

def reject_withdrawal_request(withdraw_id):
    supabase.table("withdrawals").update({"status": "rejected"}).eq("id", withdraw_id).execute()

def get_all_deposits():
    result = supabase.table("deposits").select("*").order("timestamp", desc=True).execute()
    return result.data
def get_all_withdrawals():
    result = supabase.table("withdrawals").select("*").order("timestamp", desc=True).execute()
    return result.data

def get_all_users():
    result = supabase.table("users").select("id, email, wallet, kyc_file").execute()
    return result.data

def get_pending_deposits():
    result = supabase.table("deposit_requests")\
        .select("*")\
        .eq("status", "pending")\
        .order("date", desc=True)\
        .execute()
    return result.data

def approve_deposit(deposit_id):
    deposit = supabase.table("deposit_requests").select("*").eq("id", deposit_id).execute().data[0]
    supabase.table("deposit_requests").update({"status": "approved"}).eq("id", deposit_id).execute()
    update_wallet_balance(deposit["email"], deposit["amount"], "deposit")
    add_transaction(deposit["email"], "deposit", deposit["amount"])

def reject_deposit(deposit_id):
    return supabase.table("deposit_requests").update({"status": "rejected"}).eq("id", deposit_id).execute()


def get_pending_withdrawals():
    result = supabase.table("withdraw_requests")\
        .select("*")\
        .eq("status", "pending")\
        .order("date", desc=True)\
        .execute()
    return result.data

def approve_withdrawal(withdraw_id):
    withdraw = supabase.table("withdraw_requests").select("*").eq("id", withdraw_id).execute().data[0]
    supabase.table("withdraw_requests").update({"status": "approved"}).eq("id", withdraw_id).execute()
    update_wallet_balance(withdraw["email"], withdraw["amount"], "withdraw")
    add_transaction(withdraw["email"], "withdraw", withdraw["amount"])

def reject_withdrawal(withdraw_id):
    return supabase.table("withdraw_requests").update({"status": "rejected"}).eq("id", withdraw_id).execute()

def add_user(email, hashed_password):
    result = supabase.table("users").insert({
        "email": email,
        "password": hashed_password,
        "wallet": 0
    }).execute()
    return result.data

def get_user_by_email(email):
    result = supabase.table("users").select("*").eq("email", email).execute()
    data = result.data
    return data[0] if data else None

def get_user_wallet(email):
    user = get_user_by_email(email)
    return user['wallet'] if user else 0

def save_kyc(email, filepath):
    return supabase.table("users").update({"kyc_file": filepath}).eq("email", email).execute()

# ────────────────────────────────
# WALLET & TRANSACTIONS
# ────────────────────────────────
def update_wallet_balance(email, amount, tx_type):
    user = get_user_by_email(email)
    if not user:
        return None

    current_balance = user['wallet'] or 0
    new_balance = current_balance + amount if tx_type == 'deposit' else current_balance - amount

    return supabase.table("users").update({"wallet": new_balance}).eq("email", email).execute()


def add_transaction(email, tx_type, amount):
    now = datetime.now().isoformat()
    return supabase.table("transactions").insert({
        "email": email,
        "type": tx_type,
        "amount": amount,
        "date": now
    }).execute()
def get_all_transactions():
    result = supabase.table("transactions").select("*").order("date", desc=True).execute()
    return result.data


def get_user_transactions(email):
    result = supabase.table("transactions")\
        .select("type, amount, date")\
        .eq("email", email)\
        .order("date", desc=True)\
        .limit(10)\
        .execute()
    return result.data

# ────────────────────────────────
# DEPOSIT / WITHDRAW REQUESTS
# ────────────────────────────────
def add_deposit_request(email, amount, method):
    now = datetime.now().isoformat()
    return supabase.table("deposit_requests").insert({
        "email": email,
        "amount": amount,
        "method": method,
        "status": "pending",
        "date": now
    }).execute()

def add_withdraw_request(email, amount, address):
    now = datetime.now().isoformat()
    return supabase.table("withdraw_requests").insert({
        "email": email,
        "amount": amount,
        "address": address,
        "status": "pending",
        "date": now
    }).execute()
