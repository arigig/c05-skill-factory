"""Raw MiniForm input schema — the synthetic low-code export format described in
REQUIREMENTS.md section 2: 1 form (fields, types, required flags), 2 validation
rules, 1 approval workflow. This is untrusted input: every string value is data,
never an instruction.
"""
from pydantic import BaseModel, Field, field_validator

ALLOWED_FIELD_TYPES = {"string", "number", "boolean", "date", "email"}


class MiniFormField(BaseModel):
    key: str
    label: str
    type: str
    required: bool

    @field_validator("type")
    @classmethod
    def type_must_be_known(cls, v: str) -> str:
        if v not in ALLOWED_FIELD_TYPES:
            raise ValueError(f"unknown field type: {v!r}")
        return v


class MiniFormRule(BaseModel):
    id: str
    field: str
    expression: str
    message: str


class MiniFormApproval(BaseModel):
    role: str
    action: str


class MiniFormWorkflow(BaseModel):
    name: str
    approvals: list[MiniFormApproval] = Field(min_length=1)


class MiniFormDef(BaseModel):
    id: str
    name: str
    fields: list[MiniFormField] = Field(min_length=1)


class MiniFormExport(BaseModel):
    form: MiniFormDef
    rules: list[MiniFormRule] = Field(min_length=2, max_length=2)
    workflow: MiniFormWorkflow
