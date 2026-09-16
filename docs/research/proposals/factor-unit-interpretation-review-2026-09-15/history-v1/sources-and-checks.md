# 来源、核验与交付清单

任务：双均线首轮结果解释·并行审阅任务书 v1.0.0（2026-09-15）。
执行者身份：独立审阅执行者（Claude Code，ark-code-latest）。工作目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`；分支 `codex/factor-unit-research-20260915`；HEAD `8ba16576b75e605aa1b0d0902568c760c4b99095`（与任务书一致，已核）。

## 1. 输入清单（路径 / SHA-256 / 修改时间）

读取时记录一次，交付前复算一次，**两遍哈希全部一致，无漂移**（复算时间 2026-09-15 23:1x 本地）。

| 路径 | SHA-256 | mtime | 读取范围 |
|---|---|---|---|
| `AGENTS.md` | `ca9621eec126a03c71a4f0dc3373fee958e729746520c5d133e95e3fbc550142` | 2026-09-13 01:31 | 全文 |
| `docs/research/experiment-backtest-principles.md`（v1.1 ✓） | `ac5a676c0635441b66f656c8e1249b69bade36365cc9065ed6341a610b6a53c6` | 2026-09-10 22:28 | 全文 |
| `docs/research/definition-standard.md`（1.1.0 ✓） | `3406feaea2bbb8d23a91ddc8fa0c85e62ff86437bdf443d459f2c97b0e99cd5c` | 2026-09-10 22:28 | 全文 |
| `docs/research/ai-execution-contract.md`（1.0.1 ✓） | `deab6c1ca20505f92d06516ffff943b8501fff2e01f8c6b3928c6626072af962` | 2026-09-13 01:31 | 全文 |
| `docs/research/experiment-report-template.md`（1.1.0 ✓） | `cae2853f81841de6f424c6bda10e6708dd35574ebb8a325088fe507c5755d54e` | 2026-09-10 22:30 | 全文 |
| `docs/trading-spec-v1.md` | `dd75d70cd22b103e815d3b314b47c36731230aa268d05e42fa447ba55e639798` | 2026-08-04 11:35 | §2.2、§3、§4（双均线"道路"定位相关段，行 25-94）+ 全文 grep 定位 |
| `docs/experiments/raw/factor-research-workbench-v1-2026-09-14/candidate-card-dual-ma-bull-state-draft-1.md` | `907d17631e27011423bebbf068bcb2bbc6e1b44a184618597cf54f868e066dc1` | 2026-09-14 19:33 | 全文 |
| `docs/superpowers/plans/2026-09-15-510300-offline-reuse-handoff.md` | `268fcfaee364e694f4e9200d3ea58e4f8ff03bec0f3e9552b8d226dbac8c51e4` | 2026-09-15 22:19 | 全文 |
| `docs/experiments/factor-unit-four-fixes-controller-2026-09-15.md` | `801bf584e31fa416726e3f9dd4316a85c37c19f719d6826e25e7bdf8103fcdd8` | 2026-09-15 22:19 | 全文 |
| `src/lei_signal/research/factor_unit/close_state.py` | `b0efb324a2ef65d1f415c19be4f50b96ebf25f140da0c31b2b759d68ef04db10` | 2026-09-15 12:54 | 全文（99 行） |
| `src/lei_signal/research/factor_unit/state_description.py` | `b1394792ad22e64ebf3702143e80bf3566508c75ff3a0ee3ffaf101f7e2609c0` | 2026-09-15 21:01 | 全文（352 行） |

直接调用函数（只读 grep，未全读文件、未运行）：
- `src/lei_signal/rules/dual_ma.py::dual_ma_bull_state`（行 36-59）
- `src/lei_signal/rules/lei_color.py::classify_colors`（行 25-55）
- `src/lei_signal/features/indicators.py::seeded_ema`（行 14-33）

目录级确认：输出目录事先不存在（已创建）；邻近的 `docs/research/proposals/510300-acquisition-review-2026-09-15/` 为另一 agent 产物，未读内容、未触碰。未读主线正在写的 B1 合同草案/输入包（任务书禁止依赖）。

## 2. 合成算术核验（实际命令与结果）

- 命令：`python3 docs/research/proposals/factor-unit-interpretation-review-2026-09-15/check_examples.py`
- 运行次数：**1 次**（预算 2 次，余 1 次未用）；退出码 **0**；结果 **25/25 PASS**（容差 1e-12）。
- 脚本边界自查：仅 `import statistics`；全部输入为内置常数；无项目 import、无文件读写、无网络。
- 题面期望值与独立手算核对：四例全部一致，无需改题（详见 `hand-examples.md` 末节）。

## 3. 未核项目（如实声明）

- **未运行任何项目测试、CLI 或研究代码**（含 pytest、factor_lab、describe_states）；本文所有实现行为结论来自只读源码，不来自运行。
- **未读取任何真实价格序列**、原始行情响应、日历文件或输入包；510300 相关事实（1558 行、日期边界等）转述自主控复核文档，本审阅未独立重算。
- **未复核其他 agent 产物**（含 510300-acquisition-review、主线 B1 草案）；主控复核文档中的测试计数（108 passed 等）为**主控证据**，本审阅未重跑、不冒认为自己的核验。
- 未核对 `configs/rules.v1.yaml` 中 lei_color 规则参数（`classify_colors` 内经 `get_rule` 读取）；候选卡与代码注释所述公式一致，参数值本身未独立验证。
- F1 反例为纯逻辑推演（未运行项目代码构造实例）；F2/F3 直接引源码行。
- 零联网、零安装、零密钥访问、零提交/暂存/工作树操作，全程成立。

## 4. 交付物清单（新目录全部文件）

| 文件 | 内容 |
|---|---|
| `scope.md` | Task 0：范围、对象、实际模型、边界、版本核对 |
| `interpretation-review.md` | Task 1：七行核对表 + 发现 F1-F3（含位置与反例）+ 待主控决定项 |
| `hand-examples.md` | Task 2：四个合成手算例与解读边界 |
| `check_examples.py` | Task 2：验算脚本（纯标准库，25 项断言） |
| `result-reading-card.md` | Task 3：六步解读骨架、三种合规措辞、三阶段区分、4 项建议 |
| `sources-and-checks.md` | Task 4：本文件 |

## 5. 链接与自审记录

- **相对链接检查**：四份文档均以行内代码（反引号）引用路径，无 Markdown 链接语法，无断链风险；同目录互引文件（`sources-and-checks.md`、`result-reading-card.md`、`check_examples.py`）逐一确认存在。
- **错误跳跃自审**（2026-09-15）：全目录扫描"因子有效 / 因子贡献 / 独立成功 / 独立命中 / 获准 / 交易指令 / 最大回撤 / 超额 / 显著"等词，全部命中均处于否定或禁止语境（"不是因子贡献""禁止出现独立命中 N 次""不得升级为交易指令"等），未发现"收益差=贡献""无重叠=独立""获准交易"式跳跃。
- **预算核对**：合成手算例 4 个（上限 4）；算术脚本运行 1 次（上限 2）；未跑全仓库测试或 factor_lab 回归；未写自动化平台。预算未耗尽，正常完成。
- **一致性抽查**：`interpretation-review.md` 引用行号与冻结 SHA 版本逐条对过（如 comp=行 224、up_ratio=行 69、aux=行 211-216、mature=行 218、sparse=行 269-305）。

## 6. 交付摘要（建议 / 证据 / 待裁决三分）

**执行者建议**（待主控采用，不自动生效）：
1. 首轮报告先落"数据限制"四条再出数（S1）；三种结论措辞出数前固定（S2）。
2. F1/F2/F3 用措辞与字段引用纪律解决（S3），代码增强留到后续（S4）。
3. 首轮报告禁止清单：因子贡献、独立命中、最大回撤、背景减法、状态带来收益。

**证据**（本审阅可直接支持的事实）：
- 实现与 B1 草案要求逐条相符（七行核对表，每行有源码位置）。
- 三个表述级发现 F1-F3，均有准确文件/行号/反例；无阻断级缺陷。
- 合成算术 25/25 通过；输入两遍哈希无漂移。

**待主控裁决**：
1. 是否采用 `result-reading-card.md` 的解读骨架与措辞清单。
2. F1/F3 是否触发 `state_description.py` 后续版本输出增强。
3. 首轮真实运行本身（主线事项，本审阅不含此授权）。

本任务为未采纳提案的审阅交付，不作实验结案，不写 registry/INDEX；归档由主控复核时统一处理。
