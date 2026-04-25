from __future__ import annotations

import json
import os
from groq import Groq

from app.schemas import ExtractorState


def _build_prompt(state: ExtractorState) -> str:
    request = state["request"]
    fields_description = "\n".join(
        [
            f'- "{field.name}" ({field.type}) : {field.description}. '
            f'Required: {field.required}'
            for field in request.fields
        ]
    )

    expected_json_template = {
        field.name: None for field in request.fields
    }

    return f"""
You are a strict document information extraction engine.

Document type hint:
{request.document_type_hint or "unknown"}

Fields to extract:
{fields_description}

Extra instructions:
{request.extra_instructions or "None"}

Rules:
- Return ONLY one raw JSON object.
- No markdown, no explanation, no comments.
- Use exactly the requested keys.
- If a value is not present in the document, return null.
- Do not invent values.
- Numbers must be valid JSON numbers when possible.
- Dates should be normalized to YYYY-MM-DD when possible.
- Keep French field names exactly as requested.

Expected JSON shape:
{json.dumps(expected_json_template, ensure_ascii=False, indent=2)}

OCR text:
{state.get("ocr_text", "")}
""".strip()


def extract_json_node(state: ExtractorState) -> ExtractorState:
    """Node 2: OCR text -> raw JSON string using Groq."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Put it in .env or environment variables.")

    model = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
    client = Groq(api_key=api_key)
    prompt = _build_prompt(state)

    completion = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You extract structured JSON from OCR text. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    raw_output = completion.choices[0].message.content or "{}"
    return {"raw_llm_output": raw_output}
