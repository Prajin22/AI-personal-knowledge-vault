import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Search, Plus, FileText, Tag, Folder, Trash2, Edit2, Sparkles, X } from 'lucide-react'
import './App.css'

const API_BASE = '/api'

function App() {
  const [notes, setNotes] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [editingNote, setEditingNote] = useState(null)
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    tags: '',
    category: ''
  })
  const [stats, setStats] = useState(null)
  const [activeTab, setActiveTab] = useState('notes')

  useEffect(() => {
    loadNotes()
    loadStats()
  }, [])

  const loadNotes = async () => {
    try {
      const response = await axios.get(`${API_BASE}/notes`)
      if (response.data.success) {
        setNotes(response.data.notes)
      }
    } catch (error) {
      console.error('Error loading notes:', error)
    }
  }

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/stats`)
      if (response.data.success) {
        setStats(response.data.stats)
      }
    } catch (error) {
      console.error('Error loading stats:', error)
    }
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) {
      setSearchResults([])
      setIsSearching(false)
      return
    }

    setIsSearching(true)
    try {
      const response = await axios.post(`${API_BASE}/search`, {
        query: searchQuery,
        limit: 20
      })
      if (response.data.success) {
        setSearchResults(response.data.results)
      }
    } catch (error) {
      console.error('Error searching:', error)
    } finally {
      setIsSearching(false)
    }
  }

  const handleCreateNote = () => {
    setEditingNote(null)
    setFormData({
      title: '',
      content: '',
      tags: '',
      category: ''
    })
    setShowModal(true)
  }

  const handleEditNote = (note) => {
    setEditingNote(note)
    setFormData({
      title: note.title,
      content: note.content,
      tags: note.tags.join(', '),
      category: note.category || ''
    })
    setShowModal(true)
  }

  const handleSaveNote = async (e) => {
    e.preventDefault()
    try {
      const tagsArray = formData.tags
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0)

      if (editingNote) {
        await axios.put(`${API_BASE}/notes/${editingNote.id}`, {
          title: formData.title,
          content: formData.content,
          tags: tagsArray,
          category: formData.category || null
        })
      } else {
        await axios.post(`${API_BASE}/notes`, {
          title: formData.title,
          content: formData.content,
          tags: tagsArray,
          category: formData.category || null
        })
      }
      setShowModal(false)
      loadNotes()
      loadStats()
    } catch (error) {
      console.error('Error saving note:', error)
      alert('Error saving note. Please try again.')
    }
  }

  const handleDeleteNote = async (noteId) => {
    if (!window.confirm('Are you sure you want to delete this note?')) {
      return
    }
    try {
      await axios.delete(`${API_BASE}/notes/${noteId}`)
      loadNotes()
      loadStats()
      if (searchResults.length > 0) {
        setSearchResults(searchResults.filter(note => note.id !== noteId))
      }
    } catch (error) {
      console.error('Error deleting note:', error)
    }
  }

  const handleSummarize = async (note) => {
    try {
      const response = await axios.post(`${API_BASE}/summarize`, {
        note_id: note.id,
        max_length: 200
      })
      if (response.data.success) {
        alert(`Summary:\n\n${response.data.summary}`)
      }
    } catch (error) {
      console.error('Error summarizing:', error)
      alert('Error generating summary. Please try again.')
    }
  }

  const displayNotes = searchQuery.trim() && searchResults.length > 0 ? searchResults : notes

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <Sparkles className="logo-icon" />
            <h1>AI Knowledge Vault</h1>
          </div>
          <div className="header-actions">
            <button className="btn btn-primary" onClick={handleCreateNote}>
              <Plus size={18} />
              New Note
            </button>
          </div>
        </div>
      </header>

      <div className="container">
        <div className="sidebar">
          <nav className="nav">
            <button
              className={`nav-item ${activeTab === 'notes' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('notes')
                setSearchQuery('')
                setSearchResults([])
              }}
            >
              <FileText size={18} />
              All Notes
            </button>
            <button
              className={`nav-item ${activeTab === 'stats' ? 'active' : ''}`}
              onClick={() => setActiveTab('stats')}
            >
              <Folder size={18} />
              Statistics
            </button>
          </nav>

          <div className="search-section">
            <form onSubmit={handleSearch} className="search-form">
              <div className="search-input-wrapper">
                <Search className="search-icon" size={20} />
                <input
                  type="text"
                  className="search-input"
                  placeholder="Search notes semantically..."
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    if (!e.target.value.trim()) {
                      setSearchResults([])
                    }
                  }}
                />
              </div>
              <button type="submit" className="btn btn-search" disabled={isSearching}>
                {isSearching ? 'Searching...' : 'Search'}
              </button>
            </form>
          </div>

          {stats && (
            <div className="stats-preview">
              <h3>Quick Stats</h3>
              <div className="stat-item">
                <span className="stat-label">Total Notes:</span>
                <span className="stat-value">{stats.total_notes}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Categories:</span>
                <span className="stat-value">{Object.keys(stats.categories).length}</span>
              </div>
            </div>
          )}
        </div>

        <main className="main-content">
          {activeTab === 'notes' && (
            <div className="notes-section">
              <div className="section-header">
                <h2>
                  {searchQuery.trim() && searchResults.length > 0
                    ? `Search Results (${searchResults.length})`
                    : `All Notes (${notes.length})`}
                </h2>
              </div>

              {displayNotes.length === 0 ? (
                <div className="empty-state">
                  <FileText size={48} />
                  <p>No notes found. Create your first note to get started!</p>
                </div>
              ) : (
                <div className="notes-grid">
                  {displayNotes.map((note) => (
                    <div key={note.id} className="note-card">
                      <div className="note-header">
                        <h3 className="note-title">{note.title}</h3>
                        <div className="note-actions">
                          <button
                            className="icon-btn"
                            onClick={() => handleSummarize(note)}
                            title="Summarize"
                          >
                            <Sparkles size={16} />
                          </button>
                          <button
                            className="icon-btn"
                            onClick={() => handleEditNote(note)}
                            title="Edit"
                          >
                            <Edit2 size={16} />
                          </button>
                          <button
                            className="icon-btn danger"
                            onClick={() => handleDeleteNote(note.id)}
                            title="Delete"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                      <p className="note-content">
                        {note.content.length > 200
                          ? note.content.substring(0, 200) + '...'
                          : note.content}
                      </p>
                      <div className="note-footer">
                        {note.category && (
                          <span className="note-category">
                            <Folder size={14} />
                            {note.category}
                          </span>
                        )}
                        {note.tags && note.tags.length > 0 && (
                          <div className="note-tags">
                            {note.tags.map((tag, idx) => (
                              <span key={idx} className="tag">
                                <Tag size={12} />
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                        {note.similarity !== undefined && (
                          <span className="similarity-score">
                            {(note.similarity * 100).toFixed(0)}% match
                          </span>
                        )}
                      </div>
                      <div className="note-date">
                        {new Date(note.updated_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'stats' && stats && (
            <div className="stats-section">
              <h2>Knowledge Vault Statistics</h2>
              <div className="stats-grid">
                <div className="stat-card">
                  <h3>Total Notes</h3>
                  <p className="stat-number">{stats.total_notes}</p>
                </div>
                <div className="stat-card">
                  <h3>Categories</h3>
                  <p className="stat-number">{Object.keys(stats.categories).length}</p>
                </div>
                <div className="stat-card">
                  <h3>Total Tags</h3>
                  <p className="stat-number">{stats.total_tags}</p>
                </div>
              </div>

              {Object.keys(stats.categories).length > 0 && (
                <div className="category-breakdown">
                  <h3>Notes by Category</h3>
                  <div className="category-list">
                    {Object.entries(stats.categories).map(([category, count]) => (
                      <div key={category} className="category-item">
                        <span className="category-name">{category}</span>
                        <span className="category-count">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {stats.top_tags && Object.keys(stats.top_tags).length > 0 && (
                <div className="tags-breakdown">
                  <h3>Top Tags</h3>
                  <div className="tags-list">
                    {Object.entries(stats.top_tags).map(([tag, count]) => (
                      <span key={tag} className="tag-stat">
                        {tag} ({count})
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingNote ? 'Edit Note' : 'Create New Note'}</h2>
              <button className="icon-btn" onClick={() => setShowModal(false)}>
                <X size={20} />
              </button>
            </div>
            <form onSubmit={handleSaveNote} className="note-form">
              <div className="form-group">
                <label>Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  required
                  placeholder="Enter note title..."
                />
              </div>
              <div className="form-group">
                <label>Content</label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                  required
                  rows={10}
                  placeholder="Enter note content..."
                />
              </div>
              <div className="form-group">
                <label>Tags (comma-separated)</label>
                <input
                  type="text"
                  value={formData.tags}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                  placeholder="e.g., work, ideas, todo"
                />
              </div>
              <div className="form-group">
                <label>Category</label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  placeholder="e.g., Work, Personal, Research"
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingNote ? 'Update' : 'Create'} Note
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default App

