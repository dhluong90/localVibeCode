"""JSON Schemas for Constrained Decoding across ALL 3 PEV Phases (Plan, Execute, Verify)."""

from __future__ import annotations

from typing import Any, Dict

PLAN_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "architectural_summary": {
            "type": "string",
            "description": "Concise explanation of the impact zone and how the change fits Clean Architecture.",
        },
        "atomic_tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step_id": {"type": "integer"},
                    "target_file": {
                        "type": "string",
                        "description": "Relative file path in the repository to modify.",
                    },
                    "instruction": {
                        "type": "string",
                        "description": "Exact surgical coding instructions for this single file.",
                    },
                    "verification_criteria": {
                        "type": "string",
                        "description": "How to verify this specific file modification.",
                    },
                },
                "required": ["step_id", "target_file", "instruction", "verification_criteria"],
            },
        },
    },
    "required": ["architectural_summary", "atomic_tasks"],
}

EXECUTE_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "reasoning": {
            "type": "string",
            "description": "One-sentence explanation of the exact surgical edit applied to the target file.",
        },
        "updated_code": {
            "type": "string",
            "description": "The complete, valid Python source code for the target file ONLY.",
        },
    },
    "required": ["reasoning", "updated_code"],
}

VERIFY_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["PASS", "REPLAN"],
        },
        "compliance_score": {
            "type": "integer",
            "description": "Score from 0 to 100 evaluating adherence to requirement and Enterprise Rules.",
        },
        "review_notes": {
            "type": "string",
            "description": "Detailed QA review findings.",
        },
    },
    "required": ["verdict", "compliance_score", "review_notes"],
}
