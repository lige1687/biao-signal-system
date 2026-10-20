"""已有动量指标的研究样板薄适配（momentum-research-prototype-2026-09-13）。

只复用既有引擎，不修改定义/因子运行时：

- ``compute_momentum``：调用 ``definitions.quote_features`` 暴露本轮列
  ``mixed.momentum.raw@1.0.0`` 的原始值 ``M(t)=I(t-21)/I(t-252)-1``。
- ``build_targets`` / ``rank_diagnostic``：本轮协议的唯一未来观察目标
  ``protocol:momentum-next-close-21-session@1.0.0`` 与并列平均名次的
  Spearman 等价诊断。它们不是登记表对象，也不是 ``mixed.momentum.rank``
  的按代码打破并列的选股顺序。
- 日历/身份/快照适配器为只读封装，供 CLI 离线编排使用。

本模块不实现新价格公式、不运行账户、不输出金额/交易/账户回报。
"""
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from . import definitions
from .factor_runtime import reconstructed_economic_index

# 本轮协议测量的未来观察目标身份；明确它不是登记表对象，不可冒充正式因子。
TARGET_ID = "protocol:momentum-next-close-21-session@1.0.0"

# 依赖的已登记对象（feature，不是可投资因子收益组合）。
MOMENTUM_REF = "mixed.momentum.raw@1.0.0"
ECONOMIC_REF = "mixed.price.economic@1.0.0"

# 未来目标窗口：观察日 t 之后第一个交易日 e，e 之后第 21 个交易日 x。
NEXT_SESSION_OFFSET = 1
EXIT_SESSION_OFFSET = 22  # e 之后第 21 => 观察日后第 22 个位置


def compute_momentum(index: pd.Series) -> pd.Series:
    """本轮动量原始值 ``M(t)=I(t-21)/I(t-252)-1``。

    复用 ``definitions.quote_features(index)["momentum"]``，仅暴露本轮列。
    输入为同一产品的经济指数：唯一递增日期、非缺失值有限且大于零；原定义
    的报价缺失规则保留（缺失返回 NaN）。
    """
    if not index.index.is_unique or not index.index.is_monotonic_increasing:
        raise ValueError("unique increasing dates required")
    values = index.dropna().to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("finite positive index required")
    return definitions.quote_features(index)["momentum"]


def validate_sessions(sessions: Iterable) -> pd.DatetimeIndex:
    """核验交易日期序列：唯一、升序、按日归一。

    不做静默排序：调用方必须传入已核完整的有序交易日；乱序与重复都拒绝。
    """
    s = pd.DatetimeIndex(pd.to_datetime(list(sessions), errors="raise")).normalize()
    if not s.is_unique:
        raise ValueError("sessions must be unique trading dates")
    if not s.is_monotonic_increasing:
        raise ValueError("sessions must be monotonically increasing")
    return s


def build_targets(
    index: pd.Series, sessions, observations
) -> pd.DataFrame:
    """对观察日 t 计算唯一未来观察目标 ``Y(t)=I(x)/I(e)-1``。

    参数
    ----
    index:
        同一产品的经济指数（DatetimeIndex，可含 NaN）。
    sessions:
        已核完整、有序、唯一的交易日期。
    observations:
        观察日期（须是 ``sessions`` 中的某日）。

    返回列：``observation_date, entry_date, exit_date, target, reason``。
    e 为 t 之后第一个交易日，x 为 e 之后第 21 个交易日；e、x 都要求该产品
    实际有效报价，缺端点或区间末尾不足返回缺失，不顺延到下一次报价。
    """
    sess = validate_sessions(sessions)
    positions = {day: k for k, day in enumerate(sess)}
    rows = []
    for day in observations:
        key = pd.Timestamp(day).normalize()
        if key not in positions:
            rows.append((key, None, None, np.nan, "observation_not_session"))
            continue
        e, x = positions[key] + NEXT_SESSION_OFFSET, positions[key] + EXIT_SESSION_OFFSET
        if x >= len(sess):
            rows.append((key, None, None, np.nan, "future_incomplete"))
            continue
        first, last = sess[e], sess[x]
        a, b = index.get(first, np.nan), index.get(last, np.nan)
        if not np.isfinite([a, b]).all() or a <= 0 or b <= 0:
            rows.append((key, first, last, np.nan, "endpoint_missing_or_invalid"))
        else:
            rows.append((key, first, last, b / a - 1, None))
    return pd.DataFrame(
        rows,
        columns=["observation_date", "entry_date", "exit_date", "target", "reason"],
    )


def build_diagnostic_frame(momentum: pd.Series, targets: pd.DataFrame) -> pd.DataFrame:
    """把动量序列按观察日并入目标表，产出含 ``momentum`` / ``target`` 的诊断框。"""
    m = momentum.rename("momentum")
    merged = (
        targets.set_index("observation_date")[["target", "reason"]]
        .join(m, how="left")
        .reset_index()
    )
    return merged


def rank_diagnostic(frame: pd.DataFrame) -> dict:
    """并列平均名次的 Spearman 等价：两列各自平均名次后再算 Pearson 相关。

    它衡量"当期指标排序与随后变化排序的一致程度"，不是选股名次。
    少于 3 个配对或任一列名次全相同返回缺失及原因；空集合（含无列空帧）
    是缺失结果而不是错误。
    """
    if (frame is None or len(frame) == 0
            or "momentum" not in frame.columns or "target" not in frame.columns):
        return {"n": 0, "value": None, "reason": "fewer_than_three_pairs"}
    paired = frame.loc[np.isfinite(frame["momentum"]) & np.isfinite(frame["target"])]
    n = len(paired)
    if n < 3:
        return {"n": n, "value": None, "reason": "fewer_than_three_pairs"}
    ranks = paired[["momentum", "target"]].rank(method="average")
    if (ranks.nunique() <= 1).any():
        return {"n": n, "value": None, "reason": "constant_rank"}
    return {
        "n": n,
        "value": float(ranks["momentum"].corr(ranks["target"])),
        "reason": None,
    }


def complete_month_last_trading_days(calendar, start: str, end: str) -> list[str]:
    """评价区间内各**完整**月份的最后交易日。

    完整 = 在 ``coverage.covered_months`` 内且不在缺失/逐日不完整/整月不完整中。
    月份不完整不推断月末；产品当日无报价不在此处前填。
    """
    cov = calendar.coverage(start, end)
    incomplete = (
        set(cov.missing_months)
        | set(cov.day_incomplete_months)
        | set(cov.month_incomplete_months)
    )
    tds = calendar.trading_days(start, end)
    last_by_month: dict[str, str] = {}
    for d in tds:
        month = d[:7]
        if month not in cov.covered_months or month in incomplete:
            continue
        if month not in last_by_month or d > last_by_month[month]:
            last_by_month[month] = d
    return [last_by_month[m] for m in sorted(last_by_month)]


def sessions_from_calendar(calendar, start: str, end: str) -> pd.DatetimeIndex:
    """评价区间内已确认交易日的升序 DatetimeIndex。"""
    return validate_sessions(calendar.trading_days(start, end))


#: 行动原始记录允许出现的字段（登记口径 + 冻结输入的来源/限定说明字段）。
#: 出现清单之外的字段（如账户字段 fee/amount）即结构不合法，整条记录不得
#: 进入经济指数重建。
_ALLOWED_ACTION_FIELDS = frozenset({
    "event_id", "symbol", "type",
    "effective_date", "ex_date", "record_date", "pay_date", "announcement_date",
    "cash", "cash_per_unit", "cash_per_share", "ratio", "split_ratio",
    "available_at", "source", "source_url", "source_path", "source_sha256",
    "qualification", "note",
    "halt",  # trading_halt 记录的合法嵌套区间字段（不进入经济指数）
})

_CASH_FIELDS = ("cash", "cash_per_unit", "cash_per_share")
_RATIO_FIELDS = ("ratio", "split_ratio")


def _valid_action_day(value) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    from datetime import date

    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def adapt_company_events(events: list[dict]) -> list[dict]:
    """把合法行动原始记录逐项映射为 ``reconstructed_economic_index`` 所需字段。

    参与计算的原料必须独立满足结构、身份与数值条件；不合法时抛
    ``ValueError``，由调用方停止受影响计算并列明 event_id/原因，不得
    静默跳过后宣称完整：

    - 结构：出现 :data:`_ALLOWED_ACTION_FIELDS` 之外的字段（如账户字段）即拒绝；
    - 同义字段（cash/cash_per_unit/cash_per_share；ratio/split_ratio）取值
      相互冲突即拒绝，不静默择一；
    - 数值：分红每份现金必须有限且非负；拆分比例必须有限且大于零；
    - 身份：event_id 缺失或在本批记录中重复即全部拒绝；
    - 日期：生效日/除权日必须能解析为真实日历日；
    - 单纯缺 ``available_at`` **不是**不合法：照常适配并保留 None，由上层
      记录未知可得时点（本轮已授权的事后重建）；
    - 停牌（trading_halt）只做缺口解释，不进入经济指数。
    """
    seen_ids: set[str] = set()
    for ev in events:
        eid = ev.get("event_id")
        if not eid:
            raise ValueError(f"行动缺少 event_id：{ev!r}")
        if eid in seen_ids:
            raise ValueError(f"行动 event_id 重复，本批记录全部不得消费：{eid!r}")
        seen_ids.add(eid)

    out: list[dict] = []
    for ev in events:
        foreign = sorted(set(ev) - _ALLOWED_ACTION_FIELDS)
        if foreign:
            raise ValueError(
                f"行动记录带未登记字段 {foreign}，整条记录不得进入重建："
                f"{ev.get('event_id')!r}"
            )
        typ = ev.get("type")
        if typ not in {"split", "cash_dividend"}:
            continue  # 停牌等类型不进入经济指数
        event_id = ev.get("event_id")
        eff = ev.get("effective_date") or ev.get("ex_date")
        if not eff:
            raise ValueError(f"行动 {event_id!r} 缺少生效日")
        if not _valid_action_day(eff):
            raise ValueError(f"行动 {event_id!r} 生效日不是真实日历日：{eff!r}")
        item = {
            "event_id": event_id,
            "type": typ,
            "effective_date": eff,
            "available_at": ev.get("available_at"),
        }
        if typ == "split":
            present = [f for f in _RATIO_FIELDS if ev.get(f) is not None]
            if not present:
                raise ValueError(f"拆分 {event_id!r} 缺少比例")
            values = {float(ev[f]) for f in present}
            if len(values) > 1:
                raise ValueError(
                    f"拆分 {event_id!r} 同义比例字段相互冲突："
                    f"{dict((f, ev[f]) for f in present)}；不静默择一"
                )
            ratio = values.pop()
            if not np.isfinite(ratio) or ratio <= 0:
                raise ValueError(f"拆分 {event_id!r} 比例非法：{ratio!r}")
            item["ratio"] = ratio
        else:
            present = [f for f in _CASH_FIELDS if ev.get(f) is not None]
            if not present:
                raise ValueError(f"分红 {event_id!r} 缺少每份现金")
            values = {float(ev[f]) for f in present}
            if len(values) > 1:
                raise ValueError(
                    f"分红 {event_id!r} 同义金额字段相互冲突："
                    f"{dict((f, ev[f]) for f in present)}；不静默择一"
                )
            cash = values.pop()
            if not np.isfinite(cash) or cash < 0:
                raise ValueError(f"分红 {event_id!r} 每份现金非法：{cash!r}")
            item["cash"] = cash
        out.append(item)
    return out


def reconstruct_symbol_economic_index(
    close: pd.Series, actions: list[dict], *, historical_reconstruction_only: bool = True
):
    """薄封装 ``factor_runtime.reconstructed_economic_index``。

    真实资料缺 ``available_at`` 时必须 ``historical_reconstruction_only=True``，
    返回的经济指数只能事后重建，不能冒充严格历史可知输入。输出未知可得时点的
    行动 ID 列表，交由上层标注。输入行动先经 :func:`adapt_company_events`
    字段适配。
    """
    idx, unknown = reconstructed_economic_index(close, adapt_company_events(actions))
    if not historical_reconstruction_only and unknown:
        raise ValueError(
            "events without available_at require historical_reconstruction_only=True"
        )
    return idx, unknown


# ---------------------------------------------------------------------------
# 时间资格（返修 R1）：非空可得时间不等于历史时点合格。
# 进入 t 日信号的行动必须不晚于 t 的决策时点可知；未来目标是事后评价标签，
# 按"成熟且可知"处理，不把合理的事后标签一律认成泄漏。
# ---------------------------------------------------------------------------

DECISION_TIMEZONE = "Asia/Shanghai"
DECISION_HOUR = 15  # 冻结卡 time.observation_time：t 有效收盘 15:00


def decision_moment(day) -> pd.Timestamp:
    """交易日 t 的决策时点：本地收盘 15:00（带时区，严格比较）。"""
    d = pd.Timestamp(day).normalize()
    return d.tz_localize(DECISION_TIMEZONE) + pd.Timedelta(hours=DECISION_HOUR)


def parse_available_at(raw, event_id):
    """available_at 解析为带时区时刻；缺失返回 None；无时区即无法证明时点。"""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    ts = pd.Timestamp(raw)
    if ts.tzinfo is None:
        raise ValueError(
            f"行动 {event_id!r} 的 available_at 不带时区：{raw!r}；"
            "无法证明何时可知"
        )
    return ts


def signal_time_violations(events: list[dict], observations) -> list[dict]:
    """逐事件核对信号时间资格，返回违规清单（每事件记最早受影响观察日）。

    生效日不早于任何观察日的事件不进入任何信号窗口，不算信号违规
    （只可能影响未来目标，由 :func:`target_label_incomplete` 处理）。
    """
    violations: list[dict] = []
    obs_norm = [(pd.Timestamp(t).normalize(), decision_moment(t)) for t in observations]
    for ev in events:
        eid = ev.get("event_id")
        eff = pd.Timestamp(ev["effective_date"]).normalize()
        try:
            av = parse_available_at(ev.get("available_at"), eid)
        except ValueError as exc:
            violations.append({
                "event_id": eid, "effective_date": str(eff.date()),
                "available_at": ev.get("available_at"),
                "observation_date": None, "reason": str(exc),
            })
            continue
        for tn, dm in obs_norm:
            if eff <= tn and (av is None or av > dm):
                violations.append({
                    "event_id": eid, "effective_date": str(eff.date()),
                    "available_at": None if av is None else str(av),
                    "observation_date": str(tn.date()),
                    "reason": (
                        "available_at 未知，无法证明在观察时点可知" if av is None
                        else f"available_at（{av}）晚于观察日 {tn.date()} 的决策时点"
                    ),
                })
                break
    return violations


def target_label_incomplete(events: list[dict], exit_day) -> list[dict]:
    """未来目标标签完整性：[t, x] 内生效的行动须在 x 决策时点前可知。

    返回使该标签尚不完整（未成熟可知）的行动清单；空清单即完整历史标签。
    """
    x = pd.Timestamp(exit_day).normalize()
    xm = decision_moment(x)
    incomplete: list[dict] = []
    for ev in events:
        if pd.Timestamp(ev["effective_date"]).normalize() > x:
            continue
        try:
            av = parse_available_at(ev.get("available_at"), ev.get("event_id"))
        except ValueError as exc:
            incomplete.append({
                "event_id": ev.get("event_id"),
                "available_at": ev.get("available_at"), "reason": str(exc),
            })
            continue
        if av is None or av > xm:
            incomplete.append({
                "event_id": ev.get("event_id"),
                "available_at": None if av is None else str(av),
                "reason": (
                    "available_at 未知" if av is None
                    else f"available_at（{av}）晚于 x={x.date()} 的决策时点"
                ),
            })
    return incomplete
