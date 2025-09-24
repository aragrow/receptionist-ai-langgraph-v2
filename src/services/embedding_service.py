# ==================== src/services/embedding_service.py ====================
"""Embedding service for text vectorization using Google's text-embedding-004."""

import os
import re
from typing import List, Optional
import google.generativeai as genai
from google.generativeai.types import EmbedContentResponse

from config.settings import settings


class EmbeddingService:
    """Service for text embedding using Google's text-embedding-004 model."""
    
    def __init__(self):
        # Configure Google AI with API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        self.model_name = "models/text-embedding-004"
        
        # Verify model is available
        try:
            # Test with a simple embedding
            test_response = genai.embed_content(
                model=self.model_name,
                content="test"
            )
            self.embedding_dim = len(test_response['embedding'])
            print(f"✅ Google text-embedding-004 initialized (dim: {self.embedding_dim})")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize text-embedding-004: {e}")
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for embedding."""
        if not text or not text.strip():
            return ""
        
        # Convert to string if not already
        text = str(text).strip()
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def chunk_text(self, text: str) -> List[str]:
        """Break text into chunks if it's over the token limit."""
        if not text:
            return [""]
        
        # Google's text-embedding-004 has a context length of ~2048 tokens
        # Rough estimate: 1 token ≈ 4 characters
        max_chars = getattr(settings.embedding, 'max_chars', 8000)  # ~2000 tokens
        chunk_overlap = getattr(settings.embedding, 'chunk_overlap', 200)
        
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + max_chars
            
            # If not the last chunk, try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 200 chars
                search_start = max(start + max_chars - 200, start)
                sentence_end = max(
                    text.rfind('.', search_start, end),
                    text.rfind('!', search_start, end),
                    text.rfind('?', search_start, end)
                )
                
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - chunk_overlap
            if start >= len(text):
                break
        
        return chunks if chunks else [""]
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for text using Google's text-embedding-004."""
        if not text or not text.strip():
            return [0.0] * getattr(self, 'embedding_dim', 768)
        
        processed_text = self.preprocess_text(text)
        
        try:
            response = genai.embed_content(
                model=self.model_name,
                content=processed_text,
                task_type="retrieval_document"  # Optimize for document retrieval
            )
            
            return response['embedding']
            
        except Exception as e:
            print(f"⚠️ Embedding failed for text (len={len(text)}): {e}")
            # Return zero vector if embedding fails
            return [0.0] * getattr(self, 'embedding_dim', 768)
    
    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for multiple texts."""
        embeddings = []
        
        for text in texts:
            embedding = self.create_embedding(text)
            embeddings.append(embedding)
        
        return embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """Create embedding optimized for query/search."""
        if not query or not query.strip():
            return [0.0] * getattr(self, 'embedding_dim', 768)
        
        processed_query = self.preprocess_text(query)
        
        try:
            response = genai.embed_content(
                model=self.model_name,
                content=processed_query,
                task_type="retrieval_query"  # Optimize for query
            )
            
            return response['embedding']
            
        except Exception as e:
            print(f"⚠️ Query embedding failed: {e}")
            return [0.0] * getattr(self, 'embedding_dim', 768)