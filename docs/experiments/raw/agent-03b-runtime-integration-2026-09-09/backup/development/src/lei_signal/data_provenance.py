"""数据引用元信息（共用小结构，协议 v1.2）——数字必须知道自己的出处与日期。

背景（2026-09-07 总控验收 R01/R02/R07 + 00-review-contract-v1.2 §1/§2）：
第一版把本机价格文件的日期当日历、用固定 5 交易日宽限判「当前」，日历停更/
未来日期/无日历都会被误判；引用卡缺内容摘要、发布时间与对象标识。本版按
契约 v1.2 重写：规范字段 + 旧字段兼容别名并存；未知不默认当前。

三类引用（02R 复用本模块，不再另定义第二套字段）：

1. EvidenceRef（研究数字引用）——规范字段 id / source_path / source_hash /
   source_version / status / window / statistic_kind / strategy_scope /
   limitations / compatibility；兼容别名 evidence_id→id、source→source_path、
   strategies→strategy_scope、note→limitations。source_hash 是实际读取材料
   的完整 SHA256（多文件=列表，逐文件可追溯）；快照序列化后即冻结，展示
   历史不重读今天的文件充当旧依据。
2. MarketDataRef（行情引用）——规范字段 source_id / instrument_id / market /
   observed_at / available_at / generated_at / last_valid_at / health / reason /
   calendar_ref / as_of_cutoff / source_policy_ref；兼容别名 source→source_id、
   ok→fresh、partial→incomplete（旧 completeness 键保留）。
3. RuleRef（规则引用）——rule_id / version / config_path / config_hash /
   definition_ref；代码回退（账本缺段）时记录采用值与原因，不静默。

health 枚举：fresh（确认及时）/ stale（确认滞后）/ incomplete（尾部长期
缺值）/ missing（无值/文件缺失）/ unknown（无法判定——发布时间未核实、
无可信日历、参考日历自身停更、未来日期）。**unknown 永不当作当前**。

新鲜度评价（契约 §2）：不设统一 N 日宽限。按「来源发布时间（policy）+
交易日历」判断：值日期应不早于「发布截止已过的最近交易日」。没有已核实
的发布节奏 → unknown；日历缺失或日历自身没覆盖到发布截止已过的时段 →
unknown；可另附本机参考滞后天数（仅供参考，参考过期不能据此标 fresh）。
未来时间、空值必须显式降级，不猜。

交易日历适配器（独立、只读）：`reference_calendar()` 返回 CalendarInfo
（市场/时区/来源/内容摘要/覆盖范围/交易日序列/数据截止）。当前来源=本机
日频价格文件日期，**authority="price_dates_reference"——是参考不是交易所
日历**（不能证明未列出的日期不是交易日）。不触碰全局
DEFAULT_TRADING_CALENDAR / WeekdayCalendar（见 data/calendar.py：无节假日表，
仅周一至周五近似，同样不能当完整交易所日历）。查不到 → None → unknown。

兼容性枚举（exact/reference/unknown/incompatible）：exact 要求本标的、同
模块/入场/退出/条件/期限/规则/费用与数据窗口全部匹配并保存 source_run_ids；
现有 module_winrate 表缺这些配置 → 一律 unknown，不猜默认值。

用户输入（报单金额、agree/disagree 等）单列 origin="user_input"。
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

SCHEMA_VERSION = "provenance/1.2"

# 实验数字引用的适用策略标签（展示与讲解边界；与证据账本 status 分开）
STRATEGY_INCOME_DCA = "income_dca"               # 持续收入定投（预期管理）
STRATEGY_AMBUSH = "ambush"                       # 已有闲钱分批投入（埋伏战役）
STRATEGY_TECH_EXECUTION = "technical_execution"  # 技术信号后的执行
STRATEGY_OBSERVATION = "sentiment_observation"   # 情绪观察（只叙事）
STRATEGY_ARCHIVE_ONLY = "archive_only"           # 证伪封存，仅历史说明

# 兼容性枚举（契约 §1）
COMPAT_EXACT = "exact"
COMPAT_REFERENCE = "reference"
COMPAT_UNKNOWN = "unknown"
COMPAT_INCOMPATIBLE = "incompatible"


def _dt_str(x) -> str | None:
    return x.strftime("%Y-%m-%d") if x is not None else None


# ---------------- 文件哈希（内容摘要，mtime 缓存） ----------------

_HASH_CACHE: dict[tuple[str, float], str] = {}


def file_source_hash(path: Path | str | None) -> str | None:
    """实际读取材料的完整 SHA256（按 mtime 失效的进程内缓存）。

    mtime 只用于缓存失效，不作为「数据当时已公开」的证据（契约 §1）。
    """
    if path is None:
        return None
    p = Path(path)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return None
    key = (str(p), mtime)
    if key not in _HASH_CACHE:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _HASH_CACHE[key] = h.hexdigest()
    return _HASH_CACHE[key]


def _content_digest(dates: pd.DatetimeIndex) -> str:
    """日历内容摘要：交易日序列的 SHA256（前 16 位）——日历换了内容可识别。"""
    payload = "\n".join(d.strftime("%Y-%m-%d") for d in dates.date).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


# ---------------- 来源发布策略（未核实=空 → health=unknown） ----------------

@dataclass(frozen=True)
class SourcePolicy:
    """来源发布节奏：数据按其市场交易时段与来源既有发布时间评价（契约 §2）。

    verified=False 的策略不参与 fresh 判定（源发布时间找不到就 unknown，
    不补造）。01D 核实管道节奏后由 01R 在此登记（basis 附指针）。
    """

    market: str
    cadence: str = "per_trading_day"   # 每个交易日发布一次
    publish_by: str = "16:30"          # 当地时间发布截止（"HH:MM"）
    tz: str = "Asia/Shanghai"
    basis: str = ""                    # 依据（调度配置/文档指针；空=未核实）
    verified: bool = False

    def deadline_passed(self, day: date, now: datetime) -> bool:
        """day 当日发布截止是否已过（按策略时区；now 为本地时间则先定界）。"""
        hh, mm = (int(x) for x in self.publish_by.split(":"))
        deadline = datetime.combine(day, time(hh, mm), tzinfo=ZoneInfo(self.tz))
        if now.tzinfo is None:
            now = now.replace(tzinfo=ZoneInfo(self.tz))
        return now >= deadline


#: 已核实的来源发布策略注册表（当前为空：诚实降级为 unknown，
#: 不补造日历或节奏；登记需附 basis 指针）
SOURCE_POLICIES: dict[str, SourcePolicy] = {}


# ---------------- 交易日历适配器（独立、只读） ----------------

@dataclass(frozen=True)
class CalendarInfo:
    """交易日历/参考日历信息（契约 §2 适配器返回内容）。"""

    market: str
    timezone: str
    source: str                     # 来源文件/实现标识
    content_digest: str             # 内容摘要
    coverage_start: str | None
    coverage_end: str | None        # 数据截止（可信序列末端）
    trading_dates: pd.DatetimeIndex
    authority: str                  # price_dates_reference=价格日期参考，非交易所日历
                                    # weekday_approx=周一至周五近似（无节假日表）
                                    # exchange_calendar=交易所日历（本地暂无）

    def to_dict(self) -> dict:
        return {
            "market": self.market,
            "timezone": self.timezone,
            "source": self.source,
            "content_digest": self.content_digest,
            "coverage_start": self.coverage_start,
            "coverage_end": self.coverage_end,
            "n_days": int(len(self.trading_dates)),
            "authority": self.authority,
        }


_CALENDAR_CACHE: dict[tuple[str, float], pd.DatetimeIndex] = {}


def _cache_root() -> Path:
    from lei_signal.data.cache import DEFAULT_CACHE_DIR

    return Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))


def _read_calendar_dates(path: Path) -> pd.DatetimeIndex | None:
    if not path.is_file():
        return None
    try:
        mtime = path.stat().st_mtime
        key = (str(path), mtime)
        if key not in _CALENDAR_CACHE:
            df = pd.read_parquet(path)
            if "date" in df.columns:            # a_share_klines：长表 date 列
                dates = pd.to_datetime(df["date"]).dropna().sort_values()
                idx = pd.DatetimeIndex(dates.unique())
            else:                                # 宽表：行索引即日期
                idx = pd.to_datetime(df.index).sort_values()
            _CALENDAR_CACHE[key] = idx
        return _CALENDAR_CACHE[key]
    except Exception:  # noqa: BLE001 — 日历读不出按 unknown 处理，不阻断
        return None


def market_trading_dates(market: str) -> pd.DatetimeIndex | None:
    """本机参考日历（价格文件日期，仅日期不取值）。

    注意：这是 reference 不是交易所日历——列出的日期是交易日，但**不能
    证明未列出的近期日期不是交易日**（文件停更时恰好漏掉新交易日）。
    新鲜度判定见 assess_freshness，它会对参考自身的覆盖做检查。
    """
    root = _cache_root()
    if market == "cn":
        for name in ("a_share_klines.parquet", "a_share_klines_full.parquet"):
            idx = _read_calendar_dates(root / name)
            if idx is not None:
                return idx
        return None
    if market == "us":
        return _read_calendar_dates(root / "sp500_klines.parquet")
    return None


def reference_calendar(
    market: str, dates: pd.DatetimeIndex | None = None,
) -> CalendarInfo | None:
    """构造该市场的日历信息（默认价格日期参考；测试可注入 dates）。"""
    if dates is None:
        dates = market_trading_dates(market)
    if dates is None or len(dates) == 0:
        return None
    src = {
        "cn": "a_share_klines.parquet（价格日期参考）",
        "us": "sp500_klines.parquet（价格日期参考）",
    }.get(market, f"reference:{market}")
    return CalendarInfo(
        market=market,
        timezone="Asia/Shanghai" if market == "cn" else "America/New_York",
        source=src,
        content_digest=_content_digest(dates),
        coverage_start=_dt_str(dates[0].date()),
        coverage_end=_dt_str(dates[-1].date()),
        trading_dates=dates,
        authority="price_dates_reference",
    )


# ---------------- 新鲜度评价（契约 §2：无统一宽限） ----------------

@dataclass(frozen=True)
class FreshnessAssessment:
    health: str                       # fresh/stale/incomplete/missing/unknown
    reason: str
    reference_lag_trading_days: int | None = None   # 本机参考滞后（仅参考）
    calendar: CalendarInfo | None = None
    as_of_cutoff: str | None = None   # 判定所用的「发布截止已过最近交易日」

    def to_dict(self) -> dict:
        return {
            "health": self.health,
            "reason": self.reason,
            "reference_lag_trading_days": self.reference_lag_trading_days,
            "calendar_ref": self.calendar.to_dict() if self.calendar else None,
            "as_of_cutoff": self.as_of_cutoff,
            # 兼容别名（旧 completeness 口径）
            "completeness": {"fresh": "ok", "incomplete": "partial"}.get(
                self.health, self.health),
            "lag_trading_days": self.reference_lag_trading_days,
        }


def assess_freshness(
    last_valid_at: str | date | None,
    market: str,
    *,
    now: datetime | None = None,
    policy: SourcePolicy | None = None,
    calendar: CalendarInfo | None | pd.DatetimeIndex | None = None,
) -> FreshnessAssessment:
    """评价数据新鲜度：current 依据=「值不早于发布截止已过的最近交易日」。

    判定链（任一环不可知 → unknown，绝不默认当前）：
    1. 无值 → missing；
    2. 值日期晚于当前日期 → unknown（未来时间，数据异常）；
    3. 无已核实发布策略（SOURCE_POLICIES 未登记该市场）→ unknown；
    4. 无日历 → unknown；
    5. 日历覆盖末日落后于「发布截止已过的最近候选日」（参考自身停更/
       未覆盖）→ unknown（附参考滞后天数供参考）；
    6. 值 ≥ 截止日 → fresh；否则 stale（滞后=区间内交易日数）。
    """
    now = now or datetime.now()
    cal = (reference_calendar(market, dates=calendar)
           if isinstance(calendar, pd.DatetimeIndex) else calendar)

    def _unknown(reason: str) -> FreshnessAssessment:
        lag = None
        if cal is not None and last_valid_at is not None:
            try:
                d = pd.Timestamp(last_valid_at).date()
                lag = int((cal.trading_dates.date > d).sum())
            except (ValueError, TypeError):
                lag = None
        return FreshnessAssessment("unknown", reason, lag, cal, None)

    if last_valid_at is None:
        return FreshnessAssessment("missing", "无有效值（文件缺失或全空）",
                                   None, cal, None)
    try:
        value_day = pd.Timestamp(last_valid_at).date()
    except (ValueError, TypeError):
        return _unknown("日期无法解析")

    if value_day > now.date():
        return _unknown(f"值日期 {value_day} 晚于当前日期（未来时间），不可作为当前状态")

    pol = policy or SOURCE_POLICIES.get(market)
    if pol is None or not pol.verified:
        return _unknown(f"来源发布时间未核实（{market} 无 verified 策略），"
                        "不能证明数据是否当前")
    if cal is None:
        return FreshnessAssessment("unknown", "无可信交易日历", None, None, None)

    dates = cal.trading_dates
    coverage_end = min(dates[-1].date(), now.date())
    # 发布截止已过的最近交易日（在日历覆盖内倒序找）
    required: date | None = None
    for d in reversed([x for x in dates.date if x <= coverage_end]):
        if pol.deadline_passed(d, now):
            required = d
            break
    if required is None:
        return _unknown("日历覆盖内找不到发布截止已过的交易日（覆盖过短）")

    # 参考自身是否落后（P2）：找「发布截止已过的最近候选交易日」——无交易所
    # 日历时只能用工作日近似取下界（跳过周末；今天截止未过则退到上一工作日）。
    # 候选日若晚于参考覆盖末日，说明参考没盖住一段很可能包含交易日的窗口，
    # 不能为「当前」背书。节假日（工作日但休市）退化为 unknown——保守方向。
    candidate = now.date()
    for _ in range(10):
        if candidate.weekday() < 5 and pol.deadline_passed(candidate, now):
            break
        candidate = date.fromordinal(candidate.toordinal() - 1)
    else:
        return _unknown("找不到发布截止已过的候选交易日（时间异常）")
    if coverage_end < candidate:
        return _unknown(
            f"参考日历截至 {coverage_end}，未覆盖发布截止已过的候选交易日 "
            f"{candidate}（可能漏列新交易日，不能证明当前）")

    if value_day >= required:
        return FreshnessAssessment(
            "fresh", f"值日期不早于发布截止已过的最近交易日 {required}",
            0, cal, required.isoformat())
    lag = int(sum(1 for x in dates.date if value_day < x <= required))
    return FreshnessAssessment(
        "stale", f"值日期 {value_day} 落后截止日 {required} 共 {lag} 个交易日",
        lag, cal, required.isoformat())


# ---------------- 引用卡（规范字段 + 兼容别名） ----------------

@dataclass(frozen=True)
class EvidenceRef:
    """研究数字引用（v1.2 规范字段；to_dict 附旧字段别名）。"""

    id: str
    source_path: str | list[str]
    source_hash: str | list[str] | None
    source_version: str
    status: str                 # 照抄账本 status，不推断有效性
    window: str
    statistic_kind: str
    strategy_scope: tuple[str, ...] = ()
    limitations: str = ""
    compatibility: str = COMPAT_UNKNOWN
    note: str = ""              # 兼容保留（=limitations 的旧名）

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "id": self.id,
            "source_path": self.source_path,
            "source_hash": self.source_hash,
            "source_version": self.source_version,
            "status": self.status,
            "window": self.window,
            "statistic_kind": self.statistic_kind,
            "strategy_scope": list(self.strategy_scope),
            "limitations": self.limitations or self.note,
            "compatibility": self.compatibility,
            # ---- 兼容别名（旧消费者）----
            "evidence_id": self.id,
            "source": (self.source_path if isinstance(self.source_path, str)
                       else (self.source_path[0] if self.source_path else "")),
            "strategies": list(self.strategy_scope),
            "note": self.limitations or self.note,
        }


_STRATEGY_BY_PREFIX = {
    "deep20": (STRATEGY_INCOME_DCA, STRATEGY_AMBUSH),
    "bottom_zone": (STRATEGY_INCOME_DCA, STRATEGY_AMBUSH),
    "tier_low": (STRATEGY_INCOME_DCA,),
    "tier_high": (STRATEGY_INCOME_DCA,),
    "gap_over_30": (STRATEGY_AMBUSH,),
    "ambush_template": (STRATEGY_AMBUSH,),
    "falsified_knobs": (STRATEGY_ARCHIVE_ONLY,),
    "rebalance_policy": (STRATEGY_INCOME_DCA,),
    "risk_preference_options": (STRATEGY_INCOME_DCA,),
}


def _statistic_kind(entry: dict) -> str:
    metrics = entry.get("metrics") or {}
    if "xirr_grid_median" in metrics or "xirr_grid_p10" in metrics:
        return "grid_median_p10_p90"
    if "xirr_5y_single_path" in metrics:
        return "single_path_xirr"
    if isinstance(entry.get("horizon_stats"), dict):
        return "horizon_stats"
    if "episode_bootstrap_6m" in entry or "episode_bootstrap_12m" in entry:
        return "episode_bootstrap"
    return "narrative"


def resolve_ledger_sources(entry: dict, repo_root: Path | None = None) -> list[str]:
    """账本条目的实际材料路径：source 实验名 → 报告 md + verified_against raw。"""
    root = repo_root or Path(__file__).resolve().parents[2]
    names: list[str] = []
    raw = entry.get("source") or ""
    for name in [p.strip() for p in str(raw).replace("；", ";").split(";") if p.strip()]:
        # source 形如 "dca-entry-timing-table-2026-09-07（说明）"，取括号前名字
        base = name.split("（")[0].strip()
        names.append(base)
    paths: list[str] = []
    for name in names:
        cand = root / "docs" / "experiments" / f"{name}.md"
        if cand.is_file():
            paths.append(str(cand))
    for p in (entry.get("verified_against") or []):
        cand = Path(p) if Path(p).is_absolute() else root / p
        if cand.is_file() and str(cand) not in paths:
            paths.append(str(cand))
    return paths


def evidence_ref(
    evidence_id: str,
    entry: dict | None,
    *,
    ledger_version: str = "",
    repo_root: Path | None = None,
    compatibility: str = COMPAT_UNKNOWN,
    source_paths: list[str] | None = None,
) -> EvidenceRef:
    """由账本条目构造 EvidenceRef（含材料内容哈希）。

    条目缺失/损坏时返回可识别降级引用（status=missing，数字不可引用）。
    compatibility 默认 unknown：本表数字是否回答当前问题须由调用方按
    对象/用途判断后显式给出（exact 须全配置匹配+source_run_ids）。
    """
    if not isinstance(entry, dict):
        miss = "账本条目缺失，数字不可引用"
        return EvidenceRef(evidence_id, [], None, ledger_version, "missing", "",
                           "narrative", (STRATEGY_ARCHIVE_ONLY,), miss,
                           COMPAT_UNKNOWN, miss)
    src_paths = (source_paths if source_paths is not None
                 else resolve_ledger_sources(entry, repo_root))
    hashes = [file_source_hash(p) for p in src_paths]
    limitations = str(entry.get("note") or "")
    return EvidenceRef(
        id=evidence_id,
        source_path=src_paths if src_paths else [],
        source_hash=hashes if hashes else None,
        source_version=ledger_version,
        status=str(entry.get("status") or "unverified"),
        window=str(entry.get("window") or ""),
        statistic_kind=_statistic_kind(entry),
        strategy_scope=_STRATEGY_BY_PREFIX.get(evidence_id, (STRATEGY_INCOME_DCA,)),
        limitations=limitations,
        compatibility=compatibility,
        note=limitations,
    )


@dataclass(frozen=True)
class MarketDataRef:
    """行情/数据源引用（v1.2 规范字段；to_dict 附旧字段别名）。

    available_at：来源对外可用时间（如 T+1 收盘后发布）——找不到依据时
    为 None（契约：时间未知用 null 及原因，不猜）。
    """

    source_id: str
    instrument_id: str = ""
    market: str = ""
    observed_at: str | None = None
    available_at: str | None = None
    generated_at: str | None = None
    last_valid_at: str | None = None
    health: str = "unknown"          # fresh/stale/incomplete/missing/unknown
    reason: str = ""
    calendar_ref: dict | None = None
    as_of_cutoff: str | None = None
    source_policy_ref: str | None = None
    reference_lag_trading_days: int | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        out = {
            "schema_version": SCHEMA_VERSION,
            "source_id": self.source_id,
            "instrument_id": self.instrument_id,
            "market": self.market,
            "observed_at": self.observed_at,
            "available_at": self.available_at,
            "generated_at": self.generated_at,
            "last_valid_at": self.last_valid_at,
            "health": self.health,
            "reason": self.reason,
            "calendar_ref": self.calendar_ref,
            "as_of_cutoff": self.as_of_cutoff,
            "source_policy_ref": self.source_policy_ref,
            "reference_lag_trading_days": self.reference_lag_trading_days,
            # ---- 兼容别名（旧消费者）----
            "source": self.source_id,
            "completeness": {"fresh": "ok", "incomplete": "partial"}.get(
                self.health, self.health),
            "lag_trading_days": self.reference_lag_trading_days,
        }
        if self.extra:
            out.update(self.extra)
        return out


@dataclass(frozen=True)
class RuleRef:
    """规则引用：实际启用账本的版本与内容摘要；回退须记录采用值与原因。"""

    rule_id: str
    version: str
    config_path: str
    config_hash: str | None
    definition_ref: str = ""       # 实现/溯源文档指针
    fallback_note: str = ""        # 账本缺段时：采用值与原因（无回退=空）

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "rule_id": self.rule_id,
            "version": self.version,
            "config_path": self.config_path,
            "config_hash": self.config_hash,
            "definition_ref": self.definition_ref,
            "fallback_note": self.fallback_note,
        }


def rule_ref(rule_id: str, *, fallback_note: str = "") -> RuleRef:
    """从实际加载的规则账本构造 RuleRef；条目缺失时 version=unregistered。"""
    from lei_signal.domain import rules_config

    config_path = str(rules_config._default_config_path())
    config_hash = file_source_hash(config_path)
    try:
        rule = rules_config.get_rule(rule_id)
    except Exception:  # noqa: BLE001 — 缺段=unregistered，不静默
        return RuleRef(rule_id, "unregistered", config_path, config_hash,
                       definition_ref="", fallback_note=fallback_note)
    return RuleRef(rule_id, rule.version, config_path, config_hash,
                   definition_ref=config_path, fallback_note=fallback_note)


def ruleset_ref() -> RuleRef:
    """整个规则账本的版本引用（判定层公共依赖的整体快照，供封装冻结用）。

    与单条 rule_ref 分开：ruleset_ref 说明「当时判定层整体账本版本+内容
    哈希」，不冒充某条具体规则。
    """
    from lei_signal.domain import rules_config

    config_path = str(rules_config._default_config_path())
    try:
        version = rules_config.ruleset_version()
    except Exception:  # noqa: BLE001
        version = "unavailable"
    return RuleRef("__ruleset__", version, config_path,
                   file_source_hash(config_path), definition_ref=config_path)


# ---------------- 胜率表引用适配（R08：只加事实与标记，不重写表） ----------------

WINRATE_TABLE_LIMITATIONS = (
    "现有 module_winrate 表按 symbol+entry_date 先去重再分模块：同日同标的的"
    "不同模块结果互相覆盖，取决于输入顺序（总控探针 O 已复现）；且条目未保存"
    "source_run_ids、入场/退出变体、规则版本、费用与数据窗口——配置不全，"
    "不得标 exact，引用一律按 unknown/reference 处理，重新生成方法由总控定稿"
)


def winrate_evidence_ref(symbol: str, module: str | None = None) -> EvidenceRef:
    """标的×模块胜率的引用卡（compatibility=unknown，附事实性限制）。

    不读取/修改胜率表本身；03 接线时用本卡说明「这份统计是否回答当前问题」。
    """
    obj = f"{symbol}|{module}" if module else symbol
    return EvidenceRef(
        id=f"module_winrate:{obj}",
        source_path="docs/experiments/module_winrate.json",
        source_hash=file_source_hash(
            Path(__file__).resolve().parents[2]
            / "docs" / "experiments" / "module_winrate.json"),
        source_version="1",
        status="unverified",
        window="（表内未保存数据窗口，仅 all/recent 两档）",
        statistic_kind="trade_r_stats",
        strategy_scope=(STRATEGY_TECH_EXECUTION,),
        limitations=WINRATE_TABLE_LIMITATIONS,
        compatibility=COMPAT_UNKNOWN,
    )


def file_generated_at(path: Path | None) -> str | None:
    """文件生成时间（mtime → ISO 秒）。仅说明改动时间，不证明数据当时已公开。"""
    if path is None:
        return None
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M:%S")
    except OSError:
        return None


def breadth_market(symbol: str) -> str:
    """DCA 跟踪池口径：^ 开头用 sp500 宽度，其余用 cn_all。"""
    return "us" if symbol.startswith("^") else "cn"


# ---------------- 旧接口兼容（旧消费者仍在用，语义已由上方取代） ----------------

def classify_freshness(
    last_valid_at: str | date | None,
    market: str,
) -> tuple[str, int | None]:
    """旧签名兼容：返回 (health, reference_lag_trading_days)。

    旧实现的 5 交易日宽限与「本机日历末日=当前」假设已废止（R01）；
    等价于 assess_freshness 的 (health, reference_lag) 投影。新代码请用
    assess_freshness（拿得到 reason/calendar/cutoff）。
    """
    a = assess_freshness(last_valid_at, market)
    return a.health, a.reference_lag_trading_days
