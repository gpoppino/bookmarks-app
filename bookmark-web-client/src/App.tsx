import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AddBookmarkForm } from './components/AddBookmarkForm';
import { BookmarkGallery } from './components/BookmarkGallery';
import { SearchBar } from './components/SearchBar';
import { useBookmarks } from './hooks/useBookmarks';
import { useAuth } from './context/AuthContext';
import { api } from './api/client';
import type { Bookmark } from './types';

export default function App() {
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const { bookmarks, loading, error, addBookmark, removeBookmark, replaceBookmark } = useBookmarks({
    search,
    selectedTag,
  });

  const handleDelete = async (id: number) => {
    removeBookmark(id); // Optimistic update
    try {
      await api.deleteBookmark(id);
    } catch (err) {
      console.error('Failed to delete bookmark on server:', err);
    }
  };

  const handleUpdate = async (id: number, payload: { url?: string; tags?: string[] }) => {
    const updated = await api.updateBookmark(id, payload);
    replaceBookmark(updated);
  };

  const handleBookmarkAdded = (bookmark: Bookmark) => {
    addBookmark(bookmark);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-mark">◈</span>
            <span className="logo-text">Marks</span>
          </div>
          <p className="header-sub">Your personal bookmark collection</p>
          <div className="header-user">
            <span className="header-username">{user?.username}</span>
            <button className="btn-secondary" onClick={() => navigate('/change-password')}>Change password</button>
            <button className="btn-logout" onClick={handleLogout}>Sign out</button>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="sidebar">
          <AddBookmarkForm onBookmarkAdded={handleBookmarkAdded} />
        </div>

        <div className="content">
          <div className="content-toolbar">
            <SearchBar
              value={search}
              onChange={setSearch}
              selectedTag={selectedTag}
              onClearTag={() => setSelectedTag(null)}
            />
            <span className="bookmark-count">
              {!loading && `${bookmarks.length} bookmark${bookmarks.length !== 1 ? 's' : ''}`}
            </span>
          </div>

          <BookmarkGallery
            bookmarks={bookmarks}
            loading={loading}
            error={error}
            onDelete={handleDelete}
            onUpdate={handleUpdate}
            onTagClick={(tag) => {
              setSelectedTag(tag);
              setSearch('');
            }}
          />
        </div>
      </main>
    </div>
  );
}
