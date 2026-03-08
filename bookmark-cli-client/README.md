# bookmarks-cli

A Go CLI client for the bookmarks API.

## Requirements

- Go 1.21+
- The [bookmark-backend](../bookmark-backend/) running

## Build

```bash
cd bookmark-cli-client
go build -o bookmarks .
```

## Configuration

| Method | Description |
|--------|-------------|
| `--api-url URL` | Override the backend URL (default: `http://localhost:8000`) |
| `BOOKMARKS_API_URL` | Environment variable alternative to `--api-url` |

## Usage

### Authentication

```bash
# Register a new account
./bookmarks register -n <username> -p <password>

# Log in (saves session token to ~/.config/bookmarks-cli/session)
./bookmarks login -n <username> -p <password>

# Show current user
./bookmarks me

# Log out (deletes local session)
./bookmarks logout
```

Username and password flags are optional — the CLI will prompt if omitted. Password input is hidden.

### Bookmarks

```bash
# List all bookmarks
./bookmarks list

# Filter by tag or search term
./bookmarks list --tag golang
./bookmarks list --search "fast api"

# Pagination
./bookmarks list --skip 10 --limit 5

# Add a bookmark (title and description are scraped automatically)
./bookmarks add -u https://go.dev
./bookmarks add -u https://go.dev -t golang,programming

# Update a bookmark's URL (re-scrapes title/description) and/or tags
./bookmarks update -i <id> --url https://new-url.com
./bookmarks update -i <id> --tags newtag1,newtag2
./bookmarks update -i <id> --url https://new-url.com --tags newtag1,newtag2

# Delete a bookmark (prompts for confirmation)
./bookmarks delete -i <id>
```

### Tags

```bash
# List all tags used by the current user
./bookmarks tags
```

## Session storage

The session token (JWT) is stored at `~/.config/bookmarks-cli/session` with permissions `0600` (owner read/write only).
