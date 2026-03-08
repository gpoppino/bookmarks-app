import { useState } from 'react';
import type { Bookmark } from '../types';

interface BookmarkCardProps {
  bookmark: Bookmark;
  onDelete: (id: number) => void;
  onUpdate: (id: number, payload: { url?: string; tags?: string[] }) => Promise<void>;
  onTagClick: (tag: string) => void;
}

export function BookmarkCard({ bookmark, onDelete, onUpdate, onTagClick }: BookmarkCardProps) {
  const [editing, setEditing] = useState(false);
  const [editUrl, setEditUrl] = useState(bookmark.url);
  const [editTags, setEditTags] = useState(bookmark.tags.join(', '));
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const domain = (() => {
    try { return new URL(bookmark.url).hostname.replace('www.', ''); }
    catch { return bookmark.url; }
  })();

  const handleEdit = () => {
    setEditUrl(bookmark.url);
    setEditTags(bookmark.tags.join(', '));
    setEditError(null);
    setEditing(true);
  };

  const handleCancel = () => {
    setEditing(false);
    setEditError(null);
  };

  const handleSave = async () => {
    const newUrl = editUrl.trim();
    const newTags = editTags.split(',').map((t) => t.trim()).filter(Boolean);
    const payload: { url?: string; tags?: string[] } = {};
    if (newUrl !== bookmark.url) payload.url = newUrl;
    if (JSON.stringify(newTags) !== JSON.stringify(bookmark.tags)) payload.tags = newTags;
    if (Object.keys(payload).length === 0) { setEditing(false); return; }

    setSaving(true);
    setEditError(null);
    try {
      await onUpdate(bookmark.id, payload);
      setEditing(false);
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <article className="bookmark-card">
      <div className="card-header">
        <div className="card-domain">
          <img
            src={`https://www.google.com/s2/favicons?sz=32&domain=${domain}`}
            alt=""
            className="card-favicon"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
          <span>{domain}</span>
        </div>
        <div className="card-actions">
          <button
            onClick={handleEdit}
            className="card-edit"
            title="Edit bookmark"
            aria-label="Edit bookmark"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button
            onClick={() => onDelete(bookmark.id)}
            className="card-delete"
            title="Delete bookmark"
            aria-label="Delete bookmark"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6 6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
      </div>

      {editing ? (
        <div className="card-edit-form">
          <div className="input-group">
            <label className="input-label">URL</label>
            <input
              className="input-field"
              value={editUrl}
              onChange={(e) => setEditUrl(e.target.value)}
              placeholder="https://..."
              disabled={saving}
            />
          </div>
          <div className="input-group">
            <label className="input-label">Tags</label>
            <input
              className="input-field"
              value={editTags}
              onChange={(e) => setEditTags(e.target.value)}
              placeholder="tag1, tag2"
              disabled={saving}
            />
          </div>
          {editError && <p className="form-error">{editError}</p>}
          <div className="card-edit-actions">
            <button className="btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? <span className="btn-loading"><span className="spinner" />Saving…</span> : 'Save'}
            </button>
            <button className="btn-secondary" onClick={handleCancel} disabled={saving}>Cancel</button>
          </div>
        </div>
      ) : (
        <>
          <a href={bookmark.url} target="_blank" rel="noopener noreferrer" className="card-title">
            {bookmark.title}
          </a>

          {bookmark.description && bookmark.description !== 'No description available' && (
            <p className="card-description">{bookmark.description}</p>
          )}

          <div className="card-footer">
            <div className="card-tags">
              {bookmark.tags.map((tag) => (
                <button key={tag} className="tag-pill" onClick={() => onTagClick(tag)}>
                  #{tag}
                </button>
              ))}
            </div>
            <time className="card-date" dateTime={bookmark.created_at}>
              {new Date(bookmark.created_at).toLocaleDateString(undefined, {
                month: 'short', day: 'numeric', year: 'numeric'
              })}
            </time>
          </div>
        </>
      )}
    </article>
  );
}
