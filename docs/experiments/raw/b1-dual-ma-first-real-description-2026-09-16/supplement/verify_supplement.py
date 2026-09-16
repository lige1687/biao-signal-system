"""补件只读核验（预算1次）：核字节与映射，不运行真实计算、不改任何文件。"""
import hashlib
import json
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parents[1]
SUPP = RAW / "supplement"
RUN = RAW / "run-02"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    errors, oks = [], []
    listing = json.loads((SUPP / "full-file-listing.json").read_text())
    if sha(RUN / "manifest.json") != listing["bound_run_manifest_sha256"]:
        errors.append("run-02 顶层 manifest 漂移")
    for rel, h in listing["files"].items():
        if not (RUN / rel).is_file() or sha(RUN / rel) != h:
            errors.append(f"清单与run-02文件不符: {rel}")
    oks.append(f"全文件清单 {len(listing['files'])} 项与 run-02 一致（含嵌套manifest）")

    for name in ("states.csv", "observations.csv"):
        meta = json.loads((SUPP / f"{name}.meta.json").read_text())
        if meta["binds"]["sha256"] != sha(RUN / name):
            errors.append(f"{name} metadata 绑定哈希不符")
    oks.append("states/observations 旁置metadata绑定一致")

    proto = json.loads((RAW / "protocol-v1.0.1.json").read_text())
    declared = {s["path"]: s["sha256"] for s in proto["standards"]}
    declared[proto["candidate_card"]["path"]] = proto["candidate_card"]["sha256"]
    declared[proto["task_book"]["path"]] = proto["task_book"]["sha256"]
    for f in (SUPP / "standards").iterdir():
        match = [p for p, h in declared.items()
                 if f.name == Path(p).name and sha(f) == h]
        if not match:
            errors.append(f"standards 补件与协议声明不符: {f.name}")
    oks.append(f"standards 补件 {len(list((SUPP / 'standards').iterdir()))} 项与协议声明一致")

    sm = json.loads((SUPP / "supplement-manifest.json").read_text())
    for rel, h in sm["files"].items():
        if not (SUPP / rel).is_file() or sha(SUPP / rel) != h:
            errors.append(f"supplement-manifest 与补件不符: {rel}")
    gaps = (SUPP / "gaps.md").read_text(encoding="utf-8")
    if "不可恢复" not in gaps:
        errors.append("gaps.md 未登记不可恢复件")
    oks.append(f"supplement-manifest 一致；缺口登记 {len(sm['gaps'])} 项")

    for line in oks:
        print(f"OK: {line}")
    for line in errors:
        print(f"FAIL: {line}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
