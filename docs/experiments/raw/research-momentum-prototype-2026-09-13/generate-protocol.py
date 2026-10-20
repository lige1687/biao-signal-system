"""一次性生成冻结协议 protocol.json（momentum-research-prototype-2026-09-13）。

冻结后参数不得更改；纠错需新协议版本及影响记录。本脚本仅用于本轮创建，
不进入任何测试或运行入口。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


# ---- 规范指纹（registry 版本取实际容器版本，不手写） ----
_reg_version = json.loads(
    (ROOT / "docs/research/definitions.v1.json").read_text()
).get("version")
spec_files = {
    "principles": ("docs/research/experiment-backtest-principles.md", "v1.1"),
    "definition_standard": ("docs/research/definition-standard.md", "1.1.0"),
    "execution_contract": ("docs/research/ai-execution-contract.md", "1.0.1"),
    "report_template": ("docs/research/experiment-report-template.md", "1.1.0"),
    "registry": ("docs/research/definitions.v1.json", _reg_version),
}
specs = {}
for key, (path, version) in spec_files.items():
    fp = ROOT / path
    specs[key] = {
        "path": path,
        "version": version,
        "sha256": sha256(fp) if fp.exists() else None,
    }

# ---- 代码指纹 ----
code_files = {
    "definitions": "src/lei_signal/research/definitions.py",
    "factor_runtime": "src/lei_signal/research/factor_runtime.py",
    "momentum_prototype": "src/lei_signal/research/momentum_prototype.py",
    "data_quality": "src/lei_signal/research/data_quality.py",
    "data_snapshot": "src/lei_signal/research/data_snapshot.py",
    "trading_calendar": "src/lei_signal/research/trading_calendar.py",
    "symbol_identity": "src/lei_signal/research/symbol_identity.py",
    "run_momentum_research_prototype": "scripts/run_momentum_research_prototype.py",
}
codes = {k: {"path": v, "sha256": sha256(ROOT / v)} for k, v in code_files.items()}

# ---- 输入指纹（复制旧协议 fixed_inputs 并核哈希，不复制/改写旧输入） ----
old_protocol = json.loads(
    (ROOT / "docs/experiments/raw/research-input-preflight-2026-09-13/protocol.json").read_text()
)
fixed_inputs = old_protocol["fixed_inputs"]
inputs = {
    "snapshot_dir": {
        "path": fixed_inputs["snapshot_dir"],
        "sha256": sha256(ROOT / fixed_inputs["snapshot_dir"] / "snapshot.json"),
    },
    "calendar": {"path": fixed_inputs["calendar"], "sha256": sha256(ROOT / fixed_inputs["calendar"])},
    "publication": {
        "path": fixed_inputs["publication"],
        "sha256": sha256(ROOT / fixed_inputs["publication"]),
    },
    "actions": {"path": fixed_inputs["actions"], "sha256": sha256(ROOT / fixed_inputs["actions"])},
    "evaluation_start": fixed_inputs["evaluation_start"],
    "evaluation_end": fixed_inputs["evaluation_end"],
    "pool_expectation": fixed_inputs["pool_expectation"],
}

# ---- 两张对象的完整解析卡与递归依赖（生成物，不手改） ----
sys.path.insert(0, str(ROOT / "src"))
from lei_signal.research import definitions as d  # noqa: E402

registry = d.load_registry()
cards = {}
for ref in ("mixed.momentum.raw@1.0.0", "mixed.price.economic@1.0.0"):
    card = d.resolve(registry, ref)
    closure = {}

    def _closure(r, _seen=None):
        seen = {} if _seen is None else _seen
        if r in seen:
            return seen
        seen[r] = d.resolve(registry, r)
        for dep in seen[r].get("dependencies", []):
            _closure(dep, seen)
        return seen

    closure = _closure(ref)
    cards[ref] = {
        "card": card,
        "recursive_dependencies": sorted(closure.keys()),
    }

# ---- 代码/环境版本 ----
try:
    git_head = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT)
        .decode()
        .strip()
    )
except Exception as exc:  # noqa: BLE001
    git_head = f"unavailable: {exc}"
python_version = sys.version.split()[0]

protocol = {
    "protocol_id": "momentum-research-prototype-2026-09-13",
    "protocol_version": "1.0.7",
    "plan_version": "1.0.0",
    "date": "2026-09-13",
    "research_family": "research-data-foundation",
    "target_parameters": {
        "next_session_offset": 1,
        "exit_session_offset": 22,
        "momentum_long_lag": 252,
        "momentum_skip_lag": 21,
        "note": "与实现常量逐一核对；协议声明与算法不一致时运行入口拒绝",
    },
    "revisions": [
        {
            "version": "1.0.0",
            "date": "2026-09-13",
            "sha256": "cba69d49bad430c824edcadeaae06314cd25f9523eaac6705a9763c82d2875e7",
            "note": "初版冻结（原件保留于 protocol-v1.0.0.json）。",
        },
        {
            "version": "1.0.1",
            "date": "2026-09-13",
            "sha256": "3f4ec7600953071dfe78a6dab81026f16cc955671f984ebb9fc0ddb6ad0bf312",
            "note": "validate_sessions 取消静默排序；测试参数与 NaN 期望修正；"
                    "Iterable 改从 collections.abc 导入。未被正式运行消费"
                    "（原件保留于 protocol-v1.0.1.json）。",
        },
        {
            "version": "1.0.2",
            "date": "2026-09-13",
            "sha256": "329666ff8b86fc4a58055fdc47a6927325a71ac7b50dc75a2baa7d0c4daa35de",
            "changes": [
                "新增 momentum_prototype.adapt_company_events：真实行动原始记录"
                "（cash_per_unit/ex_date/裸码符号）到 reconstructed_economic_index "
                "所需字段的逐项适配；停牌不进经济指数；字段缺失抛错停止受影响产品。"
                "首次真实运行（run-03）暴露：裸码行动未被挂接、行动字段名不匹配，"
                "经济指数在无分红/拆分调整下错误重建，run-03 已作废保留。",
            ],
            "impact": "测量参数不变；run-03 失败存档，修复后 run-04 复跑。"
                      "run-04 的 772 个真实历史值经主控独立复算一致，保留封存。",
        },
        {
            "version": "1.0.3",
            "date": "2026-09-13",
            "sha256": "7d7562f7d350038643ce4d099254d7bcc2c95ffdc137e1707e843b30eca8da1f",
            "note": "A–D 集中返修版本，主控复核 §9.1 已确认收口"
                    "（原件保留于 protocol-v1.0.3.json）。其完整修订内容见执行"
                    "报告 §11；本文件条目在此后的版本中保留为历史索引。",
        },
        {
            "version": "1.0.4",
            "date": "2026-09-13",
            "sha256": "9b05212dc6ebecfc9c1157bead981700b9778d86f461edb54ccd048276dc480e",
            "note": "R1/R2 返修版本，主控复核 §10 据此审阅。其字节文件在 Task 0 "
                    "改码后被原地覆盖且未预留版本副本，字节级重构尝试未匹配；"
                    "详见 protocol-v1.0.4.README.md，封存哈希以本条与执行报告 "
                    "§12.3 为准。",
        },
        {
            "version": "1.0.5",
            "date": "2026-09-13",
            "changes": [
                "Task 0（新长任务 fixed-etf-evidence-integration 的有限收尾）："
                "T1 全部配对被排除的期保留日期行（n=0/缺失/原因），rank_diagnostic "
                "对空集合返回缺失结果而非崩溃；标签状态改为逐行互斥分类并与总行数"
                "对账。T2 历史模式的晚取得以受影响观察时点判别（不只与评价期末"
                "比较），并声明 observation_cutoff_assumption（15:00 为保守测试"
                "截点，非已证实到达/决策时刻）。T3 修复 v1.0.3/v1.0.4 历史身份"
                "说明（旁置 README + 主控重构件）。",
            ],
            "impact": "测量参数（公式/窗口/容差/模式边界/输入）不变；772 个已确认"
                      "真实历史值继续封存；修复不改变合法输入的算术结果。",
        },
        {
            "version": "1.0.6",
            "date": "2026-09-13",
            "sha256_note": "生成后代码继续修改（out 目录创建修正），本版本未被"
                           "任何正式运行消费；字节见 protocol-v1.0.6.json。",
            "note": "本版本在其任何正式运行消费前，因函数内 import 排序修正"
                    "（ruff I001，无行为变化）重生成一次；字节以"
                    " protocol-v1.0.7.json 现值为准。",
            "changes": [
                "新长任务 fixed-etf-evidence-integration Task 5：CLI 新增可选 "
                "research_evidence 协议字段——存在时校验真实证据包（拒绝任何被拒"
                "记录）、codes 必须含 qualification_bundle 键，并把已核上市事实经 "
                "listing 桥接传入 check_snapshot(listing_evidence=…)；只让证据"
                "确实解决的具体发现改变，资格授予仍归底层闸门。省略该字段时行为"
                "与 v1.0.5 完全一致。",
            ],
            "impact": "测量参数（公式/窗口/容差/模式边界）不变；772 个已确认真实"
                      "历史值继续封存。",
        },
    ],
    "goal": (
        "把已登记的 ETF 动量指标做成输入可追溯、数值可复算、未来观察目标明确、"
        "资料不足会明确停止相关计算的研究样板；不开发更多指标、不追求更高历史收益。"
    ),
    "target_id": "protocol:momentum-next-close-21-session@1.0.0",
    "target_note": (
        "本轮协议的唯一未来观察目标；是协议测量项，不是登记表对象，"
        "不可冒充 mixed.momentum.rank 的按代码打破并列的选股顺序。"
    ),
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
        "python_version": python_version,
        "dependencies": "pandas, numpy, pytest, ruff（零新增依赖，零网络请求）",
    },
    "formula": {
        "momentum": "M(t)=I(t-21)/I(t-252)-1（按该产品自身有效报价位置；首次需 253 条）",
        "target": "Y(t)=I(x)/I(e)-1，e 为 t 之后第一个交易日，x 为 e 之后第 21 个交易日",
        "diagnostic": "Spearman 等价：两列各自并列平均名次，再算名次的 Pearson 相关",
    },
    "time_semantics": {
        "observation_dates": "评价区间内各完整月份的最后交易日；月份不完整不推断月末",
        "evaluation_window": f"{fixed_inputs['evaluation_start']} ~ {fixed_inputs['evaluation_end']}",
        "available_at": (
            "t 收盘最早只能在其实际可得后用于决策；目标在 x 收盘且必要资料可得后才"
            "可能成为完整历史标签；未知 available_at 保留 null"
        ),
        "historical_reconstruction_only": (
            "真实资料缺 available_at 时只能事后重建，不能冒充严格历史可知输入"
        ),
    },
    "modes": {
        "synthetic": {
            "description": "合成夹具验证算法与时间安排正确；标 synthetic=true，不伪装交易所数据",
            "exit": {"0": "模式完整完成", "2": "质量限制导致研究拒绝", "3": "参数/输入/运行失败"},
        },
        "historical-diagnostic": {
            "description": (
                "若完整性/来源/真实描述用途允许，重建经济指数与本轮动量、报告 unknown "
                "action 时点与 missing；不得写真实 targets/rank 结果"
            ),
            "exit": {"0": "诊断完整完成（不代表 qualified-research 也成功）", "2": "资料限制拒绝", "3": "失败"},
        },
        "qualified-research": {
            "description": (
                "仅当排序与研究信号两种用途都明确允许、对象与源通过、经济价格与公司行动"
                "历史可知证据完整、评价池/日历合格时运行；当前预期达不到，输出拒绝"
            ),
            "exit": {"0": "预测诊断放行", "2": "资格/资料限制拒绝", "3": "失败"},
        },
    },
    "tolerance": {"absolute": 1e-12, "relative": 1e-12, "integer": 0},
    "explicitly_not": [
        "不新增交易因子对象；本轮只保存协议版本与哈希",
        "不运行账户、不输出金额/交易/账户回报；policy 不伪造已运行政策卡",
        "不训练/调参/挑结果；不做五分组/十分组；不做显著性或独特 alpha 声明",
        "不安装 Qlib/Alphalens/vectorbt/Backtrader/LEAN",
        "不用 allow_conditional/accept_structural 绕过真实输入限制；不删产品、不缩短区间",
        "历史诊断成功不表示 qualified-research 也成功；描述允许不意味预测分析允许",
    ],
}

out = ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13/protocol.json"
out.write_text(json.dumps(protocol, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", rel(out))
print("git_head", git_head)
print("momentum card deps", cards["mixed.momentum.raw@1.0.0"]["recursive_dependencies"])
print("protocol sha256", sha256(out))
