"""Parquet 行情与特征缓存。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

DEFAULT_CACHE_DIR = Path.home() / ".lei_signal_lab" / "cache"


@dataclass(frozen=True, slots=True)
class CacheEntry:
    path: Path
    rows: int
    fetched_at: datetime


class ParquetCache:
    """按 symbol 存储行情与每日特征。

    缓存只是加速手段：读取时校验列完整性，损坏即视为未命中并重新获取，
    不把损坏数据当作有效行情。
    """

    def __init__(self, root: Path | str | None = None) -> None:
        self._root = Path(root) if root else DEFAULT_CACHE_DIR
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str, kind: str) -> Path:
        safe = symbol.replace("/", "_").replace("\\", "_")
        return self._root / f"{safe}.{kind}.parquet"

    def write(self, symbol: str, frame: pd.DataFrame, *, kind: str = "bars") -> CacheEntry:
        path = self._path(symbol, kind)
        payload = frame.copy()
        payload.attrs = {}
        payload.to_parquet(path, index=True)
        return CacheEntry(path=path, rows=len(payload), fetched_at=datetime.now(UTC))

    def read(
        self,
        symbol: str,
        *,
        kind: str = "bars",
        required_columns: tuple[str, ...] = (),
    ) -> pd.DataFrame | None:
        path = self._path(symbol, kind)
        if not path.exists():
            return None
        try:
            frame = pd.read_parquet(path)
        except Exception:  # noqa: BLE001 - 损坏缓存视为未命中
            return None
        if required_columns and not set(required_columns).issubset(frame.columns):
            return None
        if frame.empty:
            return None
        return frame

    def age_seconds(self, symbol: str, *, kind: str = "bars") -> float | None:
        path = self._path(symbol, kind)
        if not path.exists():
            return None
        return (datetime.now(UTC).timestamp() - path.stat().st_mtime)

    def clear(self, symbol: str | None = None) -> int:
        pattern = "*.parquet" if symbol is None else f"{symbol}.*.parquet"
        removed = 0
        for path in self._root.glob(pattern):
            path.unlink()
            removed += 1
        return removed


__all__ = ["DEFAULT_CACHE_DIR", "CacheEntry", "ParquetCache"]
