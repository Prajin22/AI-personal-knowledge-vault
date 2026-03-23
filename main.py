from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
import os
import uuid
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError
import json
from services.vector_store import VectorStore
from services.summarizer import Summarizer
from services.note_manager import NoteManager
from services.answer_generator import AnswerGenerator
from services.document_processor import DocumentProcessor

# OAuth imports
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# OAuth configuration
oauth = OAuth(app)

# Google OAuth
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', 'your-google-client-secret'),
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# GitHub OAuth
github = oauth.register(
    name='github',
    client_id=os.environ.get('GITHUB_CLIENT_ID', 'your-github-client-id'),
    client_secret=os.environ.get('GITHUB_CLIENT_SECRET', 'your-github-client-secret'),
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx', 'xls', 'csv'}
USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.json')

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class
class User(UserMixin):
    def __init__(self, id, email, username, password_hash):
        self.id = id
        self.email = email
        self.username = username
        self.password_hash = password_hash

# Login forms
def validate_email_format(email):
    """Basic email format validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

    def validate_email(self, field):
        if not validate_email_format(field.data):
            raise ValidationError('Please enter a valid email address.')

class SignupForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired(), Length(min=3)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_email(self, field):
        if not validate_email_format(field.data):
            raise ValidationError('Please enter a valid email address.')

@login_manager.user_loader
def load_user(user_id):
    users = load_users()
    user_data = users.get(user_id)
    if user_data:
        return User(user_id, user_data['email'], user_data.get('username', user_data['email']), user_data['password_hash'])
    return None

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

# Initialize services
vector_store = VectorStore()
summarizer = Summarizer()
document_processor = DocumentProcessor()
note_manager = NoteManager(vector_store, summarizer)
answer_generator = AnswerGenerator(load_model=False)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# Model loading for the answer generator is deferred to first use to
# avoid long startup times and heavy imports (transformers/torch). If
# the model isn't available at runtime, the service will use a fallback.
if getattr(answer_generator, '_load_error', None):
    app.logger.warning("Answer generator model not loaded: %s", answer_generator._load_error)

# If the embedding model couldn't be loaded at startup, warn but keep the app running.
if vector_store.embedding_model is None:
    app.logger.warning(
        "Embedding model not loaded; semantic search and document adding will fail until sentence-transformers can be imported.\n"
        "To fix: activate your virtualenv and run `pip install -r requirements.txt`."
    )

@app.route('/')
@login_required
def index():
    """Home page - show all notes"""
    notes = note_manager.get_all_notes()
    stats = note_manager.get_stats()
    return render_template('index.html', notes=notes, stats=stats)

@app.route('/note/<note_id>')
@login_required
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
@login_required
def create_note():
    """Create a new note with optional file upload"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        tags = [tag.strip() for tag in request.form.get('tags', '').split(',') if tag.strip()]
        category = request.form.get('category', '').strip() or None
        train_model = request.form.get('train_model', 'no') == 'yes'
        
        # Handle file upload if present
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                try:
                    # Get file extension and remove the dot
                    file_extension = os.path.splitext(file.filename)[1].lower().lstrip('.')
                    if not file_extension or file_extension not in ALLOWED_EXTENSIONS:
                        supported = ', '.join(f'.{ext}' for ext in ALLOWED_EXTENSIONS)
                        flash(f'Unsupported file type: .{file_extension}. Supported types: {supported}', 'error')
                        return render_template('create.html')
                    
                    # Add the dot back for the document processor
                    file_extension_with_dot = f'.{file_extension}'
                    
                    # Process the uploaded file
                    content = document_processor.process_document(file, file_extension_with_dot)

                    if train_model and content:
                        trained = document_processor.train_with_document(content)
                        if trained:
                            answer_generator.reload()
                    
                    # If title is empty, use the filename (without extension) as title
                    if not title:
                        title = os.path.splitext(file.filename)[0]
                    
                    # Add file type as a tag
                    tags.append(f"imported_{file_extension}")
                    
                except Exception as e:
                    app.logger.error(f"Error processing uploaded file: {str(e)}")
                    flash(f'Error processing file: {str(e)}', 'error')
                    return render_template('create.html')
        
        if not title or not content:
            flash('Title and content are required', 'error')
            return render_template('create.html')
        
        note_id = note_manager.create_note(
            title=title,
            content=content,
            tags=tags,
            category=category
        )
        
        if getattr(note_manager, '_last_indexing_error', None):
            flash('Note saved but indexing failed (embedding model unavailable). Install sentence-transformers to enable semantic search.', 'warning')
        else:
            flash('Note created successfully!', 'success')
        
        return redirect(url_for('view_note', note_id=note_id))
    
    return render_template('create.html')

@app.route('/edit/<note_id>', methods=['GET', 'POST'])
@login_required
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
        if getattr(note_manager, '_last_indexing_error', None):
            flash('Note updated but indexing failed (embedding model unavailable). Install sentence-transformers to enable semantic search.', 'warning')
        else:
            flash('Note updated successfully!', 'success')
        return redirect(url_for('view_note', note_id=note_id))
    
    return render_template('edit.html', note=note)

@app.route('/delete/<note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    """Delete a note"""
    if note_manager.delete_note(note_id):
        flash('Note deleted successfully', 'success')
    else:
        flash('Note not found', 'error')
    return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
@login_required
def search():
    """Search notes semantically - Template view"""
    query = request.args.get('q', '')
    results = []
    
    if query:
        results = note_manager.semantic_search(query, limit=20)
    
    return render_template('search.html', query=query, results=results)

@app.route('/stats')
@login_required
def stats():
    """Show statistics"""
    stats_data = note_manager.get_stats()
    categories = note_manager.get_categories()
    tags = note_manager.get_tags()
    return render_template('stats.html', stats=stats_data, categories=categories, tags=tags)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        users = load_users()
        user_data = None
        user_id = None
        
        # Find user by email
        for uid, data in users.items():
            if data['email'] == form.email.data:
                user_data = data
                user_id = uid
                break
        
        if user_data and check_password_hash(user_data['password_hash'], form.password.data):
            user = User(user_id, user_data['email'], user_data.get('username', user_data['email']), user_data['password_hash'])
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = SignupForm()
    if form.validate_on_submit():
        users = load_users()
        
        # Check if email already exists
        for user_data in users.values():
            if user_data['email'] == form.email.data:
                flash('Email already registered', 'error')
                return render_template('signup.html', form=form)
        
        # Create new user
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(form.password.data)
        users[user_id] = {
            'email': form.email.data,
            'username': form.username.data,
            'password_hash': password_hash
        }
        save_users(users)
        
        # Log in the new user
        user = User(user_id, form.email.data, form.username.data, password_hash)
        login_user(user)
        
        flash('Account created successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('signup.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    return redirect(url_for('index'))

@app.route('/terms')
def terms():
    """Terms of Service page"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    """Privacy Policy page"""
    return render_template('privacy.html')

@app.route('/login/google')
def login_google():
    """Google OAuth login"""
    if os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id') == 'your-google-client-id':
        flash('Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.', 'error')
        return redirect(url_for('login'))
    
    redirect_uri = url_for('auth_google', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/github')
def login_github():
    """GitHub OAuth login"""
    if os.environ.get('GITHUB_CLIENT_ID', 'your-github-client-id') == 'your-github-client-id':
        flash('GitHub OAuth is not configured. Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET environment variables.', 'error')
        return redirect(url_for('login'))
    
    redirect_uri = url_for('auth_github', _external=True)
    return github.authorize_redirect(redirect_uri)

@app.route('/auth/google')
def auth_google():
    """Google OAuth callback"""
    try:
        token = google.authorize_access_token()
        resp = google.get('https://www.googleapis.com/oauth2/v2/userinfo')
        user_info = resp.json()

        # Create or get user
        user_id = f"google_{user_info['id']}"
        users = load_users()

        if user_id not in users:
            users[user_id] = {
                'email': user_info['email'],
                'username': user_info.get('name', user_info['email']),
                'password_hash': '',  # OAuth users don't have passwords
                'oauth_provider': 'google',
                'oauth_id': user_info['id']
            }
            save_users(users)

        user = User(user_id, user_info['email'], user_info.get('name', user_info['email']), '')
        login_user(user)

        flash('Successfully logged in with Google!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        app.logger.error(f"Google OAuth error: {str(e)}")
        flash('Failed to login with Google. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/auth/github')
def auth_github():
    """GitHub OAuth callback"""
    try:
        token = github.authorize_access_token()
        resp = github.get('user')
        user_info = resp.json()

        # Get user email (GitHub may require separate request)
        email_resp = github.get('user/emails')
        emails = email_resp.json()
        primary_email = next((email['email'] for email in emails if email['primary']), user_info.get('email'))

        # Create or get user
        user_id = f"github_{user_info['id']}"
        users = load_users()

        if user_id not in users:
            users[user_id] = {
                'email': primary_email,
                'username': user_info.get('login', primary_email),
                'password_hash': '',  # OAuth users don't have passwords
                'oauth_provider': 'github',
                'oauth_id': user_info['id']
            }
            save_users(users)

        user = User(user_id, primary_email, user_info.get('login', primary_email), '')
        login_user(user)

        flash('Successfully logged in with GitHub!', 'success')
        return redirect(url_for('index'))

    except Exception as e:
        app.logger.error(f"GitHub OAuth error: {str(e)}")
        flash('Failed to login with GitHub. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/signup/google')
def signup_google():
    """Google OAuth signup - redirects to login"""
    return redirect(url_for('login_google'))

@app.route('/signup/github')
def signup_github():
    """GitHub OAuth signup - redirects to login"""
    return redirect(url_for('login_github'))

@app.route('/account')
@login_required
def account():
    """Account details page"""
    return render_template('account.html')

@app.route('/health')
def health():
    """Health endpoint reporting availability of heavy models."""
    embedding_ok = vector_store.embedding_model is not None
    summarizer_ok = getattr(summarizer, 'summarizer', None) is not None
    details = {}
    if getattr(vector_store, '_load_error', None):
        details['embedding_error'] = str(vector_store._load_error)
    if getattr(summarizer, '_load_error', None):
        details['summarizer_error'] = str(summarizer._load_error)
    if getattr(note_manager, '_last_indexing_error', None):
        details['last_indexing_error'] = str(note_manager._last_indexing_error)
    
    return jsonify({
        'status': 'ok' if embedding_ok and summarizer_ok else 'degraded',
        'embedding_model': embedding_ok,
        'summarizer': summarizer_ok,
        'details': details
    })

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
    indexed = getattr(note_manager, '_last_indexing_error', None) is None
    resp = {'status': 'note added', 'note_id': note_id, 'indexed': indexed}
    if not indexed:
        resp['indexing_error'] = str(note_manager._last_indexing_error)

    return jsonify(resp)

@app.route('/api/search', methods=['POST'])
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

@app.route('/api/stats', methods=['GET'])
def stats_api():
    """Get statistics via API"""
    stats_data = note_manager.get_stats()
    
    return jsonify({
        'total_notes': stats_data.get('total_notes', 0),
        'categories': stats_data.get('categories', {}),
        'tags': list(note_manager.get_tags())
    })

import re

def is_safe_query(query):
    """Basic safety check for user queries"""
    # Check for potentially harmful patterns
    harmful_patterns = [
        r'(?i)(kill|murder|harm|hurt|violence|weapon|bomb|explosive)',
        r'(?i)(hack|crack|exploit|malware|virus)',
        r'(?i)(illegal|drugs|criminal|fraud|scam)',
        r'(?i)(hate|racist|discriminat|offensive)',
        r'(?i)(self.harm|suicide|depress)',
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, query):
            return False
    return True

def filter_sensitive_content(content):
    """Filter potentially sensitive information from responses"""
    # Remove potential email addresses, phone numbers, etc.
    content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL REMOVED]', content)
    content = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE REMOVED]', content)
    content = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[CARD REMOVED]', content)
    return content

@app.route('/ask', methods=['POST'])
def ask_question():
    """RAG endpoint - Ask question and get AI-generated answer"""
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'Query is required'}), 400

    query = data['query'].strip()

    # Safety check
    if not is_safe_query(query):
        return jsonify({
            'query': query,
            'answer': "I apologize, but I cannot assist with that request. Please ask a different question about your knowledge base.",
            'sources': []
        })

    limit = min(data.get('limit', 5), 10)  # Cap at 10 results
    max_answer_length = min(data.get('max_length', 300), 1000)  # Cap at 1000 chars

    # DIRECT FALLBACK FOR COMMON AI QUESTIONS
    query_lower = query.lower().strip()
    fallback_responses = {
        'what is ai': {
            'answer': 'Artificial Intelligence (AI) is the simulation of human intelligence processes by machines, especially computer systems. These processes include learning (the acquisition of information and rules for using the information), reasoning (using rules to reach approximate or definite conclusions), and self-correction. AI encompasses various subfields including machine learning, natural language processing, computer vision, robotics, and expert systems.',
            'source': 'Built-in AI Knowledge Base',
            'confidence': 'high'
        },
        'what is artificial intelligence': {
            'answer': 'Artificial Intelligence (AI) refers to the capability of computational systems to perform tasks typically associated with human intelligence. This includes learning from experience, understanding natural language, recognizing patterns, solving problems, and making decisions. AI systems can be narrow (specialized in specific tasks) or general (capable of performing any intellectual task that a human can do).',
            'source': 'Built-in AI Knowledge Base',
            'confidence': 'high'
        },
        'what is machine learning': {
            'answer': 'Machine Learning is a subset of artificial intelligence (AI) that enables computers to learn and improve from experience without being explicitly programmed. Machine learning algorithms build mathematical models based on training data to make predictions or decisions. There are three main types: supervised learning (learning from labeled examples), unsupervised learning (finding patterns in unlabeled data), and reinforcement learning (learning through trial and error).',
            'source': 'Built-in AI Knowledge Base',
            'confidence': 'high'
        },
        'what is deep learning': {
            'answer': 'Deep Learning is a subset of machine learning that uses artificial neural networks with multiple layers (hence "deep") to model complex patterns in data. Deep learning architectures can automatically learn hierarchical representations of data, making them particularly effective for tasks like image recognition, natural language processing, and speech recognition. Deep learning has been responsible for many recent AI breakthroughs.',
            'source': 'Built-in AI Knowledge Base',
            'confidence': 'high'
        }
    }

    # Check for exact fallback matches
    for question_pattern, response_data in fallback_responses.items():
        if question_pattern in query_lower or query_lower in question_pattern:
            return jsonify({
                'query': query,
                'answer': f"Based on comprehensive AI knowledge, here's the answer: {response_data['answer']}",
                'sources': [{
                    'title': response_data['source'],
                    'note_id': 'builtin_ai_knowledge',
                    'similarity': 1.0,
                    'relevance_score': 100,
                    'topic_match': question_pattern.split()[-1]  # Extract topic
                }],
                'context_quality': 1,
                'relevance_score': 1.0,
                'topic_matches': [question_pattern.split()[-1]],
                'fallback_used': True
            })

    # STEP 1: Enhanced Retrieval with relevance filtering
    search_results = note_manager.semantic_search(query, limit=limit * 3)  # Get more results

    if not search_results:
        # If no search results, try basic keyword matching as last resort
        all_notes = note_manager.get_all_notes()
        keyword_matches = []
        query_words = set(query_lower.split())

        for note in all_notes:
            title_lower = note.get('title', '').lower()
            content_lower = note.get('content', '').lower()

            # Check for keyword matches
            title_matches = sum(1 for word in query_words if word in title_lower)
            content_matches = sum(1 for word in query_words if word in content_lower)

            if title_matches > 0 or content_matches > 0:
                note['keyword_score'] = title_matches * 2 + content_matches
                keyword_matches.append(note)

        if keyword_matches:
            # Sort by keyword score and use top matches
            keyword_matches.sort(key=lambda x: x.get('keyword_score', 0), reverse=True)
            search_results = keyword_matches[:limit]

    if not search_results:
        return jsonify({
            'query': query,
            'answer': "I apologize, but I couldn't find any relevant information in your knowledge base to answer this question. Please consider adding relevant notes or rephrasing your query.",
            'sources': []
        })

    # Enhanced relevance filtering with AI-specific prioritization
    filtered_results = []
    query_lower = query.lower().strip()
    query_words = set(query_lower.split())

    # Check for exact AI topic matches first
    ai_topics = {
        'artificial intelligence': ['ai', 'artificial intelligence', 'machine intelligence'],
        'machine learning': ['ml', 'machine learning', 'statistical learning'],
        'deep learning': ['deep learning', 'neural networks', 'deep neural'],
        'computer vision': ['computer vision', 'image recognition', 'visual ai'],
        'natural language processing': ['nlp', 'natural language processing', 'text analysis'],
        'reinforcement learning': ['reinforcement learning', 'rl'],
        'supervised learning': ['supervised learning'],
        'unsupervised learning': ['unsupervised learning']
    }

    # Find exact topic matches
    exact_topic_matches = []
    for topic, keywords in ai_topics.items():
        if any(keyword in query_lower for keyword in keywords):
            # Look for notes that match this exact topic
            for result in search_results:
                title_lower = result.get('title', '').lower()
                content_lower = result.get('content', '').lower()

                # Exact title match gets highest priority
                if topic in title_lower:
                    result['topic_match_score'] = 1.0
                    result['exact_topic'] = topic
                    exact_topic_matches.append(result)
                    break
                # Content contains the topic
                elif topic in content_lower:
                    result['topic_match_score'] = 0.8
                    result['exact_topic'] = topic
                    exact_topic_matches.append(result)
                    break

    for result in search_results:
        content = result.get('content', '').strip()
        title = result.get('title', '').strip()

        # Skip empty content
        if len(content) < 50:
            continue

        # Calculate relevance score with enhanced logic
        relevance_score = 0

        # Exact topic match bonus (highest priority)
        if result in exact_topic_matches:
            relevance_score += result.get('topic_match_score', 0) * 100  # Massive boost

        # Title keyword matching
        title_lower = title.lower()
        title_matches = sum(1 for word in query_words if word in title_lower)
        if title_matches > 0:
            relevance_score += title_matches * 20  # Title matches are very important

        # Content keyword matching
        content_lower = content.lower()
        content_matches = sum(1 for word in query_words if word in content_lower)
        relevance_score += content_matches * 5

        # AI-specific content bonus
        ai_indicators = ['artificial intelligence', 'machine learning', 'neural network', 'algorithm', 'model', 'training', 'prediction']
        ai_content_matches = sum(1 for indicator in ai_indicators if indicator in content_lower)
        relevance_score += ai_content_matches * 2

        # Length and quality bonus
        if len(content) > 500:
            relevance_score += 5
        if len(content) > 1000:
            relevance_score += 5

        # Question-type bonuses
        if any(word in query_lower for word in ['what is', 'define', 'explain', 'how does']):
            if 'definition' in content_lower or 'is a' in content_lower or 'refers to' in content_lower:
                relevance_score += 15

        result['enhanced_relevance_score'] = relevance_score
        filtered_results.append(result)

    # Sort by enhanced relevance score
    filtered_results.sort(key=lambda x: x.get('enhanced_relevance_score', 0), reverse=True)
    top_results = filtered_results[:limit]

    # STEP 2: Extract context chunks with better quality filtering
    context_chunks = []
    sources = []

    for result in top_results:
        content = result.get('content', '')
        title = result.get('title', '')

        # Extract most relevant chunk based on query with enhanced logic
        chunk = extract_relevant_chunk_enhanced(content, query, result.get('exact_topic'))
        if chunk and len(chunk.strip()) > 20:
            context_chunks.append(chunk)
            sources.append({
                'title': title,
                'note_id': result.get('id'),
                'similarity': result.get('similarity', 0),
                'relevance_score': result.get('enhanced_relevance_score', 0),
                'topic_match': result.get('exact_topic', None)
            })

    if not context_chunks:
        return jsonify({
            'query': query,
            'answer': "I found some potentially relevant information, but the content quality was insufficient to generate a reliable answer. Please try rephrasing your question or add more detailed notes to your knowledge base.",
            'sources': sources
        })

    # STEP 3: Enhanced Answer Generation with topic-aware prompting
    answer = answer_generator.generate_answer(
        query=query,
        context_chunks=context_chunks,
        max_length=max_answer_length
    )

    # STEP 4: Answer validation and quality improvement
    if answer:
        # Enhanced validation
        filtered_answer = filter_sensitive_content(answer)

        # Topic relevance validation
        topic_relevant = True
        if exact_topic_matches:
            topic = exact_topic_matches[0].get('exact_topic', '')
            topic_keywords = ai_topics.get(topic, [])
            answer_relevance = sum(1 for keyword in topic_keywords if keyword in filtered_answer.lower())
            if answer_relevance == 0 and len(filtered_answer) > 100:
                topic_relevant = False

        # If answer seems off-topic, provide better fallback
        if not topic_relevant and exact_topic_matches:
            topic = exact_topic_matches[0].get('exact_topic', '')
            fallback_answer = f"I found information about {topic} in your notes. {filtered_answer}"
        else:
            fallback_answer = filtered_answer

        formatted_answer = f"Based on your knowledge base, here's what I found: {fallback_answer}"
    else:
        formatted_answer = "I apologize, but I couldn't generate a comprehensive answer from the available information."

    return jsonify({
        'query': query,
        'answer': formatted_answer,
        'sources': sources,
        'context_quality': len(context_chunks),
        'relevance_score': sum(s.get('relevance_score', 0) for s in sources) / len(sources) if sources else 0,
        'topic_matches': [s.get('topic_match') for s in sources if s.get('topic_match')]
    })

def extract_relevant_chunk_enhanced(content: str, query: str, exact_topic: str = None, max_length: int = 500) -> str:
    """Enhanced chunk extraction with topic awareness"""
    if not content or len(content) < 50:
        return content

    sentences = content.split('. ')

    # Score sentences with enhanced logic
    scored_sentences = []
    query_terms = set(query.lower().split())

    for i, sentence in enumerate(sentences):
        sentence_lower = sentence.lower()
        score = 0

        # Query term matches
        query_matches = sum(1 for term in query_terms if term in sentence_lower)
        score += query_matches * 10

        # Topic-specific boosting
        if exact_topic:
            if exact_topic in sentence_lower:
                score += 50  # Massive boost for topic matches
            # Related terms
            if exact_topic == 'artificial intelligence':
                ai_terms = ['intelligence', 'human', 'machines', 'systems', 'learning']
                score += sum(5 for term in ai_terms if term in sentence_lower)

        # Question-type relevance
        if any(word in query.lower() for word in ['what is', 'define', 'explain']):
            definition_indicators = ['is a', 'is the', 'refers to', 'means', 'defined as']
            if any(indicator in sentence_lower for indicator in definition_indicators):
                score += 15

        # Position bonus (earlier sentences often more important)
        score += max(0, 10 - i)

        scored_sentences.append((i, sentence, score))

    # Sort by score and get top sentences
    scored_sentences.sort(key=lambda x: x[2], reverse=True)
    top_sentences = scored_sentences[:4]  # Get top 4 most relevant sentences
    top_sentences.sort(key=lambda x: x[0])  # Sort back to original order

    # Combine sentences
    chunk_sentences = [s[1] for s in top_sentences]
    chunk = '. '.join(chunk_sentences)

    # Ensure chunk doesn't exceed max length
    if len(chunk) > max_length:
        chunk = chunk[:max_length].rsplit(' ', 1)[0] + '...'

    return chunk.strip() + '.' if chunk and not chunk.endswith('.') else chunk.strip()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    """Handle file upload and processing"""
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Save the file temporarily
            file_extension = os.path.splitext(file.filename)[1].lower()
            filename = f"{uuid.uuid4()}{file_extension}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            try:
                # Process the document
                content = document_processor.process_document(filepath, file_extension)

                train_model = request.form.get('train_model', 'no') == 'yes'
                if train_model and content:
                    trained = document_processor.train_with_document(content)
                    if trained:
                        answer_generator.reload()
                
                # Create a note from the document
                title = os.path.splitext(file.filename)[0]
                note_id = note_manager.create_note(
                    title=title,
                    content=content,
                    tags=[f"imported_{file_extension[1:]}"],  # Add file type as a tag
                    category="Imported Documents"
                )
                
                # Clean up the temporary file
                os.remove(filepath)
                
                flash(f'Document "{title}" imported successfully!', 'success')
                return redirect(url_for('view_note', note_id=note_id))
                
            except Exception as e:
                # Clean up in case of error
                if os.path.exists(filepath):
                    os.remove(filepath)
                app.logger.error(f"Error processing document: {str(e)}")
                flash(f'Error processing document: {str(e)}', 'error')
                return redirect(request.url)
    
    return """
    <!doctype html>
    <title>Upload Document</title>
    <h1>Upload Document</h1>
    <p>Supported formats: PDF, DOCX, XLSX, XLS, CSV</p>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    <p><a href="/">Back to Home</a></p>
    """

# API endpoint for file upload
@app.route('/api/upload', methods=['POST'])
def api_upload_file():
    """API endpoint for document upload and processing"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not file or not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        # Process the file directly from memory
        file_extension = os.path.splitext(file.filename)[1].lower()
        content = document_processor.process_document(file, file_extension)

        train_model = request.form.get('train_model', 'no') == 'yes'
        trained = False
        if train_model and content:
            trained = document_processor.train_with_document(content)
            if trained:
                answer_generator.reload()

        title = os.path.splitext(file.filename)[0]

        return jsonify({
            'status': 'success',
            'title': title,
            'content': content,
            'trained': trained
        })
        
    except Exception as e:
        app.logger.error(f"API Error processing document: {str(e)}")
        return jsonify({'error': f'Error processing document: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
