import streamlit as st
import requests
import time

API_URL = "http://127.0.0.1:8000/chat"
ORDER_URL = "http://127.0.0.1:8000/order"

st.set_page_config(page_title="AI Business Support Care Bot", page_icon="Robot", layout="wide")

# ---- Custom CSS ----
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
    gap: 10px;
    max-height: 600px;
    overflow-y: auto;
    padding: 10px;
}
.chat-bubble-user {
    align-self: flex-end;
    background: #145751;
    color: white;
    padding: 12px 18px;
    border-radius: 20px 20px 0 20px;
    max-width: 65%;
    box-shadow: 0 3px 6px rgba(0,0,0,0.3);
    word-wrap: break-word;
    font-size: 15px;
}
.chat-bubble-bot {
    align-self: flex-start;
    background: #145751;
    color: white;
    padding: 12px 18px;
    border-radius: 20px 20px 20px 0;
    max-width: 65%;
    box-shadow: 0 3px 6px rgba(0,0,0,0.3);
    word-wrap: break-word;
    font-size: 15px;
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
}
.chat-container::-webkit-scrollbar { width: 8px; }
.chat-container::-webkit-scrollbar-thumb { background-color: #4b5563; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ---- Header ----
st.title("AI Business Support Care Bot")
st.subheader("AI-powered Bot")

# ---- User Info ----
with st.expander("Your Info", expanded=True):
    name = st.text_input("Name", placeholder="John Doe", key="user_name")
    email = st.text_input("Email", placeholder="johndoe@example.com", key="user_email")

# ---- Session State ----
if "history" not in st.session_state:
    st.session_state.history = []
if "order_mode" not in st.session_state:
    st.session_state.order_mode = False

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
    
    # Product list (same as backend)
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
        contact_number = st.text_input("Contact Number", placeholder="+923001234567")
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
            # Add user message instantly
            st.session_state.history.append(("user", user_input))
            chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)

            # Show typing
            st.session_state.history.append(("bot", "Thniking..."))
            chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)

            # Call API
            payload = {"name": name, "email": email, "message": user_input}
            try:
                response = requests.post(API_URL, json=payload, timeout=20)
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