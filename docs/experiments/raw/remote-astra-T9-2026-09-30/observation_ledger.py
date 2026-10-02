"""T9 未来观察记录：最小记录接口与状态推导（只用合成数据，不读任何真实或未来行情）。

记录是一份只追加的 JSON Lines 文件；每条记录带上一条的哈希（prev_hash），改写历史会被发现。
状态全部由记录推导，不另存“当前状态”。五个合成案例覆盖：等待结果、结果已成熟、
输入被修订、定义出现新版本、观察预算中断。运行：python observation_ledger.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KINDS = {"protocol_frozen", "input_snapshot", "opportunity", "outcome", "input_revision",
         "definition_version", "pause", "resume", "review"}
H = 20  # A03 固定期限：下一交易日收盘起 20 段日变化（第 21 个收盘）


def _digest(rec: dict) -> str:
    body = {k: v for k, v in rec.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def append(ledger: list[dict], rec: dict) -> dict:
    if rec["kind"] not in KINDS:
        raise ValueError(f"unknown kind {rec['kind']}")
    rec = {**rec, "seq": len(ledger), "prev_hash": ledger[-1]["hash"] if ledger else None}
    rec["hash"] = _digest(rec)
    ledger.append(rec)
    return rec


def validate(ledger: list[dict]) -> list[str]:
    """只追加、时间不倒流、结果不早于成熟日、观察机会不早于冻结时点。"""
    errors, prev, frozen = [], None, {}
    for i, r in enumerate(ledger):
        if r.get("seq") != i or r.get("prev_hash") != (prev["hash"] if prev else None) or _digest(r) != r["hash"]:
            errors.append(f"seq {i}: chain broken or record edited")
        if prev and r["recorded_at"] < prev["recorded_at"]:
            errors.append(f"seq {i}: recorded_at goes backwards")
        if r["kind"] == "protocol_frozen":
            frozen[r["object_ref"]] = r["payload"]["observe_after"]
        if r["kind"] == "opportunity":
            start = frozen.get(r["object_ref"])
            if start is None:
                errors.append(f"seq {i}: opportunity before its protocol was frozen")
            elif r["market_date"] <= start:
                errors.append(f"seq {i}: opportunity dated {r['market_date']} not after observe_after {start}")
        if r["kind"] == "outcome":
            if r["payload"]["mature_date"] > r["payload"]["data_through"]:
                errors.append(f"seq {i}: outcome recorded before it matured")
            if r["recorded_at"][:10] < r["payload"]["mature_date"]:
                errors.append(f"seq {i}: outcome recorded before maturity date")
        prev = r
    return errors


def derive(ledger: list[dict]) -> dict:
    """逐对象版本（流）与逐机会推导状态；旧版本流关闭但保留。"""
    streams, opps, paused = {}, {}, False
    for r in ledger:
        k, ref = r["kind"], r.get("object_ref")
        if k == "protocol_frozen":
            streams[ref] = {"status": "observing", "frozen_at": r["recorded_at"],
                            "protocol_sha256": r["payload"]["protocol_sha256"], "superseded_by": None}
        elif k == "definition_version":
            old, new = r["payload"]["old"], r["payload"]["new"]
            streams[old]["status"] = "closed_superseded"
            streams[old]["superseded_by"] = new
        elif k == "opportunity":
            opps[r["payload"]["opp_id"]] = {"stream": ref, "status": "waiting_outcome",
                                            "mature_date": r["payload"]["mature_date"],
                                            "snapshot": r["payload"]["snapshot_sha256"],
                                            "first_touch": r["payload"]["first_touch"], "outcome": None,
                                            "revisions": []}
        elif k == "outcome":
            o = opps[r["payload"]["opp_id"]]
            o["outcome"] = r["payload"]["values"]
            o["status"] = "matured"
        elif k == "input_revision":
            for oid in r["payload"]["affected"]:
                o = opps[oid]
                o["revisions"].append({"new_snapshot": r["payload"]["new_snapshot_sha256"],
                                       "change": r["payload"]["change"]})
                o["status"] = o["status"] + "+revised"
        elif k == "pause":
            paused = True
            for s in streams.values():
                if s["status"] == "observing":
                    s["status"] = "paused"
                    s["resume_point"] = r["payload"]["resume_point"]
        elif k == "resume":
            paused = False
            for s in streams.values():
                if s["status"] == "paused":
                    s["status"] = "observing"
                    s["gap"] = r["payload"]["gap"]
    return {"streams": streams, "opportunities": opps, "paused": paused}


def review(state: dict, stream: str) -> dict:
    """只用已成熟、属于该版本流、按首次记录值的结果；不足就说不足，不填 0。"""
    mats = [o for o in state["opportunities"].values() if o["stream"] == stream and o["outcome"]]
    first = [o["outcome"]["ret20"] for o in mats if o["first_touch"]]
    later = [o["outcome"]["ret20"] for o in mats if not o["first_touch"]]
    waiting = sum(1 for o in state["opportunities"].values()
                  if o["stream"] == stream and o["status"].startswith("waiting"))
    if not first or not later:
        verdict = "insufficient_no_comparison"
    else:
        verdict = "describe_only"
    return {"stream": stream, "matured_first": len(first), "matured_later": len(later), "waiting": waiting,
            "verdict": verdict,
            "first_mean": round(sum(first) / len(first), 6) if first else None,
            "later_mean": round(sum(later) / len(later), 6) if later else None,
            "revised_count": sum(1 for o in mats if o["revisions"])}


OBJ, OBJ2 = "research.a03.pullback_order@1.0.0", "research.a03.pullback_order@1.1.0"
FROZEN = {"protocol_sha256": "SYNTHETIC-not-a-real-protocol", "observe_after": "2026-10-09",
          "hypothesis": "first touch vs later touch, 20-day close-to-close change; A03 historical: not supported"}


def base() -> list[dict]:
    led: list[dict] = []
    append(led, {"kind": "protocol_frozen", "object_ref": OBJ, "recorded_at": "2026-10-09T16:00:00+08:00",
                 "market_date": "2026-10-09", "payload": FROZEN})
    append(led, {"kind": "input_snapshot", "object_ref": OBJ, "recorded_at": "2026-11-03T16:10:00+08:00",
                 "market_date": "2026-11-03", "payload": {"snapshot_sha256": "SYN-S1", "data_through": "2026-11-03"}})
    append(led, {"kind": "opportunity", "object_ref": OBJ, "recorded_at": "2026-11-03T16:11:00+08:00",
                 "market_date": "2026-11-03", "payload": {"opp_id": "SYN|seg1|n60|2026-11-03", "first_touch": True,
                                                          "mature_date": "2026-12-02", "snapshot_sha256": "SYN-S1"}})
    return led


def case_waiting():
    led = base()
    return led, review(derive(led), OBJ)


def case_matured():
    led = base()
    append(led, {"kind": "opportunity", "object_ref": OBJ, "recorded_at": "2026-11-20T16:05:00+08:00",
                 "market_date": "2026-11-20", "payload": {"opp_id": "SYN|seg1|n60|2026-11-20", "first_touch": False,
                                                          "mature_date": "2026-12-19", "snapshot_sha256": "SYN-S2"}})
    append(led, {"kind": "outcome", "object_ref": OBJ, "recorded_at": "2026-12-02T16:20:00+08:00",
                 "market_date": "2026-12-02", "payload": {"opp_id": "SYN|seg1|n60|2026-11-03", "mature_date": "2026-12-02",
                                                          "data_through": "2026-12-02", "values": {"ret20": 0.012}}})
    append(led, {"kind": "outcome", "object_ref": OBJ, "recorded_at": "2026-12-21T16:20:00+08:00",
                 "market_date": "2026-12-21", "payload": {"opp_id": "SYN|seg1|n60|2026-11-20", "mature_date": "2026-12-19",
                                                          "data_through": "2026-12-21", "values": {"ret20": -0.004}}})
    return led, review(derive(led), OBJ)


def case_revised():
    led, _ = case_matured()
    append(led, {"kind": "input_revision", "object_ref": OBJ, "recorded_at": "2027-01-05T10:00:00+08:00",
                 "market_date": "2027-01-04", "payload": {"old_snapshot_sha256": "SYN-S1", "new_snapshot_sha256": "SYN-S1r",
                                                          "affected": ["SYN|seg1|n60|2026-11-03"],
                                                          "change": "2026-11-03 low revised 3.912->3.905; touch still exists; ret20 unchanged (sensitivity stored separately)"}})
    return led, review(derive(led), OBJ)


def case_new_definition():
    led, _ = case_matured()
    append(led, {"kind": "definition_version", "object_ref": OBJ, "recorded_at": "2027-01-10T09:00:00+08:00",
                 "market_date": "2027-01-08", "payload": {"old": OBJ, "new": OBJ2, "reason": "synthetic: touch rule wording changed"}})
    append(led, {"kind": "protocol_frozen", "object_ref": OBJ2, "recorded_at": "2027-01-10T09:05:00+08:00",
                 "market_date": "2027-01-08", "payload": {**FROZEN, "observe_after": "2027-01-08", "protocol_sha256": "SYNTHETIC-v1.1"}})
    state = derive(led)
    return led, {"old": review(state, OBJ), "new": review(state, OBJ2),
                 "old_stream": state["streams"][OBJ], "new_stream": state["streams"][OBJ2]}


def case_budget_pause():
    led = base()
    append(led, {"kind": "pause", "object_ref": OBJ, "recorded_at": "2026-11-15T12:00:00+08:00",
                 "market_date": "2026-11-14", "payload": {"reason": "observation budget exhausted",
                                                          "resume_point": {"last_snapshot": "SYN-S1", "data_through": "2026-11-03",
                                                                           "open_opportunities": ["SYN|seg1|n60|2026-11-03"]}}})
    state = derive(led)
    return led, {"review": review(state, OBJ), "stream": state["streams"][OBJ], "paused": state["paused"]}


EXPECTED = {
    "S1_waiting_outcome": {"verdict": "insufficient_no_comparison", "waiting": 1, "matured_first": 0},
    "S2_outcome_matured": {"verdict": "describe_only", "matured_first": 1, "matured_later": 1,
                           "first_mean": 0.012, "later_mean": -0.004},
    "S3_input_revised": {"verdict": "describe_only", "revised_count": 1, "first_mean": 0.012},
    "S4_definition_new_version": {"old_status": "closed_superseded", "old_matured": 2,
                                  "new_status": "observing", "new_matured": 0},
    "S5_budget_interrupted": {"stream_status": "paused", "paused": True, "waiting": 1},
}


def main() -> int:
    results, fails = {}, []
    for name, fn in (("S1_waiting_outcome", case_waiting), ("S2_outcome_matured", case_matured),
                     ("S3_input_revised", case_revised), ("S4_definition_new_version", case_new_definition),
                     ("S5_budget_interrupted", case_budget_pause)):
        led, out = fn()
        errs = validate(led)
        exp = EXPECTED[name]
        if name == "S4_definition_new_version":
            got = {"old_status": out["old_stream"]["status"], "old_matured": out["old"]["matured_first"] + out["old"]["matured_later"],
                   "new_status": out["new_stream"]["status"], "new_matured": out["new"]["matured_first"] + out["new"]["matured_later"]}
        elif name == "S5_budget_interrupted":
            got = {"stream_status": out["stream"]["status"], "paused": out["paused"], "waiting": out["review"]["waiting"]}
        else:
            got = {k: out[k] for k in exp}
        ok = got == exp and not errs
        results[name] = {"ledger_records": len(led), "validation_errors": errs, "derived": out,
                         "expected": exp, "matches_hand_answer": ok}
        (HERE / f"ledger-{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in led),
                                                   encoding="utf-8")
        if not ok:
            fails.append(name)
    # 负例：篡改一条记录、倒填一个冻结前的机会、提前写结果，均须被发现
    led, _ = case_matured()
    tampered = json.loads(json.dumps(led))
    tampered[4]["payload"]["values"]["ret20"] = 0.05
    backdated = base()
    append(backdated, {"kind": "opportunity", "object_ref": OBJ, "recorded_at": "2026-11-04T16:00:00+08:00",
                       "market_date": "2026-10-01", "payload": {"opp_id": "SYN|back", "first_touch": True,
                                                                "mature_date": "2026-10-30", "snapshot_sha256": "SYN-S1"}})
    early = base()
    append(early, {"kind": "outcome", "object_ref": OBJ, "recorded_at": "2026-11-20T16:00:00+08:00",
                   "market_date": "2026-11-20", "payload": {"opp_id": "SYN|seg1|n60|2026-11-03", "mature_date": "2026-12-02",
                                                            "data_through": "2026-11-20", "values": {"ret20": 0.01}}})
    negatives = {"tampered_outcome": validate(tampered), "backdated_opportunity": validate(backdated),
                 "outcome_before_maturity": validate(early)}
    for k, v in negatives.items():
        if not v:
            fails.append(f"negative {k} not detected")
    results["negative_checks"] = negatives
    results["_note"] = "全部为合成记录；协议指纹为占位符；未读取任何真实或未来行情。"
    (HERE / "drill-output.json").write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k, v in results.items():
        if isinstance(v, dict) and "matches_hand_answer" in v:
            print(k, v["matches_hand_answer"], v["validation_errors"])
    print("negatives:", {k: bool(v) for k, v in negatives.items()})
    print("FAILURES:", fails or "none")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
