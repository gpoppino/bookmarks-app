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

## Revocable bot tokens

Bot tokens support unattended bookmark capture without storing a user's password
or renewing a browser session every 30 days. Each token belongs to the logged-in
user and has the fixed scope `bookmarks:create`: it can only call
`POST /api/bookmarks`. It cannot read, update, or delete bookmarks, change a
password, or create/list/revoke tokens.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/auth/bot-tokens` | Create a token; returns the secret once |
| GET | `/api/auth/bot-tokens` | List your tokens' metadata, including revoked tokens |
| DELETE | `/api/auth/bot-tokens/{id}` | Revoke your token (204; repeat calls are safe) |

All three management endpoints require a valid `access_token` **login JWT cookie**.
A bot token cannot manage itself or other tokens. Another user's token ID returns
404. Management responses use `Cache-Control: no-store`.

### Create a token for the Pi

1. Open the backend's `/docs` page and execute `POST /api/auth/login` with your
   username/password. The browser stores the login cookie for subsequent calls.
2. Execute `POST /api/auth/bot-tokens` with:

   ```json
   {"name": "amnotbot Pi"}
   ```

   Omitting `expires_in_days` (or using `null`) creates a token that lasts until
   revoked. Optionally supply an integer from 1 to 3650 to limit its lifetime.
3. Save the response's `token` value securely. It starts with `bkt_` and cannot be
   retrieved again; list responses never include the secret or its hash.
4. On the Pi, edit `~/.amnotbot/amnotbot.config` and replace the existing value:

   ```properties
   bookmark_jwt_token = bkt_YOUR_TOKEN_HERE
   ```

   The setting retains its existing name for compatibility. Keep the config
   private (`chmod 600 ~/.amnotbot/amnotbot.config`), then run:

   ```sh
   sudo systemctl restart amnotbot.service
   systemctl is-active amnotbot.service
   ```

The existing bot JAR works unchanged: this backend accepts bot tokens in the
`access_token` cookie for bookmark creation. New integrations should prefer
`Authorization: Bearer bkt_...`. An explicit invalid Authorization header is
rejected rather than falling back to a login cookie.

`GET /api/auth/me` intentionally rejects bot tokens because they have create-only
access. The older `bookmark-login.py --check` helper therefore isn't a bot-token
health check, and running that helper's login flow replaces the bot token with a
30-day login JWT. For a bot token, inspect its `last_used_at` in the management
listing and verify a real bookmark save from IRC.

### Revoke or rotate

Log in normally, list tokens to find the ID, then delete that ID. Subsequent
requests with the revoked token receive 401 immediately, without restarting the
backend or bot. Requests already authenticated may finish. To rotate without a
gap, create a replacement, update/restart the bot, verify a save, then revoke the
old token. Revoked records remain in the list for reference.

Only SHA-256 hashes of cryptographically random 256-bit secrets are stored.
Authentication checks the database on every request; an unknown, expired,
revoked token or one whose owner was deleted receives 401. Non-expiring tokens
survive application restarts and JWT signing-key rotation. User logout/password
changes do not revoke bot tokens: revoke them explicitly when needed. Prefer a
separate token per bot so revocation can target one installation.

### Deployment and tests

Deploy the updated `main.py` and restart the backend. Startup's existing
`Base.metadata.create_all()` adds the `bot_tokens` table and indexes to an
existing SQLite database without changing user/bookmark tables. Back up the
database before deployment as usual. Older backend versions cannot authenticate
bot tokens; retain a normal login path when rolling back.

```sh
pip install -r requirements-dev.txt
python -m unittest -v test_bot_tokens
```

Tests use a temporary SQLite database and mocked metadata scraping; they do not
use the live database, contact websites, or create real bookmarks.
