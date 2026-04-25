from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.schemas import DocumentResult, ExtractionRequest, ExtractorState
from app.nodes.ocr import ocr_pdf_node
from app.nodes.extract import extract_json_node
from app.nodes.validate import parse_and_validate_json_node
from app.nodes.save import save_json_node


def build_graph():
    graph = StateGraph(ExtractorState)

    graph.add_node("ocr_pdf", ocr_pdf_node)
    graph.add_node("extract_json", extract_json_node)
    graph.add_node("parse_and_validate_json", parse_and_validate_json_node)
    graph.add_node("save_json", save_json_node)

    graph.add_edge(START, "ocr_pdf")
    graph.add_edge("ocr_pdf", "extract_json")
    graph.add_edge("extract_json", "parse_and_validate_json")
    graph.add_edge("parse_and_validate_json", "save_json")
    graph.add_edge("save_json", END)

    return graph.compile()


compiled_graph = build_graph()


def run_pdf_extraction(pdf_path: str, filename: str, request: ExtractionRequest) -> DocumentResult:
    final_state = compiled_graph.invoke(
        {
            "pdf_path": pdf_path,
            "filename": filename,
            "request": request,
            "warnings": [],
        }
    )

    return DocumentResult(
        filename=filename,
        data=final_state.get("parsed_json", {}),
        missing_fields=final_state.get("missing_fields", []),
        warnings=final_state.get("warnings", []),
        raw_text_preview=(final_state.get("ocr_text", "")[:800] or None),
        output_json_path=final_state.get("output_json_path"),
    )
