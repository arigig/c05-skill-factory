from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import anthropic
import httpx2
import pytest

from app.cost_ledger import BudgetExceededError
from app.gateway import GatewayError, call_structured


def make_response(tool_input: dict, input_tokens: int = 100, output_tokens: int = 50):
    block = SimpleNamespace(type="tool_use", name="convert", input=tool_input)
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=[block], usage=usage)


@patch("app.gateway.record_spend")
@patch("app.gateway.check_budget")
def test_call_structured_returns_tool_input(mock_check_budget, mock_record_spend):
    client = MagicMock()
    client.messages.create.return_value = make_response({"result": "ok"})

    result = call_structured(
        client,
        system_prompt="system",
        user_message="untrusted data here",
        tool_name="convert",
        tool_description="desc",
        input_schema={"type": "object"},
        purpose="test",
    )

    assert result == {"result": "ok"}
    mock_check_budget.assert_called_once()
    mock_record_spend.assert_called_once()


@patch("app.gateway.record_spend")
@patch("app.gateway.check_budget")
def test_call_structured_retries_on_transient_error(mock_check_budget, mock_record_spend):
    client = MagicMock()
    connection_error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    client.messages.create.side_effect = [connection_error, make_response({"result": "ok"})]

    with patch("app.gateway.time.sleep"):
        result = call_structured(
            client,
            system_prompt="system",
            user_message="data",
            tool_name="convert",
            tool_description="desc",
            input_schema={"type": "object"},
            purpose="test",
        )

    assert result == {"result": "ok"}
    assert client.messages.create.call_count == 2


@patch("app.gateway.record_spend")
@patch("app.gateway.check_budget")
def test_call_structured_raises_after_exhausting_retries(mock_check_budget, mock_record_spend):
    client = MagicMock()
    connection_error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    client.messages.create.side_effect = connection_error

    with patch("app.gateway.time.sleep"):
        with pytest.raises(GatewayError):
            call_structured(
                client,
                system_prompt="system",
                user_message="data",
                tool_name="convert",
                tool_description="desc",
                input_schema={"type": "object"},
                purpose="test",
            )

    assert mock_record_spend.call_count == 0


@patch("app.gateway.check_budget", side_effect=BudgetExceededError("over budget"))
def test_call_structured_stops_before_calling_client_when_over_budget(mock_check_budget):
    client = MagicMock()

    with pytest.raises(BudgetExceededError):
        call_structured(
            client,
            system_prompt="system",
            user_message="data",
            tool_name="convert",
            tool_description="desc",
            input_schema={"type": "object"},
            purpose="test",
        )

    client.messages.create.assert_not_called()
