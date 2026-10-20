#!/usr/bin/env python3
"""已有动量指标研究样板的离线编排（momentum-research-prototype-2026-09-13）。

三种模式互不冒充：

- ``synthetic``：合成夹具（synthetic=true）完整跑通经济指数重建、动量、
  未来观察目标与排序诊断；不伪装交易所数据，不代表真实资料准入；
- ``historical-diagnostic``：真实冻结输入只做被允许的历史数值重建诊断；
  不写 targets/rank 结果，以 ``skipped-stages.json`` 记录未运行阶段；
- ``qualified-research``：仅当排序与研究信号两种用途均获允许、对象与来源
  通过、日历合格等全部条件满足才运行；条件不足输出拒绝报告（退出 2）。

退出码：0 模式完整完成；2 质量限制导致研究拒绝（有价值的检查结果）；
3 参数/输入/运行失败。输出不含金额/交易/账户；无资金账户计算，
policy 一律 ``not_applicable_no_account_policy``。

完全离线：启动即装断网守卫并自证拦截（守卫拒绝一次本地连接自检），
然后才运行。manifest 最后写出——仅完整写出有效 manifest 才算完成；
写盘失败时保留 FAILED.txt，部分产物不构成完成证明。
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

from lei_signal.research import momentum_prototype as mp  # noqa: E402

EXIT_OK = 0
EXIT_REJECTED = 2
EXIT_FAILED = 3

MODES = ("synthetic", "historical-diagnostic", "qualified-research")
REAL_MODES = ("historical-diagnostic", "qualified-research")

REQUIRED_PROTOCOL_KEYS = (
    "protocol_id", "target_id", "target_parameters", "objects", "codes",
    "inputs", "specs", "formula", "time_semantics", "modes", "tolerance",
)
REQUIRED_CODE_KEYS = frozenset({
    "definitions", "factor_runtime", "momentum_prototype", "data_quality",
    "data_snapshot", "trading_calendar", "symbol_identity",
    "run_momentum_research_prototype",
})
REQUIRED_INPUT_KEYS = (
    "snapshot_dir", "calendar", "publication", "actions",
    "evaluation_start", "evaluation_end",
)
USES_CHECKED = ("description", "ranking", "research_signal")

MOMENTUM_WARMUP = 253  # 首次需要 253 条有效报价（协议 §1.2）


class _Parser(argparse.ArgumentParser):
    """参数错误属输入错误（退出 3），不与"正常研究被拒"(2) 混淆。"""

    def error(self, message):  # noqa: D102
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(EXIT_FAILED)


class InputError(RuntimeError):
    """参数/协议/输入身份类失败：退出 3，不留下任何产物目录。"""


class _OfflineGuard:
    """断网守卫：先自证能拦截，再允许运行；不发起真实网络请求。"""

    def __init__(self) -> None:
        self.self_check: dict | None = None
        self._orig: tuple | None = None

    def install(self) -> None:
        def _blocked(*_a, **_k):
            raise RuntimeError("离线守卫：本次研究运行禁用网络")

        self._orig = (socket.socket, socket.create_connection, socket.getaddrinfo)
        socket.socket = _blocked  # type: ignore[assignment]
        socket.create_connection = _blocked  # type: ignore[assignment]
        socket.getaddrinfo = _blocked  # type: ignore[assignment]
        # 自证：任何连接尝试都必须被守卫拒绝（目标地址不可达也到不了）。
        try:
            socket.create_connection(("127.0.0.1", 1), timeout=0.2)
        except Exception as exc:  # noqa: BLE001 - 被拦截即预期
            self.self_check = {
                "self_check_blocked": True,
                "blocked_with": type(exc).__name__,
            }
        else:
            self.restore()
            raise InputError("断网守卫自检失败：连接未被拦截，拒绝运行")

    def restore(self) -> None:
        if self._orig is not None:
            socket.socket, socket.create_connection, socket.getaddrinfo = self._orig
            self._orig = None


# ---------------------------------------------------------------------------
# 协议与输入核验
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_protocol(path: Path) -> tuple[dict, str]:
    if not path.is_file():
        raise InputError(f"协议文件不存在：{path}")
    try:
        protocol = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"协议文件不可读或不是合法 JSON：{exc}") from exc
    if not isinstance(protocol, dict):
        raise InputError("协议 JSON 顶层必须是对象")
    missing = [k for k in REQUIRED_PROTOCOL_KEYS if k not in protocol]
    if missing:
        raise InputError(f"协议缺少必需字段：{missing}")
    return protocol, _sha256_file(path)


def _verify_protocol_codes(protocol: dict) -> None:
    """冻结协议记录的代码指纹必须与当前文件一致，防止漂移代码冒充已冻结算法。

    必需代码键固定（含本 CLI 自身——它决定身份挂接、观察日、模式与资格）：
    删键不能免核；缺失或哈希漂移一律拒绝。
    """
    missing_keys = REQUIRED_CODE_KEYS - set(protocol["codes"])
    if missing_keys:
        raise InputError(
            f"协议 codes 缺少必需代码键 {sorted(missing_keys)}；删键不能免核"
        )
    drifted = []
    for key, entry in protocol["codes"].items():
        p = ROOT / entry["path"]
        if not p.exists():
            drifted.append(f"{key}: 文件不存在 {entry['path']}")
        elif _sha256_file(p) != entry["sha256"]:
            drifted.append(f"{key}: {entry['path']}")
    if drifted:
        raise InputError(
            "代码指纹与冻结协议不一致（需新协议版本并记录影响，不得带漂移运行）："
            + "; ".join(drifted)
        )


# 本任务只支持固定两个对象、一个目标与固定窗口参数；任何不支持或相互矛盾
# 的协议声明都是输入错误，不得产出"已完成"产物（返修 B）。
SUPPORTED_TARGET_PARAMS = {
    "next_session_offset": mp.NEXT_SESSION_OFFSET,
    "exit_session_offset": mp.EXIT_SESSION_OFFSET,
}
SUPPORTED_MOMENTUM_PARAMS = {"long_lag": 252, "skip_lag": 21}


def _verify_protocol_identity(protocol: dict) -> None:
    """把协议声明的身份、卡快照与参数绑定到实际算法与唯一登记表。"""
    if protocol["objects"]["primary"] != mp.MOMENTUM_REF:
        raise InputError(
            f"协议主对象 {protocol['objects']['primary']!r} 不是本实现支持的 "
            f"{mp.MOMENTUM_REF!r}；拒绝照抄未知身份产出完成假象"
        )
    if protocol["objects"].get("dependency") != mp.ECONOMIC_REF:
        raise InputError(
            f"协议依赖对象 {protocol['objects'].get('dependency')!r} 不是本实现"
            f"支持的 {mp.ECONOMIC_REF!r}"
        )
    if protocol["target_id"] != mp.TARGET_ID:
        raise InputError(
            f"协议目标 {protocol['target_id']!r} 不是本实现支持的 "
            f"{mp.TARGET_ID!r}（固定 e+21 交易日窗口）；拒绝按固定算法冒充"
            "未支持目标"
        )
    declared_target = protocol.get("target_parameters") or {}
    for key, value in SUPPORTED_TARGET_PARAMS.items():
        if declared_target.get(key) != value:
            raise InputError(
                f"协议目标参数 {key}={declared_target.get(key)!r} 与本实现支持的 "
                f"{value} 不一致"
            )
    # 卡快照必须与唯一登记表当前解析一致；动量参数必须与算法常量一致。
    from lei_signal.research import definitions as d

    reg_path = (protocol["specs"].get("registry") or {}).get("path")
    if not reg_path:
        raise InputError("协议 specs.registry 缺少 path")
    registry = d.load_registry(ROOT / reg_path)
    declared_version = (protocol["specs"].get("registry") or {}).get("version")
    if declared_version != registry.get("version"):
        raise InputError(
            f"协议声明的登记表容器版本 {declared_version!r} 与实际文件 "
            f"{registry.get('version')!r} 不一致"
        )
    cards = (protocol.get("objects") or {}).get("cards") or {}
    for ref in (mp.MOMENTUM_REF, mp.ECONOMIC_REF):
        entry = cards.get(ref)
        if not entry or "card" not in entry:
            raise InputError(f"协议缺少 {ref} 的完整卡快照")
        try:
            actual = d.resolve(registry, ref)
        except Exception as exc:  # noqa: BLE001
            raise InputError(f"登记表解析 {ref} 失败：{exc}") from exc
        if entry["card"] != actual:
            raise InputError(
                f"协议 {ref} 卡快照与登记表实际解析不一致；协议过期或被改动"
            )
    params = (
        cards.get(mp.MOMENTUM_REF, {}).get("card", {}).get("definition", {})
        .get("parameters", {})
    )
    for key, value in SUPPORTED_MOMENTUM_PARAMS.items():
        if params.get(key) != value:
            raise InputError(
                f"协议动量参数 {key}={params.get(key)!r} 与本实现支持的 "
                f"{value} 不一致"
            )


def _verify_protocol_inputs(protocol: dict) -> dict:
    """核对协议冻结的输入位置与哈希；错源/被改动的输入不得进入计算。"""
    inputs = protocol["inputs"]
    missing = [k for k in REQUIRED_INPUT_KEYS if k not in inputs]
    if missing:
        raise InputError(f"协议 inputs 缺少字段：{missing}")
    checked: dict[str, dict] = {}
    path_keys = {
        "snapshot_dir": Path(inputs["snapshot_dir"]["path"]) / "snapshot.json",
        "calendar": Path(inputs["calendar"]["path"]),
        "publication": Path(inputs["publication"]["path"]),
        "actions": Path(inputs["actions"]["path"]),
    }
    for key, p in path_keys.items():
        if not p.exists():
            raise InputError(f"协议冻结输入不存在：{key} -> {p}")
        actual = _sha256_file(p)
        declared = inputs.get(key, {}).get("sha256")
        if declared and actual != declared:
            raise InputError(
                f"协议冻结输入哈希不一致：{key} -> {p}（声明 {declared[:12]}…，"
                f"实际 {actual[:12]}…）；拒绝使用被改动的输入"
            )
        # snapshot_dir 的 path 保持协议原值（目录）；核验的 snapshot.json 单列
        checked[key] = {"path": inputs[key]["path"], "sha256": actual,
                        "verified_file": str(p)}
    registry_entry = protocol["specs"].get("registry") or {}
    reg_path = registry_entry.get("path")
    if not reg_path or not (ROOT / reg_path).exists():
        raise InputError(f"协议登记表路径缺失或不存在：{reg_path!r}")
    if registry_entry.get("sha256") and _sha256_file(ROOT / reg_path) != registry_entry["sha256"]:
        raise InputError("登记表哈希与冻结协议不一致")
    checked["registry"] = {"path": str(ROOT / reg_path), "sha256": _sha256_file(ROOT / reg_path)}
    return checked


def _verify_research_evidence(protocol: dict, input_paths: dict | None) -> dict | None:
    """可选 ``research_evidence`` 字段（Task 5）：存在即必须通过校验，
    省略时保持旧行为。相关模块键（qualification_bundle）同时成为必需。"""
    ref = protocol.get("research_evidence")
    if not ref:
        return None
    if "qualification_bundle" not in protocol.get("codes", {}):
        raise InputError(
            "启用 research_evidence 时协议 codes 必须包含 qualification_bundle 键")
    entry = protocol["codes"]["qualification_bundle"]
    qp = ROOT / entry["path"]
    if not qp.exists() or _sha256_file(qp) != entry["sha256"]:
        raise InputError(f"qualification_bundle 代码指纹与协议不一致：{entry['path']}")
    path = Path(ref["path"])
    if not path.is_file():
        raise InputError(f"research_evidence 文件不存在：{path}")
    if not ref.get("sha256") or _sha256_file(path) != ref["sha256"]:
        raise InputError("research_evidence 哈希与协议声明不一致")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    if bundle.get("synthetic") is not False:
        raise InputError("research_evidence 必须为真实证据包（synthetic=false）")
    from lei_signal.research.qualification_bundle import validate_evidence_bundle

    universe: set[str] = set()
    if input_paths:
        meta_path = Path(input_paths["snapshot_dir"]["path"]) / "snapshot.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        universe = {item["instrument_id"] for item in meta["instruments"]}
    result = validate_evidence_bundle(bundle, root=ROOT, universe=universe)
    if result["rejected"]:
        raise InputError(
            "research_evidence 存在被拒记录，不得绑定："
            + "; ".join(f"{r['record_id']}: {r['reasons'][0]}"
                        for r in result["rejected"][:10]))
    return {
        "path": ref["path"], "sha256": ref["sha256"],
        "validated": len(result["validated"]),
        "unresolved": len(result["unresolved"]),
        "conflicts": len(result["conflicts"]),
        "note": "证据包已通过任务级校验；不等于历史可得性已证明或预测资格已获准",
    }


# ---------------------------------------------------------------------------
# 合成夹具（synthetic=true；明确虚构，不伪装交易所数据）
# ---------------------------------------------------------------------------

SYNTH_START, SYNTH_END = "2024-01-02", "2025-02-28"
SYNTH_HOLIDAYS = {"2024-05-01", "2024-10-08"}


def synthetic_sessions() -> list[str]:
    """人工交易日历：工作日为交易日，扣除两个显式节假日；跨 14 个自然月。"""
    days = pd.bdate_range(SYNTH_START, SYNTH_END)
    days = [d for d in days if d.strftime("%Y-%m-%d") not in SYNTH_HOLIDAYS]
    return [d.strftime("%Y-%m-%d") for d in days]


def _synth_path(base: float, k: int) -> float:
    """确定性价格路径：缓涨叠加缓慢正弦，恒为正。"""
    return round(base * (1.0 + 0.0008 * k + 0.02 * np.sin(k / 7.0)), 4)


def build_synthetic_fixture() -> dict:
    """五个明确虚构产品与配套公司行动，覆盖协议要求的全部边界情形。"""
    sessions = synthetic_sessions()
    pos = {d: i for i, d in enumerate(sessions)}

    def path(name: str, base: float, *, splits: dict[str, float] | None = None,
             divs: dict[str, float] | None = None, drop: set[str] | None = None,
             start_after: str | None = None) -> tuple[pd.Series, list[dict]]:
        splits, divs, drop = splits or {}, divs or {}, drop or set()
        events: list[dict] = []
        for day, ratio in sorted(splits.items()):
            events.append({
                "event_id": f"{name}:split:{day}", "symbol": name, "type": "split",
                "effective_date": day, "ratio": ratio,
                "available_at": f"SYNTH-avail-{day}",  # 合成可得时间，不移植为真实时点证据
            })
        for day, cash in sorted(divs.items()):
            events.append({
                "event_id": f"{name}:cash_dividend:{day}", "symbol": name,
                "type": "cash_dividend", "effective_date": day, "cash": cash,
                "available_at": f"SYNTH-avail-{day}",
            })
        rows: dict[str, float] = {}
        cum_split, cum_div = 1.0, 0.0
        for d in sessions:
            if d < (start_after or "") or d in drop:
                continue
            k = pos[d]
            # 拆分后所有后续价格按比例缩减、分红后所有后续价格降低——
            # 只改事件当天的价格会制造次日假跳空，经济含义即被改变。
            cum_split *= splits.get(d, 1.0)
            cum_div += divs.get(d, 0.0)
            price = _synth_path(base, k) / cum_split - cum_div
            rows[d] = round(price, 4)
        idx = pd.DatetimeIndex([pd.Timestamp(d) for d in rows])
        return pd.Series(list(rows.values()), index=idx, name=name), events

    products: dict[str, dict] = {}
    notes: dict[str, str] = {}

    s, e = path("SYN.A", 100.0)
    products["SYN.A"] = {"close": s, "events": e}
    notes["SYN.A"] = "基准路径：无行动、无缺报价"

    # 月末缺报价：2024-11 最后一个交易日无报价（该月观察日缺失，不前填）
    nov_last = max(d for d in sessions if d.startswith("2024-11"))
    s, e = path("SYN.B", 110.0, divs={"2024-07-15": 2.0, "2024-11-14": 2.0},
                drop={nov_last})
    products["SYN.B"] = {"close": s, "events": e}
    notes["SYN.B"] = f"现金分红两次 + 月末缺报价（{nov_last}）"

    s, e = path("SYN.C", 80.0, splits={"2024-08-01": 2.0}, drop={"2024-09-10"})
    products["SYN.C"] = {"close": s, "events": e}
    notes["SYN.C"] = "1拆2 + 区间内缺报价（2024-09-10）"

    # 同日事件顺序：拆分与分红同日生效
    s, e = path("SYN.D", 60.0, splits={"2024-09-02": 2.0}, divs={"2024-09-02": 1.0})
    products["SYN.D"] = {"close": s, "events": e}
    notes["SYN.D"] = "同日拆分+分红（2024-09-02，事件顺序确定性由 event_id 排序决定）"

    s, e = path("SYN.E", 50.0, start_after="2024-07-01")
    products["SYN.E"] = {"close": s, "events": e}
    notes["SYN.E"] = "晚进场：有效报价不足 253 条，动量全程缺失（不足预热）"

    return {
        "sessions": sessions, "products": products, "notes": notes,
        "holidays": sorted(SYNTH_HOLIDAYS),
        "window": [SYNTH_START, SYNTH_END],
    }


def _month_last_sessions(sessions: list[str]) -> list[str]:
    """各完整月份的最后交易日（合成日历所有月份按构造完整）。"""
    last: dict[str, str] = {}
    for d in sessions:
        last[d[:7]] = d
    return [last[m] for m in sorted(last)]


# ---------------------------------------------------------------------------
# 共享流水线：经济指数 → 动量 → 未来目标 → 逐期排序诊断
# ---------------------------------------------------------------------------


def _price_for_product(product: dict) -> pd.Series:
    s = product["close"].astype(float)
    if not s.index.is_unique or not s.index.is_monotonic_increasing:
        raise InputError("产品报价日期必须唯一且递增")
    return s


def _momentum_stage(product_name: str, product: dict, sessions: list[str],
                    observations: list[str]) -> tuple[list[list], list[list], pd.Series | None,
                                                      list[str]]:
    """动量阶段：重建经济指数并取观察日动量值；返回 (values, missing, momentum, unknown)。"""
    close = _price_for_product(product)
    try:
        econ, unknown = mp.reconstruct_symbol_economic_index(
            close, product["events"]
        )
    except ValueError as exc:
        raise InputError(f"{product_name}: 经济指数重建失败：{exc}") from exc
    momentum = mp.compute_momentum(econ)
    valid_dates = {pd.Timestamp(d).normalize() for d in close.index}
    valid_count: dict[pd.Timestamp, int] = {
        pd.Timestamp(d).normalize(): k
        for k, d in enumerate(close.index, start=1)
    }

    values_rows: list[list] = []
    missing_rows: list[list] = []
    obj = mp.MOMENTUM_REF
    for day in observations:
        key = pd.Timestamp(day).normalize()
        if key not in valid_dates:
            missing_rows.append([obj, product_name, day, "momentum",
                                 "no_quote_at_observation"])
            continue
        val = momentum.get(key, np.nan)
        if not np.isfinite(val):
            reason = ("insufficient_warmup"
                      if valid_count.get(key, 0) < MOMENTUM_WARMUP
                      else "momentum_not_finite")
            missing_rows.append([obj, product_name, day, "momentum", reason])
        else:
            values_rows.append([obj, product_name, day, repr(float(val)), "fraction"])
    return values_rows, missing_rows, momentum, list(unknown)


def _targets_stage(product_name: str, product: dict, sessions: list[str],
                   observations: list[str]) -> list[list]:
    """未来目标阶段：对每个观察日计算 Y(t)=I(x)/I(e)-1。"""
    close = _price_for_product(product)
    econ, _ = mp.reconstruct_symbol_economic_index(close, product["events"])
    frame = mp.build_targets(econ, sessions, observations)
    rows = []
    for rec in frame.itertuples(index=False):
        target = "" if pd.isna(rec.target) else repr(float(rec.target))
        entry = (pd.Timestamp(rec.entry_date).strftime("%Y-%m-%d")
                 if pd.notna(rec.entry_date) else "")
        exit_ = (pd.Timestamp(rec.exit_date).strftime("%Y-%m-%d")
                 if pd.notna(rec.exit_date) else "")
        rows.append([
            mp.TARGET_ID, product_name,
            pd.Timestamp(rec.observation_date).strftime("%Y-%m-%d"),
            entry, exit_, target,
            rec.reason if rec.reason is not None and str(rec.reason) != "None" else "",
        ])
    return rows


def count_window_overlaps(target_rows: list[list], observations: list[str]) -> dict[str, int]:
    """逐产品比较相邻两期目标窗口 [e,x] 的真实日期相交（含端点接触日）。

    端点接触（共用一个交易日）按协议定义计入相交；任一窗口缺失
    （future_incomplete/缺端点）的期对不参与计数。返回
    ``{观察日: 该期窗口与下一期窗口相交的产品数}``——这是窗口重叠的
    描述统计，不是独立成功次数。
    """
    obs_norm = [pd.Timestamp(d).normalize() for d in observations]
    index_of = {d: i for i, d in enumerate(obs_norm)}
    by_symbol: dict[str, dict[int, tuple[pd.Timestamp, pd.Timestamp]]] = {}
    for row in target_rows:
        if not row[4] or row[6]:
            continue  # 缺 exit 或带缺失原因：窗口不完整，不参与计数
        sym, obs = row[1], pd.Timestamp(row[2]).normalize()
        if obs not in index_of or not row[3]:
            continue
        by_symbol.setdefault(sym, {})[index_of[obs]] = (
            pd.Timestamp(row[3]).normalize(), pd.Timestamp(row[4]).normalize(),
        )
    counts = {d: 0 for d in observations}
    for windows in by_symbol.values():
        for i in sorted(windows):
            if i + 1 not in windows:
                continue
            e1, x1 = windows[i]
            e2, x2 = windows[i + 1]
            if x1 >= e2 and e1 <= x2:
                counts[observations[i]] += 1
    return counts


def _pool_pairs(target_rows: list[list],
                momentum_by_symbol: dict) -> dict[str, dict[str, dict]]:
    """把各产品 (M, Y) 按观察日池化，供逐期排序诊断。"""
    per_period: dict[str, dict[str, dict]] = {}
    for row in target_rows:
        day = row[2]
        bucket = per_period.setdefault(day, {})
        momentum = momentum_by_symbol.get(row[1])
        mom_val = np.nan
        if momentum is not None:
            series = momentum
            key = pd.Timestamp(day).normalize()
            if key in series.index:
                mom_val = float(series.loc[key])
        bucket[row[1]] = {
            "momentum": mom_val,
            "target": float(row[5]) if row[5] else np.nan,
        }
    return per_period


def _rank_stage(per_period: dict[str, dict[str, dict]], overlaps: dict[str, int]) -> list[list]:
    """逐期排序诊断：当期各产品 (M, Y) 配对的并列平均名次 Spearman 等价。

    全部配对被剔除的期保留日期行（n=0、value 缺失、原因），是缺失结果
    而不是程序失败（Task 0 T1）。
    """
    rows = []
    for day in sorted(per_period):
        bucket = per_period[day]
        if not bucket:
            rows.append([
                mp.TARGET_ID, day, 0, "", "fewer_than_three_pairs",
                "", "", "", "", overlaps.get(day, 0),
            ])
            continue
        frame = pd.DataFrame.from_dict(bucket, orient="index")
        res = mp.rank_diagnostic(frame)
        paired = frame.loc[np.isfinite(frame["momentum"]) & np.isfinite(frame["target"])]
        rows.append([
            mp.TARGET_ID, day, res["n"],
            "" if res["value"] is None else repr(res["value"]),
            res["reason"] or "",
            repr(float(paired["momentum"].mean())) if len(paired) else "",
            repr(float(paired["momentum"].median())) if len(paired) else "",
            repr(float(paired["target"].mean())) if len(paired) else "",
            repr(float(paired["target"].median())) if len(paired) else "",
            overlaps.get(day, 0),
        ])
    return rows


def run_synthetic_pipeline(fixture: dict) -> dict:
    """合成闭环：完整跑通四个阶段；输出纯数值与缺失原因，无金额/账户。"""
    sessions = fixture["sessions"]
    observations = _month_last_sessions(sessions)
    values_rows: list[list] = []
    missing_rows: list[list] = []
    target_rows: list[list] = []
    momentum_by_symbol: dict[str, pd.Series] = {}
    failures: list[dict] = []

    for name in sorted(fixture["products"]):
        product = fixture["products"][name]
        try:
            vrows, mrows, momentum, _ = _momentum_stage(name, product, sessions, observations)
            values_rows += vrows
            missing_rows += mrows
            momentum_by_symbol[name] = momentum
            target_rows += _targets_stage(name, product, sessions, observations)
        except InputError as exc:
            failures.append({"product": name, "error": str(exc)})

    # 重叠统计按相邻两期真实 [e,x] 区间相交（含端点接触），不称独立
    overlap_counts = count_window_overlaps(target_rows, observations)
    per_period = _pool_pairs(target_rows, momentum_by_symbol)
    rank_rows = _rank_stage(per_period, overlap_counts)
    # 有产品计算失败时不得一面列失败、一面宣称完整成功
    exit_code = EXIT_REJECTED if failures else EXIT_OK
    return {
        "exit_code": exit_code,
        "values_rows": values_rows, "missing_rows": missing_rows,
        "target_rows": target_rows, "rank_rows": rank_rows,
        "observations": observations, "failures": failures,
        "overlap_counts": overlap_counts,
        "historical_reconstruction_only": False,
        "unknown_available_at": [], "reject_reasons": [],
    }


# ---------------------------------------------------------------------------
# 真实模式：输入检查、用途资格、身份映射
# ---------------------------------------------------------------------------


def _check_real_inputs(protocol: dict, input_paths: dict,
                       listing_evidence: dict | None = None) -> dict:
    """真实模式：加载快照/日历/行动/登记表，产出六用途检查与对象绑定摘要。"""
    from lei_signal.research import data_quality as q
    from lei_signal.research import definitions as d
    from lei_signal.research.data_snapshot import load_snapshot
    from lei_signal.research.trading_calendar import TradingCalendar

    loaded = load_snapshot(input_paths["snapshot_dir"]["path"])
    calendar = TradingCalendar.from_file(
        input_paths["calendar"]["path"], input_paths["publication"]["path"]
    )
    actions_payload = json.loads(
        Path(input_paths["actions"]["path"]).read_text(encoding="utf-8")
    )
    raw_actions = actions_payload.get("events")
    if not isinstance(raw_actions, list):
        raise InputError("行动文件缺少 events 列表容器")
    registry = d.load_registry(input_paths["registry"]["path"])
    sources_verified = True
    sources_error = None
    try:
        d.verify_sources(registry)
    except Exception as exc:  # noqa: BLE001 - 保留原因，交由资格判定拒绝
        sources_verified = False
        sources_error = f"{type(exc).__name__}: {exc}"

    start = protocol["inputs"]["evaluation_start"]
    end = protocol["inputs"]["evaluation_end"]
    report = q.check_snapshot(
        loaded, calendar=calendar, actions=raw_actions,
        evaluation_start=start, evaluation_end=end,
        listing_evidence=listing_evidence or None,
    )
    uses: dict[str, dict] = {}
    for u in q.USES:
        entry = {
            "verdict": report.verdict_for(u),
            "declared": u in loaded.declared_uses,
            "default_accepted": False,
            "reason": "",
        }
        try:
            q.require_use(report, u, declared_uses=loaded.declared_uses)
            entry["default_accepted"] = True
        except q.UseNotPermitted as exc:
            entry["reason"] = "; ".join(exc.reasons) if exc.reasons else exc.verdict
        uses[u] = entry

    objects: dict[str, dict] = {}
    from lei_signal.research.data_snapshot import bind_definitions

    refs = [protocol["objects"]["primary"], protocol["objects"]["dependency"]]
    bindings = bind_definitions(
        registry=registry, refs=refs, snapshot=loaded.snapshot, purpose=None,
    )["bindings"]
    for ref in refs:
        b = bindings[ref]
        objects[ref] = {
            "missing_fields": b.get("missing_fields"),
            "directly_satisfiable": b.get("directly_satisfiable"),
        }

    # ---- 行动逐记录核验（复用现有 data_quality.check_actions）：----
    # 允许"查看坏记录"不等于允许把坏记录用于重建经济指数。
    # BLOCK 级发现与计算消费绑定：任何一条即整批行动不得进入重建。
    actions_report = q.check_actions(
        raw_actions, declared_symbols=loaded.frames.keys()
    )
    action_findings = [
        {
            "level": str(f.level), "code": f.code,
            "instrument": getattr(f, "instrument", None),
            "message": f.message,
            "evidence": getattr(f, "evidence", None),
        }
        for f in actions_report.findings
    ]
    action_block = [f for f in action_findings if f["level"] == str(q.BLOCK)]

    # ---- 价格检查发现的逐条定位（返修 D2/§9.3）：产品/日期证据随产物落盘 ----
    price_findings = [
        {
            "code": f.code, "instrument": getattr(f, "instrument", None),
            "message": f.message, "evidence": getattr(f, "evidence", None),
        }
        for f in report.findings
    ]

    # ---- 输入时间语义留痕（D2）：来源位置 + 未知说明，不伪造历史可知时刻 ----
    input_times = {
        "snapshot_timing": loaded.snapshot.get("timing"),
        "per_instrument_fetched_at": {
            item.get("instrument_id"): {
                "fetched_at": item.get("fetched_at"),
                "first_date": item.get("first_date"),
                "last_date": item.get("last_date"),
            }
            for item in loaded.snapshot.get("instruments", [])
        },
        "actions_available_at": {
            "declared": sum(1 for a in raw_actions if a.get("available_at")),
            "unknown": sum(1 for a in raw_actions if not a.get("available_at")),
            "note": "行动原始记录的 available_at 未知条目只能事后重建，"
                    "不冒充历史可知输入",
        },
    }

    cov = calendar.coverage(start, end)
    return {
        "loaded": loaded, "calendar": calendar, "actions": raw_actions,
        "registry": registry, "sources_verified": sources_verified,
        "sources_error": sources_error, "uses": uses, "objects": objects,
        "action_findings": action_findings, "action_block": action_block,
        "price_findings": price_findings,
        "input_times": input_times,
        "integrity": {
            "verified": bool(loaded.verified),
            "hash_mismatches": list(loaded.hash_mismatches),
            "instruments": len(loaded.frames),
            "rows": int(sum(len(f) for f in loaded.frames.values())),
        },
        "coverage": {
            "complete": bool(cov.complete),
            "missing_months": list(cov.missing_months),
            "day_incomplete_months": list(cov.day_incomplete_months),
        },
    }


def _identity_map(symbols, actions) -> tuple[dict[str, str], list[dict]]:
    """原始代码 → 规范身份的一对一映射；冲突/未知拒绝，原值保留。

    裸码只按快照侧既有解析结果建立的明确映射转换（快照符号 → 裸码 → 规范
    身份），不按前缀猜交易所；映射不到的行动记录交由调用方拒绝。
    """
    from lei_signal.research.symbol_identity import build_mapping, parse_identity

    errors: list[dict] = []
    try:
        mapping_raws = build_mapping(sorted(set(symbols)), require_registered=False)
    except Exception as exc:  # noqa: BLE001
        return {}, [{"scope": "snapshot", "error": str(exc)}]
    canon: dict[str, str] = {raw: ident.canonical for raw, ident in mapping_raws.items()}
    by_bare: dict[str, str] = {}
    for raw, ident in mapping_raws.items():
        prior = by_bare.get(ident.bare_code)
        if prior is not None and prior != ident.canonical:
            errors.append({
                "scope": "mapping",
                "error": f"裸码 {ident.bare_code} 同时对应 {prior!r} 与 {raw!r}",
            })
        by_bare[ident.bare_code] = ident.canonical
    for ev in actions:
        raw = ev.get("symbol")
        if raw is None or raw in canon:
            continue
        try:
            ident = parse_identity(raw, require_registered=False)
        except Exception:  # noqa: BLE001 - 带后缀解析失败时回退裸码明确映射
            ident = None
        if ident is not None:
            canon[raw] = ident.canonical
        elif raw in by_bare:
            canon[raw] = by_bare[raw]
        else:
            errors.append({
                "scope": "action", "symbol": raw,
                "error": "无法按既有明确映射解析身份（未知记录，拒绝挂接）",
            })
    # 一对一核验：不同原始码映射到同一规范身份即拒绝
    seen: dict[str, str] = {}
    for raw, c in canon.items():
        if c in seen and seen[c] != raw:
            errors.append({"scope": "mapping", "error":
                           f"{raw!r} 与 {seen[c]!r} 映射到同一规范身份 {c!r}"})
        seen[c] = raw
    return canon, errors


def run_real_mode(protocol: dict, input_paths: dict, mode: str,
                  listing_evidence: dict | None = None) -> dict:
    """真实模式：先资格后计算；historical-diagnostic 不写 targets/rank。"""
    checks = _check_real_inputs(protocol, input_paths,
                                listing_evidence=listing_evidence)
    start = protocol["inputs"]["evaluation_start"]
    end = protocol["inputs"]["evaluation_end"]
    uses = checks["uses"]
    objects = checks["objects"]
    canon, identity_errors = _identity_map(
        checks["loaded"].frames.keys(), checks["actions"]
    )
    # 无法挂接的行动记录属身份致命错误：不得静默丢弃后宣称完整，
    # 整个研究请求按质量限制拒绝并列明记录。
    fatal_identity = [e for e in identity_errors if e.get("scope") == "action"]

    reject_reasons: list[str] = []
    if fatal_identity:
        reject_reasons.append(
            "行动记录身份无法解析："
            + "; ".join(f"{e.get('symbol')}: {e['error']}" for e in fatal_identity)
        )
    # 行动逐记录核验的 BLOCK 发现与计算消费绑定（返修 A）：
    # 任何一条不合法记录即整批行动不得进入经济指数重建。
    if checks["action_block"]:
        reject_reasons.append(
            "行动记录核验存在 BLOCK 级发现，不得进入重建："
            + "; ".join(
                f"[{f['code']}] {f.get('instrument') or ''} {f['message']}"
                for f in checks["action_block"]
            )
        )
    if not checks["integrity"]["verified"]:
        reject_reasons.append("快照完整性核验失败")
    if not checks["sources_verified"]:
        reject_reasons.append(f"登记表来源哈希核验未通过：{checks['sources_error']}")
    description_ok = uses["description"]["default_accepted"]
    if not description_ok:
        reject_reasons.append("描述用途未获允许：" + uses["description"]["reason"])
    objects_ok = all(o["directly_satisfiable"] for o in objects.values())
    if mode == "qualified-research":
        if not uses["ranking"]["default_accepted"]:
            reject_reasons.append("排序用途未获允许：" + uses["ranking"]["reason"])
        if not uses["research_signal"]["default_accepted"]:
            reject_reasons.append(
                "研究信号用途未获允许：" + uses["research_signal"]["reason"])
        if not objects_ok:
            missing = {r: o["missing_fields"] for r, o in objects.items()
                       if not o["directly_satisfiable"]}
            reject_reasons.append(f"对象字段检查未满足：{missing}")
        if not checks["coverage"]["complete"]:
            reject_reasons.append(
                f"日历覆盖不完整：missing={checks['coverage']['missing_months']}，"
                f"day_incomplete={checks['coverage']['day_incomplete_months']}"
            )

    # ---- 行动挂接与逐记录预检（返修 A）：计算开始前完成 ----
    calendar = checks["calendar"]
    loaded = checks["loaded"]
    observations = mp.complete_month_last_trading_days(calendar, start, end)
    sessions = [str(d) for d in mp.sessions_from_calendar(calendar, start, end)]
    by_symbol: dict[str, list[dict]] = {s: [] for s in loaded.frames}
    for ev in checks["actions"]:
        target = canon.get(ev.get("symbol"))
        if target in by_symbol:
            by_symbol[target].append(ev)
    adapted_by_symbol: dict[str, list[dict]] = {}
    for raw_symbol in sorted(loaded.frames):
        try:
            adapted_by_symbol[raw_symbol] = mp.adapt_company_events(
                by_symbol[raw_symbol]
            )
        except ValueError as exc:
            reject_reasons.append(f"{raw_symbol} 行动记录不合法：{exc}")

    # ---- 时间资格（返修 R1）：qualified 分支在生成任何信号/目标之前，
    # 核对进入信号计算的行动是否能在观察日决策时点前证明可知；
    # 无法证明即拒绝研究，逐条列产品/event_id/时点/原因。 ----
    time_violations: list[dict] = []
    if mode == "qualified-research" and not reject_reasons:
        for raw_symbol in sorted(adapted_by_symbol):
            for v in mp.signal_time_violations(
                adapted_by_symbol[raw_symbol], observations
            ):
                time_violations.append({"product": raw_symbol, **v})
        if time_violations:
            reject_reasons.append(
                "时间资格未满足：进入信号计算的资料无法证明在观察时点可知（"
                + "; ".join(
                    f"{v['product']} {v['event_id']}"
                    f"@{v.get('observation_date') or '格式'} {v['reason']}"
                    for v in time_violations[:10]
                )
                + (f"；共 {len(time_violations)} 条" if len(time_violations) > 10 else "")
                + "）"
            )

    quality = {
        "integrity": checks["integrity"],
        "sources_verified": checks["sources_verified"],
        "sources_error": checks["sources_error"],
        "uses": {u: uses[u] for u in USES_CHECKED},
        "objects": objects,
        "coverage": checks["coverage"],
        "action_findings": checks["action_findings"],
        "price_findings": checks["price_findings"],
        "identity_errors": identity_errors,
        "time_violations": time_violations,
        "input_times": checks["input_times"],
        "policy": "not_applicable_no_account_policy",
    }

    skipped: dict[str, str] = {}
    if reject_reasons:
        reason_text = "；".join(reject_reasons)
        if mode == "qualified-research":
            skipped = {
                "economic-reconstruction": f"研究资格未满足，拒绝运行：{reason_text}",
                "targets": f"研究资格未满足，拒绝运行：{reason_text}",
                "rank-diagnostic": f"研究资格未满足，拒绝运行：{reason_text}",
            }
        else:
            skipped = {
                "economic-reconstruction": reason_text,
                "targets": "协议规定历史诊断不写真实 targets/rank",
                "rank-diagnostic": "协议规定历史诊断不写真实 targets/rank",
            }
        return {
            "exit_code": EXIT_REJECTED, "quality": quality,
            "skipped": skipped, "reject_reasons": reject_reasons,
            "values_rows": [], "missing_rows": [], "target_rows": [],
            "rank_rows": [], "observations": [], "failures": [],
            "historical_reconstruction_only": False,
            "unknown_available_at": [], "identity_errors": identity_errors,
        }

    # ---- 已获允许：重建经济指数与本轮动量（observations/sessions 已在门控前计算） ----
    values_rows: list[list] = []
    missing_rows: list[list] = []
    target_rows: list[list] = []
    momentum_by_symbol: dict[str, pd.Series] = {}
    failures: list[dict] = []
    unknown_all: list[dict] = []
    for raw_symbol in sorted(loaded.frames):
        if raw_symbol not in canon:
            failures.append({"product": raw_symbol, "error": "身份无法解析"})
            continue
        close = loaded.frames[raw_symbol]["close"].astype(float)
        close = close[close > 0].dropna()
        product = {"close": close, "events": by_symbol[raw_symbol]}
        try:
            vrows, mrows, momentum, unknown = _momentum_stage(
                raw_symbol, product, sessions, observations
            )
            if mode == "qualified-research":
                target_rows += _targets_stage(
                    raw_symbol, product, sessions, observations
                )
        except InputError as exc:
            failures.append({"product": raw_symbol, "error": str(exc)})
            continue
        values_rows += vrows
        missing_rows += mrows
        momentum_by_symbol[raw_symbol] = momentum
        unknown_all += [{"symbol": raw_symbol, "event_id": u} for u in unknown]

    # ---- 时间状态（返修 R1）：逐事件标注晚取得/未知；历史模式只诚实标注
    # 事后重建，不把"格式合法的未来时间"当成历史可知。 ----
    window_end_moment = mp.decision_moment(pd.Timestamp(end))
    late_or_unknown: list[dict] = []
    for raw_symbol in sorted(adapted_by_symbol):
        for ev in adapted_by_symbol[raw_symbol]:
            if pd.Timestamp(ev["effective_date"]) > pd.Timestamp(end):
                continue  # 评价期内未生效的行动不进入本轮计算
            try:
                av = mp.parse_available_at(ev.get("available_at"), ev.get("event_id"))
            except ValueError as exc:
                late_or_unknown.append({
                    "symbol": raw_symbol, "event_id": ev.get("event_id"),
                    "available_at": ev.get("available_at"), "reason": str(exc),
                })
                continue
            if av is None:
                late_or_unknown.append({
                    "symbol": raw_symbol, "event_id": ev.get("event_id"),
                    "available_at": None,
                    "reason": "available_at 未知，只能事后重建",
                })
            elif av > window_end_moment:
                late_or_unknown.append({
                    "symbol": raw_symbol, "event_id": ev.get("event_id"),
                    "available_at": str(av),
                    "reason": f"available_at 晚于评价期终点 {end}，晚取得、事后重建",
                })
    # Task 0 T2：晚取得以受影响的观察时点为准，不只和评价期末比较——
    # 晚于部分历史观察、早于期末的行动同样只能事后重建。
    flagged = {(d["symbol"], d["event_id"]) for d in late_or_unknown}
    for raw_symbol in sorted(adapted_by_symbol):
        for v in mp.signal_time_violations(adapted_by_symbol[raw_symbol], observations):
            key = (raw_symbol, v.get("event_id"))
            if key in flagged:
                continue
            late_or_unknown.append({
                "symbol": raw_symbol, "event_id": v.get("event_id"),
                "available_at": v.get("available_at"),
                "reason": (
                    f"晚于受影响观察日 {v.get('observation_date')} 的决策时点，"
                    "事后重建"
                ),
            })
            flagged.add(key)
    hist_recon_only = bool(late_or_unknown)

    if mode == "qualified-research":
        # 合格分支真正产出 targets/rank（返修 C1）；目标标签按成熟可知处理
        #（返修 R1 + Task 0）：逐行互斥分类，未可知标签从排序配对剔除并留痕。
        label_counts = {
            "available": 0, "action_not_knowable": 0, "endpoint_not_mature": 0,
            "endpoint_missing": 0, "observation_not_session": 0,
        }
        action_not_knowable_detail: list[dict] = []
        for row in target_rows:
            reason = row[6] or ""
            if reason == "observation_not_session":
                status = "observation_not_session"
            elif reason == "future_incomplete":
                status = "endpoint_not_mature"
            elif reason:
                status = "endpoint_missing"
            else:
                inv = mp.target_label_incomplete(
                    adapted_by_symbol.get(row[1], []), row[4])
                if inv:
                    status = "action_not_knowable"
                    action_not_knowable_detail.append({
                        "product": row[1], "observation_date": row[2],
                        "exit_date": row[4], "events": inv,
                    })
                else:
                    status = "available"
            label_counts[status] += 1
        overlap_counts = count_window_overlaps(target_rows, observations)
        per_period = _pool_pairs(target_rows, momentum_by_symbol)
        excluded = {(r["product"], r["observation_date"])
                    for r in action_not_knowable_detail}
        for day in list(per_period):
            for sym in list(per_period[day]):
                if (sym, day) in excluded:
                    del per_period[day][sym]
        rank_rows = _rank_stage(per_period, overlap_counts)
        assert sum(label_counts.values()) == len(target_rows), (
            "标签状态互斥分类总数必须与目标行总数对账")
        quality["target_label_status"] = {
            "counts": label_counts,
            "total": len(target_rows),
            "action_not_knowable_detail": action_not_knowable_detail,
            "diagnostic_pairs_pooled": sum(len(v) for v in per_period.values()),
            "note": ("互斥分类：可用/行动不可知/端点未成熟/端点缺价/非观察日；"
                     "未可知标签不参与排序配对，目标数值本身按事后评价保留"),
        }
        result_label_status = quality["target_label_status"]
        skipped = {}
    else:
        result_label_status = None
        rank_rows = []
        skipped = {
            "targets": "协议规定历史诊断模式不写真实 targets/rank 结果",
            "rank-diagnostic": "协议规定历史诊断模式不写真实 targets/rank 结果",
        }
    quality["late_or_unknown_actions"] = late_or_unknown
    quality["input_times"]["actions_available_at"]["late_or_unknown"] = len(late_or_unknown)
    quality["observation_cutoff_assumption"] = (
        "观察/决策截点 15:00（本地）是按收盘设置的保守测试假设，"
        "不是已证实的数据到达时间或实盘决策时刻；真实研究的报价可得依据仍受限"
    )
    exit_code = EXIT_REJECTED if failures else EXIT_OK
    if failures:
        skipped["affected-products"] = "; ".join(
            f"{f['product']}: {f['error']}" for f in failures
        )
    return {
        "exit_code": exit_code, "quality": quality, "skipped": skipped,
        "reject_reasons": reject_reasons,
        "values_rows": values_rows, "missing_rows": missing_rows,
        "target_rows": target_rows, "rank_rows": rank_rows,
        "observations": observations, "failures": failures,
        "historical_reconstruction_only": hist_recon_only,
        "unknown_available_at": unknown_all, "identity_errors": identity_errors,
        "late_available_at": late_or_unknown,
        "target_label_status": result_label_status,
    }


# ---------------------------------------------------------------------------
# 产物渲染与写出（manifest 最后；任一环 I/O 失败都不得留下完成假象）
# ---------------------------------------------------------------------------


def _csv(rows: list[list], header: list[str]) -> str:
    out = [",".join(header)]
    for row in rows:
        out.append(",".join("" if c is None else str(c) for c in row))
    return "\n".join(out) + "\n"


def _render_report(result: dict, protocol: dict, mode: str, fixture: dict | None) -> str:
    n_values = len(result["values_rows"])
    n_missing = len(result["missing_rows"])
    n_targets = len(result["target_rows"])
    rank_rows = result["rank_rows"]
    rank_ok = [r for r in rank_rows if r[3]]
    lines = [
        "# 动量研究样板运行报告",
        "",
        f"- 模式：`{mode}`；协议：`{protocol['protocol_id']}`",
        f"- synthetic = {mode == 'synthetic'}",
        f"- historical_reconstruction_only = "
        f"{result.get('historical_reconstruction_only', False)}",
        "",
        "## 一句话结论（大白话）",
        "",
    ]
    if mode == "synthetic":
        lines += [
            "用完全虚构的价格数据把整套计算从头到尾跑通了："
            f"重建复权指数、算动量、算未来观察目标、算排名一致性，"
            f"共写出 {n_values} 个动量值、{n_targets} 个未来目标、"
            f"{len(rank_rows)} 期排名诊断（其中 {len(rank_ok)} 期有数值）。"
            "这只能证明算法和时间安排算得对，不能证明这个指标在真实市场上有效。"
        ]
    elif mode == "historical-diagnostic":
        lines += [
            f"用真实冻结数据做了被允许的部分：重建了复权指数并算出动量值 "
            f"{n_values} 个，缺失 {n_missing} 处都写明了原因。"
            "未来目标和排名诊断按协议没有对真实数据运行。"
            "这只是历史数值复算，不构成对未来走势的任何预测证据。"
        ]
    else:
        if result["reject_reasons"]:
            lines += [
                "真实预测研究被拒绝：资料资格不够（" +
                "；".join(result["reject_reasons"]) + "）。"
                "没有写出任何真实排名结果，这不是失败，是按规定停下来。"
            ]
        else:
            lines += [
                f"真实预测研究完整运行：{len(rank_rows)} 期排名诊断"
                f"（{len(rank_ok)} 期有数值）。结果只描述过去一致性，不预测未来。"
            ]
    lines += ["", "## 阶段与数量", "",
              f"- 观察日数：{len(result['observations'])}",
              f"- 动量值：{n_values}；缺失：{n_missing}",
              f"- 未来目标：{n_targets}",
              f"- 排名诊断期数：{len(rank_rows)}（有值 {len(rank_ok)}）"]
    label_status = result.get("target_label_status")
    if label_status is not None:
        lines.append(
            f"- 目标标签（互斥分类）：{label_status['counts']}；"
            f"其中行动不可知 {len(label_status['action_not_knowable_detail'])} 个"
            "（不参与排序配对）"
        )
    if not fixture and result.get("unknown_available_at") is not None:
        q = result.get("quality") or {}
        action_counts = (q.get("input_times") or {}).get("actions_available_at") or {}
        if action_counts:
            total_actions = (action_counts.get("declared", 0)
                             + action_counts.get("unknown", 0))
            lines += [
                f"- 原始行动记录 {total_actions}"
                f" 条；其中进入经济指数的分红/拆分以挂接与逐记录核验结果为准，"
                f"停牌等非经济行动不进入；available_at 已声明 "
                f"{action_counts.get('declared', 0)} 条、未知 "
                f"{action_counts.get('unknown', 0)} 条",
            ]
    if result["failures"]:
        lines += ["", "## 受影响产品（已停止计算并列错误）", ""]
        lines += [f"- `{f['product']}`：{f['error']}" for f in result["failures"]]
    if result.get("skipped"):
        lines += ["", "## 未运行阶段", ""]
        lines += [f"- {k}：{v}" for k, v in result["skipped"].items()]
    if fixture is not None:
        lines += ["", "## 合成夹具说明（synthetic=true）", ""]
        lines += [f"- {name}：{note}" for name, note in sorted(fixture["notes"].items())]
        lines += [
            "",
            f"- 人工交易日历：{fixture['window'][0]} ~ {fixture['window'][1]}"
            f"，共 {len(fixture['sessions'])} 个交易日，节假日 {fixture['holidays']}",
            "- 全部数据为本次生成，不伪装交易所数据或上市材料；"
            "合成成功不代表真实资料准入。",
        ]
    if result.get("unknown_available_at"):
        lines += [
            "", "## 未知可得时点的行动（available_at 未知，保持 null）", "",
        ]
        lines += [
            f"- `{u['symbol']}` {u['event_id']}" for u in result["unknown_available_at"]
        ]
    if result.get("reject_reasons") and mode != "qualified-research":
        lines += ["", "## 拒绝原因", ""]
        lines += [f"- {r}" for r in result["reject_reasons"]]
    lines += [
        "", "## 状态",
        "",
        "- computation_run = "
        f"{bool(result['values_rows'] or result['target_rows'] or rank_ok)}",
        "- research_qualification = "
        + ("rejected" if result["reject_reasons"] else
           ("qualified_synthetic_only" if mode == "synthetic" else "qualified_for_this_mode")),
        "- validity = not_tested_by_this_run",
        "- production = not_authorized",
        "- policy = not_applicable_no_account_policy",
        "",
        "> 本运行不证明动量指标有效，不构成交易授权；"
        "无资金账户计算，政策卡不适用。",
    ]
    return "\n".join(lines) + "\n"


def _build_manifest(result: dict, protocol: dict, protocol_sha: str, mode: str,
                    protocol_path: str, input_paths: dict | None, files: list[tuple[str, str]],
                    fixture: dict | None, guard: _OfflineGuard) -> dict:
    code_files = {
        "momentum_prototype": ROOT / "src/lei_signal/research/momentum_prototype.py",
        "run_momentum_research_prototype": ROOT / "scripts/run_momentum_research_prototype.py",
    }
    return {
        "schema_version": "momentum-research-prototype-manifest/1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_at_note": "本次运行时刻，不得当作数据的对外可用时刻",
        "mode": mode,
        "synthetic": mode == "synthetic",
        "historical_reconstruction_only": result.get(
            "historical_reconstruction_only", False),
        "protocol": {"path": protocol_path, "sha256": protocol_sha,
                     "protocol_id": protocol["protocol_id"]},
        "target_id": protocol["target_id"],
        "objects": {"primary": protocol["objects"]["primary"],
                    "dependency": protocol["objects"]["dependency"],
                    "type": "feature（身份引用，完整卡见协议文件）"},
        "code_hashes": {k: _sha256_file(v) for k, v in code_files.items()},
        "inputs": input_paths,
        "observations": {
            "count": len(result["observations"]),
            "first": result["observations"][0] if result["observations"] else None,
            "last": result["observations"][-1] if result["observations"] else None,
        },
        "unknown_available_at": result.get("unknown_available_at", []),
        "late_available_at": result.get("late_available_at", []),
        "observation_cutoff_assumption": (
            "观察/决策截点 15:00 为按收盘设置的保守测试假设，"
            "不是已证实的数据到达时间或实盘决策时刻"
        ),
        "failures": result.get("failures", []),
        "identity_errors": result.get("identity_errors", []),
        "research_evidence": result.get("research_evidence"),
        "skipped_stages": result.get("skipped", {}),
        "offline_guard": guard.self_check,
        "statuses": {
            "computation_run": bool(
                result["values_rows"] or result["target_rows"]
                or [r for r in result["rank_rows"] if r[3]]
            ),
            "research_qualification": (
                "rejected" if result["reject_reasons"] else "qualified_for_this_mode"
            ),
            "validity": "not_tested_by_this_run",
            "production": "not_authorized",
            "policy": "not_applicable_no_account_policy",
        },
        # 文件尚未落盘：直接对最终文本内容哈希（与写出内容逐字节一致）
        "outputs": {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
                    for name, text in files},
    }


def _write_all(out: Path, files: list[tuple[str, str]], manifest_text: str) -> None:
    """按序写产物，manifest 最后；任一环失败抛 OSError 由调用方统一收尾。

    out 本身可能已由桥接产物在运行中途创建（入口处的已存在拒绝检查
    发生在此之前）；此处允许已存在。"""
    out.mkdir(parents=True, exist_ok=True)
    for name, text in files:
        (out / name).write_text(text, encoding="utf-8")
    (out / "manifest.json").write_text(manifest_text, encoding="utf-8")


def _fail(out: Path, stage: str, exc: Exception) -> int:
    with contextlib.suppress(OSError):
        out.mkdir(parents=True, exist_ok=True)
        (out / "FAILED.txt").write_text(
            f"输出阶段失败（{stage}）：{type(exc).__name__}: {exc}\n"
            "部分产物与缺失的 manifest.json 均不构成本次完成证明。\n",
            encoding="utf-8",
        )
    print(f"输出阶段失败（{stage}）：{type(exc).__name__}: {exc}", file=sys.stderr)
    return EXIT_FAILED


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--protocol", required=True, help="本轮冻结协议 JSON 路径")
    parser.add_argument("--mode", required=True, choices=list(MODES))
    parser.add_argument("--out", required=True, help="输出目录（必须不存在）")
    args = parser.parse_args(argv)

    out = Path(args.out)
    if out.exists():
        print(f"输出目录已存在，拒绝覆盖：{out}\n请显式选择新目录（如 run-NN+1）。",
              file=sys.stderr)
        return EXIT_FAILED

    guard = _OfflineGuard()
    try:
        guard.install()
    except InputError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAILED

    try:
        protocol, protocol_sha = _load_protocol(Path(args.protocol))
        _verify_protocol_codes(protocol)
        _verify_protocol_identity(protocol)
        mode = args.mode
        fixture = None
        input_paths: dict | None = None
        research_evidence = None
        if mode == "synthetic":
            fixture = build_synthetic_fixture()
            result = run_synthetic_pipeline(fixture)
            quality = {
                "fixture_notes": fixture["notes"],
                "calendar": {"sessions": len(fixture["sessions"]),
                             "window": fixture["window"],
                             "holidays": fixture["holidays"]},
                "synthetic": True,
                "policy": "not_applicable_no_account_policy",
            }
            result["quality"] = quality
            result["reject_reasons"] = []
            result["skipped"] = {}
            result["identity_errors"] = []
        else:
            input_paths = _verify_protocol_inputs(protocol)
            research_evidence = _verify_research_evidence(protocol, input_paths)
            listing_mapping = None
            if research_evidence:
                # 已核上市事实 → 既有 listing 验证器桥接（Task 5）：
                # 只让「证据确实解决的具体发现」改变，资格授予仍归底层闸门。
                from lei_signal.research.qualification_bundle import (
                    listing_evidence_from_validated,
                    validate_evidence_bundle,
                )

                meta_path = (Path(input_paths["snapshot_dir"]["path"])
                             / "snapshot.json")
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                universe = {item["instrument_id"] for item in meta["instruments"]}
                bundle = json.loads(
                    Path(research_evidence["path"]).read_text(encoding="utf-8"))
                vres = validate_evidence_bundle(
                    bundle, root=ROOT, universe=universe)
                listing_mapping = listing_evidence_from_validated(
                    [r for r in vres["validated"] if r["fact_type"] == "listing"],
                    out_dir=out / "listing-bridge",
                )
                research_evidence["listing_bridge"] = {
                    "products": sorted(listing_mapping),
                    "dir": str(out / "listing-bridge"),
                }
            result = run_real_mode(protocol, input_paths, mode,
                                   listing_evidence=listing_mapping)
        result["research_evidence"] = research_evidence

        files: list[tuple[str, str]] = [("quality.json", json.dumps(
            result["quality"], indent=1, ensure_ascii=False) + "\n")]
        if result["values_rows"]:
            files.append(("values.csv", _csv(
                result["values_rows"],
                ["object_id", "symbol", "date", "momentum", "unit"])))
        if result["missing_rows"]:
            files.append(("missing.csv", _csv(
                result["missing_rows"],
                ["object_id", "symbol", "date", "stage", "reason"])))
        if result["target_rows"]:
            files.append(("targets.csv", _csv(
                result["target_rows"],
                ["target_id", "symbol", "observation_date", "entry_date",
                 "exit_date", "target", "reason"])))
        if result["rank_rows"]:
            files.append(("rank-diagnostic.csv", _csv(
                result["rank_rows"],
                ["target_id", "observation_date", "n", "value", "reason",
                 "mean_momentum", "median_momentum", "mean_target",
                 "median_target", "windows_overlapping_next"])))
        if result["skipped"]:
            files.append(("skipped-stages.json", json.dumps(
                result["skipped"], indent=1, ensure_ascii=False) + "\n"))
        report_md = _render_report(result, protocol, mode, fixture)
        files.append(("report.md", report_md))
        # manifest 的 outputs 哈希要先知道各文件内容：先按最终内容构造，
        # 再一次性写出（manifest 最后）。
        manifest = _build_manifest(
            result, protocol, protocol_sha, mode, args.protocol,
            input_paths, files, fixture, guard,
        )
        manifest_text = json.dumps(manifest, indent=1, ensure_ascii=False) + "\n"
        _write_all(out, files, manifest_text)
    except InputError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_FAILED
    except OSError as exc:
        return _fail(out, "write", exc)
    except Exception as exc:  # noqa: BLE001 - 运行失败必须有明确出口
        print(f"运行失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_FAILED

    print(f"mode={args.mode} out={out}")
    print(f"values={len(result['values_rows'])} missing={len(result['missing_rows'])} "
          f"targets={len(result['target_rows'])} rank_periods={len(result['rank_rows'])}")
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
