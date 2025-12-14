# Project Structure

```
AI personal knowledge vault/
│
├── backend/                    # Backend API (FastAPI)
│   ├── main.py                # Main FastAPI application and API endpoints
│   ├── requirements.txt       # Python dependencies
│   ├── start.bat              # Windows startup script
│   ├── start.sh               # Unix/Mac startup script
│   ├── .env.example           # Environment configuration template
│   │
│   ├── services/              # Core business logic services
│   │   ├── __init__.py
│   │   ├── preprocessor.py    # Minimal text preprocessing
│   │   ├── chunker.py         # Document chunking (200-300 words, 20-30 overlap)
│   │   ├── vector_store.py    # FAISS vector database and embedding management
│   │   ├── summarizer.py      # NLP summarization service
│   │   └── note_manager.py    # Note CRUD and orchestration
│   │
│   └── data/                  # Data storage (created at runtime)
│       ├── notes/             # JSON files for note metadata
│       │   └── index.json     # Notes index
│       └── faiss_db/          # FAISS vector database (index + metadata)
│
├── frontend/                   # Frontend application (React + Vite)
│   ├── package.json           # Node.js dependencies
│   ├── vite.config.js         # Vite configuration
│   ├── index.html             # HTML entry point
│   ├── start.bat              # Windows startup script
│   ├── start.sh               # Unix/Mac startup script
│   │
│   └── src/                   # React source code
│       ├── main.jsx           # React entry point
│       ├── App.jsx             # Main application component
│       ├── App.css             # Application styles
│       └── index.css           # Global styles
│
├── README.md                   # Main documentation
├── QUICKSTART.md              # Quick start guide
├── PROJECT_STRUCTURE.md       # This file
└── .gitignore                 # Git ignore rules

```

## Key Components

### Backend (`backend/`)

#### `main.py`
- FastAPI application setup
- API route definitions
- CORS configuration
- Request/response models (Pydantic)
- Endpoints:
  - `/api/notes` - CRUD operations
  - `/api/search` - Semantic search
  - `/api/summarize` - Note summarization
  - `/api/stats` - Analytics
  - `/api/categories` - Category management
  - `/api/tags` - Tag management

#### `services/vector_store.py`
- FAISS vector database (IndexFlatL2)
- Sentence transformer embeddings
- Document storage and retrieval
- Semantic similarity search
- Uses `all-MiniLM-L6-v2` model for embeddings
- Implements: Raw Text → Preprocessing → Chunking → Embeddings → FAISS

#### `services/summarizer.py`
- Text summarization using transformers
- Primary model: `facebook/bart-large-cnn`
- Fallback: `sshleifer/distilbart-cnn-12-6`
- Extractive summarization fallback

#### `services/note_manager.py`
- Note lifecycle management
- File-based JSON storage
- Integration with vector store (FAISS)
- Statistics and analytics
- Category and tag management
- Orchestrates preprocessing → chunking → embedding pipeline

### Frontend (`frontend/`)

#### `src/App.jsx`
- Main React component
- State management
- API integration (Axios)
- UI components:
  - Note cards
  - Search interface
  - Modal forms
  - Statistics dashboard

#### `src/App.css`
- Modern, responsive design
- Gradient backgrounds
- Card-based layout
- Mobile-friendly

## Data Flow

1. **Note Creation**:
   ```
   User Input → Frontend → API → NoteManager → 
   [Save JSON → Preprocess → Chunk → Generate Embeddings → Store in FAISS]
   ```

2. **Semantic Search**:
   ```
   Query → Frontend → API → VectorStore.search() → 
   [Preprocess → Generate Query Embedding → FAISS Search → Rank Results]
   ```

3. **Summarization**:
   ```
   Note ID → Frontend → API → Summarizer → 
   [Load Model → Generate Summary → Return]
   ```

## Technology Stack

### Backend
- **FastAPI**: Web framework
- **FAISS**: Vector database (IndexFlatL2)
- **Sentence Transformers**: Embedding generation (all-MiniLM-L6-v2)
- **Transformers (Hugging Face)**: NLP models
- **Pydantic**: Data validation

### Frontend
- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Axios**: HTTP client
- **Lucide React**: Icon library

## File Storage

### Notes
- Format: JSON files
- Location: `backend/data/notes/{note_id}.json`
- Index: `backend/data/notes/index.json`

### Vector Embeddings
- Format: FAISS index files (.index) + metadata pickle (.pkl)
- Location: `backend/data/faiss_db/`
- Contains: Document embeddings (chunked) and metadata
- Index Type: IndexFlatL2 (L2 distance for cosine similarity)

## API Architecture

### RESTful Endpoints
- `GET /api/notes` - List all notes
- `POST /api/notes` - Create note
- `GET /api/notes/{id}` - Get note
- `PUT /api/notes/{id}` - Update note
- `DELETE /api/notes/{id}` - Delete note
- `POST /api/search` - Semantic search
- `POST /api/summarize` - Generate summary
- `GET /api/stats` - Get statistics
- `GET /api/categories` - List categories
- `GET /api/tags` - List tags

## Configuration

### Environment Variables
- `API_HOST`: Server host (default: 0.0.0.0)
- `API_PORT`: Server port (default: 8000)
- `VECTOR_STORE_COLLECTION`: Collection name
- `EMBEDDING_MODEL`: Embedding model name

## Development Workflow

1. **Backend Development**:
   - Edit Python files in `backend/`
   - Changes auto-reload with `--reload` flag
   - Test at `http://localhost:8000/docs`

2. **Frontend Development**:
   - Edit React files in `frontend/src/`
   - Hot module replacement enabled
   - Changes reflect immediately

3. **Data Management**:
   - Notes stored as JSON (human-readable)
   - Vector DB managed by ChromaDB
   - Backup: Copy `backend/data/` folder

## Extension Points

### Adding New Features

1. **New API Endpoint**:
   - Add route in `backend/main.py`
   - Add service method if needed
   - Update frontend to call endpoint

2. **New UI Component**:
   - Create component in `frontend/src/`
   - Import and use in `App.jsx`
   - Add styles in `App.css`

3. **Custom Embedding Model**:
   - Modify `backend/services/vector_store.py`
   - Change `SentenceTransformer` model name
   - Re-index existing notes

4. **Custom Summarizer**:
   - Modify `backend/services/summarizer.py`
   - Change transformer model
   - Adjust parameters

## Security Considerations

- No authentication (add for production)
- CORS configured for localhost
- File-based storage (consider database for production)
- Input validation via Pydantic
- No SQL injection risk (using JSON files)

## Performance Notes

- Embeddings cached after first generation
- Vector search is fast (FAISS IndexFlatL2 optimized)
- Summarization may be slow on first call (model loading)
- Frontend uses React hooks for efficient rendering

## Deployment Considerations

- Backend: Deploy to cloud (AWS, GCP, Azure)
- Frontend: Build with `npm run build`, serve static files
- Database: Consider PostgreSQL + pgvector for production
- Models: Pre-download models in Docker image
- Environment: Use proper `.env` files for configuration

