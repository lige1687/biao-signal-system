"""B1 固定合同与数据资格（先验证，后计算）。

两层校验，分工明确：
- ``validate_b1_protocol``：运行协议必须与本模块**常量**逐值相符——固定对象、
  510300、窗口、offsets、锚点、截止、目标公式、数据声明、固定输入身份、
  必需代码键哈希。不允许自填 approval=true、换 symbol/窗口/对象/label/mode/
  anchor、裁剪必需键或删校验清单绕过。CLI 只接受正式版本文件，草案拒绝。
- ``load_verified_input``：按（已通过校验的）合同中的输入身份逐项核验输入包：
  manifest 哈希→全部包内键/哈希→CSV 与日历内容→原件身份及声明。manifest 的
  complete 只是声明，不能替代核验；使用包内 calendar，不偷换外部最新日历。

退出语义：身份/结构错误抛 ValueError（CLI→3）；资料不完整抛
B1IncompleteError（CLI→2）；两者都不得留下成功 manifest 或状态/目标文件。
模块导入不计算、不写盘；调用方须在验证完毕后才加载真实计算路径。
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

import pandas as pd

# ── 固定输入身份（主控裁决指定；不得自改 manifest 后自证） ─────────────
FIXED_INPUT_IDENTITY = {
    "package": "docs/experiments/raw/510300-offline-reuse-2026-09-15/run-02",
    "prices_csv_sha256": "bc8582af3ac7b4c2f00a5b51d81754606179347cc3811c911d7579242cb56703",
    "manifest_sha256": "8d39a83eec833c13f14ee78ad36899b6ae49f32f64b024c33ee75474bc3a6ae7",
    "calendar_sha256": "aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1",
    "fetch_manifest_sha256": "5ba8a51d93dcca331204b4df71aa47f5b15a76dedee8ee3ab951689e0979f0c4",
}

#: 必需代码键（实现常量，协议不可裁剪；额外本地计算依赖加入集合并记录）
REQUIRED_CODE_KEYS = (
    "src/lei_signal/research/factor_unit/__init__.py",
    "src/lei_signal/research/factor_unit/description_core.py",
    "src/lei_signal/research/factor_unit/state_description.py",
    "src/lei_signal/research/factor_unit/b1_contract.py",
    "src/lei_signal/research/factor_unit/b1_description.py",
    "scripts/run_b1_dual_ma_description.py",
    "src/lei_signal/research/factor_unit/close_state.py",
    "src/lei_signal/research/trading_calendar.py",
    "src/lei_signal/features/indicators.py",
    "src/lei_signal/rules/dual_ma.py",
    "src/lei_signal/rules/lei_color.py",
    "src/lei_signal/domain/rules_config.py",
    "src/lei_signal/domain/types.py",
    "src/lei_signal/domain/canonical.py",
    "src/lei_signal/events/log.py",
    "configs/rules.v2.yaml",
)

CARD_PATH = (
    "docs/experiments/raw/factor-research-workbench-v1-2026-09-14/"
    "candidate-card-dual-ma-bull-state-draft-1.md"
)
CARD_SHA256 = "907d17631e27011423bebbf068bcb2bbc6e1b44a184618597cf54f868e066dc1"
TASK_BOOK = {
    "path": "docs/superpowers/plans/2026-09-16-b1-dual-ma-first-real-description.md",
    "sha256": "0afb4ae14920b4c04207458763df9df02ae05bfe43e693a9289c604214770e89",
}

FIXED_PARAMS = {
    "family": "B1-dual-ma-unit",
    "use": "post_hoc_historical_description",
    "object_ref": "candidate:lei.dual_ma.bull_state@draft-1",
    "symbol": "510300",
    "source_symbol_mapping": {"sh510300": "510300"},
    "evaluation_window": {"start": "2019-10-08", "end": "2025-12-31"},
    "lookback": 20,
    "e_offset": 1,
    "x_offset": 22,
    "ema_seed_sessions": 20,
    "ema_alpha": "2/21",
    "warmup_sessions": 20,
    "label_maturity_cutoff": "2026-02-03T15:00:00+08:00",
    "session_close": "15:00",
    "timezone": "Asia/Shanghai",
    "sparse_anchor_session": "2019-10-08",
    "sparse_step": 23,
    "target_basis": "vendor_adjusted_price_change",
    "target_main": "P_vendor(t+22)/P_vendor(t+1) - 1",
    "target_aux": "min(0, min(P_vendor(s)/P_vendor(t+1) - 1)), s in t+1..t+22",
    "coverage": {"start": "2019-09-02", "end": "2026-02-03"},
}

FIXED_DATA_DECLARATIONS = {
    "data_mode": "real",
    "historical_reconstruction_only": True,
    "historical_available_at": None,
    "adjustment_anchor": "unknown（精确复权锚点未证）",
    "price_basis": "vendor_qfq",
    "extracted_field": "qfqday",
    "currency": "CNY",
}

#: 当前接受的协议版本（v1.0.0 因本常量与固定输入包实际声明不符被取代，
#: 原字节保留于 raw 目录，不再受理）
SPEC_VERSION = "1.0.1"


class B1IncompleteError(Exception):
    """资料不完整（CLI 退出 2）：与身份错误（3）分开。"""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _check_fixed_pair(protocol: dict, key: str, fixed, label: str) -> None:
    got = protocol.get(key)
    _require(got == fixed, f"协议 {label or key} 必须逐值等于固定值 {fixed!r}（收到 {got!r}）")


def validate_b1_protocol(protocol_path, repo_root) -> dict:
    """校验正式运行协议；任何逐值不符抛 ValueError。返回合同 dict。"""
    root = Path(repo_root)
    p = Path(protocol_path)
    _require(p.is_file(), f"协议文件不存在：{protocol_path}")
    try:
        protocol = json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"协议不是合法JSON：{exc}") from exc
    _require(isinstance(protocol, dict), "协议必须是JSON对象")
    _require(protocol.get("spec_status") == "frozen",
             "CLI 只接受冻结正式协议（草案/草稿状态拒绝）")
    _require(protocol.get("spec_version") == SPEC_VERSION,
             f"spec_version 必须为 {SPEC_VERSION}（旧版原字节保留但不受理）")
    _require(protocol.get("approval") is not True,
             "不允许自填 approval=true（授权只来自任务书记录）")

    for key, fixed in FIXED_PARAMS.items():
        _check_fixed_pair(protocol, key, fixed, key)
    for key, fixed in FIXED_DATA_DECLARATIONS.items():
        _check_fixed_pair(protocol, key, fixed, f"数据声明 {key}")

    card = protocol.get("candidate_card") or {}
    _require(card.get("path") == CARD_PATH and card.get("sha256") == CARD_SHA256,
             "candidate_card 引用与固定卡不符")
    book = protocol.get("task_book") or {}
    _require(book.get("path") == TASK_BOOK["path"]
             and book.get("sha256") == TASK_BOOK["sha256"],
             "task_book 引用与本任务书不符")

    identity = protocol.get("input_identity") or {}
    for key, fixed in FIXED_INPUT_IDENTITY.items():
        _require(identity.get(key) == fixed,
                 f"协议 input_identity.{key} 与固定输入身份不符"
                 f"（{identity.get(key)!r} != {fixed!r}）")

    code_identity = protocol.get("code_identity")
    _require(isinstance(code_identity, dict), "code_identity 必须是 dict")
    missing = [k for k in REQUIRED_CODE_KEYS if k not in code_identity]
    _require(not missing, f"必需代码键被裁剪：{missing}")
    extra = [k for k in code_identity if k not in REQUIRED_CODE_KEYS]
    _require(not extra, f"code_identity 含未登记键（不得自行扩键）：{extra}")
    for rel in REQUIRED_CODE_KEYS:
        fp = root / rel
        _require(fp.is_file(), f"必需代码键文件缺失：{rel}")
        _require(code_identity[rel] == _sha256(fp),
                 f"必需代码键哈希不符：{rel}（代码/配置漂移拒绝；"
                 "规则加载器缓存不能掩盖配置漂移）")

    protocol["_contract"] = {
        **{k: protocol[k] for k in FIXED_PARAMS},
        **{k: protocol[k] for k in FIXED_DATA_DECLARATIONS},
        "candidate_card": card,
        "input_identity": dict(identity),
        "protocol_path": str(p),
        "protocol_sha256": _sha256(p),
    }
    return protocol["_contract"]


# ── 输入包核验 ────────────────────────────────────────────────────────

def _verify_package_integrity(pack: Path, expected_manifest_sha: str) -> dict:
    mp = pack / "manifest.json"
    _require(mp.is_file(), f"输入包缺 manifest.json：{pack}")
    _require(_sha256(mp) == expected_manifest_sha,
             "manifest 哈希与固定身份不符（不能自改manifest后自证）")
    manifest = json.loads(mp.read_text())
    listed = manifest.get("file_hashes") or {}
    actual = {str(f.relative_to(pack)) for f in pack.rglob("*")
              if f.is_file() and f.name != "manifest.json"}
    _require(set(listed) == actual,
             f"包内文件集合与 manifest 不一致（不得删键逃检查）："
             f"{sorted(set(listed) ^ actual)[:5]}")
    bad = [rel for rel, h in listed.items() if _sha256(pack / rel) != h]
    _require(not bad, f"包内文件哈希不符：{bad[:5]}")
    return manifest


def _parse_prices_csv(path: Path) -> pd.DataFrame:
    """严格解析：错列头/短行/乱码/NaN/非正/重复/乱序一律拒绝，不用 coerce。"""
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        _require(header == ["date", "open", "close", "high", "low", "volume"],
                 f"prices.csv 列头错误：{header!r}")
        raw = list(reader)
    _require(raw, "prices.csv 为空")
    dates, closes = [], []
    for i, r in enumerate(raw):
        _require(len(r) == 6, f"prices.csv 第{i + 2}行字段数错误：{r!r}")
        try:
            d = pd.Timestamp(datetime.strptime(r[0], "%Y-%m-%d"))
        except ValueError as exc:
            raise ValueError(f"prices.csv 第{i + 2}行日期乱码：{r[0]!r}") from exc
        _require(r[0] == d.strftime("%Y-%m-%d"),
                 f"prices.csv 第{i + 2}行日期格式必须严格YYYY-MM-DD：{r[0]!r}")
        vals = []
        for label, text in zip(("open", "close", "high", "low"), r[1:5], strict=True):
            try:
                v = float(text)
            except ValueError as exc:
                raise ValueError(
                    f"prices.csv 第{i + 2}行 {label} 乱码（不用coerce变缺失）：{text!r}"
                ) from exc
            _require(math.isfinite(v) and v > 0,
                     f"prices.csv 第{i + 2}行 {label} 非正/非有限：{text!r}")
            vals.append(v)
        try:
            vol = float(r[5])
        except ValueError as exc:
            raise ValueError(f"prices.csv 第{i + 2}行 volume 乱码：{r[5]!r}") from exc
        _require(math.isfinite(vol) and vol >= 0,
                 f"prices.csv 第{i + 2}行 volume 非有限/为负：{r[5]!r}")
        dates.append(d)
        closes.append(vals[1])
    idx = pd.DatetimeIndex(dates)
    _require(idx.is_unique, "prices.csv 日期重复（拒绝，不选首条/末条）")
    _require(idx.is_monotonic_increasing, "prices.csv 日期乱序（拒绝，不静默排序）")
    return pd.DataFrame({"close": closes}, index=idx)


def load_verified_input(package_path, contract: dict):
    """逐项核验输入包并返回 (prices, schedule, audit)。

    prices：DatetimeIndex + close 浮点（计算用；无效字符串/非有限/非正已拒绝）。
    schedule：session/close_at（包内日历逐日 15:00 Asia/Shanghai，不换外部日历）。
    """
    identity = contract["input_identity"]
    pack = Path(package_path)
    _require(pack.is_dir(), f"输入包目录不存在：{package_path}")
    manifest = _verify_package_integrity(pack, identity["manifest_sha256"])

    prices_path = pack / "prices.csv"
    _require(_sha256(prices_path) == identity["prices_csv_sha256"],
             "prices.csv 哈希与固定身份不符")
    cal_path = pack / "calendar.json"
    _require(_sha256(cal_path) == identity["calendar_sha256"],
             "calendar.json 哈希与固定身份不符（不偷换外部最新日历）")
    fm_path = pack / "fetch-manifest.json"
    _require(_sha256(fm_path) == identity["fetch_manifest_sha256"],
             "fetch-manifest.json 哈希与固定身份不符")

    fetch_entries = [e for e in json.loads(fm_path.read_text())
                     if e.get("symbol") == "sh510300"]
    _require(len(fetch_entries) == 7, "fetch-manifest 中 sh510300 原件必须为七份")
    retrieved_at = {}
    for e in fetch_entries:
        op = pack / "originals" / e["file"]
        _require(op.is_file(), f"原件缺失：{e['file']}")
        _require(_sha256(op) == e["sha256"], f"原件哈希不符：{e['file']}")
        ts = pd.Timestamp(e["retrieved_at"])
        _require(ts.tzinfo is not None,
                 f"{e['file']} retrieved_at 必须解析为真实带时区时间")
        retrieved_at[e["file"]] = ts.isoformat()

    quality = json.loads((pack / "quality.json").read_text())
    decl = quality.get("declarations") or {}
    for key, want in FIXED_DATA_DECLARATIONS.items():
        _require(decl.get(key) == want,
                 f"输入包声明 {key}={decl.get(key)!r} 与固定声明 {want!r} 不符")

    prices = _parse_prices_csv(prices_path)

    from lei_signal.research.trading_calendar import TradingCalendar
    cal = TradingCalendar.from_file(cal_path)
    cov = contract["coverage"]
    sessions = list(cal.trading_days(cov["start"], cov["end"]))
    _require(sessions, "覆盖区间没有任何交易日")
    have = [d.strftime("%Y-%m-%d") for d in prices.index]
    missing = [d for d in sessions if d not in set(have)]
    if missing:
        raise B1IncompleteError(
            f"输入缺交易日（先列5）：{missing[:5]}——日历集合决定完整性，不靠行数"
        )
    extra = [d for d in have if d not in set(sessions)]
    _require(not extra,
             f"输入含非交易日/窗外日期（先列5）：{extra[:5]}")
    _require(have == sessions, "输入日期序列与日历逐日推导不一致")

    schedule = pd.DataFrame({
        "session": pd.to_datetime(sessions),
        "close_at": [pd.Timestamp(f"{d}T15:00:00+08:00") for d in sessions],
    })
    audit = {
        "package": str(pack),
        "manifest_sha256": identity["manifest_sha256"],
        "prices_csv_sha256": identity["prices_csv_sha256"],
        "calendar_sha256": identity["calendar_sha256"],
        "fetch_manifest_sha256": identity["fetch_manifest_sha256"],
        "originals": {e["file"]: e["sha256"] for e in fetch_entries},
        "retrieved_at": retrieved_at,
        "retrieved_at_note": "逐原件继承的既有声明；精确请求起止仍未知，不伪造成新的请求时间",
        "rows": int(len(prices)),
        "sessions": len(sessions),
        "first_session": sessions[0],
        "last_session": sessions[-1],
        "completeness_gate": "包内日历逐日推导的交易日集合逐日比对；行数只是交叉证据",
        "manifest_complete_field": manifest.get("complete"),
        "declarations": decl,
    }
    return prices, schedule, audit
