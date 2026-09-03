"""收盘简报路由（只读磁盘冻结文件，判定权在预计算层）。

``GET /api/daily-brief/latest``     最近一份（同日收盘版优先于盘中版）
``GET /api/daily-brief/dates``      可用日期列表（降序，调试/切换用）
``GET /api/daily-brief/{date}``     指定日期（YYYY-MM-DD）
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from lei_signal import dailybrief as db

router = APIRouter(prefix="/api/daily-brief", tags=["daily-brief"])

_NOT_GENERATED = "尚未生成简报，请先跑 scripts/precompute_daily_brief.py"


@router.get("/latest")
def latest() -> dict:
    if not db.BRIEF_DIR.exists():
        raise HTTPException(status_code=404, detail=_NOT_GENERATED)
    for f in sorted(db.BRIEF_DIR.glob("*.json"), reverse=True):
        doc = db.load_brief(f.stem)
        if not doc or not doc.get("versions"):
            continue
        # 同日：收盘版优先
        for slot in (db.SLOT_CLOSE, db.SLOT_INTRADAY):
            v = doc["versions"].get(slot)
            if v:
                return {"date": doc["date"], "slot": slot, "brief": v,
                        "slots_available": sorted(doc["versions"].keys())}
    raise HTTPException(status_code=404, detail=_NOT_GENERATED)


@router.get("/dates")
def dates() -> dict:
    out: list[str] = []
    if db.BRIEF_DIR.exists():
        out = sorted((f.stem for f in db.BRIEF_DIR.glob("*.json")), reverse=True)
    return {"dates": out[:60]}


@router.get("/{day}")
def by_date(day: str, slot: str | None = None) -> dict:
    """指定日期简报；带 ?slot= 时返回指定槽位（不存在则 404），否则收盘版优先。"""
    doc = db.load_brief(day)
    if not doc or not doc.get("versions"):
        raise HTTPException(status_code=404, detail=f"该日无简报: {day}")
    if slot:
        v = doc["versions"].get(slot)
        if not v:
            raise HTTPException(
                status_code=404,
                detail=f"该日无 {slot} 槽位简报: {day}（现有: {sorted(doc['versions'].keys())}）",
            )
        return {"date": doc["date"], "slot": slot, "brief": v,
                "slots_available": sorted(doc["versions"].keys())}
    for s in (db.SLOT_CLOSE, db.SLOT_INTRADAY):
        v = doc["versions"].get(s)
        if v:
            return {"date": doc["date"], "slot": s, "brief": v,
                    "slots_available": sorted(doc["versions"].keys())}
    raise HTTPException(status_code=404, detail=f"该日无简报: {day}")
