# Quick Start Guide - Customer Support Chatbot

## For Streamlit Cloud Deployment

### Step 1: Update .gitignore
Make sure `.env` is in your `.gitignore` (it already is).

### Step 2: Commit and Push to GitHub

```bash
git add .
git commit -m "Add Streamlit Cloud deployment files"
git push origin main
```

### Step 3: Deploy on Streamlit Cloud

1. Visit: https://share.streamlit.io
2. Click "New app"
3. Select your repository: `MuhammadHanzala-13/BusinessCustomerSupportChatbot`
4. Main file path: `app_streamlit.py`
5. Click "Advanced settings"

### Step 4: Add Secrets

In the Secrets section, paste this (with your actual keys):

```toml
GEMINI_API_KEY = "your_actual_gemini_api_key_here"
HF_API_KEY = "your_actual_huggingface_api_key_here"
```

### Step 5: Deploy!

Click "Deploy" and wait 2-3 minutes for your app to build.

---

## For Local Testing

### Quick Test (Merged App)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the merged app
streamlit run app_streamlit.py
```

### Full Test (Original Two-Server)

```bash
# Terminal 1 - Backend
uvicorn app:app --reload

# Terminal 2 - Frontend
streamlit run streamlit_app.py
```

---

## Getting Your API Keys

### Gemini API Key
1. Go to: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key

### Hugging Face API Key (Optional)
1. Go to: https://huggingface.co/settings/tokens
2. Click "New token"
3. Copy the token

---

## Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt
```

### Playwright issues
```bash
playwright install chromium
```

### Database errors
Delete `dataBase.db` and restart the app.

### API errors
- Check your API keys in `.env` (local) or Secrets (cloud)
- Verify API quotas haven't been exceeded

---

## What's Different in the Merged App?

The `app_streamlit.py` file combines:
- ✅ All FastAPI backend logic
- ✅ RAG functionality
- ✅ Database operations
- ✅ AI model calls
- ✅ Streamlit UI

**Benefits:**
- Single file deployment
- No need for separate backend server
- Perfect for Streamlit Cloud
- Easier to maintain

**Original Setup (`app.py` + `streamlit_app.py`):**
- Still works perfectly
- Better for local development
- Allows separate scaling
- More modular

Choose based on your needs!
