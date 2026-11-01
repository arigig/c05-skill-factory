import pytest

from app.cost_ledger import (
    BudgetExceededError,
    check_budget,
    estimate_cost_usd,
    get_cumulative_spend,
    record_spend,
)


def test_estimate_cost_usd_matches_pricing():
    # 1,000,000 input tokens at $2/MTok + 1,000,000 output tokens at $10/MTok
    cost = estimate_cost_usd(1_000_000, 1_000_000)
    assert cost == pytest.approx(12.0)


def test_record_spend_and_cumulative(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    assert get_cumulative_spend(ledger_path) == 0.0

    record_spend(500_000, 100_000, purpose="test-call-1", ledger_path=ledger_path)
    record_spend(500_000, 100_000, purpose="test-call-2", ledger_path=ledger_path)

    expected_each = estimate_cost_usd(500_000, 100_000)
    assert get_cumulative_spend(ledger_path) == pytest.approx(expected_each * 2)


def test_check_budget_raises_when_hard_stop_would_be_exceeded(tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    # Spend close to the $4.00 hard stop.
    record_spend(input_tokens=1_900_000, output_tokens=0, purpose="setup", ledger_path=ledger_path)

    with pytest.raises(BudgetExceededError):
        check_budget(estimated_cost_usd=0.21, ledger_path=ledger_path)

    # A small-enough call should still be allowed.
    check_budget(estimated_cost_usd=0.01, ledger_path=ledger_path)
