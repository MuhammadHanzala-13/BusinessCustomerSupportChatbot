import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/chat"

st.set_page_config(page_title="💬 AI Business Support Care Bot", page_icon="🤖", layout="wide")

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
st.title("💼 AI Business Support Care Bot")
st.subheader("AI-powered Bot 🤖")

# ---- User Info ----
with st.expander("👤 Your Info", expanded=True):
    name = st.text_input("Name", placeholder="John Doe")
    email = st.text_input("Email", placeholder="johndoe@example.com")

# ---- Session history ----
if "history" not in st.session_state:
    st.session_state.history = []

# ---- Chat display function ----
def render_chat():
    chat_html = "<div class='chat-container'>"
    for role, msg in st.session_state.history:
        if role == "user":
            chat_html += f"<div class='chat-bubble-user'>{msg}</div>"
        else:
            chat_html += f"<div class='chat-bubble-bot'>{msg}</div>"
    chat_html += "</div>"
    return chat_html

# Placeholder for chat
chat_placeholder = st.empty()
chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)

# ---- Chat input ----
user_input = st.chat_input("Type your message...")

if user_input:
    if not name or not email:
        st.warning("Please enter your name and email first.")
    else:
        # Add user message
        st.session_state.history.append(("user", user_input))
        # Add typing indicator
        st.session_state.history.append(("bot", "<div class='typing'></div>"))
        chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)

        # Call backend
        response = requests.post(API_URL, json={"name": name, "email": email, "message": user_input})
        bot_reply = response.json().get("response", "Error: Backend unreachable") if response.status_code == 200 else "Error: Backend unreachable"

        # Replace typing with actual reply
        st.session_state.history[-1] = ("bot", bot_reply)
        chat_placeholder.markdown(render_chat(), unsafe_allow_html=True)
