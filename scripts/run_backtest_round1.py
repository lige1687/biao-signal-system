"""V2 第一轮最小系统回测入口（规格 §15 第一轮 + §16 输出）。

用法：
    python3 scripts/run_backtest_round1.py [--out docs/backtest-round1-report-YYYY-MM-DD.md]

对回测深池（~/.lei_signal_lab/backtest_pool，10 年回填）全标的运行模块 A：
- A4 早期版/确认版入场（与 live pipeline 同一份检测器）；
- A6 三版退出分别模拟；
- 费用三档（0/5/10bp）全跑，报告同时输出含/不含费用两组；
- 盈亏比 >=3 过滤（规格 §10，〔标定〕reward_risk_min=3）；
- 样本外起点 = 最近 2 年（决策点 3，留 2024-08-25 起为外样本——按报告日回推）。
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.backtest.runner import (  # noqa: E402
    DEFAULT_POOL_ROOT,
    Round1Config,
    format_markdown,
    load_pool_frames,
    run_round1,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", default=str(DEFAULT_POOL_ROOT), help="回测深池根目录"
    )
    parser.add_argument("--out", default="", help="报告输出路径（默认 docs/ 下按日期命名）")
    args = parser.parse_args()

    frames = load_pool_frames(args.root)
    if not frames:
        raise SystemExit(f"回测池为空：{args.root}")
    # 决策点 3：留最近 2 年样本外（以数据末日回推，避免硬编码年份漂移）
    last_date = max(frame.index[-1] for frame in frames.values()).date()
    oos_start = last_date - timedelta(days=365 * 2)
    config = Round1Config(rr_min=3.0, out_of_sample_start=oos_start)
    report = run_round1(frames, config)
    markdown = format_markdown(report)
    header = (
        f"- 生成：{date.today().isoformat()}；数据末日 {last_date}；"
        f"样本外起点 {oos_start}（最近 2 年）\n"
    )
    markdown = markdown.replace("- 免责：", header + "- 免责：")

    out = Path(args.out) if args.out else (
        Path(__file__).resolve().parents[1] / "docs" / f"backtest-round1-report-{date.today().isoformat()}.md"
    )
    out.write_text(markdown, encoding="utf-8")
    total = sum(len(t) for t in report.runs.values())
    print(f"标的 {len(frames)} 个；模拟组合 {len(report.runs)} 个；交易 {total} 笔")
    print(f"报告已写入 {out}")


if __name__ == "__main__":
    main()
