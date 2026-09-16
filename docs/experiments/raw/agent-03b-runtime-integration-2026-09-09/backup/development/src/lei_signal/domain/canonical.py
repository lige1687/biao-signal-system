"""确定性规范化 JSON 与 SHA-256，用于生成可复现的 event_id。

移植来源
--------
旧路径 : /Users/yongbiaoli/Desktop/licai-wt-pg-integration
          src/plan_guardian/domain/canonical.py
旧commit: 2ee7fdc6f3f83fa6a787286e1f7f901b309cc666
改造原因:
  1. 删除 plan_guardian.domain.errors / ids / numbers / time 依赖，新项目不引入
     FundId、SignalAssetId 等执行域 ID 类型（复用评估 D 类：禁止移植执行映射）。
  2. 旧实现拒绝 float。信号研究的价格矩阵本身就是 float，因此改为：float 允许，
     但必须先经 `canonical_float` 定点格式化为字符串，避免 repr 漂移进入哈希。
  3. set/frozenset 仍然拒绝：迭代顺序依赖 PYTHONHASHSEED，会破坏事件 ID 可复现性。
  4. 保留「dataclass 按声明顺序、Mapping 按键排序」这两条使哈希与插入顺序无关的核心设计。
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Final

_MAX_DEPTH: Final = 64
#: 价格/比率统一保留的小数位。足以区分真实行情，又不受 float repr 尾差影响。
FLOAT_PRECISION: Final = 10

CanonicalValue = str | int | bool | None | list[Any] | dict[str, Any]


class CanonicalizationError(ValueError):
    """无法确定性序列化的输入。"""


def canonical_float(value: float) -> str:
    """把 float 定点格式化为哈希安全的字符串。

    `0.1 + 0.2` 与 `0.30000000000000004` 在 10 位定点下折叠为同一串，
    因此同样的数据重复运行必然产生同样的 event_id。
    """
    if math.isnan(value) or math.isinf(value):
        raise CanonicalizationError(f"非有限浮点数不可哈希: {value!r}")
    text = f"{value:.{FLOAT_PRECISION}f}"
    # 去掉尾随 0，使 1.10 与 1.1 折叠为同一串；但保留至少一位小数。
    if "." in text:
        text = text.rstrip("0")
        if text.endswith("."):
            text += "0"
    if text in ("-0.0", "-0"):
        text = "0.0"
    return text


def canonical_form(value: object, *, path: str = "$", depth: int = 0) -> CanonicalValue:
    """把领域值转换为可确定性序列化的形式。"""
    if depth > _MAX_DEPTH:
        raise CanonicalizationError(f"{path}: 超过最大嵌套深度 {_MAX_DEPTH}")

    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        # 必须在 int 之前判断：bool 是 int 的子类。
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return {"__f__": canonical_float(value)}
    if isinstance(value, Decimal):
        return {"__dec__": str(value.normalize())}
    if isinstance(value, Enum):
        member = value.value
        if not isinstance(member, str):
            raise CanonicalizationError(f"{path}: 枚举 {type(value).__name__} 必须使用字符串值")
        return member
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, set | frozenset):
        raise CanonicalizationError(
            f"{path}: 禁止 set/frozenset，迭代顺序不稳定；请使用已排序的 tuple"
        )
    if isinstance(value, bytes | bytearray):
        raise CanonicalizationError(f"{path}: 原始字节无法确定性编码")
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_dataclass(value, path=path, depth=depth)
    if isinstance(value, Mapping):
        return _canonical_mapping(value, path=path, depth=depth)
    if isinstance(value, Sequence):
        return [
            canonical_form(item, path=f"{path}[{index}]", depth=depth + 1)
            for index, item in enumerate(value)
        ]
    raise CanonicalizationError(f"{path}: 不支持的类型 {type(value).__name__}")


def _canonical_dataclass(value: object, *, path: str, depth: int) -> CanonicalValue:
    """按字段声明顺序序列化，而不是 dir() 顺序。"""
    if not (is_dataclass(value) and not isinstance(value, type)):
        raise CanonicalizationError(f"{path}: 需要 dataclass 实例，得到 {type(value).__name__}")
    out: dict[str, CanonicalValue] = {}
    for f in fields(value):
        if f.metadata.get("canonical") is False:
            continue
        out[f.name] = canonical_form(
            getattr(value, f.name), path=f"{path}.{f.name}", depth=depth + 1
        )
    return out


def _canonical_mapping(value: Mapping[Any, Any], *, path: str, depth: int) -> CanonicalValue:
    """序列化为按键排序的 [key, value] 对列表，使插入顺序无关。"""
    encoded: list[tuple[str, CanonicalValue]] = []
    seen: set[str] = set()
    for raw_key, raw_value in value.items():
        key_form = canonical_form(raw_key, path=f"{path}.<key>", depth=depth + 1)
        sort_key = json.dumps(key_form, sort_keys=True, ensure_ascii=False)
        if sort_key in seen:
            raise CanonicalizationError(f"{path}: 重复的规范化键 {sort_key}")
        seen.add(sort_key)
        encoded.append(
            (
                sort_key,
                [key_form, canonical_form(raw_value, path=f"{path}[{sort_key}]", depth=depth + 1)],
            )
        )
    encoded.sort(key=lambda pair: pair[0])
    return [pair[1] for pair in encoded]


def canonical_json(value: object) -> str:
    """规范化 JSON 文本：键已排序，无多余空白。"""
    return json.dumps(
        canonical_form(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_sha256(value: object) -> str:
    """规范化字节的小写十六进制 SHA-256。"""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def make_event_id(
    *,
    rule_id: str,
    rule_version: str,
    symbol: str,
    timeframe: str,
    available_date: date,
    source_id: str = "",
) -> str:
    """确定性事件 ID。

    键取自架构第 9 节：
    `rule_id + rule_version + symbol + timeframe + available_date + source_id`。
    同样数据与规则重复运行必须产生完全相同的 ID，从而使事件日志幂等。
    """
    digest = canonical_sha256(
        {
            "rule_id": rule_id,
            "rule_version": rule_version,
            "symbol": symbol,
            "timeframe": timeframe,
            "available_date": available_date,
            "source_id": source_id,
        }
    )
    return f"{rule_id}:{digest[:24]}"


__all__ = [
    "FLOAT_PRECISION",
    "CanonicalizationError",
    "canonical_float",
    "canonical_form",
    "canonical_json",
    "canonical_sha256",
    "make_event_id",
]
