import { useState } from 'react';
import { api } from '../api/client';
import type { Bookmark } from '../types';

interface AddBookmarkFormProps {
  onBookmarkAdded: (bookmark: Bookmark) => void;
}

export function AddBookmarkForm({ onBookmarkAdded }: AddBookmarkFormProps) {
  const [url, setUrl] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    try {
      const bookmark = await api.createBookmark({ url, tags });
      onBookmarkAdded(bookmark);
      setUrl('');
      setTagsInput('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save bookmark');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-card">
      <h2 className="form-title">
        <span className="form-icon">+</span> Add Bookmark
      </h2>
      <form onSubmit={handleSubmit} className="form-body">
        <div className="input-group">
          <label className="input-label">URL</label>
          <input
            type="url"
            required
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="input-field"
          />
        </div>
        <div className="input-group">
          <label className="input-label">Tags</label>
          <input
            type="text"
            placeholder="python, tutorial, api"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            className="input-field"
          />
          <span className="input-hint">Separate tags with commas</span>
        </div>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? (
            <span className="btn-loading">
              <span className="spinner" /> Fetching…
            </span>
          ) : (
            'Save Bookmark'
          )}
        </button>
      </form>
    </div>
  );
}
