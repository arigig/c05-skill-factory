# ADR-0006: Include a lightweight LLM judge in the evaluation harness

**Status:** Accepted (2026-11-01)

## Context
The 14-layer workbook matrix (Layer 10, Evaluation & Quality) says to
"document judge limitations," implying an LLM-as-judge is expected.
REQUIREMENTS.md did not originally include one. Adding one means more real
API calls against the $4.00 hard stop.

## Decision
Add a lightweight LLM judge to the evaluation harness (Iteration 4, Phase F).
It scores generated code against a fixed rubric (schema fidelity, rule-logic
correctness, absence of unsupported/fabricated claims in generated comments
or docstrings) using Sonnet 5 or Haiku 5.5. Its known limitations
(non-deterministic scoring, not a substitute for human review, no guarantee
of catching subtle logic errors) are documented alongside every judge run's
output, not just once in a README.

## Consequences
- Each evaluation harness run against the golden set now costs a small
  additional amount per sample judged; this draws on the same $4.00 budget
  as conversion calls and must be tracked in the same cost ledger.
- The judge's verdict is advisory, not a gate: human reviewer approval
  (REQUIREMENTS.md §5) remains the only thing that accepts an artifact into
  the catalog, regardless of judge score.
