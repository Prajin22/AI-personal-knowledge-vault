# Quick Start Guide

Get your AI Personal Knowledge Vault up and running in minutes!

## Prerequisites Check

Make sure you have:
- ✅ Python 3.8+ installed (`python --version`)
- ✅ Node.js 16+ installed (`node --version`)
- ✅ pip installed (comes with Python)
- ✅ npm installed (comes with Node.js)

## Windows Quick Start

### 1. Start the Backend

Open a terminal in the project root and run:
```bash
start.bat
```

Or manually:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 2. Start the Frontend

Open a **new** terminal in the `frontend` folder and run:
```bash
start.bat
```

Or manually:
```bash
npm install
npm run dev
```

### 3. Open the App

Open your browser and go to: **http://localhost:3000**

## macOS/Linux Quick Start

### 1. Start the Backend

Open a terminal in the project root and run:
```bash
chmod +x start.sh
./start.sh
```

Or manually:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 2. Start the Frontend

Open a **new** terminal in the `frontend` folder and run:
```bash
chmod +x start.sh
./start.sh
```

Or manually:
```bash
npm install
npm run dev
```

### 3. Open the App

Open your browser and go to: **http://localhost:3000**

## First Time Setup Notes

### Backend
- First run will download AI models (~500MB total)
- This may take 5-10 minutes depending on your internet speed
- Models are cached, so subsequent starts are much faster
- The server will be available at `http://localhost:8000`

### Frontend
- First run will install npm packages (~100MB)
- This usually takes 1-2 minutes
- The app will be available at `http://localhost:3000`

## Verify Installation

### Backend Health Check
Visit: http://localhost:8000
You should see: `{"status":"healthy","service":"AI Personal Knowledge Vault API","version":"1.0.0"}`

### API Documentation
Visit: http://localhost:8000/docs
You should see the Swagger UI with all available endpoints.

### Frontend
Visit: http://localhost:3000
You should see the Knowledge Vault interface.

## Creating Your First Note

1. Click the **"New Note"** button
2. Enter a title (e.g., "My First Note")
3. Enter some content (e.g., "This is my first note in the AI Knowledge Vault!")
4. Optionally add tags (e.g., "test, first")
5. Optionally add a category (e.g., "Personal")
6. Click **"Create Note"**

## Testing Semantic Search

1. Create a few notes with different topics
2. Use the search box to search using natural language
3. Try queries like:
   - "ideas about productivity"
   - "notes on machine learning"
   - "work related tasks"
4. Notice how results are ranked by semantic similarity, not just keyword matching!

## Troubleshooting

### Backend won't start
- Make sure Python 3.8+ is installed
- Check that port 8000 is not in use
- Try: `pip install --upgrade pip` then reinstall requirements

### Frontend won't start
- Make sure Node.js 16+ is installed
- Delete `node_modules` folder and run `npm install` again
- Check that port 3000 is not in use

### Models won't download
- Check your internet connection
- Some corporate firewalls may block model downloads
- Try downloading models manually from Hugging Face

### CORS errors
- Make sure backend is running on port 8000
- Make sure frontend is running on port 3000
- Check browser console for specific error messages

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Explore the API at http://localhost:8000/docs
- Try creating notes with different categories and tags
- Experiment with semantic search queries
- Generate summaries of your longer notes

Enjoy your AI-powered knowledge vault! 🚀

