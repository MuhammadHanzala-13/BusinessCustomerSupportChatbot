import streamlit as st
import requests
import time
import sqlite3
from config import DB_NAME  # Assuming config has DB_NAME

API_URL = "http://127.0.0.1:8000/chat"
ORDER_URL = "http://127.0.0.1:8000/order"

st.set_page_config(page_title="AI Business Support Care Bot", page_icon="🤖", layout="wide")

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

# ---- Company Logo ----
# Replace with your actual logo URL or local path, e.g., 'https://your-company.com/logo.png'
st.image("DARK RAS IT Logo 2.png", width=200, use_container_width=False)  # Updated parameter

# ---- Header ----
st.title("RAS InnovaTech Support Bot")
st.subheader("AI-powered Bot with Personalization")

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
    products = [
        {"id": 1, "name": "Wireless Headphones", "price": 4500},
        {"id": 2, "name": "Smartwatch", "price": 7500},
        {"id": 3, "name": "Bluetooth Speaker", "price": 3800},
        {"id": 4, "name": "USB-C Charger", "price": 1200},
        {"id": 5, "name": "Gaming Mouse", "price": 3100},
    ]
    with st.form(key="order_form"):
        item_id = st.selectbox(
            "Select Product",
            options=[p["id"] for p in products],
            format_func=lambda x: f"ID {x}: {next(p['name'] for p in products if p['id'] == x)} - Rs {next(p['price'] for p in products if p['id'] == x)}"
        )
        address = st.text_input("Delivery Address", placeholder="House #, Street, City")
        contact_number = st.text_input("Contact Number", placeholder="+92xxxxxxxxxx")
        submit = st.form_submit_button("Submit Order")
        if submit:
            if not address or not contact_number:
                st.error("Please fill all fields!")
            else:
                payload = {
                    "name": name or "Guest",
                    "address": address,
                    "contact_number": contact_number,
                    "item_id": item_id
                }
                with st.spinner("Placing your order..."):
                    response = requests.post(ORDER_URL, json=payload)
                    if response.status_code == 200:
                        reply = response.json().get("response", "Order placed!")
                        st.session_state.history.append(("bot", reply))
                        st.success("Order placed successfully!")
                        st.session_state.order_mode = False
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Order failed. Try again.")

# ---- Normal Chat Input (Only if NOT in order mode) ----
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
                
                # Call API (append purpose if provided)
                message = f"{user_input} (Purpose: {purpose})" if purpose else user_input
                payload = {"name": name, "email": email, "message": message}
                try:
                    response = requests.post(API_URL, json=payload, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        bot_reply = data.get("response", "No reply")
                        action = data.get("action")
                        # Remove typing + add real reply
                        st.session_state.history[-1] = ("bot", bot_reply)
                        if action == "show_products":
                            st.session_state.order_mode = True
                    else:
                        st.session_state.history[-1] = ("bot", "Server error. Try again.")
                except:
                    st.session_state.history[-1] = ("bot", "No internet or server down. Try later.")
                chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)