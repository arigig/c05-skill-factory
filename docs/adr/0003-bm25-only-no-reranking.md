# ADR-0003: BM25-only retrieval, no reranking

**Status:** Accepted (2026-11-01)

## Context
REQUIREMENTS.md §3 fixes retrieval as BM25 keyword search, no embeddings. The
14-layer workbook matrix (Layer 6, Knowledge Fabric / RAG) asks for
"reranking where relevant" and notes that any data/vector technology is
allowed. The corpus for this project — synthetic migration standards, rules,
and templates — is expected to stay small (well under 50 documents).

## Decision
Use BM25 only, with no reranking stage. This satisfies the fixed constraint
(§3) and the workbook's "where relevant" qualifier is read as not applicable
at this corpus size: a reranker's main value is disambiguating among many
plausible matches in a large corpus, which doesn't arise here.

## Consequences
- Retrieval quality (hit rate, precision@5) is bounded by BM25's keyword
  matching, with no semantic smoothing.
- If the corpus grows materially (e.g. real enterprise standards libraries
  in a future, non-synthetic phase), this decision should be revisited.
- Retrieval tests (Phase D, Iteration 4) will validate BM25-only is
  sufficient for the hit rate / precision@5 targets in REQUIREMENTS.md §7.
