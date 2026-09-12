# GER-6: Harden session cookie settings for production

Linear issue: [GER-6](https://linear.app/gero-projects/issue/GER-6/harden-session-cookie-settings-for-production)

## Goal

Make the login session cookie safe by default in deployed environments while
preserving an explicit local HTTP development mode. Login and logout must use
the same cookie scope so logout reliably removes the browser cookie.

## Original behavior

- `POST /api/auth/login` sets `access_token` with `HttpOnly`, `SameSite=Lax`, a
  30-day `Max-Age`, and `Secure=False`.
- The cookie does not specify `Domain` or `Path`; Starlette currently defaults
  the path to `/`.
- `POST /api/auth/logout` only passes the cookie name to `delete_cookie`, so its
  attributes are not explicitly tied to the login configuration.
- Existing backend tests construct authentication cookies directly and do not
  assert the `Set-Cookie` response from login or logout.

## Intended cookie policy

| Attribute | Development | Production and other environments | Rationale |
| --- | --- | --- | --- |
| Name | `access_token` | `access_token` | Preserve the existing API contract. |
| `HttpOnly` | `true` | `true` | Prevent JavaScript from reading the JWT. |
| `Secure` | `false` | `true` | Permit explicit local HTTP development; require HTTPS elsewhere. |
| `SameSite` | `Lax` | `Lax` | Preserve normal same-site navigation while reducing CSRF exposure. The app does not currently require cross-site cookie requests. |
| `Domain` | unset | unset | Keep a host-only cookie and avoid widening it to sibling subdomains. |
| `Path` | `/` | `/` | Make the login cookie available to all API routes. |
| Lifetime | 30 days | 30 days | Match the JWT expiration and existing behavior. |

`SameSite=None` is intentionally out of scope. It would allow cross-site cookie
requests and require a separate CSRF design. If frontend and backend are later
deployed on different sites, that architecture should be reviewed explicitly
instead of weakening this cookie by default.

## Implementation plan

1. Centralize the runtime environment decision.
   - Reuse the `APP_ENV=development` convention introduced by GER-5/PR #2.
   - Treat an unset or differently named environment as deployed and therefore
     secure by default.
   - GER-6 was rebased after PR #2 merged rather than introducing a second
     environment convention.

2. Define one session-cookie configuration in `bookmark-backend/main.py`.
   - Add constants for the cookie name, path, SameSite mode, and max age.
   - Derive `secure` from the centralized environment decision.
   - Keep `domain=None` explicit so the host-only choice is visible and tested.
   - Prefer a small helper returning the shared keyword arguments used by both
     login and logout.

3. Apply the policy to login.
   - Replace the inline `set_cookie` arguments with the shared configuration.
   - Keep `HttpOnly=true` and align `Max-Age` with
     `ACCESS_TOKEN_EXPIRE_DAYS` to prevent JWT/cookie lifetime drift.

4. Apply the same scope to logout.
   - Pass the same `path`, `domain`, `secure`, `httponly`, and `samesite`
     attributes to `delete_cookie`.
   - Let Starlette set the deletion-specific empty value, expired timestamp,
     and zero max age.

5. Add endpoint-level regression tests.
   - Log in under explicit development configuration and assert that
     `Set-Cookie` contains `HttpOnly`, `Path=/`, `SameSite=lax`, and the expected
     max age, but not `Secure` or `Domain`.
   - Log in under production configuration and assert the same attributes plus
     `Secure`.
   - Call logout in both environments and assert the deletion header uses the
     matching path/domain/security/SameSite policy with `Max-Age=0` and an
     expired value.
   - Keep one functional assertion that a login cookie authenticates a
     subsequent request, so header tests do not replace behavior coverage.
   - Parse cookie headers with Python's cookie utilities where practical rather
     than relying only on fragile full-string comparisons.

6. Document deployment behavior in `bookmark-backend/README.md`.
   - State that local HTTP startup requires `APP_ENV=development`.
   - State that deployed environments require HTTPS because the session cookie
     is `Secure`.
   - Record the chosen SameSite, host-only domain, `/` path, 30-day lifetime,
     and logout behavior.
   - Mention that TLS termination at a reverse proxy is compatible as long as
     the browser-facing URL is HTTPS.

## Verification

Run from `bookmark-backend/`:

```sh
APP_ENV=development python -m unittest -v
```

Also run targeted production-cookie tests with a valid production `SECRET_KEY`
as required by GER-5. Confirm manually from response headers that development
omits `Secure`, production includes it, and logout emits the corresponding
expired cookie with the same scope.

## Risks and rollout notes

- A production deployment still served over plain HTTP will stop retaining the
  login cookie. This is the intended secure failure mode and requires HTTPS
  before rollout.
- Changing `Domain` or `Path` in a future release requires clearing the old
  cookie at its previous scope during migration; otherwise stale cookies can
  coexist.
- Keeping a 30-day browser cookie preserves current behavior. Shortening the
  session lifetime or adding refresh-token rotation should be handled in a
  separate authentication change.

## Done when

- Development and production login responses have the documented attributes.
- Production always emits `Secure`; only explicit development omits it.
- Logout deletes the cookie using the same scope and environment-aware flags.
- Automated tests cover both environments and login/logout behavior.
- Backend documentation describes the complete cookie policy and HTTPS
  requirement.
