"""T7 合同第 0 步演练：在不看任何未来结果的前提下，数出 T2 下一问题里
“两种 A3 读法有差别的回撤”能组成多少个互不重叠的时间簇。

窗口只用事前可知的日期：[触碰日, 两规则中较晚的信号日 + H 个交易日]，H=20（与已有研究的
主固定期限一致；看结果前固定）；只有一方入场时用该方信号日。跨标的、跨均线组按日历重叠合并。
输入与 T2 real_coverage.py 相同（GitHub 已跟踪的 510300、159915 名义日线，生产特征/构造函数）。
输出 qualification-count.json。
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
T2 = HERE.parent / "remote-astra-T2-2026-09-30"
sys.path[:0] = [str(HERE), str(T2), str(HERE.parents[3] / "src")]

from lifecycle_ref import RECOMMENDED  # noqa: E402
from method_examples import time_clusters  # noqa: E402
from real_coverage import SYMBOLS, features, load, ref_events, rows_of  # noqa: E402

H = 20


def main() -> None:
    opps, per_symbol = [], {}
    for symbol in SYMBOLS:
        frame, structs = features(load(symbol)[0])
        rows = rows_of(frame)
        days = [r["date"] for r in rows]
        pos = {d: i for i, d in enumerate(days)}
        any_ = {(e["group"], e["touch"]): e for e in ref_events(rows, structs, RECOMMENDED)
                if e["kind"] == "confirmed"}
        req = {(e["group"], e["touch"]): e for e in ref_events(
            rows, structs, {**RECOMMENDED, "a3_mode": "structure_required"}) if e["kind"] == "confirmed"}
        kinds = Counter()
        for key in sorted(set(any_) | set(req)):
            a, b = any_.get(key), req.get(key)
            if a and b and a["date"] == b["date"]:
                kinds["same_entry"] += 1
                continue
            kind = "dropped" if a and not b else "delayed" if a and b else "added"
            kinds[kind] += 1
            last = max(x["date"] for x in (a, b) if x)
            end = days[min(pos[last] + H, len(days) - 1)]
            opps.append({"id": f"{symbol}|g{key[0]}|{key[1]}", "window": [key[1], end], "kind": kind,
                         "symbol": symbol, "censored_at_data_end": pos[last] + H >= len(days)})
        per_symbol[symbol] = dict(kinds)
    cl = time_clusters(opps)
    sizes = Counter(cl.values())
    multi_symbol = sum(1 for c in sizes if len({o["symbol"] for o in opps if cl[o["id"]] == c}) > 1)
    out = {"H_trading_days": H, "per_symbol_kinds": per_symbol, "differing_opportunities": len(opps),
           "time_clusters": len(sizes), "cluster_size_distribution": dict(sorted(Counter(sizes.values()).items())),
           "max_cluster_size": max(sizes.values()) if sizes else 0,
           "clusters_spanning_both_symbols": multi_symbol,
           "smallest_attainable_sign_flip_share": 1 / 2 ** len(sizes) if sizes else None,
           "censored_at_data_end": sum(o["censored_at_data_end"] for o in opps),
           "years": dict(sorted(Counter(o["window"][0][:4] for o in opps).items())),
           "opportunities": [{**o, "cluster": cl[o["id"]]} for o in sorted(opps, key=lambda o: o["window"][0])],
           "_note": "只用触碰日、信号日和固定期限 H 划窗口，未读取任何未来收益；结构识别为生产全历史计算。"}
    (HERE / "qualification-count.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                                                   encoding="utf-8")
    print({k: v for k, v in out.items() if k != "opportunities"})


if __name__ == "__main__":
    main()
