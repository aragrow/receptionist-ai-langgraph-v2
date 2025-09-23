# ==================== src/services/embedding_service.py ====================
"""Embedding service for text vectorization."""

import re
import nltk
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from config.settings import settings


# Download required NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)


class EmbeddingService:
    """Service for text embedding and vectorization."""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english'
        )
        self.stop_words = set(stopwords.words('english'))
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for embedding."""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        
        # Tokenize and remove stop words
        tokens = word_tokenize(text)
        tokens = [token for token in tokens if token not in self.stop_words]
        
        return ' '.join(tokens)
    
    def chunk_text(self, text: str) -> List[str]:
        """Break text into chunks if it's over the token limit."""
        words = text.split()
        
        if len(words) <= settings.embedding.chunk_size:
            return [text]
        
        chunks = []
        for i in range(0, len(words), settings.embedding.chunk_size - settings.embedding.chunk_overlap):
            chunk_words = words[i:i + settings.embedding.chunk_size]
            chunks.append(' '.join(chunk_words))
            
            # Break if we've covered all words
            if i + settings.embedding.chunk_size >= len(words):
                break
        
        return chunks
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for text."""
        processed_text = self.preprocess_text(text)
        
        # Simple TF-IDF based embedding
        # In production, use proper embedding models
        try:
            embedding = self.vectorizer.fit_transform([processed_text])
            return embedding.toarray()[0].tolist()
        except Exception:
            # Return zero vector if embedding fails
            return [0.0] * 500