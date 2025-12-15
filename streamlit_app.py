import time
import sqlite3
import json
import difflib
import google.generativeai as genai
import streamlit as st
from sentence_transformers import SentenceTransformer
from config import DB_NAME, GEMINI_API_KEY, HF_API_KEY, KB_FILE, RAG_DIR
from rag import scrape_website, build_rag_for_user, retrieve_from_rag
from database import save_lead, save_order

# Configure AI
genai.configure(api_key=GEMINI_API_KEY)

# Products Data (Shared)
PRODUCTS = [
    {"id": 1, "name": "Wireless Headphones", "price": 4500},
    {"id": 2, "name": "Smartwatch", "price": 7500},
    {"id": 3, "name": "Bluetooth Speaker", "price": 3800},
    {"id": 4, "name": "USB-C Charger", "price": 1200},
    {"id": 5, "name": "Gaming Mouse", "price": 3100},
    {"id": 6, "name": "HP laptop elitebook prox", "price": 150000},
]

# Cached Embedder
@st.cache_resource(show_spinner=False)
def load_embedder():
    return SentenceTransformer('all-MiniLM-L6-v2')

# Pre-load to avoid delay on first chat
with st.spinner('Initializing AI...'):
    embedder = load_embedder()

st.set_page_config(page_title="AI Business Support ChatBot", layout="wide")

# ---- Custom CSS for Interactive Design ----
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
.typing {
    width: 60px;
    height: 10px;
    border-radius: 5px;
    background: #f9fafb;
    animation: blink 1s infinite;
    margin-left: 5px;
}
@keyframes blink {
    0%, 100% {opacity: 0.2;}
    50% {opacity: 1;}
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
.chat-container::-webkit-scrollbar { width: 8px; }
.chat-container::-webkit-scrollbar-thumb { background-color: #4b5563; border-radius: 4px; transition: background 0.3s; }
.chat-container::-webkit-scrollbar-thumb:hover { background-color: #6b7280; }
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
.stSelectbox>div>div>select {
    border-radius: 25px;
    background-color: #1f2937;
    color: white;
    border: 1px solid #4b5563;
}
</style>
""", unsafe_allow_html=True)

# ---- Header ----
st.title("Business Support ChatBot")
st.subheader("AI-powered ChatBot with Personalization")

# ---- Sidebar for Previous Chat Sessions ----
with st.sidebar:
    st.header("Previous Chat Sessions")
    # Fetch previous leads from DB (emails as sessions)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT DISTINCT email FROM leads ORDER BY timestamp DESC")
    sessions = [row[0] for row in c.fetchall()]
    conn.close()
    
    if sessions:
        selected_session = st.selectbox("Select a Session to View", ["New Session"] + sessions)
        if selected_session != "New Session":
            # Load chat history for selected email
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT user_message, bot_response FROM leads WHERE email = ? ORDER BY timestamp", (selected_session,))
            history = c.fetchall()
            conn.close()
            st.session_state.history = [("user", msg) if i % 2 == 0 else ("bot", msg) for i, (msg, resp) in enumerate(history)]
            st.session_state.user_email = selected_session  # Switch to this session's email
    else:
        st.info("No previous sessions found.")

# ---- User Info ----
with st.expander("Your Info", expanded=True):
    name = st.text_input("Name", placeholder="Muhammad Hanzala", key="user_name")
    email = st.text_input("Email", placeholder="Email@example.com", key="user_email", value=st.session_state.get("user_email", ""))
    purpose = st.text_input("Purpose for Link (if providing one)", placeholder="eg;  Personalize bot for my site", key="purpose")

# ---- Session State ----
if "history" not in st.session_state:
    st.session_state.history = []
if "order_mode" not in st.session_state:
    st.session_state.order_mode = False
if "link_provided" not in st.session_state:
    st.session_state.link_provided = False

# ---- Logic Functions (Direct execution for Cloud Stability) ----
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
    context = retrieve_from_rag(email, query, embedder=embedder) if email else None
    prompt = f"Answer based on context: {context}. Query: {query}" if context else query
    
    models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-pro-latest", "gemini-2.0-flash-exp"]
    for m in models:
        try:
            model = genai.GenerativeModel(m)
            out = model.generate_content(prompt)
            if out and out.text: return out.text
        except: continue
    return None

def get_huggingface_response(query, email=None):
    # Simplified fallback
    return None

def process_chat(name, email, message):
    query = message.lower()
    
    # 0. Order Intent Check
    keywords = ["order", "buy", "purchase", "delivery", "book", "cart", "item", "product", "place order"]
    if any(word in query for word in keywords):
        product_list = "\n".join([f"{p['id']}. {p['name']} - Rs {p['price']}" for p in PRODUCTS])
        response = (
            "Here's our product list:\n\n"
            f"{product_list}\n\n"
            "Please reply with the Product ID to place your order!"
        )
        # Background save
        save_lead(name, email, message, response)
        return response, "show_products"

    # 1. URL Scraping
    if "http" in message:
        import re
        url = re.search(r'(https?://[^\s]+)', message)
        if url:
            url = url.group(0)
            with st.spinner("Analyzing website..."):
                scraped = scrape_website(url)
                if scraped and build_rag_for_user(email, scraped, embedder=embedder):
                    resp = "Website processed! Ask me questions about it."
                    save_lead(name, email, message, resp)
                    return resp, None
                else:
                    return "Could not process website.", None

    # 2. Knowledge Base
    kb = search_knowledge_base(query)
    if kb: 
        save_lead(name, email, message, kb)
        return kb, None

    # 3. Gemini
    gemini = get_gemini_response(query, email)
    if gemini: 
        save_lead(name, email, message, gemini)
        return gemini, None

    return "I'm having trouble connecting. Please try again later.", None

# ---- Chat Display Function ----
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

# ---- Order Form (Only when order_mode is True) ----
if st.session_state.order_mode:
    st.subheader("Place Your Order")
    # Use globally defined PRODUCTS
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
                with st.spinner("Placing your order..."):
                    # Direct DB Save
                    save_order({
                        "customer_name": name or "Guest",
                        "address": address,
                        "contact_number": contact_number,
                        "item": product["name"],
                        "price": product["price"],
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    reply = f"Order confirmed for {product['name']}! We'll contact you soon on {contact_number}."
                    st.session_state.history.append(("bot", reply))
                    st.success("Order placed successfully!")
                    st.session_state.order_mode = False
                    time.sleep(2)
                    st.rerun()

# --- Normal Chat Input (Only if NOT in order mode) ----
if not st.session_state.order_mode:
    user_input = st.chat_input("Type your message here...")
    if user_input:
        if not name or not email:
            st.warning("Please enter your name and email first!")
        else:
            proceed = True  # Flag to control if we continue processing
            # Check if message contains a URL to trigger purpose prompt
            if "http" in user_input and not st.session_state.link_provided:
                if not purpose:
                    st.warning("Please provide the purpose for this link in the 'Your Info' section!")
                    proceed = False  # Skip the rest
                else:
                    st.session_state.link_provided = True  # Flag to avoid repeated prompts
            
            if proceed:
                # Add user message instantly
                st.session_state.history.append(("user", user_input))
                chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)
                
                # Show typing animation
                st.session_state.history.append(("bot", "Thinking..."))
                chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)
                
                # Call Logic Directly (No API)
                message = f"{user_input} (Purpose: {purpose})" if purpose else user_input
                
                try:
                    bot_reply, action = process_chat(name, email, message)
                    
                    st.session_state.history[-1] = ("bot", bot_reply)
                    if action == "show_products":
                        st.session_state.order_mode = True
                        
                except Exception as e:
                    st.session_state.history[-1] = ("bot", f"Processing error: {str(e)}")
                
                chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)
                # Force rerun to show updated UI state
                if action == "show_products":
                    st.rerun()