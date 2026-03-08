export interface Bookmark {
  id: number;
  url: string;
  title: string;
  description: string;
  created_at: string;
  tags: string[];
}

export interface Tag {
  id: number;
  name: string;
}

export interface CreateBookmarkPayload {
  url: string;
  tags: string[];
}

export interface ApiError {
  detail: string;
}

export interface User {
  id: number;
  username: string;
  created_at: string;
}
