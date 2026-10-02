"""T10 移交包校验器（最小版）与四个合成演练。

移交包 = 一个 handoff-manifest.json（不改原冻结合同，只做移交层）：
  experiment_id / review_mode（report_numbers | frozen_code_replay | new_protocol_recompute）
  originals: 原冻结合同/锁文件的相对路径与原指纹（原样保留，不改历史哈希）
  path_map:  原绝对路径前缀 -> 仓库相对路径（只用于移交，不写回原锁）
  files:     每个文件 {path, role, sha256(字节), git_blob, eol, public(bool), license}
  code:      {commit, files:[{path, git_blob}]}；frozen_code_replay 必须逐文件匹配
  environment: {python, packages{name:version}}
  objects / dates / units、expected_outputs（路径+指纹+允许误差）、missing（明确缺项与原因）
校验结果状态：complete | incomplete（缺文件）| modified（内容不同）| eol_only（仅换行符不同，
不算通过，需说明）| wrong_code_version | not_applicable。
运行：python handoff_check.py  （合成包在 /tmp 生成，结果写本目录 drill-output.json）
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git_blob(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def eol(b: bytes) -> str:
    if b"\r\n" in b:
        return "crlf"
    return "lf" if b"\n" in b else "none"


def _alt_eol(b: bytes) -> bytes:
    lf = b.replace(b"\r\n", b"\n")
    return lf.replace(b"\n", b"\r\n") if lf == b else lf


def check(package_dir: Path, manifest: dict, code_root: Path | None = None) -> dict:
    """逐文件核对；code_root 为复查方实际使用的代码目录（frozen_code_replay 时必填）。"""
    findings, status = [], "complete"
    rank = {"complete": 0, "eol_only": 1, "incomplete": 2, "modified": 3, "wrong_code_version": 4}

    def worse(s):
        nonlocal status
        if rank[s] > rank[status]:
            status = s

    for f in manifest["files"]:
        p = package_dir / f["path"]
        if not p.is_file():
            findings.append({"path": f["path"], "result": "missing"})
            worse("incomplete")
            continue
        b = p.read_bytes()
        if sha256(b) == f["sha256"]:
            continue
        if sha256(_alt_eol(b)) == f["sha256"]:
            findings.append({"path": f["path"], "result": "eol_only", "recorded_eol": f.get("eol"),
                             "actual_eol": eol(b)})
            worse("eol_only")
        else:
            findings.append({"path": f["path"], "result": "content_changed"})
            worse("modified")
    if manifest["review_mode"] == "frozen_code_replay":
        if code_root is None:
            findings.append({"code": "no code root supplied"})
            worse("wrong_code_version")
        else:
            for c in manifest["code"]["files"]:
                p = code_root / c["path"]
                if not p.is_file() or git_blob(p.read_bytes()) != c["git_blob"]:
                    findings.append({"code": c["path"], "result": "blob_mismatch_or_missing"})
                    worse("wrong_code_version")
    for m in manifest.get("missing", []):
        findings.append({"declared_missing": m["item"], "reason": m["reason"]})
    allowed = {"complete": "proceed", "eol_only": "proceed_only_after_recording_normalization",
               "incomplete": "stop", "modified": "stop", "wrong_code_version": "stop"}[status]
    return {"status": status, "action": allowed, "findings": findings}


def build_synthetic(root: Path) -> tuple[Path, Path, dict]:
    pkg, code = root / "package", root / "code"
    (pkg / "inputs").mkdir(parents=True)
    (code / "execution").mkdir(parents=True)
    files = {
        "protocol.md": b"# synthetic frozen protocol\nH=20\n",
        "protocol-lock.json": b'{"sha256": "placeholder"}\n',
        "inputs/bars-SYN.csv": b"date,open,high,low,close,volume\n2026-01-05,1,1.1,0.9,1.05,100\n",
        "expected/summary.json": b'{"final_equity": 100426.0}\n',
    }
    for rel, b in files.items():
        (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
        (pkg / rel).write_bytes(b)
    engine = b"def simulate():\n    return 100426.0\n"
    (code / "execution/engine.py").write_bytes(engine)
    manifest = {
        "schema_version": "handoff-manifest/0",
        "experiment_id": "SYNTHETIC-handoff-drill",
        "review_mode": "frozen_code_replay",
        "originals": [{"path": "protocol-lock.json", "sha256": sha256(files["protocol-lock.json"]),
                       "note": "original lock kept byte-identical; absolute paths inside are not rewritten"}],
        "path_map": [{"from_prefix": "/Users/someone/Desktop/lei-signal-lab/", "to_prefix": ""}],
        "files": [{"path": rel, "role": rel.split("/")[0], "sha256": sha256(b), "git_blob": git_blob(b),
                   "eol": eol(b), "public": True, "license": "synthetic"} for rel, b in files.items()],
        "code": {"commit": "SYNTHETIC", "files": [{"path": "execution/engine.py", "git_blob": git_blob(engine)}]},
        "environment": {"python": "3.12", "packages": {"pandas": "2.x (record exact)", "numpy": "2.x (record exact)"}},
        "objects": ["SYN"], "dates": ["2026-01-05", "2026-01-05"], "units": {"price": "CNY nominal"},
        "expected_outputs": [{"path": "expected/summary.json", "field": "final_equity", "tolerance_abs": 0.01}],
        "missing": [{"item": "historical arrival time of quotes", "reason": "never recorded upstream"}],
    }
    return pkg, code, manifest


def main() -> int:
    results, fails = {}, []
    expected = {"D1_complete": "complete", "D2_file_missing": "incomplete", "D3_content_modified": "modified",
                "D4_wrong_code_version": "wrong_code_version", "D5_eol_only_real_world": "eol_only"}
    with tempfile.TemporaryDirectory(prefix="t10-") as tmp:
        tmp = Path(tmp)
        pkg, code, manifest = build_synthetic(tmp / "base")
        (HERE / "synthetic-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
                                                      encoding="utf-8")
        for name in expected:
            work = tmp / name
            shutil.copytree(tmp / "base", work)
            p, c = work / "package", work / "code"
            if name == "D2_file_missing":
                (p / "inputs/bars-SYN.csv").unlink()
            elif name == "D3_content_modified":
                (p / "expected/summary.json").write_bytes(b'{"final_equity": 100427.0}\n')
            elif name == "D4_wrong_code_version":
                (c / "execution/engine.py").write_bytes(b"def simulate():\n    return 100426.0  # edited later\n")
            elif name == "D5_eol_only_real_world":
                b = (p / "inputs/bars-SYN.csv").read_bytes()
                (p / "inputs/bars-SYN.csv").write_bytes(b.replace(b"\n", b"\r\n"))
            out = check(p, manifest, code_root=c)
            out["matches_expected"] = out["status"] == expected[name]
            results[name] = out
            if not out["matches_expected"]:
                fails.append(name)
    results["_note"] = ("合成包在临时目录生成并删除；D5 复现了真实旧锁里看到的“只差换行符”情形。"
                        "合成演练只证明校验器按约定工作。")
    (HERE / "drill-output.json").write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n",
                                            encoding="utf-8")
    for k, v in results.items():
        if isinstance(v, dict):
            print(k, v["status"], v["action"], v["matches_expected"])
    print("FAILURES:", fails or "none")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
