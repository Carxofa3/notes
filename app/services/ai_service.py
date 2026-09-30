import requests
from flask import current_app
import numpy as np
from app.models.models import Embedding

def format_text(text):
    api_key = current_app.config.get('LLM_API_KEY')
    api_base = current_app.config.get('LLM_API_BASE')
    model = current_app.config.get('LLM_MODEL', 'gpt-3.5-turbo')

    if not api_key:
        return None

    if not api_base:
        # Default to OpenAI's API if no base is provided
        api_base = "https://api.openai.com/v1"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"Please reformat the following text for clarity and correctness, while preserving the original meaning. Fix any grammar or spelling mistakes. Use markdown for formatting like headers, lists, and bold text where appropriate:\n\n{text}"

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        response = requests.post(f"{api_base}/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        # Handle exceptions (e.g., network errors, API errors)
        print(f"Error calling AI API: {e}")
        return None

def embed_text(text):
    api_key = current_app.config.get('EMBEDDINGS_API_KEY')
    api_base = current_app.config.get('EMBEDDINGS_API_BASE')
    model = current_app.config.get('EMBEDDINGS_MODEL', 'text-embedding-ada-002')

    if not api_key:
        return None

    if not api_base:
        api_base = "https://api.openai.com/v1"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "input": text,
    }

    try:
        response = requests.post(f"{api_base}/embeddings", headers=headers, json=data)
        response.raise_for_status()
        # The embedding is in response.json()['data'][0]['embedding']
        return response.json()['data'][0]['embedding']
    except requests.exceptions.RequestException as e:
        print(f"Error calling AI API for embedding: {e}")
        return None

def search_notes_by_query(query):
    query_embedding = embed_text(query)
    if not query_embedding:
        return []

    query_vector = np.array(query_embedding)
    all_embeddings = Embedding.query.all()
    
    results = []
    for emb in all_embeddings:
        if emb.vector is None:
            continue
        emb_vector = np.array(emb.vector)
        # Cosine similarity calculation
        similarity = np.dot(emb_vector, query_vector) / (np.linalg.norm(emb_vector) * np.linalg.norm(query_vector))
        results.append({'note_id': emb.note_id, 'similarity': float(similarity), 'phrase': emb.phrase})

    # Sort results by similarity, descending
    results.sort(key=lambda x: x['similarity'], reverse=True)

    # A more advanced version would also filter by a similarity threshold.
    return results[:10] # Return top 10 results
