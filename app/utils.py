from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_filename(filename: str) -> str:
    filename = filename.replace("\\", "_").replace("/", "_").strip()
    filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename)
    return filename or f"file_{uuid.uuid4().hex}.pdf"


def file_to_data_uri(path: str | Path) -> str:
    path = Path(path)
    mime_type = mimetypes.guess_type(path.name)[0] or "application/pdf"
    content = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{content}"


def remove_think_blocks(text: str) -> str:
    """Some reasoning models return <think>...</think>. We remove it before JSON parsing."""
    if not text:
        return ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def extract_json_object(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from a raw LLM response."""
    cleaned = remove_think_blocks(text)

    try:
        loaded = json.loads(cleaned)
        if isinstance(loaded, dict):
            return loaded
        return {"value": loaded}
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM output: {cleaned[:500]}")

    return json.loads(match.group(0))


def coerce_value(value: Any, expected_type: str) -> Any:
    if value is None:
        return None

    expected_type = (expected_type or "string").lower()

    if expected_type in {"string", "str", "date"}:
        return str(value).strip() if value is not None else None

    if expected_type in {"number", "float", "int", "integer"}:
        if isinstance(value, (int, float)):
            return value
        cleaned = str(value).replace("€", "").replace("EUR", "").replace(" ", "").replace(",", ".")
        try:
            number = float(cleaned)
            if expected_type in {"int", "integer"}:
                return int(number)
            return number
        except ValueError:
            return value

    if expected_type in {"boolean", "bool"}:
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "yes", "oui", "1"}:
            return True
        if text in {"false", "no", "non", "0"}:
            return False
        return value

    return value
