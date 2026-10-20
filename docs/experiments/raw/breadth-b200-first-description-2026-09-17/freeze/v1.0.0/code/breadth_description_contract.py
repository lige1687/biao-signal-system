"""B200×510300 受限历史描述：固定身份、协议文档、协议与代码校验。

身份常量由主控冻结（执行计划 §「研究身份与用途裁定」），执行者不得更改；
``validate_protocol`` 要求协议 JSON 的身份常量与这些算法常量**逐项相等**，
不是只核对自填哈希。数据质量固定 ``restricted``：available_at 未知、历史可得
性未核验、价格逐列来源未核验；不存在“数据已合格”的自动升级。

本模块只做校验与文档构造，不做统计；读文件仅限哈希核对（只读）。
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from .breadth_description import EXCLUSION_PRIORITY

SCHEMA = "lei-signal.breadth-description-protocol/1.0.0"
PROTOCOL_ID = "breadth-b200-first-description"
PROTOCOL_VERSION = "1.0.0"
FAMILY = "breadth-unit-csi300-b200-21-v1"
USE = "restricted_post_hoc_description"

OBJECT_REFERENCE = "breadth.csi300.b200.legacy_percent@1.0.0"
OBJECT_COMPARISON = "breadth.csi300.b200.common@1.0.0"
UNIT_CONVERSION = {"from": "percent", "to": "fraction", "scale": 100}
OBJECT = {
    "reference": OBJECT_REFERENCE,
    "comparison": OBJECT_COMPARISON,
    "unit_conversion": UNIT_CONVERSION,
    "note": (
        "实际消费 legacy_percent 冻结序列并做 /100 单位转换；与 common 卡对照。"
        "不调用 common.calculate 重建宽度，不声称实际输入完全满足卡的价格/历史"
        "可知要求。"
    ),
}

SYMBOL = "510300"
EVALUATION_START = "2019-10-08"
EVALUATION_END = "2025-12-31"
CALENDAR_VERIFY_START = "2019-09-02"
CALENDAR_VERIFY_END = "2026-02-03"
DATE_WINDOW = {
    "evaluation_start": EVALUATION_START,
    "evaluation_end": EVALUATION_END,
    "calendar_verify_start": CALENDAR_VERIFY_START,
    "calendar_verify_end": CALENDAR_VERIFY_END,
}

TARGET_OFFSETS = [1, 22]
TARGET = {
    "offsets": TARGET_OFFSETS,
    "formula": "close(x)/close(e)-1",
    "unit": "fraction",
    "segments": 21,
    "note": "e = t 后第 1 个交易日收盘；x = t 后第 22 个交易日收盘。",
}

CUTOFF = "2026-09-17T00:00:00+08:00"
CALENDAR = {"timezone": "Asia/Shanghai", "decision_time": "15:00"}
STATISTICS = {
    "primary": "time_series_spearman",
    "rank_method": "average",
    "min_pairs": 3,
    "years": [2019, 2020, 2021, 2022, 2023, 2024, 2025],
    "year_assignment": "observation_date_year",
    "no_p_values": True,
    "no_resampling": True,
    "note": "min_pairs 是数学核输出约定，不是统计可信阈值；不算推断。",
}
QUALITY = {
    "qualification": "restricted",
    "available_at": None,
    "historical_availability_verified": False,
    "source_price_basis": "unverified_per_column",
}
TOLERANCES = {
    "ratio_absolute": 1e-12,
    "coverage_absolute": 1e-12,
    "verification_float_absolute": 1e-12,
}
NO_CLAIMS = [
    "不宣称预测能力或交易有效性",
    "不把相关当收益、贡献、显著性或横截面IC",
    "不证明结果不是巧合；不排除过拟合；不检验非单调关系",
    "不外推为真实当时信号、因果贡献、含分红财富或交易利润",
    "源数据已被旧研究观察，不是全新未知验证资料；宽度成员变化不全是价格转强",
]
MODES = ("synthetic_test", "restricted_historical")

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_RELATIVE_PATH = (
    "docs/experiments/raw/breadth-b200-first-description-2026-09-17/"
    "freeze/v1.0.0/protocol-v1.0.0.json"
)

#: 真实分支唯一允许的四份输入（路径相对仓库根；SHA-256 与任务书一致）。
REQUIRED_INPUTS = {
    "breadth_csi300.parquet": {
        "path": "docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/"
                "prepared/breadth_csi300.parquet",
        "sha256": "63fa7f0ef837c161194fb8f1f17140069074812085c8b449b93aa4d5f2998a58",
        "role": "只消费b200及质量列",
    },
    "observations.csv": {
        "path": "docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/"
                "run-02/observations.csv",
        "sha256": "1dfe4c206212c31809f53f4b66bb40b3dd4ec193b03daf37c1540f8307eb9d5d",
        "role": "复用既有main/e_date/x_date，忽略state及其筛选字段",
    },
    "prices.csv": {
        "path": "docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/"
                "run-02/input-package/prices.csv",
        "sha256": "bc8582af3ac7b4c2f00a5b51d81754606179347cc3811c911d7579242cb56703",
        "role": "独立核对既有目标的指定供应商调整价快照",
    },
    "calendar.json": {
        "path": "docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/"
                "run-02/input-package/calendar.json",
        "sha256": "aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1",
        "role": "日历逐日推导",
    },
}

REQUIRED_SPECS = {
    "experiment-backtest-principles.md": (
        "docs/research/experiment-backtest-principles.md",
        "ac5a676c0635441b66f656c8e1249b69bade36365cc9065ed6341a610b6a53c6",
    ),
    "ai-execution-contract.md": (
        "docs/research/ai-execution-contract.md",
        "deab6c1ca20505f92d06516ffff943b8501fff2e01f8c6b3928c6626072af962",
    ),
    "definition-standard.md": (
        "docs/research/definition-standard.md",
        "3406feaea2bbb8d23a91ddc8fa0c85e62ff86437bdf443d459f2c97b0e99cd5c",
    ),
    "experiment-report-template.md": (
        "docs/research/experiment-report-template.md",
        "cae2853f81841de6f424c6bda10e6708dd35574ebb8a325088fe507c5755d54e",
    ),
    "definitions.v1.json": (
        "docs/research/definitions.v1.json",
        "c008efb991c40f06bb7fe0236b0892a6902c68a83cb4657ae5c2651e9d270e05",
    ),
}

#: 输出包文件（manifest 最后写）；哈希清单仅排除顶层 manifest 本身。
PACKAGE_FILES = (
    "pairs.csv", "pairs.meta.json", "summary.json", "overlap.json", "quality.json",
    "report.md", "protocol.source.json", "environment.json", "manifest.json",
)

_SYNTHETIC_INPUTS = {
    "mode": "synthetic_fixtures",
    "note": "合成夹具来自 --input-dir；不钉哈希，不冒充真实指定输入。",
}


class IdentityError(Exception):
    """身份/协议错误（CLI 退出码 3）。"""


class DataError(Exception):
    """资料结构/内容不满足合同（CLI 退出码 2），不做统计。"""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def protocol_document(code: dict, *, mode: str, inputs: dict | None = None) -> dict:
    """按冻结常量构造协议文档；code 为「仓库相对路径 → SHA-256」的必需代码集合。"""
    if mode not in MODES:
        raise IdentityError(f"unknown mode {mode!r}")
    return {
        "schema": SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "protocol_version": PROTOCOL_VERSION,
        "canonical_relative_path": CANONICAL_RELATIVE_PATH,
        "family": FAMILY,
        "use": USE,
        "mode": mode,
        "object": OBJECT,
        "symbol": SYMBOL,
        "date_window": DATE_WINDOW,
        "target": TARGET,
        "cutoff": CUTOFF,
        "calendar": CALENDAR,
        "statistics": STATISTICS,
        "quality": QUALITY,
        "tolerances": TOLERANCES,
        "exclusion_priority": list(EXCLUSION_PRIORITY),
        "inputs": inputs if inputs is not None else dict(_SYNTHETIC_INPUTS),
        "specs": {
            name: {"path": spec[0], "sha256": spec[1]}
            for name, spec in REQUIRED_SPECS.items()
        },
        "code": dict(code),
        "no_claims": list(NO_CLAIMS),
    }


def _diff_constant(protocol: dict, key: str, expected) -> list[str]:
    return [] if protocol.get(key) == expected else [f"protocol {key} != frozen identity"]


def validate_protocol(protocol: dict, *, mode: str, protocol_path) -> list[str]:
    """协议身份校验：常量与算法逐项相等 + 路径/输入/规范/代码结构核对。

    返回错误列表（空 = 通过）。真实分支要求四输入哈希逐一命中白名单；
    合成分支不钉输入哈希但身份常量同样强校验。
    """
    errors: list[str] = []
    errors += _diff_constant(protocol, "schema", SCHEMA)
    errors += _diff_constant(protocol, "protocol_id", PROTOCOL_ID)
    errors += _diff_constant(protocol, "protocol_version", PROTOCOL_VERSION)
    errors += _diff_constant(protocol, "family", FAMILY)
    errors += _diff_constant(protocol, "use", USE)
    errors += _diff_constant(protocol, "object", OBJECT)
    errors += _diff_constant(protocol, "symbol", SYMBOL)
    errors += _diff_constant(protocol, "date_window", DATE_WINDOW)
    errors += _diff_constant(protocol, "target", TARGET)
    errors += _diff_constant(protocol, "cutoff", CUTOFF)
    errors += _diff_constant(protocol, "calendar", CALENDAR)
    errors += _diff_constant(protocol, "statistics", STATISTICS)
    errors += _diff_constant(protocol, "quality", QUALITY)
    errors += _diff_constant(protocol, "tolerances", TOLERANCES)
    errors += _diff_constant(protocol, "exclusion_priority", list(EXCLUSION_PRIORITY))
    errors += _diff_constant(protocol, "no_claims", NO_CLAIMS)
    if mode not in MODES:
        errors.append(f"unknown mode {mode!r}")
    if protocol.get("mode") != mode:
        errors.append(f"protocol mode {protocol.get('mode')!r} != requested {mode!r}")

    canonical = protocol.get("canonical_relative_path")
    if canonical != CANONICAL_RELATIVE_PATH:
        errors.append("canonical_relative_path != frozen location")
    path = Path(protocol_path)
    resolved = str(path.resolve())
    required_tail = "freeze/v1.0.0/protocol-v1.0.0.json"
    if path.is_symlink() or not resolved.endswith(required_tail):
        errors.append(
            f"protocol file must be a version original at .../{required_tail}；"
            "current 指针不能充当协议"
        )
    if mode == "restricted_historical" and resolved != str(REPO_ROOT / CANONICAL_RELATIVE_PATH):
        errors.append("restricted protocol must be the frozen original at the canonical path")

    specs = protocol.get("specs") or {}
    for name, (spec_path, spec_sha) in REQUIRED_SPECS.items():
        entry = specs.get(name)
        if not isinstance(entry, dict) or entry.get("sha256") != spec_sha:
            errors.append(f"missing or altered spec hash: {name}")
        elif entry.get("path") != spec_path:
            errors.append(f"spec path mismatch: {name}")

    inputs = protocol.get("inputs")
    if not isinstance(inputs, dict):
        errors.append("inputs section missing")
    elif mode == "restricted_historical":
        if set(inputs) != set(REQUIRED_INPUTS):
            errors.append(
                "restricted inputs must be exactly the four whitelisted files: "
                f"{sorted(REQUIRED_INPUTS)}"
            )
        else:
            for name, required in REQUIRED_INPUTS.items():
                entry = inputs[name]
                if not isinstance(entry, dict):
                    errors.append(f"input entry malformed: {name}")
                    continue
                if entry.get("sha256") != required["sha256"]:
                    errors.append(f"input sha mismatch: {name}")
                if entry.get("path") != required["path"]:
                    errors.append(f"input path mismatch: {name}")
    else:
        if inputs.get("mode") != "synthetic_fixtures":
            errors.append("synthetic protocol must declare inputs.mode=synthetic_fixtures")

    code = protocol.get("code")
    if not isinstance(code, dict) or not code:
        errors.append("code section missing or empty")
    else:
        for key, value in code.items():
            if not isinstance(value, str) or len(value) != 64:
                errors.append(f"code entry not a sha256: {key}")
    return errors


def compute_import_closure(extra_file: str | Path | None = None) -> dict[str, str]:
    """收集执行闭包（CLI 自身 + lei_signal.research.* 模块）的原字节哈希。

    以「运行时 sys.modules + 对本地文件的 AST 静态 import 闭包」为准：静态闭包
    保证不依赖构建协议的进程恰好导入了哪些模块（缺 trading_calendar 之类的键
    会误拒）；键集不由用户手写，删键即被 :func:`verify_code_manifest` 拒绝。
    """
    import ast

    closure: dict[str, str] = {}
    queue: list[Path] = []
    if extra_file is not None:
        queue.append(Path(extra_file).resolve())
    for name, module in sorted(sys.modules.items()):
        if not name.startswith("lei_signal.research"):
            continue
        file = getattr(module, "__file__", None)
        if file:
            queue.append(Path(file).resolve())

    def enqueue_module(module_name: str) -> None:
        parts = module_name.split(".")
        if not parts or parts[0] != "lei_signal":
            return
        # 模块名直接映射到 src/ 下的包路径：lei_signal.research.x → src/lei_signal/research/x.py
        base = REPO_ROOT / "src" / Path(*parts)
        for candidate in (base.with_suffix(".py"), base / "__init__.py"):
            if candidate.exists():
                queue.append(candidate.resolve())
                return

    while queue:
        path = queue.pop(0)
        try:
            rel = str(path.relative_to(REPO_ROOT))
        except ValueError:
            continue
        if rel in closure:
            continue
        closure[rel] = sha256_file(path)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    enqueue_module(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.module:
                    enqueue_module(f"lei_signal.research.{node.module}")
                elif node.level:
                    for alias in node.names:  # from . import x
                        enqueue_module(f"lei_signal.research.{alias.name}")
                elif node.module and node.module.startswith("lei_signal"):
                    enqueue_module(node.module)
    return closure


def verify_code_manifest(actual: dict[str, str], declared: dict[str, str]) -> list[str]:
    """实际执行闭包必须被协议声明覆盖，且所有声明文件逐一哈希核对。"""
    errors: list[str] = []
    for rel, digest in sorted(actual.items()):
        if rel not in declared:
            errors.append(f"missing required code key: {rel}")
        elif declared[rel] != digest:
            errors.append(f"code hash mismatch: {rel}")
    for rel, digest in sorted(declared.items()):
        path = REPO_ROOT / rel
        if not path.exists():
            errors.append(f"declared code file missing: {rel}")
        elif sha256_file(path) != digest:
            errors.append(f"declared code file drifted: {rel}")
    return errors


def ensure_fresh_output_dir(path) -> Path:
    """输出目录必须不存在（排他创建），拒绝覆盖。"""
    out = Path(path)
    if out.exists():
        raise IdentityError(f"output dir already exists: {out}（拒绝覆盖）")
    return out
