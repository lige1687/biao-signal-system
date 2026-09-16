"""一次性生成 fixed-etf-evidence-integration 任务协议 protocol.json（v1.0.0）。

在最终实现锁定后运行：绑定实际代码哈希（含 qualification_bundle 与 prepare
CLI）、派生快照输入与证据包。生成后立即另存 protocol-v1.0.0.json 副本；
此后改码需新版本。本脚本仅用于本轮创建，不进入测试或运行入口。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
THIS = ROOT / "docs/experiments/raw/research-fixed-etf-evidence-integration-2026-09-13"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


spec_files = {
    "principles": ("docs/research/experiment-backtest-principles.md", "v1.1"),
    "definition_standard": ("docs/research/definition-standard.md", "1.1.0"),
    "execution_contract": ("docs/research/ai-execution-contract.md", "1.0.1"),
    "report_template": ("docs/research/experiment-report-template.md", "1.1.0"),
    "registry": ("docs/research/definitions.v1.json", None),
}
specs = {}
for key, (path, version) in spec_files.items():
    fp = ROOT / path
    if key == "registry":
        version = json.loads(fp.read_text()).get("version")
    specs[key] = {"path": path, "version": version, "sha256": sha(fp)}

code_files = {
    "definitions": "src/lei_signal/research/definitions.py",
    "factor_runtime": "src/lei_signal/research/factor_runtime.py",
    "momentum_prototype": "src/lei_signal/research/momentum_prototype.py",
    "data_quality": "src/lei_signal/research/data_quality.py",
    "data_snapshot": "src/lei_signal/research/data_snapshot.py",
    "trading_calendar": "src/lei_signal/research/trading_calendar.py",
    "symbol_identity": "src/lei_signal/research/symbol_identity.py",
    "qualification_bundle": "src/lei_signal/research/qualification_bundle.py",
    "run_momentum_research_prototype": "scripts/run_momentum_research_prototype.py",
    "prepare_momentum_qualified_inputs": "scripts/prepare_momentum_qualified_inputs.py",
}
codes = {k: {"path": v, "sha256": sha(ROOT / v)} for k, v in code_files.items()}

# ---- 派生快照与冻结输入 ----
derived_snapshot_dir = THIS / "run-02/snapshot"
derived_meta = json.loads((derived_snapshot_dir / "snapshot.json").read_text())
old_protocol = json.loads(
    (ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13/protocol-v1.0.5.json")
    .read_text())
old_inputs = old_protocol["inputs"]
inputs = {
    "snapshot_dir": {
        "path": str(derived_snapshot_dir.relative_to(ROOT)),
        "sha256": sha(derived_snapshot_dir / "snapshot.json"),
        "derived_from": old_inputs["snapshot_dir"]["path"],
        "original_snapshot_json_sha256": old_inputs["snapshot_dir"]["sha256"],
    },
    "calendar": {"path": old_inputs["calendar"]["path"],
                 "sha256": old_inputs["calendar"]["sha256"]},
    "publication": {"path": old_inputs["publication"]["path"],
                    "sha256": old_inputs["publication"]["sha256"]},
    "actions": {"path": old_inputs["actions"]["path"],
                "sha256": old_inputs["actions"]["sha256"]},
    "evidence_bundle": {
        "path": "docs/experiments/raw/research-fixed-etf-evidence-integration-2026-09-13/evidence-bundle.json",
        "sha256": sha(THIS / "evidence-bundle.json"),
    },
    "evaluation_start": old_inputs["evaluation_start"],
    "evaluation_end": old_inputs["evaluation_end"],
    "pool_expectation": old_inputs["pool_expectation"],
}

sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research import definitions as d  # noqa: E402

registry = d.load_registry()
cards = {}
for ref in ("mixed.momentum.raw@1.0.0", "mixed.price.economic@1.0.0"):
    card = d.resolve(registry, ref)

    def _closure(r, _seen=None):
        seen = {} if _seen is None else _seen
        if r in seen:
            return seen
        seen[r] = d.resolve(registry, r)
        for dep in seen[r].get("dependencies", []):
            _closure(dep, seen)
        return seen

    cards[ref] = {"card": card, "recursive_dependencies": sorted(_closure(ref).keys())}

try:
    git_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
except Exception as exc:  # noqa: BLE001
    git_head = f"unavailable: {exc}"

protocol = {
    "protocol_id": "fixed-etf-evidence-integration-2026-09-13",
    "protocol_version": "1.0.1",
    "plan_version": "1.0.0",
    "date": "2026-09-13",
    "research_family": "research-data-foundation",
    "parent_protocol": {
        "protocol_id": "momentum-research-prototype-2026-09-13",
        "version": "1.0.5",
        "sha256": sha(ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13/protocol.json"),
    },
    "goal": (
        "把仓库已保存的官方材料接成固定14只ETF的可追溯资格证据，再接到现有"
        "动量研究输入；事实已核、当时可知、用途允许、实现可用、预测有效与"
        "生产授权分列。默认全离线。"
    ),
    "target_id": "protocol:momentum-next-close-21-session@1.0.0",
    "target_note": (
        "沿用原任务唯一未来观察目标；协议测量项，不是登记表对象。"
    ),
    "revisions": [
        {
            "version": "1.0.0",
            "date": "2026-09-13",
            "note": "初版冻结（原件保留于 protocol-v1.0.0.json）；其下 run-03/run-04 "
                    "为该版本下的首次真实输入检查/历史诊断与资格拒绝。",
        },
        {
            "version": "1.0.1",
            "date": "2026-09-13",
            "changes": [
                "Task 5 补全：CLI 的 listing 桥接接线与 out 目录创建修正，"
                "codes 中 run_momentum_research_prototype 哈希随之更新；"
                "其父动量协议同步升 v1.0.7。v1.0.0 下的 run-03/04 封存保留，"
                "按纠错预算以新编号 run-05/run-06 复跑一次。",
            ],
            "impact": "测量参数与输入不变；发现文案变化限于已核上市事实"
                      "（日期自洽），资格授予仍归底层闸门。",
        },
    ],
    "research_evidence": {
        "path": inputs["evidence_bundle"]["path"],
        "sha256": inputs["evidence_bundle"]["sha256"],
    },
    "objects": {
        "primary": "mixed.momentum.raw@1.0.0",
        "dependency": "mixed.price.economic@1.0.0",
        "type": "feature（描述数值，不是可投资的因子收益组合）",
        "cards": cards,
    },
    "specs": specs,
    "codes": codes,
    "inputs": inputs,
    "code_version": {
        "git_head": git_head,
        "python_version": sys.version.split()[0],
        "dependencies": "pandas, numpy, pdfplumber, pytest, ruff（零新增依赖，零网络请求）",
    },
    "formula": {
        "momentum": "M(t)=I(t-21)/I(t-252)-1（按该产品自身有效报价位置；首次需 253 条）",
        "target": "Y(t)=I(x)/I(e)-1，e 为 t 之后第一个交易日，x 为 e 之后第 21 个交易日",
        "diagnostic": "Spearman 等价：两列各自并列平均名次，再算名次的 Pearson 相关",
    },
    "target_parameters": {
        "next_session_offset": 1,
        "exit_session_offset": 22,
        "momentum_long_lag": 252,
        "momentum_skip_lag": 21,
        "note": "与实现常量逐一核对；协议声明与算法不一致时运行入口拒绝",
    },
    "time_semantics": {
        "observation_dates": "评价区间内各完整月份的最后交易日；月份不完整不推断月末",
        "evaluation_window": f"{old_inputs['evaluation_start']} ~ {old_inputs['evaluation_end']}",
        "observation_cutoff_assumption": (
            "15:00 为按收盘设置的保守测试截点，不是已证实的数据到达时间或"
            "实盘决策时刻；真实资格不得凭该字段获准"),
        "available_at": (
            "t 收盘最早只能在其实际可得后用于决策；证据包只记公布日期下界，"
            "不据此填写精确 available_at；未知保持 null"),
        "historical_reconstruction_only": (
            "派生快照的 economic_index 为事后重建列；晚取得/未知行动在"
            "历史模式如实标注，在预测模式拒绝"),
    },
    "modes": {
        "synthetic": {
            "description": "合成夹具验证算法与时间安排正确；不伪装真实资料",
            "exit": {"0": "模式完整完成", "2": "质量限制导致研究拒绝", "3": "失败"},
        },
        "historical-diagnostic": {
            "description": "派生快照上的历史数值诊断；不写真实 targets/rank",
            "exit": {"0": "诊断完整完成", "2": "资料限制拒绝", "3": "失败"},
        },
        "qualified-research": {
            "description": "仅当全部实际资格满足才运行；当前预期受限即拒绝",
            "exit": {"0": "预测诊断放行", "2": "资格/资料限制拒绝", "3": "失败"},
        },
    },
    "tolerance": {"absolute": 1e-12, "relative": 1e-12, "integer": 0},
    "explicitly_not": [
        "不新增交易因子对象/行情/产品；不动生产、账户、OKR",
        "不使用 allow_conditional/accept_structural 放行",
        "不以文件哈希一致、官方域名或自填 trusted=true 当作历史事实真实性证明",
        "不承诺真实预测本轮可跑；合法结果可以是『更多事实已核，预测仍受限』",
        "联网定向补公告只写待授权范围，本轮绝不执行",
    ],
}

out = THIS / "protocol.json"
out.write_text(json.dumps(protocol, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", out.relative_to(ROOT))
print("protocol sha256", sha(out))
