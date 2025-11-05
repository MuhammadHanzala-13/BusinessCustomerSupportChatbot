#app.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
import google.generativeai as genai
import requests, json, sqlite3
from config import GEMINI_API_KEY, HF_API_KEY, KB_FILE, DB_NAME

app = FastAPI(title="Customer Support Chatbot")

genai.configure(api_key=GEMINI_API_KEY)

# --------------------------
# Database Setup
# --------------------------
def create_db():
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

create_db()

# --------------------------
# Helper Functions
# --------------------------
import difflib

def search_knowledge_base(query):
    try:
        with open(KB_FILE, "r") as f:
            kb = json.load(f)
        questions = [item["question"] for item in kb]
        match = difflib.get_close_matches(query, questions, n=1, cutoff=0.6)
        if match:
            for item in kb:
                if item["question"] == match[0]:
                    return item["answer"]
    except Exception as e:
        print("KB Error:", e)
    return None


def get_gemini_response(query):
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")  # Free working model
        response = model.generate_content(query)
        return response.text
    except Exception as e:
        print("Gemini error:", e)
        return None


def get_huggingface_response(query):
    url = "https://api-inference.huggingface.co/models/MiniMaxAI/MiniMax-M2"  # Free model
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": query}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            return response.json()[0]["generated_text"]
    except Exception as e:
        print("HF Error:", e)
    return None


def log_lead(name, email, message, response):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO leads (name, email, user_message, bot_response) VALUES (?, ?, ?, ?)",
        (name, email, message, response),
    )
    conn.commit()
    conn.close()


# --------------------------
# Chat Endpoint
# --------------------------
class ChatRequest(BaseModel):
    name: str
    email: str
    message: str


@app.post("/chat")
def chat(req: ChatRequest):
    query = req.message
    kb_answer = search_knowledge_base(query)
    if kb_answer:
        response = kb_answer
    else:
        response = get_huggingface_response(query) or get_gemini_response(query) or "Sorry, I couldn't understand that."

    log_lead(req.name, req.email, req.message, response)
    return {"response": response}


@app.get("/")
def root():
    return {"message": "Chatbot backend running ✅"}
