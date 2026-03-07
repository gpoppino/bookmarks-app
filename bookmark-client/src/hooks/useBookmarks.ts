import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';
import type { Bookmark } from '../types';

interface UseBookmarksOptions {
  search: string;
  selectedTag: string | null;
}

export function useBookmarks({ search, selectedTag }: UseBookmarksOptions) {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBookmarks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getBookmarks({
        search: search || undefined,
        tag: selectedTag || undefined,
      });
      setBookmarks(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch bookmarks');
    } finally {
      setLoading(false);
    }
  }, [search, selectedTag]);

  useEffect(() => {
    const debounce = setTimeout(fetchBookmarks, search ? 300 : 0);
    return () => clearTimeout(debounce);
  }, [fetchBookmarks, search]);

  const addBookmark = (newBookmark: Bookmark) => {
    setBookmarks((prev) => [newBookmark, ...prev]);
  };

  const removeBookmark = (id: number) => {
    setBookmarks((prev) => prev.filter((b) => b.id !== id));
  };

  return { bookmarks, loading, error, addBookmark, removeBookmark, refetch: fetchBookmarks };
}
