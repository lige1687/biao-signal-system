"""Parquet 行情与特征缓存。

缓存来源标记（防污染）
--------------------
缓存文件名只由 symbol 决定，因此任何写入方都可能占用真实标的的名字。
曾经发生过的真实事故：合成测试行情落进 ``159915.SZ.bars.parquet``，
起点恰好 100.0、``open == close``，而真实创业板 ETF 在 3 元附近——
离线兜底读到它之后，分析结论看起来完全正常，实际毫无意义。

因此每次写入都会生成一个同名 ``.meta.json`` 旁文件记录 ``provider``。
读取时：
  * 没有 meta（老缓存或手工塞入）→ 视为未命中
  * provider 属于非行情源（fixture / synthetic / upload / 缓存自身）→ 视为未命中

宁可回退到「取不到数据」并显式报错，也不允许把来源不明的行情
当成真实行情喂进分析管线。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

DEFAULT_CACHE_DIR = Path.home() / ".lei_signal_lab" / "cache"

#: 不可作为「真实行情」信任的来源。合成/上传/夹具数据即便落了盘，
#: 也不得在离线兜底时冒充行情源。
UNTRUSTED_PROVIDERS = frozenset(
    {"fixture", "synthetic", "upload", "parquet_cache", "unknown", ""}
)


@dataclass(frozen=True, slots=True)
class CacheEntry:
    path: Path
    rows: int
    fetched_at: datetime


class ParquetCache:
    """按 symbol 存储行情与每日特征。

    缓存只是加速手段：读取时校验列完整性与来源标记，
    损坏或来源不可信即视为未命中并重新获取，不把它当作有效行情。
    """

    def __init__(self, root: Path | str | None = None) -> None:
        self._root = Path(root) if root else DEFAULT_CACHE_DIR
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str, kind: str) -> Path:
        safe = symbol.replace("/", "_").replace("\\", "_")
        return self._root / f"{safe}.{kind}.parquet"

    def _meta_path(self, symbol: str, kind: str) -> Path:
        return self._path(symbol, kind).with_suffix(".meta.json")

    def write(
        self,
        symbol: str,
        frame: pd.DataFrame,
        *,
        kind: str = "bars",
        provider: str = "unknown",
    ) -> CacheEntry:
        """写入缓存并记录来源。

        ``provider`` 必须是真实取数来源的名字（如 ``eastmoney`` / ``sina``）。
        默认值 ``unknown`` 属于不可信来源——即写得进去，也读不出来，
        以此迫使调用方显式声明来源。
        """
        path = self._path(symbol, kind)
        payload = frame.copy()
        payload.attrs = {}
        payload.to_parquet(path, index=True)
        fetched_at = datetime.now(UTC)
        meta = {
            "symbol": symbol,
            "kind": kind,
            "provider": provider,
            "rows": int(len(payload)),
            "fetched_at": fetched_at.isoformat(),
        }
        if len(payload):
            meta["first_date"] = str(payload.index[0])
            meta["last_date"] = str(payload.index[-1])
        self._meta_path(symbol, kind).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return CacheEntry(path=path, rows=len(payload), fetched_at=fetched_at)

    def read_meta(self, symbol: str, *, kind: str = "bars") -> dict | None:
        """读取来源标记；不存在或损坏返回 None。"""
        meta_path = self._meta_path(symbol, kind)
        if not meta_path.exists():
            return None
        try:
            loaded = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return loaded if isinstance(loaded, dict) else None

    def read(
        self,
        symbol: str,
        *,
        kind: str = "bars",
        required_columns: tuple[str, ...] = (),
        require_trusted_provider: bool = True,
    ) -> pd.DataFrame | None:
        path = self._path(symbol, kind)
        if not path.exists():
            return None
        if require_trusted_provider:
            meta = self.read_meta(symbol, kind=kind)
            # 没有来源标记的缓存不可信：无法区分真实行情与合成数据。
            if meta is None:
                return None
            provider = str(meta.get("provider", "")).strip().lower()
            if provider in UNTRUSTED_PROVIDERS:
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
        """删除缓存（含来源标记）。返回删除的 parquet 文件数。"""
        pattern = "*.parquet" if symbol is None else f"{symbol}.*.parquet"
        removed = 0
        for path in self._root.glob(pattern):
            path.unlink()
            removed += 1
        meta_pattern = "*.meta.json" if symbol is None else f"{symbol}.*.meta.json"
        for meta in self._root.glob(meta_pattern):
            meta.unlink()
        return removed


__all__ = [
    "DEFAULT_CACHE_DIR",
    "UNTRUSTED_PROVIDERS",
    "CacheEntry",
    "ParquetCache",
]
