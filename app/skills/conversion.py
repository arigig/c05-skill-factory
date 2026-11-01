"""Invokes the miniform_to_python Skill via the model gateway. The skill's
own instructions (SKILL.md) are the trusted system prompt; the CanonicalForm
being converted is untrusted data sent as the user message content.
"""
from pathlib import Path

import anthropic
import yaml

from app.canonical import CanonicalForm
from app.gateway import call_structured

SKILL_PATH = Path("skills/miniform_to_python/SKILL.md")
TOOL_NAME = "generate_python"

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "pydantic_model": {"type": "string"},
        "fastapi_endpoint": {"type": "string"},
        "rule_functions": {"type": "string"},
        "pytest_tests": {"type": "string"},
    },
    "required": ["pydantic_model", "fastapi_endpoint", "rule_functions", "pytest_tests"],
}


def load_skill_instructions() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def get_skill_identity() -> tuple[str, str]:
    """Returns (name, version) parsed from the Skill's YAML frontmatter."""
    text = SKILL_PATH.read_text(encoding="utf-8")
    _, frontmatter, _ = text.split("---", 2)
    meta = yaml.safe_load(frontmatter)
    return meta["name"], meta["version"]


def convert_form(client: anthropic.Anthropic, canonical_form: CanonicalForm, purpose: str = "miniform_to_python") -> dict:
    return call_structured(
        client,
        system_prompt=load_skill_instructions(),
        user_message=canonical_form.model_dump_json(),
        tool_name=TOOL_NAME,
        tool_description="Return the generated Python code for this CanonicalForm.",
        input_schema=OUTPUT_SCHEMA,
        purpose=purpose,
    )
