"""factor_evidence 独立协议与固定合同（先验证，后计算）。

本模块是「因子证据可靠性 v1」的协议绑定层：运行协议必须与本模块**常量**
逐值相符——固定对象、输入身份、方法参数、规范指纹、必需代码键哈希。不允许
自填 approval=true、裁剪必需键或删校验清单绕过。CLI 只接受正式冻结版本
文件（文件名与内容版本一致），草案与 current 指针一律拒绝。

退出语义：身份/结构错误抛 ValueError（CLI→3）；资料不完整抛
FactorEvidenceIncompleteError（CLI→2）。两者都不得留下成功 manifest。
模块导入不计算、不写盘。旧 factor_lab/factor_unit/规则/旧 raw 全部只读，
本包不 import 旧汇总函数，不调用旧因子/目标计算入口。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

#: 本轮独立协议身份（不是 B1 v1.0.2，不冒充旧协议续版）
IDENTITY = "factor-evidence-reliability@1.0.0"
SPEC_VERSION = "1.0.0"

#: 顶层身份承载字段（主控R1：逐值绑定，不得自改对象或用途）
OBJECT_REF = "candidate:lei.dual_ma.bull_state@draft-1"
FIXED_USE = "post_hoc_historical_sensitivity_diagnostic"

#: 必需规范（不可裁剪；路径/版本/指纹逐值固定，读磁盘核实际内容）
REQUIRED_STANDARDS = (
    ("docs/research/experiment-backtest-principles.md", "1.1",
     "ac5a676c0635441b66f656c8e1249b69bade36365cc9065ed6341a610b6a53c6"),
    ("docs/research/definition-standard.md", "1.1.0",
     "3406feaea2bbb8d23a91ddc8fa0c85e62ff86437bdf443d459f2c97b0e99cd5c"),
    ("docs/research/ai-execution-contract.md", "1.0.1",
     "deab6c1ca20505f92d06516ffff943b8501fff2e01f8c6b3928c6626072af962"),
    ("docs/research/experiment-report-template.md", "1.1.0",
     "cae2853f81841de6f424c6bda10e6708dd35574ebb8a325088fe507c5755d54e"),
    ("docs/research/definitions.v1.json", "容器1.2.0（只读）",
     "c008efb991c40f06bb7fe0236b0892a6902c68a83cb4657ae5c2651e9d270e05"),
)

TASK_BOOK = {
    "path": "docs/superpowers/plans/2026-09-16-factor-evidence-reliability-v1.md",
    "sha256": "77fb4152b6e415903bab427a25f823ac1d4b906cedf487ce7f47c01c71a61fc5",
}

CARD = {
    "path": ("docs/experiments/raw/factor-research-workbench-v1-2026-09-14/"
             "candidate-card-dual-ma-bull-state-draft-1.md"),
    "sha256": "907d17631e27011423bebbf068bcb2bbc6e1b44a184618597cf54f868e066dc1",
}

#: 固定输入身份（任务书 §1 指定；不得自改文件后自证）
FIXED_INPUT_IDENTITY = {
    "base_dir": "docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16",
    "observations_csv_path": "run-02/observations.csv",
    "observations_csv_sha256": "1dfe4c206212c31809f53f4b66bb40b3dd4ec193b03daf37c1540f8307eb9d5d",
    "summary_json_path": "run-02/summary.json",
    "summary_json_sha256": "ce4c51ba5e0d7bb7f7e10630b07fc106a59c98f0d4f57ac290f861164c9bfcf7",
    "run02_manifest_path": "run-02/manifest.json",
    "run02_manifest_sha256": "ca7154fc9bdde40c54490a37c8de47acfaaf138911735b1d6dac0c67bf614fde",
    "calendar_json_path": "run-02/input-package/calendar.json",
    "calendar_json_sha256": "aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1",
    "supplement_full_file_listing_path": "supplement/full-file-listing.json",
    "supplement_full_file_listing_sha256":
        "320f4c3139c8edbb92b812217310d646df68685cbaf10b4a83ff161b9ca8a453",
    "supplement_manifest_path": "supplement/supplement-manifest.json",
    "supplement_manifest_sha256":
        "982baa52667b35c732f39c3007a808a57db96acf977248bb3b834e1ede95c592",
    "b1_protocol_v101_sha256": "00a16465e5232d3760cedbe9bccb5332b05e4f777f1732e8911ee586974c3af2",
}

#: 必需代码键（实现常量，协议不可裁剪；额外依赖加入集合并记录）
REQUIRED_CODE_KEYS = (
    "src/lei_signal/research/factor_evidence/__init__.py",
    "src/lei_signal/research/factor_evidence/contract.py",
    "src/lei_signal/research/factor_evidence/observations.py",
    "src/lei_signal/research/factor_evidence/stability.py",
    "src/lei_signal/research/factor_evidence/resampling.py",
    "src/lei_signal/research/factor_evidence/runner.py",
    "scripts/run_factor_evidence_reliability.py",
    "src/lei_signal/research/trading_calendar.py",
)

#: 固定方法参数（任务书 §2；协议 fixed_params 必须与之逐值相等）
FIXED_PARAMS = {
    "family": "factor-evidence-reliability",
    "state_kind": "binary_state（首版唯一支持：真布尔或缺失）",
    "symbol": "510300",
    "evaluation_window": {"start": "2019-10-08", "end": "2025-12-31"},
    "schedule_coverage": {
        "start": "2019-09-02",
        "end": "2026-02-03",
        "note": "与 B1 覆盖区间一致；end=标签成熟截止日，用于 e/x 日期与区间身份",
    },
    "target_main": ("P_vendor(t+22)/P_vendor(t+1) - 1"
                    "（观察日t后第1个至第22个交易日收盘，21个价格变动区间；"
                    "直接取观察表 main 列，不重算）"),
    "target_aux": ("min(0, min(P_vendor(s)/P_vendor(t+1) - 1)), s∈[t+1,t+22]"
                   "（原样描述；不据 aux 另选赢家）"),
    "target_basis_note": ("供应商调整价变化，未核验作含分红财富；未来目标截止 "
                          "2026-02-03 15:00+08；原件取得 2026-09-08，历史可得性"
                          "未知；全部为事后描述"),
    "delta_definition": ("delta = mean(main | state=true) - mean(main | state=false)"
                         "；单位小数变化率，展示×100记作百分点"),
    "legal_set": ("flag_state_known ∧ flag_main_legal ∧ flag_mature"
                  "（B1 共同合法集合）；aux 缺失不删主目标"),
    "year_key": "信号发生年（session 年）；跨年目标归信号发生年，不当独立时期验证",
    "leave_one_year_out": ("2019–2025 七个年份逐一留出后全期 delta；"
                           "任一组缺失则 null+原因；不挑有利年份"),
    "equal_weight_year_mean": ("两组都有值年度差的等权均值，附实际年份键集；"
                               "只是另一描述视角，不替代全期结果，不是因果校正"),
    "partial_year_note": "2019 为不完整观察年（评价窗自 2019-10-08 起）",
    "overlap": {
        "interval_unit": ("相邻交易日的价格变动区间，按 (前session, 后session) "
                          "相邻对识别；不是共同日期点数"),
        "per_label": "每条合法标签 = 其 (e,x] 覆盖的全部相邻区间（本例 21 个）",
        "adjacent_audit": ("相邻观察（按完整交易日轴位置）共享区间数量与比例；"
                           "全表总区间引用数与唯一区间数"),
        "reuse_note": "重用比只是描述，不是有效样本数",
        "sparse_anchor_session": "2019-10-08",
        "sparse_step": 23,
        "sparse_policy": "只审计原规则锚点，不扫描其他起点选最好",
    },
    "resampling": {
        "method": ("circular_block_bootstrap：固定长度循环区块重抽；"
                   "首尾相接是计算约定，不是真实行情连接"),
        "block_lengths": [63, 126],
        "block_length_note": ("L=63 与 126 为主控固定研究设定，不是最优参数、"
                              "不是论文标准；两种L并排完整展示，不取有利一个"),
        "reps": 2000,
        "seed": 20260916,
        "rng": "numpy.random.Generator(numpy.random.PCG64(20260916))；每种 L 分别新建",
        "start_draw": ("每重复从整数[0,n)等概率抽 k=ceil(n/L) 个起点；"
                       "一次性 integers(0, n, size=(reps, k))；起点矩阵全部保存"),
        "index_rule": ("(start+j) % n, j=0..L-1，按块拼接后截到 n 行；"
                       "同一索引用于 state/main/合法性三列，绝不分别抽两组"),
        "axis_rule": ("n 为完整评价日期轴长度（日历推导，非压缩后行数）；"
                      "先保留完整时间轴，再按合法性计入每次统计；"
                      "不把缺行压缩成连续行情"),
        "null_rule": "每次缺任一组则 delta=null，保存原因与两组实际 n；不额外抽取补足有效值",
        "min_valid_reps": 1900,
        "min_valid_note": "有效重复不足 1900/2000 时不输出区间（本轮质量约定，不是学术门槛）",
        "quantiles": {"lower": 0.025, "upper": 0.975, "method": "linear",
                      "name": "条件性95%重抽范围"},
        "not_estimable": "单组、空集、n<L、日历不完整时明确 not_estimable",
        "interpretation": ("只作为假设条件下的历史敏感性诊断：不能证明行情机制不变，"
                           "不能消除资料口径/已见数据/研究选择偏差；不报有效概率、"
                           "p值、显著通过、独立样本数或已排除过拟合，"
                           "不用过零作机械采纳判决"),
    },
}

FIXED_TOLERANCE = {"float": 1e-12, "counts_keys_nulls": "严格一致"}

REQUIRED_OUTPUT_FIELDS = [
    "protocol.source.json", "stability.json", "yearly.csv",
    "leave-one-year-out.csv", "overlap.json",
    "resampling-L63-starts.npy", "resampling-L63-replicates.csv",
    "resampling-L126-starts.npy", "resampling-L126-replicates.csv",
    "uncertainty.json", "evidence-card.json", "report.md", "manifest.json",
]

FIXED_NO_CLAIMS = [
    "probability_factor_effective", "p_value", "significance_pass",
    "independent_sample_count", "overfitting_excluded", "regime_invariance_proved",
    "causal_conclusion", "strategy_return", "production_advice",
    "point_in_time_verified", "dividend_wealth_equivalence",
]

#: 输入身份哈希键（load 前逐项核验；base_dir 之外的键均须匹配磁盘）
_INPUT_SHA_KEYS = (
    ("observations_csv_path", "observations_csv_sha256"),
    ("summary_json_path", "summary_json_sha256"),
    ("run02_manifest_path", "run02_manifest_sha256"),
    ("calendar_json_path", "calendar_json_sha256"),
    ("supplement_full_file_listing_path", "supplement_full_file_listing_sha256"),
    ("supplement_manifest_path", "supplement_manifest_sha256"),
)


class FactorEvidenceIncompleteError(Exception):
    """资料不完整（CLI 退出 2）：与身份错误（3）分开。"""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def validate_protocol(protocol_path, repo_root) -> dict:
    """校验冻结运行协议；任何逐值不符抛 ValueError。返回合同 dict。"""
    root = Path(repo_root)
    p = Path(protocol_path)
    _require(p.is_file(), f"协议文件不存在：{protocol_path}")
    try:
        protocol = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"协议不是合法JSON：{exc}") from exc
    _require(isinstance(protocol, dict), "协议必须是JSON对象")
    _require(protocol.get("spec_status") == "frozen",
             "CLI 只接受冻结正式协议（草案/草稿状态拒绝）")
    _require(protocol.get("spec_version") == SPEC_VERSION,
             f"spec_version 必须为 {SPEC_VERSION}（假版本拒绝）")
    _require(p.name == f"protocol-v{SPEC_VERSION}.json",
             f"协议文件名必须与内容版本相符（protocol-v{SPEC_VERSION}.json；"
             "拒绝 current 指针与同内容改名入口）")
    _require(protocol.get("identity") == IDENTITY,
             f"identity 必须为 {IDENTITY!r}")
    _require(protocol.get("object_ref") == OBJECT_REF,
             f"协议 object_ref 必须为 {OBJECT_REF!r}"
             f"（收到 {protocol.get('object_ref')!r}；身份承载字段逐值绑定）")
    _require(protocol.get("use") == FIXED_USE,
             f"协议 use 必须为 {FIXED_USE!r}"
             f"（收到 {protocol.get('use')!r}；不得自改为生产或其他用途）")
    _require(protocol.get("approval") is not True,
             "不允许自填 approval=true（授权只来自任务书记录）")

    # 规范：不可裁剪/扩项，读磁盘核内容
    standards = protocol.get("standards")
    _require(isinstance(standards, list), "standards 必须是不可裁剪列表")
    by_path = {s.get("path"): s for s in standards if isinstance(s, dict)}
    _require(len(by_path) == len(standards) == len(REQUIRED_STANDARDS),
             "standards 不得裁剪/重复/扩项")
    for path, version, sha in REQUIRED_STANDARDS:
        s = by_path.get(path)
        _require(s is not None, f"缺少必需规范：{path}@{version}")
        _require(s.get("version") == version and s.get("sha256") == sha,
                 f"{path} 版本/指纹与固定值不符（文档变更属诚实版本变化）")
        fp = root / path
        _require(fp.is_file() and sha256_file(fp) == sha,
                 f"{path} 磁盘文件与声明指纹不符（只比较协议字段不读文件不算验收）")

    _require(protocol.get("fixed_params") == FIXED_PARAMS,
             "协议 fixed_params 与固定方法参数逐值不符")

    for key, fixed in (("task_book", TASK_BOOK), ("candidate_card", CARD)):
        got = protocol.get(key) or {}
        _require(got.get("path") == fixed["path"]
                 and got.get("sha256") == fixed["sha256"],
                 f"{key} 引用与固定值不符")
        fp = root / fixed["path"]
        _require(fp.is_file() and sha256_file(fp) == fixed["sha256"],
                 f"{key} 磁盘内容与声明不符（必须读所引用文件核实际内容）")

    identity = protocol.get("input_identity") or {}
    for key, fixed in FIXED_INPUT_IDENTITY.items():
        _require(identity.get(key) == fixed,
                 f"协议 input_identity.{key} 与固定输入身份不符"
                 f"（{identity.get(key)!r} != {fixed!r}）")

    code_identity = protocol.get("code_identity")
    _require(isinstance(code_identity, dict), "code_identity 必须是 dict")
    missing = [k for k in REQUIRED_CODE_KEYS if k not in code_identity]
    _require(not missing, f"必需代码键被裁剪：{missing}")
    extra = [k for k in code_identity if k not in REQUIRED_CODE_KEYS]
    _require(not extra, f"code_identity 含未登记键（不得自行扩键）：{extra}")
    for rel in REQUIRED_CODE_KEYS:
        fp = root / rel
        _require(fp.is_file(), f"必需代码键文件缺失：{rel}")
        _require(code_identity[rel] == sha256_file(fp),
                 f"必需代码键哈希不符：{rel}（代码/配置漂移拒绝）")

    _require(protocol.get("tolerance") == FIXED_TOLERANCE,
             f"协议 tolerance 必须逐值等于 {FIXED_TOLERANCE!r}（宽松容差拒绝）")
    _require(protocol.get("output_fields") == REQUIRED_OUTPUT_FIELDS,
             "协议 output_fields 必须逐值等于必需输出清单")
    _require(protocol.get("no_claims") == FIXED_NO_CLAIMS,
             "协议 no_claims 必须逐值等于固定禁止声明清单")

    return {
        "identity": IDENTITY,
        "fixed_params": json.loads(json.dumps(FIXED_PARAMS)),
        "input_identity": dict(FIXED_INPUT_IDENTITY),
        "protocol_path": str(p),
        "protocol_sha256": sha256_file(p),
    }


def verify_input_hashes(repo_root, input_identity=None) -> dict:
    """按固定输入身份逐项核验六个输入文件哈希；不符抛 ValueError。

    返回 {相对路径: 实测哈希}。任何文件内容漂移都在计算之前拒绝。
    """
    root = Path(repo_root)
    if input_identity is not None:
        for key, fixed in FIXED_INPUT_IDENTITY.items():
            got = input_identity.get(key)
            if got != fixed:
                raise ValueError(
                    f"input_identity.{key} 与固定输入身份不符"
                    f"（{got!r} != {fixed!r}）")
    root = Path(repo_root)
    verified: dict[str, str] = {}
    for path_key, sha_key in _INPUT_SHA_KEYS:
        rel = FIXED_INPUT_IDENTITY[path_key]
        fp = root / FIXED_INPUT_IDENTITY["base_dir"] / rel
        _require(fp.is_file(), f"固定输入缺失：{fp}")
        actual = sha256_file(fp)
        _require(actual == FIXED_INPUT_IDENTITY[sha_key],
                 f"固定输入哈希不符（错身份必须在计算前拒绝）：{rel} "
                 f"{actual} != {FIXED_INPUT_IDENTITY[sha_key]}")
        verified[rel] = actual
    return verified
