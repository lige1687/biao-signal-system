#!/usr/bin/env python3
"""跨标的名称绑定修复 S1——隔离路由 before/after 复现（GLM Flash 执行版）。

用法：python3 repro_symbol_binding_fix.py baseline|fixed
  baseline = 修复前跑，名称切换两案例预期复现「仍绑 515880」的已知缺陷；
  fixed    = 修复后跑，全部案例按验收预期强制通过。

改造自 symbol-binding-recheck-2026-09-17 的 controller-recheck-v2 脚本
（核查版），本版差异：
1. 被测代码直接指向本工作区 src（不再是冻结快照），启动即断言
   lei_signal 确从工作区导入；
2. verdict 期望按 baseline/fixed 两种模式切换（同一脚本出 before/after）；
3. 新增显示名检查（resolve 接口 display_name / catalog_names /
   _static_symbol_name 对 000300.SS 应给出「沪深300」）；
4. 硬隔离护栏同等强度：审计钩子先于一切 lei_signal 导入安装，阻断并记录
   全部 DNS/连接、沙箱外写入、真实 .env/业务库读取、非临时 SQLite；
   结束断言四类计数全零，否则退出非零。

全部外部依赖隔离：模型桩（llm._llm_call 与 _request_completion_stream 双路）、
合成行情（AnalysisService.analyze_fn）、一次性临时库、目录/宽度/情绪等
外部数据源在 runner 侧替换（不改产品代码）。证据不是真实模型/真实行情。
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

MODE = sys.argv[1] if len(sys.argv) > 1 else ""
if MODE not in ("baseline", "fixed"):
    raise SystemExit("用法: python3 repro_symbol_binding_fix.py baseline|fixed")

# ================================================================ 0. 护栏先装

RAW = Path(__file__).resolve().parent            # .../raw/agent-glm-symbol-binding-fix-2026-09-18
WORKSPACE = RAW.parents[3]                       # raw/<名>/ → raw → experiments → docs → 工作区根
SRC = WORKSPACE / "src"
LOGS = RAW / "logs"
LOGS.mkdir(exist_ok=True)

RUN_CWD = RAW / "isolated-cwd"
RUN_CWD.mkdir(exist_ok=True)
os.chdir(RUN_CWD)

_TMP = Path(tempfile.mkdtemp(prefix="symbol-binding-fix-20260918-"))
(_TMP / "cache").mkdir()
os.environ["LEI_CACHE_ROOT"] = str(_TMP / "cache")
os.environ["LEI_SQLITE_PATH"] = str(_TMP / "lab.db")
os.environ["LEI_PREHEAT_DISABLED"] = "1"
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

GUARD: dict = {
    "installed_at": datetime.now().isoformat(timespec="seconds"),
    "network_attempts": [],
    "blocked_writes": [],
    "blocked_reads": [],
    "blocked_sqlite": [],
}
_WRITE_ALLOW = (_TMP.resolve(), RUN_CWD.resolve(), RAW.resolve())
_FORBIDDEN_READ_ROOTS = ((Path.home() / ".lei_signal_lab").resolve(),)


def _under(p: Path, root: Path) -> bool:
    try:
        return p.resolve(strict=False).is_relative_to(root)
    except OSError:
        return False


def _in_write_allow(p: Path) -> bool:
    return any(_under(p, a) for a in _WRITE_ALLOW)


def _stack() -> str:
    keep = []
    ws = str(WORKSPACE)
    for fr in traceback.extract_stack()[:-1]:
        if ws in fr.filename or "repro_symbol_binding_fix" in fr.filename:
            keep.append(f"  {fr.filename}:{fr.lineno} in {fr.name} -> {fr.line}")
    return "\n".join(keep[-8:]) or "(no business frames)"


def _audit(event, args):
    if event in ("socket.getaddrinfo", "socket.connect"):
        if event == "socket.connect" and getattr(args[0], "family", None) not in (
                socket.AF_INET, socket.AF_INET6):
            return
        GUARD["network_attempts"].append(
            {"event": event, "detail": str(args)[:200], "stack": _stack()})
        raise RuntimeError("[guard] 网络尝试已被硬隔离阻断（隔离测试禁网）")
    if event == "open":
        path, mode, flags = (args + (None, None))[:3]
        try:
            p = Path(str(path))
        except Exception:  # noqa: BLE001
            return
        mode_s = mode if isinstance(mode, str) else ""
        flags_i = flags if isinstance(flags, int) else 0
        wants_write = ("w" in mode_s or "a" in mode_s or "x" in mode_s
                       or bool(flags_i & (os.O_WRONLY | os.O_RDWR | os.O_CREAT
                                          | os.O_APPEND | os.O_TRUNC)))
        try:
            rp = p.expanduser().resolve(strict=False)
        except OSError:
            return
        if wants_write and not _in_write_allow(rp):
            GUARD["blocked_writes"].append(
                {"path": str(rp)[:300], "mode": mode_s, "stack": _stack()})
            raise RuntimeError("[guard] 沙箱外写入已被阻断")
        if not wants_write:
            if p.name == ".env" and not _in_write_allow(rp):
                GUARD["blocked_reads"].append({"path": str(rp)[:300], "stack": _stack()})
                raise RuntimeError("[guard] 真实 .env 读取已被阻断")
            if any(_under(rp, fr) for fr in _FORBIDDEN_READ_ROOTS):
                GUARD["blocked_reads"].append({"path": str(rp)[:300], "stack": _stack()})
                raise RuntimeError("[guard] 真实业务库/缓存读取已被阻断")
        return
    if event == "sqlite3.connect":
        name = str(args[0]) if args else ""
        if name == ":memory:":
            return
        try:
            rp = Path(name).expanduser().resolve(strict=False)
        except OSError:
            return
        if not _in_write_allow(rp):
            GUARD["blocked_sqlite"].append({"path": str(rp)[:300], "stack": _stack()})
            raise RuntimeError("[guard] 非临时 SQLite 路径已被阻断")
    if event in ("os.remove", "os.rename", "os.rmdir"):
        for t in (str(a) for a in args if isinstance(a, (str, Path))):
            try:
                rp = Path(t).expanduser().resolve(strict=False)
            except OSError:
                continue
            if not _in_write_allow(rp):
                GUARD["blocked_writes"].append(
                    {"path": str(rp)[:300], "mode": event, "stack": _stack()})
                raise RuntimeError("[guard] 沙箱外删除/改名已被阻断")


sys.addaudithook(_audit)

# ================================================================ 1. 导入被测工作区代码

if not (SRC / "lei_signal").is_dir():
    raise SystemExit(f"缺少工作区源码: {SRC}")
sys.path.insert(0, str(SRC))

import pandas as pd  # noqa: E402

import lei_signal  # noqa: E402
import lei_signal.plans.llm as llm  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from lei_signal.api.services import AnalysisService  # noqa: E402
from lei_signal.compose.pipeline import analyze_bars  # noqa: E402
from lei_signal.data.providers import PriceData  # noqa: E402
from lei_signal.data.symbols import resolve_symbol  # noqa: E402
from lei_signal.data.validation import validate_bars  # noqa: E402

assert Path(lei_signal.__file__).resolve().is_relative_to(SRC.resolve()), (
    f"导入的不是工作区源码: {lei_signal.__file__}")

# ---- runner 侧替换全部外部数据源（不改产品代码）----
import lei_signal.env as _envmod  # noqa: E402
_envmod.load_env = lambda *a, **k: None
import lei_signal.api.catalog as _catalog  # noqa: E402
_catalog.concept_boards = lambda **kw: []
import lei_signal.copilot.breadth as _breadth  # noqa: E402
_breadth.a_share_breadth_cn = lambda: None
import lei_signal.market_context.a_share_breadth as _asb  # noqa: E402
_asb.get_a_share_breadth = lambda **kw: None
import lei_signal.market_context.market_mood as _mm  # noqa: E402
_mm.cn_mood = lambda: {}
import lei_signal.fundamentals.sources as _fsrc  # noqa: E402
_fsrc.fetch_margin_history = lambda **kw: []

from lei_signal.api.app import create_app  # noqa: E402  # 必须在打桩之后

# ================================================================ 2. 模型桩（双路）

LLM_CALLS: list[dict] = []


def _capture(material_msgs: list[dict], via: str) -> None:
    entry: dict = {"via": via, "context_kind": None, "display_name": None,
                   "ctx_symbol": None, "facts_symbol": None}
    try:
        user_msg = material_msgs[1]["content"]
        prefix = "当前标的技术材料：\n"
        if user_msg.startswith(prefix):
            payload = json.loads(user_msg[len(prefix):])
            entry["context_kind"] = payload.get("context_kind")
            entry["display_name"] = payload.get("display_name")
            entry["ctx_symbol"] = payload.get("symbol")
            card = payload.get("evidence_card") or {}
            facts = card.get("facts") or {}
            if isinstance(facts, dict):
                entry["facts_symbol"] = facts.get("symbol")
    except Exception as exc:  # noqa: BLE001
        entry["parse_error"] = repr(exc)
    LLM_CALLS.append(entry)


def fake_llm(cfg, msgs):  # noqa: ANN001, ANN002
    _capture(msgs, "nonstream:_llm_call")
    return "首段结论。\n\n其余说明。"


def fake_llm_stream(cfg, msgs):  # noqa: ANN001, ANN002
    _capture(msgs, "stream:_request_completion_stream")
    yield "首段结论。"
    yield "\n\n其余说明。"


llm._llm_call = fake_llm
llm._request_completion_stream = fake_llm_stream
llm.load_ark_config = lambda: llm.ArkConfig(
    api_key="test-only", base_url="https://isolated.invalid", model="isolated-stub")

# ================================================================ 3. 行情桩 + 应用装配


def _bars(n: int = 80) -> pd.DataFrame:
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.5
        rows.append({"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
                     "close": close, "volume": 1_000_000})
    index = pd.bdate_range(start="2024-01-02", periods=n)
    return pd.DataFrame(rows, index=index)[["open", "high", "low", "close", "volume"]]


def fake_analyze(symbol: str, _exclude: frozenset[str] = frozenset(), **kwargs):  # noqa: ANN002, ANN003
    if symbol in _exclude:
        raise RuntimeError(f"[隔离桩] {symbol} 无分析数据（模拟行情源缺失）")
    frame, report = validate_bars(_bars(), symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    price_data = PriceData(symbol=info.symbol, display_name=info.symbol,
                           bars=frame, report=report, info=info)
    return analyze_bars(symbol, frame, price_data=price_data)


def build_app(tag: str, nodata: frozenset[str] = frozenset()) -> TestClient:
    db = str(_TMP / f"lab-{tag}.db")
    service = AnalysisService(
        analyze_fn=lambda s, **kw: fake_analyze(s, _exclude=nodata, **kw),
        sqlite_path=db, ttl_seconds=900)
    app = create_app(analysis_service=service)
    app.state.plans_db_path = db
    app.state.watchlist_db_path = db
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    return TestClient(app)


# ================================================================ 4. 请求助手


def ask_stream(client: TestClient, session_id: str | None, message: str,
               selected: str | None, cri: str) -> dict:
    body: dict = {"session_id": session_id, "context_kind": "symbol",
                  "message": message, "client_request_id": cri}
    if selected:
        body["symbol"] = selected
    events: list[tuple[str | None, dict]] = []
    status = None
    with client.stream("POST", "/api/agent/chat/stream", json=body) as r:
        status = r.status_code
        cur_event = None
        for line in r.iter_lines():
            if line.startswith("event:"):
                cur_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                try:
                    events.append((cur_event, json.loads(line[5:])))
                except json.JSONDecodeError:
                    events.append((cur_event, {"_raw": line[5:]}))
    out: dict = {"route": "POST /api/agent/chat/stream", "http_status": status,
                 "request": {"message": message, "selected": selected},
                 "prepared": None, "done": None, "events": []}
    for name, payload in events:
        out["events"].append({
            "event": name,
            "resolved_symbol": payload.get("resolved_symbol"),
            "evidence_facts_symbol": ((payload.get("evidence_card") or {})
                                      .get("facts", {}) or {}).get("symbol"),
            "quick_card_symbol": (payload.get("quick_card") or {}).get("symbol")
            if isinstance(payload.get("quick_card"), dict) else None,
            "answer_state": payload.get("answer_state"),
            "verify_note": payload.get("verify_note"),
            "reply_head": (payload.get("reply") or "")[:40] or None,
            "session_id": payload.get("session_id"),
            "payload_keys": sorted(k for k in payload.keys() if k != "timing_ms"),
        })
        if name == "prepared":
            out["prepared"] = payload
        elif name == "done":
            out["done"] = payload
    return out


def ask_plain(client: TestClient, session_id: str | None, message: str,
              selected: str | None, cri: str) -> dict:
    body: dict = {"session_id": session_id, "context_kind": "symbol",
                  "message": message, "client_request_id": cri}
    if selected:
        body["symbol"] = selected
    r = client.post("/api/agent/chat", json=body)
    p = r.json()
    return {"route": "POST /api/agent/chat", "http_status": r.status_code,
            "request": {"message": message, "selected": selected},
            "resolved_symbol": p.get("resolved_symbol"),
            "evidence_facts_symbol": ((p.get("evidence_card") or {})
                                      .get("facts", {}) or {}).get("symbol"),
            "grounded": p.get("grounded"),
            "answer_state": p.get("answer_state"),
            "reply_head": (p.get("reply") or "")[:40],
            "payload_keys": sorted(p.keys()),
            "session_id": p.get("session_id"),
            "raw": p}


def history(client: TestClient, session_id: str) -> list[dict] | dict:
    resp = client.get(f"/api/agent/sessions/{session_id}/messages")
    if resp.status_code != 200 or not isinstance(resp.json(), list):
        return {"error": f"status={resp.status_code}", "body": resp.json()}
    return [{"role": m.get("role"), "message_id": m.get("message_id"),
             "question_id": m.get("question_id"),
             "resolved_symbol": m.get("resolved_symbol"),
             "evidence_facts_symbol": ((m.get("evidence_card") or {})
                                       .get("facts", {}) or {}).get("symbol"),
             "content_head": (m.get("content") or "")[:30]}
            for m in resp.json()]


def prompt_of(via_prefix: str, idx: int) -> dict | None:
    hits = [c for c in LLM_CALLS if c["via"].startswith(via_prefix)]
    return hits[idx] if idx < len(hits) else None


# ================================================================ 5. 场景驱动 + 机检

CHECKS: list[dict] = []


def chk(case: str, name: str, ok: bool, detail: str) -> bool:
    CHECKS.append({"case": case, "check": name, "ok": bool(ok), "detail": detail})
    return bool(ok)


def done_binding(r: dict) -> tuple[str | None, str | None, str | None]:
    if "events" in r:
        d = r.get("done") or {}
        facts = ((d.get("evidence_card") or {}).get("facts") or {}).get("symbol")
        quick = d.get("quick_card", {}).get("symbol") if isinstance(d.get("quick_card"), dict) else None
        return d.get("resolved_symbol"), facts, quick
    return r.get("resolved_symbol"), r.get("evidence_facts_symbol"), None


def stream_health(case: str, r: dict) -> bool:
    ok_http = chk(case, "http_200", r.get("http_status") == 200,
                  f"status={r.get('http_status')}")
    names = [e.get("event") for e in r.get("events") or []]
    ok_prep = chk(case, "prepared_event_present", "prepared" in names, f"events={names}")
    done = r.get("done") or {}
    ok_done = chk(case, "done_answered",
                  bool(done) and done.get("answer_state") == "answered",
                  f"answer_state={done.get('answer_state')} verify={done.get('verify_note')}")
    return ok_http and ok_prep and ok_done


def plain_health(case: str, r: dict) -> bool:
    ok_http = chk(case, "http_200", r.get("http_status") == 200,
                  f"status={r.get('http_status')}")
    ok_state = chk(case, "answered", r.get("answer_state") == "answered",
                   f"answer_state={r.get('answer_state')}")
    return ok_http and ok_state


def history_binding_for(session_hist: list | dict, question_head: str) -> dict | None:
    if not isinstance(session_hist, list):
        return None
    idx = None
    for i, row in enumerate(session_hist):
        if row.get("role") == "user" and str(row.get("content_head", "")).startswith(question_head[:12]):
            idx = i
            break
    if idx is None:
        return None
    for row in session_hist[idx + 1:]:
        if row.get("role") == "assistant":
            return row
    return None


t0 = __import__("time").time()
results: dict = {"meta": {
    "mode": MODE,
    "workspace": str(WORKSPACE),
    "lei_signal_from": str(Path(lei_signal.__file__).resolve()),
    "workspace_head": os.environ.get("_WORKSPACE_HEAD", "见同名报告/raw"),
    "isolated": ("audit 护栏硬隔离（网络/DNS、沙箱外写入、真实 .env、真实业务库、非临时SQLite）；"
                 "合成行情桩 + 双路模型桩 + 一次性临时库 + cwd 独立；无真实模型/行情/真实库"),
    "run_cwd": str(RUN_CWD),
    "tmp_root": str(_TMP),
    "generated_at": datetime.now().isoformat(timespec="seconds"),
}, "llm_prompt_materials": LLM_CALLS, "cases": {}}

client_ok = build_app("ok")
client_nodata = build_app("nodata", nodata=frozenset({"000300.SS", "000001.SS"}))

print(f"== [{MODE}] 会话A（流式，数据可用）：515880 → 那失效位呢 → 沪深300 → 明确000300.SS ==")
sid = None
a1 = ask_stream(client_ok, sid, "515880 现在有哪些系统定义的买点？", "515880.SS", "fix-A1")
sid = (a1.get("done") or {}).get("session_id") or sid
a2 = ask_stream(client_ok, sid, "那失效位呢", "515880.SS", "fix-A2")
a3 = ask_stream(client_ok, sid, "沪深300 现在有哪些系统定义的买点？", "515880.SS", "fix-A3")
a4 = ask_stream(client_ok, sid, "000300.SS 现在的买点结构到哪一步了", "515880.SS", "fix-A4")
results["cases"]["case1_515880_to_hs300_stream"] = {"q1": a1, "q2": a3}
results["cases"]["case3_explicit_000300_stream_selected_stale"] = a4
results["cases"]["case4_followup_invalidation_stream"] = a2
hist_a = history(client_ok, sid)
results["history_session_A"] = hist_a

print(f"== [{MODE}] 会话B（流式，沪深300/上证指数无数据）：515880 → 明确000300.SS(无数据) → 上证指数 ==")
sid_b = None
b1 = ask_stream(client_nodata, sid_b, "515880 现在有哪些系统定义的买点？", "515880.SS", "fix-B1")
sid_b = (b1.get("done") or {}).get("session_id") or sid_b
b2 = ask_stream(client_nodata, sid_b, "000300.SS 现在的买点", "515880.SS", "fix-B2")
b3 = ask_stream(client_nodata, sid_b, "上证指数 现在有哪些系统定义的买点？", "515880.SS", "fix-B3")
results["cases"]["case5_explicit_new_symbol_no_data"] = b2
results["cases"]["case2b_sse_named_nodata_stream"] = b3
results["history_session_B"] = history(client_nodata, sid_b)

print(f"== [{MODE}] 会话C（非流式，数据可用）：515880 → 上证指数 ==")
sid_c = None
c1 = ask_plain(client_ok, sid_c, "515880 现在有哪些系统定义的买点？", "515880.SS", "fix-C1")
sid_c = c1["session_id"]
c2 = ask_plain(client_ok, sid_c, "上证指数 现在有哪些系统定义的买点？", "515880.SS", "fix-C2")
results["cases"]["case2a_515880_to_sse_index_plain"] = {"q1": c1, "q2": c2}
hist_c = history(client_ok, sid_c)
results["history_session_C"] = hist_c

print(f"== [{MODE}] 会话D/E/F（非流式）：科创50板块 / 科创板整体 / 两个标的并列 ==")
d1 = ask_plain(client_ok, None, "科创50板块现在怎么看", None, "fix-D1")
e1 = ask_plain(client_ok, None, "科创板整体现在怎么样", None, "fix-E1")
f1 = ask_plain(client_ok, None, "515880 和 510300 哪个更强", "515880.SS", "fix-F1")
results["cases"]["case6_kc50_board"] = d1
results["cases"]["case7_star_market_whole"] = e1
results["cases"]["case8_two_symbols_compare"] = f1

print(f"== [{MODE}] resolve 层探针 + 显示名 ==")
resolve_probes = []
for tag, msg, sel in [
    ("hs300_named", "沪深300 现在有哪些系统定义的买点？", "515880.SS"),
    ("sse_named", "上证指数 现在有哪些系统定义的买点？", "515880.SS"),
    ("hs300_code", "000300.SS 现在有哪些系统定义的买点？", "515880.SS"),
    ("followup", "那失效位呢", "515880.SS"),
    ("kc50_board", "科创50板块现在怎么看", None),
    ("star_whole", "科创板整体现在怎么样", None),
    ("two_symbols", "515880 和 510300 哪个更强", "515880.SS"),
]:
    body: dict = {"message": msg}
    if sel:
        body["selected_symbol"] = sel
    r = client_ok.post("/api/copilot/resolve", json=body)
    p = r.json()
    resolve_probes.append({
        "tag": tag, "message": msg, "selected_symbol": sel,
        "http_status": r.status_code,
        "resolved_symbol": p.get("resolved_symbol"),
        "subject_source": p.get("subject_source"),
        "display_name": p.get("display_name"),
        "clarification_kinds": [c.get("kind") for c in (p.get("clarification") or [])
                                if isinstance(c, dict)],
    })
results["resolve_probes"] = resolve_probes

# 显示名目录（copilot/subjects.catalog_names 与 agent._static_symbol_name）
from lei_signal.api.routes import agent as agent_mod  # noqa: E402
from lei_signal.copilot import subjects as subjects_mod  # noqa: E402
display_name_checks = {
    "catalog_names_hs300": subjects_mod.catalog_names().get("000300.SS"),
    "catalog_names_sse": subjects_mod.catalog_names().get("000001.SS"),
    "static_name_hs300": agent_mod._static_symbol_name("000300.SS", None),
    "static_name_sse": agent_mod._static_symbol_name("000001.SS", None),
    "resolve_probe_hs300_code": next(
        p["display_name"] for p in resolve_probes if p["tag"] == "hs300_code"),
    "resolve_probe_hs300_named": next(
        p["display_name"] for p in resolve_probes if p["tag"] == "hs300_named"),
}
results["display_name_checks"] = display_name_checks

# ================================================================ 6. 判定（由真实响应生成）


def _fact_sym(x: dict | None) -> str | None:
    return ((x.get("evidence_card") or {}).get("facts") or {}).get("symbol") if x else None


verdicts: list[dict] = []


def build_verdict(case_id: str, name: str, runs: list[dict], paths: list[str],
                  expected_binding: str | None, *, kind: str,
                  extra_checks: list[tuple[str, bool, str]] | None = None,
                  prompt_idx: list[int] | None = None,
                  expected_prompts: list[str | None] | None = None,
                  history_rows: list[dict | None] | None = None,
                  question_heads: list[str] | None = None) -> None:
    """kind: expected_defect(基线已知缺陷，复现才算证据)  must_resolve(强制通过)  as_is(只记录)。"""
    ckey = f"case{case_id}"
    healthy = True
    for tag, r in zip(paths, runs):
        healthy = stream_health(f"{ckey}.{tag}", r) and healthy if "events" in r \
            else plain_health(f"{ckey}.{tag}", r) and healthy
    if not healthy:
        verdicts.append({"case": case_id, "name": name, "status": "error",
                         "expectation": f"绑定 {expected_binding}",
                         "actual": "请求级失败（HTTP/事件缺失/未完成），不计入缺陷复现",
                         "evidence": paths})
        return

    observed = [done_binding(r) for r in runs]
    binds = [b[0] for b in observed]
    facts = [b[1] for b in observed]
    quicks = [b[2] for b in observed]

    for i, (b, f, q) in enumerate(zip(binds, facts, quicks)):
        chk(f"{ckey}.{paths[i]}", "card_matches_resolved",
            (f is None and q is None) or (f == b and (q is None or q == b)),
            f"resolved={b} facts={f} quick={q}")

    prompt_note = ""
    if prompt_idx:
        for i, pidx in enumerate(prompt_idx):
            pm = LLM_CALLS[pidx] if pidx < len(LLM_CALLS) else {}
            want = binds[i] if kind == "expected_defect" else (
                expected_prompts[i] if expected_prompts else expected_binding)
            if want is not None:
                chk(f"{ckey}.{paths[i]}", "prompt_material_object",
                    pm.get("ctx_symbol") == want,
                    f"prompt ctx_symbol={pm.get('ctx_symbol')} 期望={want}")
            prompt_note += (f" AI材料={pm.get('display_name') or pm.get('context_kind') or '无'}"
                            f"({pm.get('ctx_symbol')})")

    if history_rows and question_heads:
        for i, (h, head) in enumerate(zip(history_rows, question_heads)):
            if h is None:
                continue
            row = history_binding_for(h, head)
            hist_resolved = row.get("resolved_symbol") if isinstance(row, dict) else None
            chk(f"{ckey}.{paths[i]}", "history_meta_matches_done",
                isinstance(row, dict) and hist_resolved == binds[i],
                f"history resolved={hist_resolved} final={binds[i]}")

    if extra_checks:
        for cname, ok, detail in extra_checks:
            chk(ckey, cname, ok, detail)

    all_ok = all(c["ok"] for c in CHECKS if c["case"].startswith(f"{ckey}."))
    if kind == "expected_defect":
        reproduced = all(b == "515880.SS" for b in binds)
        status = "expected_failure_reproduced" if reproduced else "defect_not_reproduced"
    elif kind == "as_is":
        status = "as_is_observed"
    else:
        status = "pass" if all_ok else "fail"

    actual = ("；".join(
        f"{p}: resolved={b} facts={f} quick={q}" for p, (b, f, q) in zip(paths, observed))
        + prompt_note)
    verdicts.append({"case": case_id, "name": name, "status": status,
                     "expectation": ("仅记录现状" if kind == "as_is"
                                     else (f"仍绑 515880（缺陷复现）" if kind == "expected_defect"
                                           else f"绑定 {expected_binding}")),
                     "actual": actual,
                     "bindings": {"resolved": binds, "facts": facts, "quick": quicks},
                     "evidence": paths})


# case1: 515880→沪深300（流式，沪深300有合成数据）
build_verdict(1, "515880→沪深300（流式，有数据）", [a3], ["chat/stream"],
              "000300.SS" if MODE == "fixed" else None,
              kind="must_resolve" if MODE == "fixed" else "expected_defect",
              prompt_idx=[2], history_rows=[hist_a],
              question_heads=["沪深300 现在有哪些系统定义的买点"])

# case2a: 515880→上证指数（非流式，有数据）
build_verdict("2a", "515880→上证指数（非流式，有数据）", [c2], ["chat/plain"],
              "000001.SS" if MODE == "fixed" else None,
              kind="must_resolve" if MODE == "fixed" else "expected_defect",
              prompt_idx=[8], history_rows=[hist_c],
              question_heads=["上证指数 现在有哪些系统定义的买点"])

# case2b: 上证指数名称 + 指数无行情（流式）。基线：名称识别失败→旧 selected
# 接管→附旧 515880 卡（缺陷表现之一）；修后：识别到 000001.SS 但无行情→
# 不得附旧卡，退全局。
b3_done = b3.get("done") or {}
b3_prompt = LLM_CALLS[6] if len(LLM_CALLS) > 6 else {}
build_verdict("2b", "上证指数名称+无行情（流式）", [b3], ["chat/stream-nodata"],
              None,
              kind="expected_defect" if MODE == "baseline" else "must_resolve",
              prompt_idx=[6],
              expected_prompts=[None] if MODE == "fixed" else None,
              history_rows=[results["history_session_B"]],
              question_heads=["上证指数 现在有哪些系统定义的买点"],
              extra_checks=([
                  ("no_stale_card", _fact_sym(b3_done) is None
                   and b3_done.get("resolved_symbol") is None,
                   f"done resolved={b3_done.get('resolved_symbol')} "
                   f"facts={_fact_sym(b3_done)}（明确新对象缺行情时不得附旧515880卡）"),
                  ("prompt_is_global", b3_prompt.get("context_kind") == "global",
                   f"AI 材料 context_kind={b3_prompt.get('context_kind')}"),
              ] if MODE == "fixed" else None))

# case3: 明确代码 000300.SS 覆盖旧 selected（保持既有正确行为）
build_verdict(3, "515880→明确000300.SS（selected 刻意保留旧标的）", [a4], ["chat/stream"],
              "000300.SS", kind="must_resolve", prompt_idx=[3],
              history_rows=[hist_a], question_heads=["000300.SS 现在的买点结构到哪一步"])

# case4: 无新对象追问「那失效位呢」→ 继承 515880
build_verdict(4, "515880→那失效位呢（流式追问，继承）", [a2], ["chat/stream"],
              "515880.SS", kind="must_resolve", prompt_idx=[1],
              history_rows=[hist_a], question_heads=["那失效位呢"])

# case5: 明确新代码但无行情 → 无旧卡退全局（保持既有保护）
b2_done = b2.get("done") or {}
b2_prompt = LLM_CALLS[5] if len(LLM_CALLS) > 5 else {}
build_verdict(5, "明确新标的但分析无数据（流式：000300.SS 无行情）", [b2], ["chat/stream-nodata"],
              None, kind="must_resolve", prompt_idx=[5], expected_prompts=[None],
              history_rows=[results["history_session_B"]],
              question_heads=["000300.SS 现在的买点"],
              extra_checks=[
                  ("no_stale_card", _fact_sym(b2_done) is None
                   and b2_done.get("resolved_symbol") is None,
                   f"done resolved={b2_done.get('resolved_symbol')} facts={_fact_sym(b2_done)}"),
                  ("prompt_is_global", b2_prompt.get("context_kind") == "global",
                   f"AI 材料 context_kind={b2_prompt.get('context_kind')}"),
              ])

# case6: 科创50板块 → 000688.SS 指数身份（语义保留）
build_verdict(6, "科创50板块（非流式）", [d1], ["chat/plain"], "000688.SS",
              kind="must_resolve", prompt_idx=[9])

# case7: 科创板整体 → 不冒充科创50指数
star_probe = next(p for p in resolve_probes if p["tag"] == "star_whole")
build_verdict(7, "科创板整体（非流式）", [e1], ["chat/plain"], None,
              kind="must_resolve", prompt_idx=[10],
              extra_checks=[
                  ("no_index_impersonation", (e1.get("resolved_symbol") is None
                                              and e1.get("evidence_facts_symbol") is None),
                   f"resolved={e1.get('resolved_symbol')} facts={e1.get('evidence_facts_symbol')}"),
                  ("resolve_layer_has_clarification",
                   "sector_ambiguous_index_reference" in star_probe["clarification_kinds"],
                   f"澄清类型={star_probe['clarification_kinds']}"),
              ])

# case8: 两个标的并列比较（现状记录：chat 取首个代码，不发明比较引擎）
two_probe = next(p for p in resolve_probes if p["tag"] == "two_symbols")
build_verdict(8, "两个标的并列比较（非流式，只记录现状）", [f1], ["chat/plain"],
              None, kind="as_is", prompt_idx=[11],
              extra_checks=[
                  ("chat_binds_first_candidate", f1.get("resolved_symbol") == "515880.SS",
                   f"chat 绑定={f1.get('resolved_symbol')}"),
                  ("resolve_layer_says_ambiguous", two_probe["subject_source"] == "ambiguous",
                   f"识别接口 source={two_probe['subject_source']}"),
              ])

# case9: 显示名目录（修后必须可读；基线记录缺口）
probe_code = display_name_checks["resolve_probe_hs300_code"]
probe_named = display_name_checks["resolve_probe_hs300_named"]
if MODE == "fixed":
    for k, v in display_name_checks.items():
        chk("case9.display", k, v == "沪深300" or v == "上证指数" or bool(v),
            f"{k}={v!r}")
    build_verdict(9, "显示名目录可读", [], [], None, kind="must_resolve",
                  extra_checks=[
                      ("catalog_names_hs300", display_name_checks["catalog_names_hs300"] == "沪深300",
                       f"{display_name_checks['catalog_names_hs300']!r}"),
                      ("catalog_names_sse", display_name_checks["catalog_names_sse"] == "上证指数",
                       f"{display_name_checks['catalog_names_sse']!r}"),
                      ("static_name_hs300", display_name_checks["static_name_hs300"] == "沪深300",
                       f"{display_name_checks['static_name_hs300']!r}"),
                      ("resolve_probe_display_names",
                       probe_code == "沪深300" and probe_named == "沪深300",
                       f"code探针={probe_code!r} named探针={probe_named!r}"),
                  ])
else:
    results["display_name_gap_baseline"] = {
        "catalog_names_hs300": display_name_checks["catalog_names_hs300"],
        "catalog_names_sse": display_name_checks["catalog_names_sse"],
        "resolve_probe_hs300_code": probe_code,
        "resolve_probe_hs300_named": probe_named,
    }

results["verdicts"] = verdicts

# ================================================================ 7. 护栏结果 + 落盘

results["guard"] = {
    "installed_at": GUARD["installed_at"],
    "network_attempts": len(GUARD["network_attempts"]),
    "blocked_writes": len(GUARD["blocked_writes"]),
    "blocked_reads": len(GUARD["blocked_reads"]),
    "blocked_sqlite": len(GUARD["blocked_sqlite"]),
    "note": "全部为 0 才算隔离干净；明细见 logs/guard-attempts.json",
}
results["meta"]["elapsed_s"] = round(__import__("time").time() - t0, 1)
results["checks_summary"] = {
    "total": len(CHECKS),
    "failed": sum(1 for c in CHECKS if not c["ok"]),
    "failed_detail": [c for c in CHECKS if not c["ok"]],
}

(LOGS / f"guard-attempts-{MODE}.json").write_text(
    json.dumps(GUARD, ensure_ascii=False, indent=1), encoding="utf-8")
(LOGS / f"case-checks-{MODE}.json").write_text(
    json.dumps(CHECKS, ensure_ascii=False, indent=1), encoding="utf-8")
(RAW / f"matrix-{MODE}.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

import shutil  # noqa: E402
shutil.rmtree(_TMP, ignore_errors=True)

print(f"完成[{MODE}]：用时 {results['meta']['elapsed_s']}s；"
      f"护栏=网络{results['guard']['network_attempts']}次/越界写{results['guard']['blocked_writes']}"
      f"/禁读{results['guard']['blocked_reads']}/非法SQLite{results['guard']['blocked_sqlite']}；"
      f"机检 {len(CHECKS)} 条，未过 {results['checks_summary']['failed']} 条")
for v in verdicts:
    print(f"  case{v['case']}: {v['status']}  {v['actual'][:120]}")

# ---- 硬断言 ----
if GUARD["network_attempts"] or GUARD["blocked_writes"] or GUARD["blocked_reads"] or GUARD["blocked_sqlite"]:
    raise SystemExit("[guard] 隔离不干净：存在被阻断的外部接触，见 logs/")

if MODE == "baseline":
    reproduced = [v for v in verdicts if v["status"] == "expected_failure_reproduced"]
    if len(reproduced) < 3:
        raise SystemExit(f"[baseline] 缺陷未按预期复现（仅 {len(reproduced)}/3），"
                         "复现脚本或前提已变化，禁止当证据")
    unexpected_fail = [c for c in CHECKS if not c["ok"]]
    if unexpected_fail:
        raise SystemExit(f"[baseline] 非缺陷案例出现检查失败 {len(unexpected_fail)} 条，"
                         "先排查再当基线")
    print("[baseline] 名称切换缺陷按预期复现；继承/代码切换/缺行情保护/板块语义全部保持")
else:
    bad = [v for v in verdicts if v["status"] not in ("pass", "as_is_observed")]
    failed = [c for c in CHECKS if not c["ok"]]
    if bad or failed:
        raise SystemExit(f"[fixed] 存在未通过案例/检查：{[v['status'] for v in bad]}；"
                         f"失败检查 {len(failed)} 条")
    print("[fixed] 全部案例通过")
