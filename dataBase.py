#dataBase.py
import sqlite3
from config import DB_NAME

def init_db():
    """Create leads table with correct columns."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            user_message TEXT,
            bot_response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_lead(name, email, user_message, bot_response):
    """Insert a new customer lead into the DB."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO leads (name, email, user_message, bot_response) VALUES (?, ?, ?, ?)",
        (name, email, user_message, bot_response)
    )
    conn.commit()
    conn.close()
