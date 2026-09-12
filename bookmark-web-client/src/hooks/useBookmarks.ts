import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';
import type { Bookmark } from '../types';

interface UseBookmarksOptions {
  search: string;
  selectedTag: string | null;
}

export const BOOKMARKS_PAGE_SIZE = 24;

export function useBookmarks({ search, selectedTag }: UseBookmarksOptions) {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const requestId = useRef(0);

  const fetchBookmarks = useCallback(async () => {
    const activeRequest = ++requestId.current;
    setLoading(true);
    setError(null);
    setHasNextPage(false);
    try {
      const data = await api.getBookmarks({
        search: search || undefined,
        tag: selectedTag || undefined,
        skip: page * BOOKMARKS_PAGE_SIZE,
        limit: BOOKMARKS_PAGE_SIZE + 1,
      });
      if (activeRequest !== requestId.current) return;

      if (page > 0 && data.length === 0) {
        setPage((current) => Math.max(0, current - 1));
        return;
      }

      setBookmarks(data.slice(0, BOOKMARKS_PAGE_SIZE));
      setHasNextPage(data.length > BOOKMARKS_PAGE_SIZE);
    } catch (err: unknown) {
      if (activeRequest !== requestId.current) return;
      setError(err instanceof Error ? err.message : 'Failed to fetch bookmarks');
    } finally {
      if (activeRequest === requestId.current) setLoading(false);
    }
  }, [page, search, selectedTag]);

  useEffect(() => {
    setPage(0);
  }, [search, selectedTag]);

  useEffect(() => {
    const debounce = setTimeout(fetchBookmarks, search ? 300 : 0);
    return () => {
      clearTimeout(debounce);
      requestId.current += 1;
    };
  }, [fetchBookmarks, search]);

  const addBookmark = (newBookmark: Bookmark) => {
    if (page > 0) {
      setPage(0);
      return;
    }

    if (bookmarks.length === BOOKMARKS_PAGE_SIZE) setHasNextPage(true);
    setBookmarks((prev) => [newBookmark, ...prev].slice(0, BOOKMARKS_PAGE_SIZE));
  };

  const removeBookmark = (id: number) => {
    setBookmarks((prev) => prev.filter((b) => b.id !== id));
  };

  const replaceBookmark = (updated: Bookmark) => {
    setBookmarks((prev) => prev.map((b) => (b.id === updated.id ? updated : b)));
  };

  const previousPage = () => setPage((current) => Math.max(0, current - 1));
  const nextPage = () => {
    if (hasNextPage) setPage((current) => current + 1);
  };

  return {
    bookmarks,
    loading,
    error,
    page,
    hasPreviousPage: page > 0,
    hasNextPage,
    previousPage,
    nextPage,
    addBookmark,
    removeBookmark,
    replaceBookmark,
    refetch: fetchBookmarks,
  };
}
