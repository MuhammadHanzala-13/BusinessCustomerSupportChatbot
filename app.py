# app.py
from fastapi import FastAPI
from pydantic import BaseModel
import google.generativeai as genai
import requests, json, sqlite3, os, difflib
from config import GEMINI_API_KEY, HF_API_KEY, KB_FILE, DB_NAME, init_db, save_lead
from rag import extract_url, scrape_website, build_rag_for_user, retrieve_from_rag  # Import RAG helpers

app = FastAPI(title="Customer Support Chatbot with Ordering")
genai.configure(api_key=GEMINI_API_KEY)
init_db()

# --------------------------
# Helper Functions
# --------------------------
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
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")  # Keep as in original
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print("Gemini error:", e)
        return None

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

# --------------------------
# Products & Orders
# --------------------------
PRODUCTS = [
    {"id": 1, "name": "Wireless Headphones", "price": 4500},
    {"id": 2, "name": "Smartwatch", "price": 7500},
    {"id": 3, "name": "Bluetooth Speaker", "price": 3800},
    {"id": 4, "name": "USB-C Charger", "price": 1200},
    {"id": 5, "name": "Gaming Mouse", "price": 3100},
]

ORDERS_FILE = "orders.json"

def save_order(order_details):
    orders = []
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            try: orders = json.load(f)
            except: orders = []
    orders.append(order_details)
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=4)

def is_order_related(query: str) -> bool:
    keywords = ["order", "buy", "purchase", "delivery", "book", "cart", "item", "product", "place order"]
    return any(word in query.lower() for word in keywords)

# --------------------------
# Models
# --------------------------
class ChatRequest(BaseModel):
    name: str
    email: str
    message: str

class OrderRequest(BaseModel):
    name: str
    address: str
    contact_number: str
    item_id: int

# --------------------------
# Endpoints
# --------------------------
@app.post("/chat")
def chat(req: ChatRequest):
    query = req.message.lower()
    email = req.email  # Use for RAG key
    # Check for URL to trigger customization
    url = extract_url(req.message)
    if url:
        scraped = scrape_website(url)
        if scraped and build_rag_for_user(email, scraped):
            response = "I've scraped and customized to your website! Now ask me anything specific to it."
        else:
            response = "Couldn't access or process that website—please try a valid URL."
        action = None
    else:
        # Normal flow, but with RAG if exists
        kb_answer = search_knowledge_base(query)  # Keep for non-custom users
        if kb_answer:
            response = kb_answer
        else:
            response = get_gemini_response(query, email)
            if not response:
                response = get_huggingface_response(query, email)
            if not response:
                response = "I'm having trouble connecting right now, but our team is here to help! Call +92-300-1234567 or email support@yourbusiness.com"
        # Existing order logic...
        action = None
        if is_order_related(query):
            product_list = "\n".join([f"{p['id']}. {p['name']} - Rs {p['price']}" for p in PRODUCTS])
            response = (
                "Here's our product list:\n\n"
                f"{product_list}\n\n"
                "Please reply with the Product ID to place your order!"
            )
            action = "show_products"
    save_lead(req.name, req.email, req.message, response)
    return {"response": response, "action": action}

@app.post("/order")
def place_order(req: OrderRequest):
    product = next((p for p in PRODUCTS if p["id"] == req.item_id), None)
    if not product:
        return {"response": "Invalid product ID. Please try again."}
    
    save_order({
        "customer_name": req.name,
        "address": req.address,
        "contact_number": req.contact_number,
        "item": product["name"],
        "price": product["price"],
        "timestamp": __import__("datetime").datetime.now().isoformat()
    })
    return {"response": f"Order confirmed for {product['name']}! We'll contact you soon on {req.contact_number}."}

@app.get("/")
def root():
    return {"message": "Busniess customer Support Bot is responsing "}