# LangGraph Email/PDF JSON Extractor

This project receives PDF files, runs a full LangGraph workflow, extracts the information you ask for, and returns clean JSON that you can later insert into Excel.

## Workflow

```text
PDF upload or email attachment
    ↓
LangGraph node: OCR PDF with Mistral OCR, fallback to pypdf
    ↓
LangGraph node: extract JSON with Groq
    ↓
LangGraph node: parse + validate JSON
    ↓
LangGraph node: save JSON output
    ↓
API response
```

## Install

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env`:

```env
MISTRAL_API_KEY=...
GROQ_API_KEY=...
GROQ_MODEL=qwen/qwen3-32b
```

## Run locally

```bash
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000/docs
```

## Test direct PDF extraction

Simple fields:

```bash
curl -X POST "http://localhost:8000/extract-pdfs" \
  -F "files=@facture.pdf" \
  -F "fields=numero_facture,date_facture,client,montant_ttc,devise" \
  -F "document_type_hint=facture"
```

More precise schema:

```bash
curl -X POST "http://localhost:8000/extract-pdfs" \
  -F "files=@facture.pdf" \
  -F 'fields=[{"name":"numero_facture","description":"Numéro de facture","type":"string","required":true},{"name":"date_facture","description":"Date de facture","type":"date","required":false},{"name":"montant_ttc","description":"Montant total TTC","type":"number","required":true}]' \
  -F "document_type_hint=facture"
```

## SendGrid email trigger

Configure SendGrid Inbound Parse to POST to:

```text
https://your-domain.com/webhooks/sendgrid-inbound
```

When an email arrives with PDF attachments, the endpoint runs the same LangGraph workflow.

## Important notes

- For scanned PDFs, use `MISTRAL_API_KEY`; otherwise fallback `pypdf` may return empty text.
- The API returns JSON first. Add a separate Excel-writing step after this if needed.
- This project is intentionally strict: if information is missing, the JSON value should be `null`.
