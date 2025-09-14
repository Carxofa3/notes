import json
import hashlib
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import requests
import re

from app.models.models import Note, Embedding, SearchCache, Settings
from app.database import db

class AIService:
    """Service for AI-related operations including formatting and embeddings"""
    
    @staticmethod
    def get_settings():
        """Get AI settings from database"""
        settings = Settings.query.filter_by(user_id='default').first()
        if not settings:
            return None
        return settings
    
    @staticmethod
    def test_api_connection(base_url: str, api_key: str) -> Dict:
        """Test connection to AI API"""
        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Try to get models list
            response = requests.get(
                f"{base_url.rstrip('/')}/models",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                models = response.json().get('data', [])
                return {
                    'success': True,
                    'models': [model['id'] for model in models if 'gpt' in model['id']],
                    'embedding_models': [model['id'] for model in models if 'embedding' in model['id']]
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection failed: {str(e)}"
            }
    
    @staticmethod
    def format_note_content(note_id: int) -> Dict:
        """Use AI to professionally format note content"""
        settings = AIService.get_settings()
        if not settings or not settings.ai_enabled or not settings.ai_api_key:
            return {'success': False, 'error': 'AI not configured'}
        
        note = Note.query.get(note_id)
        if not note:
            return {'success': False, 'error': 'Note not found'}
        
        try:
            headers = {
                'Authorization': f'Bearer {settings.ai_api_key}',
                'Content-Type': 'application/json'
            }
            
            prompt = f'''Please professionally format the following text in markdown without changing the core meaning. 
Focus on:
- Correcting grammar and spelling errors
- Improving sentence structure and flow
- Adding proper markdown formatting (headings, lists, emphasis)
- Maintaining the original tone and content
- Making it more readable and professional

Original text:
{note.content}

Return only the formatted markdown text, no explanations or additional comments.'''
            
            payload = {
                'model': settings.ai_model,
                'messages': [
                    {'role': 'system', 'content': 'You are a professional editor that improves text formatting and grammar while preserving the original meaning and tone.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 2000,
                'temperature': 0.3
            }
            
            response = requests.post(
                f"{settings.ai_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                formatted_content = result['choices'][0]['message']['content'].strip()
                
                # Save the formatted content
                note.ai_formatted_content = formatted_content
                note.updated_at = datetime.utcnow()
                db.session.commit()
                
                return {
                    'success': True,
                    'formatted_content': formatted_content,
                    'original_content': note.content
                }
            else:
                return {
                    'success': False,
                    'error': f"API Error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Formatting failed: {str(e)}"
            }
    
    @staticmethod
    def generate_embedding(text: str) -> Optional[List[float]]:
        """Generate embedding for text using OpenAI API"""
        settings = AIService.get_settings()
        if not settings or not settings.ai_enabled or not settings.ai_api_key:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {settings.ai_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': settings.ai_embedding_model,
                'input': text
            }
            
            response = requests.post(
                f"{settings.ai_base_url.rstrip('/')}/embeddings",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['data'][0]['embedding']
            else:
                print(f"Embedding API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Embedding generation failed: {str(e)}")
            return None
    
    @staticmethod
    def split_into_phrases(text: str, max_length: int = 500) -> List[Tuple[str, int, int]]:
        """Split text into semantic phrases for embedding"""
        if not text.strip():
            return []
        
        phrases = []
        
        # Split by paragraphs first
        paragraphs = text.split('\\n\\n')
        current_pos = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                current_pos += 2  # Account for \\n\\n
                continue
            
            # If paragraph is short enough, use as-is
            if len(paragraph) <= max_length:
                phrases.append((paragraph, current_pos, current_pos + len(paragraph)))
                current_pos += len(paragraph) + 2  # +2 for \\n\\n
                continue
            
            # Split long paragraphs by sentences
            sentences = re.split(r'(?<=[.!?])\\s+', paragraph)
            phrase_start = current_pos
            current_phrase = ""
            
            for sentence in sentences:
                if len(current_phrase + " " + sentence) <= max_length:
                    if current_phrase:
                        current_phrase += " " + sentence
                    else:
                        current_phrase = sentence
                else:
                    if current_phrase:
                        phrase_end = phrase_start + len(current_phrase)
                        phrases.append((current_phrase, phrase_start, phrase_end))
                        phrase_start = phrase_end + 1
                        current_phrase = sentence
                    else:
                        # Single sentence too long, split by words
                        words = sentence.split()
                        for i in range(0, len(words), 50):  # 50 words at a time
                            word_phrase = " ".join(words[i:i+50])
                            phrase_end = phrase_start + len(word_phrase)
                            phrases.append((word_phrase, phrase_start, phrase_end))
                            phrase_start = phrase_end + 1
            
            if current_phrase:
                phrase_end = current_pos + len(paragraph)
                phrases.append((current_phrase, phrase_start, phrase_end))
            
            current_pos += len(paragraph) + 2
        
        return phrases
    
    @staticmethod
    def embed_note(note_id: int) -> Dict:
        """Generate embeddings for all phrases in a note"""
        note = Note.query.get(note_id)
        if not note:
            return {'success': False, 'error': 'Note not found'}
        
        settings = AIService.get_settings()
        if not settings or not settings.ai_enabled:
            return {'success': False, 'error': 'AI not configured'}
        
        try:
            # Clear existing embeddings for this note
            Embedding.query.filter_by(note_id=note_id).delete()
            
            # Use AI formatted content if available, otherwise use original
            content = note.ai_formatted_content or note.content
            if not content.strip():
                return {'success': True, 'message': 'Note is empty, no embeddings generated'}
            
            # Split content into phrases
            phrases = AIService.split_into_phrases(content)
            
            embeddings_created = 0
            failed_embeddings = 0
            
            # Generate embedding for the entire note
            note_embedding = AIService.generate_embedding(content)
            if note_embedding:
                note.embedding_vector = note_embedding
                note.embedding_model = settings.ai_embedding_model
                note.last_embedded_at = datetime.utcnow()
            
            # Generate embeddings for each phrase
            for phrase_text, start, end in phrases:
                if not phrase_text.strip():
                    continue
                
                embedding_vector = AIService.generate_embedding(phrase_text)
                if embedding_vector:
                    embedding = Embedding(
                        note_id=note_id,
                        phrase_text=phrase_text,
                        phrase_start=start,
                        phrase_end=end,
                        embedding_vector=embedding_vector,
                        embedding_model=settings.ai_embedding_model
                    )
                    db.session.add(embedding)
                    embeddings_created += 1
                else:
                    failed_embeddings += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'embeddings_created': embeddings_created,
                'failed_embeddings': failed_embeddings,
                'phrases_processed': len(phrases)
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f"Embedding failed: {str(e)}"
            }
    
    @staticmethod
    def cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            a = np.array(a)
            b = np.array(b)
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        except:
            return 0.0
    
    @staticmethod
    def search_notes(query: str, limit: int = 10) -> Dict:
        """Search notes using semantic similarity"""
        settings = AIService.get_settings()
        if not settings or not settings.search_enabled:
            return {'success': False, 'error': 'Search not enabled'}
        
        if not query.strip():
            return {'success': True, 'results': []}
        
        # Check cache first
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()
        cached_result = SearchCache.query.filter_by(query_hash=query_hash).first()
        
        if cached_result and cached_result.expires_at > datetime.utcnow():
            return {
                'success': True,
                'results': cached_result.results,
                'cached': True
            }
        
        try:
            # Generate embedding for the search query
            query_embedding = AIService.generate_embedding(query)
            if not query_embedding:
                # Fallback to text search
                return AIService._fallback_text_search(query, limit)
            
            results = []
            
            # Search note-level embeddings
            notes_with_embeddings = Note.query.filter(Note.embedding_vector.isnot(None)).all()
            
            for note in notes_with_embeddings:
                if note.embedding_vector:
                    similarity = AIService.cosine_similarity(query_embedding, note.embedding_vector)
                    if similarity > 0.1:  # Minimum threshold
                        results.append({
                            'type': 'note',
                            'id': note.id,
                            'title': note.title,
                            'content': note.content[:200] + "..." if len(note.content) > 200 else note.content,
                            'lesson_id': note.lesson_id,
                            'unit_id': note.unit_id,
                            'similarity': similarity,
                            'highlight': note.content[:300]  # First 300 chars for preview
                        })
            
            # Search phrase-level embeddings
            embeddings = Embedding.query.all()
            
            for embedding in embeddings:
                if embedding.embedding_vector:
                    similarity = AIService.cosine_similarity(query_embedding, embedding.embedding_vector)
                    if similarity > 0.2:  # Higher threshold for phrases
                        # Check if we already have this note in results
                        existing = next((r for r in results if r['type'] == 'note' and r['id'] == embedding.note_id), None)
                        if existing:
                            # Update with better similarity if this phrase is more relevant
                            if similarity > existing['similarity']:
                                existing['similarity'] = similarity
                                existing['highlight'] = embedding.phrase_text
                        else:
                            note = embedding.note
                            results.append({
                                'type': 'phrase',
                                'id': note.id,
                                'title': note.title,
                                'content': note.content[:200] + "..." if len(note.content) > 200 else note.content,
                                'lesson_id': note.lesson_id,
                                'unit_id': note.unit_id,
                                'similarity': similarity,
                                'highlight': embedding.phrase_text,
                                'phrase_start': embedding.phrase_start,
                                'phrase_end': embedding.phrase_end
                            })
            
            # Sort by similarity and limit results
            results.sort(key=lambda x: x['similarity'], reverse=True)
            results = results[:limit]
            
            # Cache the results
            cache_entry = SearchCache(
                query_text=query,
                query_hash=query_hash,
                results=results,
                embedding_vector=query_embedding,
                expires_at=datetime.utcnow() + timedelta(hours=1)  # Cache for 1 hour
            )
            
            # Clean up old cache entries
            SearchCache.query.filter(SearchCache.expires_at < datetime.utcnow()).delete()
            
            db.session.add(cache_entry)
            db.session.commit()
            
            return {
                'success': True,
                'results': results,
                'cached': False,
                'query_embedding_generated': True
            }
            
        except Exception as e:
            print(f"Search failed: {str(e)}")
            # Fallback to text search
            return AIService._fallback_text_search(query, limit)
    
    @staticmethod
    def _fallback_text_search(query: str, limit: int) -> Dict:
        """Fallback text-based search when embeddings are not available"""
        try:
            search_terms = query.lower().split()
            notes = Note.query.all()
            
            results = []
            for note in notes:
                content_lower = note.content.lower()
                title_lower = note.title.lower()
                
                # Simple scoring based on term matches
                score = 0
                highlight = ""
                
                for term in search_terms:
                    title_matches = title_lower.count(term) * 3  # Title matches worth more
                    content_matches = content_lower.count(term)
                    score += title_matches + content_matches
                    
                    # Find first occurrence for highlighting
                    if not highlight and term in content_lower:
                        start_idx = content_lower.find(term)
                        start = max(0, start_idx - 50)
                        end = min(len(note.content), start_idx + 150)
                        highlight = note.content[start:end]
                
                if score > 0:
                    results.append({
                        'type': 'text_match',
                        'id': note.id,
                        'title': note.title,
                        'content': note.content[:200] + "..." if len(note.content) > 200 else note.content,
                        'lesson_id': note.lesson_id,
                        'unit_id': note.unit_id,
                        'similarity': score / 100.0,  # Normalize score
                        'highlight': highlight or note.content[:150]
                    })
            
            results.sort(key=lambda x: x['similarity'], reverse=True)
            results = results[:limit]
            
            return {
                'success': True,
                'results': results,
                'fallback_search': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Text search failed: {str(e)}"
            }
    
    @staticmethod
    def batch_embed_all_notes() -> Dict:
        """Generate embeddings for all notes that don't have them"""
        settings = AIService.get_settings()
        if not settings or not settings.ai_enabled:
            return {'success': False, 'error': 'AI not configured'}
        
        notes_without_embeddings = Note.query.filter(
            Note.embedding_vector.is_(None)
        ).all()
        
        total_notes = len(notes_without_embeddings)
        processed = 0
        failed = 0
        
        for note in notes_without_embeddings:
            result = AIService.embed_note(note.id)
            if result['success']:
                processed += 1
            else:
                failed += 1
        
        return {
            'success': True,
            'total_notes': total_notes,
            'processed': processed,
            'failed': failed
        }
