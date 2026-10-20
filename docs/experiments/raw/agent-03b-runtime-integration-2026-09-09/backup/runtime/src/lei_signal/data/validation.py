"""行情数据校验：日期严格递增、OHLC 合法、复权口径明确。

数据错误必须显式报错或标记 DATA_UNAVAILABLE，禁止静默处理为「无信号」。
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


class DataUnavailableError(ValueError):
    """行情不可用。界面必须显示 DATA_UNAVAILABLE，不得当作无信号。"""

    code = "DATA_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """校验结果，用于界面展示数据质量。"""

    symbol: str = ""
    rows: int = 0
    first_date: pd.Timestamp | None = None
    last_date: pd.Timestamp | None = None
    adjusted: bool = False
    provider: str = ""
    duplicates_removed: int = 0
    warnings: tuple[str, ...] = ()
    reason: str = ""

    @property
    def is_sufficient_for_color(self) -> bool:
        """三色至少需要 21 根。"""
        return self.rows >= 21


def validate_bars(
    frame: pd.DataFrame,
    *,
    symbol: str,
    provider: str,
    adjusted: bool,
    min_rows: int = 1,
) -> tuple[pd.DataFrame, ValidationReport]:
    """校验并规范化行情。

    做的事：字段完整性、类型、日期升序去重、OHLC 关系合法性。
    不做的事：不填补缺失价格、不平滑异常值——发现问题即报错或告警。
    """
    if frame is None or frame.empty:
        raise DataUnavailableError(f"没有找到 {symbol} 的日线行情，请检查代码和市场后缀")

    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise DataUnavailableError(f"{symbol} 行情字段不完整: {', '.join(missing)}")

    result = frame[list(REQUIRED_COLUMNS)].copy()
    for column in REQUIRED_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    if not isinstance(result.index, pd.DatetimeIndex):
        result.index = pd.to_datetime(result.index)
    if result.index.tz is not None:
        result.index = result.index.tz_localize(None)
    result.index = result.index.normalize()
    result.index.name = "date"

    warnings: list[str] = []

    # 收盘价缺失的行无法参与任何规则判断，明确剔除并告警。
    close_missing = int(result["close"].isna().sum())
    if close_missing:
        warnings.append(f"剔除 {close_missing} 行收盘价缺失记录")
        result = result[result["close"].notna()]

    before = len(result)
    result = result[~result.index.duplicated(keep="last")]
    duplicates_removed = before - len(result)
    if duplicates_removed:
        warnings.append(f"剔除 {duplicates_removed} 个重复交易日")

    result = result.sort_index()

    if result.empty:
        raise DataUnavailableError(f"{symbol} 清洗后没有可用行情")

    # OHLC 关系必须合法。数据源错误不能静默通过。
    illegal = result[
        (result["high"] < result["low"])
        | (result["high"] < result["close"])
        | (result["low"] > result["close"])
        | (result["high"] < result["open"])
        | (result["low"] > result["open"])
    ]
    if not illegal.empty:
        first_bad = illegal.index[0].date()
        raise DataUnavailableError(
            f"{symbol} 行情存在非法 OHLC 关系，最早出现在 {first_bad}，共 {len(illegal)} 行"
        )

    if (result[["open", "high", "low", "close"]] <= 0).to_numpy().any():
        raise DataUnavailableError(f"{symbol} 行情存在非正价格，无法用于均线计算")

    negative_volume = int((result["volume"].fillna(0) < 0).sum())
    if negative_volume:
        warnings.append(f"{negative_volume} 行成交量为负，已置零")
        result.loc[result["volume"] < 0, "volume"] = 0.0
    result["volume"] = result["volume"].fillna(0.0)

    if not adjusted:
        warnings.append("行情未复权：分红拆股可能造成虚假的颜色切换")

    if len(result) < min_rows:
        raise DataUnavailableError(
            f"{symbol} 只有 {len(result)} 根日K线，至少需要 {min_rows} 根"
        )

    report = ValidationReport(
        symbol=symbol,
        rows=len(result),
        first_date=result.index[0],
        last_date=result.index[-1],
        adjusted=adjusted,
        provider=provider,
        duplicates_removed=duplicates_removed,
        warnings=tuple(warnings),
    )
    return result, report


def detect_unadjusted_gaps(
    frame: pd.DataFrame,
    threshold: float = 0.25,
) -> tuple[pd.Timestamp, ...]:
    """检测疑似未复权造成的跳空（复权校验）。

    单日收盘变动超过阈值且成交量未同步放大，通常是除权而非真实行情。
    返回可疑日期供界面告警；不自动修改价格。
    """
    if len(frame) < 25:
        return ()
    change = frame["close"].pct_change()
    volume_ratio = frame["volume"] / frame["volume"].rolling(20, min_periods=20).mean()
    suspicious = frame.index[
        (change.abs() > threshold) & (volume_ratio.fillna(0) < 1.2)
    ]
    return tuple(suspicious)


__all__ = [
    "REQUIRED_COLUMNS",
    "DataUnavailableError",
    "ValidationReport",
    "detect_unadjusted_gaps",
    "validate_bars",
]
