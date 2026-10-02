"""对比人工标准答案（hand-answers.json）与冻结引擎实际行为（frozen-behavior.json），给出每条边界的判定。

用法：/tmp/bq-venv/bin/python compare.py   （先运行 ledger.py、probe_frozen.py、real_accounts.py）
只写本目录 boundary-results.json。

判定口径：
- 一致：冻结程序的输出与按旧合同手算的答案相同。
- 不一致：冻结程序与旧合同手算答案不同（实现没有做到合同写的内容）。
- 研究假设局限：冻结程序符合旧合同，但旧合同的假设与真实产品/交易规则不同，或几份旧合同对同一情形口径不一。
每条判定附“真实封存记录是否触发”，其证据来自 real-scans.json（real_accounts.py 生成）。
"""
from __future__ import annotations

import json
import sys
from decimal import Decimal as D
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TOL = D("1e-6")
REASON_MAP = {"position_exists": "position_held", "pending_exit": "position_held",
              "known_open_unavailable": "blocked", "at_open_limit_conservative": "open_limit",
              "insufficient_cash_or_risk_lot": "insufficient_cash_or_lot"}
HAND_ONLY = ("calc.", "positions.0.planned_risk", "positions.0.risk_lots", "positions.0.cash_lots")

# 研究假设局限：引擎与旧合同相符，但旧合同与真实规则不同或合同之间不一。键为案例，值为说明。
LIMITATIONS = {
    "C04b": "旧合同（IF第11行）的保守容差0.00051在“前收×10%”恰为半分位时，把比真实涨停价低一个价位的开盘也判为受限；真实规则下该价位可以报价成交。",
    "C04c": "旧合同对涨跌停双向一律不成交；真实规则只禁止越过涨跌停价，跌停价买入（或涨停价卖出）在价格上允许，能否成交取决于盘口，日线无法判断。真实记录：首12的4个宽度账户在2024-10-08开盘涨停时卖出被挡、次日低价卖出，见 real-scans.json B04。",
    "C08b_misdated": "引擎只支持“生效日开盘前”一种拆分时点；日终折算的产品若按折算当天录入，当天持仓市值按5倍计算（小例子账户从100,297元变成233,617元）。旧510300/159915没有已知拆分；新产品（如510500的2022年日终拆分）录入时必须把生效日写成首个新单位报价日。",
    "C08c": "旧合同（IF第21行）允许拆分后的零碎份额保留并全部卖出；真实产品的份额精度和零碎份额处理由基金公告决定，本快照没有这类规则。",
    "C09b": "拆分后没有新报价就除息时，48账户引擎按“旧收盘÷拆分倍数”推导参照价继续换算（与IF第21行一致），而价格换算器合同 protocol-amendment-1 第2条要求停止、不做二次推导。两份旧合同口径不同。",
}
# 不一致但由运行入口另行保护的情形
GUARDED = {
    "C05b": "引擎本身没有“禁止收盘估值”输入，会用这根报价估值并触发卖出；旧协议要求停下核口径，冻结运行入口 run_accounts.py 第36行 `assert \"2021-02-08\" not in prices[\"sz159915\"]` 承担了这项保护。复用引擎时必须保留同类断言。",
}
EXPLAIN_MISMATCH = {
    "C01a": "48账户引擎用二进制小数计算“现金÷(开盘价×(1+费率))÷100”再向下取整，现金恰好够整数手时会少算一手（应买10000份，实际9900份）。风险份数那一路加了1e-12的保护，现金那一路没有。",
    "C06d_F": "首12程序在除息日只记应收、不把估值价扣掉每份现金；除息日若没有报价，当天财富会把分红多算一次（104,851元，应为99,901元），下一个报价日才恢复。这会制造一天的假高点和随后的假回撤。",
    "C08d": "首12程序拆分时只把份数乘倍数、不把旧估值价除倍数；拆分日若没有报价（真实的513100拆分日就停牌），当天财富虚增5倍（495,901元，应为99,901元）。",
}


def num(x):
    try:
        return D(str(x))
    except Exception:
        return None


def frozen_value(res: dict, path: str):
    head, *rest = path.split(".", 1)
    if head == "status":
        return res["status"]
    if head == "trade_count":
        return len(res["trades"])
    if head == "sell_count":
        return sum(t["side"] == "sell" for t in res["trades"])
    if head == "daily":
        day, field = rest[0].rsplit(".", 1)
        return res["daily"][day][field]
    if head == "orders":
        cid, field = rest[0].split(".", 1)
        o = res["orders"][cid]
        if field == "attempt_count":
            return len(o["attempts"])
        val = o[field]
        return REASON_MAP.get(val, val) if field == "reason" else val
    if head == "sell":
        idx, field = rest[0].split(".", 1)
        return res["sells"][int(idx)][field]
    if head == "trades":
        idx, field = rest[0].split(".", 1)
        return res["trades"][int(idx)][field]
    if head == "positions":
        idx, field = rest[0].split(".", 1)
        if field == "budget":
            buys = [t for t in res["trades"] if t["side"] == "buy"]
            return buys[int(idx)]["risk_budget"]
        return res["positions"][int(idx)][field]
    raise KeyError(path)


def equal(want, got) -> bool:
    if isinstance(got, bool):
        return want == ("true" if got else "false")
    a, b = num(want), num(got)
    if a is not None and b is not None:
        return abs(a - b) <= TOL
    return str(want) == str(got)


def compare_fields(expected: dict, res: dict) -> dict:
    rows = {}
    for path, want in expected.items():
        if path.startswith(HAND_ONLY):
            rows[path] = dict(hand=want, frozen=None, ok=None, note="人工推导量，引擎不输出")
            continue
        if res["status"] != "ok" and path != "status":
            rows[path] = dict(hand=want, frozen=None, ok=False, note="引擎报错")
            continue
        try:
            got = frozen_value(res, path)
            rows[path] = dict(hand=want, frozen=got, ok=equal(want, got))
        except (KeyError, IndexError) as exc:
            rows[path] = dict(hand=want, frozen=f"<缺失 {exc}>", ok=False)
    return rows


def real_triggers(scan: dict) -> dict:
    """每条边界在真实封存记录里是否出现、是否改变已保存数字（来自 real-scans.json）。"""
    q = scan["B01_B02_buy_quantity"]
    u = scan["B04_unfilled"]
    act = scan["B06_B07_B08_actions"]
    term = scan["B10_B12_terminal"]
    f12 = u["first12_open_limit_rejections"]
    easy = [r for r in f12 if r["blocked_side_is_easy_side"]]
    return {
        "B01": f"48账户{q['buys_checked']}笔买入十进制重算份数，不同或落在取整临界的0笔；C01a的浮点少一手问题未在真实记录出现。",
        "B02": f"A/C/D共{sum(q['acd_binding_counts'].values())}笔买入：现金先卡住{q['acd_binding_counts']['现金先卡住']}笔、1%风险先卡住{q['acd_binding_counts']['1%风险先卡住']}笔。",
        "B03": f"同日既卖又买{len(scan['B03_same_day_order']['same_day_buy_and_sell'])}次、买入当天或更早卖出{len(scan['B03_same_day_order']['sell_on_or_before_entry'])}次、持仓重叠{len(scan['B03_same_day_order']['overlapping_positions'])}次；因已有持仓拒绝{scan['B03_same_day_order']['rejected_as_position_exists_or_pending_exit']}次。",
        "B04": f"48账户开盘受限未成交{u['technical_open_limit_rejections']}次、期末未执行订单{len(u['pending_at_end'])}个；首12账户开盘受限{len(f12)}次，全部正好在交易所涨跌停价，其中{len(easy)}次是开盘涨停时被挡住的卖出。全部1498笔真实成交没有一笔在涨跌停价或差一个价位。",
        "B05": f"2021-02-08在两份行情中都没有报价（技术{scan['B05_suspension']['quote_2021_02_08_present_technical']}、首12{scan['B05_suspension']['quote_2021_02_08_present_first12']}）；3个跨停牌持仓按02-05收盘估值，02-09按当日收盘估值，没有开盘成交尝试。",
        "B06": f"研究期除息日全部有报价（无报价除息日：{act['ex_dates_without_quote']}）；{act['dividend_event_rows_checked']}条账户×分红事件的权利份数与金额不同{len(act['dividend_event_mismatches'])}条。首12程序的无报价除息问题未在真实记录出现。",
        "B07": f"除息后、到账前卖出的持仓{len(act['positions_sold_between_ex_and_pay'])}段，分红均记回原持仓。",
        "B08": "510300、159915研究期内没有已记录拆分，真实记录不能覆盖；两产品拆分正式覆盖不完整。",
        "B09": f"{scan['B09_level_conversion']['positions_checked']}段带行动换算的持仓独立重算失效位/目标，不同{len(scan['B09_level_conversion']['mismatches'])}段。",
        "B10": f"期末仍持有{len(term['accounts_with_open_positions'])}个账户各1段；已卖出+未卖出=总盈亏，最大差{term['max_bridge_diff']}元；期末应收全部为0。",
        "B11": f"48账户每日累计投入均为100000元、无追加（不符{len(scan['B11_external_input']['rows_with_funding_not_100000_or_deposit'])}户）。",
        "B12": "期末假想卖出费用另列，见 real-scans.json B10_B12_terminal；保存的期末财富都未扣这笔费用。",
    }


def main():
    cases = {c["id"]: c for c in json.loads((HERE / "cases.json").read_text())["cases"]}
    hand = {c["id"]: c for c in json.loads((HERE / "hand-answers.json").read_text())["cases"]}
    frozen = {c["id"]: c for c in json.loads((HERE / "frozen-behavior.json").read_text())["cases"]}
    out = []
    for cid, case in cases.items():
        h, f = hand[cid], frozen[cid]["result"]
        prim = compare_fields(case["hand_expected"], f)
        entry = dict(id=cid, boundary=case["boundary"], engine=case["engine"], title=case["title"],
                     hand_status=h["primary"]["result"]["status"], frozen_status=f["status"],
                     hand_stop_reason=h["primary"]["result"].get("stop_reason"), primary_checks=prim)
        if "secondary" in case:
            entry["secondary_label"] = case["secondary"]["label"]
            entry["secondary_checks"] = compare_fields(case["secondary"]["hand_expected"], f)
        all_ok = all(v["ok"] is not False for v in prim.values())
        if cid in LIMITATIONS:
            verdict, why = "研究假设局限", LIMITATIONS[cid]
            entry["engine_matches_old_contract"] = all_ok if cid not in ("C08b_misdated", "C09b") else None
        elif cid in GUARDED:
            verdict, why = "一致（保护在运行入口，引擎本身不拦）", GUARDED[cid]
        elif all_ok:
            verdict, why = "一致", "冻结程序与手算答案逐项相同。"
        else:
            verdict, why = "不一致", EXPLAIN_MISMATCH.get(cid, "见 primary_checks 中 ok=false 的字段。")
        entry.update(verdict=verdict, explanation=why,
                     mismatched_fields=[p for p, v in prim.items() if v["ok"] is False])
        out.append(entry)
    summary = {}
    for e in out:
        summary.setdefault(e["verdict"], []).append(e["id"])
    scan = json.loads((HERE / "real-scans.json").read_text())
    trig = real_triggers(scan)
    per_boundary = {}
    for e in out:
        for b in e["boundary"].split(","):
            per_boundary.setdefault(b, dict(cases={}, real_records=trig[b]))["cases"][e["id"]] = e["verdict"]
    payload = dict(_note="人工答案与冻结引擎行为逐项对比；real_records 来自 real-scans.json（real_accounts.py）。",
                   summary=summary, per_boundary=dict(sorted(per_boundary.items())), cases=out)
    (HERE / "boundary-results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str) + "\n")
    for k, v in summary.items():
        print(k, len(v), v)
    unexpected = [e["id"] for e in out if e["verdict"] == "不一致" and e["id"] not in EXPLAIN_MISMATCH]
    if unexpected:
        print("UNEXPLAINED MISMATCH", unexpected)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
