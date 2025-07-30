
from supabase import create_client
import os
from datetime import datetime
import uuid

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def add_user(email, password_hash):
    return supabase.table('users').insert({
        "email": email,
        "password": password_hash,
        "wallet": {"available": 0, "locked": 0}
    }).execute()

def get_user_by_email(email):
    result = supabase.table('users').select("*").eq("email", email).single().execute()
    return result.data if result.data else None

def get_user_wallet(email):
    user = get_user_by_email(email)
    if not user or "wallet" not in user:
        return 0
    return float(user["wallet"].get("available", 0))

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

def save_kyc(email, file_path):
    supabase.table("kyc").insert({"email": email, "file_path": file_path}).execute()

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
    if not deposit:
        return
    update_wallet_balance(deposit["email"], float(deposit["amount"]), "deposit")
    add_transaction(deposit["email"], "deposit", float(deposit["amount"]))
    supabase.table("deposit_requests").update({"status": "approved"}).eq("id", deposit_id).execute()

def reject_deposit(deposit_id):
    supabase.table("deposit_requests").update({"status": "rejected"}).eq("id", deposit_id).execute()

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
    supabase.table("withdraw_requests").update({"status": "rejected"}).eq("id", withdraw_id).execute()

def get_locked_assets(email):
    user = get_user_by_email(email)
    if not user or "wallet" not in user:
        return 0.0
    return float(user["wallet"].get("locked", 0))

def get_locked_investments(email):
    result = supabase.table("user_investments").select("*").eq("user_email", email).eq("status", "active").execute()
    return result.data if result.data else []

def get_vip_from_deposit(total_deposit):
    vip = 0
    percent = 0
    max_vip = 7
    for level in range(1, max_vip + 1):
        min_amount = 12 + (level - 1) * 77
        max_amount = 88 + (level - 1) * 300
        if total_deposit >= min_amount:
            vip = level
            percent = 15 + min(level - 1, 5)  # 15% + 1% per tier up to +5%
        else:
            break
    if total_deposit >= 89:
        percent = 16
    return {"vip": vip, "percent": percent}

def generate_all_plans(unlocked_vip):
    plans = []
    for vip in range(1, 8):
        min_amount = 12 + (vip - 1) * 77
        max_amount = 88 + (vip - 1) * 300
        percent = 15 + (vip - 1)
        if vip >= 6:
            percent = 16  # final tiers get capped
        plans.append({
            "vip": vip,
            "min": min_amount,
            "max": max_amount,
            "percent": percent,
            "locked": vip > unlocked_vip
        })
    return plans

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
