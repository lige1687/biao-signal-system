"""ATR 指标词守卫独立复核（agent-continuity-zcode-closeout-2026-09-17）。

验证「指标语境不认领证券、明确证券问法保留」：
- 「如果换成ATR止损…」→ 候选为空（不把 ATR 当证券、不截走当前对象）；
- 「515880 参照ATR距离设止损」→ 只解析出 515880.SS；
- 「看看ATR这只股票」「ATR现在怎么看」→ 仍解析出证券 ATR（不全局禁用代码）。
服务端双层（token 层 + 目录层）各测。结果落 atr-guard-probe.json。
"""
from __future__ import annotations

import json
from pathlib import Path

from lei_signal.api.routes import agent as agent_mod
from lei_signal.data.symbols import resolve_symbol

OUT = Path(__file__).parent
out = {}
try:
    info = resolve_symbol("ATR")
    out["atr_as_security"] = {"symbol": info.symbol,
                              "name": getattr(info, "display_name", None)}
except Exception as e:  # noqa: BLE001
    out["atr_as_security"] = f"unresolvable: {type(e).__name__}"

out["indicator_context"] = agent_mod._symbol_candidates_from_message(
    "如果换成ATR止损，胜率会有什么变化？")
out["indicator_context_distance"] = agent_mod._symbol_candidates_from_message(
    "515880 参照ATR距离设止损靠谱吗")
out["explicit_security"] = agent_mod._symbol_candidates_from_message(
    "看看ATR这只股票现在怎么样")
out["bare_ask"] = agent_mod._symbol_candidates_from_message("ATR现在怎么看")
out["catalog_indicator"] = agent_mod._resolve_symbol_by_catalog(
    "如果换成ATR止损，胜率会有什么变化？")
out["catalog_explicit"] = agent_mod._resolve_symbol_by_catalog("看看ATR这只股票")
(OUT / "atr-guard-probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
