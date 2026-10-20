# readiness-corrections：对主控 R1–R6 的逐条回应（factor-unit-close-adapter-2026-09-15）

原则：保留旧值/旧说法原文与出处，给出纠正依据；不写"修好后当初就正确"。
被纠正对象：A 阶段交付（`docs/experiments/factor-unit-readiness-2026-09-15.md`）及其 raw。
旧报告原字节不覆盖；本文件与本目录快照是纠正记录。

## R1 成交量

- **旧说法**（A 阶段 readiness-matrix.csv 四载体行、dual-ma-dossier §6、adapter-gap-map #4）：
  "缺volume列(factor_lab bars输入合同要求OHLCV)"列为 B 阶段阻断；adapter-gap-map 建议
  "补齐volume或把输入合同降级为close-only并显式排除量能特征——需主控裁定"。
- **主控已核事实**：全量 `compute_features` 要 OHLCV，不代表双均线状态需要成交量；
  状态实际只依赖 close、EMA20、SMA20、滞后 close 和颜色。
- **本轮处理**：新建 close-only 研究适配 `factor_unit.close_state.compute_close_state`，
  只复用 `seeded_ema(close,20)`、`classify_colors`、`dual_ma_bull_state` 三个既有函数，
  SMA 用 `rolling(20,min_periods=20).mean()`、lag 用 `shift(20)`；不调用依赖 OHLCV 的
  `compute_features`，不填假成交量，不改旧接口。**范围限定**：这只是本候选（状态只依赖收盘）
  的结论，不是"任何因子都不需要成交量"的许可；四载体文件缺 volume 的事实记录保留。

## R2 时间

- **旧说法**（A 阶段 dual-ma-study-proposal.json 阻断 B4、next-execution-spec §4）：
  "真实模式须按当地收盘逐行供给available_at"。
- **主控已核事实**：当地交易所收盘是观察时刻，不是供应商资料实际可得时刻；原提案 B4 不能执行。
- **本轮处理**：合同与 CLI 把 `session_close`、`fetched_at`、`available_at` 分列；
  available_at 未知时保持 null 且 `point_in_time_verified=false`。允许合格输入的
  事后历史描述；不授予"当时已知"资格，也不因描述资格假造当时毫秒时刻。

## R3 公式信息重叠

- **旧说法**（dual-ma-dossier §1 依赖展开）："因此该状态的有效增量条件实际是：
  **收盘 > SMA20** 且 **EMA20 向上**（加上绿色已含的收盘 > EMA20）"——把 EMA 上升
  列为绿色之外的有效增量。
- **主控已核事实**：同一完整窗口中 SMA 当日变化=(C_t−C_t−20)/20；种子之后 EMA 以
  0<α<1 递推时，EMA 上升与 C_t>EMA_t 同号。因此完整公式在这些条件下等价于
  "绿色 且 C_t>SMA20"；旧表述不准确。
- **本轮处理**：保留完整生产公式不改；等价关系作为解释写入手册与合同注释；
  等价成立的假设（同窗完整、种子后递推、浮点非临界）与限制记录在
  `tests/unit/test_factor_unit_close_state.py` 的等价性测试与模块 docstring。
  数学冗余不产生任何预测价值结论。

## R4 来源不能猜

- **旧说法**（readiness-matrix.csv 四载体 price_basis）："OHLC,复权口径未标注(疑似前复权,未核)"、
  "同Yahoo系复权惯例,未核"。
- **主控已核事实**：找到 A 股 `qfq` 优先、失败回退新浪不复权的抓取代码；美股 `auto_adjust=True`。
  代码存在不证明现存文件当年走了哪个分支。
- **本轮处理**：Task 2 产出 `source-decision.csv`，逐载体区分三档：
  `producer_candidate_only`（代码可能来源）＜ `snapshot_provenance_bound`（文件绑定已证来源）＜
  `price_basis_verified`（价格尺度已独立核验）。不得用供应商惯例、文件名、mtime 或官方网页
  自填 verified。价格尺度不清时只输出结构质量，不计算有投资含义的涨跌。

## R5 窗口与风险目标

- **旧说法**（dual-ma-study-proposal.json auxiliary_target）："同一窗口内相对I(e)的最不利收盘变化
  （min over 收盘∈(e,x] 的 I(t)/I(e)-1）"——没有零下界；预热表述"预热不再加未来22根"
  未把观察前回看与观察后标签分开。
- **主控已核事实**：预热在观察之前；标签的 22 根未来资料在观察之后，不是额外起点预热；
  最不利变化只取 (e,x] 可能全为正。
- **本轮处理**：e=t+1、x=t+22 保留；观察前 lookback=20 与观察后 horizon=22 在合同中分开字段；
  下行目标固定 `min(0, min(I_s/I_e−1 for s in (e,x]))`，含零下界；不称账户回撤。
  主目标端点缺失不顺延；尾部未成熟独立记录，不并入缺失混计。

## R6 证据边界

- **旧说法**（examples-results.json scaled_x100 note）："价格同比缩放(含每份分红同尺度调整的
  极端情形)状态不变"——该例只有价格，没有现金分红，声称"分红缩放已验证"超出证据。
- **主控已核事实**：缩放例只有价格无分红，不能声称通过"每份分红同步缩放"。
- **本轮处理**：删除扩大表述（A 阶段报告顶部只加纠正指针，不改旧 raw 的 JSON；本文件记录替代说法：
  "仅验证了纯价格同比缩放状态不变；含现金分红的缩放例本轮未实现，显式标 not_applicable，
  不谎报覆盖"）。若未来实现含分红小例，须价格与每份现金分红同步缩放、拆分比例不随货币缩放。
  另：旧情绪研究的高胜率等是旧报告主张，本轮及上轮均未复核，引用时标"旧主张"。

## 附加澄清（非纠正项，随本轮固化）

- close-only 输入不是删减策略条件：完整共同确认仍调用 `dual_ma_bull_state` 生产函数，
  只剥离与该状态无关的 ATR/MACD/成交量计算。
- 状态 false 不是看空；未就绪（warmup/缺价）不是 false，输出可空布尔单列。
- SMA/EMA 条件关系（R3 等价）的假设边界：同一完整窗口、EMA 已过种子、比较非浮点临界；
  浮点临界（价格与均线差在 1e-10 相对容差内）时等价判定不作有效结论，状态按生产函数原样输出。
- 文件首日不是上市日证明；多留预热天数不创造上市证据。首轮只研究资料覆盖内的日期。
