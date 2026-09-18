#!/usr/bin/env python3
"""重命名窗口中断恢复探针（S2 指定场景，确定性模拟）。

覆盖 apply.sh/revert.sh 2026-09-18 窗口闭合后的三个中断态：

  W-skip   apply 记账已打印、原子重命名未执行（含已 staging 的残留 tmp）：
           recovery 跳过该行（目标本就在基线态），其余已应用文件全部还原；
  W-refuse 同状态 + 已应用文件其后被编辑：recovery 整次拒绝、目标零写入；
  R-skip   revert 记账已打印、基线重命名未执行：该行跳过（目标仍在
           post-apply 态），已回退文件恢复到 post-apply 态。

模拟按被测包 apply.sh/revert.sh 的真实写阶段步骤逐命令复刻（backup →
记 recovery_plan → stage → 校验 → mv），恢复则运行真实 recovery.py 与
write_fail/revert_fail 生成的同格式 restore-partial.sh。逐文件恢复，
不代表也不声称全包原子。结果落 recovery-window-results.json。
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
PKG = REPO / "docs/experiments/raw/agent-glm-landing-validation-2026-09-18/adoption-package"
RESULTS_PATH = Path(__file__).with_name("recovery-window-results.json")


def sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def rows() -> list[dict[str, str]]:
    with (PKG / "manifest.tsv").open(newline="") as h:
        return list(csv.DictReader(h, delimiter="\t"))


def dependencies() -> list[dict[str, str]]:
    with (PKG / "dependencies.tsv").open(newline="") as h:
        return list(csv.DictReader(h, delimiter="\t"))


def prepare(root: Path) -> tuple[Path, Path]:
    """独立 target（before 态 + 依赖）与 sim keepdir（含包的 recovery.py）。"""
    target = root / "target"
    (target / "docs/experiments").mkdir(parents=True)
    keepdir = root / "keep"
    keepdir.mkdir()
    shutil.copy2(PKG / "recovery.py", keepdir / "recovery.py")
    manifest = rows()
    for row in manifest:
        path = target / row["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if row["op"] == "replace":
            shutil.copy2(PKG / "before" / row["path"], path)
    for dep in dependencies():
        path = target / dep["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / dep["path"], path)
        assert sha(path) == dep["required_sha256"]
    return target, keepdir


def snapshot(target: Path, manifest: list[dict[str, str]]) -> dict[str, str | None]:
    # absent 文件归一为 "ABSENT"，与 manifest 记法一致
    return {r["path"]: sha(target / r["path"]) or "ABSENT" for r in manifest}


def apply_step_sim(target: Path, keepdir: Path, plan_path: Path, applied_log: Path,
                   row: dict[str, str], *, do_rename: bool, leave_tmp: bool) -> None:
    """按 apply.sh 新顺序复刻单个文件的写阶段（窗口点可控）。"""
    f, op, before, after = row["path"], row["op"], row["before_sha256"], row["after_sha256"]
    dest = target / f
    dest.parent.mkdir(parents=True, exist_ok=True)
    if op == "replace":
        bdir = keepdir / "backup" / Path(f).parent
        bdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, keepdir / "backup" / f)
    # 记账先于重命名（窗口闭合顺序）
    with plan_path.open("a") as h:
        if op == "replace":
            h.write(f"{f}\tcopy\t{after}\t{before}\tbackup/{f}\n")
        else:
            h.write(f"{f}\tremove\t{after}\tABSENT\t-\n")
    tmp = dest.with_name(dest.name + ".tmp.adoption")
    shutil.copy2(PKG / "after" / f, tmp)
    assert sha(tmp) == after
    if do_rename:
        tmp.replace(dest)
    elif not leave_tmp:
        tmp.unlink()
    with applied_log.open("a") as h:
        h.write(f"{op}\t{f}\n")


def revert_step_sim(target: Path, keepdir: Path, plan_path: Path, reverted_log: Path,
                    row: dict[str, str], *, do_rename: bool) -> None:
    """按 revert.sh 新顺序复刻单个文件的写阶段。"""
    f, before, after = row["path"], row["before_sha256"], row["after_sha256"]
    dest = target / f
    pdir = keepdir / "postapply" / Path(f).parent
    pdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dest, keepdir / "postapply" / f)
    with plan_path.open("a") as h:
        if row["op"] == "replace":
            h.write(f"{f}\tcopy\t{before}\t{after}\tpostapply/{f}\n")
        else:
            h.write(f"{f}\tcopy\tABSENT\t{after}\tpostapply/{f}\n")
    if row["op"] == "replace":
        tmp = dest.with_name(dest.name + ".tmp.adoption-revert")
        shutil.copy2(PKG / "before" / f, tmp)
        assert sha(tmp) == before
        if do_rename:
            tmp.replace(dest)
    else:
        if do_rename:
            dest.unlink()
    with reverted_log.open("a") as h:
        h.write(f"{row['op']}\t{f}\n")


def write_restore_script(keepdir: Path, target: Path, plan_path: Path) -> Path:
    script = keepdir / "restore-partial.sh"
    script.write_text(
        "#!/bin/sh\nset -eu\n"
        f"exec python3 \"{keepdir / 'recovery.py'}\" \"{target}\" \"{plan_path}\"\n")
    script.chmod(0o755)
    return script


def run_recovery(script: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sh", str(script)], cwd="/", capture_output=True, text=True)


def main() -> int:
    checks: list[dict] = []
    manifest = rows()

    def chk(case: str, ok: bool, detail: str) -> None:
        checks.append({"case": case, "ok": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + case + " :: " + detail)

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # ---------- W-skip: apply 记账后、重命名前中断，无后续编辑 ----------
        target, keepdir = prepare(base / "w-skip")
        plan = keepdir / "recovery-plan.tsv"
        plan.write_text("path\taction\texpected_current\trestore_sha256\tpayload\n")
        alog = keepdir / "applied.list"
        alog.write_text("")
        for row in manifest[:3]:
            apply_step_sim(target, keepdir, plan, alog, row, do_rename=True, leave_tmp=False)
        # 第4行：记账完成、重命名未执行、staging tmp 残留（真实窗口形态）
        apply_step_sim(target, keepdir, plan, alog, manifest[3],
                       do_rename=False, leave_tmp=True)
        before_state = snapshot(target, manifest)
        script = write_restore_script(keepdir, target, plan)
        proc = run_recovery(script)
        after_state = snapshot(target, manifest)
        ok = proc.returncode == 0
        for row in manifest[:4]:
            want = row["before_sha256"]
            if after_state[row["path"]] != want:
                print(f"  mismatch: {row['path']}: got={str(after_state[row['path']])[:16]} "
                      f"want={want[:12]}")
            ok = ok and after_state[row["path"]] == want
        for row in manifest[4:]:
            if after_state[row["path"]] != before_state[row["path"]]:
                print(f"  touched-after: {row['path']}")
            ok = ok and after_state[row["path"]] == before_state[row["path"]]
        chk("W-skip.apply.recorded_not_renamed",
            ok and "skipped" in (proc.stdout + proc.stderr),
            f"rc={proc.returncode} out={proc.stdout.strip()[:110]}")

        # ---------- W-refuse: 同窗口态 + 已应用文件其后被编辑 ----------
        target2, keepdir2 = prepare(base / "w-refuse")
        plan2 = keepdir2 / "recovery-plan.tsv"
        plan2.write_text("path\taction\texpected_current\trestore_sha256\tpayload\n")
        alog2 = keepdir2 / "applied.list"
        alog2.write_text("")
        for row in manifest[:3]:
            apply_step_sim(target2, keepdir2, plan2, alog2, row, do_rename=True, leave_tmp=False)
        apply_step_sim(target2, keepdir2, plan2, alog2, manifest[3],
                       do_rename=False, leave_tmp=False)
        edited = target2 / manifest[1]["path"]
        edited.write_text(edited.read_text() + "\n# later edit after interruption\n")
        state_before_recovery = snapshot(target2, manifest)
        script2 = write_restore_script(keepdir2, target2, plan2)
        proc2 = run_recovery(script2)
        state_after_recovery = snapshot(target2, manifest)
        chk("W-refuse.later_edit_refused",
            proc2.returncode != 0 and "changed after interruption" in proc2.stderr,
            f"rc={proc2.returncode} err={proc2.stderr.strip()[:110]}")
        chk("W-refuse.zero_target_writes",
            state_before_recovery == state_after_recovery,
            "恢复尝试前后目标逐文件哈希一致（零写入）")

        # ---------- R-skip: revert 记账后、基线重命名前中断 ----------
        target3, keepdir3 = prepare(base / "r-skip")
        (base / "w-tmp").mkdir()
        applied = subprocess.run(
            ["sh", str(PKG / "apply.sh"), "--target", str(target3)],
            cwd="/", capture_output=True, text=True,
            env={"PATH": "/bin:/usr/bin", "TMPDIR": str(base / "w-tmp")})
        if not (applied.returncode == 0 and "APPLY DONE: 25/25" in applied.stdout):
            chk("R-skip.setup_apply", False, applied.stdout[-200:] + applied.stderr[-200:])
        else:
            plan3 = keepdir3 / "recovery-plan.tsv"
            plan3.write_text("path\taction\texpected_current\trestore_sha256\tpayload\n")
            rlog3 = keepdir3 / "reverted.list"
            rlog3.write_text("")
            for row in manifest[:2]:
                revert_step_sim(target3, keepdir3, plan3, rlog3, row, do_rename=True)
            # 第3行：记账完成、基线重命名未执行（目标仍 post-apply 态）
            revert_step_sim(target3, keepdir3, plan3, rlog3, manifest[2], do_rename=False)
            script3 = write_restore_script(keepdir3, target3, plan3)
            proc3 = run_recovery(script3)
            state3 = snapshot(target3, manifest)
            ok3 = proc3.returncode == 0
            for row in manifest:
                ok3 = ok3 and state3[row["path"]] == row["after_sha256"]
            chk("R-skip.revert.recorded_not_renamed",
                ok3 and "skipped" in (proc3.stdout + proc3.stderr),
                f"rc={proc3.returncode} out={proc3.stdout.strip()[:110]}")

    RESULTS_PATH.write_text(json.dumps(checks, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    failed = [c for c in checks if not c["ok"]]
    print(f"window probes: {len(checks)} checks, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
