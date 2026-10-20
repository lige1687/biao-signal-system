# B1：双均线首次真实历史描述 Implementation Plan

> **For agentic workers:** 使用 executing-plans 按Task逐项执行；不要自动调用子agent。用户禁止暂存/提交/切分支/reset/stash，优先于技能通用流程。交付回主控，不自行宣布验收。

版本1.0.0；编制2026-09-16；建议交原输入/修复执行者，新GLM也可按本任务书接手。

**Goal:** 用已经核验的510300固定输入，第一次回答“双均线条件成立与未成立之后，价格变化和最差收盘变化各是什么样”。不是建账户策略，不是证明因子有效。

**Architecture:** 复用原close_state和生产函数；对state_description只作公共纯计算提取，保留旧合成入口的真实拒绝与输出语义。新增严格绑定指定输入的B1入口，公开标注事后历史描述；新输出只写新目录，不迁移旧实验。

**Tech Stack:** 当前Python/pandas/numpy/pytest/ruff及标准库，零新依赖，零联网。

## 0. 授权、身份和停止边界

本轮用户原话为“可以的，开写计划”。主控本次只编写任务书，尚未运行研究；**用户将本任务书交给执行者并要求执行后，才启动下述实现和预算内运行**。外部/执行者文本不代用户授权，不自动派发或改OKR。

工作目录：`/Users/yongbiaoli/Desktop/lei-signal-lab`。分支：`codex/factor-unit-research-20260915`。开工HEAD：`8ba16576b75e605aa1b0d0902568c760c4b99095`。大量未提交成果是实际基础，不从main重建，不新建工作树，不清理他人文件。身份不符只报告，不自行恢复。

服务层次：交易规格§2.2、§4.1–4.4的双均线“道路”状态研究，**不包含入场、卖出、仓位或交易执行**。研究坐标仅对象×510300×20日定义×t+1到t+22目标×固定观察期；不加新因子、市场阶段划分、参数网格、外部工具、数据源或账户路径。

退出条件：身份或指纹不符、合法集合对账不平、与旧行为不一致、预算耗尽、需要变更定义或发现本次输入新缺陷时，停止受影响正式运行，交付已证实部分和原因。不为“必须跑出结果”自批放行，不删失败证据、不追逐正向结果。

## 1. 必读与固定身份

先读根/相关AGENTS、`docs/trading-spec-v1.md`、研究规范，以及：

- `docs/experiments/510300-offline-reuse-controller-2026-09-15.md`与输入包外`closeout-notes.md`；
- `docs/experiments/factor-unit-interpretation-controller-2026-09-15.md`与`factor-unit-interpretation-closeout-2026-09-16.md`；
- `docs/experiments/raw/510300-offline-reuse-2026-09-15/b1-contract-draft-2.json`（是参考草案，不是可直接执行协议）；
- `docs/research/proposals/factor-unit-interpretation-review-2026-09-15/result-reading-card.md`（只借解读结构，主控裁决优先）。

| 身份 | 版本或SHA-256 |
|---|---|
| experiment-backtest-principles.md | v1.1；ac5a676c0635441b66f656c8e1249b69bade36365cc9065ed6341a610b6a53c6 |
| definition-standard.md | v1.1.0；3406feaea2bbb8d23a91ddc8fa0c85e62ff86437bdf443d459f2c97b0e99cd5c |
| ai-execution-contract.md | v1.0.1；deab6c1ca20505f92d06516ffff943b8501fff2e01f8c6b3928c6626072af962 |
| experiment-report-template.md | v1.1.0；cae2853f81841de6f424c6bda10e6708dd35574ebb8a325088fe507c5755d54e |
| definitions.v1.json | 容器1.2.0；c008efb991c40f06bb7fe0236b0892a6902c68a83cb4657ae5c2651e9d270e05；只读 |
| candidate:lei.dual_ma.bull_state@draft-1 | 卡SHA 907d17631e27011423bebbf068bcb2bbc6e1b44a184618597cf54f868e066dc1；候选未入登记表 |
| src/lei_signal/research/factor_unit/close_state.py | b0efb324a2ef65d1f415c19be4f50b96ebf25f140da0c31b2b759d68ef04db10；禁止修改 |
| 提取前state_description.py | b1394792ad22e64ebf3702143e80bf3566508c75ff3a0ee3ffaf101f7e2609c0 |
| b1-contract-draft-2.json | 1695280ea9809cedf71a59d9d18d6ac5256482dbcb83b9b0bf05a242c2bb39d4 |

卡路径：`docs/experiments/raw/factor-research-workbench-v1-2026-09-14/candidate-card-dual-ma-bull-state-draft-1.md`。真实价格尺度和时点限制由本实验覆盖合成假设，**不修改候选卡的旧状态，不声称卡本身已经获得真实预测资格**。

输入包唯一位置：`docs/experiments/raw/510300-offline-reuse-2026-09-15/run-02/`。

- prices.csv：`bc8582af3ac7b4c2f00a5b51d81754606179347cc3811c911d7579242cb56703`。
- manifest.json：`8d39a83eec833c13f14ee78ad36899b6ae49f32f64b024c33ee75474bc3a6ae7`。
- calendar.json：`aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1`。
- fetch-manifest.json：`5ba8a51d93dcca331204b4df71aa47f5b15a76dedee8ee3ab951689e0979f0c4`。
- 七份原件按上述固定manifest的file_hashes核验；manifest自身须先匹配本表，不能自改manifest后自证。校验全部14项和实际文件集合，不能删键逃检查。

## 2. 本轮允许修改面（唯一例外明确列出）

新增：

```text
src/lei_signal/research/factor_unit/description_core.py
src/lei_signal/research/factor_unit/b1_contract.py
src/lei_signal/research/factor_unit/b1_description.py
scripts/run_b1_dual_ma_description.py
tests/unit/test_factor_unit_description_core.py
tests/unit/test_b1_contract.py
tests/unit/test_b1_description.py
tests/integration/test_b1_description_cli.py
docs/experiments/b1-dual-ma-first-real-description-2026-09-16.md
docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/**
```

仅允许修改一个旧实现：`src/lei_signal/research/factor_unit/state_description.py`，用于提取复用函数与调用转接，不改变旧校验和旧结果。这是相对上一轮“该文件只读”的**显式小范围调整**，只在本任务执行时生效。旧脚本引用的旧哈希会失配，属于诚实版本变化；不更新任何旧协议伪装兼容。开工原字节归档，旧冻结代码仍可独立恢复。

禁止修改close_state、study_contract、旧CLI、factor_lab、生产函数/规则、旧tests、任何已有raw、定义登记表、OKR、registry、INDEX。新报告由主控登记。需要其他旧文件改动时暂停对应项，不自行扩面。

## 3. 实验合同：出数前固定，不能改成最好看的版本

### 3.1 对象、输入、时间

- 仅510300，原件sh510300在边界显式映射为510300，不能调用会混淆交易所的通用猜测映射。
- 输入2019-09-02至2026-02-03，按已核日历逐日覆盖。1558行只是交叉证据，日历集合才决定完整性。
- 原始字符串字段保持；计算close转浮点，但无效字符串/非有限/非正必须拒绝，不用errors=coerce把乱码变缺失。整行日期缺失、重复、乱序、错误列头皆明确拒绝真实正式输入。
- 复用compute_close_state，从2019-09-02开始初始化：20个交易日准备，EMA种子前20均值，alpha=2/21；SMA含当日；完整共同确认调用生产函数，**不用等价简式替代**；t=20（第21行）起可能有效。缺失准备状态不变成false。
- 评价日期2019-10-08至2025-12-31（含）。真实准备行与目标尾部行仍保存，但不进入评价集合。
- `label_maturity_cutoff=2026-02-03T15:00:00+08:00`；CN逐日close_at=15:00 Asia/Shanghai。
- 来源retrieved_at逐原件继承，不伪造成新的请求时间。新增`analysis_executed_at`实际带时区时间；`historical_available_at=null`。成熟截止是标签窗口截断，不是2026年2月已拥有9月快照的证明。
- 数据身份real，结果身份post_hoc_historical_description，historical_reconstruction_only=true；精确复权锚点unknown；不得填PIT verified。

### 3.2 目标及比较

```text
e = t之后第1个交易日收盘
x = t之后第22个交易日收盘
main = P_vendor(x)/P_vendor(e) - 1
aux = min(0, min(P_vendor(s)/P_vendor(e)-1)), s遍历[e,x]全部22个收盘格点
```

21个变动区间，不是22段；aux是相对起点最差收盘变化，不是最高点到最低点回撤。供应商调整价与含分红财富等价性未核，不加现金分红、不重复复权，不声称已获得真实成交利润。

主比较：评价窗内、状态已知、主目标合法且成熟的共同集合。`n_true+n_false=n_comparison`；状态真假未知合计等于窗内实际观察数；应有日程与缺整行另对账。aux有效数量独立；主目标缺失/状态未知/未成熟等可重叠原因只作标记，另给互斥主要排除原因用于总数对账，不能把标记计数相加冒充剔除人数。

输出真假组：n、mean、median、strict_up_ratio（>0）、aux_n、aux_mean、aux_worst。空组n=0，其余null；零目标不算上涨/下跌，仍计分母。差值只称两组历史描述差；不叫贡献、alpha或有效性。

背景：目标合法且成熟，不要求状态已知；标注独立分母/n_unknown，不输出背景相减。本轮不为加入新公平对照扩建策略。

逐年按**状态观察年**分组，跨年目标归观察年，不当作自然年度收益；所有年份同报，不挑年。稀疏锚点2019-10-08，step=23，固定不顺延。保留整个日程中的固定格点；窗外独立标out_of_evaluation_window，窗内无行标missing_row。按有效真/假组各报总数、上涨/下跌/零变化数，三者相加等于该组n。无分母不报比例或“方向仍成立”。旧B0仍保留旧missing_row语义，由新B1输出层区分。

## Task 0：保存开工现场与合成旧行为

- [ ] 记录身份/所有范围内文件git状态；保存旧state_description原字节及其直接依赖、此任务书、卡、规范、固定输入manifest。新目录排他创建；若已存在停止，禁止删目录重开。
- [ ] 用固定合成案例保存旧输出基线，最多1批：50日平价；100日上涨/缩短评价窗；真假未知混合且缺辅助路径；全部窗外/空输入；跨年。不调用任何真实数据。
- [ ] 记录旧public函数/辅助函数的实际调用者，只读rg，不修改其调用者。记录旧拒绝data_mode=real的负例。
- [ ] 先写独立手算期望，不从旧输出反推算术；旧输出基线只用于行为一致性，与算术正确性是两种证据。

## Task 1：公共纯计算提取（不改变旧入口）

**Files:** description_core.py、旧state_description.py、新test_factor_unit_description_core.py。

接口约定：

```python
def build_observation_rows(values, schedule, *, eval_start, eval_end,
                           cutoff, e_offset, x_offset):
    """返回含symbol/session/state/main/aux/mature/reason的观察表及窗外计数。"""

def summarize_observation_rows(rows, values, schedule, *, eval_start,
                               eval_end, anchors, sparse_step):
    """返回每产品原B0统计结构；不授予用途，不内置real/synthetic身份。"""
```

- [ ] 将原describe_states中已经验证的逐行目标/合法集合/统计逻辑移动到两个纯函数；_stat、_state_value及段计数可随之提取，旧导入引用如有调用者保留兼容别名。不要重构不相关内容。
- [ ] 原_validate_contract的synthetic要求和参数校验保持；原describe_states先校验再调用core，并仍包装synthetic及旧no_claims。core没有输入许可概念，不能被描述成“通过core就合格”。
- [ ] 新core用于B1前要先经过B1严格输入检查；旧coerce等已知宽松行为不顺手改变，避免扩大旧行为修复。
- [ ] 提取前后Task0合成基线逐字段深度相等（计数、原因、日期、布尔、null严格相等；浮点容差1e-12），旧real拒绝保持。任何非预期差异先停，不以总均值接近过关。

测试例核心期望：

```python
# 50个合成日，I=100..149、state全真、完整评价、2030截止
assert comparison_n == 28
assert sparse_valid_positions == [0, 23]
assert abs(main_at_0 - (122/101-1)) <= 1e-12
assert abs(main_at_23 - (145/124-1)) <= 1e-12
# 同一资料2019截止：comparison_n==0，所有稀疏目标不得展示
```

## Task 2：B1固定合同与数据资格（先验证，后计算）

**Files:** b1_contract.py、test_b1_contract.py。

接口：`validate_b1_protocol(protocol_path, repo_root) -> dict`；`load_verified_input(package_path, contract) -> (prices, schedule, audit)`。CLI只接受正式版本文件，不接受current指针/草案。输入/身份错退出3；资料不完整退出2；都不能留下成功manifest或真实状态目标文件。

- [ ] 冻结目标常量与本任务的固定输入SHA于b1_contract。运行协议必须逐值相符，不允许自填approval=true、换symbol、窗口、对象、label、mode、anchor、费用或通过删校验清单绕过。必需代码键集合由实现常量规定，不由协议任意裁剪。
- [ ] 必需键至少：core、旧state_description、b1_contract、b1_description、CLI、close_state、trading_calendar、indicators、dual_ma、lei_color、rules_config、domain/types.py、domain/canonical.py、events/log.py及实际加载configs/rules.v2.yaml（domain与events相对src/lei_signal）；检查实际调用依赖，有额外本地计算依赖加入集合并记录，不只核一个包装文件。模块导入不得计算/写盘；验证完毕才加载真实计算路径。规则加载器缓存不得掩盖配置漂移。
- [ ] 检查固定manifest哈希→全部包内键/哈希→CSV和日历内容→原件身份及声明；manifest complete只是声明，不能替代核验。使用包内calendar，不偷偷换外部最新日历。
- [ ] 七份原件的retrieved_at解析成真实带时区时间；保留逐件来源，不用说明性字符串充当机器时间字段。精确请求起止仍未知。
- [ ] 合成反例必须覆盖：删代码键、改CLI哈希、换对象/参数/窗口、改价格且重写自制manifest、日历漏日、重复CSV、NaN/乱码/0价格、空包、草案运行、已有输出目录、伪造synthetic。合法合成输入用于单元测试内部，不提供可向正式CLI注入任意真实文件的“跳过资格”选项。

## Task 3：真实历史描述与输出（仅新入口）

**Files:** b1_description.py、test_b1_description.py、CLI、integration test。

接口：`describe_b1(prices, schedule, contract) -> dict`，只由已通过资格的CLI调用；内部复用close_state与core，不调用describe_states时冒用synthetic。返回states、observations、summary、quality四部分；计算过程与写盘分离。

- [ ] close_state只用close，目标用同一vendor价格；真实日历不得退化为工作日。标签用交易日位置取端点，不用行缺失后的压缩序号。
- [ ] F1/F2/F3按§3输出；保存每个观察的e/x日期、成熟时刻、分组资格与排除原因，足以从逐行表重新核汇总。准备期20行单列，不伪称评价窗内未知20行。
- [ ] 真实状态/目标输出附旁置metadata：候选ID、版本、输入SHA、单位、time semantics。结果硬标post_hoc_historical_description；manifest实写data_mode=real，无predictive资格。
- [ ] 使用标准JSON（allow_nan=False）；允许统计缺失为null并有原因；无穷结果不静默当0。CSV布尔序列化有明确true/false/空，不能误读字符串false为真。
- [ ] 图表非必需，只需可读Markdown及小表。报告按六步结构：问题→资料限制→数量→两组差别→逐年/稀疏/分布特征→不能证明什么。均值和中位数不一致如实报，不编“赢家”解释，不强塞预设结论。

## Task 4：合成算术、边界与兼容验收

- [ ] 50日常数close=100：状态前20未知、后30假，完整未来配对中假组8个，目标/辅助均0；真组n0统计null。独立期望不import生产函数。
- [ ] 50日close前20为100、后为101..130：未知20、后30真、成熟真组8；第一完整观察e=102/x=123，main=123/102-1；aux=0。
- [ ] 分红不另消费：本轮没有action输入；价格与每份分红联动测试不适用，明确不声称验证了财富构造。
- [ ] 合成价格同比缩放×10不改状态和无量纲目标；普通点与严格相等边界分别检查，浮点临界差异须披露不能改规则。追加未来合法合成资料后，既有状态及已经完整的目标不变；未成熟目标后来变完整不算泄漏。
- [ ] 缺辅助路径但e/x齐全：main计数保留、aux缺失；未知不进真假组；跨年按t.year；窗外不计缺数据；早截止所有目标剔除；截止恰好15:00成熟、14:59:59不成熟；无时区拒绝。稀疏组上涨/下跌/零变化合计等于组n。
- [ ] CLI故障注入：写盘中断不得有completed=true；已有路径不得覆盖；删必需键在任何真实计算前拒绝。只用合成临时包，不篡改真实旧包做反例。

命令（实际输出计数如实，不拿某个通过数当目标）：

```bash
python3 -m pytest tests/unit/test_factor_unit_description_core.py tests/unit/test_b1_contract.py tests/unit/test_b1_description.py tests/integration/test_b1_description_cli.py -q
python3 -m pytest tests/unit/test_factor_unit_close_state.py tests/unit/test_factor_unit_study_contract.py tests/unit/test_factor_unit_state_description.py tests/unit/test_factor_unit_b0_controller_cases.py tests/unit/test_factor_unit_four_fixes.py tests/integration/test_factor_unit_readiness_cli.py tests/unit/test_experiment_reports.py -q
python3 -m ruff check src/lei_signal/research/factor_unit/description_core.py src/lei_signal/research/factor_unit/state_description.py src/lei_signal/research/factor_unit/b1_contract.py src/lei_signal/research/factor_unit/b1_description.py scripts/run_b1_dual_ma_description.py tests/unit/test_factor_unit_description_core.py tests/unit/test_b1_contract.py tests/unit/test_b1_description.py tests/integration/test_b1_description_cli.py
```

## Task 5：冻结并进行一次正式运行

- [ ] 所有代码/测试定稿并通过后，保存新协议 `protocol-v1.0.0.json`（排他）、全部必需代码原字节（保留相对目录）及环境版本，包括Python/pandas/numpy/PyYAML/pytest/ruff。不是只保存哈希。freeze清单同时绑定卡/规范/输入manifest及本任务书。
- [ ] 新协议有明确family=B1-dual-ma-unit、use=post_hoc_historical_description、固定§3参数、代码/数据身份、授权来源、尝试史、运行预算、容差、输出字段。没有代码哈希就不得正式计算；计划内JSON字段是要求，不声称接口已经实现。
- [ ] 输出目录预先不存在；保存协议原字节、输入包原字节副本或完整只读拷贝、source-snapshot、environment、states.csv、observations.csv、summary.json、quality.json、report.md、manifest.json。manifest最后写，明确complete/exit_code/qualification与no_claims，按实际文件集合双向核哈希。

正式命令（新增CLI应实现此接口）：

```bash
python3 scripts/run_b1_dual_ma_description.py --protocol docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/protocol-v1.0.0.json --out docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/run-01
```

预算：**真实正式计算1次；只允许可定位工程错误后新编号修正再1次**。若第一次正常但结果不好，不得重跑。新代码修改须新协议版本，旧版原字节保留；不得改旧协议后沿用版本。不允许额外/tmp真实调试、预览真实均值或局部真实统计试跑；所有真实状态/目标计算包括临时完整重放均计数。真实原件只读身份检查不计计算运行。

测试预算：新单测按需但失败原因必须记录；上述旧相关回归最多2次；完整合成CLI调试最多3批（批内正/负例列表事先写明），pytest内CLI调用单列次数；旧行为基线1批。真实输出恢复核验1次只核字节与从已有observations重汇总，不重新计算状态/目标。联网/安装/账户运行始终0。

正式前任何必需项没通过，即不运行、交回原因。一个组没有观察或真假差别不清楚是合法研究结果，不作为重试理由。

## Task 6：交付、独立复算证据与停止

- [ ] 从已输出observations按固定规则独立重汇总n/均值/中位数/比例/aux，不调用core汇总函数；误差≤1e-12，计数/键/null严格一致。不重算真实因子，不增加真实运行。
- [ ] 输入原包14项哈希及其他保护文件复算；唯一旧实现变化必须是获准提取的state_description，列出旧新SHA和旧协议不再匹配的影响。freeze包原字节可恢复；不要把HEAD代表源码。
- [ ] 总报告路径按§2，必须含大白话结论与决策卡、代码变更表、实际命令日志/次数、失败史、已运行与未运行、样本覆盖/两组数值/年份与稀疏结果、全部限制。不输出策略年化、显著性、IC、alpha、买卖建议或“因子有效”。
- [ ] 交付使用者先读页：一句话解释具体比较、主要数字及最重要限制；如果没有清楚差异就直说。任何真实结果都不自动触发规则修改或继续扫参数。
- [ ] 给主控回交按“执行者声明 / 证据路径 / 待主控裁决”列明；用户仅转交不代表认可，不写“用户特别指出”之类错置来源句。
- [ ] registry/INDEX登记建议附报告，执行者不写共享导航。完成即停；后续跨市场、宽度、情绪、显著性和策略归因不在此轮。

## 主控计划自检与补件结论

2026-09-16已读closeout-notes及draft-2；与draft-1比对对象、公式、offsets、评价窗及稀疏参数未变；run-02固定14文件复算一致，输入包说明收尾接受。此前两条线不再阻断计划编制。

本计划明确解决了旧冻结行为与复用的冲突：只允许state_description的提取转接，既不伪造synthetic，也不另抄整套统计后称唯一实现。数据不重抓；知识时点与成熟截止分开；真实运行前冻结；两种对账分母明确；遇差异停；用户本次仅要求计划，尚未自动执行任务。
