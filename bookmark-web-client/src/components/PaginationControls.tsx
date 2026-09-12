interface PaginationControlsProps {
  page: number;
  hasPreviousPage: boolean;
  hasNextPage: boolean;
  loading: boolean;
  onPrevious: () => void;
  onNext: () => void;
}

export function PaginationControls({
  page,
  hasPreviousPage,
  hasNextPage,
  loading,
  onPrevious,
  onNext,
}: PaginationControlsProps) {
  if (!hasPreviousPage && !hasNextPage) return null;

  return (
    <nav className="pagination" aria-label="Bookmark pagination">
      <button
        type="button"
        className="pagination-button"
        onClick={onPrevious}
        disabled={!hasPreviousPage || loading}
      >
        ← Previous
      </button>
      <span className="pagination-page" aria-current="page">
        Page {page + 1}
      </span>
      <button
        type="button"
        className="pagination-button"
        onClick={onNext}
        disabled={!hasNextPage || loading}
      >
        Next →
      </button>
    </nav>
  );
}
