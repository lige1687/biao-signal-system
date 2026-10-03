from fastapi import APIRouter, HTTPException

from lei_signal.api import strategy_documents as sd

router = APIRouter(prefix="/api/strategy-documents", tags=["strategy-documents"])


@router.get("")
def list_strategy_documents() -> dict:
    try:
        return sd.list_documents()
    except sd.StrategyDocumentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/factor-guide")
def list_factor_guide_documents() -> dict:
    try:
        return sd.list_documents(guide=True)
    except sd.StrategyDocumentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/factor-guide/{document_id}")
def get_factor_guide_document(document_id: str) -> dict:
    return _get_document(document_id, guide=True)


def _get_document(document_id: str, *, guide: bool = False) -> dict:
    try:
        document = sd.read_document(document_id, guide=guide)
    except sd.StrategyDocumentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if document is None:
        raise HTTPException(status_code=404, detail="未登记的策略文档")
    return document


@router.get("/{document_id}")
def get_strategy_document(document_id: str) -> dict:
    return _get_document(document_id)
