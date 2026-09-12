// @vitest-environment jsdom

import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../src/api/client';
import { BOOKMARKS_PAGE_SIZE, useBookmarks } from '../src/hooks/useBookmarks';
import type { Bookmark } from '../src/types';

vi.mock('../src/api/client', () => ({
  api: {
    getBookmarks: vi.fn(),
  },
}));

const getBookmarks = vi.mocked(api.getBookmarks);

function bookmark(id: number): Bookmark {
  return {
    id,
    url: `https://example.com/${id}`,
    title: `Bookmark ${id}`,
    description: '',
    created_at: '2026-09-12T00:00:00Z',
    tags: [],
  };
}

describe('useBookmarks pagination', () => {
  beforeEach(() => {
    getBookmarks.mockReset();
  });

  it('requests one extra bookmark and advances with the correct offset', async () => {
    getBookmarks
      .mockResolvedValueOnce(Array.from({ length: BOOKMARKS_PAGE_SIZE + 1 }, (_, index) => bookmark(index + 1)))
      .mockResolvedValueOnce([bookmark(25), bookmark(26)]);

    const { result } = renderHook(() => useBookmarks({ search: '', selectedTag: null }));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(getBookmarks).toHaveBeenLastCalledWith({
      search: undefined,
      tag: undefined,
      skip: 0,
      limit: BOOKMARKS_PAGE_SIZE + 1,
    });
    expect(result.current.bookmarks).toHaveLength(BOOKMARKS_PAGE_SIZE);
    expect(result.current.hasNextPage).toBe(true);

    act(() => result.current.nextPage());

    await waitFor(() => expect(result.current.page).toBe(1));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(getBookmarks).toHaveBeenLastCalledWith({
      search: undefined,
      tag: undefined,
      skip: BOOKMARKS_PAGE_SIZE,
      limit: BOOKMARKS_PAGE_SIZE + 1,
    });
    expect(result.current.bookmarks.map(({ id }) => id)).toEqual([25, 26]);
    expect(result.current.hasPreviousPage).toBe(true);
    expect(result.current.hasNextPage).toBe(false);
  });

  it('returns to the first page when the tag filter changes', async () => {
    getBookmarks
      .mockResolvedValueOnce(Array.from({ length: BOOKMARKS_PAGE_SIZE + 1 }, (_, index) => bookmark(index + 1)))
      .mockResolvedValueOnce([bookmark(25)])
      .mockResolvedValueOnce([bookmark(7)]);

    const { result, rerender } = renderHook(
      ({ selectedTag }: { selectedTag: string | null }) => useBookmarks({ search: '', selectedTag }),
      { initialProps: { selectedTag: null } },
    );

    await waitFor(() => expect(result.current.hasNextPage).toBe(true));
    act(() => result.current.nextPage());
    await waitFor(() => expect(result.current.page).toBe(1));
    await waitFor(() => expect(result.current.loading).toBe(false));

    rerender({ selectedTag: 'typescript' });

    await waitFor(() => expect(result.current.page).toBe(0));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(getBookmarks).toHaveBeenLastCalledWith({
      search: undefined,
      tag: 'typescript',
      skip: 0,
      limit: BOOKMARKS_PAGE_SIZE + 1,
    });
    expect(result.current.bookmarks.map(({ id }) => id)).toEqual([7]);
  });

  it('keeps previous-page navigation available after a later page fails', async () => {
    getBookmarks
      .mockResolvedValueOnce(Array.from({ length: BOOKMARKS_PAGE_SIZE + 1 }, (_, index) => bookmark(index + 1)))
      .mockRejectedValueOnce(new Error('Page failed'))
      .mockResolvedValueOnce([bookmark(1)]);

    const { result } = renderHook(() => useBookmarks({ search: '', selectedTag: null }));

    await waitFor(() => expect(result.current.hasNextPage).toBe(true));
    act(() => result.current.nextPage());
    await waitFor(() => expect(result.current.error).toBe('Page failed'));
    expect(result.current.page).toBe(1);
    expect(result.current.hasPreviousPage).toBe(true);

    act(() => result.current.previousPage());
    await waitFor(() => expect(result.current.page).toBe(0));
    await waitFor(() => expect(result.current.error).toBeNull());
  });

  it('returns to the previous page when the current page becomes empty', async () => {
    getBookmarks
      .mockResolvedValueOnce(Array.from({ length: BOOKMARKS_PAGE_SIZE + 1 }, (_, index) => bookmark(index + 1)))
      .mockResolvedValueOnce([bookmark(25)])
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([bookmark(1)]);

    const { result } = renderHook(() => useBookmarks({ search: '', selectedTag: null }));

    await waitFor(() => expect(result.current.hasNextPage).toBe(true));
    act(() => result.current.nextPage());
    await waitFor(() => expect(result.current.page).toBe(1));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => result.current.refetch());

    await waitFor(() => expect(result.current.page).toBe(0));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.bookmarks.map(({ id }) => id)).toEqual([1]);
  });
});
