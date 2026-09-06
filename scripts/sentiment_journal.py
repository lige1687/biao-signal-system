#!/usr/bin/env python3
"""散户情绪终版信号·每日存证与推送（2026-09-06）。

record（默认）：读最新快照的两条信号 →
  1. 落存证账本 ~/.lei_signal_lab/cache/sentiment_signal_journal.json
     （含当日收盘，供 T+N 对账）；
  2. 触发时推送（macOS + 飞书双通道，FEISHU_WEBHOOK_URL 环境变量）：
     持仓相关板块触发 → 高优先；其余 → 普通。
review：对账所有 T+10/T+20 已到期的记录（用板块趋势历史的收盘价），
  输出累计战绩（前向存证，实验报告零售-sentiment-ts 的续篇素材）。

持仓赛道→板块映射（portfolio_groups 同源，2026-09-06）：
  cn_info→通信/半导体/计算机/电子；cn_metal→有色；cn_green_other→
  电力设备/电池/公用事业；医药相关→化学制药/生物制品/医药生物。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lei_signal.data.cache import DEFAULT_CACHE_DIR  # noqa: E402

CACHE = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))
JOURNAL = CACHE / "sentiment_signal_journal.json"

HOLDING_BOARDS = {
    "BK1215", "BK1036", "BK1207", "BK1201",          # cn_info 通信/半导体/计算机/电子
    "BK0478", "BK0732", "BK1015",                    # cn_metal 有色/贵金属/能源金属
    "BK1200", "BK1033", "BK0427",                    # cn_green_other 电力设备/电池/公用事业
    "BK0465", "BK1044", "BK1216",                    # 医药（创新药近似）
    "BK1277",                                        # 白酒
}
EXP_REF = "docs/experiments/retail-sentiment-ts-2026-09-05.md"


def _load_journal() -> dict:
    if JOURNAL.exists():
        try:
            return json.loads(JOURNAL.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"records": []}


def record(*, dry_run: bool = False) -> int:
    from lei_signal.notify.base import NotificationPayload
    from lei_signal.notify.macos import MacNotifier

    snap = json.loads((CACHE / "sector_trend_snapshot.json").read_text(encoding="utf-8"))
    date = snap.get("trading_day") or snap.get("date")
    journal = _load_journal()
    if any(r.get("date") == date for r in journal["records"]):
        print(f"{date} 已存证，跳过")
        return 0

    picks, alarms = [], []
    for b in snap.get("boards", []):
        if b.get("sig_icepoint_pick"):
            picks.append({"code": b["code"], "name": b["name"], "z": b.get("sig_retail_z"),
                          "close": b.get("close"), "holding": b["code"] in HOLDING_BOARDS})
        if b.get("sig_heat_alarm"):
            alarms.append({"code": b["code"], "name": b["name"], "z": b.get("sig_retail_z"),
                           "b50": b.get("b50"), "close": b.get("close"),
                           "holding": b["code"] in HOLDING_BOARDS})
    meta = snap.get("sentiment_signals") or {}
    journal["records"].append({
        "date": date, "cn_cold": meta.get("cn_cold"),
        "picks": picks, "alarms": alarms, "as_of": snap.get("as_of"),
        "review": {},
    })
    JOURNAL.write_text(json.dumps(journal, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ 存证 {date}：冰点机会 {len(picks)} 个，强热警报 {len(alarms)} 个")

    if not (picks or alarms):
        return 0
    holding_hit = [x for x in picks + alarms if x.get("holding")]
    lines = []
    if alarms:
        lines.append("⚠️ 强势散户热警报（回测10日-9.3%）：" +
                     "、".join(f"{a['name']}{'(持仓)' if a['holding'] else ''}" for a in alarms[:6]))
    if picks:
        lines.append("❄️ 冰点机会（回测10日超额+6.5~7.8%）：" +
                     "、".join(f"{p['name']}{'(持仓)' if p['holding'] else ''}" for p in picks[:6]))
    lines.append("research_proxy·非买卖点·前向存证中")
    payload = NotificationPayload(
        title=("【情绪信号·持仓相关】" if holding_hit else "【情绪信号】") +
               f"{date} 触发 {len(alarms) + len(picks)} 项",
        body_md="\n".join(lines), tier=1 if holding_hit else 2, plan_id="sentiment-signals",
    )
    from lei_signal.notify.feishu_webhook import FeishuWebhookNotifier

    notifiers = [MacNotifier(dry_run=dry_run)]
    webhook = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
    if webhook or dry_run:
        notifiers.append(FeishuWebhookNotifier(webhook if not dry_run else None, dry_run=dry_run))
    for n in notifiers:
        try:
            if n.send(payload):
                print(f"✓ 已推送（{type(n).__name__}）")
                break
        except Exception as exc:  # noqa: BLE001
            print(f"  推送渠道失败 {type(n).__name__}: {exc}")
    return 0


def review() -> int:
    journal = _load_journal()
    hist = json.loads((CACHE / "sector_trend_history.json").read_text(encoding="utf-8"))
    close_by_date = {
        r["date"]: {c: v.get("close") for c, v in r["boards"].items()} for r in hist
    }
    dates = sorted(close_by_date)

    def close_at(code: str, date: str, offset: int) -> float | None:
        try:
            i = dates.index(date)
        except ValueError:
            return None
        j = i + offset
        if j >= len(dates):
            return None
        return close_by_date[dates[j]].get(code)

    stats = {"pick10": [], "pick20": [], "alarm10": [], "alarm20": []}
    changed = 0
    for rec in journal["records"]:
        if rec.get("review", {}).get("done"):
            continue
        d = rec["date"]
        for key, group, horizon, bucket in (
            ("t10", rec["picks"], 10, "pick10"), ("t20", rec["picks"], 20, "pick20"),
            ("a10", rec["alarms"], 10, "alarm10"), ("a20", rec["alarms"], 20, "alarm20"),
        ):
            if key in rec.get("review", {}):
                continue
            rets = []
            for x in group:
                c10 = close_at(x["code"], d, horizon)
                if c10 and x.get("close"):
                    rets.append(round(c10 / x["close"] - 1, 4))
            if len(rets) == len(group) and group:  # 全部到期才写
                rec["review"][key] = rets
                stats[bucket].extend(rets)
                changed += 1
        # 全部四个键齐了标记完成
        if all(k in rec["review"] for k in ("t10", "t20", "a10", "a20")):
            rec["review"]["done"] = True
    if changed:
        JOURNAL.write_text(json.dumps(journal, ensure_ascii=False, indent=1), encoding="utf-8")

    import numpy as np

    print("== 前向存证战绩（绝对收益；基准对账见实验报告续篇） ==")
    for label, key in (("冰点机会·10日", "pick10"), ("冰点机会·20日", "pick20"),
                       ("强热警报·10日（期望为负）", "alarm10"), ("强热警报·20日", "alarm20")):
        v = stats.get(key) or []
        if not v:
            # 汇总历史已完成记录
            v = [r for rec in journal["records"]
                 for r in (rec["review"].get({"pick10": "t10", "pick20": "t20",
                                              "alarm10": "a10", "alarm20": "a20"}[key]) or [])]
        if v:
            v_arr = np.array(v)
            print(f"  {label}: n={len(v)} 胜率{(v_arr > 0).mean() * 100:.0f}% 均{v_arr.mean() * 100:+.2f}%")
        else:
            print(f"  {label}: 暂无到期样本")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["record", "review"], nargs="?", default="record")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    return review() if args.action == "review" else record(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
