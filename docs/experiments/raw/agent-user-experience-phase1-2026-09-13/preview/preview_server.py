"""隔离预览后端（UX 第一期 2026-09-13）——合成数据 + 临时库，端口 8014。

与 tests/integration/test_agent_chat_e2e.py 的 client fixture 同一构造：
- 行情来自仓库测试夹具 parquet（合成/夹具数据，非真实行情，也不联网回补）；
- SQLite 是临时目录里的空库，不影响任何真实业务库；
- 模型配置指向本地假模型桩（fake_llm.py，8015），回复为固定合成文本。

只服务于浏览器走查，不代表生产行为。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]  # raw/…/preview → 仓库根（preview=0,任务目录=1,raw=2,experiments=3,docs=4,根=5）
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402
import uvicorn  # noqa: E402

import lei_signal.plans.llm as llm  # noqa: E402
from lei_signal.api.app import create_app  # noqa: E402
from lei_signal.api.services import AnalysisService  # noqa: E402
from lei_signal.compose.pipeline import analyze_bars  # noqa: E402
from lei_signal.data.providers import PriceData  # noqa: E402
from lei_signal.data.symbols import resolve_symbol  # noqa: E402
from lei_signal.data.validation import validate_bars  # noqa: E402
from lei_signal.plans.llm import ArkConfig  # noqa: E402

# 预览合成标的（都来自仓库测试夹具 parquet，非真实行情）：
# - 510300：主走查标的（无买点候选）
# - 516220.SS：早期转强案例（P3 后不给合法预填，转待补）
# - TH881272.SECTOR：P3 正例（唯一经完整路由 ACTIONABLE 且建议可映射 C 的夹具；失效价待用户补齐）
PREVIEW_PARQUET = {
    "510300": "510300.SS.bars.parquet",
    "516220": "516220.SS.bars.parquet",
    "159652": "159652.SZ.bars.parquet",
    "th881272": "TH881272.SECTOR.bars.parquet",
}
DEFAULT_SYMBOL = "510300"

# 指向本地假模型桩（合成回复）；绝不访问真实供应商
llm.load_ark_config = lambda: ArkConfig(
    api_key="preview-only", base_url="http://127.0.0.1:8015",
    model="fake-ux-preview",
)

# 隔离预览必须完全离线：关闭后台预热与 breadth 预热，并在本进程内拦截
# 一切非本机 socket 连接（行情预热/外部下载立即失败，不再限流重试拖慢
# 服务）。只改本预览进程，不动生产代码。
import lei_signal.api.app as app_module  # noqa: E402

app_module.start_preheat = lambda *a, **k: (lambda: None)
app_module._warm_a_share_breadth = lambda: None

import socket as _socket  # noqa: E402

_orig_connect = _socket.socket.connect

def _offline_guard(self, address):  # noqa: ANN001
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, str) and host not in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
        raise OSError(f"preview offline guard: blocked {address!r}")
    return _orig_connect(self, address)

_socket.socket.connect = _offline_guard


def _fake_analyze(symbol: str, **kwargs):  # noqa: ANN002, ANN003
    bare = (symbol or "").split(".")[0].lower()
    parquet_name = PREVIEW_PARQUET.get(bare, f"{DEFAULT_SYMBOL}.SS.bars.parquet")
    target = bare if bare in PREVIEW_PARQUET else DEFAULT_SYMBOL
    parquet = REPO / "tests" / parquet_name
    bars = pd.read_parquet(parquet)
    frame, report = validate_bars(bars, symbol=target, provider="fixture", adjusted=True)
    info = resolve_symbol(target)
    price_data = PriceData(
        symbol=info.symbol, display_name=f"{info.symbol}（预览合成数据）", bars=frame,
        report=report, info=info,
    )
    return analyze_bars(target, frame, price_data=price_data)


def main() -> None:
    db_path = os.environ.get(
        "UX_PREVIEW_DB", str(Path(__file__).parent / "preview.db"),
    )
    service = AnalysisService(analyze_fn=_fake_analyze, sqlite_path=db_path, ttl_seconds=900)
    app = create_app(analysis_service=service)
    app.state.plans_db_path = db_path
    app.state.watchlist_db_path = db_path
    app.state.quote_provider = None
    app.state.friendly_name_provider = False
    uvicorn.run(app, host="127.0.0.1", port=8014, log_level="warning")


if __name__ == "__main__":
    main()
