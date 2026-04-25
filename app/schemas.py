from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field


class RequestedField(BaseModel):
    """A field the user wants to extract from the PDF."""

    name: str = Field(..., examples=["numero_facture", "montant_ttc"])
    description: str = Field(..., examples=["Invoice total amount including taxes"])
    type: str = Field("string", examples=["string", "number", "date", "boolean"])
    required: bool = False


class ExtractionRequest(BaseModel):
    """Extraction configuration sent to the graph."""

    fields: List[RequestedField]
    document_type_hint: Optional[str] = Field(
        default=None,
        examples=["facture", "contrat", "dossier candidat", "grille de notation"],
    )
    extra_instructions: Optional[str] = None


class DocumentResult(BaseModel):
    filename: str
    data: Dict[str, Any]
    missing_fields: List[str] = []
    warnings: List[str] = []
    raw_text_preview: Optional[str] = None
    output_json_path: Optional[str] = None


class ExtractorState(TypedDict, total=False):
    # Input
    pdf_path: str
    filename: str
    request: ExtractionRequest

    # Intermediate
    ocr_text: str
    raw_llm_output: str
    parsed_json: Dict[str, Any]

    # Validation/output
    missing_fields: List[str]
    warnings: List[str]
    output_json_path: str
