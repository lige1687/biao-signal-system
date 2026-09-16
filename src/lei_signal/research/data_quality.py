"""研究数据质量校验与按用途裁决。

本轮：`research-data-provenance-2026-09-10`。

与 :func:`lei_signal.data.validation.validate_bars` 的分工
----------------------------------------------------------
``validate_bars`` 做**单个标的的 K 线基础校验**（字段、类型、去重、OHLC 关系、
非正价），本模块不重复它，而是补研究层需要、它不做的部分：

- 跨标的的口径一致性（名义价 / 信号价 / 估值延续价不得混用）；
- 日历覆盖与预热、评价期是否够；
- 公司行动的身份、类型与日期完整性；
- **按用途给出裁决**：可用 / 有条件可用 / 不可用，并给理由。

两条不可让步的规则
------------------
1. **没有合格交易日历时，不把工作日自动当交易日。** 本仓库无真实交易所日历
   （``data/calendar.py`` 的 ``WeekdayCalendar`` 节假日表为空），因此
   ``calendar_authority="none"`` 时，一切依赖「某天是否应该有报价」的判断
   都降级，不做缺失日推断。
2. **没有行动记录 ≠ 已证明没有行动。** 公司行动检查永远输出一条覆盖性未证明
   的提示，不因为文件里没有记录就断言该期间无分红或拆分。

异常只阻断受影响的产品、字段或用途，不拖住独立部分。
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

import pandas as pd

from lei_signal.data.symbols import is_a_share, resolve_symbol

#: 机器用途枚举，复用 definition-standard 1.1.0 §2，不自造。
USES: tuple[str, ...] = (
    "description",
    "ranking",
    "research_signal",
    "attribution",
    "comparison",
    "diagnostic",
)

#: 裁决三档。
USABLE = "usable"
CONDITIONAL = "conditional"
UNUSABLE = "unusable"

#: 严重级别。``block`` 才会让相关用途变成不可用。
INFO = "info"
WARN = "warn"
BLOCK = "block"

#: 允许声明的日历权威等级。**自由字符串是危险的**：
#: 早期实现允许任意字符串，于是只要传 "exchange_official" 而根本不给日历对象，
#: 「无合格日历」告警就消失、裁决直接变成可用，且无任何兜底。
CALENDAR_AUTHORITIES: tuple[str, ...] = (
    "none",                    # 没有合格日历
    "price_dates_reference",   # 仅本机价格日期参考，非交易所日历
    "exchange_official",       # 交易所官方
)

_KNOWN_ACTION_TYPES = ("cash_dividend", "split", "trading_halt")

#: 账户事件（events）独有的字段。原始公司行动（actions）不应带这些。
#: 两者混用会把「账户实际取得的权益」当成「公司公告的行动」，
#: 导致同一笔分红被重复计入或按持仓再乘一次。
_ACCOUNT_EVENT_KEYS = ("account_id", "event", "amount")

#: 各类型必须具备的日期字段（缺失即降级，不猜）。
_REQUIRED_ACTION_DATES: dict[str, tuple[str, ...]] = {
    "cash_dividend": ("effective_date",),
    "split": ("effective_date",),
    "trading_halt": ("effective_date",),
}


@dataclass(frozen=True)
class Finding:
    """一条检查结果。``scope`` 限定它影响谁，用于只阻断受影响部分。"""

    level: str
    code: str
    message: str
    instrument: str | None = None
    field_name: str | None = None
    affects_uses: tuple[str, ...] = ()
    evidence: dict = field(default_factory=dict)
    structural: bool = False
    """是否为「已正确声明的固有属性」而非可修缺陷。

    例：产品池非矩形——部分产品晚于评价期起点上市，这是池子的事实，
    补数据也改不了。把它与「可修缺陷」混在一起，会让裁决永远无法变好、
    因而失去信息量。标记它**不降低**默认闸门：调用方必须显式表示接受。
    """

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "instrument": self.instrument,
            "field": self.field_name,
            "affects_uses": list(self.affects_uses),
            "evidence": self.evidence,
            "structural": self.structural,
        }


@dataclass(frozen=True)
class UseVerdict:
    use: str
    verdict: str
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"use": self.use, "verdict": self.verdict, "reasons": list(self.reasons)}


@dataclass(frozen=True)
class QualityReport:
    findings: tuple[Finding, ...]
    verdicts: tuple[UseVerdict, ...]
    counts: dict

    def blockers_for(self, use: str) -> dict:
        """把压制某用途的原因分成「可修缺陷」与「已声明固有属性」两类。"""
        rel = [
            f for f in self.findings
            if f.level in (BLOCK, WARN) and use in f.affects_uses
        ]
        return {
            "fixable": sorted({f.code for f in rel if not f.structural}),
            "structural": sorted({f.code for f in rel if f.structural}),
        }

    @property
    def blocked_instruments(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    f.instrument
                    for f in self.findings
                    if f.level == BLOCK and f.instrument
                }
            )
        )

    def verdict_for(self, use: str) -> str:
        for v in self.verdicts:
            if v.use == use:
                return v.verdict
        raise KeyError(use)

    def to_dict(self) -> dict:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "verdicts": [v.to_dict() for v in self.verdicts],
            "counts": self.counts,
            "blocked_instruments": list(self.blocked_instruments),
        }


def _verdicts_from(findings: Sequence[Finding]) -> tuple[UseVerdict, ...]:
    """由 findings 推出每个用途的裁决。

    ``block`` → 该用途不可用；``warn`` → 有条件可用；都没有 → 可用。
    """
    out: list[UseVerdict] = []
    for use in USES:
        blocking = [f for f in findings if f.level == BLOCK and use in f.affects_uses]
        warning = [f for f in findings if f.level == WARN and use in f.affects_uses]
        if blocking:
            verdict = UNUSABLE
            reasons = tuple(f"{f.code}: {f.message}" for f in blocking)
        elif warning:
            verdict = CONDITIONAL
            reasons = tuple(f"{f.code}: {f.message}" for f in warning)
        else:
            verdict = USABLE
            reasons = ()
        out.append(UseVerdict(use=use, verdict=verdict, reasons=reasons))
    return tuple(out)


# --------------------------------------------------------------------------
# 价格
# --------------------------------------------------------------------------


def check_prices(
    frames: Mapping[str, pd.DataFrame],
    *,
    declared_basis: Mapping[str, str] | str = "nominal_close",
    calendar_authority: str = "none",
    requested_days: Mapping[str, int] | None = None,
    warmup_rows: int | None = None,
    evaluation_start: str | None = None,
    evaluation_end: str | None = None,
    expected_instruments: Iterable[str] | None = None,
    calendar=None,
    declared_currency: Mapping[str, str] | str | None = None,
    snapshot_basis: str | None = None,
    halts: Sequence[Mapping] | None = None,
    listing_evidence: Mapping[str, Mapping] | None = None,
) -> QualityReport:
    """校验一批标的的日线并按用途裁决。

    ``warmup_rows``
        预热所需的**该标的自身有效报价条数**（混合池月选资格为 273，
        见 ``factor_runtime.py:98``）。由调用方显式传入，不在此硬编码。
    ``calendar_authority``
        ``"none"`` 表示没有合格交易日历——此时不推断缺失交易日。
    """
    for name, value in (("evaluation_start", evaluation_start),
                        ("evaluation_end", evaluation_end)):
        if value is not None and not str(value).strip():
            raise ValueError(
                f"{name} 为空字符串。空串会被当作「没有评价期」静默放过，"
                "语义与 None 不同；请显式传 None 或合法日期"
            )
    if calendar_authority not in CALENDAR_AUTHORITIES:
        raise ValueError(
            f"未知日历权威 {calendar_authority!r}；合法值：{CALENDAR_AUTHORITIES}"
        )
    if calendar_authority != "none" and calendar is None:
        raise ValueError(
            f"声明了 calendar_authority={calendar_authority!r} 却未提供 calendar 对象。"
            "光靠一句字符串不能证明日历存在——请传入实际日历，或声明 'none'"
        )

    findings: list[Finding] = []
    basis_map = (
        {s: declared_basis for s in frames}
        if isinstance(declared_basis, str)
        else dict(declared_basis)
    )

    # --- 来源缺失：声明要有但一条都没有 ---
    if expected_instruments is not None:
        missing = sorted(set(expected_instruments) - set(frames))
        for symbol in missing:
            findings.append(
                Finding(
                    BLOCK,
                    "source_missing",
                    "声明的标的没有任何数据",
                    instrument=symbol,
                    affects_uses=USES,
                )
            )

    # --- 口径跨层核对：调用方的口头声明必须与产物记录一致 ---
    # 早期校验器只信 declared_basis，从不与快照记录的 price_basis 对照，
    # 调用方谎报口径不会被发现。
    if snapshot_basis is not None:
        wrong = sorted({b for b in basis_map.values() if b != snapshot_basis})
        if wrong:
            findings.append(
                Finding(
                    BLOCK,
                    "price_basis_conflict",
                    f"调用方声明的口径 {wrong} 与产物记录的 {snapshot_basis!r} 不一致；"
                    "以产物记录为准，拒绝按口头声明判定",
                    affects_uses=USES,
                    evidence={
                        "declared": basis_map,
                        "snapshot_price_basis": snapshot_basis,
                    },
                )
            )

    # --- 币种混用：快照记了币种，但早期校验器完全不看，混用无人拦 ---
    if declared_currency is not None:
        ccy_map = (
            {s: declared_currency for s in frames}
            if isinstance(declared_currency, str)
            else dict(declared_currency)
        )
        distinct_ccy = sorted({ccy_map.get(s, "unknown") for s in frames})
        if len(distinct_ccy) > 1:
            findings.append(
                Finding(
                    BLOCK,
                    "currency_mixed",
                    f"同一批中混用了不同币种：{distinct_ccy}；"
                    "不同币种的收益不可直接比较或排序",
                    affects_uses=(
                        "ranking", "research_signal", "attribution", "comparison",
                    ),
                    evidence={"currencies": distinct_ccy, "by_instrument": ccy_map},
                )
            )

    # --- 口径混用：名义价 / 信号价 / 估值延续价不得混在同一批比较里 ---
    distinct = sorted(set(basis_map.get(s, "unknown") for s in frames))
    if len(distinct) > 1:
        findings.append(
            Finding(
                BLOCK,
                "price_basis_mixed",
                f"同一批中混用了不同价格口径：{distinct}",
                affects_uses=("ranking", "research_signal", "attribution", "comparison"),
                evidence={"bases": distinct, "by_instrument": basis_map},
            )
        )

    # --- 日历 ---
    if calendar is not None:
        calendar_authority = getattr(calendar, "authority", calendar_authority)
        consumable_halts = halts
        if halts is not None:
            # 直接入口同样适用「验证后才能消费」：非法记录既不得解释缺口，
            # 其混入情况也必须可见。
            consumable_halts, invalid_halt_findings = _validated_halts(
                halts, list(frames)
            )
            findings.extend(invalid_halt_findings)
        findings.extend(
            _check_against_calendar(
                frames, calendar, evaluation_start, evaluation_end,
                halts=consumable_halts,
            )
        )
    if calendar_authority == "none":
        findings.append(
            Finding(
                WARN,
                "no_qualified_calendar",
                "无合格交易日历：不推断缺失交易日，不把工作日当交易日。"
                "跨标的同日对齐与覆盖率分母均无权威依据",
                affects_uses=("ranking", "research_signal", "comparison"),
                evidence={"calendar_authority": calendar_authority},
            )
        )

    for symbol, frame in sorted(frames.items()):
        findings.extend(_check_symbol_convention(symbol))
        findings.extend(
            _check_one_price_frame(
                symbol,
                frame,
                requested=(requested_days or {}).get(symbol),
                warmup_rows=warmup_rows,
                evaluation_start=evaluation_start,
                evaluation_end=evaluation_end,
                calendar_authority=calendar_authority,
                listing_evidence=(listing_evidence or {}).get(symbol),
                calendar=calendar,
            )
        )

    counts = {
        "instruments": len(frames),
        "rows_total": int(sum(len(f) for f in frames.values())),
        "findings_by_level": {
            level: sum(1 for f in findings if f.level == level)
            for level in (INFO, WARN, BLOCK)
        },
    }
    return QualityReport(tuple(findings), _verdicts_from(findings), counts)


class UseNotPermitted(RuntimeError):
    """试图在资料不足的情况下把数据用于某用途。

    存在的意义：让「升级用途」成为一个**必须被显式拒绝**的动作，
    而不是调用方读一眼裁决就自行决定忽略。
    """

    def __init__(self, use: str, verdict: str, reasons: tuple[str, ...]):
        self.use = use
        self.verdict = verdict
        self.reasons = reasons
        detail = "；".join(reasons) if reasons else "无附加原因"
        super().__init__(f"用途 {use!r} 当前裁决为 {verdict}，不予放行。原因：{detail}")


def require_use(
    report: QualityReport,
    use: str,
    *,
    allow_conditional: bool = False,
    accept_structural: bool = False,
    declared_uses: Iterable[str] | None = None,
):
    """请求把本批数据用于 ``use``；不满足即抛 :class:`UseNotPermitted`。

    ``allow_conditional``
        默认 ``False``：有条件可用**也不放行**，必须调用方显式承担条件。
        这样「有条件」不会在传递过程中悄悄变成「可用」。
    ``declared_uses``
        产物自身声明的允许用途（例如快照 ``uses`` 段）。给出时先做交叉核对：
        未被声明的用途一律拒绝，**质量裁决不能覆盖产物的用途声明**。
    ``accept_structural``
        默认 ``False``。置 ``True`` 表示调用方**明确接受**已声明的固有属性
        （例如产品池非矩形），此时只要不存在**可修缺陷**即放行。
        **这不是放宽闸门**，三条同时成立：
        ① 默认行为不变；② 存在任何可修缺陷仍拒绝；
        ③ **裁决为不可用（有 BLOCK 级问题）时一律拒绝**，
        因此把阻断级 finding 标成 structural 也无法绕过。
    """
    if use not in USES:
        raise ValueError(f"未知用途 {use!r}；合法值：{USES}")
    # 交叉核对产物自身声明的允许用途。两套声明（快照 uses 与质量裁决）
    # 早期各自独立、互不核对，曾出现「快照说不可排序、质量报告却放行排序」
    # 而两轮无人发现的情况。
    if declared_uses is not None and use not in set(declared_uses):
        raise UseNotPermitted(
            use,
            "not_declared",
            (
                f"产物自身声明的允许用途为 {sorted(declared_uses)}，不含 {use!r}；"
                "质量裁决不能覆盖产物的用途声明",
            ),
        )
    verdict = report.verdict_for(use)
    reasons = next(v.reasons for v in report.verdicts if v.use == use)
    if verdict == USABLE:
        return verdict
    blockers = report.blockers_for(use)
    # accept_structural 只适用于「有条件」。裁决为不可用时一律拒绝——
    # 否则把 BLOCK 级 finding 标成 structural 就能绕过闸门，那才是真后门。
    if accept_structural and verdict == CONDITIONAL and not blockers["fixable"]:
        return CONDITIONAL
    if verdict == CONDITIONAL and allow_conditional:
        return verdict
    raise UseNotPermitted(use, verdict, reasons)


def _check_against_calendar(
    frames,
    calendar,
    evaluation_start: str | None,
    evaluation_end: str | None,
    halts: Sequence[Mapping] | None = None,
) -> list[Finding]:
    """用已核验日历检查覆盖。

    三个层次分别判断，互不能顶替：
    1. **月份覆盖**：区间内哪些月没取到（未知，不推断）；
    2. **逐日完整**：已取的月里每一天是否都有记录——月份被请求过
       不等于每天都有记录（主控反例：月内漏一天却 complete=True）；
    3. **逐产品覆盖**：全池日期并集完好，不等于每只产品自身连续——
       单产品内部缺日不能被并集掩盖（主控反例：删 510300 一天，
       其他产品仍完整时 findings 完全不变）。

    未知不能被当作休市；缺口不自动等于错误，也不自动等于停牌——
    没有来源证明时一律标 ``cause=unconfirmed``。停牌解释必须
    匹配**具体产品与日期**，不能用「停牌数量够了」解释任意缺失。
    """
    out: list[Finding] = []
    all_dates = sorted({str(d)[:10] for f in frames.values() for d in f.index})
    if not all_dates:
        return out
    start = evaluation_start or all_dates[0]
    end = evaluation_end or all_dates[-1]

    coverage = calendar.coverage(start, end)
    if coverage.missing_months:
        out.append(
            Finding(
                WARN,
                "calendar_coverage_partial",
                f"日历缺 {len(coverage.missing_months)} 个月；"
                "未覆盖区间的缺失日期保持未知，不推断",
                affects_uses=("ranking", "research_signal", "comparison"),
                evidence={
                    "missing_months": coverage.missing_months[:12],
                    "missing_month_count": len(coverage.missing_months),
                },
            )
        )
    if coverage.day_incomplete_months:
        out.append(
            Finding(
                WARN,
                "calendar_days_incomplete",
                f"日历在 {len(coverage.day_incomplete_months)} 个已请求月份内"
                "逐日记录不完整（月份被请求过 ≠ 每天都有记录）；"
                "缺失日保持未知，不当作休市，也不从覆盖率分母消失",
                affects_uses=(
                    "ranking", "research_signal", "comparison", "attribution",
                ),
                evidence={
                    "day_incomplete_months": coverage.day_incomplete_months[:12],
                },
            )
        )

    present = set(all_dates)
    conflicts = [d for d in all_dates if calendar.status(d).status == "closed"]
    if conflicts:
        out.append(
            Finding(
                BLOCK,
                "quote_on_closed_day",
                "日历判定休市的日期却存在报价——来源冲突，须先查明",
                affects_uses=USES,
                evidence={"dates": conflicts[:20], "count": len(conflicts)},
            )
        )
    # 报价存在于日历完全未知的日期：日历连「这是什么日子」都说不出来，
    # 不能静默当作正常（主控反例：月内漏记一天，该日报价照常被判可用）。
    # 只针对「日历声称覆盖的月份内漏记的日」：那是来源的内部不一致。
    # 从未取过的月份由 calendar_coverage_partial 单独处理，不在这里重复报。
    covered_months = set(coverage.covered_months)
    unknown_days = [
        d for d in all_dates
        if start <= d <= end
        and d[:7] in covered_months
        and calendar.status(d).status == "unknown"
    ]
    if unknown_days:
        out.append(
            Finding(
                BLOCK,
                "quote_on_unknown_calendar_day",
                "存在日历完全无法判定的日期上的报价——未知不能被当作休市，"
                "也不能被静默当作正常交易日",
                affects_uses=("ranking", "research_signal", "comparison"),
                evidence={"dates": unknown_days[:20], "count": len(unknown_days)},
            )
        )

    known_trading = list(calendar.trading_days(start, end))
    empty_days = [d for d in known_trading if d not in present]
    if empty_days:
        out.append(
            Finding(
                WARN,
                "trading_day_without_any_quote",
                "日历判定为交易日但整池无报价——数据缺口（非休市）",
                affects_uses=("ranking", "research_signal", "comparison"),
                evidence={"dates": empty_days[:20], "count": len(empty_days)},
            )
        )

    # ---- 逐产品内部缺口：首末有效报价之间的缺失 ----
    # 首次报价之前、最后报价之后的资格另行说明（与上市证据相关，见
    # starts_after_window），此处只查中间。
    halt_index = _halt_index(halts)
    for symbol, frame in sorted(frames.items()):
        if frame is None or frame.empty:
            continue
        idx = pd.to_datetime(frame.index)
        lo, hi = str(idx.min())[:10], str(idx.max())[:10]
        expected = [
            d for d in calendar.trading_days(max(start, lo), min(end, hi))
            if lo <= d <= hi
        ]
        have = {str(d)[:10] for d in idx}
        missing = [d for d in expected if d not in have]
        if not missing:
            continue
        # 按**完整产品身份**匹配，不用前六位截断；解释保留可追溯引用。
        try:
            from lei_signal.research.symbol_identity import parse_identity as _pi

            bare = _pi(symbol, require_registered=False).bare_code
        except Exception:  # noqa: BLE001 - 无法解析即无法匹配，不作解释
            bare = None
        explained = [
            d for d in missing if bare is not None and (bare, d) in halt_index
        ]
        unexplained = [d for d in missing if d not in explained]
        # 与登记的停牌记录逐日匹配的缺口是**已确认的已知事件**，
        # 不是数据质量问题，降级为提示，不计入阻断项。
        # 只有未解释的缺口才保留为警告。
        out.append(
            Finding(
                WARN if unexplained else INFO,
                "product_internal_gap",
                f"产品在自身首末报价之间缺 {len(missing)} 个交易日的报价"
                + (
                    f"，其中 {len(explained)} 天与登记的停牌记录逐日匹配"
                    if explained
                    else ""
                )
                + "；不自动等于数据错误，也不自动等于停牌",
                instrument=symbol,
                affects_uses=("ranking", "research_signal", "comparison"),
                evidence={
                    "dates": unexplained[:20],
                    "count": len(unexplained),
                    "explained_by_halt": explained[:20],
                    "explained_count": len(explained),
                    "explained_by": [
                        {"date": d, "event_id": halt_index.get((bare, d))}
                        for d in explained[:20]
                    ],
                    "cause": "unconfirmed" if unexplained else "halt",
                    "note": (
                        "首次报价之前、最后报价之后的资格与上市证据相关，"
                        "不在本检查范围；停牌解释只说明数据缺口来源，"
                        "不等于当时可交易"
                    ),
                },
            )
        )
    return out


def check_snapshot(
    loaded,
    *,
    calendar=None,
    actions: Sequence[Mapping] | None = None,
    warmup_rows: int | None = None,
    evaluation_start: str | None = None,
    evaluation_end: str | None = None,
    listing_evidence: Mapping[str, Mapping] | None = None,
) -> QualityReport:
    """从**快照自身**派生口径、币种与字段，再做校验。

    存在的理由：前轮自查反复出现同一类缺陷——「某个字段由调用方口头声明、
    从未与产物记录核对」。本函数不接受口径与币种参数，一律从快照读，
    从结构上掐掉这条路。需要故意传入不一致的值做测试时，直接用
    :func:`check_prices`。

    **完整性是前置闸门**：``loaded.verified`` 为 ``False`` 时，
    所有用途一律不可用（``snapshot_integrity_failed``），
    核验失败不能被重新标为正常可用；``allow_conditional`` 与
    ``accept_structural`` 都绕不过它（该 finding 是 BLOCK 且非结构属性）。
    查看坏数据以排查问题仍保留（``load_snapshot`` 本身不抛错），
    但不得经本入口混成正常研究使用。
    """
    integrity: list[Finding] = []
    if not getattr(loaded, "verified", False):
        integrity.append(
            Finding(
                BLOCK,
                "snapshot_integrity_failed",
                "快照完整性核验失败（哈希不一致或字段结构不符），"
                "该批数据不得进入任何正常研究用途；"
                "请用 load_snapshot 查看差异定位问题后重新取得",
                affects_uses=USES,
                evidence={
                    "hash_mismatches": list(
                        getattr(loaded, "hash_mismatches", ())
                    ),
                    "verified": getattr(loaded, "verified", None),
                },
            )
        )
    sem = loaded.snapshot["semantics"]
    # 行动**先核验**，只有未被判 BLOCK 的记录才允许参与缺口解释——
    # 非法身份、账户事件混入、冲突重复、非法停牌区间都不能先被消费。
    actions_report: QualityReport | None = None
    valid_halts: list[Mapping] | None = None
    if actions is not None:
        actions_list = list(actions)
        actions_report = check_actions(
            actions_list, declared_symbols=list(loaded.frames)
        )
        blocked = {
            f.evidence["index"]
            for f in actions_report.findings
            if f.level == BLOCK and isinstance(f.evidence, dict) and "index" in f.evidence
        }
        # 同一 event_id 出现冲突内容时，该 ID 下**所有**记录都不可信——
        # 不能只排除后被抓到的那一条。
        blocked_event_ids = {
            f.evidence["event_id"]
            for f in actions_report.findings
            if f.level == BLOCK
            and isinstance(f.evidence, dict)
            and f.evidence.get("event_id")
        }
        valid_halts = [
            a
            for i, a in enumerate(actions_list)
            if a.get("type") == "trading_halt"
            and i not in blocked
            and a.get("event_id") not in blocked_event_ids
        ]
    report = check_prices(
        loaded.frames,
        declared_basis=sem["price_basis"],
        snapshot_basis=sem["price_basis"],
        declared_currency=sem["currency"],
        calendar=calendar,
        calendar_authority=(
            getattr(calendar, "authority", "none") if calendar is not None else "none"
        ),
        warmup_rows=warmup_rows,
        evaluation_start=evaluation_start,
        evaluation_end=evaluation_end,
        halts=valid_halts,
        listing_evidence=listing_evidence,
    )
    if actions_report is not None:
        report = merge_reports(report, actions_report)
    if integrity:
        report = merge_reports(
            QualityReport(tuple(integrity), _verdicts_from(tuple(integrity)), {}),
            report,
        )
    return report


def _validated_halts(
    halts: Sequence[Mapping],
    declared_symbols: Iterable[str],
) -> tuple[list[Mapping], list[Finding]]:
    """验证后才能消费：对直接入口传入的停牌记录做与 `check_snapshot` 同源
    的核验，返回（可参与缺口解释的记录，非法记录的 BLOCK 级发现）。

    返回的发现只保留与**记录有效性**直接相关的 BLOCK 项；
    文件级的时间知识提示（`coverage_unproven`、`action_available_at_unknown`）
    不属于"该条停牌能否解释缺口"，不在此重复。
    合法停牌缺少 `available_at` 不阻碍其解释缺口（历史时点未知另行声明，
    不得补造）。
    """
    actions_list = list(halts)
    report = check_actions(actions_list, declared_symbols=list(declared_symbols))
    noise = {"coverage_unproven", "action_available_at_unknown",
             "action_announcement_lower_bound_available"}
    blocked_indices = {
        f.evidence["index"]
        for f in report.findings
        if f.level == BLOCK and isinstance(f.evidence, dict) and "index" in f.evidence
    }
    blocked_event_ids = {
        f.evidence["event_id"]
        for f in report.findings
        if f.level == BLOCK and isinstance(f.evidence, dict)
        and f.evidence.get("event_id")
    }
    valid = [
        a for i, a in enumerate(actions_list)
        if a.get("type") == "trading_halt"
        and i not in blocked_indices
        and a.get("event_id") not in blocked_event_ids
    ]
    invalid_findings = [
        f for f in report.findings if f.level == BLOCK and f.code not in noise
    ]
    return valid, invalid_findings


def _halt_index(
    halts: Sequence[Mapping] | None,
) -> dict[tuple[str, str], str]:
    """把**已核验合格**的停牌记录展开为 ``{(裸码, 日期): event_id}``。

    只接受调用方已经验证过的记录；本函数再做两道防线：
    - 产品符号用完整身份解析（带后缀走 ``parse_identity``，裸六位码
      要求在登记表中有唯一映射），**不再用前六位截断**；
    - ``halt.start_date`` / ``end_date`` 必须是真实有效日期且 ``start <= end``。

    任何一项不满足即整条跳过——无效记录不得作为解释缺口的证据。
    值保留 ``event_id``，使解释可追溯。
    """
    from datetime import date, timedelta

    from lei_signal.research.symbol_identity import (
        REGISTERED_PRODUCTS,
        IdentityError,
        parse_identity,
    )

    out: dict[tuple[str, str], str] = {}
    if not halts:
        return out
    for h in halts:
        if h.get("type") != "trading_halt":
            continue
        token = str(h.get("symbol") or "").strip()
        bare: str | None = None
        if "." in token:
            try:
                bare = parse_identity(token, require_registered=False).bare_code
            except IdentityError:
                continue
        elif token.isdigit() and len(token) == 6 and token in REGISTERED_PRODUCTS:
            bare = token
        if bare is None:
            continue
        info = h.get("halt") or {}
        start = str(info.get("start_date") or h.get("effective_date") or "")
        end = str(info.get("end_date") or start)
        try:
            d0 = date.fromisoformat(start[:10])
            d1 = date.fromisoformat(end[:10])
        except ValueError:
            continue
        if len(start) < 10 or len(end) < 10 or d0 > d1:
            continue
        event_id = str(h.get("event_id") or "")
        d = d0
        while d <= d1:
            out[(bare, d.isoformat())] = event_id
            d += timedelta(days=1)
    return out


def _check_symbol_convention(symbol: str) -> list[Finding]:
    """产品代码是否符合本仓库的规范写法。

    实测背景：冻结输入 ``prices.csv`` 用 ``510300.SH``，而本仓库
    ``data/symbols.py::resolve_symbol`` 的规范形式是 ``510300.SS``，``.SH``
    会被判为 ``other`` / 非 A 股。两套写法各自内部自洽，但**按代码 join 时
    会得到空交集且不报错**——属于静默污染路径，必须显式告警。
    """
    try:
        info = resolve_symbol(symbol)
    except Exception as exc:  # noqa: BLE001 - 解析失败本身就是发现
        return [
            Finding(
                BLOCK,
                "symbol_unresolvable",
                f"产品代码无法解析：{exc}",
                instrument=symbol,
                affects_uses=USES,
            )
        ]
    if not is_a_share(info):
        return [
            Finding(
                WARN,
                "symbol_convention_mismatch",
                f"{symbol!r} 不被本仓库 resolve_symbol 判为 A 股"
                f"（解析为 {info.symbol!r}/{info.market}）。若与仓库口径数据"
                "按代码合并会得到空交集且不报错，须先统一写法",
                instrument=symbol,
                affects_uses=("ranking", "comparison", "attribution"),
                evidence={
                    "given": symbol,
                    "resolved": info.symbol,
                    "market": str(info.market),
                    "repo_canonical_example": "510300.SS",
                },
            )
        ]
    if info.symbol != symbol:
        return [
            Finding(
                INFO,
                "symbol_normalized",
                f"{symbol!r} 规范化为 {info.symbol!r}",
                instrument=symbol,
                evidence={"given": symbol, "resolved": info.symbol},
            )
        ]
    return []


def _check_listing_dates(
    listing: object, *, window_start: str, first_quote: str, calendar
) -> dict:
    """日期与窗口自洽的**独立算法诊断**——不代表来源资格。"""
    if not listing:
        return {"outcome": "missing_listing_date",
                "detail": "证据缺少 listing_date"}
    try:
        from datetime import date as _d

        listing_day = _d.fromisoformat(str(listing)[:10])
        if len(str(listing)) != 10:
            raise ValueError
    except ValueError:
        return {"outcome": "bad_date",
                "detail": f"listing_date 不是合法日期：{listing!r}"}
    if str(listing_day) < window_start:
        return {
            "outcome": "earlier_than_window",
            "detail": f"上市日期 {listing_day} 早于评价期起点 {window_start}；"
            "评价期前已上市不能解释评价期后才有报价",
        }
    if str(listing_day) > first_quote:
        return {"outcome": "after_first_quote",
                "detail": f"上市日期 {listing_day} 晚于首个报价 {first_quote}，自相矛盾"}
    if calendar is None:
        return {"outcome": "no_calendar",
                "detail": "无日历可核上市至首报价之间的残余缺口，按未确认处理"}
    # 残余 = 上市日（含当天，若当天开市）至首个报价之间的应有报价日。
    # 上市当天是否具备报价资格未知，不得仅因隔着周末就忽略当天。
    residual = [
        d
        for d in calendar.trading_days(str(listing_day), first_quote)
        if d != first_quote
    ]
    if residual:
        return {
            "outcome": "residual",
            "detail": f"上市 {listing_day} 至首个报价 {first_quote} 之间仍有 "
            f"{len(residual)} 个应有报价日未解释（如 {residual[:5]}）；"
            "残余缺口不得整体免除",
            "residual_days": residual[:10],
        }
    return {"outcome": "coherent",
            "detail": "上市日期与评价期/首报价/残余缺口自洽"}


def _verify_listing_source(evidence: Mapping, *, symbol: str) -> dict:
    """来源可回查性核验。

    哈希一致只证明「读到的字节与引用的字节一致」，**不证明文件内容为真**——
    能写文件、算哈希、填日期的是同一个调用方时，三者一致也不构成独立可信来源。

    自述/合成记录最高只能标记为 ``synthetic`` 或 ``unverified``：
    当前**未建立真实资料准入标准**，没有任何记录获得真实研究资格
    （``qualified`` 恒为 ``False``）。不得通过新增可信标签、白名单或
    调用方自填标记绕过这一点；真实资料的准入是另行授权事项。
    """
    source = evidence.get("source")
    if not isinstance(source, Mapping):
        return {
            "outcome": "not_reference",
            "qualified": False,
            "detail": f"来源未核验：{source!r} 不是可回查的引用"
            "（须为 {path, sha256} 且内容一致）；日期与窗口关系成立不代替来源核验",
        }
    path = source.get("path")
    expected_sha = source.get("sha256")
    if not isinstance(path, str) or not path.strip():
        return {"outcome": "missing_path", "qualified": False,
                "detail": "来源未核验：引用缺少 path"}
    if not (
        isinstance(expected_sha, str)
        and len(expected_sha) == 64
        and all(c in "0123456789abcdef" for c in expected_sha)
    ):
        return {"outcome": "bad_sha256", "qualified": False,
                "detail": "来源未核验：引用缺少合法的 sha256（64 位十六进制）"}
    import hashlib
    import json as _json
    from pathlib import Path as _Path

    doc_path = _Path(path)
    if not doc_path.is_file():
        return {"outcome": "file_missing", "qualified": False,
                "detail": f"来源未核验：引用文件不存在 {path}"}
    actual_sha = hashlib.sha256(doc_path.read_bytes()).hexdigest()
    if actual_sha != expected_sha:
        return {"outcome": "hash_mismatch", "qualified": False,
                "detail": "来源未核验：引用内容哈希不匹配（内容已变化，"
                "不得沿用旧核验结论）"}
    try:
        doc = _json.loads(doc_path.read_text(encoding="utf-8"))
    except _json.JSONDecodeError:
        return {"outcome": "not_json", "qualified": False,
                "detail": "来源未核验：引用文件不是合法 JSON"}
    from lei_signal.research.symbol_identity import IdentityError, parse_identity

    try:
        bare = parse_identity(symbol, require_registered=False).bare_code
    except IdentityError:
        bare = None
    doc_symbol = doc.get("symbol")
    if bare is None or doc_symbol != bare:
        return {"outcome": "product_mismatch", "qualified": False,
                "detail": f"来源未核验：引用记录的产品 {doc_symbol!r} "
                f"与证据所属产品 {bare!r} 不符"}
    if doc.get("listing_date") != evidence.get("listing_date"):
        return {"outcome": "date_mismatch", "qualified": False,
                "detail": f"来源未核验：引用记录的上市日期 "
                f"{doc.get('listing_date')!r} 与声明的 "
                f"{evidence.get('listing_date')!r} 不符"}
    qualification = doc.get("qualification")
    if qualification == "synthetic_algorithm_test":
        return {
            "outcome": "synthetic",
            "qualified": False,
            "synthetic": True,
            "detail": "来源为显式标注的合成记录，仅用于算法诊断；"
            "自述/合成记录不获得真实研究资格"
            "（当前未建立真实资料准入标准）",
        }
    return {
        "outcome": "unverified",
        "qualified": False,
        "detail": f"来源的资格状态无法确认（qualification={qualification!r}）；"
        "未声明或被省略不等于真实来源已核验，"
        "自述值如 official/verified 同样不构成资格",
    }


def _validate_listing_evidence(
    evidence: Mapping | None,
    *,
    symbol: str,
    window_start: str,
    first_quote: str,
    calendar,
) -> dict:
    """把「日期算法自洽」与「可用于真实研究的证据资格」彻底分开。

    - ``dates``：独立的日期诊断（同日/早于评价期/残余缺口……），
      可用于算法验证；
    - ``source``：来源可回查性与资格状态。哈希一致只证明字节一致，
      不证明内容为真；自述/合成记录一律不获得真实资格。

    ``structural`` 只有在来源**确实取得真实研究资格**且日期自洽时才可为
    ``True``。当前未建立真实资料准入标准，因此**任何输入都不会产生
    ``structural=True``**——``starts_after_window`` 的原因一律保留为
    未确认。这不抛错、不关闭算法诊断路径。
    """
    fail = lambda reason, dates=None, source=None: {  # noqa: E731
        "structural": False,
        "reason": reason,
        "dates": dates or {"outcome": "missing"},
        "source": source or {"outcome": "missing"},
        "synthetic": False,
    }
    if not evidence:
        return fail("缺少上市资格证据")
    if not isinstance(evidence, Mapping):
        return fail("证据不是结构化的映射")

    dates = _check_listing_dates(
        evidence.get("listing_date"),
        window_start=window_start,
        first_quote=first_quote,
        calendar=calendar,
    )
    source = _verify_listing_source(evidence, symbol=symbol)
    synthetic = bool(source.get("synthetic"))

    if not source.get("qualified"):
        if dates["outcome"] == "coherent":
            reason = f"日期算法自洽，但{source['detail']}"
        else:
            reason = f"{dates['detail']}；且{source['detail']}"
        return {
            "structural": False,
            "reason": reason,
            "dates": dates,
            "source": source,
            "synthetic": synthetic,
        }
    # 当前没有任何路径能到达这里：真实资料准入标准未建立。
    # 不删除这段结构是为了让「资格」与「日期」的汇合点显式可见，
    # 而不是留一个调用方可填的开关。
    return {
        "structural": False,
        "reason": "真实资料准入标准未建立；自述/合成记录不获得真实研究资格",
        "dates": dates,
        "source": source,
        "synthetic": synthetic,
    }


def _check_one_price_frame(
    symbol: str,
    frame: pd.DataFrame,
    *,
    requested: int | None,
    warmup_rows: int | None,
    evaluation_start: str | None,
    evaluation_end: str | None,
    calendar_authority: str,
    listing_evidence: Mapping | None = None,
    calendar=None,
) -> list[Finding]:
    out: list[Finding] = []

    if frame is None or frame.empty:
        return [
            Finding(
                BLOCK,
                "empty_frame",
                "没有任何报价行",
                instrument=symbol,
                affects_uses=USES,
            )
        ]

    idx = pd.to_datetime(frame.index)

    # 日期顺序
    if not idx.is_monotonic_increasing:
        out.append(
            Finding(
                BLOCK,
                "dates_not_sorted",
                "日期非递增",
                instrument=symbol,
                affects_uses=USES,
            )
        )

    # 重复行与重复冲突：同日多行且内容不同 = 冲突（比单纯重复更严重）
    dup_mask = idx.duplicated(keep=False)
    if dup_mask.any():
        dup_dates = sorted({str(d.date()) for d in idx[dup_mask]})
        conflicting = []
        for d in pd.DatetimeIndex(sorted(set(idx[dup_mask]))):
            rows = frame.loc[frame.index == d]
            if len(rows.drop_duplicates()) > 1:
                conflicting.append(str(d.date()))
        if conflicting:
            out.append(
                Finding(
                    BLOCK,
                    "duplicate_conflict",
                    "同一日期存在内容不同的多行，无法判定哪一行为准",
                    instrument=symbol,
                    affects_uses=USES,
                    evidence={"dates": conflicting[:20], "count": len(conflicting)},
                )
            )
        else:
            out.append(
                Finding(
                    WARN,
                    "duplicate_rows",
                    "存在完全重复的日期行",
                    instrument=symbol,
                    affects_uses=("ranking", "research_signal", "attribution"),
                    evidence={"dates": dup_dates[:20], "count": len(dup_dates)},
                )
            )

    # 数值：非有限、非正价、OHLC 关系
    price_cols = [c for c in ("open", "high", "low", "close") if c in frame.columns]
    for col in price_cols:
        values = pd.to_numeric(frame[col], errors="coerce")
        nonfinite = values.map(lambda v: not math.isfinite(v) if pd.notna(v) else True)
        if bool(nonfinite.any()):
            out.append(
                Finding(
                    BLOCK,
                    "non_finite_value",
                    "存在非有限数（NaN/inf）",
                    instrument=symbol,
                    field_name=col,
                    affects_uses=USES,
                    evidence={
                        "count": int(nonfinite.sum()),
                        "first_date": str(idx[nonfinite.to_numpy()][0].date()),
                    },
                )
            )
        finite = values[values.map(lambda v: pd.notna(v) and math.isfinite(v))]
        if (finite <= 0).any():
            out.append(
                Finding(
                    BLOCK,
                    "non_positive_price",
                    "存在非正价格",
                    instrument=symbol,
                    field_name=col,
                    affects_uses=USES,
                    evidence={"count": int((finite <= 0).sum())},
                )
            )

    if {"open", "high", "low", "close"} <= set(frame.columns):
        hi, lo = frame["high"], frame["low"]
        bad = (
            (hi < lo)
            | (hi < frame["close"])
            | (lo > frame["close"])
            | (hi < frame["open"])
            | (lo > frame["open"])
        )
        if bool(bad.any()):
            out.append(
                Finding(
                    BLOCK,
                    "ohlc_relation",
                    "OHLC 关系非法",
                    instrument=symbol,
                    affects_uses=USES,
                    evidence={
                        "count": int(bad.sum()),
                        "first_date": str(idx[bad.to_numpy()][0].date()),
                    },
                )
            )

    # 成交量异常：零量可能是停牌或无成交，单列不当错误
    if "volume" in frame.columns:
        vol = pd.to_numeric(frame["volume"], errors="coerce")
        if (vol < 0).any():
            out.append(
                Finding(
                    BLOCK,
                    "negative_volume",
                    "存在负成交量",
                    instrument=symbol,
                    field_name="volume",
                    affects_uses=USES,
                    evidence={"count": int((vol < 0).sum())},
                )
            )
        zero_days = int((vol == 0).sum())
        if zero_days:
            out.append(
                Finding(
                    WARN,
                    "zero_volume_days",
                    "存在零成交量日（可能停牌或无成交，本轮不区分——"
                    "无停牌数据源可核）",
                    instrument=symbol,
                    field_name="volume",
                    affects_uses=("research_signal", "attribution"),
                    evidence={"days": zero_days},
                )
            )

    # 覆盖：请求 vs 实际
    if requested is not None and len(frame) < requested:
        out.append(
            Finding(
                WARN,
                "coverage_short",
                f"实际 {len(frame)} 行少于请求的 {requested} 行",
                instrument=symbol,
                affects_uses=("ranking", "research_signal", "comparison"),
                evidence={"requested": requested, "actual": int(len(frame))},
            )
        )

    # 预热
    if warmup_rows is not None and len(frame) < warmup_rows:
        out.append(
            Finding(
                BLOCK,
                "warmup_insufficient",
                f"有效报价 {len(frame)} 条不足预热所需 {warmup_rows} 条",
                instrument=symbol,
                affects_uses=("ranking", "research_signal", "attribution"),
                evidence={"rows": int(len(frame)), "required": warmup_rows},
            )
        )

    # 评价期：只在有权威日历时才谈「缺了哪些交易日」
    if evaluation_start or evaluation_end:
        start = pd.Timestamp(evaluation_start) if evaluation_start else idx.min()
        end = pd.Timestamp(evaluation_end) if evaluation_end else idx.max()
        inside = int(((idx >= start) & (idx <= end)).sum())
        if inside == 0:
            out.append(
                Finding(
                    BLOCK,
                    "evaluation_window_empty",
                    "评价期内没有任何报价",
                    instrument=symbol,
                    affects_uses=USES,
                    evidence={"start": str(start.date()), "end": str(end.date())},
                )
            )
        else:
            if idx.min() > start:
                # 「首个报价较晚」不能自动判为「晚上市、补不了的固有属性」。
                # 只有拿到该产品的上市资格证据（由调用方按产品传入）时才允许
                # 标为结构属性；否则保留未知，accept_structural 不得放行。
                verdict = _validate_listing_evidence(
                    listing_evidence,
                    symbol=symbol,
                    window_start=str(start.date()),
                    first_quote=str(idx.min().date()),
                    calendar=calendar,
                )
                out.append(
                    Finding(
                        WARN,
                        "starts_after_window",
                        (
                            "首个报价晚于评价期起点，且上市资格证据自洽，"
                            "属产品池固有属性；跨该期比较须自行处理可比性"
                            if verdict["structural"]
                            else "首个报价晚于评价期起点；"
                            f"{verdict['reason']}——不得自动判为晚上市"
                        ),
                        instrument=symbol,
                        affects_uses=("ranking", "comparison"),
                        evidence={
                            "first_date": str(idx.min().date()),
                            "window_start": str(start.date()),
                            "listing_evidence": dict(listing_evidence)
                            if listing_evidence
                            else None,
                            "cause": "listed_late"
                            if verdict["structural"]
                            else "unconfirmed",
                            "evidence_check": verdict,
                        },
                        structural=verdict["structural"],
                    )
                )
            if calendar_authority == "none":
                out.append(
                    Finding(
                        INFO,
                        "coverage_denominator_unknown",
                        "无权威日历，评价期覆盖率没有可信分母，只报绝对条数",
                        instrument=symbol,
                        evidence={"rows_in_window": inside},
                    )
                )
    return out


# --------------------------------------------------------------------------
# 公司行动
# --------------------------------------------------------------------------


def check_actions(
    actions: Sequence[Mapping],
    *,
    declared_symbols: Iterable[str] | None = None,
    require_available_at: bool = False,
) -> QualityReport:
    """校验公司行动的身份、类型、日期与每份金额/比例。

    永远输出一条 ``coverage_unproven``：**没有行动记录不等于已证明没有行动。**
    """
    findings: list[Finding] = []
    # 早期实现用 s[:6] 截断，前六位相同的不同产品会被认成同一只。
    # 改用身份模块解析出裸码；无法解析即报错，不猜。
    declared: set[str] | None = None
    if declared_symbols:
        from lei_signal.research.symbol_identity import (
            IdentityError,
            parse_identity,
        )

        declared = set()
        for s in declared_symbols:
            try:
                declared.add(parse_identity(s, require_registered=False).bare_code)
            except IdentityError as exc:
                raise ValueError(
                    f"declared_symbols 中的 {s!r} 无法解析为产品身份：{exc}"
                ) from exc

    seen: dict[str, Mapping] = {}
    without_available_at = 0
    with_announcement_lower_bound = 0
    by_type: dict[str, int] = {}

    from lei_signal.research.symbol_identity import (
        REGISTERED_PRODUCTS,
        IdentityError,
        parse_identity,
    )

    def _action_identity(symbol: object) -> tuple[str | None, Finding | None]:
        """把行动的产品符号解析为裸码；任何不确定都拒绝，不猜。

        - ``None`` / 空 → ``action_missing_identity``
        - 带后缀形式 → 完整身份解析；与登记表冲突即拒绝
        - 裸六位码 → 仅当它在登记表中**唯一映射**到一只产品时才接受
          （本批行动文件的明确来源约定）；查无此码即拒绝
        """
        if symbol is None or (isinstance(symbol, str) and not symbol.strip()):
            return None, Finding(
                BLOCK, "action_missing_identity",
                "公司行动缺少产品符号，无法建立身份",
                affects_uses=("attribution", "research_signal"),
            )
        token = str(symbol).strip()
        if "." in token:
            try:
                ident = parse_identity(token, require_registered=False)
            except IdentityError as exc:
                return None, Finding(
                    BLOCK, "action_identity_conflict",
                    f"产品符号无法解析：{exc}",
                    instrument=token,
                    affects_uses=("attribution", "research_signal"),
                )
            registered_exchange = REGISTERED_PRODUCTS.get(ident.bare_code)
            if registered_exchange and registered_exchange != ident.exchange:
                return None, Finding(
                    BLOCK, "action_identity_conflict",
                    f"{token!r} 的后缀指向 {ident.exchange}，但登记表记录 "
                    f"{ident.bare_code} 属于 {registered_exchange}",
                    instrument=token,
                    affects_uses=("attribution", "research_signal"),
                )
            if declared is not None and ident.bare_code not in declared:
                return ident.bare_code, Finding(
                    BLOCK, "action_symbol_not_declared",
                    "行动所属产品不在声明池内",
                    instrument=token, affects_uses=("attribution",),
                )
            return ident.bare_code, None
        if token.isdigit() and len(token) == 6:
            if token not in REGISTERED_PRODUCTS:
                return None, Finding(
                    BLOCK, "action_symbol_not_declared",
                    f"裸码 {token!r} 在登记表中无唯一映射，不接受猜测",
                    instrument=token,
                    affects_uses=("attribution", "research_signal"),
                )
            if declared is not None and token not in declared:
                return token, Finding(
                    BLOCK, "action_symbol_not_declared",
                    "行动所属产品不在声明池内",
                    instrument=token, affects_uses=("attribution",),
                )
            return token, None
        return None, Finding(
            BLOCK, "action_identity_conflict",
            f"产品符号 {token!r} 既非带后缀身份也非六位裸码",
            instrument=token,
            affects_uses=("attribution", "research_signal"),
        )

    def _valid_day(value: object) -> bool:
        if not isinstance(value, str) or len(value) != 10:
            return False
        from datetime import date as _d

        try:
            _d.fromisoformat(value)
            return True
        except ValueError:
            return False

    def _available_at_ok(value: object) -> bool:
        """available_at 必须是**带时区**的合法时刻。"""
        if not isinstance(value, str) or not value.strip():
            return False
        from datetime import datetime

        try:
            parsed = datetime.fromisoformat(value.strip())
        except ValueError:
            return False
        return parsed.tzinfo is not None

    for i, action in enumerate(actions):
        eid = action.get("event_id")
        atype = action.get("type")
        bare, identity_finding = _action_identity(action.get("symbol"))
        symbol = action.get("symbol")
        where = {"index": i, "event_id": eid, "symbol": symbol, "type": atype}

        # events（账户权益）不得混作 actions（原始公司行动）
        leaked = sorted(k for k in _ACCOUNT_EVENT_KEYS if k in action)
        if leaked:
            findings.append(
                Finding(
                    BLOCK, "events_passed_as_actions",
                    f"记录带有账户事件字段 {leaked}，这是 events（账户实际取得的权益），"
                    "不是 actions（原始公司行动）。两者不得混用",
                    instrument=symbol,
                    affects_uses=("attribution", "research_signal"),
                    evidence={**where, "account_event_keys": leaked},
                )
            )
            continue

        if identity_finding is not None:
            findings.append(
                Finding(
                    identity_finding.level, identity_finding.code,
                    identity_finding.message,
                    instrument=identity_finding.instrument,
                    affects_uses=identity_finding.affects_uses,
                    evidence=where,
                )
            )
            if identity_finding.level == BLOCK:
                continue

        # event_id：唯一身份的底线
        if not eid:
            findings.append(
                Finding(
                    BLOCK, "action_missing_id",
                    "公司行动缺少 event_id，无法建立唯一身份",
                    instrument=symbol,
                    affects_uses=("attribution", "research_signal"),
                    evidence=where,
                )
            )
            continue
        if eid in seen:
            same = dict(seen[eid]) == dict(action)
            findings.append(
                Finding(
                    BLOCK,
                    "action_duplicate_id" if same else "action_conflicting_id",
                    "重复的 event_id" + ("" if same else "，且内容冲突"),
                    instrument=symbol,
                    affects_uses=("attribution", "research_signal"),
                    evidence=where,
                )
            )
            continue
        seen[eid] = action
        by_type[atype] = by_type.get(atype, 0) + 1

        if atype not in _KNOWN_ACTION_TYPES:
            findings.append(
                Finding(
                    WARN, "action_unknown_type",
                    f"未声明的行动类型 {atype!r}，本轮不解释其含义",
                    instrument=symbol, affects_uses=("attribution",),
                    evidence=where,
                )
            )

        # 日期字段：区分缺失与非法格式
        for date_field in _REQUIRED_ACTION_DATES.get(atype, ()):
            value = action.get(date_field)
            if not value:
                findings.append(
                    Finding(
                        BLOCK, "action_missing_date",
                        f"缺少必需日期字段 {date_field}",
                        instrument=symbol, field_name=date_field,
                        affects_uses=("attribution",), evidence=where,
                    )
                )
            elif not _valid_day(value):
                findings.append(
                    Finding(
                        BLOCK, "action_bad_date",
                        f"{date_field} 不是真实有效日期：{value!r}",
                        instrument=symbol, field_name=date_field,
                        affects_uses=("attribution", "research_signal"),
                        evidence=where,
                    )
                )
        for optional in ("record_date", "ex_date", "pay_date", "announcement_date"):
            value = action.get(optional)
            if value and not _valid_day(value):
                findings.append(
                    Finding(
                        BLOCK, "action_bad_date",
                        f"{optional} 不是真实有效日期：{value!r}",
                        instrument=symbol, field_name=optional,
                        affects_uses=("attribution", "research_signal"),
                        evidence=where,
                    )
                )

        # available_at：区分缺失、非法格式、生效后取得
        raw_available = action.get("available_at")
        if raw_available and not _available_at_ok(raw_available):
            findings.append(
                Finding(
                    BLOCK, "action_available_at_bad_format",
                    f"available_at 不是带时区的合法时刻：{raw_available!r}；"
                    "require_available_at 也不能让它变得合法",
                    instrument=symbol, field_name="available_at",
                    affects_uses=("attribution", "research_signal"),
                    evidence=where,
                )
            )
        elif raw_available and action.get("effective_date") and (
            str(raw_available)[:10] > str(action["effective_date"])[:10]
        ):
            findings.append(
                Finding(
                    INFO, "action_acquired_after_effective",
                    "available_at 晚于生效日：属生效后取得，可用于注明修订性质的"
                    "历史重建，但不证明生效日之前已可知",
                    instrument=symbol, evidence=where,
                )
            )

        # 金额与比例
        if atype == "cash_dividend":
            cash = action.get("cash_per_unit", action.get("cash"))
            if cash is None:
                findings.append(
                    Finding(
                        BLOCK, "action_missing_amount",
                        "现金分红缺少每份金额；不接受未声明字段代替",
                        instrument=symbol, affects_uses=("attribution",),
                        evidence=where,
                    )
                )
            elif not (isinstance(cash, int | float) and math.isfinite(cash) and cash >= 0):
                findings.append(
                    Finding(
                        BLOCK, "action_bad_amount",
                        f"每份现金金额非法：{cash!r}",
                        instrument=symbol, affects_uses=("attribution",),
                        evidence=where,
                    )
                )
        if atype == "split":
            ratio = action.get("split_ratio", action.get("ratio"))
            if not (
                isinstance(ratio, int | float) and math.isfinite(ratio) and ratio > 0
            ):
                findings.append(
                    Finding(
                        BLOCK, "action_bad_ratio",
                        f"拆分比例非法：{ratio!r}",
                        instrument=symbol, affects_uses=("attribution",),
                        evidence=where,
                    )
                )
        if atype == "trading_halt":
            # 停牌实际生效的区间在嵌套 halt 里，不能只验顶层 effective_date。
            info = action.get("halt") or {}
            h_start = info.get("start_date")
            h_end = info.get("end_date")
            h_resume = info.get("resume_date")
            for field, value in (("halt.start_date", h_start),
                                 ("halt.end_date", h_end),
                                 ("halt.resume_date", h_resume)):
                if value and not _valid_day(value):
                    findings.append(
                        Finding(
                            BLOCK, "action_bad_date",
                            f"{field} 不是真实有效日期：{value!r}",
                            instrument=symbol, field_name=field,
                            affects_uses=("attribution", "research_signal"),
                            evidence=where,
                        )
                    )
            if h_start and h_end and _valid_day(h_start) and _valid_day(h_end) and (
                str(h_start) > str(h_end)
            ):
                findings.append(
                    Finding(
                        BLOCK, "action_bad_halt_range",
                        f"停牌区间倒置：start={h_start} > end={h_end}",
                        instrument=symbol,
                        affects_uses=("attribution", "research_signal"),
                        evidence=where,
                    )
                )
            if not h_start or not h_end:
                findings.append(
                    Finding(
                        BLOCK, "action_missing_date",
                        "停牌记录缺少 halt.start_date 或 halt.end_date",
                        instrument=symbol, field_name="halt",
                        affects_uses=("attribution",),
                        evidence=where,
                    )
                )

        if not action.get("available_at"):
            without_available_at += 1
            # 公告日期是「不晚于该日已公布」的下界证据，不是精确到达时刻。
            # 只统计与报告，**绝不**写进 available_at 冒充精确时点。
            if action.get("announcement_date"):
                with_announcement_lower_bound += 1

    if without_available_at:
        fully_unknown = without_available_at - with_announcement_lower_bound
        findings.append(
            Finding(
                BLOCK if require_available_at else WARN,
                "action_available_at_unknown",
                f"{without_available_at}/{len(actions)} 条行动缺少 available_at"
                f"（其中 {with_announcement_lower_bound} 条有 announcement_date 可作"
                f"「不晚于该日已公布」的下界，{fully_unknown} 条完全未知）；"
                "下界不等于精确到达时刻，一律不写入 available_at。"
                "本批只能用于历史重建，不得声称当时可知",
                affects_uses=("research_signal", "attribution"),
                evidence={
                    "without_available_at": without_available_at,
                    "with_announcement_lower_bound": with_announcement_lower_bound,
                    "fully_unknown": fully_unknown,
                    "total": len(actions),
                    "lower_bound_semantics": (
                        "announcement_date 只证明不晚于该日已公布，"
                        "不证明该日之前不可知，也不是带时区的真实到达时刻"
                    ),
                },
            )
        )
        if with_announcement_lower_bound:
            findings.append(
                Finding(
                    INFO,
                    "action_announcement_lower_bound_available",
                    f"{with_announcement_lower_bound} 条行动带 announcement_date，"
                    "可作可得性下界；这是现有本地资料中唯一的时点线索",
                    evidence={"count": with_announcement_lower_bound},
                )
            )

    # 永远存在：覆盖性无法证明
    findings.append(
        Finding(
            INFO,
            "coverage_unproven",
            "没有行动记录不等于已证明该期间没有分红、拆分或停牌；"
            "本文件缺连续官方「无其他行动」证明",
            affects_uses=("attribution",),
        )
    )

    counts = {
        "total": len(actions),
        "unique_ids": len(seen),
        "by_type": by_type,
        "without_available_at": without_available_at,
        "with_announcement_lower_bound": with_announcement_lower_bound,
        "findings_by_level": {
            level: sum(1 for f in findings if f.level == level)
            for level in (INFO, WARN, BLOCK)
        },
    }
    return QualityReport(tuple(findings), _verdicts_from(findings), counts)


def merge_reports(*reports: QualityReport) -> QualityReport:
    """合并多份报告；用途裁决取最严。"""
    findings = tuple(f for r in reports for f in r.findings)
    counts = {f"part_{i}": r.counts for i, r in enumerate(reports)}
    return QualityReport(findings, _verdicts_from(findings), counts)


__all__ = [
    "USES",
    "USABLE",
    "CONDITIONAL",
    "UNUSABLE",
    "INFO",
    "WARN",
    "BLOCK",
    "Finding",
    "UseVerdict",
    "QualityReport",
    "check_prices",
    "check_snapshot",
    "check_actions",
    "merge_reports",
    "require_use",
    "UseNotPermitted",
    "CALENDAR_AUTHORITIES",
]
