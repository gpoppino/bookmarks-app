# Bookmarks App — Firefox extension

A Firefox desktop extension that saves the current page to your existing
`bookmark-backend`. The toolbar button opens a short Spanish-language form with
the current URL and optional comma-separated tags. It uses a dedicated,
revocable `bookmarks:create` bot token; no backend changes are required.

## Requirements

- Firefox desktop **140 or later**.
- A running backend with [bot-token support](../bookmark-backend/README.md#revocable-bot-tokens)
  and an existing user account.
- HTTPS for deployed backends. HTTP is allowed only for `localhost`,
  `127.0.0.1`, and `[::1]` on the same computer as Firefox.

The extension is plain HTML, CSS, and JavaScript. Loading it into Firefox requires
no Node.js installation, dependency downloads, or build step. Node.js 20+ is used
for development checks and tests; Python 3 is used for ZIP packaging.

## Install for local use and development

1. Clone or update this repository.
2. In Firefox, open `about:debugging#/runtime/this-firefox`.
3. Click **Load Temporary Add-on…** (Spanish: **Cargar complemento temporal…**).
4. Select `bookmark-firefox-extension/manifest.json`.
5. Open Firefox's Extensions menu (puzzle-piece icon) and pin **Bookmarks App**
   to the toolbar if desired.

Temporary installation lasts until Firefox restarts. Use **Reload** on the
`about:debugging` extension card after source changes. Load the same manifest
again after restarting; if settings are missing, configure it again.

For permanent installation in normal Firefox, use a Mozilla-signed XPI as
described below. Renaming an unsigned ZIP to `.xpi` does not sign it.

## Create a dedicated token

1. Open your **backend** `/docs` page, for example
   `http://127.0.0.1:8000/docs` in local development.
2. Expand **POST /api/auth/login**, click **Try it out**, enter your existing
   username and password, and execute the request. The browser stores the
   session cookie used for token management. There is no need to copy that cookie.
3. Expand **POST /api/auth/bot-tokens**, click **Try it out**, and execute:

   ```json
   {
     "name": "Firefox — personal laptop",
     "expires_in_days": 365
   }
   ```

   `expires_in_days` is optional: omit it or use `null` for a token valid until
   revoked. Use a separate token for each browser/profile.
4. Copy the response's `token` field, beginning with `bkt_`. The backend shows
   the secret only once. Do not commit it, put it in the extension source, or
   include it in a distributed ZIP.

For a local backend, start it with `APP_ENV=development` so login cookies work
over HTTP; follow the [backend setup instructions](../bookmark-backend/README.md#setup).
Production requires its normal HTTPS and secret-key configuration.

## Configure the extension

1. Click the **Bookmarks App** toolbar button, then **Configuración**. You can
   also open `about:addons`, select the extension, and open its preferences.
2. Enter **URL del backend**, such as:

   | Deployment | Backend URL |
   |------------|-------------|
   | Local backend | `http://127.0.0.1:8000` |
   | Remote backend | `https://bookmarks.example.com` |
   | Reverse proxy under a path | `https://example.com/bookmarks` |

   Use the address exposing the API, which may differ from the React web
   client's address. Do not append `/api/bookmarks` or `/docs`. For example,
   `https://example.com/bookmarks` produces requests to
   `https://example.com/bookmarks/api/bookmarks`.
3. Paste the token into **Bot token**.
4. Click **Guardar y autorizar servidor** and accept Firefox's host-access
   request. The extension requests the chosen protocol and host; Firefox host
   permissions cover all ports of that host. Requests use the configured port
   and base path. Denying access leaves the previous configuration unchanged.
5. A success message confirms the settings were stored. It does **not** validate
   the token against the backend: its create-only scope has no authentication
   probe endpoint. The first bookmark save verifies it.

The saved token is never filled back into the form. Leave the token field blank
to retain it when keeping the same backend URL. To change the server or base
path, explicitly enter a token for that destination. Saving a new server removes
old host grants. No CORS changes to the backend are needed: the background
extension page uses Firefox's granted host permission for API requests.

## Save a page

1. Open a normal HTTP or HTTPS page and click the toolbar button.
2. Review the URL and optionally edit it. The entire URL, including query
   parameters and fragments, is preserved; remove sensitive parameters yourself
   before submitting if necessary.
3. Enter optional tags, separated by commas, for example `go, linux, lectura`.
4. Click **Guardar bookmark**. The extension normalizes tags to lowercase,
   removes duplicates, and submits the URL and tags to `POST /api/bookmarks`.
5. Wait for **Bookmark guardado.** The bookmark is visible in your account in
   the web or CLI client. The server scrapes the title and description, and may
   add automatic tags if configured to do so.

You can close the popup after submitting; the request runs in the background
while Firefox remains open. Closing Firefox or disabling/reloading the extension
can interrupt it. There is no offline queue or automatic retry. Reopening the
popup does not display the previous request's result; verify in the web client
if you closed it before confirmation. A repeated URL returns **Esta URL ya está
guardada en tu cuenta.** and does not modify the existing bookmark or its tags.

Firefox internal pages (`about:*`), local files, and non-web URLs cannot be saved.
The backend must be able to fetch the target page: pages requiring your browser
login, blocked sites, and intranet pages unreachable from the backend may fail.
The extension does not copy browser cookies or page contents to work around this.

## Rotate or remove credentials

- To rotate: create a replacement bot token, save it in the extension, verify a
  bookmark save, then revoke the previous token through
  `DELETE /api/auth/bot-tokens/{id}` in `/docs` while logged in.
- To disconnect this profile: click **Borrar configuración local**. This removes
  the stored URL/token and host grants. It does not revoke the token on the
  backend or cancel a request already in progress; revoke separately if needed.
- Logging out of the web client does not invalidate bot tokens.

## Troubleshooting

| Message / symptom | What to check |
|-------------------|---------------|
| Token rejected | Replace an expired or revoked bot token. Login JWTs cannot be used here. |
| Missing host permission | Open configuration, save again, and accept the access request. Also inspect permissions in `about:addons`. |
| Connection failure | Use the backend URL, ensure it is reachable from Firefox, and verify the HTTPS certificate. The extension rejects redirects; configure the final API base URL. |
| Timeout | Check the web client before retrying: a timed-out request may already have committed the bookmark. |
| Page cannot be saved | Check that the backend can fetch the URL and scrape its metadata. |
| Backend running on another device over HTTP | Expose it using HTTPS; remote plaintext URLs are rejected to protect the bearer token. |
| Extension disappeared on restart | Temporary add-ons must be loaded again; use a signed XPI for permanent installation. |

## Development and packaging

```sh
cd bookmark-firefox-extension
npm ci
npm run lint
npm test
npm run build
```

`lint` checks JavaScript syntax and manifest resource paths. Tests use Node's
built-in test runner and jsdom, with mocked Firefox APIs and HTTP responses;
they never use your real token, database, or backend. They cover permissions,
configuration, the popup, request/authentication behavior, duplicate prevention,
error handling, timeout, and the full configuration-to-save flow.

`build` uses Python's standard library to create
`dist/bookmarks-app-firefox-1.0.0.zip` with an explicit allowlist of runtime files.
It excludes tests, dependencies, docs, local configuration, and source maps. The
ZIP is **unsigned** and can be loaded temporarily through `about:debugging`.
Do not commit generated archives or `node_modules`.

For Mozilla's full manifest and add-on checks, with registry access available:

```sh
npx --yes web-ext lint --source-dir . --ignore-files 'tests/**' 'scripts/**' 'dist/**' 'node_modules/**' 'package*.json' 'README.md' 'PRIVACY.md'
```

### Manual Firefox verification

After the automated checks, load the extension in a test profile and verify:

1. First run opens configuration and does not permit saving without a token.
2. Accepting/denying the host request has the expected effect. Check an HTTP
   loopback URL with a port as well as the deployed HTTPS URL.
3. Save a publicly accessible page with manual tags; verify it in the web client.
4. Save the same URL twice; check the duplicate message and unchanged bookmark.
5. Revoke the token and retry with a new URL; check the authentication message.
6. Stop the backend and check the connection error; restart before continuing.
7. Save a page, close the popup immediately, and verify the background save.
8. Change the server with a new token and inspect host permissions; clear the
   settings and verify that local credentials and host access are removed.

## Permanent installation through Mozilla signing

Normal Firefox releases require Mozilla-signed extensions. For personal use,
choose **self-distribution / unlisted**: signing does not require a public AMO
listing, but Mozilla receives the extension package for review and signing.

1. Run the checks and build above. Keep the manifest ID stable across updates;
   if AMO reports that `firefox@bookmarks-app.local` is already registered by
   someone else, choose your own unique ID before the first submission.
2. Sign in at [Mozilla Add-on Developer Hub](https://addons.mozilla.org/developers/)
   and submit a new add-on for **distribution on your own** (unlisted).
3. Upload the generated ZIP. Complete Mozilla's validation, data disclosures,
   and any review questions. The source is plain JavaScript with no build-time
   transformation; no credentials belong in the submission. See
   [PRIVACY.md](PRIVACY.md) for the data flow.
4. Download the **signed `.xpi`** provided by Mozilla.
5. In Firefox, open `about:addons`, use the gear menu → **Install Add-on From
   File…**, and select that signed XPI. Then configure your backend and token.

For updates, increment the extension version in `manifest.json`, `package.json`,
and `package-lock.json`, rebuild, sign a new unlisted version under the same ID,
and install its signed XPI. This repository does not configure automatic updates.
This implementation does not submit to Mozilla or include a signed XPI.

Official references:

- [Temporary installation](https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/)
- [Host permissions](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/host_permissions)
- [Signing and distribution](https://extensionworkshop.com/documentation/publish/signing-and-distribution-overview/)
- [Firefox data consent](https://extensionworkshop.com/documentation/develop/firefox-builtin-data-consent/)
