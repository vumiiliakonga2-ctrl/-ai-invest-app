from supabase import create_client
import os
from uuid import uuid4
from datetime import datetime

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# ---------------- USER AUTH ---------------- #
def add_user(email, hashed_password):
    supabase.table("users").insert({
        "email": email,
        "password": hashed_password,
        "wallet": {"available": 0.0, "locked": 0.0}
    }).execute()

def get_user_by_email(email):
    result = supabase.table("users").select("*").eq("email", email).single().execute()
    return result.data if result.data else None

# ---------------- WALLET ---------------- #
def get_user_wallet(email):
    user = get_user_by_email(email)
    return float(user["wallet"]["available"]) if user and user.get("wallet") else 0.0

def update_wallet_balance(email, amount, tx_type):
    user = get_user_by_email(email)
    if not user: return

    wallet = user.get("wallet", {"available": 0.0, "locked": 0.0})

    if tx_type == "invest":
        wallet["available"] -= amount
        wallet["locked"] += amount
    elif tx_type == "unlock":
        wallet["locked"] -= amount
        wallet["available"] += amount
    elif tx_type == "withdraw":
        wallet["available"] -= amount
    elif tx_type == "deposit":
        wallet["available"] += amount

    supabase.table("users").update({"wallet": wallet}).eq("email", email).execute()

# ---------------- KYC ---------------- #
def save_kyc(email, filepath):
    supabase.table("kyc").insert({"email": email, "filepath": filepath}).execute()

# ---------------- TRANSACTIONS ---------------- #
def add_transaction(email, tx_type, amount):
    supabase.table("transactions").insert({
        "email": email,
        "tx_type": tx_type,
        "amount": amount,
        "timestamp": datetime.utcnow().isoformat()
    }).execute()

def get_user_transactions(email):
    res = supabase.table("transactions").select("*").eq("email", email).order("timestamp", desc=True).execute()
    return res.data if res.data else []

# ---------------- DEPOSITS ---------------- #
def add_deposit_request(email, amount, method):
    supabase.table("deposit_requests").insert({
        "id": str(uuid4()),
        "email": email,
        "amount": amount,
        "method": method,
        "status": "pending"
    }).execute()

def get_pending_deposits():
    return supabase.table("deposit_requests").select("*").eq("status", "pending").execute().data

def approve_deposit(deposit_id):
    req = supabase.table("deposit_requests").select("*").eq("id", deposit_id).single().execute().data
    if req and req["status"] == "pending":
        update_wallet_balance(req["email"], float(req["amount"]), "deposit")
        add_transaction(req["email"], "deposit", float(req["amount"]))
        supabase.table("deposit_requests").update({"status": "approved"}).eq("id", deposit_id).execute()

def reject_deposit(deposit_id):
    supabase.table("deposit_requests").update({"status": "rejected"}).eq("id", deposit_id).execute()

def get_all_deposits(email):
    return supabase.table("deposit_requests").select("*").eq("email", email).eq("status", "approved").execute().data

# ---------------- WITHDRAWALS ---------------- #
def add_withdraw_request(email, amount, address):
    supabase.table("withdraw_requests").insert({
        "id": str(uuid4()),
        "email": email,
        "amount": amount,
        "address": address,
        "status": "pending"
    }).execute()

def get_pending_withdrawals():
    return supabase.table("withdraw_requests").select("*").eq("status", "pending").execute().data

def get_withdraw_by_id(withdraw_id):
    result = supabase.table("withdraw_requests").select("*").eq("id", withdraw_id).single().execute()
    return result.data if result.data else None

def update_withdraw_status(withdraw_id, new_status):
    supabase.table("withdraw_requests").update({"status": new_status}).eq("id", withdraw_id).execute()

def approve_withdrawal(withdraw_id):
    withdraw = get_withdraw_by_id(withdraw_id)
    if withdraw and withdraw["status"] == "pending":
        update_withdraw_status(withdraw_id, "approved")
        update_wallet_balance(withdraw["email"], float(withdraw["amount"]), "withdraw")
        add_transaction(withdraw["email"], "withdraw", float(withdraw["amount"]))

def reject_withdrawal(withdraw_id):
    update_withdraw_status(withdraw_id, "rejected")

# ---------------- VIP & PLANS ---------------- #
def get_vip_from_deposit(total_deposit):
    vip = 0
    if total_deposit >= 12:
        vip = 1
        if total_deposit > 89:
            vip = 2
        if total_deposit >= 300:
            vip += int((total_deposit - 300) // 300) + 1
        vip = min(vip, 7)
    return {"vip": vip}

def generate_all_plans(unlocked_vip):
    plans = []
    for vip in range(1, unlocked_vip + 1):
        base = 15.0
        extra = (vip - 1) if vip <= 5 else 5
        percent = base + extra
        plan = {
            "vip": vip,
            "min": 12 + (vip - 1) * 10,
            "max": 89 if vip == 1 else 299 + (vip - 2) * 300,
            "percent": 16.0 if vip >= 2 and plan["max"] > 89 else percent
        }
        plans.append(plan)
    return plans

# ---------------- LOCKED FUNDS ---------------- #
def get_locked_assets(email):
    investments = supabase.table("user_investments").select("*").eq("user_email", email).eq("status", "active").execute().data
    if not investments:
        return 0.0
    return round(sum(float(i["amount"]) for i in investments), 2)

def get_locked_investments(email):
    return supabase.table("user_investments").select("*").eq("user_email", email).eq("status", "active").execute().data

# ---------------- EARNINGS ---------------- #
def process_user_earnings(email):
    now = datetime.utcnow()
    res = supabase.table("user_investments").select("*").eq("user_email", email).eq("status", "active").execute()
    if not res.data:
        return

    updates = []
    for inv in res.data:
        last_paid = datetime.fromisoformat(inv["last_paid"])
        if (now - last_paid).days >= 1:
            daily_earning = (float(inv["amount"]) * float(inv["daily_return"])) / 100
            update_wallet_balance(email, daily_earning, "deposit")
            add_transaction(email, "earning", daily_earning)
            updates.append(inv["id"])

    for inv_id in updates:
        supabase.table("user_investments").update({"last_paid": now.isoformat()}).eq("id", inv_id).execute()
