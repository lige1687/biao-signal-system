#!/usr/bin/env python3
"""散户情绪终版信号·每日存证与推送（2026-09-06；09-07 GLM02；09-08 GLM02R 返修）。

record（默认）：读最新快照的两条信号 →
  1. 落 JSON 存证账本（含当日收盘，供 T+N 对账）；
  2. 同步统一观察账本（SQLite，幂等去重）；同日内容变化=修订：旧记录标
     superseded 保留原文、新记录追加——不再直接返回吞掉修订（R03）；
     同内容重试也会重跑同步（同步失败可见、可幂等重试，R05/§5）；
  3. 触发时推送（macOS + 飞书）。dry-run 对 JSON 与 SQLite 均零写入、
     零通知（§5）。

review：对账所有 T+10/T+20 已到期记录：
  - 逐对象逐期限检查：一个板块缺价只挂起它自己，整天 done 只在所有
    对象×期限全部成熟时置位（R06，不再组键齐了就标整天完成）；
  - 旧格式结果（纯收益列表、无对象对应证据）整体转 legacy_{key} 原样
    保留，不按列表位置猜配对象（§5）；
  - 缺数据可恢复：missing 行等行情补齐后下次继续（无 60 天停止标准）；
  - 强热方向=看跌：按「方向命中」统计（下跌=命中），同时展示带符号
    真实涨跌；无基准只报绝对涨跌不标"超额"；
  - 均值口径：证据账本原文为「15日均收」，通知/汇总文案统一用"平均"
    （01R 裁定，不改回测结论本身）；
  - 结果同步观察账本（行参考口径 + 严格日历口径占位；严格口径需 01R
    日历适配器，日历不明不产生 ready）。

--dry-run：不写任何账本（JSON 与 SQLite）、不发通知。
--as-of YYYY-MM-DD：review 历史重放截止日（晚于该日的行情行不可用，R06/M）。

持仓赛道→板块映射（portfolio_groups 同源，2026-09-06）：
  cn_info→通信/半导体/计算机/电子；cn_metal→有色；cn_green_other→
  电力设备/电池/公用事业；医药相关→化学制药/生物制品/医药生物。
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
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

#: (review键, 组名, 期限, 期待方向)：picks=看涨，alarms=看跌
GROUPS = (
    ("t10", "picks", 10, "up"),
    ("t20", "picks", 20, "up"),
    ("a10", "alarms", 10, "down"),
    ("a20", "alarms", 20, "down"),
)


def _content_hash(picks: list, alarms: list) -> str:
    canon = json.dumps([picks, alarms], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def _load_journal() -> dict:
    if JOURNAL.exists():
        try:
            return json.loads(JOURNAL.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"records": []}


def _save_journal(journal: dict) -> None:
    """原子写（tmp+replace），防并发半写。"""
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    tmp = JOURNAL.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(journal, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(JOURNAL)


def _open_ledger_db():
    """统一观察账本连接（LEI_SQLITE_PATH 可覆盖；失败不阻断情绪线）。"""
    try:
        from lei_signal.api.config import sqlite_path
        from lei_signal.storage.sqlite_store import connect

        return connect(sqlite_path())
    except Exception:  # noqa: BLE001
        return None


def _sync_observations(journal: dict) -> tuple[bool, str]:
    """JSON 账本 → 观察账本（幂等；返回 成功与否+说明，失败可见可重试）。

    旧记录（无 origin 标记）迁入时标 legacy，不与上线后真实前向样本合并
    （v1.2 §5）；同日修订由 JSON 的 superseded 记录承载，SQLite 侧按
    完整语义身份去重、展示批次按内容比较。
    """
    conn = _open_ledger_db()
    if conn is None:
        return False, "观察账本不可用（打开失败）"
    try:
        from lei_signal.copilot import observation

        # 稳定修订键（P5）：date + 同日第几版 + 内容 hash——同一份 JSON 重放
        # 键不变（重跑不增批次）；旧版重试不夺当前（record_observations 带键
        # 模式保证）。同日版本序按 JSON 记录顺序计算（追加写保序）。
        per_date_seq: dict[str, int] = {}
        synced = failed = 0
        first_err: str | None = None
        for rec in journal["records"]:
            if not isinstance(rec, dict):  # 损坏记录跳过，不阻断其余同步
                failed += 1
                continue
            date = rec.get("date")
            if not isinstance(date, str) or not date:
                failed += 1  # dict 缺 date：单条隔离（P9），不回滚其他记录
                continue
            seq = per_date_seq.get(date, 0) + 1
            per_date_seq[date] = seq
            picks = [p for p in (rec.get("picks") or [])
                     if isinstance(p, dict) and p.get("code")]
            alarms = [a for a in (rec.get("alarms") or [])
                      if isinstance(a, dict) and a.get("code")]
            revision_key = (f"{date}#v{seq}:"
                            f"{rec.get('content_hash') or _content_hash(picks, alarms)}")
            try:  # 单条失败隔离（P9）：逐条提交，坏一条只回滚它自己
                observation.record_sentiment_day(
                    conn, date=date, picks=picks, alarms=alarms,
                    emitted_at=rec.get("as_of") or None,
                    legacy=rec.get("origin", "legacy") != "live",
                    revision_key=revision_key,
                    input_hash=rec.get("content_hash") or "unknown",
                    available_at=rec.get("as_of"),
                )
                conn.commit()
                synced += 1
            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                failed += 1
                first_err = first_err or str(exc)
        if synced == 0 and failed > 0:
            # 一条都没成功：系统性故障（如连接损坏）——失败可见、下次重试，
            # 不把「全部隔离」伪装成同步成功
            return False, f"同步失败：{failed} 条记录全部失败（首个错误：{first_err}）"
        note = f"已同步 {synced} 条记录"
        if failed:
            note += f"；{failed} 条损坏/缺键记录已隔离跳过"
        return True, note
    except Exception as exc:  # noqa: BLE001  失败可见；JSON 账本不受影响
        with contextlib.suppress(Exception):
            conn.rollback()
        return False, f"同步失败：{exc}"
    finally:
        conn.close()


def record(*, dry_run: bool = False) -> int:
    snap = json.loads((CACHE / "sector_trend_snapshot.json").read_text(encoding="utf-8"))
    date = snap.get("trading_day") or snap.get("date")
    journal = _load_journal()

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
    chash = _content_hash(picks, alarms)

    if dry_run:
        same = any(r.get("date") == date and not r.get("superseded")
                   and r.get("content_hash") == chash for r in journal["records"])
        print(f"[dry-run] {date} 冰点机会 {len(picks)} 个，强热警报 {len(alarms)} 个；"
              f"同日同内容={'是（重试，仅重跑同步）' if same else '否（记新修订）'}"
              "（不写 JSON 账本、不写观察账本、不推送）")
        return 0

    same_day = [r for r in journal["records"] if r.get("date") == date]
    current = next((r for r in same_day if not r.get("superseded")
                    and r.get("content_hash") == chash), None)
    if current is not None:
        # 同日同内容重试：不追加，但同步必须重跑（上次可能失败）
        print(f"{date} 已存证且内容未变，跳过追加；重跑观察账本同步")
    else:
        for r in same_day:
            if not r.get("superseded"):
                r["superseded"] = True  # 旧话原文保留，只标被修订（R03）
        journal["records"].append({
            "date": date, "cn_cold": meta.get("cn_cold"),
            "picks": picks, "alarms": alarms, "as_of": snap.get("as_of"),
            "review": {}, "origin": "live", "content_hash": chash,
        })
        _save_journal(journal)
        print(f"✓ 存证 {date}：冰点机会 {len(picks)} 个，强热警报 {len(alarms)} 个"
              + (f"（同日第 {len(same_day) + 1} 版，旧版已标修订保留）" if same_day else ""))

    ok, note = _sync_observations(journal)
    print(("✓ 观察账本同步：" + note) if ok else f"✗ 观察账本未同步（{note}）——"
          "下次 record/review 会自动重试；JSON 存证不受影响")

    if not (picks or alarms) or current is not None and not (picks or alarms):
        return 0
    if current is not None:
        return 0  # 同内容重试不重复推送
    _push(date=date, alarms=alarms, picks=picks)
    return 0


def _push(*, date, alarms, picks) -> None:
    from lei_signal.notify.base import NotificationPayload
    from lei_signal.notify.macos import MacNotifier

    holding_hit = [x for x in picks + alarms if x.get("holding")]

    def names(xs):
        return "、".join(f"{x['name']}{'(持仓)' if x['holding'] else ''}" for x in xs[:6])

    lines = []
    if alarms:
        lines.append("⚠️ 强势散户热警报（条件版：仅市场转弱期可信 -3.6%~-12.7%，"
                     "结构牛市期反向 +7.6%）：" + names(alarms))
    if picks:
        # 均值口径（01R 裁定：证据账本原文为「15日均收」，非中位）
        lines.append("❄️ 冰点机会（四次恐慌期均收为正：15日平均 "
                     "+0.6%~+12.9%）：" + names(picks))
    lines.append("research_proxy·非买卖点·前向存证对账中")
    payload = NotificationPayload(
        title=("【情绪信号·持仓相关】" if holding_hit else "【情绪信号】") +
               f"{date} 触发 {len(alarms) + len(picks)} 项",
        body_md="\n".join(lines), tier=1 if holding_hit else 2, plan_id="sentiment-signals",
    )
    from lei_signal.notify.feishu_webhook import FeishuWebhookNotifier

    notifiers = [MacNotifier(dry_run=False)]
    webhook = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
    if webhook:
        notifiers.append(FeishuWebhookNotifier(webhook, dry_run=False))
    for n in notifiers:
        try:
            if n.send(payload):
                print(f"✓ 已推送（{type(n).__name__}）")
                break
        except Exception as exc:  # noqa: BLE001
            print(f"  推送渠道失败 {type(n).__name__}: {exc}")


class _History:
    """板块趋势历史收盘查询（行参考口径）+ 精确日期查询（严格口径用）。

    as_of 截止（R06/M）：晚于 as_of 的行情行一律不可用。
    """

    def __init__(self, hist: list, as_of: str | None = None):
        self.close_by_date = {
            r["date"]: {c: v.get("close") for c, v in r.get("boards", {}).items()}
            for r in hist if isinstance(r, dict) and r.get("date")
            and (as_of is None or r["date"] <= as_of)
        }
        self.dates = sorted(self.close_by_date)

    def base_index(self, date: str) -> int | None:
        import bisect

        i = bisect.bisect_right(self.dates, date) - 1
        return i if i >= 0 else None

    def close_at(self, code: str, date: str, offset: int) -> tuple[str, float] | None:
        i = self.base_index(date)
        if i is None:
            return None
        j = i + offset
        if j >= len(self.dates):
            return None
        d = self.dates[j]
        c = self.close_by_date[d].get(code)
        if c is None or c != c or c <= 0:  # None/NaN/非正 → 坏值隔离
            return None
        return d, float(c)

    def price_at(self, code: str, date: str) -> float | None:
        c = self.close_by_date.get(date, {}).get(code)
        if c is None or c != c or c <= 0:
            return None
        return float(c)


def _valid_close(v) -> bool:
    # None/NaN/非正/非数值（含字符串）均为坏值
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v > 0


def review(*, save: bool = True, as_of: str | None = None) -> int:
    """对账到期记录并打印累计战绩。save=False 只读；as_of 裁剪历史重放。"""
    journal = _load_journal()
    hist = json.loads((CACHE / "sector_trend_history.json").read_text(encoding="utf-8"))
    history = _History(hist, as_of=as_of)

    newly_done: list[tuple[str, str]] = []
    for rec in journal["records"]:
        if not isinstance(rec, dict):  # 损坏的单条旧记录：跳过，不阻断其他记录
            continue
        # 旧格式结果（纯收益列表，无对象对应证据）：整体转 legacy_ 原样保留，
        # 不按列表位置猜配对象（v1.2 §5）
        rv = rec.setdefault("review", {})
        for key, *_ in GROUPS:
            if isinstance(rv.get(key), list):
                rv[f"legacy_{key}"] = rv.pop(key)
                rec.setdefault("origin", "legacy")
        if rv.get("done"):
            continue
        d = rec["date"]
        for key, group_name, horizon, _direction in GROUPS:
            group = [x for x in (rec.get(group_name, []) or [])
                     if isinstance(x, dict) and x.get("code")]
            entry = rv.get(key)
            if not group:
                if entry is None:
                    rv[key] = {}
                    newly_done.append((d, key))
                continue
            done_map: dict[str, dict] = dict(entry) if isinstance(entry, dict) else {}
            changed = False
            for x in group:
                code = x["code"]
                if code in done_map:
                    continue
                base = x.get("close")
                if not _valid_close(base):
                    done_map[code] = {"invalid_base": True}
                    changed = True
                    continue
                found = history.close_at(code, d, horizon)
                if found is None:
                    continue  # 未到期/缺价 → 留空待补（可恢复，R06）
                done_map[code] = {"ret": round(found[1] / base - 1, 4),
                                  "eval_date": found[0]}
                changed = True
            if changed:
                rv[key] = done_map
                newly_done.append((d, key))
        # 整天 done：每个组内每个对象都有结果（缺价对象不算完成）才置位
        all_groups_complete = True
        for key, group_name, _h, _dir in GROUPS:
            group = [x for x in (rec.get(group_name, []) or [])
                     if isinstance(x, dict) and x.get("code")]
            entry = rv.get(key)
            if not group:
                continue
            codes = {x["code"] for x in group}
            if not isinstance(entry, dict) or not codes <= set(entry):
                all_groups_complete = False
        if all_groups_complete and all(k in rv for k, *_ in GROUPS):
            rv["done"] = True
    if save:
        _save_journal(journal)

    # ---- 汇总：累计全部已成熟（新格式逐对象；旧格式 legacy 单列不并入） ----
    import numpy as np

    buckets = {"pick10": [], "pick20": [], "alarm10": [], "alarm20": []}
    legacy_buckets = {"pick10": 0, "pick20": 0, "alarm10": 0, "alarm20": 0}
    new_counts = {k: 0 for k in buckets}
    zero_days = pending_objs = invalid_objs = future_saved = 0
    keymap = (("t10", "pick10"), ("t20", "pick20"), ("a10", "alarm10"), ("a20", "alarm20"))
    for rec in journal["records"]:
        if not isinstance(rec, dict):
            continue
        rv = rec.get("review", {})
        if not rec.get("picks") and not rec.get("alarms"):
            zero_days += 1
        for key, bucket in keymap:
            v = rv.get(key)
            if isinstance(v, dict):
                for _code, e in v.items():
                    if isinstance(e, dict) and "ret" in e:
                        # P10：历史重放时，评价日晚于 as_of 的已存结果不算
                        # （未来成绩不进重放视图；生产已存结果不被抹掉）
                        ed = e.get("eval_date")
                        if as_of and isinstance(ed, str) and ed > as_of:
                            future_saved += 1
                            continue
                        buckets[bucket].append(e["ret"])
                    elif isinstance(e, dict) and e.get("invalid_base"):
                        invalid_objs += 1
                    else:
                        pending_objs += 1
                if any(rec["date"] == nd[0] and nd[1] == key for nd in newly_done):
                    new_counts[bucket] += sum(
                        1 for e in v.values()
                        if isinstance(e, dict) and "ret" in e)
            lk = f"legacy_{key}"
            if lk in rv and isinstance(rv[lk], list):
                legacy_buckets[bucket] += len(rv[lk])

    def _line(label: str, vals: list[float], expect_down: bool) -> str:
        if not vals:
            return f"  {label}: 暂无到期样本"
        arr = np.array(vals)
        hit = int((arr < 0).sum()) if expect_down else int((arr > 0).sum())
        return (f"  {label}: 到期{len(arr)}个 方向命中{hit}个"
                f"（{hit / len(arr) * 100:.0f}%）平均涨跌{arr.mean() * 100:+.2f}%"
                f" 最好{arr.max() * 100:+.1f}% 最差{arr.min() * 100:+.1f}%")

    print("== 前向存证累计战绩（绝对涨跌，无基准不标超额；未到期不进分母） ==")
    print(_line("冰点机会·10日（期待上涨，上涨=方向命中）", buckets["pick10"], False))
    print(_line("冰点机会·20日（期待上涨）", buckets["pick20"], False))
    print(_line("强热警报·10日（期待下跌，下跌=方向命中）", buckets["alarm10"], True))
    print(_line("强热警报·20日（期待下跌）", buckets["alarm20"], True))
    print(f"  零触发日：{zero_days} 天（无信号，不计任何胜率）")
    if any(legacy_buckets.values()):
        print("  旧格式遗留样本（无法对应对象，单列不并入）：" + "，".join(
            f"{k}×{v}" for k, v in legacy_buckets.items() if v))
    if pending_objs:
        print(f"  待补数据对象×期限：{pending_objs} 项（行情到位后自动补）")
    if invalid_objs:
        print(f"  坏基价对象×期限：{invalid_objs} 项（存证收盘无效，隔离不计）")
    if future_saved:
        print(f"  重放截止后已有结果：{future_saved} 项（评价日晚于 --as-of，"
              "不计入本次重放；生产结果保留不变）")
    if any(new_counts.values()):
        print("  本次新增：" + "，".join(f"{k}+{v}" for k, v in new_counts.items() if v))

    # ---- 观察账本同步 + 到期检查（行参考口径；严格日历口径待 01R） ----
    if save:
        ok, note = _sync_observations(journal)
        print(("✓ 观察账本同步：" + note) if ok
              else f"✗ 观察账本未同步（{note}）——下次 record/review 自动重试")
        conn = _open_ledger_db()
        if conn is not None:
            try:
                from lei_signal.copilot import observation

                stats = observation.evaluate_sentiment_outcomes(
                    conn, lambda code, d, h: history.close_at(code, d, h),
                    as_of=as_of,
                )
                conn.commit()
                if stats.get("ready_rows_reference") or stats.get("ready_rows_strict"):
                    print(f"  观察账本：行参考口径补结果 {stats['ready_rows_reference']} 档"
                          + (f"，严格日历口径 {stats['ready_rows_strict']} 档"
                             if stats.get("ready_rows_strict") else
                             "（严格口径需日历适配器，未接入前不产生结果）"))
            except Exception as exc:  # noqa: BLE001
                print(f"  观察账本对账失败（不影响 JSON 账本）：{exc}")
            finally:
                conn.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["record", "review"], nargs="?", default="record")
    ap.add_argument("--dry-run", action="store_true",
                    help="不写任何账本（JSON/SQLite）、不发通知")
    ap.add_argument("--as-of", default=None,
                    help="review 历史重放截止日 YYYY-MM-DD（晚于该日的行情不可用）")
    args = ap.parse_args()
    if args.action == "review":
        return review(save=not args.dry_run, as_of=args.as_of)
    return record(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
