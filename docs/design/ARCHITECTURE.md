# Architecture

Living document. Updated as each Iteration 4 phase lands. Source of truth for
*what exists and how it fits together*; REQUIREMENTS.md remains the source of
truth for *what must be built and why*. See `docs/adr/` for the reasoning
behind individual decisions referenced below.

## Current system (as of end of Iteration 3)

```
                         ┌─────────────────────┐
  Browser (reviewer) ───▶│  app/static/index.html │
                         └──────────┬───────────┘
                                    │ fetch()
                                    ▼
                         ┌─────────────────────┐
                         │   FastAPI app        │   app/main.py
                         │  /health /samples    │
                         │  /convert /runs       │
                         │  /review/.../approve  │
                         │  /review/.../reject   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  app/pipeline.py      │  orchestrates one run
                         └──────────┬───────────┘
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
┌───────────────────┐   ┌───────────────────────┐   ┌───────────────────┐
│ app/loader.py       │   │ app/skills/conversion.py│   │ app/sandbox.py      │
│ app/miniform_schema │   │  → app/gateway.py        │   │ (Docker, --network  │
│ app/canonical.py    │   │  → app/cost_ledger.py    │   │  none)              │
│ (validate + map to  │   │  (calls real Claude API, │   │ runs generated      │
│  CanonicalForm)      │   │   enforces budget/retry) │   │  pytest in isolation│
└─────────┬──────────┘   └───────────────────────┘   └───────────────────┘
          │
          ▼
┌───────────────────┐
│ app/provenance.py   │  →  ops/provenance/log.jsonl  (lineage)
└───────────────────┘

                         All runs persisted to:
                         ┌───────────────────┐
                         │  app/db.py (SQLite) │  ops/app.db
                         │  conversion_runs    │
                         └───────────────────┘
```

**Data flow for one conversion (`POST /convert`):**
1. `app/loader.py` validates the raw MiniForm JSON (`app/miniform_schema.py`)
   and maps it to the canonical schema (`app/canonical.py`). Invalid input is
   rejected here; nothing past this point ever sees invalid input.
2. `app/provenance.py` records a lineage entry (source, hash, timestamp,
   accepted/rejected) for every file processed.
3. `app/skills/conversion.py` loads `skills/miniform_to_python/SKILL.md` as
   the trusted system prompt and sends the canonical form's JSON as untrusted
   user-message data to `app/gateway.py`, which calls the real Claude API
   (Sonnet 5, with a Haiku 5.5 fallback — ADR-0002), forcing a structured
   tool-call response. Every call's cost is logged via
   `app/cost_ledger.py` (`ops/cost_ledger/ledger.jsonl`) and checked against
   the $4.00 hard stop *before* the call is made.
4. `app/sandbox.py` writes the generated code to
   `ops/generated_runs/<run_id>/` and runs its pytest suite inside a Docker
   container with `--network none` (dependencies baked into
   `Dockerfile.sandbox` ahead of time, so no network is needed at validation
   time).
5. `app/db.py` persists the run (`conversion_runs` table in `ops/app.db`)
   with `status = pending_review`.
6. A human reviewer calls `/review/{run_id}/approve` or `/reject` from the
   HTML page — this is the only thing that changes a run's final status.
   Nothing is written to a reusable catalog automatically (REQUIREMENTS.md
   §5); that catalog-write step does not exist yet and will require its own
   explicit approval action when built.

**Known limitation (ADR-0004):** the sandbox step needs the host's Docker
daemon. The FastAPI app must run from the host venv (`uvicorn` directly), not
from inside its own `docker compose` container, for conversions to work.
`docker compose up` is still valid for Iteration 1's health-check/static-page
check, just not for real conversion runs yet.

## Planned additions (Iteration 4)

| Phase | Adds | Where it plugs in |
|---|---|---|
| A — Roles | Local login, `submitter`/`reviewer` roles | Gates `/convert` to submitter-or-above, `/review/*` to reviewer only |
| B — Memory/State | Formal state schema, checkpoint/resume, isolation tests | Extends `app/db.py`; `run_id` is the isolation unit (ADR-0005) |
| C — MCP | Local MCP server, one governed tool, audit log | New `mcp_server/` component, called from an agent (Phase E) with least-privilege scope |
| D — RAG | BM25 index over a synthetic standards/rules/templates corpus, citations | New `app/retrieval.py` + `knowledge/` corpus; used by the Mapping/Conversion agents |
| E — Agents | Discovery, Mapping, Conversion, Validation, Reviewer agents replace the single `pipeline.py` function | `app/agents/` package; orchestrator routes between them with retries/timeouts/safe-stop; human approval gate stays before catalog acceptance |
| F — Evaluation | Harness over golden set + negative inputs + LLM judge (ADR-0006) | New `app/evaluation.py` + `scripts/run_eval.py` |
| G — Security | Threat model, control matrix, red-team cases | `docs/evidence/11-security-rai-governance.md` + test cases exercising real injection attempts |
| H — Observability | Structured traces, dashboard, incident scenario | New `app/tracing.py`; every gateway/tool/retrieval call emits a trace record |

## Directory layout

```
app/                   FastAPI app, business logic
  canonical.py          Canonical schema (shared target for all source types)
  miniform_schema.py     Raw MiniForm input schema
  loader.py              Validates + maps MiniForm → canonical
  provenance.py          Lineage logging
  cost_ledger.py          Budget tracking + hard stop
  gateway.py              Only module that calls the Claude API
  skills/conversion.py     Wires the Skill into the gateway
  sandbox.py              Isolated Docker-based pytest validation
  db.py                   SQLite run storage
  pipeline.py             Orchestrates one run end-to-end (pre-agent version)
  main.py                 FastAPI routes
  static/index.html        Plain HTML reviewer UI (replaced in Iteration 6)
skills/                 Versioned, reusable Skill definitions (SKILL.md per skill)
config/                 pricing.json, future runtime config
tests/                  pytest suite, fixtures, golden set
docs/
  REQUIREMENTS.md         Source of truth for scope
  adr/                    Architecture Decision Records
  design/                 This file
  data_dictionary.md       Canonical schema field reference
  evidence/               Per-layer evidence (Iteration 4+)
ops/                    Runtime state (git-ignored): cost ledger, provenance
                         log, generated run artifacts, SQLite DB
```
