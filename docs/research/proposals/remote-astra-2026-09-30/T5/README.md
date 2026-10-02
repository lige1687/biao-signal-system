# T5：跨模块的交易时点反例检查（核验报告，draft / not approved）

## 一句话结论（大白话）

这次检查的问题是：系统在某一天给出的判断，会不会偷偷用到“当天还不知道”的信息，或者把“不知道”显示成“没事”。我先写下 12 个怀疑点和预计结果，再用人工编造的报价（不是任何真实行情）走真实程序入口去试。结果：**4 个怀疑点没发现问题**（摆动点要等右边三根走完才用、同一根K线既触及止损又突破时按“先失效”处理、转黑当天不升级、整条分析链在 75 个截断日上前后一致）；**发现 4 个此前没被记录的问题**，按影响从大到小是：①盘中还没收盘的K线会被当成收盘事实，系统一边在“可交易性第9条”写“信号不依赖未完成K线”，一边把盘中算出的“结构确认”永久写进研究记录库，收盘后条件不成立了也删不掉；②“放量突破颈线”这条记录，只要这个底部**后来**跌破止损位，就会从过去的历史里消失或改挂到另一个底部，进而让研究记录库报“同一记录前后不一致”而停止写入；③某天的最低价缺失时，系统不报错，直接当成“没碰到止损位”，结构继续算有效；成交量缺失被悄悄当 0；④行情源更正旧数据、补回缺的一天或回放旧日时，研究记录库里的结构状态被直接改写，没有留下“这是修订”的痕迹。另有 4 处显示或定义问题需要你拍板（列为待确认），3 处是已知问题本次只复核仍然存在。**这些都是“程序是否守住时点和数据规矩”的检查，不代表任何策略赚不赚钱；本任务没有改任何生产代码。**

几个词先说清楚：
- “C”：底部结构的失效价（止损位）。最低价碰到或跌破它，这个底部就永久作废。
- “颈线”：底部结构里两次低点之间的最高价；收盘站上颈线叫“结构确认”。
- “研究记录库”：程序每次分析后写入的本地 SQLite 数据库（事件、结构、生命周期表），用于事后审计和研究，当前看盘页面不从它读数据。
- “截断/全历史一致”：只给程序截至某天的数据跑一次，再给它全部数据跑一次，两次对“某天及以前”的输出必须一样；不一样就说明过去的结论被后来的信息改了。

## 基准与范围

- 代码基准：`639ad8dbd3d2aa72f824b626b86149c466c132a4`（分支 `codex/astra-core-review-20260930`），运行时 `src/ configs/ tests/` 无改动（`results.json.meta.git_status_src_configs_tests = clean`，并记录了 17 个相关源文件的 sha256）。任务书 README 提到的审阅基准 `9561df0…` 在本克隆中不存在（只有一个提交），以 639ad8d 为准。
- 规则账本实际加载 `configs/rules.v2.yaml`（`domain/rules_config.py` 第 12 行）。
- 策略原文副本 sha256 与确认指纹一致：体系 `df92d85b…`、实现 `85e0e327…`。
- 输入全部人工合成（`synth.py`，确定性生成），未联网、未读本机数据库或接口；SQLite 只写 `/tmp/t5-work/`，运行结束已删除。
- 排除（只引用不重复计数）：T2 已证实的模块 A 生命周期问题（`T2/production-fix-notes.md` P1–P8）；严格构造包含合并改写过去（第十批、09-27 主控复核 §4）；周线时点字段合同（T4）。

## 发现（按实际影响排序）

| # | 标签 | 一句话 | 影响哪个决定 | 假设 |
|---|---|---|---|---|
| F1 | 新发现（部分已知） | 盘中K线被当收盘事实；第9条写“不依赖未完成K线”；盘中事件永久入库 | 买点复核结论、看盘阶段；研究库真实性 | H05 |
| F2 | 新发现 | “放量突破”事件被后来的 C 失效删除或改挂；触发研究库身份冲突后持续停写 | 事件时间轴、按事件做的统计、研究库 | H01、H01b、H01d |
| F3 | 新发现 | 最低价缺失当成“没碰到 C”；成交量缺失当 0；都不报警 | 底部结构是否失效（止损）；量能事件 | H08 |
| F4 | 新发现（修订规则原文未定义，判待确认） | 修订旧K线、回补缺的一天、回放旧日都直接改写研究库结构状态，无修订记录 | 研究库审计与复现 | H09 |
| F5 | 待确认 | 从未确认的底部候选触及 C，也发“硬”档结构失效卖点，但没有对应事件 | 卖点提醒档位、可追溯性 | H02b/H02c |
| F6 | 待确认 | 一个底部失效当天，看盘综合阶段显示“失效”，即使另一个已确认底部仍在“共同确认” | 看盘卡阶段标签（一天） | H02 |
| F7 | 新发现（显示层，低） | 长周期数据不足时，长周期维度写“冲突”而非“数据不足” | 只影响解读；不开新仓的判断另由第1/8条阻断 | H12 |
| F8 | 新发现（定义一致性，非时点） | 阳线反转底部上的“放量突破”事件，当天收盘其实没过颈线 | 量能事件真实性 | H01c |
| K1 | 已知范围，归 T4 | 周五盘中，当周周线已被标“完成”，周收盘取盘中价 | 周线长周期标签、模块A周线环境 | H06 |
| K2 | 已知 | 注入的交易所日历没传到模块A周线环境 | 模块A周线门禁（偏晚）与状态机周线标签 | H07 |
| K3 | 已知/已记录，当前基准仍存在 | 严格构造的包含合并让后来K线改写过去确认 | 模块A的构造依据、回测严格顶部退出 | H10 |
| N1–N4 | 未发现问题 | 摆动点确认日、同日先后（其中一处原文待确认）、转黑/失效当日不升级、全链路截断一致 | — | H04、H03(a)(b)、H03(c)、H11 |

### F1　盘中没走完的K线被当成收盘事实（H05）

**最小输入**：`inputs/H05_intraday_1430.json` 与 `inputs/H05_final_close.json`（下标 0–62，`synth.base_rows()` 前 63 根）。D=2024-03-28：盘中版收盘 74.4（暂时站上颈线 73.5）、量 240 万；收盘版收盘 73.0（回到颈线下方）、量 350 万。两次都经 `analyze("510300", provider=MemoryProvider(...), sqlite_path=临时库, run_id="api-2024-03-28")`，与 `AnalysisService._run` 的调用方式相同。

**实际输出**（`results.json` H05）：
- 盘中版 D 日产生 `higher_low_bottom:confirmed`、`double_bottom:confirmed`、两条 `ema20_reclaim_rising_structure_confirmed`、`breakout_volume`；机会阶段 `early_strength`（早期转强）。收盘版只有两条 `early_watch`，机会阶段 `bottom_watch`。
- 可交易性第 9 条“依赖未来K线”：`blocked=false`，说明文字“系统严格前向，信号不依赖未完成K线”（`rules/tradability_gate.py:262-265` 写死）。
- `AnalysisResult` 与 `BuyPointReviewDTO` 都没有完成度字段（详情页 meta 有 `is_intraday_forming`，买点复核没有）。
- 收盘版运行后，研究库 `structure_instances` 两个结构被改回 `candidate`，但 `structure_lifecycle` 仍有 2024-03-28 `candidate→confirmed` 两行，`signal_events` 仍保留收盘版不存在的 4 类事件（两种确认、结构确认档、放量突破）。事件表只追加、不可撤回。
- 决定翻转搜索（人工合成上升序列 seed=101，尝试 35 天）：3 天出现“盘中版=等待条件成立（次级别确认·日线代理）/收盘版=当前无机会”。本次搜索范围内没有找到“可执行”级别的翻转，不能据此说一定会产生错误买点。

**按来源应有**：实现 §13 第 9 条“信号依赖尚未完成的未来K线，不开新仓”；`docs/ops/bar-completeness-contract.md` §3 禁止“静默当 final 用”；`events/log.py` 不变量 2 事件不可回写——反过来，尚未成立的事实不应写成永久事件。

**已知与新增的边界**：完成度守卫没接线是已知的（`bar-completeness-wiring-design-2026-09-20.md` 为 W2-S3 设计稿，未授权；其 §2 把详情页、买点复核定为“允许盘中但必须标注”）。**新增的是两点**：(a) 第 9 条把“没有判定能力”写成“已确认不依赖”；(b) 设计稿没有覆盖 `analyze()` 的研究库写入——`AnalysisService` 每次都传 `sqlite_path` 和 `run_id=api-当天`（`api/services.py:182-191`），盘中查看详情或 11:35/14:45 信号扫描都会把盘中事件写进研究库（此条为代码阅读，未对真实服务运行）。

**反例**：同一交易日，14:30 看到“结构确认、早期转强”，收盘变回“底部观察”；研究库里那次“确认”永久留存，而结构表又写着“候选”，两张表互相矛盾。

### F2　“放量突破”事件被后来的失效删掉或改挂（H01、H01b、H01d）

**最小输入**：`inputs/H01_base.json`（91 根）。两次探底，C=68.8，颈线 73.5；D=2024-03-28 收盘 74.4、量为均量 3.5 倍、收涨 → 两个底部同日确认并产生 `breakout_volume`；2024-04-23 最低价 68.6 触及 C。

**实际输出**：截到 2024-04-22 运行，D 日有 `breakout_volume`（挂在 double_bottom 上）；截到 2024-04-23 或全历史运行，D 日这条事件消失，其余事件不变。原因：`compose/pipeline.py:81` 按结构**最终**状态 `invalidated` 整体排除颈线，而不是看 D 日当时是否有效；`pipeline.py:85` 颈线表以确认日为键，同日确认的两个结构只留最后写入的一个（H01b：D 日两结构确认，表中只剩 double_bottom）。

H01d（事后追加的确认检查，来源是 H11 扫描结果）：人工合成序列 S3 在 2022-07-06 有 higher_low（颈线 156.29）与 double_bottom（颈线 154.32）同日确认。截到当天时事件挂在 double_bottom；double_bottom 在 2022-07-18 失效后，全历史运行里**同一事件编号**改挂 higher_low、颈线也变了。把两次运行先后写入同一临时研究库：第二次抛 `EventIdentityConflictError: …身份字段 structure_id 不一致`。此时 `signal_events` 已经写入了第二次运行的 337 条新事件，但生命周期快照和运行记录都没写（部分写入）。之后每次用全历史运行都会因为同一行再次冲突（代码推断：库里那行永远是旧的结构编号）。服务层会降级为“不入库重算”并在页面标注 `persist_warning`（既有测试 `tests/unit/test_api_endpoints.py` 用假冲突覆盖了这一降级）。H01d 里的服务层子检查因脚本缺陷无效，见“未解决”。

**按来源应有**：门禁 1（`tests/integration/test_acceptance_gates.py`）与实现 §3.2：追加未来行情不改变旧日期事件；`_build_structure_necklines` 自己的说明“确认之后、失效之前都作为可用颈线”；`sqlite_store.EventIdentityConflictError`：身份字段是不可变历史事实。

**影响**：当前 `src/` 里没有任何地方读取 `breakout_volume` 做判定（解释层读的 `breakout_volume_ready` 列不存在，恒为假）。影响的是事件时间轴、`/symbols/{symbol}/events`、研究记录库，以及任何按“放量突破”统计后续表现的研究——只会剩下后来没失败的那些（幸存者偏差）。研究库停写是更实际的后果：`services.py` 把这类冲突解释为“历史上用不同数据集/规则版本写库留下的污染”，本次证明**同一数据、同一规则正常往后推进也会产生**。

**既有测试为何没发现**：门禁 1 只比较 `(event_id, event_date, available_date)` 和阶段，不比较 `structure_id` 与证据，且只用一个随机序列、一个截断点。

### F3　缺价被当成“没碰到止损”（H08）

**最小输入**：`inputs/H08a_missing_low.json`：`base_rows()` 把下标 80（2024-04-23）的最低价置空（真实最低 68.6 会触及 C=68.8）。`inputs/H08b_missing_volume.json`：下标 70 成交量置空。都先过真实 `validate_bars`。

**实际输出**：
- (a) `validate_bars` 没有任何警告，最低价保持空值；该日比较 `空值 <= C` 结果为假，两个底部结构继续有效直到最后一天，当日风险状态 `black`。同一数据带真实最低价时，两结构当日失效、风险状态 `c_invalidated`、看盘阶段“失效”。
- (b) 成交量被填 0（`data/validation.py:111`），没有警告（负成交量反而有警告）；当日量比=0，其后 19 天量比被抬高 4.7%–5.3%（20 日均量里混进一个 0）。

**按来源应有**：`data/validation.py` 模块说明“数据错误必须显式报错或标记 DATA_UNAVAILABLE，禁止静默处理为‘无信号’；不填补缺失价格”。

**影响**：止损位 C 是否被触及——这是持仓“认赔”的硬条件（实现 §14）。真实行情源多久出现缺最低价的行，本次没有核对。与 T2 的 P6（缺价当成模块 A 趋势重置）不是同一处，不重复。

### F4　数据修订、回补、回放都直接改写研究库（H09）

**最小输入**：(a) 先跑 `base_rows()`（结构 2024-04-23 失效），再跑把该日最低价从 68.6 更正为 69.0 的版本（`inputs/H09a_revised_low.json`），同一临时库；(b) 首次缺 2024-03-25 一天（`inputs/H09b_gap_first_run.json`），再跑补齐版；(c) 先跑全历史，再 `analyze(as_of=2024-04-16)`（与 `api/signal_replay.py:43-46` 相同调用，带 `sqlite_path`）。

**实际输出**：
- (a) `structure_instances` 改回 `confirmed`、失效日清空；`structure_lifecycle` 仍有 `confirmed→invalidated` 行；`signal_events` 仍有两条“触及 C”事件。没有任何“因数据修订撤销”的记录。另：生命周期表每一行的 `reason` 都填成了 `bottom_C_touched`（`sqlite_store.py:1438` 用失效原因填所有转换），连 `None→candidate` 也是。
- (b) 缺一天时生成的两个结构（2024-03-28 候选、03-29 确认）在补齐后的分析里已不存在，但在库里永远停在 `confirmed`；同一个低点的摆动事件出现两条（可用日 03-28 与 03-27）。
- (c) 回放旧日把已失效结构改回 `confirmed`、失效日清空。

**按来源应有**：`bottom_structure.py`“失效结构永不复活”；任务约束“不得静默改变已失效结构的历史”。但原文和代码文档都没有规定“行情源事后更正”该怎么记，所以修订本身怎么处理判**待确认**；“改写时不留痕”与“回放写研究库”两点不需要用户选择也能修。

**影响**：当前 `src/` 没有读取这几张表的地方，交易决定不直接受影响；影响事后审计、复现和以后基于研究库的研究。

### F5　从未确认的候选失效也发“硬”卖点（H02b/H02c，待确认）

**最小输入**：`inputs/H02b_candidate_only.json`（两次探底但从未收盘突破颈线，2024-04-19 最低价回到 C 以下）。

**实际输出**：当日风险 `c_invalidated`、看盘阶段“失效”、风险提示“2个底部结构因触及C而永久失效”；卖点提取给出 `tier=hard`“结构失效”；但事件日志里**没有**对应的 `bottom_c_lifecycle` 事件（`apply_c_lifecycle` 只处理已确认结构，`bottom_structure.py:278`），提示无法追溯到事件。

**需要你选择**：未确认的候选从来不是买入依据（`ema_reclaim_tiers.py`：候选期只进观察档），它失效是否算“硬”卖点？原文“什么逻辑进就什么逻辑出”（体系 §2.7、实现 §2.3）没有直接回答。可追溯性缺口不需要选择。

### F6　另一结构失效当天，看盘阶段显示“失效”（H02，待确认）

**最小输入**：`inputs/H02_two_structures.json`。两个阳线反转底部，后一个在 2024-05-10 触及 C；前一个仍有效且观察档为 `joint_confirmed`。

**实际输出**：前一个底部的观察档、机会阶段在当天及之后都不受影响（与 `state/machine.py` 不变量 1/5 一致，核心语义无问题）；但当天兼容字段 `stage`=`invalidated`，看盘卡（`card_mapper.py:225-226`）显示“失效”，次日恢复“共同确认”。是否应在仍有已确认结构时把“某个结构失效”只放在风险栏，需要你决定。

### F7　长周期数据不足显示成“冲突”（H12）

**最小输入**：`inputs/H12_short_history.json`（100 根，EMA120 与周线都不可算）。

**实际输出**：日线、周线长周期都是 `unknown`；“长周期”维度=“冲突”，因素标题“长周期背景仍冲突”（细节里才写 unknown）。可交易性第 1、8 条另行阻断开新仓，所以交易判断不变，只是把“不知道”说成“不利”。来源：`rules/long_trend.py` 不足时保持 unknown；门禁 8 要求未知不得显示成具体状态。

### F8　阳线反转底部的“放量突破”其实没突破（H01c）

**最小输入**：`inputs/H01c_reversal.json`（长跌后阴线 + 放量 3 倍的阳线反包，下标 61）。

**实际输出**：2024-03-27 产生 `breakout_volume`，文案“收盘价突破结构颈线 53.8000”，实际收盘 53.60 < 53.80。反转底部的颈线就是这根K线的最高价，收盘不可能高于它；`rules/volume.py:141-148` 只看“当天是颈线表里的日期 + 收涨 + 量比”，没有比较收盘与颈线。规则账本 `volume_proxies.formula` 写的是“Close 突破某个明确结构颈线”。这是定义一致性问题，不是时点问题，附带列出（来源于构造 H01 时的调试观察，不计入预先登记的预测命中）。

### 已知问题复核

- **K1（H06）**：`inputs/H06_friday_intraday.json`，2024-02-09 周五盘中收 13.5（收盘版 12.5）。`aggregate_weekly` 把当周标 `is_complete=True`、可用日=周五、周收盘=13.5；`analyze_bars` 的周线趋势也用 13.5。原因：完成判定只看“截至日是否到了本周最后交易日”，不看那根日线是否已收盘；bar-completeness 设计稿 §5 第 6 条明确不改 `aggregate_weekly`。T4 的合成用例清单含“周内未完成周线”，交 T4 设计字段合同，本任务不计新发现。
- **K2（H07）**：人工设定 2024-02-08/09 休市，`analyze_bars(calendar=…)` 截至周三：主流程周线最新一周可用日 2024-02-07；模块 A 内部和回撤机会卡调用的 `weekly_env_series`（两次调用，都未传日历）最新一周仍是 2024-02-02。生产 `AnalysisService` 默认不注入日历，所以生产当前两处一致（都保守）。已记录于 T2 condition-map 第 7 行与第十批 a-contract。
- **K3（H10）**：严格顶部 2024-01-03 确认（低点 8.3）；追加一根内包K线后确认日变成 2024-01-04；追加一根创新高的外包K线后这次确认整个消失。当前基准仍存在；`tests/unit/test_strict_structure.py::test_prefix_invariance` 的第 4 根不构成包含，未覆盖。影响模块 A 的构造依据（`first_ma_pullback.py:194`）与回测严格顶部日期（`backtest/engine.py:181`）。

### 未发现问题

- **N1（H04 摆动点确认日）**：第二低点 2024-03-22，右侧三根收盘已在颈线上方。截到拐点后第 2 根看不到这个低点和结构；第 3 根（03-27）才出现候选；确认最早在次日 03-28，截断与全历史一致；B1 也只在高点确认日之后出现。
- **N2（H03(a)(b) 同日先后）**：(a) 候选次日同一根K线最低 68.5≤C 且收盘 74.4>颈线：判失效、永不确认，与模块说明“先触及 C 即永久失效”一致。(b) 严格顶部等待确认时出现一根同时新高并跌破触发低点的外包K线：它先被包含合并吞掉，构造不成立。原文没规定单根K线内的先后，也没说包含合并要不要连带更早的K线，**判待确认**，但两种读法在本例结果相同。(c) 三个合成序列上：转黑当天无档位事件、无观察实例；C 失效当天及之后无该结构的档位事件或观察。
- **N3（H03(c) 转黑/失效当日不升级）**：三个合成序列上，转黑当天无档位事件、无观察实例；C 失效当天及之后无该结构的档位事件或观察。
- **N4（H11 全链路截断一致性）**：三个人工合成序列（640/700/700 根，事件 1867/1900/2625 条，结构 85/101/132 个）各 25 个截断日，比较截断日及以前的全部事件（编号、日期、结构、生命周期编号、证据、截断内有效期）、逐日状态（机会、风险、颜色、主结构、有效结构集合、观察档、日/周长周期）、结构日期、当日 active 事件、解释层阶段与 B1。除 F2 的“放量突破”外**没有其他差异**。另有一处设计说明：`assessments_by_date` 的历史日评估不带筹码代理（`pipeline.py:445` `profile=None`），所以历史日“量价”维度与当天实时显示可能不同（11/7/8 次）；不是时点泄漏，`src/` 内也没有读取方。本扫描中模块 A 与模块 D 的已知问题没有出现，不代表已修复。

## 既有测试运行结果与覆盖范围

日志：`docs/experiments/raw/remote-astra-T5-2026-09-30/existing-tests.log`。

| 命令 | 结果 |
|---|---|
| 任务书指定：`tests/no_lookahead/`、`test_bar_completeness.py`、`test_lifecycle_order.py`、`test_event_lifecycle_v2.py`、`test_state_machine_v2.py`、`test_strict_structure.py` | **67/67 通过** |
| 补充：`test_acceptance_gates.py`、`test_round3_incremental_sqlite.py`、`test_ema_tier_binding.py`、`test_weekly_context.py`、`test_providers.py` | 61 通过、7 失败；7 项全是本虚拟环境缺可选依赖（`streamlit` 3 项、`yfinance` 1 项、`py_mini_racer` 3 项），不是业务断言失败，未安装依赖 |

覆盖了什么、没覆盖什么：
- `no_lookahead`：指标、颜色、模块 A 事件、摆动点、周线在“追加未来行情”下不变；周线只用完整日线数据，**没有盘中未完成日线**的用例（K1）。
- 门禁 1：一个随机序列、一个截断点，只比事件编号与日期和阶段，不比结构绑定与证据（F2 漏过的原因）。
- `test_bar_completeness`：只测纯函数；`test_signal_scan_calling_contract_gates_before_scan` 名字像是测扫描接线，实际只调用守卫函数本身，没有证明 `run_signal_scan` 调用了守卫。
- `test_lifecycle_order`：候选先触 C 后突破、顶部先新高后跌破，都是“不同天”的先后；同一根K线的情况由本次 H03(a) 补上。
- `test_round3_incremental_sqlite`：只测“往后追加数据”的增量写库，没有修订、回补、回放（F4）。
- 没有任何既有测试输入缺最低价/成交量的行情（F3）。

## 本次运行的命令

```bash
cd /Users/liyongbiao/Desktop/biao-queue-20260930
# 既有测试（日志见 existing-tests.log）
/tmp/bq-venv/bin/python -m pytest -q -p no:cacheprovider tests/no_lookahead/ tests/unit/test_bar_completeness.py \
  tests/unit/test_lifecycle_order.py tests/unit/test_event_lifecycle_v2.py tests/unit/test_state_machine_v2.py \
  tests/unit/test_strict_structure.py -rA
/tmp/bq-venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/test_acceptance_gates.py \
  tests/integration/test_round3_incremental_sqlite.py tests/integration/test_ema_tier_binding.py \
  tests/unit/test_weekly_context.py tests/unit/test_providers.py -rA
# 反例核验（约 94 秒；输出 results.json、inputs/、run.log）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /tmp/bq-venv/bin/python \
  docs/experiments/raw/remote-astra-T5-2026-09-30/check_counterexamples.py
```

## 方法纪律

- 假设先于运行登记：`hypotheses.json` 于 01:04 保存，sha256 `f9417e6a…2f66f2b0dbd` 当时即记录；之后只在 `addenda` 追加。02:10 追加时文件被整体重新排版，原字节已重建为 `hypotheses-as-registered.json`（sha256 一致，`hypotheses` 内容逐项相同）。
- 预测命中情况（与 `hypotheses-as-registered.json` 逐条对照）：H01、H05、H06、H07、H09、H10 与预测一致。H08(a) 的要点一致（不判触及 C、结构继续有效），但预测“风险正常”不准——当天颜色为黑，风险状态是 `black`；H08(b) 预测“可能出现回调缩量”未出现，实测是量比为 0 并抬高其后 19 天量比。H02、H04 与预测一致。H03(b) 结果一致（不确认）但机制预测错了：不是“先判新高作废”，而是那根外包K线与前一根被包含合并、把已建立的 lower high 一起吞掉。H12 只测了 100 根的情形，预测中“日线够长时第 8 条不报数据不足”未测。H11 预测“除已知来源与 H01 外无差异”与实测一致，但已知的模块 A/模块 D 差异在本次三个序列里没有出现。H01c、H02c、H09c 是运行前追加的子检查；H01d 是运行后追加的确认检查，不计入预先预测命中。
- 核验脚本机械修复 2 次（已用满）：①仓库根路径少算一级；②H09b 对照分析的符号写错导致结构编号对照失效。真实业务代码没有改动；隔离只用内存行情源替身，H07 在内存中临时包装 `aggregate_weekly` 记录参数、运行后恢复，H01d 在内存中临时替换 `services.default_provider`。

## 未解决

1. H01d 的服务层子检查无效（脚本在构造服务时就固定了前缀数据，第二、三次运行仍是旧数据，`analysis_runs.last_data_date` 可证）；修复次数已用满，未重跑。服务层降级行为改引既有测试与代码阅读；“冲突后每次运行都重复冲突”是代码推断，未实测。
2. F1 中“生产服务盘中会写研究库”来自代码阅读（`services.py:182-191`、`signal_scan` 排程见 `docs/ops/job-ledger-diagnosis-2026-09-19.md` 表中第 19 项），没有对真实服务或真实行情源运行。
3. F3 在真实行情源中的出现频率未核（不读真实数据）。
4. F2 与 F8 若修，会改变 `volume_proxies` 的事件集合，必须作为新规则版本登记，是否修、何时修由主负责人决定。
5. F4、F5、F6 的语义需用户选择；N2(b) 原文先后待确认。

## 产物

- 核验脚本与输入输出：`docs/experiments/raw/remote-astra-T5-2026-09-30/`（`check_counterexamples.py`、`synth.py`、`inputs/*.json`、`results.json`、`run.log`、`existing-tests.log`、`hypotheses.json`、`hypotheses-as-registered.json`）。
- 最小修复建议：[fix-suggestions.md](fix-suggestions.md)。
