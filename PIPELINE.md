# AI Knowledge Vault - Pipeline Architecture

## 🔗 Pipeline Overview

```
Raw Text
   ↓
Preprocessing (Minimal)
   ↓
Chunking (200-300 words, 20-30 overlap)
   ↓
Sentence Embeddings (BERT - all-MiniLM-L6-v2)
   ↓
FAISS Vector Index (IndexFlatL2)
   ↓
Semantic Search
   ↓
Ranked Results
```

## 1️⃣ Text Preprocessing (Minimal)

**Philosophy**: We are NOT training models. We are consuming pretrained intelligence.

### What We Do ✅
- **Lowercase**: Convert all text to lowercase
- **Remove Extra Spaces**: Normalize whitespace (multiple spaces → single space)
- **Keep Punctuation**: BERT understands context from punctuation

### What We DON'T Do ❌
- **Stopword Removal**: BERT already knows word importance
- **Stemming**: BERT handles word variations naturally
- **Aggressive Cleaning**: Preserve natural language structure

**Reason**: BERT already knows language structure. Over-processing can harm semantic understanding.

### Implementation
```python
# services/preprocessor.py
class Preprocessor:
    @staticmethod
    def preprocess(text: str) -> str:
        text = text.lower()                    # Lowercase
        text = re.sub(r'\s+', ' ', text)      # Remove extra spaces
        text = text.strip()                    # Strip edges
        return text  # Keep punctuation!
```

## 2️⃣ Chunking Strategy (Critical Design Choice)

**Never embed huge documents directly.**

### Best Practice
- **Chunk Size**: 200-300 words (default: 250)
- **Overlap**: 20-30 words (default: 25)

### Why Chunking?
1. **Improves Search Accuracy**: Smaller, focused chunks match queries better
2. **Prevents Context Loss**: Large documents lose semantic coherence
3. **Better Embeddings**: BERT works best with focused text segments
4. **Efficient Storage**: Smaller vectors, faster search

### Implementation
```python
# services/chunker.py
class Chunker:
    def __init__(self, chunk_size: int = 250, overlap: int = 25):
        self.chunk_size = chunk_size  # 200-300 words
        self.overlap = overlap        # 20-30 words
```

### Chunking Process
1. Split text into sentences (preserve punctuation)
2. Group sentences into chunks of ~250 words
3. Add 25-word overlap between chunks
4. Each chunk gets its own embedding

## 3️⃣ Sentence Embeddings (The Brain)

### Model Choice: `all-MiniLM-L6-v2`

**Why This Model?**
- ✅ **Fast**: Optimized for speed
- ✅ **Lightweight**: ~80MB, runs on CPU
- ✅ **High Semantic Accuracy**: Excellent for semantic search
- ✅ **Widely Accepted**: Academically recognized
- ✅ **Exam-Safe**: Standard choice for projects

### Technical Details
- **Architecture**: BERT-based (MiniLM)
- **Embedding Dimension**: 384
- **Normalization**: L2 normalized for cosine similarity
- **Language**: English (multilingual variants available)

### Implementation
```python
# services/vector_store.py
self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode(text, normalize_embeddings=True)
```

## 4️⃣ FAISS Vector Store (The Engine)

### Why FAISS?
- **Fast**: Optimized C++ implementation
- **Scalable**: Handles millions of vectors efficiently
- **Reliable**: Battle-tested by Facebook AI Research
- **Simple**: Easy to use, well-documented

### Index Type: `IndexFlatL2`

**Why IndexFlatL2?**
- ✅ **Simple**: No complex parameters
- ✅ **Reliable**: Exact nearest neighbor search
- ✅ **Suitable for Projects**: Perfect for semester/academic work
- ❌ **No IVF**: Unnecessary complexity for small-medium datasets
- ❌ **No HNSW**: Overkill for most use cases

### How It Works
1. **Storage**: All embeddings stored in memory
2. **Search**: Brute-force L2 distance calculation
3. **Normalization**: Embeddings are L2-normalized → L2 distance ≈ cosine distance
4. **Results**: Returns k nearest neighbors with distances

### Implementation
```python
# services/vector_store.py
import faiss

# Initialize index
index = faiss.IndexFlatL2(embedding_dim)  # 384 for all-MiniLM-L6-v2

# Add vectors
index.add(embeddings)

# Search
distances, indices = index.search(query_embedding, k=10)
```

## 5️⃣ Semantic Search Process

### Query Pipeline
```
User Query
   ↓
Preprocessing (lowercase, normalize spaces)
   ↓
Generate Query Embedding (all-MiniLM-L6-v2)
   ↓
FAISS Search (IndexFlatL2)
   ↓
Rank by Similarity
   ↓
Return Top K Results
```

### Similarity Calculation
- **Distance**: L2 distance (Euclidean)
- **Normalization**: Embeddings are L2-normalized
- **Conversion**: `similarity = 1 / (1 + distance)`
- **Result**: Higher similarity = better match

## 6️⃣ Complete Flow Example

### Adding a Document
```python
# 1. Raw Text
text = "Your note content here..."

# 2. Preprocessing
preprocessed = preprocessor.preprocess(text)
# → "your note content here..."

# 3. Chunking
chunks = chunker.chunk(preprocessed)
# → [
#     {"text": "chunk 1 (250 words)", "chunk_index": 0},
#     {"text": "chunk 2 (250 words)", "chunk_index": 1},
#   ]

# 4. Embeddings
embeddings = model.encode([chunk['text'] for chunk in chunks])
# → numpy array of shape (num_chunks, 384)

# 5. FAISS Index
index.add(embeddings)
# → Stored in FAISS IndexFlatL2
```

### Searching
```python
# 1. Query
query = "find information about X"

# 2. Preprocess
preprocessed_query = preprocessor.preprocess(query)

# 3. Embed Query
query_embedding = model.encode(preprocessed_query)

# 4. Search FAISS
distances, indices = index.search(query_embedding, k=10)

# 5. Rank Results
results = rank_by_similarity(distances, indices)
# → Top 10 most similar chunks
```

## Performance Characteristics

### Preprocessing
- **Speed**: Very fast (< 1ms per document)
- **Memory**: Negligible

### Chunking
- **Speed**: Fast (~10-50ms per document)
- **Memory**: Minimal (text processing only)

### Embedding Generation
- **Speed**: ~50-200ms per chunk (CPU)
- **Memory**: ~80MB for model + embeddings
- **First Run**: Downloads model (~80MB)

### FAISS Search
- **Speed**: ~1-10ms for 1000 vectors
- **Memory**: ~1.5KB per vector (384 dims × 4 bytes)
- **Scales**: Linear with number of vectors

## Design Decisions

### Why Not ChromaDB?
- FAISS is more lightweight
- Better for academic projects (simpler)
- Direct control over indexing
- No external dependencies

### Why Not Larger Models?
- `all-MiniLM-L6-v2` is optimal for speed/accuracy tradeoff
- Larger models (e.g., `all-mpnet-base-v2`) are slower
- For semantic search, MiniLM is sufficient

### Why IndexFlatL2?
- Simple and reliable
- No hyperparameters to tune
- Perfect for projects with < 100K vectors
- Easy to understand and explain

## File Structure

```
services/
├── preprocessor.py      # Minimal text preprocessing
├── chunker.py          # Document chunking (200-300 words, 20-30 overlap)
├── vector_store.py     # FAISS + Embeddings + Search
└── note_manager.py     # Orchestrates the pipeline
```

## Data Flow

```
Note Creation:
  NoteManager.create_note()
    → VectorStore.add_document()
      → Preprocessor.preprocess()
      → Chunker.chunk()
      → SentenceTransformer.encode()
      → FAISS.index.add()

Search:
  NoteManager.semantic_search()
    → VectorStore.search()
      → Preprocessor.preprocess(query)
      → SentenceTransformer.encode(query)
      → FAISS.index.search()
      → Rank results by similarity
```

## Summary

This pipeline implements a **production-ready semantic search system** using:
- ✅ Minimal preprocessing (preserves semantic meaning)
- ✅ Smart chunking (200-300 words, 20-30 overlap)
- ✅ BERT embeddings (`all-MiniLM-L6-v2`)
- ✅ FAISS vector index (`IndexFlatL2`)
- ✅ Ranked semantic search results

**Result**: Fast, accurate, and academically sound semantic search for personal knowledge management.

