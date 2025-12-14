from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import os
from services.vector_store import VectorStore
from services.summarizer import Summarizer
from services.note_manager import NoteManager
from services.answer_generator import AnswerGenerator

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize services
vector_store = VectorStore()
summarizer = Summarizer()
note_manager = NoteManager(vector_store, summarizer)
answer_generator = AnswerGenerator()

@app.route('/')
def index():
    """Home page - show all notes"""
    notes = note_manager.get_all_notes()
    stats = note_manager.get_stats()
    return render_template('index.html', notes=notes, stats=stats)

@app.route('/note/<note_id>')
def view_note(note_id):
    """View a specific note"""
    note = note_manager.get_note(note_id)
    if not note:
        flash('Note not found', 'error')
        return redirect(url_for('index'))
    
    # Generate summary
    summary = summarizer.summarize(note["content"], max_length=200)
    return render_template('note.html', note=note, summary=summary)

@app.route('/create', methods=['GET', 'POST'])
def create_note():
    """Create a new note"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        category = request.form.get('category', '').strip() or None
        
        if not title or not content:
            flash('Title and content are required', 'error')
            return render_template('create.html')
        
        note_id = note_manager.create_note(
            title=title,
            content=content,
            tags=tags,
            category=category
        )
        flash('Note created successfully!', 'success')
        return redirect(url_for('view_note', note_id=note_id))
    
    return render_template('create.html')

@app.route('/edit/<note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    """Edit an existing note"""
    note = note_manager.get_note(note_id)
    if not note:
        flash('Note not found', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        category = request.form.get('category', '').strip() or None
        
        if not title or not content:
            flash('Title and content are required', 'error')
            return render_template('edit.html', note=note)
        
        note_manager.update_note(note_id, {
            'title': title,
            'content': content,
            'tags': tags,
            'category': category
        })
        flash('Note updated successfully!', 'success')
        return redirect(url_for('view_note', note_id=note_id))
    
    return render_template('edit.html', note=note)

@app.route('/delete/<note_id>', methods=['POST'])
def delete_note(note_id):
    """Delete a note"""
    if note_manager.delete_note(note_id):
        flash('Note deleted successfully', 'success')
    else:
        flash('Note not found', 'error')
    return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
def search():
    """Search notes semantically - Template view"""
    query = request.args.get('q', '')
    results = []
    
    if query:
        results = note_manager.semantic_search(query, limit=20)
    
    return render_template('search.html', query=query, results=results)

@app.route('/stats')
def stats():
    """Show statistics"""
    stats_data = note_manager.get_stats()
    categories = note_manager.get_categories()
    tags = note_manager.get_tags()
    return render_template('stats.html', stats=stats_data, categories=categories, tags=tags)

@app.route('/api/summarize/<note_id>')
def api_summarize(note_id):
    """API endpoint to get note summary"""
    note = note_manager.get_note(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    max_length = request.args.get('max_length', 20000, type=int)
    summary = summarizer.summarize(note["content"], max_length=max_length)
    
    return jsonify({
        'note_id': note_id,
        'summary': summary,
        'original_length': len(note["content"]),
        'summary_length': len(summary)
    })

# PHASE 2: API Endpoints for UI Integration
@app.route('/add_note', methods=['POST'])
def add_note_api():
    """Add note via API"""
    data = request.json
    if not data or 'content' not in data:
        return jsonify({'error': 'Content is required'}), 400
    
    title = data.get('title', 'Untitled')
    content = data['content']
    tags = data.get('tags', [])
    category = data.get('category')
    
    note_id = note_manager.create_note(
        title=title,
        content=content,
        tags=tags if isinstance(tags, list) else [],
        category=category
    )
    
    return jsonify({'status': 'note added', 'note_id': note_id})

@app.route('/search', methods=['POST'])
def search_api():
    """Semantic search via API"""
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query = data['query']
    limit = data.get('limit', 10)
    
    results = note_manager.semantic_search(query, limit=limit)
    
    formatted_results = []
    for result in results:
        formatted_results.append({
            'title': result.get('title', 'Untitled'),
            'snippet': result.get('content', '')[:200] + '...' if len(result.get('content', '')) > 200 else result.get('content', ''),
            'note_id': result.get('id'),
            'similarity': result.get('similarity', 0)
        })
    
    return jsonify(formatted_results)

@app.route('/stats', methods=['GET'])
def stats_api():
    """Get statistics via API"""
    stats_data = note_manager.get_stats()
    
    return jsonify({
        'total_notes': stats_data.get('total_notes', 0),
        'categories': stats_data.get('categories', {}),
        'tags': list(note_manager.get_tags())
    })

@app.route('/ask', methods=['POST'])
def ask_question():
    """RAG endpoint - Ask question and get AI-generated answer"""
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400
    
    query = data['query']
    limit = data.get('limit', 5)
    max_answer_length = data.get('max_length', 200)
    
    # STEP 1: Retrieval - Get relevant chunks
    search_results = note_manager.semantic_search(query, limit=limit)
    
    if not search_results:
        return jsonify({
            'query': query,
            'answer': "I couldn't find any relevant information in your knowledge base to answer this question.",
            'sources': []
        })
    
    # Extract context chunks from search results
    context_chunks = []
    sources = []
    
    for result in search_results:
        content = result.get('content', '')
        if content:
            # Use matched chunk if available, otherwise use full content
            chunk_text = result.get('matched_chunk', content[:500])
            context_chunks.append(chunk_text)
            sources.append({
                'title': result.get('title', 'Untitled'),
                'note_id': result.get('id'),
                'similarity': result.get('similarity', 0)
            })
    
    # STEP 2: Prompt Construction + STEP 3: Answer Generation
    answer = answer_generator.generate_answer(
        query=query,
        context_chunks=context_chunks,
        max_length=max_answer_length
    )
    
    return jsonify({
        'query': query,
        'answer': answer,
        'sources': sources
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
