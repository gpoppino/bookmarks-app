# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

Full-stack bookmarking app with three independently runnable components:

- **`bookmark-backend/`** — Python FastAPI REST API with SQLAlchemy ORM and SQLite storage. All logic lives in a single file: `main.py`. The backend scrapes webpage metadata (title, description) using BeautifulSoup when a bookmark is created or its URL is updated.
- **`bookmark-web-client/`** — React 18 + TypeScript SPA built with Vite. All backend communication goes through `src/api/client.ts` (single source of truth). State lives in `App.tsx` and is fed by the `useBookmarks` hook, which debounces search queries before hitting the API.
- **`bookmark-cli-client/`** — Go CLI client built with Cobra. Covers all backend endpoints (register, login, logout, me, list, add, update, delete, tags). JWT session token stored at `~/.config/bookmarks-cli/session` (permissions `0600`).

### Data flow

`App.tsx` holds search/tag state → `useBookmarks` hook fetches/mutates → `api/client.ts` calls backend → FastAPI returns serialized bookmark objects with tags as string arrays.

Tags are normalized to lowercase on the backend. Tag filtering and full-text search (title, description, URL) are both server-side.

## Backend commands

```bash
cd bookmark-backend

# Setup (first time)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run dev server
uvicorn main:app --reload
```

API runs at `http://127.0.0.1:8000`. Swagger docs at `http://127.0.0.1:8000/docs`. SQLite DB (`bookmarks.db`) is auto-created on first run.

## Frontend commands

```bash
cd bookmark-web-client

# Setup (first time)
npm install
cp .env.example .env.local

# Dev server
npm run dev

# Type-check + build
npm run build

# Lint
npm run lint
```

App runs at `http://localhost:3000`. Requires the backend to be running first.

## CLI commands

```bash
cd bookmark-cli-client

# Build
go build -o bookmarks .

# Run
./bookmarks --help
./bookmarks login -n <username> -p <password>
```

Default API URL: `http://localhost:8000`. Override with `--api-url` flag or `BOOKMARKS_API_URL` env var.

## Environment

`bookmark-web-client/.env.local` — set `VITE_API_URL` to override the default backend URL (`http://127.0.0.1:8000`).
