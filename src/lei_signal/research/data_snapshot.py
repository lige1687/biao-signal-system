"""研究专用数据获取/导入、只读快照与离线复用。

本轮：`research-data-provenance-2026-09-10`。

职责边界
--------
只服务研究层的四个问题：数据从哪来、取得了哪个版本、是否完整、当时是否可知。

**不新增任何并行体系**：

- 抓取复用 :mod:`lei_signal.data.providers`（超时、有限重试、失败一律抛错）；
- K 线校验复用 :func:`lei_signal.data.validation.validate_bars`；
- 时间与来源语义复用 :mod:`lei_signal.data_provenance` 的 ``MarketDataRef``
  与 ``file_source_hash``；
- 质量裁决在同目录 :mod:`lei_signal.research.data_quality`。

不运行账户、不做收益回测、不写生产缓存、不新增供应商或凭据。

时间语义（不可放宽）
--------------------
四类时间分别记录，缺一不可混用：

``observed_at``
    数据自身的观察日（日线即交易日收盘）。
``available_at``
    来源对外可用的真实时刻。**历史资料缺到达时间一律 ``None`` 加 reason**，
    禁止补成收盘时刻或本次抓取时刻。
``generated_at``
    本地标准化产物的生成时刻。
``fetched_at``
    本次取得的时刻。

后来取得的历史资料只证明「本次取得了该版本」，**不证明历史当天就拿得到**。

防覆盖
------
输出目录必须全新；已存在则顺延 ``-NN``。相同请求返回不同内容时保存**新**快照
并写差异，不静默刷新旧证据。

``fresh_dir`` 与 ``scripts/run_factor_library_v0.py:62-79`` 语义一致；该脚本有
顶层 ``sys.path`` 与 ``sys.dont_write_bytecode`` 副作用，不宜作为库导入，故在此
重新实现同语义版本（已在本轮报告的缺口表登记为必要重复）。
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from lei_signal.data.validation import DataUnavailableError, validate_bars
from lei_signal.data_provenance import MarketDataRef, file_source_hash

#: 标准化转换的版本号。改变标准化产物的字段、单位或语义时必须升版。
TRANSFORM_VERSION = "research-data-snapshot/1.0"

#: 快照结构版本。读回时严格比对，不接受静默跨版本读入。
SNAPSHOT_SCHEMA_VERSION = "research-data-snapshot/1.0"

#: 快照默认允许用途。价格行本身可服务全部六类机器用途，
#: **实际能否使用由质量裁决决定**——用途声明与质量裁决是两道独立的关卡。
DEFAULT_SNAPSHOT_USES: tuple[str, ...] = (
    "description", "ranking", "research_signal", "attribution",
    "comparison", "diagnostic",
)

#: 快照默认禁止用途。
DEFAULT_SNAPSHOT_NOT_FOR: tuple[str, ...] = (
    "production_trade",
    "宣称历史时点可交易",
    "作为复权价格使用",
)

#: 标准化产物的字段与单位（写进快照，不让下游猜）。
NORMALIZED_FIELDS: dict[str, str] = {
    "date": "交易日（Asia/Shanghai，无时区标注的日期）",
    "open": "开盘价，人民币元",
    "high": "最高价，人民币元",
    "low": "最低价，人民币元",
    "close": "收盘价，人民币元",
    "volume": "成交量，原始单位未统一认证（只宜同一标的自身相对比较）",
}


class BudgetExceeded(RuntimeError):
    """超出本轮声明的请求预算。必须在实际发出请求之前阻断。"""


class AcquisitionFailed(RuntimeError):
    """获取失败。

    **绝不允许伪装成空成功**：任何失败都以本异常向上暴露，
    不返回空 DataFrame、不返回部分结果假装完整。
    """


# --------------------------------------------------------------------------
# 预算与请求规格
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FetchBudget:
    """本轮联网预算。``max_requests`` 含重试与翻页。"""

    max_instruments: int
    max_trading_days: int
    max_requests: int
    timeout_seconds: float = 15.0
    max_retries: int = 2

    @property
    def attempts_per_instrument(self) -> int:
        """一个标的最多发起几次请求（首次 + 重试）。"""
        return self.max_retries + 1


@dataclass(frozen=True)
class RequestSpec:
    """一次获取的意图声明。实际 URL 由 provider 构造并在快照中如实记录。"""

    source_id: str
    instrument_id: str
    market: str = "CN"
    trading_days: int = 60
    fields: tuple[str, ...] = tuple(NORMALIZED_FIELDS)
    price_basis: str = "nominal_close"
    currency: str = "CNY"
    note: str = ""


# --------------------------------------------------------------------------
# 记录型 opener：预算强制 + 原始响应与时刻捕获
# --------------------------------------------------------------------------


@dataclass
class _Call:
    url: str
    requested_at: str
    returned_at: str | None
    ok: bool
    error: str | None
    body_sha256: str | None
    body_bytes: int | None


class _RecordingOpener:
    """包住 provider 的 opener：计数、限额、记录 URL / 时刻 / 原始响应体。

    预算命中时置位 ``budget_hit`` 再抛错。provider 的重试循环会把任意异常
    转成 ``DataUnavailableError``，因此**不能**依赖异常类型穿透——调用方在
    provider 返回后必须检查 ``budget_hit`` 并无条件重抛 :class:`BudgetExceeded`。
    """

    def __init__(
        self,
        inner: Callable[[str], str],
        *,
        max_requests: int,
        clock: Callable[[], datetime],
    ) -> None:
        self._inner = inner
        self._max_requests = max_requests
        self._clock = clock
        self.calls: list[_Call] = []
        self.bodies: dict[str, str] = {}
        self.budget_hit = False

    @property
    def request_count(self) -> int:
        return len(self.calls)

    def __call__(self, url: str) -> str:
        if self.request_count >= self._max_requests:
            self.budget_hit = True
            raise BudgetExceeded(
                f"请求预算 {self._max_requests} 次已用尽，拒绝发出新请求"
            )
        requested_at = self._clock().isoformat()
        try:
            body = self._inner(url)
        except Exception as exc:  # noqa: BLE001 - 如实记录后原样上抛
            self.calls.append(
                _Call(
                    url=url,
                    requested_at=requested_at,
                    returned_at=self._clock().isoformat(),
                    ok=False,
                    error=f"{type(exc).__name__}: {exc}",
                    body_sha256=None,
                    body_bytes=None,
                )
            )
            raise
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self.calls.append(
            _Call(
                url=url,
                requested_at=requested_at,
                returned_at=self._clock().isoformat(),
                ok=True,
                error=None,
                body_sha256=digest,
                body_bytes=len(body.encode("utf-8")),
            )
        )
        self.bodies[url] = body
        return body


# --------------------------------------------------------------------------
# 快照结果
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SnapshotResult:
    """一次获取或导入的产物位置与身份。"""

    directory: Path
    snapshot: dict
    frames: dict[str, pd.DataFrame] = field(default_factory=dict)

    @property
    def instruments(self) -> list[str]:
        return sorted(self.frames)


@dataclass(frozen=True)
class LoadedSnapshot:
    """从磁盘离线读回的快照。``verified`` 表示逐文件哈希是否与快照记录一致。"""

    directory: Path
    snapshot: dict
    frames: dict[str, pd.DataFrame]
    verified: bool
    hash_mismatches: tuple[str, ...] = ()

    @property
    def declared_uses(self) -> tuple[str, ...]:
        """产物自身声明的允许用途。传给 ``require_use(declared_uses=...)`` 做交叉核对。"""
        return tuple(self.snapshot.get("uses", ()))

    @property
    def declared_not_for(self) -> tuple[str, ...]:
        return tuple(self.snapshot.get("not_for", ()))


# --------------------------------------------------------------------------
# 目录防覆盖
# --------------------------------------------------------------------------


def fresh_dir(requested: Path) -> Path:
    """永不覆盖：目录已存在则顺延到第一个空闲的 ``-NN`` 兄弟目录。

    语义与 ``scripts/run_factor_library_v0.py:62-79`` 一致（见模块文档）。
    """
    requested = Path(requested)
    if not requested.exists():
        return requested
    stem = requested.name
    parent = requested.parent
    if "-" in stem and stem.rsplit("-", 1)[1].isdigit():
        base, _ = stem.rsplit("-", 1)
    else:
        base = stem
    n = 1
    while True:
        candidate = parent / f"{base}-{n:02d}"
        if not candidate.exists():
            return candidate
        n += 1


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _code_identity() -> dict[str, str | None]:
    """本模块与其直接复用模块的代码身份。"""
    here = Path(__file__).resolve()
    root = here.parents[3]
    paths = {
        "data_snapshot": here,
        "data_quality": here.with_name("data_quality.py"),
        "providers": root / "src/lei_signal/data/providers.py",
        "validation": root / "src/lei_signal/data/validation.py",
        "data_provenance": root / "src/lei_signal/data_provenance.py",
    }
    return {name: file_source_hash(path) for name, path in paths.items()}


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=False, default=str),
        encoding="utf-8",
    )


def _frame_to_csv(frame: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    out.index.name = "date"
    out = out.reset_index()
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    text = out.to_csv(index=False, lineterminator="\n")
    path.write_text(text, encoding="utf-8")
    return _sha256_text(text)


def _market_data_ref(
    spec: RequestSpec,
    frame: pd.DataFrame,
    *,
    fetched_at: str | None,
    generated_at: str,
    available_at_reason: str,
) -> dict:
    """构造 MarketDataRef。``available_at`` 未核实一律 None + reason。"""
    last = frame.index.max() if not frame.empty else None
    ref = MarketDataRef(
        source_id=spec.source_id,
        instrument_id=spec.instrument_id,
        market=spec.market,
        observed_at=last.strftime("%Y-%m-%d") if last is not None else None,
        # 没有已核实的来源发布节奏（data_provenance.SOURCE_POLICIES 故意为空），
        # 因此对外可用时刻未知——不猜、不用抓取时刻顶替。
        available_at=None,
        generated_at=generated_at,
        last_valid_at=last.strftime("%Y-%m-%d") if last is not None else None,
        health="unknown",
        reason=available_at_reason,
        source_policy_ref=None,
        extra={"fetched_at": fetched_at, "transform_version": TRANSFORM_VERSION},
    )
    return ref.to_dict()


# --------------------------------------------------------------------------
# 获取（联网）
# --------------------------------------------------------------------------


def acquire_prices(
    specs: Sequence[RequestSpec],
    *,
    budget: FetchBudget,
    out_dir: Path,
    opener: Callable[[str], str] | None = None,
    clock: Callable[[], datetime] | None = None,
    provider_factory: Callable[..., object] | None = None,
) -> SnapshotResult:
    """按声明的预算获取日线，落原始响应 + 标准化产物 + 快照。

    ``opener`` 用于测试注入模拟响应；为 ``None`` 时使用 provider 默认联网实现。
    任何失败都抛 :class:`AcquisitionFailed`，**不返回空成功**。
    """
    clock = clock or _utcnow
    specs = list(specs)
    if not specs:
        raise ValueError("specs 不能为空")

    # 预检：在发出任何请求之前阻断超额，不靠事后发现。
    if len(specs) > budget.max_instruments:
        raise BudgetExceeded(
            f"标的数 {len(specs)} 超过预算 {budget.max_instruments}"
        )
    for spec in specs:
        if spec.trading_days > budget.max_trading_days:
            raise BudgetExceeded(
                f"{spec.instrument_id} 请求 {spec.trading_days} 个交易日，"
                f"超过预算 {budget.max_trading_days}"
            )
    worst_case = len(specs) * budget.attempts_per_instrument
    if worst_case > budget.max_requests:
        raise BudgetExceeded(
            f"最坏情况请求数 {worst_case}（{len(specs)} 标的 × "
            f"{budget.attempts_per_instrument} 次尝试）超过预算 {budget.max_requests}"
        )

    from lei_signal.data.providers import SinaPriceProvider

    factory = provider_factory or SinaPriceProvider

    directory = fresh_dir(Path(out_dir))
    directory.mkdir(parents=True)

    started_at = clock().isoformat()
    frames: dict[str, pd.DataFrame] = {}
    per_instrument: list[dict] = []
    refs: dict[str, dict] = {}
    all_calls: list[_Call] = []
    requests_used = 0

    for spec in specs:
        remaining = budget.max_requests - requests_used
        provider_kwargs = {
            "timeout": budget.timeout_seconds,
            "max_bars": spec.trading_days,
            "attempts": budget.attempts_per_instrument,
        }
        base_provider = factory(**provider_kwargs)
        inner = opener if opener is not None else base_provider._default_opener
        recorder = _RecordingOpener(inner, max_requests=remaining, clock=clock)
        provider = factory(recorder, **provider_kwargs)

        failure: str | None = None
        try:
            data = provider.fetch(spec.instrument_id, min_rows=1)
        except Exception as exc:  # noqa: BLE001 - 统一转本模块异常
            failure = f"{type(exc).__name__}: {exc}"
            data = None
        finally:
            all_calls.extend(recorder.calls)
            requests_used += recorder.request_count

        # provider 的重试循环会把任意异常吞成 DataUnavailableError，
        # 因此预算命中必须由这里无条件重抛，不能依赖异常类型穿透。
        if recorder.budget_hit:
            _write_json(
                directory / "aborted.json",
                {
                    "reason": "budget_exceeded",
                    "requests_used": requests_used,
                    "max_requests": budget.max_requests,
                    "calls": [c.__dict__ for c in all_calls],
                },
            )
            raise BudgetExceeded(
                f"请求预算 {budget.max_requests} 次用尽于 {spec.instrument_id}"
            )

        if failure is not None or data is None:
            _write_json(
                directory / "aborted.json",
                {
                    "reason": "acquisition_failed",
                    "instrument_id": spec.instrument_id,
                    "error": failure,
                    "calls": [c.__dict__ for c in all_calls],
                },
            )
            raise AcquisitionFailed(f"{spec.instrument_id} 获取失败：{failure}")

        # 原始响应体与标准化产物分开存放。
        raw_paths: list[dict] = []
        for idx, (url, body) in enumerate(recorder.bodies.items()):
            raw_path = directory / "raw" / f"{spec.instrument_id}.{idx:02d}.raw.json"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(body, encoding="utf-8")
            raw_paths.append(
                {
                    "path": str(raw_path.relative_to(directory)),
                    "url": url,
                    "sha256": _sha256_text(body),
                    "bytes": len(body.encode("utf-8")),
                }
            )

        frame = data.bars
        norm_path = directory / "normalized" / f"{spec.instrument_id}.csv"
        norm_sha = _frame_to_csv(frame, norm_path)
        frames[spec.instrument_id] = frame

        report = data.report
        fetched_at = recorder.calls[-1].returned_at if recorder.calls else None
        generated_at = clock().isoformat()
        refs[spec.instrument_id] = _market_data_ref(
            spec,
            frame,
            fetched_at=fetched_at,
            generated_at=generated_at,
            available_at_reason=(
                "来源发布节奏未核实（data_provenance.SOURCE_POLICIES 为空）；"
                "对外可用时刻未知，不用抓取时刻顶替"
            ),
        )
        per_instrument.append(
            {
                "instrument_id": spec.instrument_id,
                "market": spec.market,
                "requested_trading_days": spec.trading_days,
                "rows": int(len(frame)),
                "first_date": str(frame.index.min().date()) if len(frame) else None,
                "last_date": str(frame.index.max().date()) if len(frame) else None,
                "raw_responses": raw_paths,
                "normalized": {
                    "path": str(norm_path.relative_to(directory)),
                    "sha256": norm_sha,
                },
                "provider_report": {
                    "provider": report.provider,
                    "adjusted": bool(report.adjusted),
                    "duplicates_removed": int(report.duplicates_removed),
                    "warnings": list(report.warnings),
                },
                "fetched_at": fetched_at,
            }
        )

    snapshot = _build_snapshot(
        mode="acquire",
        directory=directory,
        specs=specs,
        per_instrument=per_instrument,
        refs=refs,
        started_at=started_at,
        finished_at=clock().isoformat(),
        calls=all_calls,
        budget=budget,
        requests_used=requests_used,
    )
    _write_json(directory / "snapshot.json", snapshot)
    _write_json(directory / "market_data_refs.json", refs)
    return SnapshotResult(directory=directory, snapshot=snapshot, frames=frames)


# --------------------------------------------------------------------------
# 导入（离线，已有合法文件）
# --------------------------------------------------------------------------


def import_prices(
    csv_path: Path | str,
    *,
    source_id: str,
    out_dir: Path,
    instrument_ids: Sequence[str] | None = None,
    price_basis: str = "nominal_close",
    currency: str = "CNY",
    available_at_reason: str = "冻结历史输入缺到达时间；保持未知，不补造",
    clock: Callable[[], datetime] | None = None,
    symbol_mapper: Callable[[str], str] | None = None,
    adjusted: bool | None = None,
) -> SnapshotResult:
    """从已有的合法本地文件导入，完全离线。

    源文件按**只读**处理：只记录其路径与 SHA-256，不改写、不移动。

    ``symbol_mapper``
        可选的产品代码映射（例如把来源写法 ``510300.SH`` 换成仓库规范写法
        ``510300.SS``）。**只换标签，不动任何数值**；原始写法逐条记录在
        快照的 ``symbol_mapping`` 段，随时可回溯。映射后若出现重复身份即报错，
        不静默合并。
    ``adjusted``
        是否为复权价。**不猜**：只有已知口径才自动判定
        （``nominal_close`` → ``False``）；其它口径必须显式给出，
        否则报错。早期实现用 ``price_basis != "nominal_close"`` 推断，
        对未登记的口径会给出无依据的 ``True``。
    """
    clock = clock or _utcnow
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise AcquisitionFailed(f"导入源不存在：{csv_path}")

    # adjusted 只对已登记口径自动判定，其余必须显式声明。
    if adjusted is None:
        if price_basis == "nominal_close":
            resolved_adjusted = False
        else:
            raise AcquisitionFailed(
                f"price_basis={price_basis!r} 的复权口径未登记；"
                "请显式传入 adjusted=True/False，不接受推断"
            )
    else:
        resolved_adjusted = bool(adjusted)

    raw = pd.read_csv(csv_path)
    required = {"date", "symbol", "open", "high", "low", "close", "volume"}
    missing = required - set(raw.columns)
    if missing:
        raise AcquisitionFailed(f"{csv_path} 缺少字段：{sorted(missing)}")

    wanted = set(instrument_ids) if instrument_ids else set(raw["symbol"].unique())
    unknown = wanted - set(raw["symbol"].unique())
    if unknown:
        raise AcquisitionFailed(f"{csv_path} 中不存在标的：{sorted(unknown)}")

    # 标签映射：只换代码写法，不动任何数值；重复身份必须报错。
    symbol_mapping: dict[str, str] = {}
    if symbol_mapper is not None:
        for original in sorted(wanted):
            mapped = symbol_mapper(original)
            if mapped in symbol_mapping.values():
                dup = next(k for k, v in symbol_mapping.items() if v == mapped)
                raise AcquisitionFailed(
                    f"{original!r} 与 {dup!r} 映射到同一身份 {mapped!r}，拒绝合并"
                )
            symbol_mapping[original] = mapped
        raw = raw.copy()
        raw["symbol"] = raw["symbol"].map(
            lambda s: symbol_mapping.get(s, s)  # noqa: B023
        )
        wanted = set(symbol_mapping.values())

    directory = fresh_dir(Path(out_dir))
    directory.mkdir(parents=True)
    started_at = clock().isoformat()

    frames: dict[str, pd.DataFrame] = {}
    per_instrument: list[dict] = []
    refs: dict[str, dict] = {}
    specs: list[RequestSpec] = []

    for symbol in sorted(wanted):
        part = raw[raw["symbol"] == symbol].copy()
        part["date"] = pd.to_datetime(part["date"])
        part = part.set_index("date")[["open", "high", "low", "close", "volume"]]
        # 复用既有 K 线校验，不另写一套。
        frame, report = validate_bars(
            part,
            symbol=symbol,
            provider=source_id,
            adjusted=resolved_adjusted,
            min_rows=1,
        )
        spec = RequestSpec(
            source_id=source_id,
            instrument_id=symbol,
            trading_days=int(len(frame)),
            price_basis=price_basis,
            currency=currency,
            note="offline import",
        )
        specs.append(spec)
        norm_path = directory / "normalized" / f"{symbol}.csv"
        norm_sha = _frame_to_csv(frame, norm_path)
        frames[symbol] = frame
        generated_at = clock().isoformat()
        refs[symbol] = _market_data_ref(
            spec,
            frame,
            fetched_at=None,  # 导入不代表本次取得；源文件的取得时刻未知
            generated_at=generated_at,
            available_at_reason=available_at_reason,
        )
        per_instrument.append(
            {
                "instrument_id": symbol,
                "market": spec.market,
                "requested_trading_days": None,
                "rows": int(len(frame)),
                "first_date": str(frame.index.min().date()) if len(frame) else None,
                "last_date": str(frame.index.max().date()) if len(frame) else None,
                "raw_responses": [],
                "normalized": {
                    "path": str(norm_path.relative_to(directory)),
                    "sha256": norm_sha,
                },
                "provider_report": {
                    "provider": report.provider,
                    "adjusted": bool(report.adjusted),
                    "duplicates_removed": int(report.duplicates_removed),
                    "warnings": list(report.warnings),
                },
                "fetched_at": None,
            }
        )

    snapshot = _build_snapshot(
        mode="import",
        directory=directory,
        specs=specs,
        per_instrument=per_instrument,
        refs=refs,
        started_at=started_at,
        finished_at=clock().isoformat(),
        calls=[],
        budget=None,
        requests_used=0,
        import_source={
            "path": str(csv_path),
            "sha256": file_source_hash(csv_path),
            "read_only": True,
            "symbol_mapping": symbol_mapping or None,
            "symbol_mapping_note": (
                "只把来源写法换成仓库规范写法，数值与日期未改；原始写法保留在此可回溯"
                if symbol_mapping
                else None
            ),
        },
    )
    _write_json(directory / "snapshot.json", snapshot)
    _write_json(directory / "market_data_refs.json", refs)
    return SnapshotResult(directory=directory, snapshot=snapshot, frames=frames)


# --------------------------------------------------------------------------
# 快照组装
# --------------------------------------------------------------------------


def _build_snapshot(
    *,
    mode: str,
    directory: Path,
    specs: Sequence[RequestSpec],
    per_instrument: list[dict],
    refs: dict[str, dict],
    started_at: str,
    finished_at: str,
    calls: list[_Call],
    budget: FetchBudget | None,
    requests_used: int,
    import_source: dict | None = None,
    uses: Sequence[str] | None = None,
    not_for: Sequence[str] | None = None,
) -> dict:
    # 口径与币种必须全批一致。协议明令「不静默拼接不同价格口径」——
    # 早期实现用 specs[0] 取值，异构时会把第二个 spec 的口径悄悄丢掉，
    # 且下游 check_prices 从快照读单一口径，因此混用检查也永远不会触发。
    bases = sorted({s.price_basis for s in specs})
    currencies = sorted({s.currency for s in specs})
    if len(bases) > 1:
        raise AcquisitionFailed(
            f"同一批出现多种价格口径 {bases}；拒绝写入单一口径的快照，"
            "请分批处理或显式声明为不同批次"
        )
    if len(currencies) > 1:
        raise AcquisitionFailed(
            f"同一批出现多种币种 {currencies}；拒绝写入单一币种的快照"
        )
    first = specs[0]
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "transform_version": TRANSFORM_VERSION,
        "mode": mode,
        "protocol_id": "research-data-provenance-2026-09-10",
        "source": {
            "source_id": first.source_id,
            "import_source": import_source,
        },
        "request": {
            "instruments": [s.instrument_id for s in specs],
            "trading_days_requested": {s.instrument_id: s.trading_days for s in specs},
            "fields_requested": list(first.fields),
            "calls": [c.__dict__ for c in calls],
            "requests_used": requests_used,
            "budget": (
                {
                    "max_instruments": budget.max_instruments,
                    "max_trading_days": budget.max_trading_days,
                    "max_requests": budget.max_requests,
                    "timeout_seconds": budget.timeout_seconds,
                    "max_retries": budget.max_retries,
                }
                if budget
                else None
            ),
        },
        "timing": {
            "started_at": started_at,
            "finished_at": finished_at,
            "note": (
                "started_at/finished_at 是本次运行时刻；不得当作数据的对外可用时刻。"
            ),
        },
        "instruments": per_instrument,
        "market_data_refs": refs,
        "semantics": {
            "fields": NORMALIZED_FIELDS,
            "currency": first.currency,
            "price_basis": first.price_basis,
            "price_basis_by_instrument": {
                s.instrument_id: s.price_basis for s in specs
            },
            "price_basis_note": (
                "nominal_close = 名义未复权收盘价；公司行动不在价格里，"
                "需另接已登记的 actions 输入"
            ),
            "corporate_action_basis": "not_included_in_price",
            "trading_calendar": {
                "authority": "none",
                "note": (
                    "本仓库无真实交易所日历。data/calendar.py 的 WeekdayCalendar 是"
                    "周一至周五近似且节假日表为空，不得当交易日历使用；"
                    "data_provenance.reference_calendar 的 authority 为 "
                    "price_dates_reference，只是参考。"
                ),
            },
            "time_semantics": {
                "observed_at": "数据自身观察日（日线收盘）",
                "available_at": "来源对外可用时刻；未核实一律 null 并给 reason",
                "generated_at": "本地标准化产物生成时刻",
                "fetched_at": "本次取得时刻；导入模式为 null",
                "rule": (
                    "后来取得的历史资料只证明本次取得了该版本，"
                    "不证明历史当天就拿得到"
                ),
            },
        },
        "code_identity": _code_identity(),
        "known_gaps": [
            "来源发布节奏未核实，available_at 全部未知（health=unknown）",
            "无真实交易所日历，无法区分整池缺席日与非交易日",
            "volume 绝对单位未统一认证，只宜同一标的自身相对比较",
            "价格不含公司行动；分红拆分须由已登记的 actions 输入单独提供",
        ],
        # 用途声明必须是**深思后的显式声明**，不是硬编码默认值。
        # 早期版本硬编码为 [description, diagnostic, comparison]，未含 ranking，
        # 与质量裁决对 ranking 的判断长期冲突而无人核对。
        "uses": list(uses) if uses is not None else list(DEFAULT_SNAPSHOT_USES),
        "uses_basis": (
            "调用方显式声明" if uses is not None else
            "本实现默认：价格行可服务全部六类机器用途，实际能否使用由质量裁决决定"
        ),
        "not_for": list(not_for) if not_for is not None else list(DEFAULT_SNAPSHOT_NOT_FOR),
        "authorization": {
            "production_trade": False,
            "note": "本快照只是数据资料，不构成策略有效或获准交易的证据",
        },
    }


# --------------------------------------------------------------------------
# 离线复用与差异
# --------------------------------------------------------------------------


def load_snapshot(snapshot_dir: Path | str) -> LoadedSnapshot:
    """完全离线读回快照，并逐文件核对 SHA-256。"""
    directory = Path(snapshot_dir)
    snapshot_path = directory / "snapshot.json"
    if not snapshot_path.exists():
        raise AcquisitionFailed(f"快照不存在：{snapshot_path}")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    # 版本核对：早期实现完全不看，未来或过期版本写的快照会被静默读入。
    got_schema = snapshot.get("schema_version")
    if got_schema != SNAPSHOT_SCHEMA_VERSION:
        raise AcquisitionFailed(
            f"快照 schema_version={got_schema!r} 与本实现 "
            f"{SNAPSHOT_SCHEMA_VERSION!r} 不一致；拒绝静默读入"
        )
    got_transform = snapshot.get("transform_version")
    if got_transform != TRANSFORM_VERSION:
        raise AcquisitionFailed(
            f"快照 transform_version={got_transform!r} 与本实现 "
            f"{TRANSFORM_VERSION!r} 不一致；标准化语义可能已变，拒绝静默读入"
        )

    frames: dict[str, pd.DataFrame] = {}
    mismatches: list[str] = []
    for item in snapshot["instruments"]:
        # 原始响应体也必须核验：它是第一手证据，被改动却不报会更危险。
        for raw in item.get("raw_responses", []):
            rp = directory / raw["path"]
            if not rp.exists():
                mismatches.append(f"{raw['path']} (missing)")
                continue
            if _sha256_text(rp.read_text(encoding="utf-8")) != raw["sha256"]:
                mismatches.append(raw["path"])
        rel = item["normalized"]["path"]
        path = directory / rel
        text = path.read_text(encoding="utf-8")
        if _sha256_text(text) != item["normalized"]["sha256"]:
            mismatches.append(rel)
        frame = pd.read_csv(path)
        # 哈希一致 ≠ 结构正确：早期只核哈希，一份只剩 close 列的 CSV 也能
        # verified=True 通过，而下游默认存在 open/high/low/close/volume。
        declared_fields = set(snapshot["semantics"]["fields"])
        actual = set(frame.columns)
        missing_cols = sorted(declared_fields - actual)
        extra_cols = sorted(actual - declared_fields)
        if missing_cols or extra_cols:
            mismatches.append(
                f"{rel} (fields missing={missing_cols} extra={extra_cols})"
            )
        frame["date"] = pd.to_datetime(frame["date"])
        frames[item["instrument_id"]] = frame.set_index("date")
    return LoadedSnapshot(
        directory=directory,
        snapshot=snapshot,
        frames=frames,
        verified=not mismatches,
        hash_mismatches=tuple(mismatches),
    )


def diff_snapshots(old_dir: Path | str, new_dir: Path | str) -> dict:
    """比较两次快照的标准化产物。相同请求内容不同时用它留证，不覆盖旧证据。"""
    old = load_snapshot(old_dir)
    new = load_snapshot(new_dir)
    old_h = {
        i["instrument_id"]: i["normalized"]["sha256"] for i in old.snapshot["instruments"]
    }
    new_h = {
        i["instrument_id"]: i["normalized"]["sha256"] for i in new.snapshot["instruments"]
    }
    changed: dict[str, dict] = {}
    for symbol in sorted(set(old_h) & set(new_h)):
        if old_h[symbol] == new_h[symbol]:
            continue
        a, b = old.frames[symbol], new.frames[symbol]
        common = a.index.intersection(b.index)
        differing = [
            str(d.date())
            for d in common
            if not a.loc[d].equals(b.loc[d])
        ]
        changed[symbol] = {
            "old_sha256": old_h[symbol],
            "new_sha256": new_h[symbol],
            "rows_old": int(len(a)),
            "rows_new": int(len(b)),
            "dates_only_in_old": [str(d.date()) for d in a.index.difference(b.index)],
            "dates_only_in_new": [str(d.date()) for d in b.index.difference(a.index)],
            "dates_with_changed_values": differing,
            "classification": (
                "historical_revision" if differing else "append_only"
            ),
        }
    return {
        "old": str(old.directory),
        "new": str(new.directory),
        "instruments_only_in_old": sorted(set(old_h) - set(new_h)),
        "instruments_only_in_new": sorted(set(new_h) - set(old_h)),
        "changed": changed,
        "identical": not changed
        and set(old_h) == set(new_h),
        "note": (
            "dates_with_changed_values 非空即历史修订，须保留新旧两份快照与本差异；"
            "仅新增未来日期为 append_only。"
        ),
    }


# --------------------------------------------------------------------------
# 定义与调用绑定
# --------------------------------------------------------------------------


class BindingRejected(RuntimeError):
    """本批数据不满足所声明对象的输入契约。"""


def bind_definitions(
    *,
    registry: dict,
    refs: Sequence[str],
    provided_fields: Iterable[str] | None = None,
    declared_currency: str = "CNY",
    purpose: str | None = None,
    snapshot: dict | None = None,
) -> dict:
    """把本批数据绑定到**精确的 ``id@version``**，并如实判断能否直接满足。

    判定方式是机械的，不解释卡里的散文：对象的 ``input.fields`` 必须是本批
    实际提供字段的子集，才算**直接可满足**；否则列出缺什么。

    这样做的目的是防止贴标签——例如名义价并不能直接满足
    ``mixed.momentum.raw@1.0.0``（它要的是 ``economic_index``），
    只有真正被调用并测试过的能力才可以标「已接入」。

    ``registry``
        由 :func:`lei_signal.research.definitions.load_registry` 读入，
        **不在此另建第二份登记表**。
    ``purpose``
        传入时由 ``resolve`` 强制校验 ``uses``/``not_for``。
    ``snapshot``
        实际快照。给出时**从它读取字段与币种**，而不是套用
        ``NORMALIZED_FIELDS`` 常量——否则快照字段与常量不符时，
        绑定判定会建立在错误前提上。
    """
    from lei_signal.research import definitions as d
    from lei_signal.research.factor_runtime import contract_digest

    if snapshot is not None:
        sem = snapshot["semantics"]
        provided = set(provided_fields or sem["fields"]) | {"symbol"}
        declared_currency = sem.get("currency", declared_currency)
    else:
        provided = set(provided_fields or NORMALIZED_FIELDS) | {"symbol"}
    out: dict[str, dict] = {}
    for ref in refs:
        if "@" not in ref:
            raise BindingRejected(f"必须使用精确 id@version，收到 {ref!r}")
        try:
            card = d.resolve(registry, ref, purpose) if purpose else d.resolve(registry, ref)
        except Exception as exc:  # noqa: BLE001 - 未知/错版本/用途不符都在此暴露
            out[ref] = {
                "resolved": False,
                "error": f"{type(exc).__name__}: {exc}",
                "directly_satisfiable": False,
            }
            continue

        card_input = card.get("input", {})
        required = set(card_input.get("fields", []))
        missing = sorted(required - provided)
        currency_prose = str(card_input.get("currency", ""))
        currency_ok = declared_currency in currency_prose
        dimensionless = "无量纲" in currency_prose

        reasons: list[str] = []
        if missing:
            reasons.append(f"缺少输入字段 {missing}")
        if dimensionless:
            reasons.append("该对象的单位是无量纲比值，不接受价格行作为直接输入")
        elif not currency_ok:
            reasons.append(
                f"币种不匹配：本批声明 {declared_currency}，卡片声明 {currency_prose!r}"
            )

        out[ref] = {
            "resolved": True,
            "id": card["id"],
            "version": card["version"],
            "type": card["type"],
            "uses": card.get("uses", []),
            "not_for": card.get("not_for", []),
            "contract_digest": contract_digest(card),
            "required_fields": sorted(required),
            "missing_fields": missing,
            "directly_satisfiable": not reasons,
            "reasons": reasons,
        }
    return {
        "provided_fields": sorted(provided),
        "declared_currency": declared_currency,
        "purpose": purpose,
        "bindings": out,
        "note": (
            "directly_satisfiable=false 不是错误，而是如实说明本批数据还不足以"
            "直接喂给该对象；只有真正被调用并测试过的能力才可标「已接入」。"
        ),
    }


__all__ = [
    "TRANSFORM_VERSION",
    "SNAPSHOT_SCHEMA_VERSION",
    "DEFAULT_SNAPSHOT_USES",
    "DEFAULT_SNAPSHOT_NOT_FOR",
    "NORMALIZED_FIELDS",
    "BudgetExceeded",
    "AcquisitionFailed",
    "FetchBudget",
    "RequestSpec",
    "SnapshotResult",
    "LoadedSnapshot",
    "DataUnavailableError",
    "fresh_dir",
    "acquire_prices",
    "import_prices",
    "load_snapshot",
    "diff_snapshots",
    "bind_definitions",
    "BindingRejected",
]
