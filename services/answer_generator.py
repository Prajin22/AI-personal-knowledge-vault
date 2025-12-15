"""Answer Generator Service - RAG Implementation

This module avoids importing heavy ML libraries at import time. The
transformers `pipeline` is imported lazily when an answer is requested.
If the model can't be loaded, a lightweight fallback is used so the
server can start quickly without heavy dependencies installed.
"""

from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generates answers using RAG with a local LLM.

    By default this class will not load the model at import/startup. Set
    `load_model=True` to attempt loading immediately (not recommended for
    fast startup). The model is attempted on first call to
    `generate_answer()` if not loaded yet.
    """

    def __init__(self, model_name: str = "google/flan-t5-small", load_model: bool = False):
        self.model_name = model_name
        self.generator = None
        self._load_error: Optional[Exception] = None
        if load_model:
            self._try_load_generator()
    
    def _try_load_generator(self) -> None:
        """Attempt to import transformers.pipeline and load the model.

        Any exception is captured in `self._load_error` and `self.generator`
        remains `None` so callers fall back gracefully. If a load attempt
        already happened, we don't retry repeatedly.
        """
        if getattr(self, "_load_attempted", False):
            return
        self._load_attempted = True

        try:
            from transformers import pipeline

            try:
                self.generator = pipeline(
                    "text2text-generation",
                    model=self.model_name,
                    device=-1,
                )
            except Exception:
                # Try a slightly larger fallback model
                try:
                    self.generator = pipeline(
                        "text2text-generation",
                        model="google/flan-t5-base",
                        device=-1,
                    )
                    self.model_name = "google/flan-t5-base"
                except Exception as e:
                    self._load_error = e
                    self.generator = None
                    logger.warning("AnswerGenerator: failed to load model: %s", e)
        except Exception as e:
            # Import-time failure (e.g., transformers or torch missing)
            self._load_error = e
            self.generator = None
            logger.warning("AnswerGenerator: transformers import failed: %s", e)

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
            # Attempt to load model on-demand; if it fails, fall back.
            self._try_load_generator()
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

