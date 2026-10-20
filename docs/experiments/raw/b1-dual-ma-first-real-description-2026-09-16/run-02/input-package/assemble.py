"""510300 离线拼接：七份原始响应 → 单一 prices 行序列（确定性、只读原件）。

只做身份核验与确定性合并，不计算任何收益/因子/状态。价格以原始字符串输出，
禁止舍入或修改。规则：
- 文件缺失/哈希不符（篡改）拒绝；code != 0 拒绝；
- 缺 qfqday 字段拒绝，不回退 day 名义价；
- 非正/非有限开收高低拒绝（量只按原字符串携带）；
- 同日同值（全字段一致）去重；同日任何字段不同即冲突拒绝；
- 缺必需交易日拒绝；覆盖窗口（sessions 首末之间）内出现非交易日报价 → 隔离
  列明于 audit，不自动剔除后宣称合格（audit["complete"]=False，待判定）；
  窗口之外的合法交易日数据不属本包范围，记 out_of_window 供审计，不算异常。

接口：``assemble(entries, base_dir, sessions) -> (rows, audit)``。
entries 为 fetch-manifest 中 symbol=sh510300 的记录；sessions 为必需交易日
字符串集合（由已核日历逐日推导，本函数不读日历、不联网）。
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROW_FIELDS = ("date", "open", "close", "high", "low", "volume")


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _positive_finite(text: str, label: str) -> None:
    try:
        v = float(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} 不是数值：{text!r}") from exc
    _require(math.isfinite(v) and v > 0, f"{label} 非正/非有限：{text!r}")


def assemble(entries: list[dict], base_dir, sessions) -> tuple[list[list[str]], dict]:
    base = Path(base_dir)
    required = {str(s) for s in sessions}
    by_date: dict[str, list[str]] = {}
    duplicates = 0
    inputs = []
    for entry in entries:
        path = base / str(entry["file"])
        _require(path.is_file(), f"原件缺失：{entry['file']}")
        actual = _sha256(path)
        _require(actual == entry["sha256"],
                 f"原件哈希不符（文件篡改拒绝）：{entry['file']}")
        payload = json.loads(path.read_text())
        _require(payload.get("code") == 0, f"{entry['file']} code != 0")
        node = (payload.get("data") or {}).get(entry["symbol"]) or {}
        _require("qfqday" in node,
                 f"{entry['file']} 缺 qfqday 字段（拒绝，不回退 day 名义价）")
        n_rows = 0
        for raw in node["qfqday"]:
            _require(len(raw) >= 6, f"{entry['file']} 行字段不足：{raw!r}")
            row = [str(raw[i]) for i in range(6)]
            date = row[0]
            for label, val in zip(("open", "close", "high", "low"), row[1:5],
                                  strict=True):
                _positive_finite(val, f"{entry['file']} {date} {label}")
            if date in by_date:
                _require(by_date[date] == row,
                         f"同日冲突拒绝：{date}（{by_date[date]!r} vs {row!r}）")
                duplicates += 1
            else:
                by_date[date] = row
            n_rows += 1
        inputs.append({"file": entry["file"], "sha256": actual, "rows": n_rows,
                       "retrieved_at": entry.get("retrieved_at")})
    lo, hi = min(required), max(required)
    extra = sorted(d for d in by_date if lo <= d <= hi and d not in required)
    out_of_window = sorted(d for d in by_date if d < lo or d > hi)
    missing = sorted(d for d in required if d not in by_date)
    _require(not missing, f"缺交易日拒绝（先列5）：{missing[:5]}")
    rows = [by_date[d] for d in sorted(by_date) if d in required]
    audit = {
        "inputs": inputs,
        "unique_dates": len(by_date),
        "duplicates_deduped": duplicates,
        "missing_sessions": missing,
        "extra_rows_quarantined": [by_date[d] for d in extra],
        "out_of_window_rows": len(out_of_window),
        "out_of_window_note": "覆盖窗口之外的合法交易日数据，不属本包范围，不算异常",
        "selected_rows": len(rows),
        "required_sessions": len(required),
        "complete": not extra and not missing,
    }
    return rows, audit
