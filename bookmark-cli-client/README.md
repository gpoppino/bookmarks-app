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
# Register a new account (password is prompted with hidden input)
./bookmarks register -n <username>

# Log in (password is prompted; saves session token locally)
./bookmarks login -n <username>

# Change password (prompts for current, new, and confirmation)
./bookmarks change-password

# Show current user
./bookmarks me

# Log out (deletes local session)
./bookmarks logout
```

The username flag is optional for interactive login and registration. Passwords
are never accepted as command-line values because arguments can leak through
shell history, logs, scripts, and process inspection. Interactive password input
is hidden.

For non-interactive use, pass `--password-stdin` and always supply `--username`:

```bash
# login and register read one password line
printf '%s\n' "$PASSWORD" | ./bookmarks login --username alice --password-stdin
printf '%s\n' "$PASSWORD" | ./bookmarks register --username alice --password-stdin

# change-password reads current and new passwords from two lines
printf '%s\n%s\n' "$CURRENT_PASSWORD" "$NEW_PASSWORD" | ./bookmarks change-password --password-stdin
```

Do not put literal passwords in `echo` or `printf` commands, scripts, or shell
history. Populate the shell variables without echoing them (for example with
`read -s`) or pipe values directly from a trusted secret manager. Do not export
them unless necessary, and unset them promptly. Stdin mode does not confirm the
new password, so automated callers must validate their two-line input.

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
