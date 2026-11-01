# C05 - Application Migration Skill Factory · Requirements One-Pager (v1.0, 01-Nov-2026)

> **Purpose:** Single source of truth for Claude Code. Claude Code turns each iteration below into small, numbered steps for a builder with very basic coding knowledge. **Do not invent requirements; if something is not stated here, stop and ask.**

## 1. Goal
Build a factory that runs locally. It reads **synthetic low-code app exports** (forms, workflows, rules and metadata) and maps them to a **canonical intermediate schema**. It then applies **versioned, reusable Skills** to generate target code, validates that code, and **stops for human approval** before any asset is accepted into a reusable catalog. All 14 workbook layers need executable evidence. To pass: score ≥80% with zero critical security, privacy or safety gaps.

## 2. Scenario (example data only: synthetic, no real or client data)
| Stage | Source (low-code) | Target |
|---|---|---|
| **Starter example** (iterations 2-3) | Synthetic `MiniForm` JSON: 1 form (fields, types, required flags), 2 validation rules, 1 approval workflow | Python: Pydantic model, FastAPI endpoint, rule functions and pytest tests |
| **Realistic upgrade** (iteration 5) | Synthetic export **modelled on the Microsoft Power Platform style**: canvas-style form definitions, Power Fx-style rule expressions and a Power Automate-style flow JSON. **Written by hand, labelled synthetic, and not claimed to match the real export format.** | Same Python target, plus a generated workflow state machine |

*Why Power Platform:* it matches the workbook's "forms, workflows, rules" wording. It is also widely used in enterprises, and its components are easy to describe as JSON or YAML.
*Validation:* run the generated pytest inside an **isolated Docker container with no network access**, check the output against the schema, and measure field and rule coverage.

## 3. Fixed constraints
- **Laptop:** personal Windows laptop.
- **Coding tool:** Claude Code (Pro subscription) in VS Code, used to *build* the app.
- **Runtime model:** the app calls **Claude Sonnet 5** through the Claude API at run time. *Sonnet 5 pricing has not been verified. Look it up, then set it in the config.*
- **Spending limit:** the app has **$5 of API credit in total**. Its gateway must enforce a token cap per run and a **hard stop at $4.00 cumulative** spend, tracked in `ops/cost_ledger`.
- **CI:** CI must **never call the real API**. It uses recorded or mock responses. Real-model evaluations run only when started by hand on the laptop.
- **Repository and CI:** public GitHub repository with GitHub Actions. No secrets in the repo; the API key lives only in a git-ignored `.env`. Enable secret scanning and add a pre-commit check.
- **Deployment:** local Docker Desktop with `docker compose`. Cloud deployment is out of scope.
- **Stack:**
  - **Language:** Python 3.14. Confirm library compatibility before pinning versions.
  - **Back end:** FastAPI.
  - **State storage:** SQLite.
  - **Retrieval:** BM25 keyword search. No embeddings.
  - **Governed tools:** a local MCP server.
  - **Login:** simple local login with two roles, *submitter* and *reviewer*.
- **Cowork** is not used at run time.

## 4. Iterations (each one ends with a pass/fail check; do not move on until it passes)
| # | Iteration | Done when |
|---|---|---|
| 0 | **Install checks:** Python 3.14, Git, Docker Desktop (with WSL2), VS Code, Claude Code, Node LTS (needed from iteration 6), GitHub account and API key in `.env` | A script prints each tool's version and returns PASS or FAIL |
| 1 | **Skeleton:** repo, `CLAUDE.md` (commands, allow/ask/deny rules that block `.env`, definition of done), folder layout, FastAPI health endpoint, **plain HTML page** | `docker compose up` serves the page and the health check returns 200; CI is green |
| 2 | **Data and schema:** MiniForm samples (3 valid, 2 invalid, 1 containing an injection attempt), canonical schema, loader, data dictionary, provenance record, golden set | Valid samples pass the validator, invalid ones are rejected, and lineage is recorded |
| 3 | **Starter slice end to end:** model gateway (structured output, retries, cost log, budget stop), 1 conversion Skill (`SKILL.md` with positive and negative tests), sandboxed validation, reviewer Approve/Reject | One happy path and one rejection path both work from the HTML page |
| 4 | **Remaining layers:** five agents (Discovery, Mapping, Conversion, Validation, Reviewer) with retries, timeouts and safe stop; BM25 search over standards, rules and templates with citations; checkpoint and resume; MCP tool with least privilege and audit log; evaluation harness; threat model and red-team cases; traces and dashboard; roles | Every one of the 14 layers has an evidence file under `docs/evidence/`. This is the Gate 2 slice |
| 5 | **Upgrade to Power Platform-style:** new parser that maps exports to the same canonical schema, plus Skills for forms, Power Fx-style rules and flows; existing Skills reused | Golden set passes for both source types; reuse rate is reported |
| 6 | **React UI:** replaces the HTML page and keeps the same API contract | All UI checks from iteration 3 pass in React |
| 7 | **Hardening and handover:** CI gates (tests, secret scan, recorded-response evaluation regression), release notes, ADRs, runbook including rollback, value case (measured vs projected), RACI | Final checklist complete and demo recorded |

## 5. Non-negotiable rules
- **Human approval:** nothing is accepted without a reviewer's approval.
- **Agents:** no agent can write to the catalog or push to Git.
- **Untrusted input:** metadata is treated as untrusted data, never as instructions.
- **Honest metrics:** every metric comes from a real run. Benefits that have not been measured are labelled *projected*.

## 6. Still open (not decided here)
- The rate for Sonnet 5 per million tokens.
- The exact compatible versions of PySpark/MCP SDK/libraries for Python 3.14.
- The exact effort per person: the workbook gives about 200 *team-hours*.
