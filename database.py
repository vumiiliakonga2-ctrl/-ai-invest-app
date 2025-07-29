import sqlite3
from datetime import datetime
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            wallet REAL DEFAULT 0,
            kyc_file TEXT
        )
    ''')

    # Transactions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL
        )
    ''')

    # Withdraw requests table (new)
    c.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            date TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

def add_user(email, hashed_password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO users (email, password, wallet) VALUES (?, ?, ?)', (email, hashed_password, 0))
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_wallet(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT wallet FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0
def add_withdraw_request(email, amount):
    from datetime import datetime
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO withdraw_requests (email, amount, status, date) VALUES (?, ?, ?, ?)",
              (email, amount, 'pending', date))
    conn.commit()
    conn.close()

def update_wallet_balance(email, amount, tx_type):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    if tx_type == 'deposit':
        c.execute("UPDATE users SET wallet = wallet + ? WHERE email = ?", (amount, email))
    elif tx_type == 'withdraw':
        c.execute("UPDATE users SET wallet = wallet - ? WHERE email = ?", (amount, email))
    conn.commit()
    conn.close()

def add_transaction(email, tx_type, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO transactions (email, type, amount, date) VALUES (?, ?, ?, ?)", 
              (email, tx_type, amount, date))
    conn.commit()
    conn.close()

def get_user_transactions(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT type, amount, date FROM transactions WHERE email = ? ORDER BY date DESC LIMIT 10", (email,))
    results = c.fetchall()
    conn.close()
    return [{"type": row[0], "amount": row[1], "date": row[2]} for row in results]

def save_kyc(email, filepath):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET kyc_file = ? WHERE email = ?', (filepath, email))
    conn.commit()
    conn.close()
