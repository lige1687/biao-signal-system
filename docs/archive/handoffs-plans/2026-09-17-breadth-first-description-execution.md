# B200 × 510300 首轮历史描述 Implementation Plan

> For agentic workers: 使用 executing-plans 按本任务逐项执行；模型 GLM-5.3-Flash。用户已指定 ZCode，不另派子任务，不提交 git。项目文件归置与冻结限制优先于技能默认提交约定。

**Goal:** 用一份已指定的历史宽度序列，描述其高低与510300随后21个交易日区间价格变化的关系，交付可复算结果与诚实限制。

**Architecture:** 两个新增研究模块负责窄用途合同与配对/描述；复用已有日历与平均名次相关数学核；一次性CLI、独立核验脚本与冻结产物放本实验 raw。旧实现和旧消费者保持不动。

**Tech Stack:** Python、现有 pandas/numpy/pytest/ruff；不安装依赖、不联网。规范版本1.0.0，2026-09-17。

## Global Constraints / 用户授权

用户确认设计后明确“对你去delegate一下任务好吧, 给zcode”。据此允许本任务实施、合成检验、下述一次真实历史描述与限定独立复核；不授权预测宣称、交易、生产、扩池或参数搜索。

目录 `/Users/yongbiaoli/Desktop/lei-signal-lab`，分支 `codex/factor-unit-research-20260915`，HEAD `29b150f58b3f6d8c6e558a748c12dac3384af173`。共享工作区有他人改动，全部保留。身份变化先回报，不切分支、不暂存/提交/reset。

先读AGENTS/CLAUDE、交易规格与规则账本、板块层方案，以及：

| 规范 | 版本 | SHA256 |
|---|---|---|
| docs/research/experiment-backtest-principles.md |1.1|ac5a676c0635441b66f656c8e1249b69bade36365cc9065ed6341a610b6a53c6|
| docs/research/ai-execution-contract.md |1.0.1|deab6c1ca20505f92d06516ffff943b8501fff2e01f8c6b3928c6626072af962|
| docs/research/definition-standard.md |1.1.0|3406feaea2bbb8d23a91ddc8fa0c85e62ff86437bdf443d459f2c97b0e99cd5c|
| docs/research/experiment-report-template.md |1.1.0|cae2853f81841de6f424c6bda10e6708dd35574ebb8a325088fe507c5755d54e|
| docs/research/definitions.v1.json |容器1.2.0|c008efb991c40f06bb7fe0236b0892a6902c68a83cb4657ae5c2651e9d270e05|

设计来源：同目录 `2026-09-17-breadth-first-description-design.md`。资料裁决：`docs/experiments/factor-breadth-readiness-controller-review-2026-09-17.md` §9。读B1收尾及使用手册的目标端点，不重读整条历史研究。

### 研究身份与用途裁定（主控固定，执行者不能改）

研究家族 `breadth-unit-csi300-b200-21-v1`；用途 `restricted_post_hoc_description`；只研究一个标的 `510300`，一个宽度 `B200`，一个目标。

对象参照 `breadth.csi300.b200.legacy_percent@1.0.0`，单位转换后与 `breadth.csi300.b200.common@1.0.0` 对照。用现有 `definitions.resolve` 解析完整卡并保存只读快照；**不调用 calculate 重建宽度，不称实际输入完全满足卡的价格/历史可知要求**。

本次主控允许消费这份指定冻结序列作受限事后描述，数据质量必须仍写 `restricted`，available_at=null、historical_availability_verified=false、source_price_basis=unverified_per_column。不存在“数据已合格”的自动升级。研究结论只描述本快照，不外推为真实当时信号、选股IC、因果贡献、收益因子、含分红财富、交易利润或显著性。

不按结果调整定义或扩测B50、宽度变化、分档、情绪、双均线条件、第二标的。相关系数正负均可交付，没有效果阈值，不把负相关自动判为无价值，也不把零相关判为没有非线性关系。

## 1. 固定输入（简称均在本节定义）

`B1` = `docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/run-02/`

`BR` = `docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09/prepared/`

| 输入 | SHA256 | 角色 |
|---|---|---|
| BR/breadth_csi300.parquet |63fa7f0ef837c161194fb8f1f17140069074812085c8b449b93aa4d5f2998a58|只消费b200及质量列|
| B1/observations.csv |1dfe4c206212c31809f53f4b66bb40b3dd4ec193b03daf37c1540f8307eb9d5d|复用既有main/e_date/x_date，忽略state及其筛选字段|
| B1/input-package/prices.csv |bc8582af3ac7b4c2f00a5b51d81754606179347cc3811c911d7579242cb56703|独立核对既有目标的指定供应商调整价快照|
| B1/input-package/calendar.json |aa43736b67bbcee04fc21eedf8d510b184b764adf138456c8bce93a3155eb6c1|日历逐日推导|

复用只读数学核 `momentum_prototype.rank_diagnostic`（当前文件SHA 5425e4f5494710041ae42816bf259ac7cdc1ed6aaef01986ac1d3d34d90e568f）；日历 `TradingCalendar`（文件SHA 4651fa7d0e1e20aeaf3b40d9446f3ea76ec0eac037bbe965c018c3e5ccb6389e）。导入前确认无顶层联网/写盘。无法复用须停相应实现，不修改旧接口绕过其合成模式限制。

### 唯一评价合同

- 观察轴：日历覆盖2019-10-08至2025-12-31的全部交易日；**先推导完整轴，再左连接**宽度和目标。范围是沿用B1以复用已核目标，不是由宽度效果挑选；不能把它当未知验证资料。
- 标签端点：同一日历轴t后的第1和第22交易日收盘，21段相邻价格区间。日历完整核验从2019-09-02至2026-02-03；需要的最后端点不得越出价格覆盖。
- main应等于 close(x)/close(e)-1。协议截止 `2026-09-17T00:00:00+08:00`，标签市场成熟需x日15:00+08≤截止，但不据此补造历史available_at。
- 输入身份/字段结构、重复键、非法日期/布尔字符串、价格非正/非有限、非交易日报价、有效b200越界[0,100]、coverage越界[0,1]、计数非整数或违反0≤eligible≤quoted≤pool_total均硬拒绝。每行valid须是真布尔；有效行须有pool_total>0、coverage与eligible/pool_total在1e-12内一致且≥0.9、b200有限。禁止凭非空字符串判断真。
- 质量不足或缺失按日期保留：无宽度行、valid=false/coverage不足、b200缺失、无目标行、标签未成熟、目标缺失分别有原因。所有原因列表可保留，但primary_exclusion按上述先宽度后目标顺序互斥；n_all=n_included+Σprimary_exclusion。无值不能填0，不前填、不顺延。
- 目标行存在时端点必须和日历推导完全相同；与冻结价格的比率不符超过1e-12绝对误差，视为一致性错误整体拒绝，不把该行悄悄删掉。宽度与目标过滤绝不依赖B1的state、flag_state_known、in_comparison、primary_exclusion等旧状态字段。

### 固定统计及其解释

主指标 `time_series_spearman`：在共同合法行上，两列各自按并列平均名次排名，再计算名次相关。复用rank_diagnostic时只把b200_fraction重命名为其内部momentum列，输出不叫动量或横截面IC。

全期和2019…2025逐年各计算一次（跨年标签按观察日所属年份），每年内部重新排名。全部年份保留；不足3对或任一列常数返回null+reason。min_pairs=3是沿用数学核的输出约定，**不是统计可信阈值**。不取年度相关的简单平均作第二主指标。

每表同时给出n_all/n_included/排除数、b200与目标的均值/中位数/最小/最大和目标上涨比例，仅帮助理解数据，不产生分档或策略收益。范围内n=0同样形成报告。所有JSON严格允许null不允许NaN/Infinity。

时间重叠：用合法配对行的(e,x]交易日相邻区间集合，报告全部区间引用数、唯一区间数、连续两条合法观察之间共享区间数直方图。保留原日历位置，不把删除缺失后的行号当交易日。例e=1,x=22与e=2,x=23共享20段而非21个价格点。不估有效样本量。

本轮**不计算p值、置信区间、重抽样、参数扫描或风险回归**。时间相关未处理成推断，报告明确“不证明不是巧合；不排除过拟合；不检验非单调关系”。

## 2. 可写文件和产物

仅新增（如存在先停）：

- `src/lei_signal/research/breadth_description.py`：配对、统计、重叠的纯函数；不自行读真实文件。
- `src/lei_signal/research/breadth_description_contract.py`：固定身份、模式、参数、输出与协议校验。
- `tests/unit/test_breadth_description.py`：纯函数/合同/CLI合成测试，全部tmp_path；不读真实输入。
- `docs/experiments/raw/breadth-b200-first-description-2026-09-17/`（下文RAW）：run_breadth.py、verify_result.py、合成夹具/独立期望、protocol-v1.0.0.json、freeze/v1.0.0/、日志、run-01、verification-01、registration-proposal.json。
- `docs/experiments/breadth-b200-first-description-2026-09-17.md`：按模板写报告与决策卡。

其余全部只读：不修改旧factor_lab/factor_unit/factor_evidence、生产、已有测试/研究结果/登记卡/任务书、registry/INDEX/OKR。共享登记由主控完成。

## 3. Task 0：身份冻结和接口核对

- [ ] 读规范，核HEAD和上述哈希。记录环境/模型与工作区状态；不因脏工作区而回滚。输出Task0检查，不计算任何相关系数。
- [ ] 保存本任务依赖的实际原字节与哈希（代码不只存git HEAD）、卡快照、规范及输入。输入放新包或声明带准确哈希的外部依赖；本例文件小，优先复制四份指定输入。只读输入复制不提升用途资格。
- [ ] 解析日历、列名与日期身份完成纯检查，记录复用方法。禁止把旧合成runner的synthetic标记伪造为真，不能绕过用途拒绝。

## 4. Task 1：合成小例先行与最小实现

接口固定为 `build_pairs(breadth, observations, prices, sessions, *, evaluation_start, evaluation_end, cutoff) -> DataFrame`，`summarize_pairs(pairs, years) -> dict`，`audit_overlap(pairs, sessions) -> dict`。日期统一ISO日字符串，不能混时区推移交易日。

核心统计薄适配代码语义：

```python
from lei_signal.research.momentum_prototype import rank_diagnostic

def rank_summary(clean):
    pair = clean[['b200_fraction', 'target']].rename(
        columns={'b200_fraction': 'momentum'})
    result = rank_diagnostic(pair)
    return {'n': result['n'], 'time_series_spearman': result['value'],
            'reason': result['reason'], 'axis': 'dates',
            'use': 'restricted_post_hoc_description'}
```

期望值独立固定，不调用被测函数生成：

```python
# x=[0.1,0.2,0.3], y=[0.01,0.02,0.03] => rho=1
# x同上, y=[0.03,0.02,0.01] => rho=-1
# x=[0.1,0.1,0.3], y=[0.01,0.02,0.03] => rho=sqrt(3)/2
# x常数 => null/constant_rank；只有2对=>null/fewer_than_three_pairs
# target: e收盘100,x收盘110 => 0.1；价格同乘10后仍0.1
# breadth:百分数25 => 比例0.25；0与100为合法边界。
```

- [ ] 写测试并留首次失败日志，再最小实现；同一合法夹具的B1 state改真假/缺失、in_comparison取反，配对和统计必须完全不变。
- [ ] 缺宽度/目标、valid=false、等于0.90、空年/空全期、常数、并列、跨年、日历缺日、缺目标端点、重复键、字符串false、越界/非有限、错误单位、价格比例不符各测试。
- [ ] 时间测试使用独立交易日序号手造e/x；重叠20/21段例，间隔足够不重叠例，缺行后不能压缩轴例。价格追加未来行不改变原目标；声明评价期之外的输入不进入统计。
- [ ] 协议/文件篡改、删必需代码键、改对象/标的/端点/日期窗/用途/数据模式/容差均在真实统计之前拒绝；合法合成链必须成功，防止一律拒绝假修复。

## 5. Task 2：协议与CLI冻结

只读CLI接口：`python3 RAW/run_breadth.py --protocol <version-file> --output <new-dir>`。模式分别 `synthetic_test` 与 `restricted_historical`，不能自填旗标将任意输入当真实指定输入。真实分支仅本节四输入身份白名单，不支持任意目录或多标的。

协议要求身份常量与实际算法核对，不仅验证自填SHA。schema/family/use、对象、symbol、date_window、target_offsets=[1,22]、min_pairs=3、statistics字段、calendar时区/15:00、quality标签、容差、no_claims必须等于本规格；冻结输入哈希/规范哈希/必需代码文件集合缺一拒绝。实际执行代码键含CLI自身、两新增模块及被调用旧模块（至少definitions、trading_calendar、momentum_prototype与其本地研究依赖），从实际import核对，不能用户删键免验。

版本原件排他创建，current指针不能充当协议；保存冻结源码原字节，输出包保存协议原字节与卡/规范引用。数据截止、observed_at、snapshot_fetched_at来源、available_at未知分列；未知不可用mtime补造。

输出包：pairs.csv（完整观察轴）、pairs.meta.json、summary.json、overlap.json、quality.json、report.md、protocol.source.json、environment.json、manifest.json。manifest最后写；只有全部落盘且严格JSON/哈希/键集检查完才package_completed=true；qualification固定restricted不变绿。输出哈希清单仅排除顶层manifest本身，包括嵌套manifest。拒绝覆盖目录；模拟写盘失败时不能留下成功manifest。

退出码：0=完整描述产物（含诚实null），2=资料结构/内容不满足本合同，不做统计；3=身份/协议错误；异常失败非0。拒绝路径保留原因和日志，不产相关结果。输出元数据列出实际消费legacy序列及单位转换，不声称调用过common.calculate。

## 6. Task 3：正式一次运行与独立复算

- [ ] 在真实结果出数前冻结最终代码、协议与任务清单，并保存每次命令日志。
- [ ] 一次正式调用写 `RAW/run-01/`。**只有1次，失败即停，不自动重试；出数前失败也算尝试。** 不因结果不好换期限或指标。
- [ ] 独立脚本不import新增统计/配对函数、不调用rank_diagnostic：只用冻结输入与run-01明细，按日历独立推导完整键集，核每行单位/端点/目标/排除，按数值排序区间平均名次和标准库算术独立复算所有全期/年度指标与重叠计数。浮点绝对误差≤1e-12，整数/键集/null理由严格一致；多/少/重复键都拒绝。一次核验+仅限核验脚本自身错误的1次纠错许可，不得重跑正式结果或改期望迎合它。
- [ ] 合成测试内证明独立核验能抓出删行、额外行、改值、改单位；不能只输出“检查通过”不记录检查对象。

## 7. Task 4：报告、证据记录与交付

按模板写一句话结论/五种状态/实际消费对象、时间限制/全期与全部年份/共同样本对账/重叠/尝试史/决策卡。三层归因均注明本轮不适用：未检验资金贡献、决策增量或收益模型解释。

用大白话解释相关：正值表示本快照中宽度较高日期的随后涨幅也倾向较高，负值方向相反；不等于涨幅增加了该百分比，不把rho写成收益。若年度方向不同如实说，不能只汇报最好年份。源数据已被旧研究观察，无全新未知验证资料；宽度成员变化不全是价格转强。

本任务规范建设产出为可追溯的协议/证据记录/使用说明，不改唯一登记表、总规范或新增一套总纲。列出新增消费者已支持的仅是受限历史描述；旧接口未迁移。留主控登记建议，不自宣布验收。

## 8. 次数预算与停止

所有次数含失败，逐条记账，不以“批次”藏重试。纯读取/哈希不限次数但不扩大数据范围。

- 合成定向pytest≤10次，含CLI合成子进程的实际数量另列（子进程均只能合成，无真实资料偷跑）。相关旧回归最多1次：`tests/unit/test_research_definitions.py` 与 `tests/unit/test_factor_evidence_stability.py`（不存在的测试路径先记录，不猜替代）；新增测试通过后再跑。
- ruff≤3次，hygiene≤2次；合成完整CLI最多3次（pytest内完整CLI也计入这3次，其他协议/纯函数测试不调用完整CLI）。
- 正式真实运行1次，无自行纠错复跑；独立核验2次（初次+检查脚本纠错），不能改正式产物。
- 不联网、不新依赖、不新数据，不重建宽度，不改参数/策略/生产/OKR，不提交。预算到达即停相应动作，未完成明确交回。goal回调最多3轮不自动增加上述真实运行额度。

### 完成标准

输入/代码/协议身份闭合；一份完整真实历史描述及独立对账，或者有证据的拒绝报告。工程失败不冒充研究成功；无统计结果则G3未完成。负面或零关系是合法研究产出，不允许为结果重跑。最终由主控独立复核，不自判因子有效。
