#!/usr/bin/env python3
"""S2 浏览器两入口验证——隔离后端启动器（只服务本验证，非产品代码）。

- 进程级禁网护栏先于一切业务导入：阻断并记录全部 DNS/外连（AF_INET/6）、
  沙箱外写入、真实 .env / 真实业务库读取、非临时 SQLite；退出码非零=隔离不干净。
- 全部外部依赖打桩：合成行情（上证指数 000001.SS 刻意无行情，用于验证
  「明确新对象缺行情不附旧卡」）、双路模型桩（固定回复文本）、一次性临时库、
  预热/目录/宽度/情绪等外部数据源替换。
- 被测后端源码 = 演练已应用树（adoption package apply 后的 runtime 副本）。
- 只绑 127.0.0.1 隔离端口，不写真实运行工作区。

用法：python3 serve_browser_candidate.py <applied_target_root> <port>
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

TARGET = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 18765
if not TARGET or not (TARGET / "src/lei_signal").is_dir():
    raise SystemExit("usage: serve_browser_candidate.py <applied_target_root> [port]")

HERE = Path(__file__).resolve().parent
TMP = Path(tempfile.mkdtemp(prefix="glm-browser-s2-"))
(TMP / "cache").mkdir()
os.environ["LEI_CACHE_ROOT"] = str(TMP / "cache")
os.environ["LEI_SQLITE_PATH"] = str(TMP / "lab.db")
os.environ["LEI_PREHEAT_DISABLED"] = "1"
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

GUARD: dict = {"installed_at": datetime.now().isoformat(timespec="seconds"),
               "network_attempts": [], "blocked_writes": [], "blocked_reads": [],
               "blocked_sqlite": []}
_ALLOW = (TMP.resolve(), HERE.resolve(), Path(tempfile.gettempdir()).resolve())
_NO_READ_ROOTS = ((Path.home() / ".lei_signal_lab").resolve(),)


def _ok(p: Path) -> bool:
    try:
        return p.resolve(strict=False).is_relative_to(_ALLOW[0]) or \
            p.resolve(strict=False).is_relative_to(_ALLOW[1]) or \
            p.resolve(strict=False).is_relative_to(_ALLOW[2])
    except OSError:
        return False


def _stack() -> str:
    keep = []
    for fr in traceback.extract_stack()[:-1]:
        if str(TARGET) in fr.filename or "serve_browser_candidate" in fr.filename:
            keep.append(f"  {fr.filename}:{fr.lineno} in {fr.name}")
    return "\n".join(keep[-6:]) or "(no frames)"


def _audit(event, args):
    if event in ("socket.getaddrinfo", "socket.connect"):
        if event == "socket.connect" and getattr(args[0], "family", None) not in (
                socket.AF_INET, socket.AF_INET6):
            return
        GUARD["network_attempts"].append({"event": event, "detail": str(args)[:160],
                                          "stack": _stack()})
        raise RuntimeError("[guard] 服务进程网络尝试已被阻断")
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
        if wants_write and not _ok(rp):
            GUARD["blocked_writes"].append({"path": str(rp)[:240], "stack": _stack()})
            raise RuntimeError("[guard] 沙箱外写入已被阻断")
        if not wants_write:
            if p.name == ".env" and not _ok(rp):
                GUARD["blocked_reads"].append({"path": str(rp)[:240], "stack": _stack()})
                raise RuntimeError("[guard] 真实 .env 读取已被阻断")
            if any(rp.is_relative_to(fr) for fr in _NO_READ_ROOTS):
                GUARD["blocked_reads"].append({"path": str(rp)[:240], "stack": _stack()})
                raise RuntimeError("[guard] 真实业务库读取已被阻断")
        return
    if event == "sqlite3.connect":
        name = str(args[0]) if args else ""
        if name == ":memory:":
            return
        # URI 形态（file:...?mode=ro）先剥前缀与查询串再按路径核对；
        # 直接 resolve 会把 URI 当相对路径拼到 cwd，可能落进允许目录造成漏报
        # （S1 复现脚本的已核实漏洞，见本轮报告）。
        if name.startswith("file:"):
            name = name[len("file:"):].split("?", 1)[0]
        try:
            rp = Path(name).expanduser().resolve(strict=False)
        except OSError:
            return
        if not _ok(rp):
            GUARD["blocked_sqlite"].append({"path": str(rp)[:240], "stack": _stack()})
            raise RuntimeError("[guard] 非临时 SQLite 已被阻断")


sys.addaudithook(_audit)

# ---- 业务导入（来自已应用树）----
sys.path.insert(0, str(TARGET / "src"))

import pandas as pd  # noqa: E402

import lei_signal  # noqa: E402
import lei_signal.plans.llm as llm  # noqa: E402
from lei_signal.api.services import AnalysisService  # noqa: E402
from lei_signal.compose.pipeline import analyze_bars  # noqa: E402
from lei_signal.data.providers import PriceData  # noqa: E402
from lei_signal.data.symbols import resolve_symbol  # noqa: E402
from lei_signal.data.validation import validate_bars  # noqa: E402

assert Path(lei_signal.__file__).resolve().is_relative_to((TARGET / "src").resolve()), \
    f"导入的不是已应用树: {lei_signal.__file__}"

import lei_signal.env as _envmod  # noqa: E402
_envmod.load_env = lambda *a, **k: None
import lei_signal.api.catalog as _catalog  # noqa: E402
_catalog.concept_boards = lambda **kw: []
import lei_signal.copilot.breadth as _breadth  # noqa: E402
_breadth.a_share_breadth_cn = lambda: None
# 美股宽度直读 ~/.lei_signal_lab/lab.db（URI 只读）；隔离内一律桩掉，
# 不以任何形式接触真实个人库（含只读）。
_breadth.us_breadth = lambda: {"available": False, "note_cn": "隔离桩：美股宽度库隔离"}
_breadth.us_breadth_cn = lambda: None
from types import SimpleNamespace  # noqa: E402
_中性宽度桩 = SimpleNamespace(
    up=0, down=0, flat=0, total=0, up_pct=None, adv_dec_ratio=None,
    limit_up=None, limit_down=None, as_of=None,
    source_detail="隔离桩：无市场环境数据", data_status="unavailable")
import lei_signal.market_context.a_share_breadth as _asb  # noqa: E402
_asb.get_a_share_breadth = lambda **kw: _中性宽度桩
import lei_signal.market_context.market_mood as _mm  # noqa: E402
_mm.cn_mood = lambda: {}
import lei_signal.fundamentals.sources as _fsrc  # noqa: E402
_fsrc.fetch_margin_history = lambda **kw: []

REPLY = "首段结论。\n\n其余说明。"
llm._llm_call = lambda cfg, msgs: REPLY
llm._request_completion_stream = lambda cfg, msgs: iter([  # type: ignore
    "首段结论。", "\n\n其余说明。"])
llm.load_ark_config = lambda: llm.ArkConfig(
    api_key="test-only", base_url="https://isolated.invalid", model="isolated-stub")


def _bars(n: int = 80) -> pd.DataFrame:
    rows = []
    for i in range(n):
        close = 100.0 + i * 0.5
        rows.append({"open": close - 0.2, "high": close + 0.4, "low": close - 0.5,
                     "close": close, "volume": 1_000_000})
    idx = pd.bdate_range(start="2024-01-02", periods=n)
    return pd.DataFrame(rows, index=idx)[["open", "high", "low", "close", "volume"]]


NO_DATA = frozenset({"000001.SS"})  # 上证指数刻意无行情（缺数据腿）


def fake_analyze(symbol: str, **kwargs):  # noqa: ANN002, ANN003
    if symbol in NO_DATA:
        raise RuntimeError(f"[隔离桩] {symbol} 无分析数据")
    frame, report = validate_bars(_bars(), symbol=symbol, provider="fixture", adjusted=True)
    info = resolve_symbol(symbol)
    return analyze_bars(symbol, frame,
                        price_data=PriceData(symbol=info.symbol, display_name=info.symbol,
                                             bars=frame, report=report, info=info))


from lei_signal.api.app import create_app  # noqa: E402  # 打桩之后

db = str(TMP / "lab.db")
service = AnalysisService(analyze_fn=fake_analyze, sqlite_path=db, ttl_seconds=900)
app = create_app(analysis_service=service)
app.state.plans_db_path = db
app.state.watchlist_db_path = db
app.state.quote_provider = None
app.state.friendly_name_provider = False

import uvicorn  # noqa: E402


class _GuardedServer(uvicorn.Server):
    def run(self, sockets=None):
        super().run(sockets=sockets)
        dirty = {k: len(v) for k, v in GUARD.items() if k != "installed_at"}
        (HERE / "browser-guard-report.json").write_text(
            json.dumps({"guard": GUARD, "dirty": dirty}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        if any(dirty.values()):
            raise SystemExit(f"[guard] 隔离不干净: {dirty} → browser-guard-report.json")


_GuardedServer(uvicorn.Config(app, host="127.0.0.1", port=PORT,
                              log_level="warning")).run()
