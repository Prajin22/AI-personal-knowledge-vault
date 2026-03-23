"""Answer Generator Service - RAG Implementation

This module avoids importing heavy ML libraries at import time. The
transformers `pipeline` is imported lazily when an answer is requested.
If the model can't be loaded, a lightweight fallback is used so the
server can start quickly without heavy dependencies installed.
"""

from typing import List, Optional, Dict
import logging
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Generates answers using RAG with a local LLM.

    By default this class will not load the model at import/startup. Set
    `load_model=True` to attempt loading immediately (not recommended for
    fast startup). The model is attempted on first call to
    `generate_answer()` if not loaded yet.
    """

    def __init__(self, model_name: str = "facebook/blenderbot-400M-distill", load_model: bool = False):
        self.model_name = model_name
        self.generator = None
        self._load_error: Optional[Exception] = None
        self._cache: Dict[str, str] = {}  # Simple cache for responses
        self._max_cache_size = 100  # Limit cache size
        if load_model:
            self._try_load_generator()

    def _get_fine_tuned_model_dir(self) -> Optional[str]:
        # First check the new AI education model location
        ai_education_dir = Path(__file__).parent.parent / "models" / "ai_education_model"
        if (ai_education_dir / "config.json").exists():
            return str(ai_education_dir)

        # Fallback to the old location
        model_dir = Path(__file__).parent.parent / "data" / "fine_tuned_models" / "answer_generator"
        if (model_dir / "config.json").exists():
            return str(model_dir)
        return None

    def reload(self) -> None:
        self.generator = None
        self._load_error = None
        self._load_attempted = False
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
                fine_tuned_dir = self._get_fine_tuned_model_dir()
                model_to_load = fine_tuned_dir if fine_tuned_dir else self.model_name
                self.generator = pipeline(
                    "conversational",
                    model=model_to_load,
                    device=-1,
                )
                if fine_tuned_dir:
                    self.model_name = fine_tuned_dir
            except Exception:
                # Try DialoGPT-large as fallback
                try:
                    self.generator = pipeline(
                        "text-generation",
                        model="microsoft/DialoGPT-large",
                        device=-1,
                        pad_token_id=50256,
                    )
                    self.model_name = "microsoft/DialoGPT-large"
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
        """Construct conversational prompt with context for BlenderBot."""
        # Limit context to most relevant chunks
        relevant_context = []
        total_length = 0
        max_context_length = 600  # BlenderBot works better with shorter context

        for chunk in context_chunks:
            if total_length + len(chunk) > max_context_length:
                break
            relevant_context.append(chunk)
            total_length += len(chunk)

        if relevant_context:
            context = " ".join(relevant_context)
            # Format context as part of the conversation
            prompt = f"I have this information from my knowledge base: {context}. Based on this, {query}"
        else:
            prompt = query

        return prompt
    
    def generate_answer(
        self,
        query: str,
        context_chunks: List[str],
        max_length: int = 200
    ) -> str:
        """Generate answer using RAG pipeline with relevance checking."""
        if not context_chunks:
            return "I don't have enough information to answer this question based on your knowledge base."

        # Create cache key from query and context
        cache_key = self._create_cache_key(query, context_chunks)
        
        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Check if context is actually relevant to the query
        if not self._is_context_relevant(query, context_chunks):
            answer = "I don't have specific information about this topic in your knowledge base. Please add relevant notes or documents first."
            self._add_to_cache(cache_key, answer)
            return answer
        
        if not self.generator:
            # Attempt to load model on-demand; if it fails, fall back.
            self._try_load_generator()
            if not self.generator:
                answer = self._simple_answer_fallback(query, context_chunks)
                self._add_to_cache(cache_key, answer)
                return answer
        
        try:
            from transformers import Conversation

            prompt = self._construct_prompt(query, context_chunks)

            # Create conversation object for BlenderBot
            conversation = Conversation(prompt)

            result = self.generator(
                conversation,
                max_length=min(max_length, 128),  # BlenderBot works better with shorter responses
                min_length=10,
                do_sample=True,
                temperature=0.8,  # Slightly higher for more natural conversation
                top_p=0.9,
            )

            # Extract the generated response
            if hasattr(result, 'generated_responses') and result.generated_responses:
                answer = result.generated_responses[-1]  # Get the last response
            elif hasattr(result, '__iter__') and len(result) > 0:
                answer = str(result[0])
            else:
                answer = str(result)

            # Clean up the answer
            answer = answer.strip()
            if len(answer) > 400:  # Limit response length
                answer = answer[:400] + "..."

            final_answer = answer if answer else self._simple_answer_fallback(query, context_chunks)

            # Cache the result
            self._add_to_cache(cache_key, final_answer)
            return final_answer
        except Exception as e:
            logger.warning("BlenderBot generation failed, trying fallback: %s", e)
            # Fallback to DialoGPT-style generation if BlenderBot fails
            try:
                if hasattr(self, '_dialoGPT_fallback'):
                    return self._dialoGPT_fallback(query, context_chunks)
            except:
                pass

            answer = self._simple_answer_fallback(query, context_chunks)
            self._add_to_cache(cache_key, answer)
            return answer

    def _is_context_relevant(self, query: str, context_chunks: List[str]) -> bool:
        """Check if the context is actually relevant to the query."""
        if not context_chunks:
            return False
        
        query_lower = query.lower()
        context_text = " ".join(context_chunks).lower()
        
        # Extract key terms from query (simple approach)
        query_words = set(query_lower.split())
        # Remove common stop words
        stop_words = {'is', 'are', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'what', 'how', 'why', 'when', 'where', 'who'}
        key_words = query_words - stop_words
        
        # Check if any key words from query appear in context
        relevant_words_found = 0
        for word in key_words:
            if word in context_text:
                relevant_words_found += 1
        
        # Require at least 30% of key words to be present for relevance
        min_relevance = max(1, len(key_words) * 0.3)
        return relevant_words_found >= min_relevance

    def _create_cache_key(self, query: str, context_chunks: List[str]) -> str:
        """Create a cache key from query and context."""
        # Create a hash of the query and first few context chunks
        content = query + "".join(context_chunks[:3])  # Use first 3 chunks for cache key
        return hashlib.md5(content.encode()).hexdigest()

    def _add_to_cache(self, key: str, value: str) -> None:
        """Add item to cache with size management."""
        if len(self._cache) >= self._max_cache_size:
            # Remove oldest item (simple FIFO)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = value
    
    def _simple_answer_fallback(self, query: str, context_chunks: List[str]) -> str:
        """Simple fallback when LLM is not available."""
        if not context_chunks:
            return "I couldn't find relevant information to answer your question."
        
        best_chunk = context_chunks[0][:500]
        return f"Based on your notes: {best_chunk}..."

