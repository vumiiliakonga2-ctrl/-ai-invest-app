from datetime import datetime
from database import supabase, add_to_wallet  # make sure these are accessible

def process_daily_earnings():
    today = datetime.utcnow()

    # Fetch active investments
    investments = supabase.table("user_investments").select("*").eq("status", "active").execute().data

    for inv in investments:
        unlock_date = datetime.fromisoformat(inv["unlock_date"])
        if unlock_date < today:
            supabase.table("user_investments").update({"status": "expired"}).eq("id", inv["id"]).execute()
            continue

        last_paid = datetime.fromisoformat(inv["last_paid"])
        if (today - last_paid).days >= 1:
            earning = (inv["amount"] * inv["daily_return"]) / 100
            add_to_wallet(inv["user_email"], earning)

            supabase.table("user_investments").update({
                "last_paid": today.isoformat()
            }).eq("id", inv["id"]).execute()

if __name__ == "__main__":
    process_daily_earnings()
