"""三档成绩汇总：纯系统 / AI否决权 / AI仓位权。"""
from __future__ import annotations

import json
import statistics


def main() -> None:
    signals = json.load(open("/tmp/ai_signals.json"))
    judges = {}
    for line in open("/tmp/ai_judgments.jsonl"):
        d = json.loads(line)
        judges[d["id"]] = d
    rows = []
    for s in signals:
        j = judges.get(s["id"])
        if not j:
            continue
        rows.append((s, j))
    n = len(rows)
    print(f"已判定 {n}/{len(signals)} 笔\n")

    def stats(rs):
        if not rs:
            return None
        vals = [r for r in rs]
        wins = sum(1 for r in vals if r > 0)
        return {
            "n": len(vals), "win": wins * 100 // len(vals),
            "total": sum(vals), "avg": sum(vals) / len(vals),
            "worst": min(vals),
            "hold_med": None,
        }

    # 档0：纯系统（全做，1倍注）
    t0 = [s["_r_net"] for s, _ in rows]
    # 档1：AI 否决权（do 子集，1倍注）
    t1 = [s["_r_net"] for s, j in rows if j["action"] == "do"]
    # 档2：AI 仓位权（全做，size 加权）
    t2 = [s["_r_net"] * j["size"] for s, j in rows if j["action"] == "do"]
    # 对照：AI 放弃的信号成绩（看它砍对了没有）
    skipped = [s["_r_net"] for s, j in rows if j["action"] == "skip"]

    for label, vals in [("档0 纯系统（全做×1.0）", t0), ("档1 AI否决（做do子集×1.0）", t1),
                        ("档2 AI仓位（do×size加权）", t2), ("（对照）AI放弃的信号", skipped)]:
        st = stats(vals)
        if st is None:
            continue
        worst5 = sum(sorted(vals)[:5])
        print(f"{label:24s}: {st['n']:>3d}笔 胜率{st['win']:>3d}% 累计{st['total']:>+7.1f}R "
              f"平均{st['avg']:>+5.2f}R 最差{st['worst']:>+6.1f}R 最差5笔{worst5:>+7.1f}R")

    # 仓位档分布与抽样理由
    from collections import Counter
    sizes = Counter((j["action"], j["size"]) for _, j in rows)
    print("\n决策分布:", dict(sizes))
    print("\ndo 且 size=1.5（AI 加大注）的信号实绩:")
    for s, j in rows:
        if j["action"] == "do" and j["size"] == 1.5:
            print(f"  {s['symbol']:12s} {s['entry_date']} {s['regime_cn']:4s} → {s['_r_net']:+.1f}R | {j['reason'][:30]}")
    print("\nskip 里 AI 砍掉的赚钱笔（前5笔最可惜的）:")
    for s, j in sorted([r for r in rows if r[1]["action"] == "skip"], key=lambda x: -x[0]["_r_net"])[:5]:
        print(f"  {s['symbol']:12s} {s['entry_date']} 砍掉了 {s['_r_net']:+.1f}R | {j['reason'][:32]}")


if __name__ == "__main__":
    main()
