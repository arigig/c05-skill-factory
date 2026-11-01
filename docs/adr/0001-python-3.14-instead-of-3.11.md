# ADR-0001: Use Python 3.14 instead of the originally pinned 3.11

**Status:** Accepted (2026-11-01)

## Context
REQUIREMENTS.md originally pinned Python 3.11 as the project's language version
(§3). During Iteration 0's install checks, only Python 3.14 was present on the
build laptop; 3.11 was not installed. Python 3.11 can be installed side by
side with 3.14 via the `py` launcher with no conflict.

## Decision
Rather than install 3.11 alongside the existing 3.14, the project adopts
Python 3.14 as its pinned language version. REQUIREMENTS.md §3 and the
Iteration 0 table were updated accordingly.

## Consequences
- FastAPI, Uvicorn, and Pydantic versions had to be re-verified for 3.14
  compatibility (confirmed: FastAPI ≥0.120.1, Uvicorn ≥0.38.0, Pydantic
  ≥2.12.1; Pydantic v1 is not supported on 3.14).
- The "still open" compatibility note in REQUIREMENTS.md §6 (PySpark/MCP SDK
  versions for the pinned Python) now targets 3.14, which is a very recent
  release — some third-party libraries may lag in support. This remains an
  open risk to watch, particularly for the MCP SDK (Phase C, Iteration 4).
