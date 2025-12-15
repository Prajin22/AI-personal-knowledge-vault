"""Vector Store Service"""

import faiss
import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict, Optional

from .preprocessor import Preprocessor
from .chunker import Chunker

class VectorStore:
    """Manages vector embeddings and semantic search using FAISS."""
    
    def __init__(self, collection_name: str = "knowledge_vault"):
        """Initialize the vector store with FAISS and sentence transformers."""
        # Lazy-load the embedding model to avoid import-time hangs
        self.embedding_model = None
        self._load_error = None
        self.embedding_dim = 384  # Dimension for all-MiniLM-L6-v2

    def _load_embedding_model(self):
        """Attempt to import and instantiate the sentence-transformers model.

        Raises the original exception if loading fails.
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception:
            # Leave embedding_model as None and re-raise so callers can handle.
            raise
        
        # Initialize preprocessing and chunking
        self.preprocessor = Preprocessor()
        self.chunker = Chunker(chunk_size=250, overlap=25)
        
        # Storage paths
        data_dir = Path(__file__).parent.parent / "data" / "faiss_db"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_file = data_dir / f"{collection_name}.index"
        self.metadata_file = data_dir / f"{collection_name}_metadata.pkl"
        
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        
        # Metadata storage: {chunk_id: {text, metadata, note_id, chunk_index}}
        self.metadata_store = {}
        
        # Track order of chunks in FAISS index (index -> chunk_id mapping)
        self.index_to_chunk_id = []
        
        # Load existing index if available
        self._load_index()
    
    def _load_index(self):
        """Load FAISS index and metadata from disk."""
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                with open(self.metadata_file, 'rb') as f:
                    data = pickle.load(f)
                    self.metadata_store = data.get('metadata', {})
                    self.index_to_chunk_id = data.get('index_mapping', [])
                
                if not self.index_to_chunk_id and self.metadata_store:
                    self.index_to_chunk_id = list(self.metadata_store.keys())
            except Exception:
                self.index = faiss.IndexFlatL2(self.embedding_dim)
                self.metadata_store = {}
    
    def _save_index(self):
        """Save FAISS index and metadata to disk."""
        try:
            faiss.write_index(self.index, str(self.index_file))
            with open(self.metadata_file, 'wb') as f:
                pickle.dump({
                    'metadata': self.metadata_store,
                    'index_mapping': self.index_to_chunk_id
                }, f)
        except Exception:
            pass
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a text."""
        if self.embedding_model is None:
            # Try to load on-demand; raise a helpful error if it fails
            try:
                self._load_embedding_model()
            except Exception:
                raise RuntimeError(
                    "Embedding model not available. Check your environment and install sentence-transformers."
                )

        preprocessed = self.preprocessor.preprocess(text)
        embedding = self.embedding_model.encode(preprocessed, convert_to_numpy=True)
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding.astype('float32')
    
    def add_document(
        self,
        document_id: str,
        text: str,
        metadata: Optional[Dict] = None
    ):
        """Add a document to the vector store."""
        preprocessed = self.preprocessor.preprocess(text)
        chunks = self.chunker.chunk(preprocessed, metadata)
        
        if not chunks:
            return
        
        if self.embedding_model is None:
            try:
                self._load_embedding_model()
            except Exception:
                raise RuntimeError("Embedding model not available. Cannot add documents.")

        chunk_texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embedding_model.encode(
            chunk_texts,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype('float32')
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{document_id}_chunk_{chunk['chunk_index']}"
            self.index.add(embedding.reshape(1, -1))
            self.index_to_chunk_id.append(chunk_id)
            self.metadata_store[chunk_id] = {
                'text': chunk['text'],
                'chunk_index': chunk['chunk_index'],
                'note_id': document_id,
                'metadata': metadata or {},
                'word_count': chunk.get('word_count', 0)
            }
        
        self._save_index()
    
    def update_document(
        self,
        document_id: str,
        text: str,
        metadata: Optional[Dict] = None
    ):
        """Update an existing document."""
        self.delete_document(document_id)
        self.add_document(document_id, text, metadata)
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks."""
        chunk_ids_to_delete = [
            chunk_id for chunk_id in self.metadata_store.keys()
            if self.metadata_store[chunk_id].get('note_id') == document_id
        ]
        
        if not chunk_ids_to_delete:
            return False
        
        new_index = faiss.IndexFlatL2(self.embedding_dim)
        new_metadata = {}
        new_index_mapping = []
        
        for chunk_id, chunk_meta in self.metadata_store.items():
            if chunk_id not in chunk_ids_to_delete:
                text = chunk_meta['text']
                embedding = self.generate_embedding(text)
                new_index.add(embedding.reshape(1, -1))
                new_metadata[chunk_id] = chunk_meta
                new_index_mapping.append(chunk_id)
        
        self.index = new_index
        self.metadata_store = new_metadata
        self.index_to_chunk_id = new_index_mapping
        self._save_index()
        
        return True
    
    def search(
        self,
        query: str,
        limit: int = 10,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """Perform semantic search."""
        preprocessed_query = self.preprocessor.preprocess(query)
        query_embedding = self.embedding_model.encode(
            preprocessed_query,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype('float32').reshape(1, -1)
        
        k = min(limit * 2, self.index.ntotal)
        if k == 0:
            return []
        
        distances, indices = self.index.search(query_embedding, k)
        results = []
        seen_note_ids = set()
        
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx >= len(self.index_to_chunk_id) or idx < 0:
                continue
            
            chunk_id = self.index_to_chunk_id[idx]
            chunk_meta = self.metadata_store.get(chunk_id)
            
            if not chunk_meta:
                continue
            note_id = chunk_meta.get('note_id')
            
            if filter_metadata:
                chunk_metadata = chunk_meta.get('metadata', {})
                if not all(chunk_metadata.get(k) == v for k, v in filter_metadata.items()):
                    continue
            
            if note_id in seen_note_ids:
                continue
            
            seen_note_ids.add(note_id)
            similarity = 1 / (1 + distance)
            
            results.append({
                'id': chunk_id,
                'text': chunk_meta['text'],
                'metadata': chunk_meta.get('metadata', {}),
                'note_id': note_id,
                'chunk_index': chunk_meta.get('chunk_index', 0),
                'distance': float(distance),
                'similarity': float(similarity)
            })
            
            if len(results) >= limit:
                break
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results
    
    def get_document(self, document_id: str) -> Optional[Dict]:
        """Retrieve all chunks for a specific document."""
        chunks = [
            {
                'id': chunk_id,
                'text': meta['text'],
                'metadata': meta.get('metadata', {}),
                'chunk_index': meta.get('chunk_index', 0)
            }
            for chunk_id, meta in self.metadata_store.items()
            if meta.get('note_id') == document_id
        ]
        
        if not chunks:
            return None
        
        chunks.sort(key=lambda x: x['chunk_index'])
        full_text = ' '.join(chunk['text'] for chunk in chunks)
        
        return {
            'id': document_id,
            'text': full_text,
            'metadata': chunks[0]['metadata'] if chunks else {},
            'chunks': chunks
        }
