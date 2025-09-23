# ==================== src/utilities/text_processing.py ====================
"""Text processing utilities."""

import re
import html
from typing import List


class TextProcessor:
    """Utility class for text processing operations."""
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input text."""
        if not text:
            return ""
        
        # Remove potentially harmful characters
        text = re.sub(r'[<>\"\'%;()&+]', '', text)
        
        # Limit length
        text = text[:1000]
        
        return text.strip()
    
    @staticmethod
    def escape_output(text: str) -> str:
        """Escape text for safe output."""
        return html.escape(text) if text else ""
    
    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """Extract keywords from text."""
        if not text:
            return []
        
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Remove common words
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
        
        keywords = [word for word in words if word not in stop_words]
        
        return list(set(keywords))[:10]  # Return unique keywords, max 10