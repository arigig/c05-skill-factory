# ADR-0007: HTTP Basic Auth for the submitter/reviewer roles

**Status:** Accepted (2026-11-02)

## Context
REQUIREMENTS.md §3 asks for "simple local login with two roles, submitter
and reviewer." This is a single-user local app with no existing session
infrastructure. Options considered: a session-cookie login with a login
page and server-side session store; a JWT issued on login; or HTTP Basic
Auth checked per-request against configured credentials.

## Decision
Use HTTP Basic Auth. Credentials for each role are configured via `.env`
(`SUBMITTER_USERNAME`/`PASSWORD`, `REVIEWER_USERNAME`/`PASSWORD`), with
local-dev defaults (`submitter`/`submitter123`, `reviewer`/`reviewer123`)
baked into `app/auth.py` so the app runs with zero setup. The browser sends
credentials on every request (base64-encoded in the `Authorization` header);
the HTML page collects them once via a login form and stores the header in
a JS variable, not a cookie.

## Consequences
- No session store, no CSRF concerns, no login-expiry logic needed — simpler
  than cookie/JWT sessions, appropriate for a local single-user app.
- Credentials travel on every request; this is only acceptable because the
  app runs on `localhost` without TLS termination needed for this project's
  scope. This would **not** be acceptable for any real multi-user or
  internet-facing deployment — flagged in the threat model (Phase G) as an
  explicit out-of-scope risk, not a silently accepted one.
- The default credentials are intentionally weak and documented as
  local-demo-only; anyone deploying this beyond a solo local demo must set
  real values via `.env` (see `.env.example`).
