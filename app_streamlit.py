import streamlit as st
import sqlite3
import json
import os
import re
import difflib
import numpy as np
from datetime import datetime
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import requests

# -------------------------------------------------
# CACHED RESOURCES (heavy models) – loaded once
# -------------------------------------------------
st.set_page_config(page_title="AI Business Support Care Bot", layout="wide")
@st.cache_resource(show_spinner=False)
def load_embedder():
    """Load the SentenceTransformer model once and cache it."""
    return SentenceTransformer('all-MiniLM-L6-v2')

# removed load_gemini_model caching as we need to switch models dynamically on failure



# ============================================
# CONFIGURATION
# ============================================

# Show a quick status indicator so the user knows the app has loaded
st.success("✅ Application loaded – ready to chat!")

# Initialise heavy models early (cached) – show spinner so user sees progress
with st.spinner('Initializing AI models...'):
    _ = load_embedder()
    # Gemini model is now loaded on demand with fallback, so no pre-loading needed here
    pass


# Use Streamlit secrets in production, fallback to env vars locally
# Also handle case where secrets.toml exists but has placeholder values
from dotenv import load_dotenv

def get_api_key(key_name):
    """Retrieve API key from st.secrets or .env, handling placeholders."""
    # 0. Load env vars immediately
    load_dotenv()
    
    key = None
    source = "None"
    
    # 1. Try Streamlit Secrets
    try:
        if key_name in st.secrets:
            val = st.secrets[key_name]
            # Valid check: not placeholder, has reasonable length
            if val and "Replace with" not in val and "your_" not in val and len(val) > 20:
                key = val
                source = "st.secrets"
    except:
        pass
        
    # 2. If no valid key from secrets, try .env
    if not key:
        env_val = os.getenv(key_name)
        if env_val and len(env_val) > 20:
            key = env_val
            source = ".env"

        
    return key

GEMINI_API_KEY = get_api_key("GEMINI_API_KEY")
HF_API_KEY = get_api_key("HF_API_KEY")


DB_NAME = "dataBase.db"
KB_FILE = "knowledgeBase.json"
RAG_DIR = "rags"
ORDERS_FILE = "orders.json"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# ============================================
# DATABASE INITIALIZATION
# ============================================

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

def init_rag_dir():
    os.makedirs(RAG_DIR, exist_ok=True)

# Initialize on startup
init_db()
init_rag_dir()

# ============================================
# RAG FUNCTIONS
# ============================================

def extract_url(message: str) -> str:
    """Detect and extract a URL from the message."""
    url_pattern = r'(https?://[^\s]+)'
    match = re.search(url_pattern, message)
    return match.group(0) if match else None

def scrape_with_requests(url: str) -> str:
    """Fallback scraping using requests and BeautifulSoup."""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text(separator=' ')
        return " ".join(text.split())
    except Exception as e:
        print(f"Requests scraping failed: {e}")
        return None

def scrape_website(url: str) -> str:
    """Scrape the website for text content with robust fallback."""
    # 1. Try Playwright
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=30000)
            try:
                page.wait_for_load_state('networkidle', timeout=5000)
            except:
                pass 
            html = page.content()
            browser.close()
            
            soup = BeautifulSoup(html, 'html.parser')
            texts = [elem.get_text(strip=True) for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span', 'li', 'td', 'th'])]
            cleaned_text = ' '.join(filter(None, texts))
            return cleaned_text if cleaned_text else None
    except Exception as e:
        print(f"Playwright failed ({e}). Falling back to requests...")
        
    # 2. Fallback to requests
    return scrape_with_requests(url)

def build_rag_for_user(email: str, scraped_text: str) -> bool:
    """Build and save a RAG index for the user based on scraped text."""
    if not scraped_text:
        return False
    try:
        # Split into chunks
        chunks = [scraped_text[i:i+500] for i in range(0, len(scraped_text), 500)]
        # Embed using cached model
        embedder = load_embedder()
        embeddings = embedder.encode(chunks)
        # FAISS index
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(embeddings))
        # Save per user
        user_dir = os.path.join(RAG_DIR, email.replace('@', '_'))
        os.makedirs(user_dir, exist_ok=True)
        faiss.write_index(index, os.path.join(user_dir, 'faiss_index'))
        with open(os.path.join(user_dir, 'chunks.json'), 'w') as f:
            json.dump(chunks, f)
        return True
    except Exception as e:
        st.error(f"Error building RAG: {e}")
        return False

def retrieve_from_rag(email: str, query: str, top_k=3) -> str:
    """Retrieve relevant chunks from the user's RAG index."""
    user_dir = os.path.join(RAG_DIR, email.replace('@', '_'))
    if not os.path.exists(os.path.join(user_dir, 'faiss_index')):
        return None
    try:
        # Load index and chunks
        index = faiss.read_index(os.path.join(user_dir, 'faiss_index'))
        with open(os.path.join(user_dir, 'chunks.json'), 'r') as f:
            chunks = json.load(f)
        # Embed query
        embedder = load_embedder()
        query_emb = embedder.encode([query])
        # Search
        _, indices = index.search(np.array(query_emb), top_k)
        retrieved = [chunks[i] for i in indices[0] if i < len(chunks)]
        return ' '.join(retrieved) if retrieved else None
    except Exception as e:
        st.error(f"Error retrieving from RAG: {e}")
        return None

# ============================================
# KNOWLEDGE BASE & AI FUNCTIONS
# ============================================

def search_knowledge_base(query):
    try:
        with open(KB_FILE, "r", encoding="utf-8") as f:
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

def get_gemini_response(query, email=None):
    context = retrieve_from_rag(email, query) if email else None
    if context:
        prompt = f"Answer only based on this website context: {context}. Query: {query}. Do not use general knowledge."
    else:
        prompt = query
    
    # List of models to try in order
    GEMINI_MODELS = [
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-pro-latest",
        "gemini-2.0-flash-exp",
    ]
    
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"Gemini model {model_name} failed: {e}")
            continue # Try next model
            
    return None # All attempts failed

def get_huggingface_response(query, email=None):
    context = retrieve_from_rag(email, query) if email else None
    if context:
        prompt = f"Answer only based on this website context: {context}. Query: {query}. Do not use general knowledge."
    else:
        prompt = query
    try:
        url = "https://api-inference.huggingface.co/models/MiniMaxAI/MiniMax-M2"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        payload = {"inputs": prompt}
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()[0]["generated_text"]
    except Exception as e:
        print("HF Error:", e)
    return None

# ============================================
# PRODUCTS & ORDERS
# ============================================

PRODUCTS = [
    {"id": 1, "name": "Wireless Headphones", "price": 4500},
    {"id": 2, "name": "Smartwatch", "price": 7500},
    {"id": 3, "name": "Bluetooth Speaker", "price": 3800},
    {"id": 4, "name": "USB-C Charger", "price": 1200},
    {"id": 5, "name": "Gaming Mouse", "price": 3100},
]

def save_order(order_details):
    orders = []
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            try:
                orders = json.load(f)
            except:
                orders = []
    orders.append(order_details)
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=4)

def is_order_related(query: str) -> bool:
    keywords = ["order", "buy", "purchase", "delivery", "book", "cart", "item", "product", "place order"]
    return any(word in query.lower() for word in keywords)

# ============================================
# CHAT LOGIC
# ============================================

def process_chat(name, email, message):
    """Process chat message and return response."""
    query = message.lower()
    
    # Check for URL to trigger customization
    url = extract_url(message)
    if url:
        with st.spinner("Scraping and analyzing website..."):
            scraped = scrape_website(url)
            if scraped and build_rag_for_user(email, scraped):
                response = "I've scraped and customized to your website! Now ask me anything specific to it."
            else:
                response = "Couldn't access or process that website—please try a valid URL."
        action = None
    else:
        # Normal flow with RAG if exists
        kb_answer = search_knowledge_base(query)
        if kb_answer:
            response = kb_answer
        else:
            response = get_gemini_response(query, email)
            if not response:
                response = get_huggingface_response(query, email)
            if not response:
                response = "I'm having trouble connecting right now, but our team is here to help! Call +92-300-1234567 or email support@yourbusiness.com"
        
        # Check for order intent
        action = None
        if is_order_related(query):
            product_list = "\n".join([f"{p['id']}. {p['name']} - Rs {p['price']}" for p in PRODUCTS])
            response = (
                "Here's our product list:\n\n"
                f"{product_list}\n\n"
                "Please reply with the Product ID to place your order!"
            )
            action = "show_products"
    
    # Save to database
    save_lead(name, email, message, response)
    
    return response, action

# ============================================
# STREAMLIT UI
# ============================================



# Show a quick status indicator so the user knows the app has loaded
st.success("✅ Application loaded – ready to chat!")

# Custom CSS
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #1f2937, #111827);
    color: white;
    font-family: 'Segoe UI', sans-serif;
}
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 15px;
    max-height: 600px;
    overflow-y: auto;
    padding: 15px;
    border: 1px solid #4b5563;
    border-radius: 15px;
    background: rgba(255, 255, 255, 0.05);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}
.chat-bubble-user {
    align-self: flex-end;
    background: linear-gradient(135deg, #145751, #0d3f39);
    color: white;
    padding: 12px 18px;
    border-radius: 20px 20px 0 20px;
    max-width: 65%;
    box-shadow: 0 3px 6px rgba(0,0,0,0.3);
    word-wrap: break-word;
    font-size: 15px;
    animation: fadeIn 0.3s ease-in-out;
}
.chat-bubble-bot {
    align-self: flex-start;
    background: linear-gradient(135deg, #1e3a8a, #172554);
    color: white;
    padding: 12px 18px;
    border-radius: 20px 20px 20px 0;
    max-width: 65%;
    box-shadow: 0 3px 6px rgba(0,0,0,0.3);
    word-wrap: break-word;
    font-size: 15px;
    animation: fadeIn 0.3s ease-in-out;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
.stTextInput>div>div>input {
    border-radius: 25px;
    padding: 12px;
    font-size: 16px;
    background-color: #1f2937;
    color: white;
    border: 1px solid #4b5563;
    transition: border-color 0.3s;
}
.stTextInput>div>div>input:focus {
    border-color: #10b981;
    box-shadow: 0 0 5px rgba(16, 185, 129, 0.5);
}
.stButton>button {
    border-radius: 25px;
    background: linear-gradient(135deg, #145751, #0d3f39);
    color: white;
    transition: transform 0.2s, box-shadow 0.2s;
}
.stButton>button:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 8px rgba(0,0,0,0.4);
}
</style>
""", unsafe_allow_html=True)

# Header
st.title("RAS InnovaTech Support Bot")
st.subheader("AI-powered Bot with Personalization")

# Sidebar for Previous Chat Sessions
with st.sidebar:
    st.header("Previous Chat Sessions")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT DISTINCT email FROM leads ORDER BY timestamp DESC")
    sessions = [row[0] for row in c.fetchall()]
    conn.close()
    
    if sessions:
        selected_session = st.selectbox("Select a Session to View", ["New Session"] + sessions)
        if selected_session != "New Session":
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT user_message, bot_response FROM leads WHERE email = ? ORDER BY timestamp", (selected_session,))
            history = c.fetchall()
            conn.close()
            st.session_state.history = []
            for msg, resp in history:
                st.session_state.history.append(("user", msg))
                st.session_state.history.append(("bot", resp))
            st.session_state.user_email = selected_session
    else:
        st.info("No previous sessions found.")

# User Info
with st.expander("Your Info", expanded=True):
    name = st.text_input("Name", placeholder="Muhammad Hanzala", key="user_name")
    email = st.text_input("Email", placeholder="Email@example.com", key="user_email", value=st.session_state.get("user_email", ""))
    purpose = st.text_input("Purpose for Link (if providing one)", placeholder="eg; Personalize bot for my site", key="purpose")

# Session State
if "history" not in st.session_state:
    st.session_state.history = []
if "order_mode" not in st.session_state:
    st.session_state.order_mode = False
if "link_provided" not in st.session_state:
    st.session_state.link_provided = False

# Chat Display Function
def render_chat():
    chat_html = "<div class='chat-container'>"
    for role, msg in st.session_state.history:
        if role == "user":
            chat_html += f"<div class='chat-bubble-user'>{msg}</div>"
        else:
            chat_html += f"<div class='chat-bubble-bot'>{msg}</div>"
    chat_html += "</div>"
    return chat_html

chat_placeholder = st.empty()
chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)

# Order Form
if st.session_state.order_mode:
    st.subheader("Place Your Order")
    with st.form(key="order_form"):
        item_id = st.selectbox(
            "Select Product",
            options=[p["id"] for p in PRODUCTS],
            format_func=lambda x: f"ID {x}: {next(p['name'] for p in PRODUCTS if p['id'] == x)} - Rs {next(p['price'] for p in PRODUCTS if p['id'] == x)}"
        )
        address = st.text_input("Delivery Address", placeholder="House #, Street, City")
        contact_number = st.text_input("Contact Number", placeholder="+92xxxxxxxxxx")
        submit = st.form_submit_button("Submit Order")
        if submit:
            if not address or not contact_number:
                st.error("Please fill all fields!")
            else:
                product = next((p for p in PRODUCTS if p["id"] == item_id), None)
                save_order({
                    "customer_name": name or "Guest",
                    "address": address,
                    "contact_number": contact_number,
                    "item": product["name"],
                    "price": product["price"],
                    "timestamp": datetime.now().isoformat()
                })
                reply = f"Order confirmed for {product['name']}! We'll contact you soon on {contact_number}."
                st.session_state.history.append(("bot", reply))
                st.success("Order placed successfully!")
                st.session_state.order_mode = False
                st.rerun()

# Normal Chat Input
if not st.session_state.order_mode:
    user_input = st.chat_input("Type your message here...")
    if user_input:
        if not name or not email:
            st.warning("Please enter your name and email first!")
        else:
            proceed = True
            # Check if message contains a URL
            if "http" in user_input and not st.session_state.link_provided:
                if not purpose:
                    st.warning("Please provide the purpose for this link in the 'Your Info' section!")
                    proceed = False
                else:
                    st.session_state.link_provided = True
            
            if proceed:
                # Add user message
                st.session_state.history.append(("user", user_input))
                chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)
                
                # Show typing animation
                st.session_state.history.append(("bot", "Thinking..."))
                chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)
                
                # Process message
                message = f"{user_input} (Purpose: {purpose})" if purpose else user_input
                bot_reply, action = process_chat(name, email, message)
                
                # Update with real reply
                st.session_state.history[-1] = ("bot", bot_reply)
                if action == "show_products":
                    st.session_state.order_mode = True
                
                chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)
                st.rerun()
