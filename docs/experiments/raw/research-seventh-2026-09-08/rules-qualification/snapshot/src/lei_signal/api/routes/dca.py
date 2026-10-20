"""定投模块 REST 路由（/api/dca）——agent 可接入的标准接口。

设计（沿 mindset/copilot 路由先例）：
- 只读现状 + 按归档规则计算清单；判定与数字来自 configs/dca_evidence.json
  证据账本（新实验归档后登记即自动接入）；
- 计划存储复用主 sqlite（app.state.dca_db_path，默认 config.sqlite_path()），
  独立表 dca_plans；预设（十六轮归档口径）只读，用户计划可增删；
- 数据加载器可注入（app.state.dca_data_loader）供单测合成行情；
- 实际成交落账走既有 /copilot/trades（fund_trades 台账），本路由不重复记账。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from lei_signal.api.config import sqlite_path as default_db
from lei_signal.dca import service
from lei_signal.dca.presets import (
    PRESETS,
    VALID_FREQUENCIES,
    VALID_REBALANCE,
)
from lei_signal.dca.state import BreadthReading, default_data_loader, read_breadth
from lei_signal.storage.sqlite_store import connect

router = APIRouter(prefix="/api/dca", tags=["dca"])

# routes/ 在 src/lei_signal/api/routes/ 下，上溯 4 层才是仓库根（parents[3]
# 是 src/——2026-09-07 前的缺陷：默认证据路径指向 src/configs/ 不存在文件）
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_EVIDENCE = _REPO_ROOT / "configs" / "dca_evidence.json"


def _db_path(request: Request) -> str:
    return getattr(request.app.state, "dca_db_path", None) or default_db()


def _evidence_path(request: Request) -> Path:
    return Path(getattr(request.app.state, "dca_evidence_path", None)
                or _DEFAULT_EVIDENCE)


def _loader(request: Request) -> Callable[[str], pd.DataFrame | None]:
    return getattr(request.app.state, "dca_data_loader", None) or \
        default_data_loader()


def _breadth_readings(request: Request) -> dict:
    """一次读两市宽度（值+元信息）。注入覆盖时如实标 unknown（无日期可查）。

    返回 {"cn": BreadthReading, "us": BreadthReading}（market 键：cn_all/sp500）。
    """
    ov = getattr(request.app.state, "dca_breadth_override", None)
    out = {}
    for key, market in (("cn", "cn_all"), ("us", "sp500")):
        if isinstance(ov, dict):
            val = ov.get(key)
            out[key] = BreadthReading(
                market=market, value=val, source="test_override",
                observed_at=None, last_valid_at=None, generated_at=_now(),
                health="unknown",
                reason="宽度由调用方注入，无日期与发布节奏可查")
        else:
            out[key] = read_breadth(market)
    return out


def _broadths(readings: dict) -> tuple[float | None, float | None]:
    return (readings.get("cn").value if readings.get("cn") else None,
            readings.get("us").value if readings.get("us") else None)


def _breadth_refs(readings: dict) -> dict:
    """宽度引用（MarketDataRef 对象，供 service 拼到每行状态里）。"""
    return {k: v.meta() for k, v in readings.items() if v is not None}


def _breadth_meta(readings: dict) -> dict:
    """宽度元信息（dict，直接进响应 JSON）。"""
    return {k: v.meta().to_dict() for k, v in readings.items()
            if v is not None}


def _data_meta(request: Request, readings: dict) -> dict:
    """状态/触发板共用的数据元信息块（证据可用性 + 两市宽度日期）。"""
    ev = service.load_evidence(_evidence_path(request))
    return {
        "evidence": {
            "available": bool(ev.get("available")),
            "error_code": ev.get("error_code"),
            "error_detail": ev.get("error_detail"),
            "version": ev.get("version"),
        },
        "breadth": _breadth_meta(readings),
        "generated_at": _now(),
        "note": "行情数字各自的日期见 breadth[].last_valid_at；实验数字的"
                "来源/状态/窗口见 /api/dca/evidence 的 meta.refs",
    }


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dca_plans (
            plan_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            legs_json TEXT NOT NULL,
            frequency TEXT DEFAULT 'weekly',
            rebalance TEXT DEFAULT 'quarterly',
            base_amount REAL,
            origin TEXT DEFAULT 'user',
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
        """
    )
    conn.commit()


class LegIn(BaseModel):
    code: str = Field(min_length=3, max_length=16)
    name: str = Field(min_length=1, max_length=40)
    role: str = Field(default="", max_length=20)
    state_symbol: str = Field(default="", max_length=16)
    take_profit: float | None = Field(default=None, gt=0, le=3)
    note: str = Field(default="", max_length=200)


class PlanCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    legs: list[LegIn] = Field(min_length=2, max_length=10)
    frequency: str = "weekly"
    rebalance: str = "quarterly"
    base_amount: float | None = Field(default=None, gt=0)


class PlanDTO(BaseModel):
    plan_id: str
    name: str
    legs: list[dict]
    frequency: str
    rebalance: str
    base_amount: float | None = None
    origin: str = "user"
    active: bool = True
    note: str = ""


def _row_to_plan(row: sqlite3.Row) -> PlanDTO:
    return PlanDTO(
        plan_id=row["plan_id"], name=row["name"],
        legs=json.loads(row["legs_json"]),
        frequency=row["frequency"], rebalance=row["rebalance"],
        base_amount=row["base_amount"], origin=row["origin"],
        active=bool(row["active"]),
        note="预设（只读，十六轮归档口径）" if row["origin"] == "preset"
        else "")


@router.get("/plans")
def list_plans(request: Request) -> dict:
    out: list[dict] = []
    for _pid, p in PRESETS.items():
        out.append({"plan_id": p["plan_id"], "name": p["name"],
                    "legs": p["legs"], "frequency": p["frequency"],
                    "rebalance": p["rebalance"], "base_amount": None,
                    "origin": "preset", "active": True,
                    "note": p["note"]})
    with closing(connect(_db_path(request))) as conn, conn:
        _ensure_table(conn)
        rows = conn.execute(
            "SELECT * FROM dca_plans WHERE active = 1 "
            "ORDER BY created_at DESC").fetchall()
        for r in rows:
            out.append(_row_to_plan(r).model_dump())
    return {"plans": out}


@router.post("/plans", status_code=201)
def create_plan(payload: PlanCreateRequest, request: Request) -> dict:
    if payload.frequency not in VALID_FREQUENCIES:
        raise HTTPException(400, f"frequency 需为 {VALID_FREQUENCIES}")
    if payload.rebalance not in VALID_REBALANCE:
        raise HTTPException(400, f"rebalance 需为 {VALID_REBALANCE}")
    legs = [leg.model_dump() for leg in payload.legs]
    plan_id = f"dca_{uuid.uuid4().hex[:8]}"
    with closing(connect(_db_path(request))) as conn, conn:
        _ensure_table(conn)
        conn.execute(
            """INSERT INTO dca_plans
               (plan_id, name, legs_json, frequency, rebalance, base_amount,
                origin, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'user', 1, ?, ?)""",
            (plan_id, payload.name, json.dumps(legs, ensure_ascii=False),
             payload.frequency, payload.rebalance, payload.base_amount,
             _now(), _now()))
    return {"plan_id": plan_id}


def _find_preset(plan_id: str) -> dict | None:
    for p in PRESETS.values():
        if p["plan_id"] == plan_id:
            return p
    return None


def _load_plan(request: Request, plan_id: str) -> dict:
    preset = _find_preset(plan_id)
    if preset is not None:
        return preset
    with closing(connect(_db_path(request))) as conn, conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT * FROM dca_plans WHERE plan_id = ? AND active = 1",
            (plan_id,)).fetchone()
        if row is None:
            raise HTTPException(404, f"计划不存在: {plan_id}")
        return _row_to_plan(row).model_dump()


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: str, request: Request) -> dict:
    if _find_preset(plan_id) is not None:
        raise HTTPException(400, "预设计划只读，不可删除")
    with closing(connect(_db_path(request))) as conn, conn:
        _ensure_table(conn)
        cur = conn.execute(
            "UPDATE dca_plans SET active = 0, updated_at = ? WHERE plan_id = ?",
            (_now(), plan_id))
        if cur.rowcount == 0:
            raise HTTPException(404, f"计划不存在: {plan_id}")
    return {"deleted": plan_id}


@router.get("/plans/{plan_id}/weekly")
def plan_weekly(plan_id: str, request: Request,
                base_amount: float = 1000.0) -> dict:
    if base_amount <= 0:
        raise HTTPException(400, "base_amount 需为正")
    plan = _load_plan(request, plan_id)
    result = service.weekly_buy_list(
        plan["legs"], base_amount,
        frequency=plan.get("frequency", "weekly"),
        rebalance=plan.get("rebalance", "quarterly"))
    result["plan_id"] = plan_id
    result["plan_name"] = plan["name"]
    result["note"] = ("平投，无任何择时旋钮（一~十二轮全部判负）；"
                      "实际成交请经 /copilot/trades 落账")
    return result


@router.get("/state")
def state_board(request: Request, symbols: str | None = None) -> dict:
    syms: list[tuple[str, str]] | None = None
    if symbols:
        from lei_signal.dca.presets import TRACKED
        known = dict(TRACKED)
        syms = []
        for s in symbols.split(","):
            s = s.strip()
            if s not in known:
                raise HTTPException(400, f"未跟踪标的: {s}")
            syms.append((s, known[s]))
    ev = service.load_evidence(_evidence_path(request))
    readings = _breadth_readings(request)
    b_cn, b_us = _broadths(readings)
    states = service.targets_state(_loader(request), ev, syms, b_cn, b_us,
                                   breadth_meta=_breadth_refs(readings))
    return {"states": states,
            "data_meta": _data_meta(request, readings),
            "note": "状态=路牌统计（只提示不判定）；期望为历史分布非预测；"
                    "各状态基于行情 as_of 与宽度 last_valid_at，非实时"}


@router.get("/triggers")
def trigger_board(request: Request) -> dict:
    ev = service.load_evidence(_evidence_path(request))
    readings = _breadth_readings(request)
    b_cn, b_us = _broadths(readings)
    board = service.triggers_board(_loader(request), ev, b200_cn=b_cn,
                                   b200_us=b_us,
                                   breadth_meta=_breadth_refs(readings))
    board["data_meta"] = _data_meta(request, readings)
    return board


@router.get("/evidence")
def evidence_registry(request: Request) -> dict:
    body = service.load_evidence(_evidence_path(request))
    body["meta"] = service.evidence_meta(_evidence_path(request))
    return body
