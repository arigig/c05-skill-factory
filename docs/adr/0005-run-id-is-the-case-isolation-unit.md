# ADR-0005: One conversion run (`run_id`) is the case-isolation unit

**Status:** Accepted (2026-11-01)

## Context
The 14-layer workbook matrix (Layer 7, Memory / State) asks for tenant/case
isolation tests. This is a single-user local app with no multi-tenant
concept, so "case" needed a concrete definition before isolation could be
tested meaningfully.

## Decision
Each conversion run, identified by its `run_id` (UUID), is treated as an
isolated case. Isolation tests must prove that one run's generated files
(`ops/generated_runs/<run_id>/`), sandbox output, and SQLite row never leak
into or get overwritten by another run's.

## Consequences
- `app/pipeline.py` already generates a fresh UUID per run and writes
  generated code to a `run_id`-named subdirectory — this already satisfies
  the isolation unit structurally; Iteration 4 (Phase B) adds explicit tests
  proving it.
- If the app later gains real multi-user support, this definition of "case"
  would need revisiting (e.g. scoping by user/tenant in addition to run).
