import { BookmarkCard } from './BookmarkCard';
import type { Bookmark } from '../types';

interface BookmarkGalleryProps {
  bookmarks: Bookmark[];
  loading: boolean;
  error: string | null;
  onDelete: (id: number) => void;
  onTagClick: (tag: string) => void;
}

export function BookmarkGallery({
  bookmarks,
  loading,
  error,
  onDelete,
  onTagClick,
}: BookmarkGalleryProps) {
  if (loading) {
    return (
      <div className="gallery-state">
        <div className="skeleton-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton-card">
              <div className="skeleton-line short" />
              <div className="skeleton-line" />
              <div className="skeleton-line" />
              <div className="skeleton-line medium" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="gallery-state gallery-error">
        <span className="state-icon">⚠</span>
        <p>{error}</p>
      </div>
    );
  }

  if (bookmarks.length === 0) {
    return (
      <div className="gallery-state gallery-empty">
        <span className="state-icon">◎</span>
        <p>No bookmarks yet. Add one above!</p>
      </div>
    );
  }

  return (
    <div className="bookmark-grid">
      {bookmarks.map((bookmark) => (
        <BookmarkCard
          key={bookmark.id}
          bookmark={bookmark}
          onDelete={onDelete}
          onTagClick={onTagClick}
        />
      ))}
    </div>
  );
}
