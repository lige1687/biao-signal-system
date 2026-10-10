"""Finalize only the current owner's evidence review and navigation additions."""
import datetime
import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RAW = Path(__file__).parent
CONTROL = RAW.parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def main():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
    b4 = json.loads((RAW / "b4-510300-local-coverage-delta.json").read_text())
    for item in b4["inputs"]:
        data = (ROOT / item["path"]).read_bytes()
        assert len(data) == item["bytes"] and sha(data) == item["sha256"]
    old = json.loads((ROOT / b4["inputs"][2]["path"]).read_text())
    old_events = [x for x in old["events"] if x["symbol"] == "510300" and
                  x["type"] == "cash_dividend" and "2019-09-02" <= x["ex_date"] <= "2026-06-30"]
    accepted = json.loads((ROOT / b4["inputs"][0]["path"]).read_text())
    rows = [x for x in accepted["rows"] if x["symbol"] == "510300" and
            x["period_end"] >= "2019-09-02" and x["period_start"] <= "2026-06-30"]
    assert len(rows) == 8 and len(old_events) == 7
    accepted_events = {}
    candidates = {x["event_id"]: x for x in json.loads((ROOT / b4["inputs"][3]["path"]).read_text())}
    for row in rows:
        assert row["split_or_share_conversion"]["event_count"] == 0
        for e in row["cash"].get("events", []):
            if "2019-09-02" <= e["ex_date"] <= "2026-06-30":
                accepted_events[e["ex_date"]] = (e, e.get("cash_per_unit", row["cash"].get("cash_per_unit_CNY")))
        for event_id in row["cash"].get("event_ids", []):
            e = candidates[event_id]
            assert e["symbol"] == "510300" and row["period_start"] <= e["exchange_ex_date"] <= row["period_end"]
            accepted_events[e["exchange_ex_date"]] = ({"record_date": e["record_date"],
                                                       "scheduled_pay_date": e["payment_date"]},
                                                      e["cash_per_unit_cny"])
    assert len(accepted_events) == 7
    for e in old_events:
        a, amount = accepted_events[e["ex_date"]]
        assert e["record_date"] == a["record_date"]
        assert e["pay_date"] == a.get("scheduled_pay_date", a.get("pay_date"))
        # The frozen table stores binary floats; permit only one floating-point
        # representation step, not a financial-amount discrepancy.
        delta = abs(Decimal.from_float(e["cash_per_unit"]) - Decimal(str(amount)))
        assert delta <= Decimal.from_float(math.ulp(e["cash_per_unit"]))
    assert b4["event_amount_date_match_count"] == 7
    save(RAW / "b4-controller-delta-readback.json", {
        "at": now, "accepted_addendum_sha256": sha((RAW / "b4-510300-local-coverage-delta.json").read_bytes()),
        "input_hashes_actual": True, "periods_independently_selected": len(rows),
        "old_events_independently_selected": len(old_events), "dates_and_amounts_actual_match": True,
        "amount_comparison": "Accepted decimal source amount versus old binary float, absolute difference no greater than one math.ulp; 2024 old 0.06899999999999999 represents source 0.0690, not a different cash amount.",
        "pre_window_event_excluded": "2019-01-16", "other_five_non_target_products_not_qualified": True,
        "R2_authorized_to_run": False, "new_source_requests": 0, "scientific_runs": 0})

    recovery = json.loads((RAW / "idle-input-recovery-readback.json").read_text())
    for key in ["backup_manifest", "restore_manifest"]:
        m = recovery[key]
        data = Path(m["path"]).read_bytes()
        assert sha(data) == m["sha256"] and len(data) == m["bytes"]
    samples = []
    for item in recovery["files"]:
        p = ROOT / item["source"]
        st = p.stat()
        expected = item["source_stat_before"]
        actual = {"ctime_ns": st.st_ctime_ns, "device": st.st_dev, "inode": st.st_ino,
                  "mtime_ns": st.st_mtime_ns, "size": st.st_size}
        assert actual == expected == item["source_stat_after_restore"]
        if p.name in {"588000.SS-A_SMA-base-daily.csv", "510300.SS-A_ALL-base-daily.csv"}:
            for path in [p, Path(item["backup"]), Path(item["restored"])]:
                data = path.read_bytes()
                assert len(data) == item["bytes"] and sha(data) == item["sha256"]
            samples.append(item["source"])
    assert len(samples) == 2 and recovery["file_count"] == 12
    save(RAW / "idle-input-recovery-controller-readback.json", {
        "at": now, "worker_receipt_sha256": sha((RAW / "idle-input-recovery-readback.json").read_bytes()),
        "actual_manifest_hashes_match": True, "all_original_source_stats_unchanged": True,
        "three_path_content_samples": samples, "sample_content_actual_match": True,
        "worker_all_twelve_content_reconciliation_reused": True,
        "same_external_disk_backup_and_restore_only": True, "other_machine_verified": False,
        "failed_disk_recovery_verified": False, "scientific_runs": 0, "source_requests": 0})

    idle = json.loads((RAW / "account-idle-report.json").read_text())
    table = ["| 基金 | 原方法零持仓报价日 | 加均线确认后零持仓报价日 | 最长连续零持仓段（报价日，原/确认） |",
             "|---|---:|---:|---:|"]
    for symbol, name in [("510300.SS", "沪深300"), ("510050.SS", "上证50"),
                         ("510500.SS", "中证500"), ("512100.SS", "中证1000"),
                         ("159915.SZ", "创业板"), ("588000.SS", "科创50")]:
        a = idle["old_six_etf_base_fee_accounts"][symbol + "/A_ALL"]
        b = idle["old_six_etf_base_fee_accounts"][symbol + "/A_SMA"]
        assert a["model_quote_days"] == b["model_quote_days"] == 1147
        table.append(f"| {name}（{symbol[:6]}） | {a['zero_share_model_days']}/1147 | {b['zero_share_model_days']}/1147 | {a['longest_zero_share_run']['model_quote_days']}/{b['longest_zero_share_run']['model_quote_days']} |")
    replacements = {
        "{{IDLE_TABLE}}": "\n".join(table),
        "{{B4_DELTA}}": "510300的准确补注已完成：2019年只取9月2日之后，至2026上半年共8个报告期间；现金分红在窗口内7笔，日期、登记日、计划付款日及每份金额均与原行动表逐笔相符，8期间均无份额折算。旧‘窗口内8笔’多算了2019-01-16这一笔窗口前分红；保留原记录，补注纠正计数，不编造第8笔。该产品的两类事后覆盖缺口可以关闭，原六个非目标产品目前仍有另外五个未证明完整行动史。历史到达、实际到账、调整价格资格、其他产品和两次正式计算放行都不因此通过。见[执行补注](raw/original-eight-continuation-2026-10-10/eight-goal-resume-20261011/b4-510300-local-coverage-delta.json)及[根直接对照](raw/original-eight-continuation-2026-10-10/eight-goal-resume-20261011/b4-controller-delta-readback.json)。",
        "{{RECOVERY_RESULT}}": "本轮新使用12份原日账，共7,803,991字节，已在固定外盘新目录建立12份副本；另一个进程只从副本恢复12份，全部内容指纹与原件相符，原件大小、修改时刻、文件身份未变。新增两套CSV共15,607,982字节，备份进程13171、恢复进程13202。这验证的是本机从同一外盘的副本恢复，不能算另一台电脑或外盘损坏后的恢复。根核两份关键原件/副本/恢复内容及全部原件身份，与执行者12/12完整核对相符。\n\n准确位置：`/Volumes/win+mac通用/LeiSignal-新实验结果/eight-goal-idle-input-recovery-20261011/eight-goal-idle-input-recovery-20261011-20261011T020139-697075e68738/recovery-proof`；设备UUID `DEBA1C85-6059-3865-B50A-A8EE1F80E4D9`。见[12份副本及恢复回执](raw/original-eight-continuation-2026-10-10/eight-goal-resume-20261011/idle-input-recovery-readback.json)和[根实际核对](raw/original-eight-continuation-2026-10-10/eight-goal-resume-20261011/idle-input-recovery-controller-readback.json)。",
        "{{API_RESULT}}": "2026-10-11 02:05+08已通过实际API逐步读回：`K-data-boundary`原三标准3/3，版本22、状态`review`（提交待验收），未代替用户验收；`K-risk-attribution`原标准2/3，版本23、状态`in_progress`，只新增完成报告性m3，相近风险对照m2仍为false。原owner、目的、标准ID与文字、授权及旧历史保持。见[四次实际读回](raw/original-eight-continuation-2026-10-10/eight-goal-resume-20261011/goal-progress-readback.json)及[最终状态](raw/original-eight-continuation-2026-10-10/eight-goal-resume-20261011/goal-progress-final-state.json)。原其他条目只追加本轮证据，不改变其更广状态或完成标准。"}
    report = ROOT / "docs/experiments/original-eight-open-work-review-2026-10-11.md"
    body = report.read_text()
    for key, value in replacements.items():
        assert body.count(key) == 1
        body = body.replace(key, value)
    body = body.replace("原25來源", "原25来源").replace("结果见后续补注", "准确结果见下方已完成补注")
    assert "{{" not in body
    report.write_text(body)
    name = report.relative_to(ROOT).as_posix()
    entry = {"category": "方法论与验证", "verdict": "mixed",
             "oneLiner": "资料限制审计已提交验收，原账户空仓时间与12份资料恢复已补齐；旧因子缺源及相近风险下的新增收益仍未证明。",
             "report_sha256": sha(report.read_bytes()), "raw_directory": RAW.relative_to(ROOT).as_posix(),
             "archive_status": "completed_bounded_evidence_review",
             "K_data_audit_criteria_done": 3, "K_data_submitted_for_review": True,
             "K_risk_criteria_done": 2, "comparable_risk_increment_proven": False,
             "saved_account_descriptors": 14, "new_input_recovery_files": 12,
             "new_source_requests": 0, "scientific_runs": 0,
             "other_machine_recovery_verified": False, "production_authorized": False}
    insert = "    " + json.dumps(name) + ": " + json.dumps(entry, ensure_ascii=False, indent=2) + ",\n"
    save(CONTROL / "eight-goal-review-registration-entry.json", {"report": name, "entry": entry, "insert": insert})
    registry_path = ROOT / "docs/experiments/registry.json"
    registry = json.loads(registry_path.read_text())
    assert entry["category"] in registry["categories"]
    previous = dict(registry["entries"])
    assert name not in previous
    registry["entries"] = {name: entry, **previous}
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n")
    assert all(registry["entries"][k] == v for k, v in previous.items())
    save(RAW / "report-registration-protected-readback.json", {
        "at": now, "report": name, "report_sha256": entry["report_sha256"],
        "other_registry_entries_semantically_unchanged": True, "new_entries": 1})
    inserts_path = CONTROL / "shared-document-insertions.json"
    inserts = json.loads(inserts_path.read_text())
    line = "- 2026-10-11：[原八目标剩余工作复核与资料边界审计](original-eight-open-work-review-2026-10-11.md)：数据审计3/3提交待验收，资金报告2/3；12份日账准确空仓及同盘恢复已补，510300窗口内7笔纠正旧计数，策略增量仍未证明。\n"
    inserts["eight_goal_review_index_line"] = line
    prefix = inserts["catalog_prefix"]
    anchor = "以上是本批有界答案"
    pos = prefix.index(anchor)
    prefix = prefix[:pos] + "- [原八目标当前复核](original-eight-open-work-review-2026-10-11.md)：六主题13来源根审与Astra独核完成，K-data原3/3已提交待验收；K-risk原2/3，技术增量仍未证。旧12账户准确空仓日已补，新增12原日账同盘副本/恢复12/12；510300原窗口7/7分红及8期间零折算可复用，旧窗口前一笔多计纠正。\n\n" + prefix[pos:]
    prefix = prefix.replace("原owner/status/标准不改", "原owner/标准保留；K-data与K-risk仅按原标准更新实际进度")
    inserts["catalog_prefix"] = prefix
    inserts["registry_change"] = "Only this task ten dated report entries; all unrelated entries preserved"
    save(inserts_path, inserts)
    index_path = ROOT / "docs/experiments/INDEX.md"
    index = index_path.read_text()
    anchor = "## 1. 任务编号总账（任务书 → 执行归档）"
    pos = index.index("\n", index.index(anchor)) + 1
    assert line not in index
    index_path.write_text(index[:pos] + "\n" + line + index[pos:])
    catalog_path = ROOT / "docs/experiments/research-evidence-catalog-2026-10-07.md"
    catalog = catalog_path.read_text()
    header = "## 2026-10-10 当前接续：D条件描述已结案，历史成员单事件复用已有原件\n"
    assert catalog.startswith(header)
    marker = "\n---\n\n"
    catalog_path.write_text(prefix + catalog[catalog.index(marker) + len(marker):])
    todo = ROOT / "docs/okr/RESEARCH_TODO.md"
    old_todo = todo.read_bytes()
    assert len(old_todo) == 9705 and sha(old_todo) == "35b020040b005746a78708a1414caeed4566c18550705287a4224eb3aa6f4fcd"
    top = """## 2026-10-11 当前八目标实际接续

用户已授权继续原八目标、磁盘管理和按效率并行。本聊天沿稳定任务`original-eight-continuation-20261010`负责本轮，当前状态以远端同名任务及系统原条目为准。旧快照全文保留在下方；不能按历史‘尚未接手’或‘25来源未恢复’重做。

最新[八目标复核与准确未完成项](../experiments/original-eight-open-work-review-2026-10-11.md)已完成本轮有界审计与必要补充：第4项目的资料限制审计3/3已实际提交待验收，第5项报告标准2/3，同风险技术贡献标准未通过。原owner、授权、完成标准及失败历史保留。第3项510300研究窗口7笔分红及8期间零折算可复用，旧窗口前一笔多计纠正；其他产品、旧取证预算合规及R2放行仍有准确缺件。

第8项原25输入恢复复用，本轮新使用12份日账另补副本及只读副本恢复12/12；大副本和恢复在固定外盘，原件不挪不删，相关文件指纹和恢复进程见报告。该盘现在可用并已实际核对；另一台电脑不是本机继续工作的前提，同盘恢复也不能冒称异机或坏盘恢复。小报告/当前环境/活动数据库继续留本机。

目标1/2/6/7的本批必要范围已有结案或证据，没有被具体新问题触发的全库重跑。月度4/4、旧固定2/2、A03 4/4及其他原次数保持，负结果不调参再跑。新两ETF完整资金问题已另文有条件结案；该问题未显示新增收益，不能代替全部技术策略有效性。

三路Sol/Astra分工各自有界文件范围，共享报告、目录和系统仅根写；没有新用户对话、定时器或无限后台任务。后续真实来源/新独立判断/设备访问按原条件接续，不把计划写成运行中。

---

"""
    todo.write_bytes(top.encode() + old_todo)
    save(RAW / "todo-historical-body-preservation.json", {
        "at": now, "historical_bytes": len(old_todo), "historical_sha256": sha(old_todo),
        "historical_body_bytes_unchanged": todo.read_bytes().endswith(old_todo),
        "new_top_section_only": True})
    print(json.dumps({"report_sha256": entry["report_sha256"], "B4_events": 7,
                      "new_recovery_files": 12, "registration_and_navigation_done": True}))


if __name__ == "__main__":
    main()
