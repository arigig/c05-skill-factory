"""Model gateway: the only place in the app that talks to the Claude API.
Enforces the token cap and cost hard stop, retries on transient errors, and
always requests structured (tool-call) output rather than free text.
"""
import os
import time

import anthropic

from app.cost_ledger import check_budget, estimate_cost_usd, record_spend

MODEL_NAME = "claude-sonnet-5"
MAX_OUTPUT_TOKENS_PER_CALL = 4096
MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 2

RETRYABLE_ERRORS = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


class GatewayError(Exception):
    """Raised when the gateway cannot produce a usable structured result."""


def build_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise GatewayError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=api_key)


def call_structured(
    client: anthropic.Anthropic,
    system_prompt: str,
    user_message: str,
    tool_name: str,
    tool_description: str,
    input_schema: dict,
    purpose: str,
) -> dict:
    """Calls the model, forcing it to respond via a single tool call whose
    input matches input_schema. Returns the parsed tool input (a dict).
    Untrusted content in user_message is passed as plain data inside the
    message, never as system instructions.
    """
    estimated_input_tokens = len(system_prompt + user_message) // 4
    check_budget(estimate_cost_usd(estimated_input_tokens, MAX_OUTPUT_TOKENS_PER_CALL))

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=MAX_OUTPUT_TOKENS_PER_CALL,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                tools=[
                    {
                        "name": tool_name,
                        "description": tool_description,
                        "input_schema": input_schema,
                    }
                ],
                tool_choice={"type": "tool", "name": tool_name},
            )
            break
        except RETRYABLE_ERRORS as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                raise GatewayError(f"model call failed after {MAX_RETRIES} attempts: {exc}") from exc
            time.sleep(RETRY_BASE_DELAY_SECONDS * attempt)
    else:
        raise GatewayError(f"model call failed: {last_error}")

    record_spend(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        purpose=purpose,
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input

    raise GatewayError("model response did not contain the expected tool call")
