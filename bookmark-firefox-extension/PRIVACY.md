# Privacy and data flow

The Bookmarks App Firefox extension sends data only to the backend URL the user
configures. It has no analytics, advertising, telemetry, or developer-operated
collection endpoint.

- Opening the toolbar popup reads the active tab's title and URL. The title is
  displayed locally; no page is submitted until the user presses Save.
- Saving sends the selected URL and manually entered tags in a JSON body to
  `POST /api/bookmarks`, with the configured bot token in an Authorization
  header. The complete URL includes query parameters and fragments. The user
  can edit it before saving.
- The backend URL and bot token are stored in `browser.storage.local`, in the
  Firefox profile. They are not synchronized through Firefox Sync. The extension
  does not add encryption to this storage. It does not store a browsing history
  or a record of submitted pages.
- The extension does not access native Firefox bookmarks, inject scripts into
  pages, read page contents, or forward browser session cookies. Its API requests
  omit cookies and reject redirects. HTTP backends are allowed only on loopback.
- The user grants access to the chosen backend host. Firefox's host permission
  applies to all ports on that host; requests use only the configured base URL.
  Removing configuration removes its stored credentials and host permissions;
  revoking a bot token is a separate action on the backend.
- The backend fetches the saved page to obtain its title and description. If
  automatic tagging is enabled there, the backend may send metadata and existing
  tags to OpenAI as documented in the backend README. Data retention and access
  to saved bookmarks are controlled by the configured backend operator.

The manifest declares `authenticationInfo` and `browsingActivity` because the
token and selected page URL are transmitted outside the browser for the requested
save operation. There is no automatic collection of pages visited.
