interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  selectedTag: string | null;
  onClearTag: () => void;
}

export function SearchBar({ value, onChange, selectedTag, onClearTag }: SearchBarProps) {
  return (
    <div className="search-bar-wrapper">
      <div className="search-input-wrap">
        <span className="search-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
        </span>
        <input
          type="text"
          placeholder="Search bookmarks…"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="search-input"
        />
        {value && (
          <button className="search-clear" onClick={() => onChange('')} title="Clear search">
            ×
          </button>
        )}
      </div>

      {selectedTag && (
        <div className="active-filter">
          <span className="active-filter-label">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <path d="M21.41 11.58L12.41 2.58A2 2 0 0 0 11 2H4a2 2 0 0 0-2 2v7a2 2 0 0 0 .59 1.42l9 9a2 2 0 0 0 2.82 0l7-7a2 2 0 0 0 0-2.84z"/>
            </svg>
            #{selectedTag}
          </span>
          <button className="active-filter-clear" onClick={onClearTag}>
            Clear filter
          </button>
        </div>
      )}
    </div>
  );
}
