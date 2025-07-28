import sqlite3

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            wallet TEXT,
            kyc_file TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_user(email, hashed_password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO users (email, password) VALUES (?, ?, ?)', (email, hashed_password))
    conn.commit()
    conn.close()

def get_user_by_email(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    conn.close()
    return user

def save_kyc(email, filepath):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET kyc_file = ? WHERE email = ?', (filepath, email))
    conn.commit()
    conn.close()
