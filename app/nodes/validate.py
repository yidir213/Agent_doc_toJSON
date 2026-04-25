from __future__ import annotations

from app.schemas import ExtractorState
from app.utils import coerce_value, extract_json_object


def parse_and_validate_json_node(state: ExtractorState) -> ExtractorState:
    """Node 3: raw LLM output -> clean dict matching requested fields."""
    request = state["request"]
    warnings = list(state.get("warnings", []))

    parsed = extract_json_object(state.get("raw_llm_output", "{}"))

    clean = {}
    missing_fields = []

    for field in request.fields:
        value = parsed.get(field.name)
        if value in [None, "", "null", "None"]:
            value = None
            if field.required:
                missing_fields.append(field.name)

        clean[field.name] = coerce_value(value, field.type)

    unknown_keys = sorted(set(parsed.keys()) - {field.name for field in request.fields})
    if unknown_keys:
        warnings.append(f"LLM returned unknown keys ignored: {unknown_keys}")

    return {
        "parsed_json": clean,
        "missing_fields": missing_fields,
        "warnings": warnings,
    }
