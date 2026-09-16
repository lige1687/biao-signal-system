"""factor_evidence contract/observations 测试：协议绑定 + 观察表严格校验。

合法合成输入只用于单元测试内部；正式 CLI 只接受经 validate_protocol 绑定到
模块常量的冻结协议。真实 B1 数据没有 synthetic 旁路：load_b1_observations
恒做固定输入身份核验（错哈希在计算前拒绝）。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from lei_signal.research.factor_evidence.contract import (
    CARD,
    FIXED_INPUT_IDENTITY,
    FIXED_NO_CLAIMS,
    FIXED_PARAMS,
    FIXED_TOLERANCE,
    FIXED_USE,
    IDENTITY,
    OBJECT_REF,
    REQUIRED_CODE_KEYS,
    REQUIRED_OUTPUT_FIELDS,
    REQUIRED_STANDARDS,
    SPEC_VERSION,
    TASK_BOOK,
    FactorEvidenceIncompleteError,
    validate_protocol,
)
from lei_signal.research.factor_evidence.observations import (
    B1_OBS_HEADER,
    build_schedule,
    load_b1_observations,
    parse_b1_observations_csv,
    validate_observations,
)

REPO = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
B1_BASE = REPO / FIXED_INPUT_IDENTITY["base_dir"]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _protocol(**over):
    p = {
        "identity": IDENTITY,
        "spec_status": "frozen",
        "spec_version": SPEC_VERSION,
        "object_ref": OBJECT_REF,
        "use": FIXED_USE,
        "fixed_params": json.loads(json.dumps(FIXED_PARAMS)),
        "standards": [{"path": path, "version": version, "sha256": sha}
                      for path, version, sha in REQUIRED_STANDARDS],
        "task_book": dict(TASK_BOOK),
        "candidate_card": dict(CARD),
        "input_identity": dict(FIXED_INPUT_IDENTITY),
        "code_identity": {rel: _sha(REPO / rel) for rel in REQUIRED_CODE_KEYS},
        "tolerance": dict(FIXED_TOLERANCE),
        "output_fields": list(REQUIRED_OUTPUT_FIELDS),
        "no_claims": list(FIXED_NO_CLAIMS),
        "approval": None,
    }
    p.update(over)
    return p


def _write_protocol(tmp: Path, proto: dict, name: str | None = None) -> Path:
    p = tmp / (name or f"protocol-v{SPEC_VERSION}.json")
    p.write_text(json.dumps(proto, ensure_ascii=False), encoding="utf-8")
    return p


# ── 协议校验 ─────────────────────────────────────────────────────────

def test_valid_frozen_protocol_passes(tmp_path):
    contract = validate_protocol(_write_protocol(tmp_path, _protocol()), REPO)
    assert contract["input_identity"] == FIXED_INPUT_IDENTITY
    assert contract["fixed_params"] == FIXED_PARAMS


def test_draft_and_current_entry_rejected(tmp_path):
    with pytest.raises(ValueError, match="冻结|frozen|草案"):
        validate_protocol(_write_protocol(
            tmp_path, _protocol(spec_status="draft")), REPO)
    p = _write_protocol(tmp_path, _protocol(), name="current.json")
    with pytest.raises(ValueError, match="文件名"):
        validate_protocol(p, REPO)


def test_fake_version_rejected(tmp_path):
    sub = tmp_path / "v"
    sub.mkdir()
    with pytest.raises(ValueError, match="spec_version"):
        validate_protocol(_write_protocol(
            sub, _protocol(spec_version="9.9.9"),
            name="protocol-v9.9.9.json"), REPO)


def test_self_granted_approval_rejected(tmp_path):
    with pytest.raises(ValueError, match="approval"):
        validate_protocol(_write_protocol(tmp_path, _protocol(approval=True)), REPO)


def test_wrong_identity_rejected(tmp_path):
    proto = _protocol()
    proto["identity"] = "factor-evidence-reliability@1.0.1"
    with pytest.raises(ValueError, match="identity"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)


def test_object_ref_and_use_bound(tmp_path):
    # 主控R1反例：顶层对象/用途改任意值必须拒绝（身份承载字段逐值绑定）
    proto = _protocol(object_ref="wrong.object@9")
    with pytest.raises(ValueError, match="object_ref"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol(use="production")
    with pytest.raises(ValueError, match="use"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    del proto["object_ref"]
    with pytest.raises(ValueError, match="object_ref"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)


def test_fixed_params_cannot_change(tmp_path):
    for i, mutate in enumerate((
            lambda fp: fp.update(symbol="159915"),
            lambda fp: fp.update(resampling={**fp["resampling"], "reps": 9999}),
            lambda fp: fp["resampling"].update(seed=1),
            lambda fp: fp["resampling"]["quantiles"].update(lower=0.05),
            lambda fp: fp.update(evaluation_window={"start": "2020-01-01",
                                                    "end": "2025-12-31"}),
            lambda fp: fp.update(delta_definition="mean(false)-mean(true)"),
            lambda fp: fp["overlap"].update(sparse_step=22),
    )):
        proto = _protocol()
        mutate(proto["fixed_params"])
        sub = tmp_path / str(i)
        sub.mkdir()
        with pytest.raises(ValueError, match="逐值|不符"):
            validate_protocol(_write_protocol(sub, proto), REPO)


def test_standards_cannot_trim_or_drift(tmp_path):
    proto = _protocol()
    proto["standards"] = []
    with pytest.raises(ValueError, match="standards"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["standards"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="指纹"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["standards"].append({"path": "docs/extra.md", "version": "1",
                               "sha256": "0" * 64})
    with pytest.raises(ValueError, match="裁剪|扩项"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)


def test_code_keys_cannot_trim_or_extend(tmp_path):
    proto = _protocol()
    del proto["code_identity"][REQUIRED_CODE_KEYS[0]]
    with pytest.raises(ValueError, match="裁剪|必需代码键"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["code_identity"]["extra/file.py"] = "0" * 64
    with pytest.raises(ValueError, match="未登记键"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    first = REQUIRED_CODE_KEYS[0]
    proto["code_identity"][first] = "0" * 64
    with pytest.raises(ValueError, match="哈希|漂移"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)


def test_loose_tolerance_rejected(tmp_path):
    proto = _protocol()
    proto["tolerance"] = {"float": 1, "counts_keys_nulls": "严格一致"}
    with pytest.raises(ValueError, match="tolerance"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["tolerance"] = {"float": 1e-12}
    with pytest.raises(ValueError, match="tolerance"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)


def test_input_identity_cannot_change(tmp_path):
    proto = _protocol()
    proto["input_identity"]["observations_csv_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="input_identity"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)


def test_task_book_and_card_read_from_disk(tmp_path):
    proto = _protocol()
    proto["task_book"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="task_book"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)
    proto = _protocol()
    proto["candidate_card"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="candidate_card"):
        validate_protocol(_write_protocol(tmp_path, proto), REPO)


# ── 观察表：CSV 适配与纯校验 ────────────────────────────────────────

N_WINDOW = 40
N_TAIL = 30
DAYS = [d.strftime("%Y-%m-%d")
        for d in pd.bdate_range("2019-10-08", periods=N_WINDOW + N_TAIL)]


def _sched() -> pd.DataFrame:
    return pd.DataFrame({
        "session": DAYS,
        "in_window": [i < N_WINDOW for i in range(len(DAYS))],
    })


def _frame(states, mains, **over):
    n = len(states)
    base = {
        "symbol": ["510300"] * n,
        "session": DAYS[:n],
        "state": list(states),
        "main": list(mains),
        "aux": [0.0] * n,
        "legal": [True] * n,
        "legal_reason": [None] * n,
        "e_date": DAYS[1:n + 1],
        "x_date": DAYS[22:22 + n],
    }
    base.update(over)
    return pd.DataFrame(base)


def test_validate_observations_positive_and_unknown_state():
    frame, audit = validate_observations(
        _frame([True, False] * 20, [0.1] * 40), _sched())
    assert len(frame) == 40
    assert audit["counts"]["rows"] == 40
    assert audit["counts"]["legal"] == 40
    assert audit["counts"]["legal_true"] == 20
    assert audit["counts"]["legal_false"] == 20


def test_state_rejects_non_boolean_and_loose_strings():
    for bad in (1, 0, 2, "true", "True", "yes", 1.5, "F"):
        with pytest.raises(ValueError, match="state|布尔"):
            validate_observations(_frame([bad, False] + [True] * 38,
                                         [0.1] * 40), _sched())


def test_nan_state_is_unknown_not_error():
    frame, audit = validate_observations(_frame([float("nan")] + [True] * 39,
                                                [0.1] * 40,
                                                legal=[False] + [True] * 39,
                                                legal_reason=["state_unknown"]
                                                + [None] * 39), _sched())
    assert frame.loc[0, "state"] is None
    assert audit["counts"]["illegal"] == 1


def test_main_aux_reject_inf_and_treat_nan_as_missing():
    # inf/-inf 是非法数值，必须拒绝
    for bad in (float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="有限|finite|inf"):
            validate_observations(_frame([True] * 39 + [False],
                                         [0.1] * 39 + [bad]), _sched())
    with pytest.raises(ValueError, match="有限|finite|inf"):
        validate_observations(_frame([True, False] + [True] * 38,
                                     [0.1] * 40,
                                     aux=[0.0, float("inf")] + [0.0] * 38),
                              _sched())
    # 内存 NaN 视为缺失：合法行上缺失目标 → 合法性矛盾（不静默接受）；
    # 非法行上缺失目标 → 合法保留原因
    with pytest.raises(ValueError, match="合法|legal|矛盾"):
        validate_observations(_frame([True] + [True] * 39,
                                     [float("nan")] + [0.1] * 39), _sched())
    f, audit = validate_observations(
        _frame([True] + [True] * 39, [None, 0.1] + [0.1] * 38,
               legal=[False, True] + [True] * 38,
               legal_reason=["target_missing", None] + [None] * 38), _sched())
    assert pd.isna(f.loc[0, "main"])
    assert audit["counts"]["illegal"] == 1


def test_duplicate_session_rejected():
    f = _frame([True, False] + [True] * 38, [0.1] * 40)
    f.loc[1, "session"] = f.loc[0, "session"]
    with pytest.raises(ValueError, match="重复"):
        validate_observations(f, _sched())


def test_inverted_dates_rejected():
    f = _frame([True] + [False] * 39, [0.1] * 40)
    f.loc[0, "e_date"], f.loc[0, "x_date"] = f.loc[0, "x_date"], f.loc[0, "e_date"]
    with pytest.raises(ValueError, match="倒挂|先后|e_date|x_date"):
        validate_observations(f, _sched())
    f = _frame([True] + [False] * 39, [0.1] * 40)
    f.loc[0, "e_date"] = f.loc[0, "session"]
    with pytest.raises(ValueError, match="倒挂|先后|e_date|x_date"):
        validate_observations(f, _sched())


def test_off_schedule_date_rejected():
    f = _frame([True] + [False] * 39, [0.1] * 40)
    f.loc[0, "x_date"] = "2019-10-12"  # 周六：不在合成交易日轴
    with pytest.raises(ValueError, match="日历|schedule|交易日"):
        validate_observations(f, _sched())


def test_missing_trading_day_incomplete():
    f = _frame([True, False], [0.1, 0.2])  # 只给 2 行，日程窗内 40 日
    with pytest.raises(FactorEvidenceIncompleteError, match="缺|漏|键集"):
        validate_observations(f, _sched())


def test_extra_window_outside_session_rejected():
    # 40 行窗内 + 1 行窗外（日程尾部、非评价窗）
    f = _frame([True] * 41, [0.1] * 41)
    f.loc[40, "session"] = DAYS[40]
    f.loc[40, "e_date"] = DAYS[41]
    f.loc[40, "x_date"] = DAYS[62]
    with pytest.raises(ValueError, match="窗外|键集|一致|evaluation"):
        validate_observations(f, _sched())


def test_legal_reason_contradictions_rejected():
    # legal=True 但 main 缺失
    f = _frame([True, False] + [True] * 38, [None] + [0.1] * 39)
    with pytest.raises(ValueError, match="合法|legal|矛盾"):
        validate_observations(f, _sched())
    # legal=True 但 legal_reason 非空
    f = _frame([True, False] + [True] * 38, [0.1] * 40,
               legal_reason=["why"] + [None] * 39)
    with pytest.raises(ValueError, match="合法|legal|矛盾|理由"):
        validate_observations(f, _sched())
    # legal=False 但没有理由
    f = _frame([True, False] + [True] * 38, [0.1] * 40,
               legal=[True, False] + [True] * 38,
               legal_reason=[None, None] + [None] * 38)
    with pytest.raises(ValueError, match="合法|legal|矛盾|理由"):
        validate_observations(f, _sched())


def test_illegal_rows_need_not_have_target():
    f = _frame([True, None] + [True] * 38, [0.1, None] + [0.1] * 38,
               legal=[True, False] + [True] * 38,
               legal_reason=[None, "state_unknown"] + [None] * 38)
    _, audit = validate_observations(f, _sched())
    assert audit["counts"]["legal"] == 39
    assert audit["counts"]["illegal"] == 1


def test_parse_b1_csv_strict_bool_strings(tmp_path):
    good = ("session,state,e_date,x_date,main,aux,mature,reason,"
            "flag_state_known,flag_main_legal,flag_mature,in_comparison,"
            "primary_exclusion\n"
            "2019-10-08,false,2019-10-09,2019-11-07,0.04,0.0,True,,"
            "True,True,True,True,\n"
            "2019-10-09,true,2019-10-10,2019-11-08,-0.02,-0.03,True,,"
            "True,True,True,True,\n")

    def _csv(text):
        p = tmp_path / "observations.csv"
        p.write_text(text, encoding="utf-8")
        return p

    frame = parse_b1_observations_csv(_csv(good))
    assert list(frame["state"]) == [False, True]
    assert list(frame["legal"]) == [True, True]
    assert frame.loc[0, "symbol"] == "510300"
    # state 大小写/未知字符串拒绝（不做任意真值转换）
    for bad_state in ("True", "TRUE", "yes", "1", "0"):
        row = good.splitlines()
        row[1] = row[1].replace(",false,", f",{bad_state},")
        with pytest.raises(ValueError, match="state"):
            parse_b1_observations_csv(_csv("\n".join(row) + "\n"))
    # NaN/inf 数值拒绝
    row = good.splitlines()
    row[1] = row[1].replace("0.04", "nan")
    with pytest.raises(ValueError, match="有限|nan"):
        parse_b1_observations_csv(_csv("\n".join(row) + "\n"))
    row = good.splitlines()
    row[2] = row[2].replace("-0.02", "inf")
    with pytest.raises(ValueError, match="有限|inf"):
        parse_b1_observations_csv(_csv("\n".join(row) + "\n"))
    # 表头不符拒绝
    with pytest.raises(ValueError, match="列头|header"):
        parse_b1_observations_csv(_csv(good.replace("primary_exclusion",
                                                    "primary_excl")))
    # in_comparison 与共同合法集合矛盾拒绝
    row = good.splitlines()
    row[2] = row[2].replace("True,True,True,True,", "True,True,False,True,")
    with pytest.raises(ValueError, match="in_comparison|矛盾"):
        parse_b1_observations_csv(_csv("\n".join(row) + "\n"))
    # 重复日期拒绝
    row = good.splitlines()
    row[2] = row[2].replace("2019-10-09,true", "2019-10-08,true")
    with pytest.raises(ValueError, match="重复"):
        parse_b1_observations_csv(_csv("\n".join(row) + "\n"))


def test_parse_b1_csv_unknown_state_row(tmp_path):
    header = ",".join(B1_OBS_HEADER)
    line_unknown = ("2019-10-08,,2019-10-09,2019-11-07,0.04,0.0,True,"
                    "warmup,,True,False,False,")
    p = tmp_path / "observations.csv"
    p.write_text(header + "\n" + line_unknown + "\n", encoding="utf-8")
    frame = parse_b1_observations_csv(p)
    assert frame.loc[0, "state"] is None
    assert bool(frame.loc[0, "legal"]) is False
    assert frame.loc[0, "legal_reason"]


def test_build_schedule_incomplete_calendar_raises(tmp_path):
    # 月份覆盖不完整的日历 → 资料不足（非身份错误）
    cal = {
        "schema_version": "test", "authority": "test", "publisher": "test",
        "months_requested": ["2019-10"], "months_failed": [], "days": {},
    }
    p = tmp_path / "calendar.json"
    p.write_text(json.dumps(cal), encoding="utf-8")
    with pytest.raises(FactorEvidenceIncompleteError, match="完整|覆盖"):
        build_schedule(p, "2019-10-08", "2019-11-01",
                       "2019-10-01", "2019-11-30")


# ── 真实 B1 输入身份核验（无 synthetic 旁路） ───────────────────────

def _real_contract() -> dict:
    return {
        "identity": IDENTITY,
        "fixed_params": json.loads(json.dumps(FIXED_PARAMS)),
        "input_identity": dict(FIXED_INPUT_IDENTITY),
    }


def test_load_real_b1_observations_matches_independent_expectations():
    frame, schedule, audit = load_b1_observations(REPO, _real_contract())
    assert audit["axis_n"] == 1516
    assert len(frame) == 1516
    assert audit["hashes_verified"] == 6
    counts = audit["counts"]
    assert counts["legal"] == 1516 and counts["illegal"] == 0
    assert counts["legal_true"] == 590 and counts["legal_false"] == 926
    # 独立期望（stdlib 脚本推导，见 raw/expectations.json）
    delta = (frame.loc[frame["state"] == True, "main"].mean()  # noqa: E712
             - frame.loc[frame["state"] == False, "main"].mean())  # noqa: E712
    assert delta == pytest.approx(0.007015924582548178, abs=1e-12)
    assert int(schedule["in_window"].sum()) == 1516
    assert audit["calendar_complete"] is True
    assert audit["sessions_equal_axis"] is True


def test_load_rejects_wrong_hash_before_any_computation(tmp_path):
    # 复制真实观察表到 tmp 并篡改一行数值：固定身份核验必须先拒绝
    dst_base = tmp_path / "b1copy"
    (dst_base / "run-02").mkdir(parents=True)
    src = B1_BASE / FIXED_INPUT_IDENTITY["observations_csv_path"]
    text = src.read_text(encoding="utf-8")
    (dst_base / "run-02/observations.csv").write_text(
        text.replace("0.04325775656324593", "0.05"), encoding="utf-8")
    with pytest.raises(ValueError, match="哈希|sha256|身份"):
        load_b1_observations(tmp_path, {**_real_contract(),
                                        "input_identity": {
                                            **FIXED_INPUT_IDENTITY,
                                            "base_dir": "b1copy"}})
