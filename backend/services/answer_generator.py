"""Answer Generator Service - RAG Implementation"""

from transformers import pipeline
from typing import List, Optional

class AnswerGenerator:
    """Generates answers using RAG with local LLM."""
    
    def __init__(self, model_name: str = "google/flan-t5-small"):
        """Initialize the answer generator with a local LLM."""
        try:
            self.generator = pipeline(
                "text2text-generation",
                model=model_name,
                device=-1
            )
            self.model_name = model_name
        except Exception:
            try:
                self.generator = pipeline(
                    "text2text-generation",
                    model="google/flan-t5-base",
                    device=-1
                )
                self.model_name = "google/flan-t5-base"
            except Exception:
                self.generator = None
                self.model_name = None
    
    def _construct_prompt(self, query: str, context_chunks: List[str]) -> str:
        """Construct RAG prompt with context and question."""
        context = "\n\n".join([f"- {chunk}" for chunk in context_chunks])
        
        prompt = f"""You are an AI assistant answering questions using the user's personal knowledge base.

Context:
{context}

Question:
{query}

Answer in a clear, concise, and personalized manner using only the given context."""
        
        return prompt
    
    def generate_answer(
        self,
        query: str,
        context_chunks: List[str],
        max_length: int = 200
    ) -> str:
        """Generate answer using RAG pipeline."""
        if not context_chunks:
            return "I don't have enough information to answer this question based on your knowledge base."
        
        if not self.generator:
            return self._simple_answer_fallback(query, context_chunks)
        
        try:
            prompt = self._construct_prompt(query, context_chunks)
            result = self.generator(
                prompt,
                max_length=max_length,
                min_length=50,
                do_sample=False,
                temperature=0.7
            )
            answer = result[0]['generated_text'].strip()
            return answer if answer else self._simple_answer_fallback(query, context_chunks)
        except Exception:
            return self._simple_answer_fallback(query, context_chunks)
    
    def _simple_answer_fallback(self, query: str, context_chunks: List[str]) -> str:
        """Simple fallback when LLM is not available."""
        if not context_chunks:
            return "I couldn't find relevant information to answer your question."
        
        best_chunk = context_chunks[0][:500]
        return f"Based on your notes: {best_chunk}..."

