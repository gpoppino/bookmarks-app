import type { Bookmark, CreateBookmarkPayload, Tag, User } from '../types';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    ...init,
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail ?? 'An unknown error occurred');
  }

  return data as T;
}

export const api = {
  getBookmarks(params?: {
    search?: string;
    tag?: string;
    skip?: number;
    limit?: number;
  }): Promise<Bookmark[]> {
    const qs = new URLSearchParams();
    if (params?.search) qs.set('search', params.search);
    if (params?.tag)    qs.set('tag', params.tag);
    if (params?.skip !== undefined) qs.set('skip', String(params.skip));
    if (params?.limit !== undefined) qs.set('limit', String(params.limit));
    const query = qs.toString() ? `?${qs.toString()}` : '';
    return request<Bookmark[]>(`/api/bookmarks${query}`);
  },

  createBookmark(payload: CreateBookmarkPayload): Promise<Bookmark> {
    return request<Bookmark>('/api/bookmarks', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateBookmark(id: number, payload: { url?: string; tags?: string[] }): Promise<Bookmark> {
    return request<Bookmark>(`/api/bookmarks/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  deleteBookmark(id: number): Promise<{ success: boolean; message: string }> {
    return request(`/api/bookmarks/${id}`, { method: 'DELETE' });
  },

  getTags(): Promise<Tag[]> {
    return request<Tag[]>('/api/tags');
  },

  register(payload: { username: string; password: string }): Promise<User> {
    return request<User>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  login(payload: { username: string; password: string }): Promise<User> {
    return request<User>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  logout(): Promise<{ success: boolean }> {
    return request('/api/auth/logout', { method: 'POST' });
  },

  me(): Promise<User> {
    return request<User>('/api/auth/me');
  },

  changePassword(currentPassword: string, newPassword: string): Promise<{ message: string }> {
    return request<{ message: string }>('/api/auth/password', {
      method: 'PUT',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  },
};
