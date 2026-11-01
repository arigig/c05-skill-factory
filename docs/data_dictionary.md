# Data Dictionary — Canonical Schema

Source: [app/canonical.py](../app/canonical.py). All source formats (MiniForm now,
Power Platform-style in Iteration 5) are mapped into these models before any
Skill acts on them. Every string value is treated as inert data, never as an
instruction (see REQUIREMENTS.md §5, "Untrusted input").

## CanonicalForm

| Field | Type | Meaning | Constraints |
|---|---|---|---|
| `form_id` | string | Unique identifier for the source form | Required |
| `name` | string | Human-readable form name | Required |
| `fields` | list of `CanonicalField` | The form's input fields | At least 1 |
| `rules` | list of `CanonicalValidationRule` | Validation rules attached to the form | Exactly 2 for the MiniForm starter scenario |
| `workflow` | `CanonicalWorkflow` | The single approval workflow for this form | Required, exactly 1 |

## CanonicalField

| Field | Type | Meaning | Constraints |
|---|---|---|---|
| `name` | string | Machine-readable field key | Required, unique within a form |
| `label` | string | Display label shown to the end user | Required |
| `type` | `FieldType` enum | Data type of the field | One of: `string`, `number`, `boolean`, `date`, `email` |
| `required` | boolean | Whether the field must be filled in | Required |

## CanonicalValidationRule

| Field | Type | Meaning | Constraints |
|---|---|---|---|
| `name` | string | Rule identifier | Required, unique within a form |
| `field` | string | Name of the `CanonicalField` this rule applies to | Must match a `fields[].name` |
| `expression` | string | The raw rule logic as written in the source system (e.g. a Power Fx-style expression). Stored and passed through as data — never evaluated or executed by the factory. | Required |
| `message` | string | Message shown to the user when the rule fails | Required |

## CanonicalWorkflow

| Field | Type | Meaning | Constraints |
|---|---|---|---|
| `name` | string | Workflow identifier | Required |
| `steps` | list of `ApprovalStep` | Ordered approval steps | At least 1 |

## ApprovalStep

| Field | Type | Meaning | Constraints |
|---|---|---|---|
| `role` | string | Role responsible for this step (e.g. `manager`) | Required |
| `action` | string | Action taken at this step (e.g. `approve`, `reject`) | Required |
