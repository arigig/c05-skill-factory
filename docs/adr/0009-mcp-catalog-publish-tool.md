# ADR-0009: One governed MCP tool — publish_to_catalog — closes the catalog-write gap

**Status:** Accepted (2026-11-02)

## Context
REQUIREMENTS.md §1 (Goal) says the factory "stops for human approval before
any asset is accepted into a reusable catalog," and §3 fixes the governed
tool mechanism as a local MCP server. Through Iteration 3, reviewer
approval existed (a run's `status` becomes `approved`), but nothing ever
actually wrote an approved run's code into a catalog — the loop was never
closed. The 14-layer workbook matrix (Layer 8) asks for a tool schema,
least privilege, approval-before-write, and an audit log.

## Decision
Add one deterministic tool, `publish_to_catalog(run_id)` (`app/catalog.py`),
exposed three ways that all share the same underlying function:
1. As an MCP tool (`mcp_server/server.py`, via the official `mcp` SDK's
   `MCPServer`), runnable over stdio for any MCP client.
2. As `POST /catalog/publish/{run_id}` on the FastAPI app, gated to the
   `reviewer` role.
3. Directly importable for agents in Phase E to call.

The tool refuses to run unless: the `run_id` is a syntactically valid UUID
(input validation, checked before any DB/filesystem access); the run exists;
the run's reviewer `status` is exactly `approved` (approval-before-write);
and the destination doesn't already exist (no silent overwrite of a
published artifact). Every call — success or rejection — is recorded via
`app/audit.py` to `ops/audit/log.jsonl`.

## Consequences
- The tool's "least privilege" claim rests on: it only reads the
  `conversion_runs` table (no other tables touched), only writes new files
  under `ops/catalog/` (never deletes, never overwrites), and never accepts
  a raw filesystem path from the caller — the destination is derived from
  trusted DB fields (`skill_name`, `skill_version`, `form_id`, `run_id`),
  not from untrusted input.
- `mcp[cli]>=2.3.0` (the SDK's current major version) was added to
  `requirements.txt`; note its `FastMCP` class was renamed to `MCPServer`
  between SDK v1 and v2 — code written against older MCP tutorials will not
  import correctly here.
- This closes REQUIREMENTS.md §1's "accepted into a reusable catalog" loop,
  which had no implementation prior to this ADR.
