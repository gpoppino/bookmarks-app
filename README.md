# Bookmarks App

This repository contains three independently runnable components:

- `bookmark-backend`: FastAPI, SQLAlchemy, and SQLite
- `bookmark-web-client`: React, TypeScript, and Vite
- `bookmark-cli-client`: Go and Cobra

See each component's README for setup and usage instructions.

## Local CI checks

Pull requests run the backend, web, and CLI jobs defined in
`.github/workflows/ci.yml`. Run their local equivalents before pushing:

```sh
# Backend
cd bookmark-backend
pip install -r requirements-dev.txt
APP_ENV=development python -m unittest -v

# Web
cd ../bookmark-web-client
npm ci
npm run lint
npm test
npm run build

# CLI
cd ../bookmark-cli-client
go test ./...
go build -o /tmp/bookmarks-cli .
```

The CI setup caches package-manager downloads through the official Python,
Node.js, and Go setup actions. It does not cache build outputs or application
data.
