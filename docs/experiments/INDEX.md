# docs/experiments 总索引

> 2026-09-03 整理建索引。**没有移动、改名、删除任何现有文件**——所有归档、
> 任务书、raw 数据都在原位，本文件是新增的导航层。大白话说：这里的每份
> 文件都是一次独立实验或任务的"结案报告"，之前散着放找不到，现在按
> "任务编号 → 归档"和"主题 → 归档"两条路都能查。
>
> 维护约定：新增归档或新发任务书时，顺手在 §1 字母账和 §2 对应主题组各
> 补一行，保持索引不过期。

---

## 0. 新会话入口（按顺序读）

1. 仓库根 `AGENTS.md` — 项目级约束（先读策略文档、说人话、红线词汇）
2. `../next-steps-master-plan-2026-09-02.md` — **下一步方向总纲**（九个新组合
   语义 + 五项遗留债务 + 优先级建议，当前选题的唯一入口）
3. `coverage-sync-2026-09-02.md` — 跨机器任务覆盖对账（A–W 哪些做过、
   何处存疑；注意其 §3/§4 写于 23ca826 补齐归档之前，部分"零归档"结论
   已过时，以本索引 §1 为准）
4. `CROSS-GROUP-SYNTHESIS-2026-09-01.md` — 跨组统一视图与开放冲突清单
5. 本索引

## 1. 任务编号总账（任务书 → 执行归档）

### 9-01 轮（A–M，任务书合订本：`prompts-2026-09-01.md`）

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| A | 美债10Y/收益率曲线做美股触发 | us-treasury-ARCHIVE + us-treasury-CROSSCHECK | ✅ |
| B | VIX期限结构/PUT-CALL情绪触发 | vix-sentiment-ARCHIVE | ✅ |
| C | A股宏观变量触发层 | ashare-macro-ARCHIVE | ✅ |
| D | 新信号×现有两腿正交检查 | orthogonality-check | ✅ |
| E | MACD强度信号分层验证 | macd-strength-layering-ARCHIVE | ✅ |
| F | 宽度/利率分位仓位映射复活 | position-mapping-revival-ARCHIVE | ✅ |
| G | 纯结构止损复活（补止盈） | exit-structural-stop-revival-ARCHIVE | ✅ |
| H | vt目标波动缩放网格 | vt-grid-ARCHIVE | ✅ |
| I | 止损方式跨模块统一矩阵 | stop-loss-matrix-ARCHIVE | ✅ |
| J | a6_1三部件拆解（三件套） | exit-three-piece-ARCHIVE | ✅ 证伪（0/27 全灭） |
| K | vt接入信号驱动单标的仓位层 | vt-signal-driven-sizing-ARCHIVE | ✅ |
| L | 板块级RS加权 | sector-rs-ARCHIVE | ✅ |
| M | 时间止损接受右尾（反向设计） | time-stop-tail-aware-ARCHIVE | ✅ |

### 9-02 单发（N–X，任务书各自单独成文件）

| 编号 | 任务书 | 执行归档 | 状态 |
|---|---|---|---|
| N | prompt-N-module-conflict-resonance | module-conflict-resonance-ARCHIVE | ✅ |
| O | prompt-O-pool-recovery | pool-recovery-audit | ✅ |
| P | prompt-PQ（P：标普替代纳指） | spx-vs-ndx-ARCHIVE-2026-09-03 | ✅ 已执行 09-03（标普版年化-1.9pp、回撤略浅） |
| Q | prompt-PQ（Q：纯宽基vs行业篮子） | 无独立归档 | 〰️ 被 X 阶段三间接回答 |
| R | prompt-R-full-pool-revalidation | full-pool-revalidation-ARCHIVE | ✅ |
| S | prompt-S-b-module-reverse-vt | b-module-reverse-vt-ARCHIVE | ✅ |
| T | prompt-T-valuation-overlay | valuation-overlay-ARCHIVE | ✅ A股主判定证伪→催生U |
| U | prompt-U-us-erp-overlay | us-erp-overlay-ARCHIVE | ✅ |
| V | prompt-V-current-holdings-check | 无独立归档 | 〰️ 内容被 W 吸收（W 第三步） |
| W | prompt-W-holdings-correlation | holdings-correlation-study | ✅ |
| X | prompt-X-broad-index-comprehensive | coverage-sync + broad-index 三份 | ✅ 四份产出齐全 |

### 9-03 本轮拆分（任务书已入库；Y 已执行，其余待分发）

| 编号 | 任务书 | 内容 | 梯队 |
|---|---|---|---|
| Y | prompt-Y-pollution-recheck-2026-09-03 | 债务一+三复核：模块B仍成立；510500证据不足 | 一 · ✅已执行 |
| AE | prompt-AE-staged-entry-precheck-2026-09-03 | 语义九前置：分批执行叠加现有信号 | 一 |
| Z | prompt-Z-antifragile-precheck-2026-09-03 | 语义三前置：反脆弱补偿效应事件研究 | 一 |
| AA | prompt-AA-master-slave-precheck-2026-09-03 | 语义一前置：主从关系依赖性验证 | 二 |
| AB | prompt-AB-multi-confirm-frequency-2026-09-03 | 语义四前置：多重确认共触发频率 | 二 |
| AC | prompt-AC-timescale-layering-precheck-2026-09-03 | 语义五前置：长短期信号分层 | 二 |
| AD | prompt-AD-overnight-us-cn-precheck-2026-09-03 | 语义七前置：美股隔夜×次日A股关联 | 二 |

### 9-04 轮（AU–AW，会话内自研自跑，预注册+双跑哈希同前例）

| 编号 | 任务 | 执行归档 | 状态 |
|---|---|---|---|
| AU | 二元+滞回 vs 现役三档（决策级，AJ/AP 搁置的决策） | binary-hysteresis-vs-t3-decision-2026-09-04 | ✅ 判「换」（宽基域，待用户拍板） |
| AV | 极端底部价格阶梯执行（R1 主臂+R2 追涨兜底） | price-ladder-execution-2026-09-04 | ✅ 交换结构（+6.1pp中位 vs V型左尾） |
| AW | 宽度择时个股边界（12美股大盘股+SPY/QQQ） | us-stocks-timing-boundary-2026-09-04 | ✅ 判「无优势」（有效域=跟随宽度的宽基） |

不发（等条件）：语义二/六（总纲判高风险暂缓）、语义八（等 Z 结果）、
债务二（等用户拍板立项）、债务五 P 部分（等用户表态是否有兴趣）。

## 2. 归档按主题（每份文件只归一组，标题即内容摘要）

### 元与跨组

- `CROSS-GROUP-SYNTHESIS-2026-09-01.md` — 跨组统一视图（五路归档汇总）
- `coverage-sync-2026-09-02.md` — 跨机器任务覆盖对账 + stash 26份报告恢复
- `FINAL-VERDICT-walkforward-2026-08-27.md` — walk-forward 时序终审（第十三轮）
- `todo-new-composition-semantics-2026-09-02.md` — 新组合语义待办（已并入总纲）

### 宽度择时主线（大盘冷热信号）

- `kuandu-quanzhan-ARCHIVE-2026-09-01.md` — 31轮总决算（冠军三档、两只版、8指数篮子）
- `breadth-overlay-report-2026-08-27.md` — 宽度极值叠加（用户口径两档制）
- `stage-b200-report-2026-08-27.md` — stage路由 + B200 牛熊口径纠正

### 入场模块与标的池（8-25～8-28 早期探索 + 后续板块/判别器）

- `etf-expansion-log/report-2026-08-25.md` ×2 — 扩池实验（A稳健档被推翻）
- `experiment-log / final-report-2026-08-25.md` — 8-25 四轮总日志与终报
- `filters-round4-log/report-2026-08-25.md` ×2 — 第四轮过滤器（量能/筹码/状态机）
- `shrink-filter-report-2026-08-25.md` — 缩量回调过滤器
- `bcd-retrial-report-2026-08-26.md` — B/C/D 公平重测
- `b-adaptation-report-2026-08-26.md` — B 模块全谱参数×标的类型
- `bform-*-report-2026-08-28.md` ×3 — B 形态探索/动态/终审
- `portfolio-params-pool-report-2026-08-28.md` — B 形态参数真高原、9只最优池
- `regime-gate-report-2026-08-27.md` — 宽基"仅横"门禁（干净发现）
- `rs26-detector / siphon-detector-report-2026-08-27.md` — RS虹吸灯方法论源头
- `sector-layer-report-2026-08-27.md` — 板块第四层筛选器
- `sector-rs-ARCHIVE-2026-09-02.md` — 板块级RS加权（任务L）
- `module-conflict-resonance-ARCHIVE-2026-09-02.md` — 四模块同标的同日互斥（任务N）

### 出场与止损

- `exit-matrix-report-2026-08-31.md` — A/B'/C × 四种出场矩阵
- `exit-structural-stop-revival-ARCHIVE-2026-09-01.md` — a6_3 结构止损复活（任务G）
- `exit-three-piece-ARCHIVE-2026-09-02.md` — a6_5 三件套证伪（任务J）
- `stop-loss-matrix-ARCHIVE-2026-09-01.md` — 止损跨模块统一矩阵（任务I）
- `time-stop-tail-aware-ARCHIVE-2026-09-02.md` — 时间止损接受右尾（任务M）
- `knife-timestop-report-2026-08-27.md` — 接刀格时间止损判负

### 仓位与波动机制

- `breadth-position-report-2026-08-27.md` — 宽度→仓位曲线（定投基准对比出处）
- `position-mapping-revival-ARCHIVE-2026-09-01.md` — 仓位映射复活判负（任务F）
- `vt-grid-ARCHIVE-2026-09-01.md` — vt 网格（任务H）
- `vt-signal-driven-sizing-ARCHIVE-2026-09-02.md` — vt 信号驱动单标的仓位（任务K）
- `b-module-reverse-vt-ARCHIVE-2026-09-02.md` — B 高波反向 vt（任务S）
- `huanjing-ARCHIVE-2026-09-01.md` — 环境组宽度×RV 总仓位系数

### 组合与资金层

- `portfolio-report / portfolio-split-report-2026-08-27~28.md` — 资金层与分账制
- `bform-global-report + m5-final-review-report-2026-08-28.md` — M5 跨市场宽指组合全周期
- `heiti-ARCHIVE-2026-08-31.md` — 合体组（B9+LEI 分账制 224.6万/-9.7%）
- `combined-certification-report-2026-08-31.md` — 合体认证 6/6
- `cash-leg / gold-expand-report-2026-08-31.md` — 现金腿与黄金腿增强
- `lifecycle-report / full-stack-sim-report-2026-08-27.md` — 生命周期与三层串联
- `lei-ARCHIVE + meta-scan + signal-density` — LEI 个股腿三份
- `module-e-report-2026-08-27.md` — 模块E 情绪极值择时（手册口径）

### 宏观/情绪/估值确认层（触发路线，基本全线判负）

- `us-treasury-ARCHIVE + us-treasury-CROSSCHECK-2026-09-01.md` — 美债（任务A）
- `vix-sentiment-ARCHIVE-2026-09-01.md` — VIX/PUT-CALL（任务B）
- `ashare-macro-ARCHIVE-2026-09-01.md` — A股宏观（任务C）
- `sentiment-gate-report-2026-08-28.md` — 两融分位闸 + 北向
- `trd-gate-report-2026-08-31.md` — 股债性价比门首测即证伪
- `valuation-overlay-ARCHIVE-2026-09-02.md` — 估值确认层（任务T，A股证伪）
- `us-erp-overlay-ARCHIVE-2026-09-02.md` — 美股ERP（任务U）
- `orthogonality-check-2026-09-01.md` — 新信号×两腿正交（任务D）
- `macd-strength-layering-ARCHIVE-2026-09-01.md` — MACD强度分层（任务E）

### 宽基/全池/持仓/数据质量专项（9-02）

- `broad-index-coverage-summary / gap-fill / portfolio-and-signals-2026-09-02.md` — 任务X 阶段一/二/三+四
- `full-pool-revalidation-ARCHIVE-2026-09-02.md` — 175标的全池复验（任务R复验M+K）
- `data-quality-jump-audit-2026-09-02.md` — 13处复权断裂审计（修平方法出处）
- `holdings-correlation-study-2026-09-02.md` — 用户持仓×已验证标的相关性（任务W）
- `pool-recovery-audit-2026-09-02.md` — 深池环境盘点（任务O）
- `pollution-recheck-moduleB-csi500-2026-09-03.md` — 债务一+三复核（任务Y）
- `spx-vs-ndx-ARCHIVE-2026-09-03.md` — 标普替代纳指全量对比（任务P）

## 3. raw/ 数据目录对照

按目录名与归档名对应（个别按任务编号/提交信息推断并标注）；空白 = 未对账，
使用前以归档报告内的 raw 引用为准。快照类目录（backtest-runs / pool-snapshot）
是环境保全，不隶属单一实验。

| raw 目录 | 对应归档 |
|---|---|
| ashare-macro / vix-sentiment / us-treasury-signal(+crosscheck) / A_round2 | 任务A/B/C 归档（A_round2 为任务A二轮，推断） |
| breadth_overlay / stage_b200 | breadth-overlay / stage-b200 |
| breadth_position | breadth-position |
| etf_expansion | etf-expansion 系列 |
| b_adaptation / B_breakout_matrix（推断） / bcd_retrial | b-adaptation / bcd-retrial |
| bform 系列（无独立 raw，参数在归档内） | — |
| exit_matrix / exit_revival_a64 / exit_three_piece | exit-matrix / exit-structural-stop-revival / exit-three-piece |
| stop_loss_matrix / knife_timestop / time_stop_tail_aware(+full_pool) | stop-loss-matrix / knife-timestop / time-stop-tail-aware（full_pool=任务R复验） |
| position-mapping-revival / vt-grid / vt_signal_sizing(+full_pool) / b_reverse_vt / huanjing | 仓位机制组各归档（vt full_pool=任务R复验） |
| portfolio / portfolio_split / cash_leg / gold_expand / combined_cert / heiti / lei / meta_scan / signal_density / lifecycle_combo / full_stack / module_e / ultimate（heiti终极组合，推断） | 组合与资金层组各归档 |
| regime_gate / rs26_detector / siphon_detector / sector_layer / sector_rs / module-conflict-resonance | 入场模块组各归档 |
| sentiment / trd_gate / valuation_overlay / us_erp_overlay / orthogonality-check / macd-strength-layering | 触发/确认层组各归档 |
| gap_fill / holdings_correlation | broad-index-gap-fill / holdings-correlation |
| ashare_axes / cross_check / etf_breadth / stock_breadth | —（未对账） |
| backtest-runs-snapshot-2026-08-31 / pool-snapshot-2026-08-25 | 环境保全快照（非单一实验） |
| pollution_recheck / spx_vs_ndx | pollution-recheck / spx-vs-ndx（任务Y/P，09-03） |
| agent_AU-binary-hyst-vs-t3 / agent_AV-price-ladder / agent_AW-us-stocks-timing | binary-hysteresis-vs-t3-decision / price-ladder-execution / us-stocks-timing-boundary（09-04） |

## 4. 悬案与未执行清单

- ~~P（标普替代纳指）~~ **已执行（09-03，spx-vs-ndx-ARCHIVE）** — 两只版换腿：
  年化 15.9%→14.0%（-1.9pp）、回撤 -25.6%→-24.0%；防守版纳指档保险性价比更高
  （13.8 vs 8.7）。附勘误：原防守版归档"纳指5档"标签与代码不符（实为3档）。
- **数据断裂正式修复未立项** — `data-quality-jump-audit` 第7节，属生产数据
  操作，等用户拍板（总纲债务二）。新增两条待立项线索：①HEAD 引擎代码断链
  （engine.py 引用已丢失模块，复现靠 git 悬空对象重建，gc 后会失效）；
  ②512690 深池 2020-02-03 单日 +25.1% 超物理限制，不在审计 13 清单内。
- **债务一/三已复核（09-03，pollution-recheck 归档）** — 模块B宽基正收益仍
  成立（三跑分解），且审计 §5"b-adaptation 7宽基受污染"系跨数据源误推
  （该实验用深池数据、深池无跳变；勘误登记于此，不改原归档）；中证500 重审
  落"证据不足"中间态（翻案三条件仅过一条，判负触发条件也未命中）。
- **总纲债务四（J–N/P–S/U–V 去向不明）已基本自解** — 23ca826 补齐了任务书
  原文和 J/K/L/M/T/U 归档，实际残留只有上面两条。
- timing-sweep 时代引用的 `vt-signal / time-stop-tail` 两份后续归档，即
  vt-signal-driven-sizing 与 time-stop-tail-aware（coverage-sync 疑点2 的答案）。

## 5. 相邻目录

- `docs/timing-sweep/` — 8-27 时代 31 轮择时实验档案（`execution_playbook_20260827.md`
  被大量引用，其余为各轮 txt/csv）
- `docs/reports/` — 说明：回测 HTML 报告已迁至 `web/public/reports/`
- `docs/` 根的 `handoff-* / plan-*` 为应用线（data-sync）历史任务书与方案，
  与本目录研究线互不隶属
