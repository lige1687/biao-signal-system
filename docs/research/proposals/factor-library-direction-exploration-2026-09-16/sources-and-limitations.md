# 来源与限制记录（sources-and-limitations）

日期：2026-09-16（v1.1 返修轮更新）。【来源：执行agent探索提案，待主控复核】
本轮（v1.1）为按主控复核 R1–R4 的文档返修：零代码修改、零测试/真实统计、
零联网/安装、零共享登记与 OKR 写入；只读核对了被引代码与对象卡事实。

## 1. 本地阅读范围（全部只读）

**规范与策略（全文或主要部分）**：AGENTS.md（根）、docs/trading-spec-v1.md、
docs/research/experiment-backtest-principles.md（v1.1）、
docs/research/definition-standard.md（v1.1.0）、
docs/research/ai-execution-contract.md（v1.0.1）、
docs/literature-learning/README.md（含 v1.1.0 工作流）、
docs/research/factor-unit-usage.md、
docs/superpowers/plans/2026-09-16-factor-evidence-reliability-v1.md（含
dispatch-status）、docs/plan-sector-trend-page.md（前 120 行，红线与前提部分）。

**主控裁决（全文）**：b1-closeout-controller-2026-09-16.md、
factor-lab-final-controller-decision-2026-09-15.md（含 §6 归档补件复核）、
factor-unit-interpretation-closeout-2026-09-16.md。

**执行报告与工作线材料（结论与关键节）**：
b1-dual-ma-first-real-description-2026-09-16.md（一句话结论/先读页/§1-2/
节标题）、factor-research-workbench-v1-2026-09-14.md（头部与结论）、
factor-research-workbench-mandate-2026-09-14.md、
factor-library-external-backlog-2026-09-09.md（全文）、
research-tool-reuse-shortlist-2026-09-14.md（全文）、
factorhub-api-reuse-review-2026-09-14.md（全文）、
qlib-alpha158-definition-review-2026-09-12.md（结论与依据节）、
docs/handoff-sentiment-workstream-2026-09-07.md（全文）、
midzone-breadth-timing-2026-09-07.md 与 breadth-price50-decision-2026-09-09.md
（一句话结论）、docs/superpowers/plans/2026-09-08-broad-index-etf-research.md
（结构与状态节）、docs/experiments/broad-etf-research-plan-and-baseline-2026-09-08.md
（一句话结论）。

**登记表与配置（结构化提取）**：definitions.v1.json（容器 v1.2.0；枚举全部
81 个对象 ID/类型/用途，未逐卡读全文）；configs/rules.v1.yaml（dual_ma/
ema20 相关节定位，未全文）。

**代码盘点（存在性与关键定义，未通读）**：src/lei_signal/research/ 目录树、
factor_unit/factor_lab 文件清单；rules/dual_ma.py::dual_ma_bull_state 定位；
market_context 下 a_share_breadth.py（P0 修复段）、sentiment.py、
market_mood.py、retail_heat.py 模块头、sector_trend.py 存在性；
factor_evidence 目录存在性（v1.0 时不存在；**返修轮复核：主控复核时已见
六模块文件**）；本地缓存 a_share_codes.json 计数（5564 码含 618 只 sh68）。

**返修轮新增只读核对（v1.1，供 revision-response 引用）**：
docs/experiments/factor-library-direction-controller-review-2026-09-16.md
（主控复核报告全文）；state_description.py 的 synthetic-only 校验段
（`data_mode != "synthetic"` 即抛错）；b1_description.py::describe_b1 签名
（data_mode=real）；b1_contract.py 固定 symbol "510300"；登记卡
breadth.csi300.b200.common（unit=fraction）、breadth.three_tier（阈值
0.433/0.567）、mixed.asset.total_return（unit=fraction）、cash.zero。

**本轮未读但存在的相关材料（不代表不存在，只是未消费）**：
qlib-alpha158-controller-review-2026-09-13.md、factor-lab-final-closeout
执行报告正文、宽度证据映射两份、factor-unit b0 各轮修复报告、
sentiment 线六轮实验正文、.claude/skills/macd-reading/SKILL.md、
web/ 前端实现、OKR 服务端数据（未调用 API）。

## 2. 外部访问记录

| 时间 | 对象 | 方式 | 结果 |
|---|---|---|---|
| 2026-09-16 | https://pypi.org/pypi/alphalens-reloaded/json | 一次只读 fetch | 0.4.6（2025-06-02）、Apache-2.0、Python≥3.10、依赖链含 empyrical-reloaded/statsmodels/seaborn |

外部公开页面消费共 **1 个**（限额 20）。其余外部结论全部转引本地 2026-09-09
至 09-14 的审阅文档，本轮未复核其原始链接的当前有效性（本地审阅时已核，
标注日期见各文档）。FactorHub 本轮零调用（不读密钥、不碰认证接口）。

## 3. 未确认项（不影响主结论，但引用时须带本标注）

1. 全A宽度历史序列在 P0 修复后是否回算（代码与缓存已修，回算未证）。
2. B1 目标"含分红财富"等价性：维持 blocked，主控未解除。
3. factor_lab 任何真实数据 IC 诊断：未找到执行记录（推断为不存在）。
4. 情绪线"板块热度分位满窗口"（交接称约 2026-09 底）当前是否已达；前向
   存证账本是否连续执行（交接声明，未核验）。
5. ETF bars 本地缓存对候选载体（如 510500/159915）的覆盖与档位（C1 预算
   估算未做实测）。
6. OSAP/JKP/French 各下载页当前状态（本地审阅后未再核）。
7. factor_evidence 六模块的运行与验收状态：**文件存在已核实（主控复核与
   返修轮均见），但运行/交付/验收状态未知**，以该任务实际交付为准。

## 4. 推断与证据边界

- **【推断】**"宽基 ETF 同涨同跌使多载体独立性有限"——来自市场常识与
  本地宽度证据的间接推论，未做本地相关性计算。
- **【推断】**C2 极端位格子样本稀少——基于情绪线恐慌事件次数（4 次/4 年）
  的类比，未预计算。
- **【推断】**"alphalens 依赖链对本地环境是新增负担"——基于 pyproject
  已声明依赖与 PyPI 元数据对比，未在本地环境试装。
- **【裁决转引】**B1 数字、factor_lab 收口范围、情绪线信号状态、宽度择时
  证伪——均为本地主控裁决/已归档实验，本轮未重算。
- 本提案中的路线排序、候选比较、预算建议全部是**我的判断**，待主控复核；
  引用的他人完成声明（如 factor_lab 145 测试通过）均为执行者声明+主控
  实跑记录的组合，本轮未复跑。

## 5. 实际修改清单

**v1.0（初版）新增**：本目录六文件（README / capability-map /
candidate-directions / reuse-decisions / roadmap-and-next-prompts /
sources-and-limitations）。

**v1.1（返修轮）修改，全部仍限于本目录**：

- `history-v1/` 新建，封存 v1.0 六文件原字节（SHA-256 与主控复核记录一致，
  见 §7）；
- 六份现行文件按 R1–R4 修订（各文件末尾有修订记录）；
- 新增 `revision-response.md`（逐项旧说法/新说法/证据位置）。

未修改：src/、tests/、scripts/、configs/、AGENTS.md、registry.json、INDEX.md、
OKR、任何旧报告/raw/冻结协议；未执行任何 git 写操作；未安装依赖；未运行
回测或真实因子计算；未调用付费 API；未读取密钥文件。返修轮外部访问为零。

## 6. 复核线索（给主控的快速抽查入口）

- B1 数字：docs/experiments/b1-dual-ma-first-real-description-2026-09-16.md
  §一句话结论 + b1-closeout-controller-2026-09-16.md §2。
- 登记表对象清单：docs/research/definitions.v1.json（objects 数组）。
- 可靠性任务状态：docs/superpowers/plans/2026-09-16-factor-evidence-reliability-v1.dispatch-status.md
  （派发史）+ src/lei_signal/research/factor_evidence/（实现文件，运行状态未知）。
- 情绪线证伪清单：docs/handoff-sentiment-workstream-2026-09-07.md §3.3
  （旧交接标注，本轮转引未复验）。
- P0 修复：src/lei_signal/market_context/a_share_breadth.py:132-140 +
  ~/.lei_signal_lab/cache/a_share_codes.json（sh68 计数）。
- 本提案返修依据：docs/experiments/factor-library-direction-controller-review-2026-09-16.md。

## 7. 封存件指纹（history-v1/，与主控复核记录一致）

| 文件 | SHA-256 |
|---|---|
| README.md | c17065086224dc9efa808a1dfd1bf0a650ac426069db0251a776690a391fb836 |
| candidate-directions.md | 9ba28fab958f25bfec24bed06e17f4cb4f5feaa8db6ad19d04ed39ea7d24a1f3 |
| capability-map.md | df4cf3d98646d6f38b08a2ca4e87046ecfdc0164fde274c79adf770ad3393e72 |
| reuse-decisions.md | 2192557530ec33137eb8bd87759ec0e8fbe8ab78581fabccb8c9c5aee232f03b |
| roadmap-and-next-prompts.md | 10fc5548ff8d4166c354f5cb70327cee85f5e9721605cb0b25113b59ee2f0381 |
| sources-and-limitations.md | 9dbb327989b70ed74123cb01cd2fee0ba84a4b20e6707014706285b861da79b1 |

## 修订记录

| 版本 | 日期 | 变化 |
|---|---|---|
| v1.0 | 2026-09-16 | 初版 |
| v1.1 | 2026-09-16 | 返修轮：新增主控复核报告与 R3 关键代码/对象卡核对记录、factor_evidence 时点状态、前向存证未核验标注；修改清单与复核线索更新；新增 §7 封存件指纹 |
