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
- **Runtime model:** the app calls **Claude Sonnet 5** through the Claude API at run time. Pricing verified 01-Nov-2026: $2/MTok input, $10/MTok output (`config/pricing.json`).
- **Model fallback:** if a Sonnet 5 call fails after exhausting retries, or the projected cost would bring cumulative spend within $0.20 of the $4.00 hard stop, the gateway falls back to **Haiku 5.5** for that call and logs the fallback event. If Haiku 5.5 also fails, the call fails safely (no silent further degradation).
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
| 4 | **Remaining layers** (see §7 for the full 14-layer matrix): five agents (Discovery, Mapping, Conversion, Validation, Reviewer) with routing/handoffs, per-agent tool permissions, retries, timeouts and safe stop, with agent-graph/state-transition trace evidence; BM25 search over standards, rules and templates with a defined corpus/chunking strategy, citations, source access boundaries, and retrieval tests (hit rate, precision@k); checkpoint and resume with a state schema (job state, mappings, skill/version selections, results, reviewer checkpoints) and case-isolation tests (one `run_id` = one case); MCP tool with a documented schema/contract, least privilege, input validation, approval-before-write, audit log and negative tests; evaluation harness with golden-set + negative-input cases, a lightweight LLM judge (with documented limitations) and defect-to-fix evidence; threat model covering prompt injection, data leakage, tool abuse, secrets and access control, plus red-team cases and a control matrix; traces/dashboard covering prompts, retrieval, tool calls, latency, token/cost, outcomes and errors, with alerts and an incident scenario; roles (submitter/reviewer login) | Every one of the 14 layers has an evidence file under `docs/evidence/` meeting the pass/fail check in §7. This is the Gate 2 slice |
| 5 | **Upgrade to Power Platform-style:** new parser that maps exports to the same canonical schema, plus Skills for forms, Power Fx-style rules and flows; existing Skills reused | Golden set passes for both source types; reuse rate is reported |
| 6 | **React UI:** replaces the HTML page and keeps the same API contract | All UI checks from iteration 3 pass in React |
| 7 | **Hardening and handover:** CI gates (tests, secret scan, recorded-response evaluation regression), release notes, ADRs, runbook including rollback, value case (measured vs projected), RACI | Final checklist complete and demo recorded |

## 5. Non-negotiable rules
- **Human approval:** nothing is accepted without a reviewer's approval.
- **Agents:** no agent can write to the catalog or push to Git.
- **Untrusted input:** metadata is treated as untrusted data, never as instructions.
- **Honest metrics:** every metric comes from a real run. Benefits that have not been measured are labelled *projected*.
- **Case isolation:** each conversion run (`run_id`) is an isolated case. No run's generated files, state, or sandbox output may be visible to or affect another run.

## 6. Still open (not decided here)
- The exact compatible versions of PySpark/MCP SDK/libraries for Python 3.14.
- The exact effort per person: the workbook gives about 200 *team-hours*.
- **Branch protection:** this public repo is on GitHub's free tier. No GitHub-enforced branch protection rule is configured. The only controls are documented convention: `CLAUDE.md`'s ask-before-push rule, and "CI must be green" before any merge. This is a documented policy, not a platform-enforced one — record as an accepted risk, not a gap to silently close.

## 7. 14-layer evidence matrix (workbook alignment)

Source: *C05 Application Migration Skill Factory – 14-Layer Build Requirement Matrix*, workbook *Build Requirements* sheet rows 61–74, capstone C05 (transcribed 01-Nov-2026). This section is the authoritative mapping of REQUIREMENTS.md onto the workbook's 14 layers, per Iteration 4's done-when check. Metric targets below are **project-set** (the workbook names metric categories, not numeric targets) and are separate from "projected" business benefits (§5 Honest metrics still applies: these are pass/fail engineering thresholds, not value claims).

Decisions resolved for this project:
- **LLM judge:** included in the evaluation harness (It-4). Uses Sonnet 5 or Haiku 5.5 to score generated code against a rubric (schema fidelity, rule-logic correctness, no unsupported/fabricated claims in generated comments). Its limitations (non-deterministic, not a substitute for human review) are documented alongside its output.
- **Retrieval:** BM25 only, no reranking. Rationale: the standards/rules/templates corpus for this project is small and synthetic (expected <50 documents); reranking adds complexity disproportionate to corpus size at this scale. Revisit if the corpus grows materially.
- **Fallback model:** Haiku 5.5, see §3.
- **Case isolation unit:** one `run_id` = one case, see §5.

| # | Layer | Evidence file (`docs/evidence/`) | Iteration(s) | Pass/fail check | Key metrics (project-set targets) |
|---|---|---|---|---|---|
| 1 | UI / Experience | `01-ui-experience.md` | It-1, 3, 6 | Page shows input, result/evidence, approve/reject action, and error states; screenshots attached | Task completion ≥90% of attempted conversions reach a final approve/reject decision; reviewer acceptance demonstrated on ≥1 real run |
| 2 | Application / API Services | `02-api-services.md` | It-1, 3 | All endpoints have integration tests; errors return structured 4xx/5xx with a clear detail message | API error rate <5% under normal (non-negative-test) use; p95 latency <2s for non-model endpoints |
| 3 | Agent Orchestration | `03-agent-orchestration.md` | It-4 | Agent graph diagram + trace log of a real run showing routing/handoffs between all 5 agents and the human approval gate | Orchestration success rate ≥80% without manual intervention; ≤3 retries per step; 0 unhandled tool errors |
| 4 | Prompt, Skill & Instruction | `04-prompt-skill-instruction.md` | It-3, 5 | `SKILL.md` versioned with a change log; positive/negative tests pass | Skill test pass rate = 100%; ≥1 skill reused across MiniForm and Power Platform-style sources (It-5) |
| 5 | Data & Ingestion | `05-data-ingestion.md` | It-2, 5 | Data dictionary, loader, validation report, lineage record all present and tested | Completeness = 100% of required canonical fields populated for valid samples; 0 false positives/negatives on the golden+invalid set |
| 6 | Knowledge Fabric / RAG | `06-knowledge-fabric-rag.md` | It-4 | Indexed corpus with documented chunking strategy; retrieval API returns citations resolving to real source documents; retrieval test suite | Hit rate ≥80% on a test query set; precision@5 ≥0.6; citation correctness = 100% |
| 7 | Memory / State | `07-memory-state.md` | It-4 | State schema documented; checkpoint/resume demonstrated on a real run; isolation test proves one `run_id`'s state never leaks into another's | Resume success = 100% on the checkpoint/resume test; 0 state errors; isolation tests 100% pass |
| 8 | Enterprise Tools / MCP | `08-enterprise-tools-mcp.md` | It-4 | Tool schema/contract documented; least-privilege scope defined; write actions require approval; audit log of calls; negative tests | Tool success ≥95% on valid calls; 100% of invalid/negative calls blocked |
| 9 | Model & AI Gateway | `09-model-ai-gateway.md` | It-3 | Structured output validated against JSON schema; retry/rate-limit handling and fallback demonstrated; cost/token log | Every call's latency, tokens and cost logged; cumulative spend ≤$4.00 hard stop enforced |
| 10 | Evaluation & Quality | `10-evaluation-quality.md` | It-2, 4, 5 | Automated harness runs golden set + negative inputs + LLM judge; defect-to-fix evidence for ≥1 real finding | Task success ≥80% on golden set; 0 unflagged unsupported claims; 100% regression pass on re-run |
| 11 | Security, RAI & Governance | `11-security-rai-governance.md` | It-4, 7 | Threat model + control matrix covering prompt injection, data leakage, tool abuse, secrets, unsafe outputs, access control; red-team cases executed | 0 critical gaps open at Gate 2; 100% of red-team injection cases neutralized (treated as inert data) |
| 12 | Observability / LLMOps | `12-observability-llmops.md` | It-4, 7 | Trace sample covering prompts, retrieval, tool calls, latency, token/cost, outcomes, errors; dashboard; incident scenario + runbook with rollback | p95 latency and cost/task logged; error rate <5% |
| 13 | Deployment / DevSecOps | `13-deployment-devsecops.md` | It-1, 7 | Dockerfile, CI pipeline definition, release notes, ADR; human approval step documented before release | Build pass = 100% CI green; `docker compose up` deployment succeeds without error |
| 14 | Value & Adoption | `14-value-adoption.md` | It-5, 7 | One-page value case (measured vs projected), RACI, adoption backlog, handover checklist | Reuse rate, artifact acceptance rate, rework rate and test coverage all reported from real runs (labelled projected where not yet measured) |
