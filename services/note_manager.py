"""Note Manager Service"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from .vector_store import VectorStore
from .summarizer import Summarizer

class NoteManager:
    """Manages notes with full CRUD operations and semantic search"""
    
    def __init__(self, vector_store: VectorStore, summarizer: Summarizer):
        """Initialize note manager with dependencies"""
        self.vector_store = vector_store
        self.summarizer = summarizer
        # Track last indexing error to communicate to callers
        self._last_indexing_error: Optional[Exception] = None
        
        # Storage directory for notes metadata
        self.storage_dir = Path(__file__).parent.parent / "data" / "notes"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Notes index file
        self.index_file = self.storage_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        """Load notes index from disk"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.index = json.load(f)
            except Exception:
                self.index = {}
        else:
            self.index = {}
    
    def _save_index(self):
        """Save notes index to disk"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving index: {e}")
    
    def _save_note_file(self, note_id: str, note_data: Dict):
        """Save individual note to file"""
        note_file = self.storage_dir / f"{note_id}.json"
        try:
            with open(note_file, 'w', encoding='utf-8') as f:
                json.dump(note_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving note {note_id}: {e}")
    
    def _load_note_file(self, note_id: str) -> Optional[Dict]:
        """Load individual note from file"""
        note_file = self.storage_dir / f"{note_id}.json"
        if note_file.exists():
            try:
                with open(note_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    def create_note(
        self,
        title: str,
        content: str,
        tags: List[str] = None,
        category: str = None
    ) -> str:
        """Create a new note"""
        note_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        note_data = {
            "id": note_id,
            "title": title,
            "content": content,
            "tags": tags or [],
            "category": category,
            "created_at": now,
            "updated_at": now
        }
        
        self._save_note_file(note_id, note_data)
        self.index[note_id] = {
            "title": title,
            "created_at": now,
            "updated_at": now,
            "category": category,
            "tags": tags or []
        }
        self._save_index()
        
        searchable_text = f"{title}\n{content}"
        metadata = {
            "note_id": note_id,
            "title": title,
            "category": category or "",
            "tags": ",".join(tags or [])
        }
        try:
            self.vector_store.add_document(note_id, searchable_text, metadata)
            self._last_indexing_error = None
        except Exception as e:
            # Don't fail note creation if embedding/indexing isn't available.
            self._last_indexing_error = e
            print(f"Indexing failed for note {note_id}: {e}")
        
        return note_id
    
    def get_note(self, note_id: str) -> Optional[Dict]:
        """Get a note by ID"""
        return self._load_note_file(note_id)
    
    def get_all_notes(self) -> List[Dict]:
        """Get all notes"""
        notes = []
        for note_id in self.index.keys():
            note = self._load_note_file(note_id)
            if note:
                notes.append(note)
        
        notes.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return notes
    
    def update_note(self, note_id: str, updates: Dict) -> bool:
        """Update an existing note"""
        note = self._load_note_file(note_id)
        if not note:
            return False
        
        # Update fields
        if "title" in updates:
            note["title"] = updates["title"]
        if "content" in updates:
            note["content"] = updates["content"]
        if "tags" in updates:
            note["tags"] = updates["tags"]
        if "category" in updates:
            note["category"] = updates["category"]
        
        note["updated_at"] = datetime.utcnow().isoformat()
        
        self._save_note_file(note_id, note)
        
        if note_id in self.index:
            self.index[note_id].update({
                "title": note["title"],
                "updated_at": note["updated_at"],
                "category": note.get("category"),
                "tags": note.get("tags", [])
            })
            self._save_index()
        
        searchable_text = f"{note['title']}\n{note['content']}"
        metadata = {
            "note_id": note_id,
            "title": note["title"],
            "category": note.get("category") or "",
            "tags": ",".join(note.get("tags", []))
        }
        try:
            self.vector_store.update_document(note_id, searchable_text, metadata)
            self._last_indexing_error = None
        except Exception as e:
            self._last_indexing_error = e
            print(f"Index update failed for note {note_id}: {e}")
        
        return True
    
    def delete_note(self, note_id: str) -> bool:
        """Delete a note"""
        if note_id not in self.index:
            return False
        
        # Delete note file
        note_file = self.storage_dir / f"{note_id}.json"
        if note_file.exists():
            note_file.unlink()
        
        # Remove from index
        del self.index[note_id]
        self._save_index()
        
        # Remove from vector store
        self.vector_store.delete_document(note_id)
        
        return True
    
    def semantic_search(self, query: str, limit: int = 10) -> List[Dict]:
        """Perform semantic search across notes with enhanced error handling.
        
        Args:
            query: The search query string
            limit: Maximum number of results to return
            
        Returns:
            List of dictionaries containing note information and relevance scores
        """
        if not query or not query.strip():
            return []
            
        try:
            # Try vector search first
            vector_results = self.vector_store.search(query, limit=limit)
            
            if not vector_results:
                return self._fallback_text_search(query, limit)
                
            enriched_results = []
            seen_note_ids = set()
            
            for result in vector_results:
                try:
                    note_id = result.get('note_id')
                    if not note_id or note_id in seen_note_ids:
                        continue
                                
                    note = self.get_note(note_id)
                    if note:
                        enriched_result = {
                            'id': note_id,
                            'title': note.get('title', 'Untitled'),
                            'content': note.get('content', ''),
                            'similarity': float(result.get('similarity', 0.0)),
                            'score': float(result.get('distance', 0.0)),
                            'metadata': result.get('metadata', {}),
                            'snippet': self._generate_snippet(note.get('content', ''), query),
                            'tags': note.get('tags', []),
                            'category': note.get('category')
                        }
                        enriched_results.append(enriched_result)
                        seen_note_ids.add(note_id)
                        
                        if len(enriched_results) >= limit:
                            break
                except Exception as e:
                    print(f"Error processing search result: {e}")
                    continue
                            
            return enriched_results
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            # Fall back to basic text search if vector search fails
            return self._fallback_text_search(query, limit)
            
    def _fallback_text_search(self, query: str, limit: int) -> List[Dict]:
        """Fallback to basic text search when vector search is not available."""
        query = query.lower().strip()
        results = []
        
        for note_id, note_info in self.index.items():
            try:
                note = self.get_note(note_id)
                if not note:
                    continue
                    
                content = f"{note.get('title', '')} {note.get('content', '')}".lower()
                if query in content:
                    results.append({
                        'id': note_id,
                        'title': note.get('title', 'Untitled'),
                        'content': note.get('content', ''),
                        'similarity': 0.5,  # Default similarity for text search
                        'score': 1.0,  # Default score for text search
                        'metadata': {},
                        'snippet': self._generate_snippet(note.get('content', ''), query),
                        'tags': note.get('tags', []),
                        'category': note.get('category')
                    })
                    
                    if len(results) >= limit:
                        break
            except Exception as e:
                print(f"Error in fallback text search for note {note_id}: {e}")
                continue
                
        return results
        
    def _generate_snippet(self, content: str, query: str, max_length: int = 200) -> str:
        """Generate a text snippet around the query match."""
        if not content or not query:
            return content[:max_length] if content else ""
            
        query = query.lower()
        content_lower = content.lower()
        pos = content_lower.find(query)
        
        if pos == -1:
            return content[:max_length] + ("..." if len(content) > max_length else "")
            
        # Get some context around the match
        start = max(0, pos - max_length // 2)
        end = min(len(content), pos + len(query) + max_length // 2)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
            
        return snippet
    
    def get_stats(self) -> Dict:
        """Get statistics about notes."""
        stats = {
            'total_notes': len(self.index),
            'categories': {},
            'tags': {}
        }
        
        for note_info in self.index.values():
            # Count categories
            category = note_info.get('category')
            if category:
                stats['categories'][category] = stats['categories'].get(category, 0) + 1
                
            # Count tags
            for tag in note_info.get('tags', []):
                stats['tags'][tag] = stats['tags'].get(tag, 0) + 1
                
        return stats
    
    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        categories = set()
        for note_info in self.index.values():
            category = note_info.get("category")
            if category:
                categories.add(category)
        return sorted(list(categories))
    
    def get_tags(self) -> List[str]:
        """Get all unique tags"""
        tags = set()
        for note_info in self.index.values():
            for tag in note_info.get("tags", []):
                tags.add(tag)
        return sorted(list(tags))

