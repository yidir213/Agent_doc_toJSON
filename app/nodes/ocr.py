from __future__ import annotations

import os
from pathlib import Path
from pypdf import PdfReader
import base64
import os

from app.schemas import ExtractorState
from app.utils import file_to_data_uri

def encode_file(file_path):
    with open(file_path, "rb") as pdf_file:
        return base64.b64encode(pdf_file.read()).decode('utf-8')


def _mistral_client():
    """Compatible with recent and older mistralai SDK imports."""
   
    from mistralai.client import Mistral  

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return None
    return Mistral(api_key=api_key)


def _extract_text_with_pypdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n\n".join(pages).strip()


def ocr_pdf_node(state: ExtractorState) -> ExtractorState:
    """
    Node 1: PDF -> text.

    Priority:
    1. Mistral OCR if MISTRAL_API_KEY is configured.
    2. pypdf fallback for text-based PDFs.
    """
    pdf_path = state["pdf_path"]
    warnings = list(state.get("warnings", []))

    client = _mistral_client()
    if client is None:
        warnings.append("MISTRAL_API_KEY not found: using pypdf fallback. Scanned PDFs may fail.")
        return {"ocr_text": _extract_text_with_pypdf(pdf_path), "warnings": warnings}

    try:
        data_uri =encode_file(pdf_path)
        ocr_response = client.ocr.process(
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{data_uri}"
            },
            model="mistral-ocr-latest",
            include_image_base64=True,
        )

        text = "\n\n".join([page.markdown for page in ocr_response.pages]).strip()
        if not text:
            warnings.append("Mistral OCR returned empty text; using pypdf fallback.")
            text = _extract_text_with_pypdf(pdf_path)

        return {"ocr_text": text, "warnings": warnings}

    except Exception as exc:
        warnings.append(f"Mistral OCR failed: {exc}. Using pypdf fallback. ")
        return {"ocr_text": _extract_text_with_pypdf(pdf_path), "warnings": warnings}
