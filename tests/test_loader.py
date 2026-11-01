import json
from pathlib import Path

import pytest

from app.loader import MiniFormLoadError, load_miniform_file
from app.provenance import record_provenance

FIXTURES = Path("tests/fixtures/miniform")
GOLDEN = Path("tests/golden")

VALID_SAMPLES = ["expense_request", "leave_request", "equipment_request"]
INVALID_SAMPLES = ["unknown_field_type", "missing_rule_and_workflow"]


@pytest.mark.parametrize("name", VALID_SAMPLES)
def test_valid_sample_matches_golden(name):
    canonical = load_miniform_file(FIXTURES / "valid" / f"{name}.json")
    expected = json.loads((GOLDEN / f"{name}.json").read_text(encoding="utf-8"))
    assert json.loads(canonical.model_dump_json()) == expected


@pytest.mark.parametrize("name", INVALID_SAMPLES)
def test_invalid_sample_is_rejected(name):
    with pytest.raises(MiniFormLoadError):
        load_miniform_file(FIXTURES / "invalid" / f"{name}.json")


def test_injection_sample_loads_as_inert_data():
    canonical = load_miniform_file(FIXTURES / "injection" / "injection_attempt.json")
    # The text is preserved verbatim as plain string data...
    assert "IGNORE PREVIOUS INSTRUCTIONS" in canonical.name
    # ...but nothing about it changes program behavior: it's still a normal
    # CanonicalForm instance with ordinary fields, not an executed command.
    assert canonical.form_id == "injection_attempt"
    assert isinstance(canonical.name, str)
    assert all(isinstance(r.expression, str) for r in canonical.rules)


def test_lineage_is_recorded_for_every_sample(tmp_path):
    log_path = tmp_path / "log.jsonl"
    samples = (
        [(FIXTURES / "valid" / f"{n}.json", "accepted") for n in VALID_SAMPLES]
        + [(FIXTURES / "invalid" / f"{n}.json", "rejected") for n in INVALID_SAMPLES]
    )

    for path, expected_outcome in samples:
        try:
            load_miniform_file(path)
            outcome = "accepted"
        except MiniFormLoadError as exc:
            outcome = "rejected"
            record_provenance(path, outcome, detail=str(exc), log_path=log_path)
            assert outcome == expected_outcome
            continue
        record_provenance(path, outcome, log_path=log_path)
        assert outcome == expected_outcome

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(samples)
    entries = [json.loads(line) for line in lines]
    assert all({"timestamp", "source", "sha256", "outcome"} <= entry.keys() for entry in entries)
    accepted = [e for e in entries if e["outcome"] == "accepted"]
    rejected = [e for e in entries if e["outcome"] == "rejected"]
    assert len(accepted) == len(VALID_SAMPLES)
    assert len(rejected) == len(INVALID_SAMPLES)
