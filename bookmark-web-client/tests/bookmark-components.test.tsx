// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../src/api/client';
import { AddBookmarkForm } from '../src/components/AddBookmarkForm';
import { BookmarkCard } from '../src/components/BookmarkCard';
import { BookmarkGallery } from '../src/components/BookmarkGallery';
import type { Bookmark } from '../src/types';

vi.mock('../src/api/client', () => ({
  api: {
    createBookmark: vi.fn(),
  },
}));

const bookmark: Bookmark = {
  id: 7,
  url: 'https://example.test/article',
  title: 'Example bookmark',
  description: 'Useful description',
  created_at: '2026-09-14T10:00:00Z',
  tags: ['react'],
};

describe('bookmark components', () => {
  afterEach(cleanup);

  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('adds a bookmark with trimmed tags and clears the form', async () => {
    vi.mocked(api.createBookmark).mockResolvedValue(bookmark);
    const onBookmarkAdded = vi.fn();
    render(<AddBookmarkForm onBookmarkAdded={onBookmarkAdded} />);
    const urlInput = screen.getByPlaceholderText('https://example.com') as HTMLInputElement;
    const tagsInput = screen.getByPlaceholderText('python, tutorial, api') as HTMLInputElement;

    fireEvent.change(urlInput, { target: { value: bookmark.url } });
    fireEvent.change(tagsInput, { target: { value: ' react, , testing ' } });
    fireEvent.click(screen.getByText('Save Bookmark'));

    await waitFor(() => expect(onBookmarkAdded).toHaveBeenCalledWith(bookmark));
    expect(api.createBookmark).toHaveBeenCalledWith({
      url: bookmark.url,
      tags: ['react', 'testing'],
    });
    expect(urlInput.value).toBe('');
    expect(tagsInput.value).toBe('');
  });

  it('shows API errors while adding a bookmark', async () => {
    vi.mocked(api.createBookmark).mockRejectedValue(new Error('Bookmark already exists'));
    render(<AddBookmarkForm onBookmarkAdded={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText('https://example.com'), {
      target: { value: bookmark.url },
    });
    fireEvent.click(screen.getByText('Save Bookmark'));

    await waitFor(() => {
      expect(screen.getByText('Bookmark already exists')).toBeTruthy();
    });
  });

  it('edits, deletes, and filters from a bookmark card', async () => {
    const onDelete = vi.fn();
    const onUpdate = vi.fn().mockResolvedValue(undefined);
    const onTagClick = vi.fn();
    render(
      <BookmarkCard
        bookmark={bookmark}
        onDelete={onDelete}
        onUpdate={onUpdate}
        onTagClick={onTagClick}
      />,
    );

    fireEvent.click(screen.getByText('#react'));
    expect(onTagClick).toHaveBeenCalledWith('react');
    fireEvent.click(screen.getByLabelText('Delete bookmark'));
    expect(onDelete).toHaveBeenCalledWith(7);

    fireEvent.click(screen.getByLabelText('Edit bookmark'));
    fireEvent.change(screen.getByPlaceholderText('https://...'), {
      target: { value: ' https://updated.test ' },
    });
    fireEvent.change(screen.getByPlaceholderText('tag1, tag2'), {
      target: { value: 'react, tests' },
    });
    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith(7, {
      url: 'https://updated.test',
      tags: ['react', 'tests'],
    }));
    await waitFor(() => expect(screen.queryByText('Save')).toBeNull());
  });

  it('renders loading, error, empty, and populated list states', () => {
    const props = { onDelete: vi.fn(), onUpdate: vi.fn(), onTagClick: vi.fn() };
    const { rerender } = render(
      <BookmarkGallery bookmarks={[]} loading error={null} {...props} />,
    );
    expect(document.querySelectorAll('.skeleton-card')).toHaveLength(6);

    rerender(<BookmarkGallery bookmarks={[]} loading={false} error="Load failed" {...props} />);
    expect(screen.getByText('Load failed')).toBeTruthy();

    rerender(<BookmarkGallery bookmarks={[]} loading={false} error={null} {...props} />);
    expect(screen.getByText('No bookmarks yet. Add one above!')).toBeTruthy();

    rerender(<BookmarkGallery bookmarks={[bookmark]} loading={false} error={null} {...props} />);
    expect(screen.getByText('Example bookmark')).toBeTruthy();
  });
});
