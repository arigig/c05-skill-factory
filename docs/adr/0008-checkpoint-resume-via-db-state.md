# ADR-0008: Checkpoint/resume driven by persisted DB state, not a separate job queue

**Status:** Accepted (2026-11-02)

## Context
The 14-layer workbook matrix (Layer 7, Memory/State) asks for checkpoint and
resume evidence. The pipeline has three real steps: load+validate (free),
convert (paid API call), sandbox-validate (local Docker, free). A crash
between convert and sandbox-validate should not force re-paying for the
conversion call.

## Decision
`app/db.py`'s `conversion_runs` table gained a `stage` column plus
nullable `generated_code`/`sandbox_output` columns that are filled in as each
step completes (`start_run` → `mark_converted` → `mark_validated`).
`app/pipeline.py`'s `resume_conversion(client, run_id)` re-derives what still
needs to happen purely by checking which columns are already populated:
if `generated_code` is set, skip the paid call and reuse it; if
`sandbox_output` is set, skip re-running the sandbox. `run_conversion_pipeline`
(the "start fresh" entry point) is just `start_run` followed by
`resume_conversion` — there is no separate code path for starting vs.
resuming.

## Consequences
- No job queue, message broker, or background worker needed — resume is just
  "call the same function again with an existing `run_id`." Appropriate for
  this project's single-user local scope.
- The source MiniForm path is stored per-run (`source_miniform_path`) so
  resume doesn't depend on the caller remembering which sample was used.
- A still-open gap: if the process crashes *during* `mark_converted`'s
  `UPDATE` (vanishingly unlikely with SQLite's single-statement commit, but
  not theoretically impossible) the run could be left without a clear
  checkpoint. Not hardened against here — acceptable for a local demo, flagged
  for Iteration 7 if ever taken further.
