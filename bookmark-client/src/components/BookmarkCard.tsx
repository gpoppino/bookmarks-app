import type { Bookmark } from '../types';

interface BookmarkCardProps {
  bookmark: Bookmark;
  onDelete: (id: number) => void;
  onTagClick: (tag: string) => void;
}

export function BookmarkCard({ bookmark, onDelete, onTagClick }: BookmarkCardProps) {
  const domain = (() => {
    try { return new URL(bookmark.url).hostname.replace('www.', ''); }
    catch { return bookmark.url; }
  })();

  const handleDelete = async () => {
    onDelete(bookmark.id);
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
        <button
          onClick={handleDelete}
          className="card-delete"
          title="Delete bookmark"
          aria-label="Delete bookmark"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 6 6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>

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
    </article>
  );
}
