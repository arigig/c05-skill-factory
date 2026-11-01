# ADR-0002: Claude Sonnet 5 as runtime model, with Haiku 5.5 as fallback

**Status:** Accepted (2026-11-01)

## Context
REQUIREMENTS.md §3 fixes the runtime model as Claude Sonnet 5, but its
pricing was unverified and no fallback strategy was specified. The 14-layer
workbook matrix (Layer 9, Model & AI Gateway) explicitly asks for a fallback
strategy. A cost comparison was done against Haiku 5.5 (the cheaper tier):
Sonnet 5 is $2/$10 per MTok input/output; Haiku 5.5 is $0.10/$0.50 per MTok
(≤100K-token prompts). At this project's scale (a handful of small conversion
calls per run), the absolute cost difference is negligible (~$0.02 vs ~$0.001
per call) against the $4.00 hard stop.

## Decision
Keep Sonnet 5 as the primary runtime model for conversion quality. Add Haiku
5.5 as a live fallback: if a Sonnet 5 call fails after exhausting retries, or
the projected cost of a call would bring cumulative spend within $0.20 of the
$4.00 hard stop, the gateway calls Haiku 5.5 instead and logs the fallback
event. If Haiku 5.5 also fails, the call fails safely — no further
degradation.

## Consequences
- `app/gateway.py` needs fallback branching logic in addition to its existing
  retry loop.
- The cost ledger must distinguish which model actually served each call
  (not just assume Sonnet 5), since cost-per-token differs.
- Pricing for both models is confirmed from Anthropic's official pricing page
  (2026-11-01) and recorded in `config/pricing.json`.
