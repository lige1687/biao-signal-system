"""宽度择时样本外打分卡：逐日存档全部执行信号（档位/引擎/警报），供月度归因。

用法：python3.11 scripts/timing_scorecard.py [--force]
- 追加一行 JSON 到 ~/.lei_signal_lab/timing_scorecard/scorecard.jsonl，并刷新 latest.json
- 按「数据截至日集合」去重：同一天的数据重复跑不会产生重复行（--force 强制写）
- 月度归因用第十二轮六格框架对照（低/中/高 × MA200 下/上），由 analyze 子命令
  在积累数据后提供（当前只做存档）。

launchd/cron 接线建议：每个交易日 18:30 跑一次（宽度回填在 18:00 后）。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.timing_backtest.service import build_signals

SCORECARD_DIR = Path.home() / ".lei_signal_lab/timing_scorecard"


def as_of_key(signals: list[dict]) -> str:
    """去重键 = A 股信号的最新数据日（美股宽度刷新节奏独立，不并入键）。"""
    cn_dates = [
        str(s.get("as_of"))
        for s in signals
        if s.get("as_of") and str(s.get("symbol", "")[:1]).isdigit()
    ]
    return max(cn_dates) if cn_dates else ""


def main() -> None:
    force = "--force" in sys.argv
    signals = build_signals()
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "as_of": as_of_key(signals),
        "signals": [
            {
                "key": s.get("key"),
                "symbol": s.get("symbol"),
                "label": s.get("label"),
                "breadth_now": s.get("breadth_now"),
                "weight_now": s.get("weight_now"),
                "engine": s.get("engine"),
                "rs120": s.get("rs120"),
                "siphon": s.get("siphon"),
                "alert": s.get("alert"),
                "error": s.get("error"),
            }
            for s in signals
        ],
    }
    SCORECARD_DIR.mkdir(parents=True, exist_ok=True)
    jsonl = SCORECARD_DIR / "scorecard.jsonl"
    if jsonl.exists() and not force:
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            try:
                if json.loads(line).get("as_of") == entry["as_of"]:
                    print(f"已存在 as_of={entry['as_of']} 的存档，跳过（--force 强制写）")
                    return
            except json.JSONDecodeError:
                continue
    with jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    (SCORECARD_DIR / "latest.json").write_text(
        json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fired = [s["label"] for s in entry["signals"] if s.get("siphon")]
    print(f"存档完成 as_of={entry['as_of']}：{len(entry['signals'])} 条配置 → {jsonl}")
    print(f"虹吸灯亮：{fired if fired else '无'}")


if __name__ == "__main__":
    main()
