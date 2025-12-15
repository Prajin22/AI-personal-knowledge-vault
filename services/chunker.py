"""Text Chunking Service"""

import re
from typing import List, Dict

class Chunker:
    """Chunking strategy for document processing."""
    
    def __init__(self, chunk_size: int = 250, overlap: int = 25):
        """Initialize chunker."""
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def _word_count(self, text: str) -> int:
        """Count words in text"""
        words = text.split()
        return len(words)
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences while preserving punctuation."""
        sentences = re.split(r'([.!?]+)\s+', text)
        result = []
        
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
                sentence = sentence.strip()
                if sentence:
                    result.append(sentence)
        
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            result.append(sentences[-1].strip())
        
        return result if result else [text]
    
    def chunk(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Split text into chunks with overlap."""
        if not text or not text.strip():
            return []
        
        # Split into sentences first
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = []
        current_word_count = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_words = self._word_count(sentence)
            
            if current_word_count + sentence_words > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'chunk_index': chunk_index,
                    'word_count': current_word_count,
                    'metadata': metadata or {}
                })
                chunk_index += 1
                
                if self.overlap > 0:
                    overlap_text = ' '.join(current_chunk[-self.overlap:])
                    current_chunk = [overlap_text] if overlap_text else []
                    current_word_count = self._word_count(overlap_text)
                else:
                    current_chunk = []
                    current_word_count = 0
            
            current_chunk.append(sentence)
            current_word_count += sentence_words
        
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'chunk_index': chunk_index,
                'word_count': current_word_count,
                'metadata': metadata or {}
            })
        
        return chunks
    
    def chunk_batch(self, texts: List[str], metadata_list: List[Dict] = None) -> List[List[Dict]]:
        """Chunk multiple texts"""
        if metadata_list is None:
            metadata_list = [None] * len(texts)
        
        return [self.chunk(text, meta) for text, meta in zip(texts, metadata_list)]

