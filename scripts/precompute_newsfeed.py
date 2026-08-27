#!/usr/bin/env python3
"""资讯流 · 每日管线入口（launchd 20:30 或手动）。

跑 ``lei_signal.newsfeed.pipeline.run_pipeline``：
抓取（东财/新浪快讯 + Google News + B站 UP主 + RSS）→ 粗筛入库（幂等）
→ LLM 批量打分（类别/重要性/方向/标的/点评）→ 今日整合简报。

凭据走环境变量（.env）：LLM 用 ARK_*/DEEPSEEK_API_KEY/ANTHROPIC_*（复用
plans/llm.py 优先级）；B站字幕可选配 BILI_SESSDATA（无则匿名降级，仅标题+简介）。

用法
----
  export PYTHONPATH=/path/to/lei-signal-lab/src
  python scripts/precompute_newsfeed.py            # 正常增量跑
  python scripts/precompute_newsfeed.py --full     # 忽略水位全量回看（lookback_days）
  python scripts/precompute_newsfeed.py --no-llm   # 只抓取入库，不打分
  python scripts/precompute_newsfeed.py --db /tmp/newsfeed_e2e.db  # 指定临时库

返回码
------
  0  ok / partial（部分源失败不算致命）
  1  failed（全部源失败）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.api import config as api_config  # noqa: E402
from lei_signal.env import load_env  # noqa: E402
from lei_signal.newsfeed.pipeline import run_pipeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="newsfeed 每日管线")
    parser.add_argument("--full", action="store_true", help="忽略水位全量回看")
    parser.add_argument("--no-llm", action="store_true", help="只抓取入库，不打分")
    parser.add_argument("--db", default=None, help="SQLite 路径（默认 lab.db）")
    args = parser.parse_args()

    load_env()
    db_path = args.db or api_config.sqlite_path()
    result = run_pipeline(db_path, full=args.full, no_llm=args.no_llm)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result["status"] in ("ok", "partial") else 1


if __name__ == "__main__":
    raise SystemExit(main())
