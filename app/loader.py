"""Loads a raw MiniForm export, validates it, and maps it to the canonical
schema. All string values (labels, expressions, messages) are copied through
verbatim as data — never parsed as code or treated as instructions.
"""
import json
from pathlib import Path

from pydantic import ValidationError

from app.canonical import (
    ApprovalStep,
    CanonicalField,
    CanonicalForm,
    CanonicalValidationRule,
    CanonicalWorkflow,
    FieldType,
)
from app.miniform_schema import MiniFormExport


class MiniFormLoadError(Exception):
    """Raised when a MiniForm export fails schema validation."""


def parse_miniform(raw: dict) -> MiniFormExport:
    try:
        return MiniFormExport.model_validate(raw)
    except ValidationError as exc:
        raise MiniFormLoadError(str(exc)) from exc


def to_canonical(export: MiniFormExport) -> CanonicalForm:
    fields = [
        CanonicalField(
            name=f.key,
            label=f.label,
            type=FieldType(f.type),
            required=f.required,
        )
        for f in export.form.fields
    ]
    rules = [
        CanonicalValidationRule(
            name=r.id,
            field=r.field,
            expression=r.expression,
            message=r.message,
        )
        for r in export.rules
    ]
    steps = [ApprovalStep(role=a.role, action=a.action) for a in export.workflow.approvals]
    workflow = CanonicalWorkflow(name=export.workflow.name, steps=steps)
    return CanonicalForm(
        form_id=export.form.id,
        name=export.form.name,
        fields=fields,
        rules=rules,
        workflow=workflow,
    )


def load_miniform_file(path: Path) -> CanonicalForm:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    export = parse_miniform(raw)
    return to_canonical(export)
