# Updated version of database.py using Supabase PostgreSQL
import psycopg2
from datetime import datetime
import os

def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("SUPABASE_DB_HOST"),
        database=os.environ.get("SUPABASE_DB_NAME", "postgres"),
        user=os.environ.get("SUPABASE_DB_USER"),
        password=os.environ.get("SUPABASE_DB_PASSWORD"),
        port=5432
    )

def add_user(email, hashed_password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO users (email, password, wallet) VALUES (%s, %s, %s)', (email, hashed_password, 0))
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = %s', (email,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_wallet(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT wallet FROM users WHERE email = %s", (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def add_withdraw_request(email, amount, address):
    conn = get_db_connection()
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO withdraw_requests (email, amount, address, status, date) VALUES (%s, %s, %s, %s, %s)",
              (email, amount, address, 'pending', date))
    conn.commit()
    conn.close()

def update_wallet_balance(email, amount, tx_type):
    conn = get_db_connection()
    c = conn.cursor()
    if tx_type == 'deposit':
        c.execute("UPDATE users SET wallet = wallet + %s WHERE email = %s", (amount, email))
    elif tx_type == 'withdraw':
        c.execute("UPDATE users SET wallet = wallet - %s WHERE email = %s", (amount, email))
    conn.commit()
    conn.close()

def add_deposit_request(email, amount, method):
    conn = get_db_connection()
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO deposit_requests (email, amount, method, status, date) VALUES (%s, %s, %s, %s, %s)",
              (email, amount, method, 'pending', date))
    conn.commit()
    conn.close()

def add_transaction(email, tx_type, amount):
    conn = get_db_connection()
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO transactions (email, type, amount, date) VALUES (%s, %s, %s, %s)", 
              (email, tx_type, amount, date))
    conn.commit()
    conn.close()

def get_user_transactions(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT type, amount, date FROM transactions WHERE email = %s ORDER BY date DESC LIMIT 10", (email,))
    results = c.fetchall()
    conn.close()
    return [{"type": row[0], "amount": row[1], "date": row[2]} for row in results]

def save_kyc(email, filepath):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET kyc_file = %s WHERE email = %s', (filepath, email))
    conn.commit()
    conn.close()
