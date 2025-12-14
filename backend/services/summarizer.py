"""Summarizer Service"""

from transformers import pipeline
from typing import Optional
import re

class Summarizer:
    """Handles text summarization using NLP models"""
    
    def __init__(self):
        """Initialize the summarization pipeline."""
        try:
            self.summarizer = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=-1
            )
        except Exception:
            try:
                self.summarizer = pipeline(
                    "summarization",
                    model="sshleifer/distilbart-cnn-12-6",
                    device=-1
                )
            except Exception:
                self.summarizer = None
    
    def summarize(
        self,
        text: str,
        max_length: int = 200,
        min_length: int = 50
    ) -> str:
        """Generate a summary of the input text."""
        if not text or len(text.strip()) == 0:
            return ""
        
        if len(text) <= max_length:
            return text.strip()
        
        if self.summarizer:
            try:
                max_input_length = 1024
                if len(text) > max_input_length:
                    text = text[:max_input_length]
                
                summary = self.summarizer(
                    text,
                    max_length=max_length,
                    min_length=min_length,
                    do_sample=False
                )
                return summary[0]['summary_text'].strip()
            except Exception:
                return self._extractive_summarize(text, max_length)
        else:
            return self._extractive_summarize(text, max_length)
    
    def _extractive_summarize(self, text: str, max_length: int) -> str:
        """Simple extractive summarization as fallback."""
        sentences = re.split(r'[.!?]+\s+', text)
        summary = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if current_length + len(sentence) + 1 <= max_length:
                summary.append(sentence)
                current_length += len(sentence) + 1
            else:
                break
        
        result = '. '.join(summary)
        if result and not result.endswith('.'):
            result += '.'
        
        return result if result else text[:max_length] + "..."
    
    def summarize_batch(self, texts: list, max_length: int = 200) -> list:
        """Summarize multiple texts"""
        return [self.summarize(text, max_length) for text in texts]

