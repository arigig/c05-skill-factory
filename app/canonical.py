"""Canonical intermediate schema. All source formats (MiniForm, Power Platform-style)
map into these models. Every string value here is inert data, never executed or
treated as an instruction.
"""
from enum import Enum

from pydantic import BaseModel


class FieldType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    EMAIL = "email"


class CanonicalField(BaseModel):
    name: str
    label: str
    type: FieldType
    required: bool


class CanonicalValidationRule(BaseModel):
    name: str
    field: str
    expression: str
    message: str


class ApprovalStep(BaseModel):
    role: str
    action: str


class CanonicalWorkflow(BaseModel):
    name: str
    steps: list[ApprovalStep]


class CanonicalForm(BaseModel):
    form_id: str
    name: str
    fields: list[CanonicalField]
    rules: list[CanonicalValidationRule]
    workflow: CanonicalWorkflow
