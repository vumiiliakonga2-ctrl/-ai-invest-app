from supabase import create_client, Client
from datetime import datetime
import os

# Load Supabase URL and Key from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ────────────────────────────────
# USER MANAGEMENT
# ────────────────────────────────
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
