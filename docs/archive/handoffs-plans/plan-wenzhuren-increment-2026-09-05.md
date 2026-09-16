# 任务书：文主任调研增量的落地计划（含 6 个执行 Prompt）

> 日期：2026-09-05 ｜ 来源：小红书博主「文主任」（金融分析师）全部 482 条笔记的调研
> （调研材料：`~/Desktop/文主任-干货截图/` 有总结网页+75 篇字幕全文；本任务书已把关键口径内联，执行时不依赖桌面文件）
> 性质：本文档是待做清单 + 分头执行的任务书。每个 Prompt 可单独交给一个执行 Agent 并行开工。

## 待做表

| # | 优先级 | 事项 | 落点 | 服务于策略哪一层 | 依赖 |
|---|--------|------|------|------------------|------|
| 1 | P0 | 信号含金量表：路牌+触发的历史胜率/赔率 vs 无条件基准 | `research/` 新增统计 + API + 研究页 | 全层（给规则配"含金量说明书"，不改判定） | 无 |
| 2 | P0 | 脆弱性指标：指数回撤 vs 个股中位数回撤差值 | `market_context/vulnerability.py` + global-strip | 市场环境层（叙事标注，不硬挡） | 无 |
| 3 | P0 | 偏离度分位提醒：过热/超跌路牌的量化定义 + 通知 | `market_context/` 新模块 + `rules.v1.yaml` + 通知基建 | 路牌层（新增一类可回测路牌） | 无 |
| 4 | P0 | 跌破 200 日均线分步检查清单（A 股自测版） | `rules/` + 回测 + 实验归档 | 道路层校准（预警分级，非反向信号） | 无 |
| 5 | P1 | 横截面动量标的池（12-1 排名，研究先行） | 实验回测 → 通过后再进选池 | 标的池选择层（不挡触发） | #1 的统计口径 |
| 6 | P1 | 因子实验台扩展：BAB/质量/低波/价值 + L1-L6 风险分级 | 扩展现有 FactorPanelPage（勿另起炉灶） | 市场环境层探索（带下架条件） | 无 |

明确不做：期权类一切内容（卖方策略/分布统计定行权价）；KDJ/斐波那契（博主自己都不用）；不新建独立项目——全部用现有基建。

---

## 公共约法（每个执行 Agent 开工前必读，随 Prompt 一起传递）

1. **先读后写**：动手前读 `AGENTS.md`、`docs/trading-spec-v1.md`（找本次改动对应的那一层）、`configs/rules.v1.yaml`。说不清服务于策略哪一层，就停下来问，不要硬做。
2. **判定权在 Python 规则层**：一切判定/统计在 `src/lei_signal/` 完成；`web/` 只做展示，前端不重新计算信号。**Streamlit 目录（`src/lei_signal/ui/`）冻结不许动**；图表数据扩展走 `src/lei_signal/api/` 纯函数。
3. **阈值不硬编码**：任何新阈值写进 `configs/rules.v1.yaml` 对应规则条目（含 `version`、`provenance: research_proxy`、`note_cn` 注明口径来源=文主任视频+日期，以及"初值待 A 股数据自测校准"），并同步提升 `ruleset_version`。博主给的数字（如 +15%、58%）一律当**假设初值**，不是结论。
4. **市场环境层红线**：新增观测（脆弱性/估值分位/风险分级）只做**叙事标注**，独立分组展示，**永不参与技术判定、不做硬过滤、不挡信号**——与 Round 4「独立分组研究、不硬挡信号」同原则。新增"路牌"必须遵守"只预警、不必然反向"。
5. **数据红线**（博主踩过的坑，照办）：统计/回测一律用本地原始数据自算；不引入前视（用当时点可得数据）；注意 `a_share_klines.parquet` 只有收盘价一列（无 OHLCV），涉及成交量/振幅的结论另寻数据源。
6. **实验归档规约**：凡是"试效果"性质的工作（#4 复测、#5、#6），结案必须：报告落 `docs/experiments/`（文件名带日期）+ 正文含 `## 一句话结论（大白话）` + 在 `docs/experiments/registry.json` 登记（`category` 必须用现有枚举，不许自造）。
7. **说人话**：面向用户的一切 UI 文案与报告结论，禁止裸用黑话（胜率/赔率/分位/因子等第一次出现要带一句大白话解释；Calmar/回撤比之类的必须翻译）。
8. **工作区有未提交改动**（fund nav series 与 factor panel 相关：`api/routes/portfolio.py`、`api/schemas.py`、`market_context/factor_panel.py`、`web/src/pages/FactorPanelPage.tsx`、`factorPanelLogic.ts`、`FundNavCompare.tsx`、`funddata.py`、`a_share_breadth.py` 等）。**严禁 revert/覆盖/重构这些文件**；如任务必须改到同一文件，只做追加式修改并在交付说明里注明；发现冲突立即停下询问。
9. 完成定义：单测通过（`tests/unit/` 下新增）、接口可 curl、页面可看、文案过了说人话检查。不满足不报完成。

---

## Prompt 1（P0）：信号含金量表——路牌与触发的历史胜率基准化

**背景**：博主方法论里最值钱的一条：任何信号先算历史账——该状态出现后固定持有期的收益分布、胜率、赔率，再与"无条件基准"（随便挑一天做的胜率）比较，高出基准的幅度才是信号真实含金量。我们系统已有模块粒度统计（`research/scenario_backtest_common.py::fixed_horizon_stats` 已算 win_rate/MFE/MAE；`research/module_backtest.py::MODULE_MAP` 已映射 A/B/C/D 四模块），**缺的是路牌粒度**（顶部构造确认、反向关键性波动、长趋势转灰、量能异常等预警类事件）的统计。

**任务**：
1. 新建 `src/lei_signal/research/signpost_stats.py`（或并入现有结构，你判断）：输入事件名列表（从 `storage/sqlite_store.py` 的 `signal_events` / `signal_alerts` 表取历史，或直接跑 `signal_replay` 重放生成），对每个事件统计：出现后 N 日（N=5/10/20/60）固定持有期的胜率、平均收益、盈亏比（平均赚/平均亏），并计算同期标的的**无条件基准**（全样本随便挑日的同口径统计），输出"超额胜率/超额收益"。统计口径必须复用 `fixed_horizon_stats`，不许另造。
2. 新增 API：GET `/api/research/signal-edge`（放 `routes/backtest.py` 或新 `routes/research.py`，注册进 `app.py`），返回每个信号/路牌的含金量行。DTO 加到 `schemas.py` 相应分节。
3. 前端：在 `ResearchPage.tsx`（或 BacktestPage 旁你判断哪个更顺）加"信号含金量"表：列=信号名/样本数/胜率/基准胜率/超额/盈亏比，行=各触发与路牌。表头文案说人话（例：胜率=历史上出现后 20 日内上涨的比例；基准=不看信号随便做的胜率）。
4. 单测：合成数据验证统计正确（含零样本、单样本边界）。

**红线**：这是研究/展示层，不改变任何判定逻辑；不许把统计结果写成新的过滤器。**验收**：curl 能出 A/B/C/D 四触发+至少 3 类路牌的含金量行；页面表格可排序；单测绿。

---

## Prompt 2（P0）：脆弱性指标——指数回撤 vs 个股中位数回撤差值

**背景**：博主微观监控三件套之一：指数回撤与"市场中位数个股回撤"的差值，历史上必然收敛——差值拉大意味着"指数的平静是假象"，要么指数补跌、要么个股补涨。对趋势系统是路牌可靠性的标注器。我们已有宽度（`market_context/a_share_breadth.py`）但无此指标。

**任务**：
1. 新建 `src/lei_signal/market_context/vulnerability.py`，**照 `a_share_breadth.py` 的三层模式**（当日计算 + parquet 缓存 + 历史序列/滚动分位，TTL 参照它）：
   - 输入：指数日线（`market_context/data_sources.py::LocalMarketBarsProvider` 的指数 parquet；指数清单先用上证/沪深300/中证500，可配）+ 全 A 收盘矩阵（`a_share_breadth.load_kline_cache()` 的 `a_share_klines.parquet`）。
   - 计算：窗口 W（60/120 日，参数进 rules.v1.yaml）内指数自高点回撤 vs 个股回撤的中位数（与均值都算，中位数为主），差值 spread；spread 的 3 年滚动分位。
   - 输出 dataclass + `data_status`（数据缺失时的降级标记，学 a_share_breadth）。
2. rules.v1.yaml 新增条目 `vulnerability_spread`（阈值如 spread>5pp 且分位>90% 记"脆弱性拉大"，标注为初值待校准）。
3. 接入 `routes/symbols.py::market_context_global_strip`（L1709 附近，追加字段）+ 新端点 GET `/api/market-context/vulnerability`（含历史序列）。
4. 前端：`MarketBreadthStrip.tsx`（或其旁）加一枚 chip：文案例"脆弱性：差值 6.2%，三年分位 93%（个股跌得比指数深，要么指数补跌要么个股补涨——路牌可靠性打折）"。chip 只展示，颜色最多做提示色，**不接任何判定**。
5. 单测：构造"指数横盘+个股大跌"的合成数据验证 spread 与分位计算。

**红线**：只进市场环境层叙事；不得进入 tradability_gate、不得挡信号。**验收**：curl 出当日值+历史序列；页面 chip 可见；单测绿；在 PR/交付说明里注明"是否有效待观察"。

---

## Prompt 3（P0）：偏离度分位提醒——把"过热/超跌"从定性变可回测的路牌

**背景**（已确认的系统空白）：现全系统无"价格偏离均线极端"类提醒（唯一乖离计算 `tradability_gate.py::bias_ema120` 是门禁不提醒）。博主口径：偏离度=(收盘-均线)/均线，看 20/60/200 日三档，换算 3 年/5 年历史分位并统计**连续极端天数**；参照初值：沪深300 偏离 200 日线 +15%、上证 +13% 为过热警戒（美股标普 +8~12%）；向下打到历史极低分位=机会区。且他反复强调：高偏离可磨 3-6 个月才回归，**只警醒、给不出买卖点**。

**任务**：
1. 新建 `src/lei_signal/market_context/price_deviation.py`（照 breadth 模式）：对一组标的（默认：上证、沪深300、创业板、恒生科技、纳指、标普——沿用系统已有的指数数据源；外加 watchlist 里的标的可选）计算 close/EMA20、EMA60、EMA200 偏离，各自 3 年/5 年滚动分位、当前连续极端天数（分位≥95 或 ≤5 视为极端）。
2. rules.v1.yaml 新增 `deviation_percentile_alert`：params 含分位极端线（0.95/0.05）、连续天数下限（如 3 天）、窗口（3y/5y）；note_cn 注明来源与"初值待校准；只预警不必然反向；高偏离可长期不回归"。
3. 提醒接入现有基建（三选一或组合，你按侵入度最小选）：a) `signal_alerts_store.upsert_signal_alerts` 新增事件类型；b) 走 `watch_subscriptions` 的 check-now；c) 每日 brief 汇总一行。提醒文案说人话且带方向感克制（"偏离 200 日线达 3 年分位 98%，连续 5 天——历史上此状态常伴随阶段性过热，仅预警"）。
4. 前端：global-strip 或 watchlist 相关页加展示（偏离分位 chip + 连续天数）；`/api/market-context/price-deviation` 端点。
5. 单测：合成趋势序列验证分位与连续天数。

**红线**：新事件是**路牌**（只预警）；不得参与任何模块触发、不得作为反向信号。**验收**：当前真实数据下能对各指数出分位；人为构造极端样本能触发提醒落库；单测绿。

---

## Prompt 4（P0）：跌破 200 日均线分步检查清单——A 股自测版

**背景**：博主对标普 1928 年以来 295 次跌破 200 日线的统计：58% 五天内收回、仅 5.8% 成熊；检查清单=前 3 天观望 → 第 5 天查三项（5 日累计跌>3% / 低于均线>2% 且均线斜率向下 / 均线死叉）任一命中则熊市概率升至 30%+ → 10 天不回=明确跑路 → 20 天不回=系统性风险；**急速跌破最安全、缓慢阴跌筑底最危险**。这是美股数字，**A 股是否成立必须自测**。

**任务**：
1. 先做研究：用上证/沪深300/创业板/深成指尽量长的历史日线（本地 fixtures + 可用的 provider），复测：跌破 200 日线后 5/10/20 天收回率、最终演变为深度回撤（如 20 日内再跌>10%）的比例；按跌破形态分"急速（5 日内跌破幅度>8%）/缓慢（>15 日阴跌跌破）"两组对比。产出统计表。
2. 根据自测结果（不是照抄博主数字）在 rules.v1.yaml 落 `ma200_break_checklist`（分档事件：ma200_break_d3_watch / d5_check / d10_warn / d20_risk，params 含各档判定式），挂到道路层预警流（trend_stage 相邻的新检测器文件，不动现有状态机语义，只新增事件）。
3. 事件可出提醒（复用 Prompt 3 的接入方式；若 Prompt 3 未完成则先落库不通知）。
4. **实验归档**：把 A 股复测写成 `docs/experiments/ma200-breakdown-checklist-astock-YYYY-MM-DD.md`（含 `## 一句话结论（大白话）`），登记 registry.json（category 建议"宽度择时"或"方法论与验证"，verdict 按实测结果如实填）。
5. 单测。

**红线**：清单是**道路层分级预警**，"跌破"绝不等于翻空信号；不得改动现有 lei_color/趋势状态机的判定。**验收**：实验报告+登记完成；新事件在历史重放中能触发；单测绿。

---

## Prompt 5（P1）：横截面动量标的池——研究先行，通过再落地

**背景**：我们的动量是"时序"（每个标的跟自己比，趋势在不在）；博主做"横截面"（全市场排名次：过去 12 个月涨幅剔除最近 1 个月=12-1 动量，取前 20-30%）。互补点在**选池**：只在动量排名靠前的池子里等 A/B/C/D 触发，可能提高触发质量。这是假设，必须先证。

**任务**（分两段，第一段不通过就不做第二段）：
1. **研究段**：用 `a_share_klines.parquet`（注意只有收盘价）计算每月末的 12-1 动量排名（剔除上市<1 年、ST 可按现有 universe 规则；`market_context/universe.py` 参考）。回测对比两组信号质量：动量前 20%/30% 池内触发的 A/B/C/D（复用 `research/module_backtest.py`）vs 全池触发，看胜率/盈亏比/收益差异与稳定性（分年度）。写成实验报告并归档登记（category 建议"模块与信号"或"组合与仓位"）。
2. **落地段（仅当研究段结论为正）**：在 `signal_scan.py`/opportunities 流程加"动量池"排序维度（**软排序展示，不硬过滤**——池外标的信息保留但标注"池外"），前端 opportunities 页加一列；rules.v1.yaml 落 `momentum_pool` 条目（窗口、比例、刷新频率）。
3. 单测 + 说人话文案。

**红线**：任何情况下不做"池外直接不显示"的硬过滤；研究结果为负就如实归档证伪并停在研究段。**验收**：实验报告+登记；（若落地）opportunities 页可见动量池标注。

---

## Prompt 6（P1）：因子实验台扩展——BAB/质量/低波/价值组合 + L1-L6 风险分级 + 估值分位

**背景**：用户想"碰一碰"博主的另一套东西：BAB（低波动异象）、质量、低波、价值因子组合，以及他的 L1-L6 周度风险分级（宽度/波动/情绪等信号合成的难度分级）。**重要：系统已在建因子面板**（未提交的 `web/src/pages/FactorPanelPage.tsx` + `factorPanelLogic.ts` + `market_context/factor_panel.py` + `routes/factors.py` + `scripts/verify_factor_panel_value.py`），本任务在该基础上**扩展**，严禁另起炉灶或覆盖现有工作。

**任务**：
1. 先通读现有 factor_panel 实现（读了才能动手），弄清已有哪些因子/口径，写三行现状小结放进交付说明。
2. 扩展因子覆盖（按现有模式加）：价值（PE/PB 等权复合——注意当前价格矩阵无估值数据，需评估数据源可得性；拿不到就先用价格可算的代理并明确标注"代理口径"）、12-1 动量、低波（60 日波动率排序）、质量（如无可得财务数据则缓做并在页面标"数据受限"）。每个因子在 A 股全市场（`a_share_klines.parquet`）做 long-only 前 30% 组合的长期净值与分年度表现。
3. L1-L6 风险分级：用**已有**市场环境模块（`market_context/classifier.py` 热度、宽度、`vol_regime.py`、情绪）设计一个评分卡映射到 6 档（规则进 rules.v1.yaml，provenance=research_proxy，注明灵感来源与"A 股参数自定"）；离线回放历史给每周评级序列，验证"高难度档之后的市场波动是否显著更大"。
4. 估值分位叙事 chips：主要指数 PE-TTM 的 3/10 年分位（数据源评估同上；等权与市值加权两个口径都展示——博主教训：两者可差 35 分位）。文案必须含"估值分位=当前贵贱程度在历史中的位置，只做背景标注，不构成买卖依据"。
5. 页面顶部固定"实验"标识 + 下架条件写在页脚（例：连续 8 周无有效结论即下架本页对应模块）。
6. 结案走实验归档规约（报告+registry，category 建议"组合与仓位"或"方法论与验证"，verdict 如实）。

**红线**：实验台一切输出不得流入主判定链/过滤链；不改 FactorPanelPage 之外的现有页面结构。**验收**：页面可见新因子+分级+估值 chips；历史回放数据可导出（API）；实验报告+登记完成。

---

## 总执行 Prompt（整包交给一个执行 Agent 用，直接复制）

```
你在 /Users/yongbiaoli/lei-signal-sync 仓库工作。本任务是按任务书落地一批外部调研产生的增量功能。

【第一步：先读，读完再动手】
1. AGENTS.md（项目级强制约束）
2. docs/trading-spec-v1.md（交易系统规格——每个改动必须能说清服务于哪一层，说不清就停下来问）
3. configs/rules.v1.yaml（规则账本——一切新阈值只进这里，不许硬编码）
4. docs/plan-wenzhuren-increment-2026-09-05.md（本任务书，含"公共约法"九条与 #1-#6 六个任务的详细要求——你的全部工作就是执行它）

【工作范围与顺序】
Phase A（先做，全部完成）：
  #1 信号含金量表（research/signpost_stats + /api/research/signal-edge + 研究页表格）
  #2 脆弱性指标（market_context/vulnerability.py + global-strip 接入 + chip）
  #3 偏离度分位提醒（market_context/price_deviation.py + rules.v1.yaml + 提醒落库 + chip）
  #4 200 日线跌破分步清单（先 A 股自测复刻统计 → 成立才落规则 → 实验归档）
Phase B（Phase A 验收通过后）：
  #5 横截面动量标的池（研究先行，结论为负就地证伪归档、不做落地段）
  #6 因子实验台扩展（扩在现有 FactorPanelPage/factor_panel.py 上，严禁另起炉灶）
每完成一个任务号：跑通它的单测 + curl 验证 + 简短交付说明（改了哪些文件、口径、遗留项），再进下一个。

【不可逾越的红线】（任务书"公共约法"的压缩版，全文以任务书为准）
- 判定权在 Python 规则层；web/ 只展示不算信号；src/lei_signal/ui/（Streamlit）冻结不许动。
- 调研来源的数字（+15%、58%、-8%~-10% 等）一律是"假设初值"：进 rules.v1.yaml（provenance: research_proxy，note_cn 注明来源与待校准），不得直接当结论用。
- 市场环境类新增（脆弱性/估值/风险分级/动量池）只做叙事标注或软排序，永不参与技术判定、不做硬过滤、不挡信号；新增路牌只预警不必然反向。
- #4/#5/#6 必须走实验归档规约：报告落 docs/experiments/（带日期）+ 含 "## 一句话结论（大白话）" 小节 + registry.json 登记（category 用现有枚举，verdict 如实填）。
- 所有面向用户的 UI 文案与结论用大白话，术语第一次出现带一句解释。
- 工作区已有一批未提交改动（fund nav series 与 factor panel 相关：api/routes/portfolio.py、api/schemas.py、market_context/factor_panel.py、market_context/a_share_breadth.py、portfolio/funddata.py、web/src/pages/FactorPanelPage.tsx、web/src/pages/factorPanelLogic.ts、web/src/components/FundNavCompare.tsx、web/src/pages/FundamentalsPage.tsx、web/src/pages/PortfolioPage.tsx 等）：严禁 revert/覆盖/重构它们；必须改到同一文件时只做追加式修改并在交付说明里注明。
- 不自行 git commit / push，改动留在工作区由用户验收。
- 数据注意：~/.lei_signal_lab/cache/a_share_klines.parquet 只有收盘价一列（无 OHLCV）；统计不得引入前视。

【遇到以下情况立即停下来问，不要自行发挥】
- 某改动无法归入 trading-spec 的某一层；
- 需要覆盖或重构上述未提交文件；
- 所需数据拿不到（如估值/财务数据无源），需要降级为代理口径时——可以先用代理口径但必须页面标注"代理口径"，并在交付说明里列出。

【最终交付】
全部完成后输出总结：逐任务列出（文件清单 / 新增规则条目与版本 / 单测结果 / curl 示例与返回样例 / 页面改动点 / 实验报告与 registry 登记路径 / 遗留项），最后一节"给用户的大白话总结"——说清楚每件事让用户多看到了什么、哪些结论待观察。单测不全绿、归档缺项，不许声称完成。
```

## 附：两条纪律备忘（不派工，记录在案）

- **低估不是止损豁免理由**：博主《别用"低估值"麻痹自己》对趋势系统的转译——"它已经很便宜"永远不能成为"跌不动了/不用止损了"的论据。落点：可考虑未来在 copilot 的 grounding/话术里加这条反提醒（单独小任务，暂不派）。
- **价值与动量负相关**：若未来基金台账做配置分层，价值型基金腿天然对冲动量腿崩溃月——记账即可，现在不动。
