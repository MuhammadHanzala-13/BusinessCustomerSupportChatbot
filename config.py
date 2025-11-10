import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")
DB_NAME = "dataBase.db"
KB_FILE = "knowledgeBase.json"

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