from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from app.schemas import ExtractorState
from app.utils import ensure_dir, safe_filename


def save_json_node(state: ExtractorState) -> ExtractorState:
    """Node 4: save extracted JSON to disk."""
    output_dir = ensure_dir(os.getenv("OUTPUT_DIR", "outputs"))
    base = safe_filename(state.get("filename", "document.pdf")).rsplit(".", 1)[0]
    output_path = output_dir / f"{base}_{uuid.uuid4().hex[:8]}.json"

    payload = {
        "filename": state.get("filename"),
        "data": state.get("parsed_json", {}),
        "missing_fields": state.get("missing_fields", []),
        "warnings": state.get("warnings", []),
    }

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"output_json_path": str(output_path)}
