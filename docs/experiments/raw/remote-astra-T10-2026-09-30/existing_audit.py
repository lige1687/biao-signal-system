"""T10 只读审查：GitHub 克隆里已有的旧源码锁能否在另一台电脑复核，定义登记表能否加载。

不修改任何旧文件；绝对路径只在内存中按前缀映射为仓库相对路径。输出 existing-audit.json。
"""
from __future__ import annotations

import glob
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PREFIX = "/Users/yongbiaoli/Desktop/lei-signal-lab/"


def _alt(b: bytes) -> bytes:
    lf = b.replace(b"\r\n", b"\n")
    return lf.replace(b"\n", b"\r\n") if lf == b else lf


def audit_locks() -> dict:
    out = {}
    for lp in sorted(glob.glob(str(REPO / "docs/experiments/raw/**/source-lock.json"), recursive=True)):
        rel_lock = str(Path(lp).relative_to(REPO))
        data = json.loads(Path(lp).read_text(encoding="utf-8"))
        files = data.get("files") if isinstance(data, dict) else None
        if not isinstance(files, dict):
            out[rel_lock] = {"format": "no files map (other lock schema; not audited)"}
            continue
        c = {"entries": len(files), "absolute_paths": 0, "relative_paths": 0, "byte_match": 0,
             "eol_only": 0, "changed": [], "missing": 0, "relative_base": None}
        for p, h in files.items():
            h = h if isinstance(h, str) else (h or {}).get("sha256")
            if p.startswith("/"):
                c["absolute_paths"] += 1
                f = REPO / p[len(PREFIX):] if p.startswith(PREFIX) else None
            else:
                c["relative_paths"] += 1
                cands = [Path(lp).parent / p, REPO / p]
                f = next((x for x in cands if x.is_file()), None)
                if f is not None:
                    c["relative_base"] = "lock_directory" if f == cands[0] else "repo_root"
            if f is None or not f.is_file():
                c["missing"] += 1
                continue
            b = f.read_bytes()
            if hashlib.sha256(b).hexdigest() == h:
                c["byte_match"] += 1
            elif hashlib.sha256(_alt(b)).hexdigest() == h:
                c["eol_only"] += 1
            else:
                c["changed"].append(str(f.relative_to(REPO)))
        out[rel_lock] = c
    return out


def audit_registry() -> dict:
    reg = json.loads((REPO / "docs/research/definitions.v1.json").read_text(encoding="utf-8"))
    refs = [(o["id"] + "@" + o["version"], b) for o in reg["objects"]
            for b in (o.get("lifecycle") or {}).get("basis", [])]
    missing = [r for r in refs if not (REPO / r[1]).is_file()]
    sys.path.insert(0, str(REPO / "src"))
    try:
        from lei_signal.research.definitions import load_registry
        load_registry()
        load = "ok"
    except Exception as exc:  # noqa: BLE001
        load = f"{type(exc).__name__}: {exc}"
    dirs = sorted({Path(b).parts[3] for _, b in missing if len(Path(b).parts) > 3})
    return {"objects": len(reg["objects"]), "lifecycle_basis_refs": len(refs), "missing_refs": len(missing),
            "missing_raw_directories": dirs, "load_registry": load}


def main() -> None:
    result = {"locks": audit_locks(), "definition_registry": audit_registry(),
              "_note": "只读；绝对路径按前缀映射；未改写任何旧锁或登记表。"}
    (HERE / "existing-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                                              encoding="utf-8")
    print(json.dumps(result["definition_registry"], ensure_ascii=False)[:600])
    for k, v in result["locks"].items():
        if "entries" in v:
            print(k.replace("docs/experiments/raw/", ""), {x: (len(y) if isinstance(y, list) else y)
                                                            for x, y in v.items()})


if __name__ == "__main__":
    main()
