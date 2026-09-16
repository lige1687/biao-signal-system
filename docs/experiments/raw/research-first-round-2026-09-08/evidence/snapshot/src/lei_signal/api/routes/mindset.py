"""认知与心态页 REST 路由（/mindset）。

用途：沉淀调研得来的认知/心态/纪律/复盘观点（首个来源=小红书博主「文主任」
2026-09-05 调研，种子见 configs/mindset_seed.json），以判断题卡片形式供用户
逐条评价（认可/中立/不认可），认可项进入"篮子"供温习；用户也可新增自己的
认知与复盘。纯个人知识管理，不参与任何信号判定——与策略体系无关，属叙事
标注层之外的独立记录层。

设计：
- 存储复用主 sqlite（app.state.mindset_db_path，默认 config.sqlite_path()），
  独立表 mindset_items，首次访问自动建表并导入种子（按 seed_key 幂等去重，
  后续增补种子文件不会重复插入）。
- seed 来源支持覆盖（app.state.mindset_seed_path），单测用小种子文件。
"""
from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api/mindset", tags=["mindset"])

CATEGORIES = ("认知", "心态", "纪律", "复盘")
STATUSES = ("unevaluated", "agree", "neutral", "disagree")
Status = Literal["unevaluated", "agree", "neutral", "disagree"]

# routes/ 在 src/lei_signal/api/routes/ 下，上溯 4 层才是仓库根（parents[3]
# 是 src/——2026-09-07 前的缺陷：默认种子路径指向 src/configs/ 不存在文件）
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_SEED = _REPO_ROOT / "configs" / "mindset_seed.json"


class MindsetItemDTO(BaseModel):
    id: str
    category: str
    text: str
    quote: str | None = None
    source: str = ""
    origin: str = "user"  # seed:<名字> | user
    status: Status = "unevaluated"
    review_count: int = 0
    last_reviewed_at: str | None = None
    created_at: str = ""


class MindsetSummaryDTO(BaseModel):
    total: int = 0
    unevaluated: int = 0
    agree: int = 0
    neutral: int = 0
    disagree: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)


class SeedMeta(BaseModel):
    """种子文件元信息：读没读到、是否完好、本次导入几条（可识别降级）。"""
    available: bool
    status: str          # ok / missing / corrupt
    path: str
    imported_now: int = 0
    note: str = ""


class MindsetListResponse(BaseModel):
    items: list[MindsetItemDTO]
    summary: MindsetSummaryDTO
    seed: SeedMeta | None = None


class MindsetStatusRequest(BaseModel):
    status: Status


class MindsetCreateRequest(BaseModel):
    category: Literal["认知", "心态", "纪律", "复盘"]
    text: str = Field(min_length=2, max_length=500)
    quote: str | None = Field(default=None, max_length=300)
    source: str = Field(default="自己记录", max_length=120)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "mindset_db_path", None) or default_db()


def _seed_path(request: Request) -> Path:
    return Path(getattr(request.app.state, "mindset_seed_path", None) or _DEFAULT_SEED)


def _seed_key(text: str, source: str) -> str:
    return hashlib.sha1(f"{text}|{source}".encode("utf-8")).hexdigest()[:16]


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mindset_items (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            text TEXT NOT NULL,
            quote TEXT,
            source TEXT DEFAULT '',
            origin TEXT DEFAULT 'user',
            seed_key TEXT,
            status TEXT DEFAULT 'unevaluated',
            review_count INTEGER DEFAULT 0,
            last_reviewed_at TEXT,
            created_at TEXT DEFAULT ''
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mindset_status ON mindset_items(status)")
    conn.commit()


def _import_seed(conn: sqlite3.Connection, seed_path: Path) -> int | str:
    """幂等导入种子文件：按 seed_key 去重，返回本次新插入条数；损坏返回 "corrupt"。

    返回 int=正常（0 也正常：已导入过或空文件）；"corrupt"=JSON 损坏——
    调用方据此在 seed 元信息里如实标注，不静默吞掉也不阻断列表。
    """
    if not seed_path.is_file():
        return 0
    try:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return "corrupt"
    rows = data.get("items") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return "corrupt"
    inserted = 0
    for row in rows:
        text = str(row.get("text", "")).strip()
        if not text:
            continue
        source = str(row.get("source", "")).strip()
        category = row.get("category", "认知")
        if category not in CATEGORIES:
            category = "认知"
        key = _seed_key(text, source)
        exists = conn.execute(
            "SELECT 1 FROM mindset_items WHERE seed_key = ?", (key,)
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """INSERT INTO mindset_items
               (id, category, text, quote, source, origin, seed_key, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'unevaluated', ?)""",
            (
                uuid.uuid4().hex[:12],
                category,
                text,
                row.get("quote"),
                source,
                f"seed:{row.get('origin', seed_path.stem)}",
                key,
                _now(),
            ),
        )
        inserted += 1
    conn.commit()
    return inserted


def _row_to_dto(r: sqlite3.Row) -> MindsetItemDTO:
    return MindsetItemDTO(
        id=r["id"],
        category=r["category"],
        text=r["text"],
        quote=r["quote"],
        source=r["source"] or "",
        origin=r["origin"] or "user",
        status=r["status"] or "unevaluated",
        review_count=r["review_count"] or 0,
        last_reviewed_at=r["last_reviewed_at"],
        created_at=r["created_at"] or "",
    )


def _summary(conn: sqlite3.Connection) -> MindsetSummaryDTO:
    s = MindsetSummaryDTO()
    for r in conn.execute(
        "SELECT status, COUNT(*) AS n FROM mindset_items GROUP BY status"
    ):
        s.total += r["n"]
        setattr(s, r["status"], r["n"])
    for r in conn.execute(
        "SELECT category, COUNT(*) AS n FROM mindset_items GROUP BY category"
    ):
        s.by_category[r["category"]] = r["n"]
    return s


@router.get("/items", response_model=MindsetListResponse)
def list_items(
    request: Request,
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
) -> MindsetListResponse:
    seed_path = _seed_path(request)
    with closing(connect(_db_path(request))) as conn:
        _ensure_table(conn)
        imported = _import_seed(conn, seed_path)
        if not seed_path.is_file():
            seed_meta = SeedMeta(
                available=False, status="missing", path=str(seed_path),
                note="种子文件不存在——首启导入未发生，库里只有用户自建条目")
        elif imported == "corrupt":
            seed_meta = SeedMeta(
                available=False, status="corrupt", path=str(seed_path),
                note="种子文件 JSON 损坏——本次跳过导入，既有条目不受影响")
        else:
            seed_meta = SeedMeta(
                available=True, status="ok", path=str(seed_path),
                imported_now=int(imported))
        sql = "SELECT * FROM mindset_items"
        conds, args = [], []
        if status:
            if status not in STATUSES:
                raise HTTPException(400, f"status 取值必须是 {STATUSES} 之一")
            conds.append("status = ?")
            args.append(status)
        if category:
            if category not in CATEGORIES:
                raise HTTPException(400, f"category 取值必须是 {CATEGORIES} 之一")
            conds.append("category = ?")
            args.append(category)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY created_at DESC, id"
        items = [_row_to_dto(r) for r in conn.execute(sql, args)]
        return MindsetListResponse(items=items, summary=_summary(conn),
                                   seed=seed_meta)


@router.post("/items", response_model=MindsetItemDTO, status_code=201)
def create_item(request: Request, payload: MindsetCreateRequest) -> MindsetItemDTO:
    item_id = uuid.uuid4().hex[:12]
    now = _now()
    with closing(connect(_db_path(request))) as conn:
        _ensure_table(conn)
        conn.execute(
            """INSERT INTO mindset_items
               (id, category, text, quote, source, origin, seed_key, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'user', NULL, 'unevaluated', ?)""",
            (item_id, payload.category, payload.text.strip(), payload.quote, payload.source, now),
        )
        conn.commit()
        r = conn.execute("SELECT * FROM mindset_items WHERE id = ?", (item_id,)).fetchone()
        return _row_to_dto(r)


@router.patch("/items/{item_id}/status", response_model=MindsetItemDTO)
def set_status(
    request: Request, item_id: str, payload: MindsetStatusRequest
) -> MindsetItemDTO:
    with closing(connect(_db_path(request))) as conn:
        _ensure_table(conn)
        cur = conn.execute(
            "UPDATE mindset_items SET status = ? WHERE id = ?",
            (payload.status, item_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "条目不存在")
        conn.commit()
        r = conn.execute("SELECT * FROM mindset_items WHERE id = ?", (item_id,)).fetchone()
        return _row_to_dto(r)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(request: Request, item_id: str):
    with closing(connect(_db_path(request))) as conn:
        _ensure_table(conn)
        r = conn.execute("SELECT origin FROM mindset_items WHERE id = ?", (item_id,)).fetchone()
        if r is None:
            raise HTTPException(404, "条目不存在")
        if r["origin"] != "user":
            raise HTTPException(409, "调研来源的条目不可删除（可用\"不认可\"归档），自己新增的才可删")
        conn.execute("DELETE FROM mindset_items WHERE id = ?", (item_id,))
        conn.commit()


@router.get("/review/next", response_model=MindsetItemDTO | None)
def review_next(request: Request) -> MindsetItemDTO | None:
    """从"篮子"（认可项 + 自己新增项）随机抽一条温习，并记一次复习。

    没有可温习条目时返回 null（前端显示空态）。
    """
    with closing(connect(_db_path(request))) as conn:
        _ensure_table(conn)
        rows = conn.execute(
            "SELECT * FROM mindset_items WHERE status IN ('agree', 'neutral') "
            "OR origin = 'user'"
        ).fetchall()
        if not rows:
            return None
        pick = random.choice(rows)
        conn.execute(
            "UPDATE mindset_items SET review_count = review_count + 1, "
            "last_reviewed_at = ? WHERE id = ?",
            (_now(), pick["id"]),
        )
        conn.commit()
        fresh = conn.execute(
            "SELECT * FROM mindset_items WHERE id = ?", (pick["id"],)
        ).fetchone()
        return _row_to_dto(fresh)
