"""归档补件：保存 v1.2.0 完整必需代码集合的原字节终版包（15键）。

主控第二轮收口（2026-09-15）指定：在后续任何源码修改之前，另存 v1.2.0
完整必需代码集合的原字节终版包，含运行环境/依赖版本说明，并按协议
``code_identity`` 逐项核对哈希；开工快照（source-snapshot/）保留不覆盖。
本脚本只读当前代码、只写新目录（排他创建）；不改旧 manifest、不倒填旧运行。
"""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "v1.2.0-code-archive"

PROTOCOLS = sorted(HERE.glob("protocol-*.json"))
REPO_FILES = [
    "src/lei_signal/research/factor_lab/__init__.py",
    "src/lei_signal/research/factor_lab/contracts.py",
    "src/lei_signal/research/factor_lab/adapters.py",
    "src/lei_signal/research/factor_lab/diagnostics.py",
    "src/lei_signal/research/factor_lab/validation.py",
    "src/lei_signal/research/factor_lab/attribution.py",
    "src/lei_signal/research/factor_lab/runner.py",
    "scripts/run_factor_lab.py",
    "src/lei_signal/research/definitions.py",
    "src/lei_signal/research/momentum_prototype.py",
    "src/lei_signal/research/factor_diagnostics.py",
    "src/lei_signal/rules/dual_ma.py",
    "src/lei_signal/rules/lei_color.py",
    "src/lei_signal/features/indicators.py",
    "src/lei_signal/domain/rules_config.py",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout


def main() -> int:
    if ARCHIVE.exists():
        print(f"refusing to overwrite {ARCHIVE}")
        return 3
    ARCHIVE.mkdir()
    files = {}
    for rel in REPO_FILES:
        source = ROOT / rel
        if not source.is_file():
            print(f"missing source file: {rel}")
            return 3
        target = ARCHIVE / rel.replace("/", "__")
        shutil.copy2(source, target)
        files[rel] = {"sha256": sha(source.read_bytes()),
                      "archive_file": target.name,
                      "bytes": source.stat().st_size}

    # 逐项对照三份 v1.2.0 协议的 code_identity（与当前代码必须一致）
    protocol_check: dict = {}
    for protocol_path in PROTOCOLS:
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        declared = protocol["code_identity"]
        mismatches = [rel for rel in REPO_FILES
                      if declared.get(rel) != files[rel]["sha256"]]
        key_set_diff = sorted(set(declared) ^ set(REPO_FILES))
        protocol_check[protocol_path.name] = {
            "protocol_version": protocol["version"],
            "code_identity_matches_current_bytes": not mismatches and not key_set_diff,
            "mismatches": mismatches,
            "key_set_diff": key_set_diff,
        }

    env = {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
    }
    for module in ("pandas", "numpy", "pytest", "ruff"):
        try:
            mod = __import__(module)
            env[module] = getattr(mod, "__version__", "unknown")
        except ImportError:
            env[module] = "not importable"
    ruff = subprocess.run(["ruff", "--version"], capture_output=True, text=True)
    env["ruff_cli"] = ruff.stdout.strip() or ruff.stderr.strip()

    manifest = {
        "purpose": "v1.2.0 终版必需代码集合原字节归档（归档补件，非新一轮功能建设）",
        "created": "2026-09-15",
        "controller_review": (
            "docs/experiments/factor-lab-repair-controller-review-2026-09-15.md"),
        "code_files": files,
        "protocol_verification": protocol_check,
        "runtime_environment": env,
        "git_head": git("rev-parse", "HEAD").strip(),
        "note": (
            "开工快照 source-snapshot/ 是开工时状态（attribution/diagnostics/"
            "runner/validation 四文件与 v1.2.0 不符），保留不覆盖；本包才是与 "
            "v1.2.0 协议 code_identity 一致的终版源码。恢复方法：将 archive_file "
            "按文件名中的 __ 还原为路径写回仓库，再逐项核对本清单哈希。"
        ),
    }
    (ARCHIVE / "archive-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    all_ok = all(v["code_identity_matches_current_bytes"]
                 for v in protocol_check.values())
    print(f"archived {len(files)} files; protocol verification "
          f"all_match={all_ok}")
    for name, check in protocol_check.items():
        print(f"  {name}: v{check['protocol_version']} "
              f"match={check['code_identity_matches_current_bytes']}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
