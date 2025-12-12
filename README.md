# Business Customer Support Chatbot

## Overview
This project is an AI-powered customer support chatbot designed to assist businesses in automating customer interactions. It features a personalized experience where users can input a website URL to train the bot on specific content using Retrieval-Augmented Generation (RAG). The system also includes an integrated ordering system, allowing users to browse products and place orders directly within the chat interface.

## Features
- **AI-Powered Chat:** Utilizes Google Gemini for intelligent responses, with a fallback to Hugging Face models and a local knowledge base.
- **Custom Knowledge Base (RAG):** Users can provide a website URL, which the bot scrapes to build a custom knowledge base for answering specific queries.
- **Order Management:** Built-in functionality to view products and place orders.
- **Session History:** Users can view and revisit previous chat sessions.
- **Robust Backend:** Powered by FastAPI for handling chat requests and order processing.
- **Interactive Frontend:** A user-friendly interface built with Streamlit.

## Technology Stack
- **Frontend:** Streamlit
- **Backend:** FastAPI
- **AI Models:** Google Gemini, Hugging Face (MiniMax-M2)
- **Vector Search:** FAISS, Sentence Transformers
- **Database:** SQLite
- **Web Scraping:** Playwright, BeautifulSoup

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd CustomerSupportChatBot
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright browsers:
   ```bash
   playwright install
   ```

4. Configure Environment Variables:
   Create a `.env` file in the root directory and add your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   HF_API_KEY=your_huggingface_api_key
   ```

## Usage

### Option 1: Merged Streamlit App (Recommended for Deployment)

Run the single-file Streamlit app that includes all backend functionality:

```bash
streamlit run app_streamlit.py
```

Access the application in your browser (usually at `http://localhost:8501`).

### Option 2: Two-Server Architecture (Original)

1. Start the Backend Server:
   ```bash
   uvicorn app:app --reload
   ```

2. Start the Streamlit Application:
   ```bash
   streamlit run streamlit_app.py
   ```

3. Access the application in your browser (usually at `http://localhost:8501`).

## Deployment to Streamlit Cloud

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

Quick steps:
1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Set main file to `app_streamlit.py`
5. Add your API keys in Secrets (TOML format)
6. Deploy!

## Project Structure
- `app.py`: The FastAPI backend handling API requests.
- `streamlit_app.py`: The Streamlit frontend interface (two-server architecture).
- `app_streamlit.py`: **NEW** - Merged single-file Streamlit app (recommended for deployment).
- `rag.py`: Handles website scraping and RAG implementation.
- `backend.py`: Helper functions for backend logic.
- `dataBase.py`: Database initialization and management.
- `config.py`: Configuration and environment variables.
- `requirements.txt`: List of Python dependencies.
- `packages.txt`: System-level dependencies for Streamlit Cloud.
- `.streamlit/config.toml`: Streamlit configuration.
- `DEPLOYMENT.md`: Detailed deployment guide.

## Developed By
**~Muhammad Hanzala**
