# I made rag.py to Handles website scraping and per user RAG (Retrieval-Augmented Generation) functionality

import re 
import os
import json
import requests
import numpy as np
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from playwright.sync_api import sync_playwright
import faiss
from config import RAG_DIR

def extract_url(message: str) -> str:
    """Detect and extract a URL from the message."""
    url_pattern = r'(https?://[^\s]+)'
    match = re.search(url_pattern, message)
    return match.group(0) if match else None

def scrape_website(url: str) -> str:
    """Scrape the website for text content (headings and paragraphs), handling JS-rendered pages."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Try Playwright for JS-rendered content
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=60000)  # 60s timeout
                page.wait_for_load_state('networkidle')  # Wait for content
                html = page.content()
                browser.close()
            soup = BeautifulSoup(html, 'html.parser')
            # Extract more broadly: headings, paragraphs, divs/spans/lis, and table cells for price lists
            texts = [elem.get_text(strip=True) for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span', 'li', 'td', 'th'])]
            cleaned_text = ' '.join(filter(None, texts))  # Remove empties and join
            if cleaned_text:
                print(f"Scraped content (preview): {cleaned_text[:200]}...")  # Debug log
                return cleaned_text
            else:
                print("Scraped but no meaningful text found.")
                return None
        except Exception as e:
            print(f"Playwright scrape error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                # Fallback to basic requests
                try:
                    response = requests.get(url, headers=headers, timeout=30)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        texts = [elem.get_text(strip=True) for elem in soup.find_all(['h1', 'h2', 'h3', 'p', 'div', 'span', 'td', 'th'])]
                        return ' '.join(filter(None, texts))
                    return None
                except Exception as fallback_e:
                    print("Fallback scrape error:", fallback_e)
                    return None
    return None

def build_rag_for_user(email: str, scraped_text: str) -> bool:
    """Build and save a RAG index for the user based on scraped text."""
    if not scraped_text:
        return False
    # Split into chunks
    chunks = [scraped_text[i:i+500] for i in range(0, len(scraped_text), 500)]
    # Embed
    embedder = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight model
    embeddings = embedder.encode(chunks)
    # FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))
    # Save per user
    user_dir = os.path.join(RAG_DIR, email.replace('@', '_'))  # Safe folder name
    os.makedirs(user_dir, exist_ok=True)
    faiss.write_index(index, os.path.join(user_dir, 'faiss_index'))
    with open(os.path.join(user_dir, 'chunks.json'), 'w') as f:
        json.dump(chunks, f)
    return True

def retrieve_from_rag(email: str, query: str, top_k=3) -> str:
    """Retrieve relevant chunks from the user's RAG index."""
    user_dir = os.path.join(RAG_DIR, email.replace('@', '_'))
    if not os.path.exists(os.path.join(user_dir, 'faiss_index')):
        return None
    # Load index and chunks
    index = faiss.read_index(os.path.join(user_dir, 'faiss_index'))
    with open(os.path.join(user_dir, 'chunks.json'), 'r') as f:
        chunks = json.load(f)
    # Embed query
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    query_emb = embedder.encode([query])
    # Search
    _, indices = index.search(np.array(query_emb), top_k)
    retrieved = [chunks[i] for i in indices[0] if i < len(chunks)]
    return ' '.join(retrieved) if retrieved else None