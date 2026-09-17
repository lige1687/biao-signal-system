#!/usr/bin/env python3
"""一次性协议冻结脚本：创建 protocol-v1.0.0.json 版本原件并保存冻结代码原字节。

- 排他创建（'x' 模式），已存在即停；
- 代码闭包在干净子进程内计算（静态 AST + 运行时种子）；
- 真实分支四输入按协议白名单钉哈希；
- 创建后立即用 contract.validate_protocol 自检。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
RAW = HERE.parent
REPO = RAW.parents[3]
sys.path.insert(0, str(REPO / "src"))

from lei_signal.research import breadth_description_contract as contract  # noqa: E402

CLI = RAW / "run_breadth.py"
PROTOCOL_PATH = RAW / "freeze/v1.0.0/protocol-v1.0.0.json"
CODE_COPY_DIR = RAW / "freeze/v1.0.0/code"

SNIPPET = (
    "import json,sys;sys.path.insert(0, sys.argv[1]);"
    "from lei_signal.research import breadth_description_contract as c\n"
    "print(json.dumps(c.compute_import_closure(sys.argv[2])))"
)


def main() -> int:
    out = subprocess.run(
        [sys.executable, "-c", SNIPPET, str(REPO / "src"), str(CLI)],
        capture_output=True, text=True, check=True,
    )
    closure = json.loads(out.stdout)
    inputs = {
        name: {"path": required["path"], "sha256": required["sha256"],
               "role": required["role"]}
        for name, required in contract.REQUIRED_INPUTS.items()
    }
    doc = contract.protocol_document(closure, mode="restricted_historical", inputs=inputs)
    if PROTOCOL_PATH.exists():
        # 断点续跑：原件已排他创建过，则核对内容与本次重算完全一致后才补齐后续步骤。
        existing = json.loads(PROTOCOL_PATH.read_bytes())
        if existing != doc:
            print("existing protocol differs from recomputed doc; stop")
            return 1
    else:
        with open(PROTOCOL_PATH, "x", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
            fh.write("\n")

    CODE_COPY_DIR.mkdir(parents=True, exist_ok=True)
    import shutil

    for rel in closure:
        src = REPO / rel
        dst = CODE_COPY_DIR / Path(rel).name
        if dst.exists():
            print(f"code copy already exists; stop: {dst}")
            return 1
        shutil.copyfile(src, dst)

    errors = contract.validate_protocol(doc, mode="restricted_historical",
                                        protocol_path=PROTOCOL_PATH)
    if errors:
        print(f"self-check failed: {errors}")
        return 1
    print(f"protocol frozen: {PROTOCOL_PATH}")
    print(f"code files: {len(closure)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
