# Bookmark App — Client

A React + TypeScript frontend for the bookmarking application.

## Stack

- **React 18** — UI library
- **TypeScript** — Type safety
- **Vite** — Build tool & dev server

## Setup

```bash
# 1. Install dependencies
npm install

# 2. Copy the environment file
cp .env.example .env.local

# 3. Start the dev server
npm run dev
```

The app will be running at **http://localhost:3000**

> Make sure the Python backend is running at `http://127.0.0.1:8000` first.

## Project Structure

```
src/
├── api/
│   └── client.ts          # All API calls to the backend (single source of truth)
├── components/
│   ├── AddBookmarkForm.tsx # Form to submit new bookmarks
│   ├── BookmarkCard.tsx    # Individual bookmark card with tags & delete
│   ├── BookmarkGallery.tsx # Grid of bookmark cards + loading/empty states
│   └── SearchBar.tsx       # Search input + active tag filter indicator
├── hooks/
│   └── useBookmarks.ts    # Data fetching hook with debounced search
├── types/
│   └── index.ts           # Shared TypeScript interfaces
├── App.tsx                # Root dashboard component (state lives here)
├── main.tsx               # Entry point
└── index.css              # Global styles & design tokens
```

## Features

- **Add bookmarks** — paste any URL; title and description are auto-fetched from the page
- **Tags** — add comma-separated tags when saving a bookmark
- **Search** — debounced live search across title, description, and URL (server-side)
- **Tag filter** — click any tag pill to filter the gallery by that tag
- **Delete** — optimistic UI deletion with server sync
- **Skeleton loading** — polished loading state while fetching

## Environment Variables

| Variable       | Default                   | Description              |
|----------------|---------------------------|--------------------------|
| `VITE_API_URL` | `http://127.0.0.1:8000`   | Base URL for the backend |

## Build for Production

```bash
npm run build
```

Output will be in the `dist/` folder.
