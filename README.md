# AI-Powered Personal Knowledge Vault

An intelligent personal knowledge management system that enables users to store, organize, search, and summarize personal notes using semantic understanding and natural language processing techniques.

## Features

### 🧠 Semantic Search
- **AI-Powered Search**: Find notes using natural language queries, not just keyword matching
- **Vector Embeddings**: Uses sentence transformers to understand the meaning of your notes
- **Similarity Scoring**: See how relevant each result is to your query

### 📝 Note Management
- **Create & Edit Notes**: Full CRUD operations for your personal notes
- **Organize with Tags**: Categorize notes with custom tags
- **Categories**: Group notes by category for better organization
- **Rich Content**: Store detailed notes with titles and content

### 🤖 AI Summarization
- **Automatic Summaries**: Generate concise summaries of your notes
- **Configurable Length**: Control summary length based on your needs
- **NLP-Powered**: Uses transformer models for intelligent summarization

### 📊 Analytics
- **Statistics Dashboard**: View insights about your knowledge vault
- **Category Breakdown**: See how your notes are distributed
- **Tag Analytics**: Discover your most used tags

## Architecture

### Semantic Search Pipeline
```
Raw Text → Preprocessing → Chunking → BERT Embeddings → FAISS Index → Semantic Search → Ranked Results
```

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **FAISS**: Vector database for semantic search (IndexFlatL2)
- **Sentence Transformers**: BERT-based embeddings (`all-MiniLM-L6-v2`)
- **Text Preprocessing**: Minimal preprocessing (lowercase, normalize spaces)
- **Chunking**: Smart document chunking (200-300 words, 20-30 overlap)
- **Transformers**: NLP models for text summarization
- **JSON Storage**: Simple file-based storage for note metadata

**See [PIPELINE.md](PIPELINE.md) for detailed architecture documentation.**

### Frontend
- **React**: Modern UI framework
- **Vite**: Fast build tool and dev server
- **Axios**: HTTP client for API communication
- **Lucide Icons**: Beautiful icon library

## Installation

### Prerequisites
- Python 3.8 or higher
- Node.js 16 or higher
- pip (Python package manager)
- npm or yarn

### Backend Setup

1. Navigate to the project root directory:
```bash
cd "AI personal knowledge vault"
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
```

3. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. (Optional) Copy `.env.example` to `.env` and configure:
```bash
copy .env.example .env
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd "AI personal knowledge vault/frontend"
```

2. Install dependencies:
```bash
npm install
```

## Running the Application

### Start the Backend

1. Navigate to the project root directory:
```bash
cd "AI personal knowledge vault"
```

2. Activate your virtual environment (if using one)

3. Run the FastAPI server:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`
API documentation (Swagger UI) at `http://localhost:8000/docs`

### Start the Frontend

1. Navigate to the frontend directory:
```bash
cd "AI personal knowledge vault/frontend"
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Usage

### Creating Notes

1. Click the "New Note" button in the header
2. Fill in the title and content
3. Optionally add tags (comma-separated) and a category
4. Click "Create Note"

### Searching Notes

1. Type your search query in the search box in the sidebar
2. Click "Search" or press Enter
3. Results are ranked by semantic similarity
4. Each result shows a similarity score

### Summarizing Notes

1. Click the sparkles icon (✨) on any note card
2. A summary will be generated and displayed
3. The summary length is configurable (default: 200 characters)

### Organizing Notes

- **Tags**: Add multiple tags to categorize notes (e.g., "work", "ideas", "todo")
- **Categories**: Assign a single category to group related notes (e.g., "Work", "Personal", "Research")

## API Endpoints

### Notes
- `POST /api/notes` - Create a new note
- `GET /api/notes` - Get all notes
- `GET /api/notes/{note_id}` - Get a specific note
- `PUT /api/notes/{note_id}` - Update a note
- `DELETE /api/notes/{note_id}` - Delete a note

### Search
- `POST /api/search` - Semantic search across notes
  ```json
  {
    "query": "your search query",
    "limit": 10
  }
  ```

### Summarization
- `POST /api/summarize` - Generate a summary
  ```json
  {
    "note_id": "note-uuid",
    "max_length": 200
  }
  ```

### Analytics
- `GET /api/stats` - Get statistics
- `GET /api/categories` - Get all categories
- `GET /api/tags` - Get all tags

## Data Storage

- **Notes**: Stored as JSON files in `data/notes/`
- **Vector Embeddings**: Stored in `data/faiss_db/` (FAISS index + metadata)
- **Index**: Metadata index in `data/notes/index.json`

## Technology Stack

### Backend
- FastAPI - Web framework
- FAISS - Vector database (IndexFlatL2)
- Sentence Transformers - BERT-based embedding generation
- Text Preprocessing - Minimal preprocessing module
- Chunking - Smart document chunking (200-300 words, 20-30 overlap)
- Transformers (Hugging Face) - NLP models
- Pydantic - Data validation

### Frontend
- React 18 - UI framework
- Vite - Build tool
- Axios - HTTP client
- Lucide React - Icons

## Model Information

**Note (Answer Generator):** The RAG-based answer generator uses `transformers` and `torch` which are large optional dependencies. The server will start without them and will use a lightweight fallback; install full dependencies (`pip install -r requirements.txt`) to enable AI answer generation.

### Embedding Model
- **Model**: `all-MiniLM-L6-v2` (BERT-based)
- **Size**: ~80MB
- **Dimension**: 384
- **Performance**: Fast, efficient, high semantic accuracy
- **Language**: English (multilingual support available)
- **Why**: Exam-safe, widely accepted, optimal speed/accuracy tradeoff

### Vector Store
- **Technology**: FAISS (Facebook AI Similarity Search)
- **Index Type**: IndexFlatL2 (simple, reliable, exact search)
- **Why**: Fast, scalable, battle-tested, perfect for academic projects

### Summarization Model
- **Primary**: `facebook/bart-large-cnn`
- **Fallback**: `sshleifer/distilbart-cnn-12-6`
- **Extractive Fallback**: Simple sentence extraction if models fail

## Customization

### Changing the Embedding Model

Edit `services/vector_store.py`: 
```python
self.embedding_model = SentenceTransformer('your-model-name')
self.embedding_dim = <new_dimension>  # Update dimension!
```

Popular alternatives:
- `all-mpnet-base-v2` - Better quality, larger (768 dims)
- `paraphrase-multilingual-MiniLM-L12-v2` - Multilingual support (384 dims)

**Note**: If changing models, delete `data/faiss_db/` to rebuild the index.

### Changing the Summarization Model

Edit `services/summarizer.py`:
```python
self.summarizer = pipeline(
    "summarization",
    model="your-model-name",
    device=-1
)
```

## Troubleshooting

### Backend Issues

**Problem**: Models fail to download
- **Solution**: Ensure you have internet connection for first-time model download. Models are cached after first download.

**Problem**: Out of memory errors
- **Solution**: Use smaller models or reduce batch sizes. The default models are optimized for efficiency.

**Problem**: FAISS index errors
- **Solution**: Delete `data/faiss_db/` and restart. The index will be recreated.

### Frontend Issues

**Problem**: Cannot connect to backend
- **Solution**: Ensure backend is running on port 8000. Check `vite.config.js` proxy settings.

**Problem**: CORS errors
- **Solution**: Ensure backend CORS settings in `main.py` include your frontend URL.

## Future Enhancements

Potential features for future versions:
- [ ] Markdown support in notes
- [ ] Note linking and references
- [ ] Export/import functionality
- [ ] Advanced filtering and sorting
- [ ] Note templates
- [ ] Collaborative features
- [ ] Mobile app
- [ ] Cloud sync
- [ ] Advanced analytics and insights
- [ ] Multi-language support

## License

This project is open source and available for personal and educational use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues, questions, or suggestions, please open an issue on the project repository.

---

**Built with ❤️ using AI and modern web technologies**

