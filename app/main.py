from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.graph import run_pdf_extraction
from app.schemas import ExtractionRequest, RequestedField
from app.utils import ensure_dir, safe_filename

load_dotenv()

app = FastAPI(title="LangGraph Email/PDF JSON Extractor")
TMP_DIR = ensure_dir(os.getenv("TMP_DIR", "tmp"))


DEFAULT_FIELDS = [
    RequestedField(name="document_type", description="Type of document", type="string"),
    RequestedField(name="reference_number", description="Document reference or invoice number", type="string"),
    RequestedField(name="document_date", description="Main document date", type="date"),
    RequestedField(name="client_name", description="Client/customer/person name", type="string"),
    RequestedField(name="total_amount", description="Total amount if present", type="number"),
    RequestedField(name="currency", description="Currency such as EUR, USD, DZD", type="string"),
]


def parse_fields(fields: Optional[str]) -> List[RequestedField]:
    """
    Accepted formats:
    1. JSON list:
       [{"name":"montant_ttc","description":"...","type":"number","required":true}]
    2. Comma-separated:
       numero_facture,date_facture,montant_ttc
    """
    if not fields:
        return DEFAULT_FIELDS

    fields = fields.strip()

    try:
        loaded = json.loads(fields)
        if not isinstance(loaded, list):
            raise ValueError("fields JSON must be a list")
        return [RequestedField(**item) for item in loaded]
    except json.JSONDecodeError:
        pass

    return [
        RequestedField(name=name.strip(), description=f"Extract field: {name.strip()}", type="string")
        for name in fields.split(",")
        if name.strip()
    ]


async def save_upload(file: UploadFile) -> Path:
    filename = safe_filename(file.filename or f"document_{uuid.uuid4().hex}.pdf")
    path = TMP_DIR / f"{uuid.uuid4().hex}_{filename}"
    content = await file.read()
    path.write_bytes(content)
    return path


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract-pdfs")
async def extract_pdfs(
    files: List[UploadFile] = File(...),
    fields: Optional[str] = Form(default=None),
    document_type_hint: Optional[str] = Form(default=None),
    extra_instructions: Optional[str] = Form(default=None),
):
    """
    Direct upload endpoint.

    Example:
    curl -X POST http://localhost:8000/extract-pdfs \
      -F 'files=@facture.pdf' \
      -F 'fields=numero_facture,date_facture,montant_ttc'
    """
    request = ExtractionRequest(
        fields=parse_fields(fields),
        document_type_hint=document_type_hint,
        extra_instructions=extra_instructions,
    )

    results = []
    for file in files:
        if not (file.filename or "").lower().endswith(".pdf"):
            continue

        pdf_path = await save_upload(file)
        try:
            result = run_pdf_extraction(str(pdf_path), file.filename or pdf_path.name, request)
            results.append(result.model_dump())
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed processing {file.filename}: {exc}") from exc
        finally:
            if pdf_path.exists():
                pdf_path.unlink()

    return JSONResponse(
        {
            "status": "success",
            "documents_processed": len(results),
            "results": results,
        }
    )


@app.post("/webhooks/sendgrid-inbound")
async def sendgrid_inbound_parse(
    # SendGrid sends email fields as multipart form data.
    sender: Optional[str] = Form(default=None, alias="from"),
    subject: Optional[str] = Form(default=None),
    text: Optional[str] = Form(default=None),
    html: Optional[str] = Form(default=None),
    fields: Optional[str] = Form(default=None),
    document_type_hint: Optional[str] = Form(default=None),
    extra_instructions: Optional[str] = Form(default=None),
    attachment1: Optional[UploadFile] = File(default=None),
    attachment2: Optional[UploadFile] = File(default=None),
    attachment3: Optional[UploadFile] = File(default=None),
    attachment4: Optional[UploadFile] = File(default=None),
    attachment5: Optional[UploadFile] = File(default=None),
):
    """
    Email trigger endpoint for SendGrid Inbound Parse.
    Configure SendGrid to POST emails to this URL.
    """
    attachments = [a for a in [attachment1, attachment2, attachment3, attachment4, attachment5] if a]

    request = ExtractionRequest(
        fields=parse_fields(fields),
        document_type_hint=document_type_hint,
        extra_instructions=extra_instructions,
    )

    results = []
    for attachment in attachments:
        if not (attachment.filename or "").lower().endswith(".pdf"):
            continue

        pdf_path = await save_upload(attachment)
        try:
            result = run_pdf_extraction(str(pdf_path), attachment.filename or pdf_path.name, request)
            results.append(result.model_dump())
        finally:
            if pdf_path.exists():
                pdf_path.unlink()

    return {
        "status": "success",
        "email": {
            "from": sender,
            "subject": subject,
        },
        "documents_processed": len(results),
        "results": results,
    }
