#backend.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Create FastAPI app
app = FastAPI(title="Gemini + MiniMax Chatbot API")

# Chat request model
class ChatRequest(BaseModel):
    prompt: str

# Initialize Gemini Model
gemini_model = genai.GenerativeModel("models/gemini-2.5-flash")

@app.post("/chat/")
async def chat(request: ChatRequest):
    prompt = request.prompt

    try:
        # 🔹 Try Gemini first
        response = gemini_model.generate_content(prompt)
        reply = response.text
        return {"model": "Gemini 2.5 Flash", "reply": reply}

    except Exception as e:
        print("Gemini error:", e)

        # 🔹 Fallback: MiniMax Hugging Face model
        try:
            url = "https://api-inference.huggingface.co/models/MiniMaxAI/MiniMax-M2"
            headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
            data = {"inputs": prompt}
            hf_response = requests.post(url, headers=headers, json=data)

            if hf_response.status_code == 200:
                reply = hf_response.json()[0]["generated_text"]
                return {"model": "MiniMax-M2", "reply": reply}
            else:
                raise HTTPException(status_code=500, detail="Hugging Face API failed")

        except Exception as e2:
            print("MiniMax fallback error:", e2)
            raise HTTPException(status_code=500, detail="Both models failed")

@app.get("/")
def home():
    return {"message": "Welcome to the Hybrid Chatbot (Gemini + MiniMax)!"}
