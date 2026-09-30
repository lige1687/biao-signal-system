# Bar 完成度三态契约（W2-S1，2026-09-20）

> 说人话：这个契约回答一个问题——**「这根 K 线走完没有」**。以前只靠
> 「扫描作业都排在收盘后」这一条排程约定来保证不会用到没走完的 K 线；
> 盘中或 API 即时刷新一旦接入，就没有任何数据层的表达能拦住它。本契约
> 把「走完没有」变成数据本身可表达、可测试的属性。

## 1. 三态定义（G1）

每根 bar 的完成度 ∈ **{partial, final, unknown}**：

- **final（已走完）**：这根 bar 对应的交易时段已经收盘，OHLCV 不再变化。
- **partial（形成中）**：交易时段尚未结束，最新价/量还在变，这根 bar
  只是「到目前为止」的快照。
- **unknown（无法判定）**：手头信息（交易日历、时间源、数据日期）不足
  以证明走完。**保守缺省：unknown 在生产路径按 partial 同等对待**——
  宁可拒绝，不可猜测。

## 2. 分层关系：数据层三态 → 编排层 as_of → 调用契约

| 层 | 表达的东西 | 已有/新增 |
|---|---|---|
| 数据层 | 单根 bar 走完没有（三态，本契约） | 新增：`lei_signal.data.bar_completeness` |
| 编排层 | 本次扫描按什么时点语义跑（`as_of ∈ {intraday, close}`，`api/signal_scan.py`） | 已有 |
| 调用契约 | 某类调用允许什么完成度（见 §3） | 本契约成文 |

关系：**三态是 as_of 的前提而不是替代**。`as_of=close` 的扫描隐含
「参与判定的每根 bar 都必须是 final」；`as_of=intraday` 只说明扫描时点，
不自动豁免完成度——盘中跑 close 语义的信号同样必须先过完成度守卫。

## 3. 调用契约（G2）

- **`production_signal_requires_final = true`**：生产信号路径（收盘信号
  语义，含 daily_opportunity_scan / signal_alerts 落库链路）要求最后一根
  bar 为 final。遇 partial 或 unknown（保守缺省视同 partial）时的合法
  处置**二选一，语义必须明确**：
  1. **拒绝**（本阶段实现）：抛 `PartialBarError`，整次不产出信号；
  2. **显式标注不可用于 close 信号**：继续运行，但结果必须带显式
     partial/unknown 标注并被下游排除出 close 信号。

  两条处置之外的第三种行为——**静默当 final 用**——被本契约禁止。
- **`research_allow_partial = true`**：研究/回测路径显式允许 partial bar
  参与计算，但取数时必须拿到显式完成度标注（`research_view`），且结论
  中不得把含 partial bar 的结果表述为收盘语义。

## 4. A股 final 判定（G4，最小实现）

纯函数 `classify_a_share_bar(bar_date, observed_at, *, calendar, close_time)`：

- 输入：bar 日期、观测时刻（换算上海时间）、注入式交易日历
  （`data/calendar.py::TradingCalendar`，默认 `WeekdayCalendar`）、
  注入式收盘时刻（缺省 15:00，参数而非分支内启发式）；
- 判定：bar 日期非交易日或观测时刻早于 bar 当天 → **unknown**；
  交易日当天观测时刻 ≥ 收盘时刻 → **final**（时段收盘即走完，与之后
  节假日无关）；其余 → **partial**；
- 无 IO；**美股判定不做**（W2-S2 设计稿范畴，禁钟点启发式外推）。

## 5. 实现与测试落点

- 实现：`src/lei_signal/data/bar_completeness.py`（旁侧标注
  `BarCompletenessReport`，不改 DataFrame 结构）。
- 契约测试：`tests/unit/test_bar_completeness.py`（生产守卫拒绝
  partial/unknown、研究路径放行且带标注、A股判定单测）。
- golden 标注：`tests/golden/test_golden_completeness.py`（既有引擎样本
  补 `completeness=final` 标注断言，不改冻结哈希与既有断言）。
- 接线边界：本阶段不改 `run_signal_scan` 本体与判定引擎；守卫以上述
  调用契约形式供编排层接入，接线属后续阶段。

## 6. 版本

- v1.0（2026-09-20）：W2-S1 冻结——三态定义、分层关系、两条调用契约、
  A股判定纯函数与契约测试。
