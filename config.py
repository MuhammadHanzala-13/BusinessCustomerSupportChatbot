import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")
DB_NAME = "dataBase.db"
KB_FILE = "knowledgeBase.json"
RAG_DIR = "rags"  # New: Folder for per-user RAG stores
ORDERS_FILE = "orders.json"

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
# ... existing code ...

def init_rag_dir():
    os.makedirs(RAG_DIR, exist_ok=True)

# Call this in init_db() or at app start
init_db()
init_rag_dir()  # Add this line after init_db()