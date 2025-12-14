"""Text Preprocessing Service"""

import re
from typing import List

class Preprocessor:
    """Minimal text preprocessing for BERT-based embeddings."""
    
    @staticmethod
    def preprocess(text: str) -> str:
        """Apply minimal preprocessing to text."""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace (multiple spaces, tabs, newlines)
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def preprocess_batch(texts: list) -> list:
        """Preprocess multiple texts"""
        return [Preprocessor.preprocess(text) for text in texts]

