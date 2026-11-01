# ADR-0004: Sandbox validation runs from the host process, not from inside the app's own container

**Status:** Accepted (2026-11-01)

## Context
Iteration 3's sandboxed validation (`app/sandbox.py`) launches a Docker
container (`docker run --rm --network none ...`) to execute generated pytest
suites in isolation. When the main app itself was run via `docker compose up`
(its own container), this failed: a container cannot launch sibling
containers on the host's Docker daemon without the host's Docker socket
being explicitly mounted into it (Docker-in-Docker).

## Decision
For now, run the FastAPI app directly on the host (via the project's `.venv`
and `uvicorn`) for any workflow that needs to trigger sandboxed validation.
`docker compose up` (the containerized app) remains valid for serving the
health check and static page per Iteration 1's done-when check, but is not
used for real conversion runs yet.

## Consequences
- There are now two ways to run the app (containerized vs. host venv), which
  could confuse a new contributor. This should be documented clearly in the
  runbook (Iteration 7) and `docs/design/ARCHITECTURE.md`.
- If full containerization of the convert-and-validate flow is wanted later,
  the fix is to mount `/var/run/docker.sock` into the app container (or use a
  docker-in-docker sidecar) and install the `docker` CLI in `Dockerfile`.
  This has real security implications (a compromised app container would
  gain host Docker control) and should be a deliberate, reviewed decision —
  tracked as a known gap for Iteration 7 hardening, not done casually.
