from unittest.mock import MagicMock, patch

from app.loader import load_miniform_file
from app.skills.conversion import OUTPUT_SCHEMA, convert_form

SAMPLE = "tests/fixtures/miniform/valid/expense_request.json"


@patch("app.skills.conversion.call_structured")
def test_convert_form_calls_gateway_with_canonical_data_as_user_message(mock_call_structured):
    mock_call_structured.return_value = {
        "pydantic_model": "class M: pass",
        "fastapi_endpoint": "def endpoint(): pass",
        "rule_functions": "def rule(): pass",
        "pytest_tests": "def test_x(): pass",
    }
    canonical = load_miniform_file(SAMPLE)
    client = MagicMock()

    result = convert_form(client, canonical, purpose="test")

    assert result["pydantic_model"] == "class M: pass"
    _, kwargs = mock_call_structured.call_args
    assert kwargs["input_schema"] == OUTPUT_SCHEMA
    assert canonical.form_id in kwargs["user_message"]
    assert "Untrusted input" in kwargs["system_prompt"]
