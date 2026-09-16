"""隔离服务（agent-experience-continuity-2026-09-16 修前/修后对照用）。

与 2026-09-14 可靠性一轮 serve_iso.py 同构，差异：
- 开发目录换成本轮工作区；对象换成 515880.SS（通信ETF）+ BK1215 板块快照；
- 端口默认 8022；每次启动全新临时业务库（不碰真实业务库）；
- MODEL_MODE=degraded：清掉全部模型环境变量 → LLM 不可用，走系统直出
  （确定性表达基线，修前/修后逐字对照的就是这条路径）；
- MODEL_MODE=stub：GLM_* 指向本机桩服务（OpenAI 兼容，支持流式），验证
  提示词链路工程行为（grounded=True、token 流、保存），输出是合成文本；
- MODEL_MODE=real：清掉继承变量后加载运行仓 .env（真实模型，逐次计数）。
- 板块/情绪/宽度等快照读真实缓存目录（只读，与上轮方法一致）；业务写入
  （会话/问题/回答/补测任务）全部落在临时库。
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

DEV = Path("/Users/yongbiaoli/lei-agent-main-consolidation-20260915")
sys.path.insert(0, str(DEV / "src"))

MODE = os.environ.get("MODEL_MODE", "degraded")
PORT = int(os.environ.get("ISO_PORT", "8022"))

for key in list(os.environ):
    if key.startswith(("ARK_", "GLM_", "DEEPSEEK_", "ANTHROPIC_")):
        os.environ.pop(key)

if MODE == "real":
    from lei_signal.env import load_env

    load_env(path="/Users/yongbiaoli/Desktop/lei-signal-lab/.env")
elif MODE == "stub":
    os.environ["GLM_API_KEY"] = "stub-key"
    os.environ["GLM_BASE_URL"] = os.environ.get("STUB_BASE_URL", "http://127.0.0.1:8032")
    os.environ["GLM_MODEL"] = "stub-model"
elif MODE != "degraded":
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
from lei_signal.storage.sqlite_store import connect  # noqa: E402

OUT = Path(__file__).parent
TEMP = tempfile.TemporaryDirectory(prefix="lei-iso-cont-")
db = str(Path(TEMP.name) / "case.db")
connect(db).close()

BARS = Path("/Users/yongbiaoli/.lei_signal_lab/cache/515880.SS.bars.parquet")
bars = pd.read_parquet(BARS)


def local_analyze(symbol, **kwargs):
    if symbol not in ("515880", "515880.SS"):
        raise ValueError("isolated case limited to 515880")
    info = resolve_symbol(symbol)
    frame, report = validate_bars(
        bars.copy(), symbol=info.symbol, provider="existing_local_cache", adjusted=True)
    return analyze_bars(
        info.symbol, frame,
        price_data=PriceData(symbol=info.symbol, display_name="通信ETF",
                             bars=frame, report=report, info=info))


service = AnalysisService(analyze_fn=local_analyze, sqlite_path=db,
                          cache_root=str(Path(TEMP.name) / "cache"), ttl_seconds=3600)
entry = service.get("515880.SS")
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


_dist = DEV / "web/dist"
if (_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}")
    def index(path: str):
        return FileResponse(_dist / "index.html")


from lei_signal.plans.llm import load_ark_config  # noqa: E402

cfg = load_ark_config()
cfg_info = None
if cfg:
    cfg_info = {
        "model": cfg.model, "base_url": cfg.base_url, "style": cfg.style,
        "timeout": cfg.timeout, "max_tokens": cfg.max_tokens, "api_key": "<masked>",
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
