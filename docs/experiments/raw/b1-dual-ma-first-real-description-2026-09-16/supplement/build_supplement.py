"""R2 包外补件：全文件清单、CSV旁置metadata、规范/卡/任务书原字节、缺口登记。

run-02、两版旧协议、现存 freeze 与旧日志全部只读；本脚本只在 supplement/ 内写。
从现存内容补存前逐项匹配原协议声明哈希，不匹配列缺口，禁止补造。
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAW = Path(__file__).resolve().parents[1]
ROOT = RAW.parents[3]
SUPP = RAW / "supplement"
RUN = RAW / "run-02"
PROTO = RAW / "protocol-v1.0.1.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    now = datetime.now(timezone(timedelta(hours=8)))
    protocol = json.loads(PROTO.read_text())
    old_manifest_sha = sha(RUN / "manifest.json")
    gaps = []

    # 1) 全文件补充清单（含嵌套 input-package/manifest.json；旧manifest的37项
    #    清单因按文件名排除漏掉了它——按“只排除顶层manifest”正确口径实际38项）
    # 正确口径：只排除顶层 manifest（嵌套 input-package/manifest.json 必须入列）
    actual = sorted(str(f.relative_to(RUN)) for f in RUN.rglob("*")
                    if f.is_file() and f != RUN / "manifest.json")
    listing = {
        "note": "run-02全文件补充清单（补件，不改旧包）；绑定旧顶层manifest SHA。",
        "bound_run_manifest_sha256": old_manifest_sha,
        "old_manifest_listed_count": 37,
        "actual_file_count": len(actual),
        "omitted_by_old_listing": ["input-package/manifest.json"],
        "generated_at": now.isoformat(),
        "files": {rel: sha(RUN / rel) for rel in actual},
    }
    (SUPP / "full-file-listing.json").write_text(
        json.dumps(listing, ensure_ascii=False, indent=1) + "\n")

    # 2) CSV 旁置 metadata（成熟时间以固定映射规则注明“补充恢复”，
    #    不是原运行已经输出的列）
    for name, extra in (
        ("states.csv", {"columns": {
            "date": "上海本地交易日", "close": "CNY，vendor_qfq供应商调整价",
            "state": "true/false/空（缺失；字符串false不得读成真）",
            "missing_reason": "price_missing/warmup_not_ready/空"}}),
        ("observations.csv", {"columns": {
            "session": "状态观察日（评价窗内）",
            "state": "true/false/空", "e_date": "t之后第1个交易日",
            "x_date": "t之后第22个交易日",
            "main": "P_vendor(x)/P_vendor(e)-1（无量纲）",
            "aux": "min(0,min(P_vendor(s)/P_vendor(e)-1))，相对区间起点最差"
                   "收盘变化，非盘中回撤",
            "mature": "x_date 15:00(Asia/Shanghai) <= label_maturity_cutoff",
            "maturity_time_recovery": "成熟时刻=x_date + 15:00 Asia/Shanghai"
                                      "（固定CN时刻映射；本列为补充恢复规则，"
                                      "不是原运行已经输出的列）"},
         }),
    ):
        meta = {
            "binds": {"file": f"run-02/{name}", "sha256": sha(RUN / name)},
            "object_ref": protocol["object_ref"],
            "candidate_card": protocol["candidate_card"],
            "result_identity": "post_hoc_historical_description",
            "data_mode": "real",
            "historical_reconstruction_only": True,
            "historical_available_at": None,
            "knowledge_time_note": "输入快照2026-09-08取回；成熟截止"
                                   "2026-02-03T15:00+08是标签窗口截断，"
                                   "不是2月已拥有快照的证明",
            "supplement_generated_at": now.isoformat(),
            **extra,
        }
        (SUPP / f"{name}.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=1) + "\n")

    # 3) 规范/卡/任务书原字节（先匹配原协议声明哈希，不匹配列缺口）
    copied = {}
    for s in protocol["standards"]:
        src = ROOT / s["path"]
        if not src.is_file() or sha(src) != s["sha256"]:
            gaps.append(f"规范与协议声明不符或缺失：{s['path']}")
            continue
        dest = SUPP / "standards" / Path(s["path"]).name
        dest.write_bytes(src.read_bytes())
        copied[s["path"]] = s["sha256"]
    for key, ref in (("candidate_card", protocol["candidate_card"]),
                     ("task_book", protocol["task_book"])):
        src = ROOT / ref["path"]
        if not src.is_file() or sha(src) != ref["sha256"]:
            gaps.append(f"{key} 与协议声明不符或缺失：{ref['path']}")
            continue
        dest = SUPP / "standards" / Path(ref["path"]).name
        dest.write_bytes(src.read_bytes())
        copied[ref["path"]] = ref["sha256"]

    # 4) 冻结历史核查：v1.0.0 与 v1.0.1 的 code_identity 差异键逐项核对现存原件
    v0 = json.loads((RAW / "protocol-v1.0.0.json").read_text())["code_identity"]
    v1 = protocol["code_identity"]
    freeze_audit = []
    for rel in v0:
        if v0[rel] == v1.get(rel):
            snap = RAW / "freeze" / "code-snapshot" / rel
            ok = snap.is_file() and sha(snap) == v0[rel]
            freeze_audit.append({"key": rel, "status": "两版相同，现存原件"
                                 + ("一致" if ok else "【异常：不符】")})
        else:
            found = None
            for cand in (RAW / "freeze" / "code-snapshot" / rel,
                         RUN / "source-snapshot" / rel):
                if cand.is_file() and sha(cand) == v0[rel]:
                    found = str(cand)
            if found:
                freeze_audit.append({"key": rel, "status": f"v1.0.0原件幸存于 {found}"})
            else:
                gaps.append(
                    f"{rel}: v1.0.0 声明哈希 {v0[rel]} 的原字节不可恢复"
                    "（freeze/ 共用目录被 v1.0.1 覆盖；不从哈希编造旧源码）"
                )
                freeze_audit.append({"key": rel, "status": "v1.0.0原字节不可恢复"
                                     f"（声明 {v0[rel][:16]}…）"})

    (SUPP / "gaps.md").write_text(
        "# 补件缺口与冻结历史登记（" + now.isoformat() + "）\n\n"
        "## 冻结历史\n\n"
        + "\n".join(f"- {a['key']}: {a['status']}" for a in freeze_audit)
        + "\n\n## 偏差说明\n\n"
        "- freeze_build 早期将两个版本写入同一 freeze/code-snapshot 并覆盖 "
        "environment.json：v1.0.0 的 b1_contract.py 原字节不可恢复。该版本在输入"
        "核验阶段失败、未计算真实结果，不影响现存 v1.0.1 结果，但属冻结纪律偏差，"
        "如实登记不抹去。freeze_build 已改为版本化排他目录（freeze-v{version}/）。\n"
        "- run-02 顶层 manifest 的 file_hashes（37项）按文件名排除了嵌套的 "
        "input-package/manifest.json：'全文件双向一致'声明不成立，已由 "
        "full-file-listing.json（38项）补齐；旧包未改。\n"
        "- 恢复核验实际 2 次（首轮因核验脚本自身 off-by-one 失败、纠错后再一次），"
        "协议上限 1 次：记为 2 次及单项超预算，不写'1次目的'。首次真实 CLI 计入 "
        "2/2 尝试预算属保守可接受；实际成功计算仅一次，两者分列。\n"
        "## 当前缺口\n\n"
        + ("\n".join(f"- {g}" for g in gaps) if gaps else "- 无") + "\n",
        encoding="utf-8")

    (SUPP / "supplement-manifest.json").write_text(json.dumps({
        "generated_at": now.isoformat(),
        "bound_run_manifest_sha256": old_manifest_sha,
        "copied_standards": copied,
        "gaps": gaps,
        "files": {str(f.relative_to(SUPP)): sha(f)
                  for f in sorted(SUPP.rglob("*")) if f.is_file()
                  and f.name != "supplement-manifest.json"},
    }, ensure_ascii=False, indent=1) + "\n")
    print(f"supplement built: {SUPP}")
    print(f"files={len(actual)} copied_standards={len(copied)} gaps={len(gaps)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
