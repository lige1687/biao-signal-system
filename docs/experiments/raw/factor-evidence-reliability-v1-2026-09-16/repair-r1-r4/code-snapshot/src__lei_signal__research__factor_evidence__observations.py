"""factor_evidence 观察表输入：B1 适配、日称日程推导与纯校验。

- ``parse_b1_observations_csv``：B1 run-02 ``observations.csv`` 的严格适配器
  ——CSV 布尔字符串 ``true``/``false``（小写）与标志列 ``True``/``False``
  逐字符串解析，拒绝任意真值转换；NaN/inf 数值拒绝；重复日期拒绝；
  ``in_comparison`` 与共同合法集合推导矛盾拒绝。
- ``build_schedule``：只读封存日历（TradingCalendar），按覆盖区间推导完整
  交易日序列与评价窗标记；日历覆盖不完整抛资料不足错误，不回退工作日。
- ``validate_observations``：纯函数校验（合成/测试入口），规范列
  symbol/session/state/main/aux/legal/legal_reason/e_date/x_date；非法数值、
  重复键、倒挂日期、合法性与理由矛盾一律拒绝；观察日键集必须与评价窗轴
  严格相等。真实 B1 数据不得靠合成入口绕过身份检查——真实路径必须走
  ``load_b1_observations``（先核六个固定输入哈希，再解析）。
"""
from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.research.factor_evidence.contract import (
    FIXED_INPUT_IDENTITY,
    FIXED_PARAMS,
    FactorEvidenceIncompleteError,
    verify_input_hashes,
)

B1_OBS_HEADER = [
    "session", "state", "e_date", "x_date", "main", "aux", "mature", "reason",
    "flag_state_known", "flag_main_legal", "flag_mature", "in_comparison",
    "primary_exclusion",
]

CANONICAL_COLUMNS = [
    "symbol", "session", "state", "main", "aux", "legal", "legal_reason",
    "e_date", "x_date",
]


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _strict_date(text, where: str) -> str:
    _require(isinstance(text, str) and len(text) == 10,
             f"{where} 日期必须是YYYY-MM-DD字符串（收到 {text!r}）")
    try:
        d = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{where} 日期乱码：{text!r}") from exc
    _require(text == d.isoformat(),
             f"{where} 日期格式必须严格YYYY-MM-DD：{text!r}")
    return text


def _parse_state_scalar(x):
    """state 统一：真布尔或缺失；NaN 视为缺失（未知）；其余一律拒绝。"""
    if x is None or x is pd.NA:
        return None
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, float) and math.isnan(x):
        return None
    raise ValueError(f"state 只接受真布尔或缺失（收到 {x!r}，"
                     "字符串true/数字0/1/2都拒绝）")


def _parse_number_scalar(x, col: str):
    """main/aux 统一：缺失（None/NaN）或有限实数；inf/其他类型拒绝。

    CSV 文本 'nan'/'inf' 在适配器层已拒绝；内存 NaN 视为缺失（与 B1
    notna 口径一致），inf 不是缺失而是非法数值。
    """
    if x is None or x is pd.NA:
        return None
    if isinstance(x, (float, np.floating)) and math.isnan(x):
        return None
    if isinstance(x, bool) or not isinstance(x, (int, float, np.integer,
                                                 np.floating)):
        raise ValueError(f"{col} 只接受有限数值或缺失（收到 {x!r}）")
    v = float(x)
    _require(math.isfinite(v), f"{col} 非有限（inf 拒绝）：{x!r}")
    return v


# ── B1 CSV 适配器（严格） ────────────────────────────────────────────

def parse_b1_observations_csv(path) -> pd.DataFrame:
    """把 B1 observations.csv 解析为规范观察表；任何非法输入抛 ValueError。"""
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        _require(header == B1_OBS_HEADER, f"observations.csv 列头错误：{header!r}")
        raw = list(reader)
    _require(raw, "observations.csv 为空")
    rows: list[dict] = []
    sessions: list[str] = []
    for i, r in enumerate(raw):
        _require(len(r) == 13, f"observations.csv 第{i + 2}行字段数错误：{r!r}")
        rec = dict(zip(B1_OBS_HEADER, r, strict=True))
        session = _strict_date(rec["session"], f"第{i + 2}行 session")
        state_txt = rec["state"]
        _require(state_txt in ("true", "false", ""),
                 f"第{i + 2}行 state 只接受小写 true/false/空（收到 "
                 f"{state_txt!r}，不做任意真值转换）")
        state = {"true": True, "false": False, "": None}[state_txt]
        flags: dict[str, bool | None] = {}
        for flag in ("flag_state_known", "flag_main_legal", "flag_mature",
                     "in_comparison"):
            txt = rec[flag]
            _require(txt in ("True", "False", ""),
                     f"第{i + 2}行 {flag} 只接受 True/False/空（收到 {txt!r}）")
            flags[flag] = {"True": True, "False": False, "": None}[txt]
        main = (None if rec["main"] == "" else
                _require_number_text(rec["main"], "main", i + 2))
        aux = (None if rec["aux"] == "" else
               _require_number_text(rec["aux"], "aux", i + 2))
        e_date = None if rec["e_date"] == "" else _strict_date(
            rec["e_date"], f"第{i + 2}行 e_date")
        x_date = None if rec["x_date"] == "" else _strict_date(
            rec["x_date"], f"第{i + 2}行 x_date")
        # 共同合法集合 = 状态已知 ∧ 主目标合法 ∧ 成熟（缺标志按不满足计）
        legal = bool(flags["flag_state_known"] is True
                     and flags["flag_main_legal"] is True
                     and flags["flag_mature"] is True)
        _require((flags["in_comparison"] is True) == legal,
                 f"第{i + 2}行 in_comparison 与共同合法集合推导矛盾"
                 f"（in_comparison={rec['in_comparison']!r}，推导 legal={legal}）")
        if legal:
            legal_reason = None
        else:
            missing = [k for k in ("flag_state_known", "flag_main_legal",
                                   "flag_mature") if flags[k] is not True]
            legal_reason = (rec["primary_exclusion"] or rec["reason"]
                            or ("flag_missing:" + ",".join(missing) if missing
                                else "unknown_exclusion"))
        rows.append({
            "symbol": "510300", "session": session, "state": state,
            "main": main, "aux": aux, "legal": legal,
            "legal_reason": legal_reason, "e_date": e_date, "x_date": x_date,
        })
        sessions.append(session)
    _require(len(set(sessions)) == len(sessions), "observations.csv session 重复")
    return pd.DataFrame(rows, columns=CANONICAL_COLUMNS)


def _require_number_text(text: str, col: str, lineno: int) -> float:
    try:
        v = float(text)
    except ValueError as exc:
        raise ValueError(
            f"第{lineno}行 {col} 数值乱码（不用coerce变缺失）：{text!r}") from exc
    _require(math.isfinite(v), f"第{lineno}行 {col} 非有限（NaN/inf 拒绝）：{text!r}")
    return v


# ── 日程推导（只读封存日历） ────────────────────────────────────────

def build_schedule(calendar_path, window_start: str, window_end: str,
                   coverage_start: str, coverage_end: str) -> pd.DataFrame:
    """从封存日历推导交易日日程；返回列 session/in_window。

    只用 TradingCalendar 读取已封存日历；覆盖不完整/无交易日抛
    FactorEvidenceIncompleteError（明确 not_estimable，不回退工作日近似）。
    """
    from lei_signal.research.trading_calendar import TradingCalendar

    cal = TradingCalendar.from_file(Path(calendar_path))
    cov = cal.coverage(coverage_start, coverage_end)
    if not cov.complete:
        raise FactorEvidenceIncompleteError(
            f"日历覆盖不完整：缺月份 {list(cov.missing_months)}、"
            f"逐日不完整 {list(cov.day_incomplete_months)}"
            "（不完整时明确 not_estimable，不回退工作日近似）")
    days = list(cal.trading_days(coverage_start, coverage_end))
    if not days:
        raise FactorEvidenceIncompleteError(
            f"覆盖区间没有任何交易日：{coverage_start}..{coverage_end}")
    return pd.DataFrame({
        "session": days,
        "in_window": [window_start <= d <= window_end for d in days],
    })


# ── 纯校验（合成/测试入口） ─────────────────────────────────────────

def _check_schedule(schedule: pd.DataFrame) -> list[str]:
    _require(isinstance(schedule, pd.DataFrame)
             and list(schedule.columns) == ["session", "in_window"],
             "schedule 需要 session/in_window 两列")
    days = [_strict_date(d, "schedule.session") for d in schedule["session"]]
    _require(len(set(days)) == len(days), "schedule.session 重复")
    _require(days == sorted(days), "schedule.session 必须升序")
    iw = schedule["in_window"].tolist()
    _require(all(isinstance(v, (bool, np.bool_)) for v in iw),
             "schedule.in_window 必须为布尔")
    return days


def validate_observations(frame, schedule) -> tuple[pd.DataFrame, dict]:
    """规范观察表纯校验；返回 (规范化frame, audit)。非法输入抛异常。"""
    _require(isinstance(frame, pd.DataFrame), "frame 必须是 DataFrame")
    _require(list(frame.columns) == CANONICAL_COLUMNS,
             f"规范列必须为 {CANONICAL_COLUMNS}（收到 {list(frame.columns)}）")
    days = _check_schedule(schedule)
    pos = {d: i for i, d in enumerate(days)}
    window_days = [d for d, w in zip(days, schedule["in_window"].tolist(),
                                     strict=True) if w]
    window_set = set(window_days)

    n = len(frame)
    symbols = frame["symbol"].tolist()
    _require(all(isinstance(s, str) and s for s in symbols),
             "symbol 必须是非空字符串")
    distinct_symbols = sorted(set(symbols))
    _require(len(distinct_symbols) == 1,
             f"首版只支持单标的，多标的输入明确拒绝"
             f"（收到 {distinct_symbols}）；不做隐式合并")
    sessions = [_strict_date(s, "frame.session") for s in frame["session"]]
    _require(len(set(sessions)) == len(sessions), "frame.session 重复")
    _require(sessions == sorted(sessions), "frame.session 必须升序")

    states, mains, auxs = [], [], []
    legals, reasons = [], []
    e_dates, x_dates = [], []
    for i in range(n):
        states.append(_parse_state_scalar(frame["state"].iat[i]))
        mains.append(_parse_number_scalar(frame["main"].iat[i], "main"))
        auxs.append(_parse_number_scalar(frame["aux"].iat[i], "aux"))
        lv = frame["legal"].iat[i]
        _require(isinstance(lv, (bool, np.bool_)),
                 f"legal 必须为布尔（第{i + 1}行收到 {lv!r}，0/1 拒绝）")
        legals.append(bool(lv))
        rv = frame["legal_reason"].iat[i]
        _require(rv is None or (isinstance(rv, str) and rv),
                 f"legal_reason 只接受 None 或非空字符串（第{i + 1}行 {rv!r}）")
        reasons.append(rv)
        e = frame["e_date"].iat[i]
        x = frame["x_date"].iat[i]
        e_dates.append(None if e is None else _strict_date(e, "e_date"))
        x_dates.append(None if x is None else _strict_date(x, "x_date"))

    for i in range(n):
        # 合法性与理由 / 目标的一致性
        if legals[i]:
            _require(reasons[i] is None,
                     f"第{i + 1}行合法但 legal_reason 非空（合法行理由必须为空）")
            _require(states[i] is not None,
                     f"第{i + 1}行合法但 state 缺失（合法性矛盾）")
            _require(mains[i] is not None,
                     f"第{i + 1}行合法但 main 缺失（合法性矛盾）")
            _require(e_dates[i] is not None and x_dates[i] is not None,
                     f"第{i + 1}行合法但 e_date/x_date 缺失")
        else:
            _require(reasons[i] is not None,
                     f"第{i + 1}行非法但 legal_reason 为空（合法缺失必须有原因）")
        if e_dates[i] is not None:
            _require(e_dates[i] in pos,
                     f"第{i + 1}行 e_date 不在交易日日程内：{e_dates[i]}")
        if x_dates[i] is not None:
            _require(x_dates[i] in pos,
                     f"第{i + 1}行 x_date 不在交易日日程内：{x_dates[i]}")
        if e_dates[i] is not None and x_dates[i] is not None:
            _require(pos[sessions[i]] < pos[e_dates[i]] < pos[x_dates[i]],
                     f"第{i + 1}行日期倒挂：session < e_date < x_date 必须"
                     f"（{sessions[i]} < {e_dates[i]} < {x_dates[i]}）")
        elif x_dates[i] is not None and e_dates[i] is None:
            _require(False, f"第{i + 1}行 x_date 存在但 e_date 缺失")

    # 观察日键集与评价窗轴严格相等（先报缺，再报多）
    frame_set = set(sessions)
    missing = [d for d in window_days if d not in frame_set]
    if missing:
        raise FactorEvidenceIncompleteError(
            f"观察表缺评价窗交易日（先列5）：{missing[:5]}"
            "——键集严格相等，不靠行数")
    extra = [d for d in sessions if d not in window_set]
    _require(not extra, f"观察表含窗外/多余日期（先列5）：{extra[:5]}")

    normalized = pd.DataFrame({
        "symbol": symbols, "session": sessions, "state": states,
        "main": mains, "aux": auxs, "legal": legals,
        "legal_reason": reasons, "e_date": e_dates, "x_date": x_dates,
    }, columns=CANONICAL_COLUMNS)
    legal_rows = [i for i in range(n) if legals[i]]
    counts = {
        "rows": n,
        "legal": len(legal_rows),
        "illegal": n - len(legal_rows),
        "legal_true": sum(1 for i in legal_rows if states[i] is True),
        "legal_false": sum(1 for i in legal_rows if states[i] is False),
        "legal_unknown_state": sum(1 for i in legal_rows
                                   if states[i] is None),
        "aux_missing_in_legal": sum(1 for i in legal_rows if auxs[i] is None),
    }
    audit = {
        "counts": counts,
        "first_session": sessions[0] if sessions else None,
        "last_session": sessions[-1] if sessions else None,
        "window_axis_n": len(window_days),
        "sessions_equal_axis": sessions == window_days,
    }
    return normalized, audit


# ── 真实 B1 装载（先身份后解析，无 synthetic 旁路） ─────────────────

def load_b1_observations(root, contract: dict):
    """核验固定输入身份后装载 B1 观察表；返回 (frame, schedule, audit)。

    恒做六项输入哈希核验（错身份在计算前拒绝）；真实数据没有 synthetic
    参数或跳过资格选项。
    """
    from pathlib import Path as _P

    repo = _P(root)
    ident = contract.get("input_identity") or {}
    hashes = verify_input_hashes(repo, ident)
    fp = contract.get("fixed_params") or FIXED_PARAMS
    window = fp["evaluation_window"]
    coverage = fp["schedule_coverage"]
    calendar_path = (repo / FIXED_INPUT_IDENTITY["base_dir"]
                     / FIXED_INPUT_IDENTITY["calendar_json_path"])
    schedule = build_schedule(
        calendar_path, window["start"], window["end"],
        coverage["start"], coverage["end"])
    axis_days = schedule.loc[schedule["in_window"], "session"].tolist()
    obs_path = (repo / FIXED_INPUT_IDENTITY["base_dir"]
                / FIXED_INPUT_IDENTITY["observations_csv_path"])
    frame = parse_b1_observations_csv(obs_path)
    frame_sessions = frame["session"].tolist()
    missing = [d for d in axis_days if d not in set(frame_sessions)]
    if missing:
        raise FactorEvidenceIncompleteError(
            f"观察表缺评价窗交易日（先列5）：{missing[:5]}")
    extra = [d for d in frame_sessions if d not in set(axis_days)]
    _require(not extra, f"观察表含窗外/多余日期（先列5）：{extra[:5]}")
    frame, v_audit = validate_observations(frame, schedule)
    audit = {
        "hashes_verified": len(hashes),
        "hashes": hashes,
        "calendar_complete": True,
        "calendar": str(calendar_path),
        "axis_n": len(axis_days),
        "sessions_equal_axis": frame_sessions == axis_days,
        "window": dict(window),
        "schedule_coverage": {"start": coverage["start"],
                              "end": coverage["end"]},
        **v_audit,
    }
    return frame, schedule, audit
