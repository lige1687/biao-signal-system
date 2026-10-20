"""一次性重构 v1.0.4 协议字节（Task 0 T3 同类问题的自我纠正）。

背景：Task 0 修改本轮代码后，未按规程另存版本文件即原地重生成
protocol.json，导致已封存的 v1.0.4 原件（SHA-256
9b05212dc6ebecfc9c1157bead981700b9778d86f461edb54ccd048276dc480e，
见执行报告 §12.3 与主控复核 §10）被覆盖。

生成器完全确定：以现行 generate-protocol.py 为基础，仅回退两处差异——
1) codes 中 momentum_prototype / run_momentum_research_prototype 换回
   §12.3 记录的封存哈希（其余代码文件自封存以来未改动）；
2) revisions 回退为封存时的五条目结构（v1.0.3 含 A–D changes，
   尚无 Task 0 的 v1.0.5 条目）。
若重构字节哈希与 9b05212d… 完全一致，则写出 protocol-v1.0.4.json
（明确标注为重构件）；不一致则不写任何文件，如实报告失败。
本脚本不修改现行 protocol.json 与任何旧产物。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/yongbiaoli/Desktop/lei-signal-lab")
RAW = ROOT / "docs/experiments/raw/research-momentum-prototype-2026-09-13"
SEALED_SHA = "9b05212dc6ebecfc9c1157bead981700b9778d86f461edb54ccd048276dc480e"
SEALED_MODULE_SHA = ("dd0f12c614bb2b4f8a177763535965003e51556e62a113297e4da236306ccb40")
SEALED_CLI_SHA = ("e70b440fe39c26819861810bb3c69fae922db651988b3a0a8a18392dd729dfec")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


# ---- 规范指纹（与现行相同） ----
_reg_version = json.loads(
    (ROOT / "docs/research/definitions.v1.json").read_text()).get("version")
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
    specs[key] = {"path": path, "version": version, "sha256": sha(fp)}

# ---- 代码指纹：两个本轮文件换回封存哈希 ----
code_files = {
    "definitions": "src/lei_signal/research/definitions.py",
    "factor_runtime": "src/lei_signal/research/factor_runtime.py",
    "momentum_prototype": None,  # sealed
    "data_quality": "src/lei_signal/research/data_quality.py",
    "data_snapshot": "src/lei_signal/research/data_snapshot.py",
    "trading_calendar": "src/lei_signal/research/trading_calendar.py",
    "symbol_identity": "src/lei_signal/research/symbol_identity.py",
    "run_momentum_research_prototype": None,  # sealed
}
codes = {}
for k, v in code_files.items():
    codes[k] = (
        {"path": "src/lei_signal/research/momentum_prototype.py", "sha256": SEALED_MODULE_SHA}
        if k == "momentum_prototype" else
        {"path": "scripts/run_momentum_research_prototype.py", "sha256": SEALED_CLI_SHA}
        if k == "run_momentum_research_prototype" else
        {"path": v, "sha256": sha(ROOT / v)}
    )

# ---- 输入指纹（同现行） ----
old_protocol = json.loads(
    (ROOT / "docs/experiments/raw/research-input-preflight-2026-09-13/protocol.json").read_text()
)
fixed_inputs = old_protocol["fixed_inputs"]
inputs = {
    "snapshot_dir": {
        "path": fixed_inputs["snapshot_dir"],
        "sha256": sha(ROOT / fixed_inputs["snapshot_dir"] / "snapshot.json"),
    },
    "calendar": {"path": fixed_inputs["calendar"], "sha256": sha(ROOT / fixed_inputs["calendar"])},
    "publication": {
        "path": fixed_inputs["publication"],
        "sha256": sha(ROOT / fixed_inputs["publication"]),
    },
    "actions": {"path": fixed_inputs["actions"], "sha256": sha(ROOT / fixed_inputs["actions"])},
    "evaluation_start": fixed_inputs["evaluation_start"],
    "evaluation_end": fixed_inputs["evaluation_end"],
    "pool_expectation": fixed_inputs["pool_expectation"],
}

# ---- 对象卡（同现行：登记表未变） ----
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

    closure = _closure(ref)
    cards[ref] = {"card": card, "recursive_dependencies": sorted(closure.keys())}

try:
    git_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
except Exception as exc:  # noqa: BLE001
    git_head = f"unavailable: {exc}"

revisions = [
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
        "changes": [
            "返修 A：adapt_company_events 增加严格结构/数值校验——未登记字段"
            "（含账户字段）、同义字段冲突、负/非有限金额、非正比例、重复 "
            "event_id、非法日期一律拒绝；CLI 复用 data_quality.check_actions "
            "把 BLOCK 级行动发现与计算消费绑定。",
            "返修 B：运行入口新增协议身份绑定校验（主对象/依赖/目标 ID/目标"
            "参数/卡快照与登记表实际解析/动量参数/登记表容器版本）；必需代码"
            "键固定（含本 CLI 自身），删键不能免核。specs.registry 版本改取"
            "实际容器版本 1.2.0（旧版误写 v1.0.0，纠正文案不改登记表）。",
            "返修 C：qualified-research 实现真正的合格分支（targets/rank 产出"
            "与可得时点标注），不再落回历史诊断尾部；窗口重叠计数改为按相邻"
            "两期真实 [e,x] 区间相交（含端点接触）；合成模式有产品失败时退出 2。",
            "返修 D：quality.json 落盘行动逐条发现、identity_errors 与输入"
            "时间语义；新比对脚本带 --out 且拒绝覆盖（旧 run-06 封存不重跑）。",
        ],
        "impact": "测量参数（公式/窗口/容差/模式边界/输入）不变；run-04 数值"
                  "保留为 v1.0.2 封存版本；修复不改变合法记录的消费结果，"
                  "经新比对脚本对 772 个正式键复核一致，无需重跑真实历史诊断。",
    },
    {
        "version": "1.0.4",
        "date": "2026-09-13",
        "changes": [
            "返修 R1：新增时间资格——qualified 分支在生成任何信号/目标前核对"
            "进入信号计算的行动能否在观察日决策时点（本地 15:00，带时区严格"
            "比较）前证明可知，无法证明即拒绝研究并逐条列产品/event_id/时点/"
            "原因；未来目标按事后评价标签处理，尚不可知（含晚于 x 决策时点与"
            "未知）的标签从排序配对剔除并逐条留痕；历史诊断对晚取得行动如实"
            "标 historical_reconstruction_only 与晚取得清单，不再只数空值。",
            "返修 R2：run-07 确认为中间阶段产物（其绑定的协议/CLI 原件未保留，"
            "见其 EARLY-STAGE-README），终版合成示例另存新编号；quality 新增"
            "价格检查发现逐条定位与时间违规清单。",
        ],
        "impact": "测量参数（公式/窗口/容差/模式边界/输入）不变；已确认的 "
                  "run-04 真实历史值继续封存，修复只影响资格判定与标注，"
                  "不改变合法输入的算术结果。",
    },
]

protocol = {
    "protocol_id": "momentum-research-prototype-2026-09-13",
    "protocol_version": "1.0.4",
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
    "revisions": revisions,
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
        "python_version": sys.version.split()[0],
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

payload = json.dumps(protocol, indent=1, ensure_ascii=False)
actual = hashlib.sha256(payload.encode("utf-8")).hexdigest()
print("reconstructed sha256:", actual)
if actual == SEALED_SHA:
    out = RAW / "protocol-v1.0.4.json"
    out.write_text(payload, encoding="utf-8")
    print("MATCH — 写出重构件", rel(out))
else:
    print("MISMATCH — 不写出任何文件；v1.0.4 原件按未保留处理")
    sys.exit(1)
