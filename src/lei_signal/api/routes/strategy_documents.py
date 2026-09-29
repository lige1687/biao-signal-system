from fastapi import APIRouter, HTTPException

from lei_signal.api import strategy_documents as sd

router = APIRouter(prefix="/api/strategy-documents", tags=["strategy-documents"])


@router.get("")
def list_strategy_documents() -> dict:
    try:
        return sd.list_documents()
    except sd.StrategyDocumentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{document_id}")
def get_strategy_document(document_id: str) -> dict:
    try:
        document = sd.read_document(document_id)
    except sd.StrategyDocumentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if document is None:
        raise HTTPException(status_code=404, detail="未登记的策略文档")
    return document
