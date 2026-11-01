# Layer 8 Evidence: Enterprise Tools / MCP

Written for: a beginner trying to understand what the MCP integration does and why it exists.

## What problem this solves

Earlier in the project, a human reviewer could **approve** a converted form
(Iteration 3), but nothing ever actually moved the generated code anywhere
permanent — "approved" just sat in a database column. The project's goal
(`docs/REQUIREMENTS.md` §1) says the factory must "stop for human approval
**before any asset is accepted into a reusable catalog**." That catalog-write
step didn't exist. Phase C built it — as one governed tool, reachable
through MCP.

## What is MCP, in plain terms?

MCP (**Model Context Protocol**) is a standard way for an AI system (or any
other client program) to call a small set of well-defined "tools" on your
computer — without that AI being able to run arbitrary code. Instead of
giving an AI model unrestricted file/shell access, you write one specific
function, describe exactly what inputs it takes, and the AI can only ever
call that function with those inputs. Think of it like a hotel room key
that opens exactly one door, instead of a master key to the whole building.

In this project, the "one door" is: **publish an already-approved
conversion run into the catalog.** Nothing else. Not "run any command," not
"read any file" — just that one specific, narrow action.

## Architecture diagram

```
                     ┌──────────────────────────────────────┐
                     │        app/catalog.py                   │
                     │   publish_to_catalog(run_id, caller)     │
                     │                                          │
                     │  1. Is run_id a real UUID?  ─── no ──▶ reject
                     │  2. Does this run exist in the DB? ── no ──▶ reject
                     │  3. Is its status == "approved"? ── no ──▶ reject
                     │  4. Does it already exist in the catalog? │
                     │       yes ──▶ reject (no overwrite)       │
                     │  5. Write 4 code files to ops/catalog/...  │
                     │  6. Log the outcome (success or reject)    │
                     └───────┬───────────────┬──────────────┬────┘
                             │               │              │
             reads/writes    │               │              │
                             ▼               ▼              ▼
                 ┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐
                 │  ops/app.db       │  │ ops/catalog/   │  │ ops/audit/        │
                 │  (SQLite:          │  │ (approved        │  │ log.jsonl           │
                 │  conversion_runs)  │  │  code files,    │  │ every call, pass    │
                 │  — READ ONLY here  │  │  never          │  │ or fail, who/when/  │
                 │                    │  │  overwritten)   │  │ what)               │
                 └─────────────────┘  └──────────────┘  └─────────────────┘

        Three different "front doors" call the exact same function above —
        none of them bypass its checks:

  ┌────────────────────┐   ┌──────────────────────────┐   ┌───────────────────────┐
  │  An MCP client       │   │  The reviewer's browser    │   │  A future agent          │
  │  (e.g. Claude Code,   │   │  POST /catalog/publish/… │   │  (Phase E) calling       │
  │  talking over stdio)  │   │  (requires reviewer role)  │   │  the Python function      │
  │  mcp_server/server.py │   │  app/main.py               │   │  directly                 │
  └────────────────────┘   └──────────────────────────┘   └───────────────────────┘
```

## Walking through one call

Say a reviewer clicks "Publish to Catalog" for run `abc-123` on the web
page:

1. The browser sends `POST /catalog/publish/abc-123` with the reviewer's
   login credentials attached.
2. `app/main.py` checks the credentials prove a **reviewer** (not just a
   submitter) — only reviewers may trigger a write.
3. It calls `publish_to_catalog("abc-123", caller="reviewer1")` — the exact
   same function an MCP client would call.
4. That function runs its five checks (shown in the diagram) in order. If
   any check fails, it immediately logs the rejection and raises an error —
   no partial writes ever happen.
5. If everything passes, it writes four files (the Pydantic model, the rule
   functions, the FastAPI endpoint, and the pytest tests) into a folder
   named after the skill version, form, and run ID — e.g.
   `ops/catalog/miniform_to_python-1.0.0/expense_request/abc-123/`.
6. It writes one line to `ops/audit/log.jsonl` recording exactly what
   happened, who asked for it, and when.
7. The browser shows the catalog path back to the reviewer.

## Why this counts as "governed" and "least privilege"

- **The tool can't be tricked into writing somewhere else.** The destination
  folder name is built entirely from trusted database fields (the skill
  name/version and form ID already stored when the run was created) — the
  caller only ever supplies a `run_id`, never a file path.
- **It can't approve its own write.** Approval already had to happen through
  the separate, human-only `/review/.../approve` action before this tool
  will do anything.
- **It can't silently overwrite history.** If a run was already published,
  trying again is rejected, not silently replaced.
- **Every attempt is recorded**, including the ones that get rejected — so
  there's a full trail of who tried to publish what, and whether it
  succeeded.

## Where to see this yourself

- The tool's code: [`app/catalog.py`](../../app/catalog.py)
- The MCP server wrapper: [`mcp_server/server.py`](../../mcp_server/server.py)
- The audit logger: [`app/audit.py`](../../app/audit.py)
- Tests proving every rejection case actually rejects:
  [`tests/test_catalog_tool.py`](../../tests/test_catalog_tool.py)
- The design decision behind this layer: [ADR-0009](../adr/0009-mcp-catalog-publish-tool.md)

## Pass/fail check (from REQUIREMENTS.md §7)

| Check | Status |
|---|---|
| Tool schema documented | ✅ confirmed via `mcp.list_tools()` — see ADR-0009 |
| Least privilege | ✅ read-only on the DB, append-only on the catalog, no caller-supplied paths |
| Input validation | ✅ UUID format checked before any DB/filesystem access |
| Approval before write | ✅ refuses anything not `status == approved` |
| Audit log | ✅ `ops/audit/log.jsonl`, every call |
| Negative tests | ✅ 6 of 9 tests in `test_catalog_tool.py` are negative cases |
| Tool success / invalid calls blocked (metric) | ✅ measured directly by the test suite: 100% of the 6 negative cases are blocked |
