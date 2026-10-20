"""研究专用的产品身份映射（第二轮）。

问题背景（实测，非推测）
------------------------
冻结输入 ``prices.csv`` 用 ``510300.SH``；本仓库
``data/symbols.py::resolve_symbol`` 的规范形式是 ``510300.SS``，且把 ``.SH``
判为 ``other`` / 非 A 股。两套写法各自内部自洽，但**按代码 join 会得到空交集
且不报错**——这是静默污染路径。

问题的性质是**代码形式（后缀写法）**，不是交易所识别错误，也不是产品身份错误：
``510300.SH`` 与 ``510300.SS`` 指同一只产品（上交所 510300），只是后缀约定不同。
本模块只解决这一层，**不声称**价格口径、公司行动或历史可得时间因此合格。

边界
----
- **只读**：不修改生产 ``resolve_symbol``，不修改任何冻结输入。
- **显式**：本轮 14 只产品逐一登记，不做全局字符串替换冒充身份核验。
- **拒绝而非猜测**：未知交易所、歧义、重复身份、冲突映射一律报错或降级。
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from lei_signal.data.symbols import is_a_share, resolve_symbol

#: 本轮显式登记的产品。键是六位裸码，值是交易所。
#: 依据：``research-rotation-clean-2026-09-09/full-pool-preparation/candidate-pool.json``
#: 的 14 个 candidates；此处只登记身份，不复制其它字段。
REGISTERED_PRODUCTS: dict[str, str] = {
    "510300": "SSE",
    "512400": "SSE",
    "512890": "SSE",
    "515880": "SSE",
    "515300": "SSE",
    "515050": "SSE",
    "515130": "SSE",
    "518850": "SSE",
    "588000": "SSE",
    "515170": "SSE",
    "516220": "SSE",
    "562590": "SSE",
    "513870": "SSE",
    "159652": "SZSE",
}

#: 后缀写法 → 交易所。``.SH`` 是冻结输入的来源格式，``.SS`` 是仓库规范格式。
_SUFFIX_TO_EXCHANGE: dict[str, str] = {
    "SH": "SSE",
    "SS": "SSE",
    "SZ": "SZSE",
}

#: 交易所 → 仓库规范后缀。
_EXCHANGE_TO_CANONICAL_SUFFIX: dict[str, str] = {
    "SSE": "SS",
    "SZSE": "SZ",
}


class IdentityError(ValueError):
    """身份无法确定。绝不猜测，绝不静默降级为「原样通过」。"""


@dataclass(frozen=True)
class ProductIdentity:
    """一个产品的三层身份，原始写法与规范写法并存，互不覆盖。"""

    raw: str
    """输入中出现的原始代码，逐字保留。"""

    bare_code: str
    """六位裸码。"""

    exchange: str
    """``SSE`` / ``SZSE``。"""

    canonical: str
    """仓库规范写法（``resolve_symbol`` 可识别）。"""

    source_format: str
    """原始后缀写法，如 ``SH``。"""

    registered: bool
    """是否在本轮显式登记的 14 只之内。"""

    repo_resolvable: bool
    """规范写法能否被生产 ``resolve_symbol`` 判为 A 股。"""

    def to_dict(self) -> dict:
        return {
            "raw": self.raw,
            "bare_code": self.bare_code,
            "exchange": self.exchange,
            "canonical": self.canonical,
            "source_format": self.source_format,
            "registered": self.registered,
            "repo_resolvable": self.repo_resolvable,
        }


def parse_identity(raw: str, *, require_registered: bool = True) -> ProductIdentity:
    """解析单个代码。无法确定身份时抛 :class:`IdentityError`，不返回猜测值。"""
    if not isinstance(raw, str) or not raw.strip():
        raise IdentityError(f"空代码或非字符串：{raw!r}")
    token = raw.strip()

    if "." not in token:
        raise IdentityError(
            f"{token!r} 缺少交易所后缀。研究层不按前缀猜交易所——"
            "六位码在不同市场可能重复，猜测会造成错误合并"
        )
    code, _, suffix = token.partition(".")
    suffix = suffix.upper()

    if not (code.isdigit() and len(code) == 6):
        raise IdentityError(f"{token!r} 的代码部分不是六位数字")
    if suffix not in _SUFFIX_TO_EXCHANGE:
        raise IdentityError(
            f"{token!r} 的后缀 {suffix!r} 未登记。已知：{sorted(_SUFFIX_TO_EXCHANGE)}"
        )

    exchange = _SUFFIX_TO_EXCHANGE[suffix]
    registered = code in REGISTERED_PRODUCTS
    if registered and REGISTERED_PRODUCTS[code] != exchange:
        raise IdentityError(
            f"{token!r} 的后缀指向 {exchange}，但登记表记录 {code} 属于 "
            f"{REGISTERED_PRODUCTS[code]}——冲突，拒绝映射"
        )
    if require_registered and not registered:
        raise IdentityError(
            f"{code} 不在本轮显式登记的 {len(REGISTERED_PRODUCTS)} 只产品内。"
            "研究层不接受未登记产品，避免误把别的产品并进来"
        )

    canonical = f"{code}.{_EXCHANGE_TO_CANONICAL_SUFFIX[exchange]}"
    try:
        info = resolve_symbol(canonical)
        repo_ok = is_a_share(info)
    except Exception:  # noqa: BLE001 - 解析失败即视为不可识别
        repo_ok = False

    return ProductIdentity(
        raw=token,
        bare_code=code,
        exchange=exchange,
        canonical=canonical,
        source_format=suffix,
        registered=registered,
        repo_resolvable=repo_ok,
    )


def build_mapping(
    raws: Iterable[str], *, require_registered: bool = True
) -> dict[str, ProductIdentity]:
    """批量解析并检查**重复身份**：两个不同原始代码映射到同一规范身份即报错。"""
    out: dict[str, ProductIdentity] = {}
    seen: dict[str, str] = {}
    for raw in raws:
        identity = parse_identity(raw, require_registered=require_registered)
        if raw in out:
            raise IdentityError(f"输入中出现重复代码：{raw!r}")
        prior = seen.get(identity.canonical)
        if prior is not None:
            raise IdentityError(
                f"{raw!r} 与 {prior!r} 映射到同一规范身份 {identity.canonical!r}——"
                "重复身份，拒绝合并"
            )
        seen[identity.canonical] = raw
        out[raw] = identity
    return out


@dataclass(frozen=True)
class MappingAudit:
    """映射前后的可核对账：产品数、行数、日期覆盖必须一一对上。"""

    products_before: int
    products_after: int
    rows_before: int
    rows_after: int | None
    """映射**输出侧**实际行数。

    只有调用方把映射后的数据传进来才能得到真值；没传时为 ``None``，
    表示**该项未核对**——不能用 ``rows_after = rows_before`` 假装核过。
    """

    first_date: str | None
    last_date: str | None
    unmapped: tuple[str, ...]
    empty_intersection: bool
    rows_verified: bool = False
    note: str = ""

    @property
    def balanced(self) -> bool:
        """产品数与已映射项都对得上，**且行数经过实际核对**。"""
        return (
            self.products_before == self.products_after
            and self.rows_verified
            and self.rows_before == self.rows_after
            and not self.unmapped
        )

    def to_dict(self) -> dict:
        return {
            "products_before": self.products_before,
            "products_after": self.products_after,
            "rows_before": self.rows_before,
            "rows_after": self.rows_after,
            "rows_verified": self.rows_verified,
            "first_date": self.first_date,
            "last_date": self.last_date,
            "unmapped": list(self.unmapped),
            "empty_intersection": self.empty_intersection,
            "balanced": self.balanced,
            "note": self.note,
        }


def audit_mapping(
    frames_by_raw: Mapping[str, object],
    mapping: Mapping[str, ProductIdentity],
    *,
    counterpart_symbols: Sequence[str] | None = None,
    mapped_frames: Mapping[str, object] | None = None,
) -> MappingAudit:
    """核对映射前后账目，并显式检测**空交集**。

    ``counterpart_symbols``
        另一侧数据的代码列表（例如仓库口径抓来的 ``.SS``）。给出时会检查
        按规范身份是否至少有一个共同产品——空交集必须被报告，不能静默。
    ``mapped_frames``
        映射**之后**的数据（键为规范身份）。**只有传入它，行数才算真核对过**；
        不传则 ``rows_after=None``、``rows_verified=False``、``balanced=False``。
        早期版本把 ``rows_after`` 直接写成 ``rows_before``，那样这个核对永远
        不可能失败——一个不可能失败的核对不是核对。
    """
    rows_before = 0
    first: str | None = None
    last: str | None = None
    for frame in frames_by_raw.values():
        n = len(frame)  # type: ignore[arg-type]
        rows_before += n
        idx = getattr(frame, "index", None)
        if idx is not None and n:
            lo, hi = str(min(idx))[:10], str(max(idx))[:10]
            first = lo if first is None or lo < first else first
            last = hi if last is None or hi > last else last

    unmapped = tuple(sorted(set(frames_by_raw) - set(mapping)))
    empty = False
    note = ""
    if counterpart_symbols is not None:
        ours = {i.canonical for i in mapping.values()}
        theirs: set[str] = set()
        for s in counterpart_symbols:
            try:
                theirs.add(parse_identity(s, require_registered=False).canonical)
            except IdentityError:
                continue
        shared = ours & theirs
        empty = not shared
        note = (
            f"与对侧共有产品 {len(shared)} 个"
            if shared
            else "与对侧规范身份空交集——按代码合并将得到空结果，必须先统一写法"
        )

    rows_after: int | None = None
    rows_verified = False
    if mapped_frames is not None:
        rows_after = sum(len(f) for f in mapped_frames.values())  # type: ignore[arg-type]
        rows_verified = True

    return MappingAudit(
        products_before=len(frames_by_raw),
        products_after=len(mapping),
        rows_before=rows_before,
        rows_after=rows_after,
        first_date=first,
        last_date=last,
        unmapped=unmapped,
        empty_intersection=empty,
        rows_verified=rows_verified,
        note=note,
    )


__all__ = [
    "REGISTERED_PRODUCTS",
    "IdentityError",
    "ProductIdentity",
    "MappingAudit",
    "parse_identity",
    "build_mapping",
    "audit_mapping",
]
