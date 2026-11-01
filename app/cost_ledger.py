"""Tracks every model call's cost and enforces the hard budget stop.
Pricing and budget limits come from config/pricing.json (REQUIREMENTS.md §3).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

PRICING_PATH = Path("config/pricing.json")
DEFAULT_LEDGER_PATH = Path("ops/cost_ledger/ledger.jsonl")


class BudgetExceededError(Exception):
    """Raised when a call would push cumulative spend past the hard stop."""


def _load_pricing() -> dict:
    return json.loads(PRICING_PATH.read_text(encoding="utf-8"))


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    pricing = _load_pricing()["per_million_tokens"]
    return (input_tokens / 1_000_000) * pricing["input"] + (output_tokens / 1_000_000) * pricing["output"]


def get_cumulative_spend(ledger_path: Path = DEFAULT_LEDGER_PATH) -> float:
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return 0.0
    total = 0.0
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            total += json.loads(line)["cost_usd"]
    return total


def check_budget(estimated_cost_usd: float, ledger_path: Path = DEFAULT_LEDGER_PATH) -> None:
    hard_stop = _load_pricing()["budget"]["hard_stop_cumulative_usd"]
    projected = get_cumulative_spend(ledger_path) + estimated_cost_usd
    if projected > hard_stop:
        raise BudgetExceededError(
            f"projected cumulative spend ${projected:.4f} would exceed hard stop ${hard_stop:.2f}"
        )


def record_spend(
    input_tokens: int,
    output_tokens: int,
    purpose: str,
    ledger_path: Path = DEFAULT_LEDGER_PATH,
) -> dict:
    cost_usd = estimate_cost_usd(input_tokens, output_tokens)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "purpose": purpose,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 6),
    }
    ledger_path = Path(ledger_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
