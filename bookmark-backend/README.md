# Bookmark App — Backend

A FastAPI + SQLAlchemy REST API for the bookmarking application.

## Stack

- **Python 3.11+**
- **FastAPI** — API framework
- **SQLAlchemy** — ORM
- **SQLite** — Database (file-based, zero config)
- **BeautifulSoup4** — Webpage metadata scraping

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the development server
uvicorn main:app --reload
```

The API will be running at **http://127.0.0.1:8000**

## Interactive Docs

FastAPI auto-generates Swagger UI. Open your browser at:

```
http://127.0.0.1:8000/docs
```

## API Endpoints

| Method   | Endpoint                      | Description                                      |
|----------|-------------------------------|--------------------------------------------------|
| `GET`    | `/api/bookmarks`              | List all bookmarks (supports search & tag filter)|
| `POST`   | `/api/bookmarks`              | Create a new bookmark                            |
| `DELETE` | `/api/bookmarks/{id}`         | Delete a bookmark by ID                          |
| `GET`    | `/api/tags`                   | List all tags                                    |
| `GET`    | `/health`                     | Health check                                     |

## Query Parameters — GET /api/bookmarks

| Param    | Type   | Description                                   |
|----------|--------|-----------------------------------------------|
| `search` | string | Search across title, description, and URL     |
| `tag`    | string | Filter bookmarks by a specific tag name       |
| `skip`   | int    | Pagination offset (default: 0)                |
| `limit`  | int    | Max results to return (default: 50)           |

### Examples

```
GET /api/bookmarks?search=fastapi
GET /api/bookmarks?tag=python
GET /api/bookmarks?search=api&tag=tutorial&skip=0&limit=20
```

## Request Body — POST /api/bookmarks

```json
{
  "url": "https://fastapi.tiangolo.com",
  "tags": ["python", "api", "tutorial"]
}
```

## Database

SQLite database is auto-created as `bookmarks.db` in the project root on first run. No migration step needed.
