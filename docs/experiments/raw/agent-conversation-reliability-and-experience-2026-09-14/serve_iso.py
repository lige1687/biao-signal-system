"""隔离服务（验收 B/C/D/A 用）：临时业务库 + 本地行情 + 指定模型配置。

与上轮 serve_case.py 同构，差异：
- 端口 8021；每次启动全新 temp DB（--db 打印到 stdout 的 environment.json）。
- MODEL_MODE=real：清除继承模型变量后加载运行仓 .env（应用保存的配置）。
- MODEL_MODE=stub：GLM_* 指向本机桩服务（默认 127.0.0.1:8031，OpenAI 风格），
  用于验收 B 的可控延迟/失败；不触碰任何配置文件。
- 只挂载讨论所需路由；不联网补行情。
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

DEV = Path("/Users/yongbiaoli/lei-agent-ux-20260913")
sys.path.insert(0, str(DEV / "src"))

MODE = os.environ.get("MODEL_MODE", "real")
PORT = int(os.environ.get("ISO_PORT", "8021"))

for key in list(os.environ):
    if key.startswith(("ARK_", "GLM_", "DEEPSEEK_", "ANTHROPIC_")):
        os.environ.pop(key)

if MODE == "real":
    from lei_signal.env import load_env
    load_env(path="/Users/yongbiaoli/Desktop/lei-signal-lab/.env")
elif MODE == "stub":
    os.environ["GLM_API_KEY"] = "stub-key"
    os.environ["GLM_BASE_URL"] = os.environ.get("STUB_BASE_URL", "http://127.0.0.1:8031")
    os.environ["GLM_MODEL"] = "stub-model"
    os.environ["ARK_TIMEOUT"] = os.environ.get("STUB_TIMEOUT", "60")
else:
    raise SystemExit(f"unknown MODEL_MODE={MODE}")

import pandas as pd  # noqa: E402
import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from lei_signal.api.routes import agent, copilot, opportunities, plans, symbols  # noqa: E402
from lei_signal.api.services import AnalysisService  # noqa: E402
from lei_signal.compose.pipeline import analyze_bars  # noqa: E402
from lei_signal.data.providers import PriceData  # noqa: E402
from lei_signal.data.symbols import resolve_symbol  # noqa: E402
from lei_signal.data.validation import validate_bars  # noqa: E402
from lei_signal.plans.llm import load_ark_config  # noqa: E402
from lei_signal.storage.sqlite_store import connect  # noqa: E402

OUT = Path(__file__).parent
TEMP = tempfile.TemporaryDirectory(prefix="lei-iso-")
db = str(Path(TEMP.name) / "case.db")
connect(db).close()

BARS = Path("/Users/yongbiaoli/.lei_signal_lab/cache/510300.SS.bars.parquet")
bars = pd.read_parquet(BARS)


def local_analyze(symbol, **kwargs):
    if symbol not in ("510300", "510300.SS"):
        raise ValueError("isolated case limited to 510300")
    info = resolve_symbol(symbol)
    frame, report = validate_bars(
        bars.copy(), symbol=info.symbol, provider="existing_local_cache", adjusted=True)
    return analyze_bars(
        info.symbol, frame,
        price_data=PriceData(symbol=info.symbol, display_name="沪深300ETF",
                             bars=frame, report=report, info=info))


service = AnalysisService(analyze_fn=local_analyze, sqlite_path=db,
                          cache_root=str(Path(TEMP.name) / "cache"), ttl_seconds=3600)
entry = service.get("510300.SS")
assert entry.result is not None, entry.error

app = FastAPI()
app.state.analysis_service = service
for k in ("plans_db_path", "watchlist_db_path", "portfolio_db_path"):
    setattr(app.state, k, db)
app.state.quote_provider = None
app.state.friendly_name_provider = False
for r in (agent.router, plans.router, opportunities.router, symbols.router, copilot.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": MODE}


app.mount("/assets", StaticFiles(directory=DEV / "web/dist/assets"), name="assets")


@app.get("/{path:path}")
def index(path: str):
    return FileResponse(DEV / "web/dist/index.html")


cfg = load_ark_config()
assert cfg, "no model config resolved"
cfg_info = {
    "model": cfg.model,
    "base_url": cfg.base_url,
    "style": cfg.style,
    "timeout": cfg.timeout,
    "max_tokens": cfg.max_tokens,
    "api_key": "<masked>",
}
(OUT / f"environment-iso-{MODE}.json").write_text(json.dumps({
    "development": str(DEV),
    "temporary_db": db,
    "model_mode": MODE,
    "resolved_config": cfg_info,
    "bars": str(BARS),
    "bars_sha256": hashlib.sha256(BARS.read_bytes()).hexdigest(),
    "rows": len(bars),
    "last_bar": str(bars.index.max()),
    "api": f"http://127.0.0.1:{PORT}",
    "local_bars_only": True,
}, ensure_ascii=False, indent=2))
print(f"ISO-READY mode={MODE} db={db}", flush=True)
uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
