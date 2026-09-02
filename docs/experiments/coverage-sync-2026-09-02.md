# 跨机器任务覆盖清单同步报告（2026-09-02，Prompt X 阶段零）

> 本报告是 Prompt X 的第一优先级产出：在任何宽基回测开始之前，先确认
> 本机 git 环境、远端分支、prompt 任务书与归档文件三方的覆盖状态一致。
> 全程只读 + 新增文件恢复，未改任何现有归档、未动 `src/`、未 push。

---

## 0. 执行摘要（三句话）

1. **本机与远端完全同步**：`git fetch --all` 无新对象；远端仅 3 个分支
   （data-sync / feat/timing-backtest / recovery/lei-round2），全部已包含
   在本机，无未拉取的 experiments 相关 commit。
2. **重大新发现——"git 无痕"第二批幸存者**：`stash@{0}` 的第三 parent
   （untracked-files commit `1a321ce`）保存着 9-1 事故时全部 2000 个未
   跟踪文件，其中 **26 份 `docs/experiments/` 报告从未进过任何分支
   commit、也不在本机工作区**——本次已全部恢复（blob hash 验证一致）。
3. **头号疑点**：`prompt-*.md` 任务书系列（A 至 W）与
   `prompts-2026-09-01.md` **从未存在于本仓库的任何分支、stash 或远端**，
   覆盖核对只能靠报告内引用重建字母映射；**J–N、P–S、U–V 共 12 个
   编号在本机零引用零归档**，去向无法从本机核实（详见 §4）。

---

## 1. 同步操作记录（可复现）

| 步骤 | 命令 | 结果 |
|---|---|---|
| 1 | `git fetch --all` | 无新对象（本机已与 origin 同步） |
| 2 | `git ls-remote --heads origin` | 仅 3 分支：`data-sync@ee9a8e5`、`feat/timing-backtest@ef89d12`、`recovery/lei-round2@1bc54d3`；无 tags |
| 3 | `git log recovery/lei-round2..data-sync --oneline` | 17 个 commit 超前，**全部是 newsfeed 工作线**（页面/服务/数据源），不涉及 `docs/experiments/` |
| 4 | `git log recovery/lei-round2..feat/timing-backtest` | 空（本分支完全包含该分支历史） |
| 5 | `git log --all --oneline -- docs/experiments/` | 10 个 commit 触及该目录（1bc54d3 / 021b95c / d9dfa98 / 0b0958d / 21e2cd9 / 528a604 / 5c8b35b / 47790a7 / 0ced1ff / fb33547） |
| 6 | `git status` | 工作区干净（恢复操作前），分支 recovery/lei-round2 与 origin 一致 |

**结论：远端没有本机缺失的 commit，无需 pull，无冲突。**
用户所述"至少两台机器"中，另一台机器若有未 push 的本地工作，从本机
不可见——这是覆盖同步的固有边界，如实声明（见 §4 疑点 3）。

---

## 2. 重大发现：stash untracked commit `1a321ce` 与 26 份报告的恢复

### 2.1 机制（为什么此前查不到）

`stash@{0}`（`a816485`，"On feat/timing-backtest: WIP … before archive
task"）是三 parent 的 stash commit：`ef89d12`（原 HEAD）+ `4dcf794`
（index）+ **`1a321ce`（untracked files，2000 个文件）**。

9-1 事故时工作区被 checkout 切走，这批 untracked 文件从工作区消失且
从未被任何分支 commit 引用。`git log --all -- <path>` 因 merge commit
的 TREESAME 历史简化跟随第一 parent（`ef89d12` 的 tree 里没有这些文件），
**把第三 parent `1a321ce` 剪掉了**——所以逐路径查询返回空。这与
`scripts/legacy_recovery/README.md` 记录的"悬空 blob"是同一事故的两种
"git 无痕"形态：那批是解链的 dangling blob，这批是挂在 stash 第三
parent 上、被历史简化隐藏的 commit。

发现路径：`git log --all --name-only` 的文件流里出现了
`regime-gate-report-2026-08-27.md` 等文件名，但逐路径 `git log` 查不到
归属 commit → 定位到 stash 三个组成 commit → `git show --name-only
1a321ce` 确认。

### 2.2 恢复内容与可信度证据

恢复方法：`git show 1a321ce:docs/experiments/<file> > docs/experiments/<file>`。
**只新增，不覆盖任何现有文件**（恢复前逐一确认工作区无同名文件）。

可信度三重证据：

1. **同源验证**：11 份"stash 有、工作区也有"的报告
   （breadth-overlay / cash-leg / combined-certification / exit-matrix /
   FINAL-VERDICT-walkforward / gold-expand / meta-scan / module-e /
   sentiment-gate / signal-density / trd-gate）逐一 `git diff 1a321ce HEAD
   -- <file>`，**全部 0 行差异**——stash 快照与事后入库内容逐字节一致，
   证明 stash 副本与已归档内容同源。
2. **完整性验证**：抽样 `git rev-parse 1a321ce:<path>` vs
   `git hash-object <恢复文件>`，blob hash 一致（regime-gate /
   portfolio-split / siphon-detector 三份 OK）。
3. **时间线自洽**：恢复文件日期（8-25～8-28）与 raw 数据入库
   （21e2cd9"宽度组raw原始数据入库(20目录32MB)"）及后续归档引用吻合。

### 2.3 恢复的 26 份报告清单（一行一条）

| # | 文件 | 一句话内容 |
|---|---|---|
| 1 | b-adaptation-report-2026-08-26.md | B 模块全谱参数×标的类型适配：宽基/美股 ETF 上默认档 N=0 |
| 2 | bcd-retrial-report-2026-08-26.md | B/C/D 公平重测：C 在 ETF 池维持原判（零轴未劈开） |
| 3 | bform-dynamic-report-2026-08-28.md | 动态入池/动态权重判负；回答"为什么是这 9 只" |
| 4 | bform-exploration-report-2026-08-28.md | B 形态六个探索方向零采纳，v1-final 保持默认 |
| 5 | bform-final-review-report-2026-08-28.md | B 形态过全部四道终审（WF OOS +8.6%/年、安慰剂 100 分位） |
| 6 | bform-global-report-2026-08-28.md | **M5 跨市场宽指组合**（A腿宽度闸+美腿无闸）：Calmar 0.483 全场最优 |
| 7 | breadth-position-report-2026-08-27.md | 宽度→仓位曲线：美股调仓不成立；A股档位式有效但跑不赢 DCA（S3 纯择时除外） |
| 8 | etf-expansion-log-2026-08-25.md | 扩池实验日志 |
| 9 | etf-expansion-report-2026-08-25.md | **A 稳健档在 33 行业 ETF 池被推翻；唯一稳健子池=沪深300 ETF 单标的（OOS +2.26R）** |
| 10 | experiment-log-2026-08-25.md | 8-25 四轮实验总日志 |
| 11 | filters-round4-log-2026-08-25.md | Round4 过滤器日志 |
| 12 | filters-round4-report-2026-08-25.md | Round4 过滤器报告 |
| 13 | final-report-2026-08-25.md | 8-25 终报：建议 B="A 不应对 A股指数/外盘指数/申万板块开放"（§0 建议A 已被 etf-expansion 推翻，报告头部有更正声明） |
| 14 | full-stack-sim-report-2026-08-27.md | 三层串联模拟器：两过一失，卡在终值（57.4%<70%） |
| 15 | knife-timestop-report-2026-08-27.md | 接刀格时间止损判负（创业板 V 陡结构，躲刀必错过 V 反） |
| 16 | lifecycle-report-2026-08-27.md | 生命周期组合未达有效，输给"全都要"；B' 定案切 a6_1 |
| 17 | m5-final-review-report-2026-08-28.md | **M5 两道终审 FAIL，不转正，定格"配置型可选"**（WF 与等权打平） |
| 18 | portfolio-params-pool-report-2026-08-28.md | B 形态参数真高原（24/24）、9 只已是最优池规模 |
| 19 | portfolio-report-2026-08-27.md | 资金层 0/54 过双杠；2026 失血真实量级比统计小一半 |
| 20 | portfolio-split-report-2026-08-28.md | **组合级宽度预算：9 标的等权×冠军三档 年化+12.0% vs 持有−0.5%，31/31 起点占优**（8指数篮子前身） |
| 21 | regime-gate-report-2026-08-27.md | **宽基 ETF "仅横"门禁是干净发现**（牛市是宽基 B 唯一亏损源） |
| 22 | rs26-detector-report-2026-08-27.md | RS26 判别器判负（方向正确强度不足）——现行 RS 虹吸灯的方法论源头 |
| 23 | sector-layer-report-2026-08-27.md | 板块层筛选器 0/4 过双杠；RS 动量有真信息但笔数不足 |
| 24 | shrink-filter-report-2026-08-25.md | 收缩过滤器实验 |
| 25 | siphon-detector-report-2026-08-27.md | **虹吸判别器预注册判负**：宽度市场层结构不能判虹吸；RS26 背离是正确变量（虹吸灯诞生史） |
| 26 | stage-b200-report-2026-08-27.md | B200 口径纠正（coverage≠宽度）+ 双层路由 +45% 未达判定 |

### 2.4 stash 中尚未恢复的资产（本任务范围外，如实登记）

| 类别 | 内容 | 恢复命令（供后续任务使用） |
|---|---|---|
| docs/ 根 24 份 .md | PROJECT-HANDOFF-2026-08-27.md、backtest-round1/rr-sensitivity/validation-2026-08-25、data-sufficiency-audit-2026-08-24、handbook-30-videos.md、handoff-*-prompt.md×13（8-25～8-27 任务书）、trading-spec-v2/v2.1/v2-audit | `git show 1a321ce:<path> > <path>` |
| scripts/ 约 60+ 个 | run_bform_global / run_bform_mini（**legacy_recovery README §6 点名的依赖**）、run_siphon_detector、run_portfolio_split、run_knife_timestop、run_stage_b200 等 | 同上 |
| configs/ | rules.v2.yaml（9-1 事故核心账本） | 同上 |
| raw/ | raw/b_adaptation/b_adaptation_heatmaps.md 等 | 红线"不动 raw 目录"，未动 |

**判断依据**：Prompt X 的恢复需求止于"实验归档覆盖清单"，scripts 与
配置账本的恢复属于 legacy_recovery 任务的延伸，超出本任务范围；raw
目录受红线保护。以上清单登记在案，等用户统一核验后决定是否恢复。

---

## 3. Prompt 字母 ↔ 归档映射（重建结果）

任务书文件本身不在仓库（见 §4 疑点 1），映射只能靠报告内引用与
commit message 重建：

| 编号 | 任务 | 归档文件 | 状态 |
|---|---|---|---|
| A | 美债 | us-treasury-ARCHIVE-2026-09-01.md + us-treasury-CROSSCHECK-2026-09-01.md | ✅已同步（0b0958d） |
| B | VIX 情绪 | vix-sentiment-ARCHIVE-2026-09-01.md | ✅已同步 |
| C | A股宏观 | ashare-macro-ARCHIVE-2026-09-01.md | ✅已同步 |
| D | 正交检查 | orthogonality-check-2026-09-01.md | ✅已同步（报告内引用 8 次） |
| E | MACD 分层 | macd-strength-layering-ARCHIVE-2026-09-01.md | ✅已同步 |
| F | 仓位映射复活 | position-mapping-revival-ARCHIVE-2026-09-01.md | ✅已同步 |
| G | 出场复活 | exit-structural-stop-revival-ARCHIVE-2026-09-01.md | ✅已同步 |
| H | vt 网格 | vt-grid-ARCHIVE-2026-09-01.md | ✅已同步 |
| I | 止损矩阵 | stop-loss-matrix-ARCHIVE-2026-09-01.md | ✅已同步 |
| J–N | ？ | **本机零引用零归档** | ❌无法核实 |
| O | 池恢复审计 | pool-recovery-audit-2026-09-02.md（+d9dfa98/021b95c 两个 commit） | ✅已同步（报告自述"Prompt O 阶段一产出"） |
| P–S | ？ | **本机零引用零归档** | ❌无法核实 |
| T | （指数↔指数代理 0.80 阈值研究） | **无归档**——仅被 holdings-correlation（W）引用其 0.80 阈值 | ❌未归档/未同步 |
| U–V | ？ | **本机零引用零归档** | ❌无法核实 |
| W | 持仓相关性 | holdings-correlation-study-2026-09-02.md（1bc54d3，已 push） | ✅已同步 |
| X | 宽基体系化（本任务） | coverage-sync / broad-index-* 四份（本任务产出） | 🔄执行中 |

A–I 的映射依据是 commit `0b0958d` 的 message（"research(round-2026-09-01):
九任务探索归档入库——A美债/B VIX情绪/C A股宏观/D正交检查/E MACD分层/
F仓位映射复活/G出场复活/H vt网格/I止损矩阵"），非臆测。

**对阶段三的直接影响（按 Prompt X 红线要求预先声明）**：Prompt X 提到
"Prompt PQ 里可能测过的其他宽基对比结果"与"Prompt Q 提议但可能未执行
的纯宽基篮子方向"。本次同步确认：**P/Q（以及 U）在本机没有任何归档或
引用**。因此阶段三设计组合时，不能假设"宽基对比已被 PQ 测过"，应把
"纯宽基篮子 vs 1宽基+7行业篮子"当作未验证方向处理（M5 终审 FAIL 的
结论可作旁证，见阶段三报告）。

---

## 4. 未能同步的疑点清单（如实报告，未自行解决）

1. **prompt 任务书系列从未入仓**。`prompt-*.md`、`prompts-2026-09-01.md`
   在工作区、全部分支 commit、stash（含 1a321ce）、远端分支中均不存在
   （`git rev-list --all --objects | grep -i prompt` 仅命中 8-25～8-27
   时代的 `docs/handoff-*-prompt.md` 13 份，那是另一套编号体系）。
   它们只存在于用户侧或另一台机器。**后果**：J–N、P–S、U–V 共 12 个
   编号的任务内容、是否已执行、执行结果在哪，本机无法核实。
2. **vt-signal / time-stop-tail 两份归档不存在**。stop-loss-matrix（I）
   引用了"exit-structural/vt-signal/time-stop-tail 三份后续归档"，其中
   exit-structural-stop-revival 已存在（G）；vt-signal 与 time-stop-tail
   在本机所有分支 + stash 中均无同名文件。vt-grid-ARCHIVE（H）与
   knife-timestop-report（本次恢复）主题相近但文件名不同，**是否即所指
   无法核实，不作臆测**。
3. **另一台机器未 push 的工作不可见**。本机只能确认远端 3 分支已全部
   同步；若另一台机器存在未 push 的本地分支/工作区（例如执行了 J–N/
   P–S/U–V 中某些任务的机器），其产出本机看不到，需用户人工确认。
4. **恢复的 26 份报告未 commit**（本报告写入时为未跟踪状态）。将随本
   任务产出一起 commit 到本地 recovery/lei-round2，**不 push**（遵守
   收尾规约）。若用户核验后认为不应保留，删除这 26 个未跟踪文件即可
   完全回退（不影响任何已入库内容）。

---

## 5. 同步后归档总账（54 份 .md，全部在本机工作区）

- **已入库且已同步**（28 份，commit 0b0958d～1bc54d3）：ashare-macro、
  breadth-overlay、cash-leg、combined-certification、CROSS-GROUP-
  SYNTHESIS、exit-matrix、exit-structural-stop-revival、FINAL-VERDICT-
  walkforward、gold-expand、heiti-ARCHIVE、holdings-correlation、
  huanjing-ARCHIVE、kuandu-quanzhan-ARCHIVE、lei-ARCHIVE、macd-strength-
  layering-ARCHIVE、meta-scan、module-e、orthogonality-check、
  pool-recovery-audit、position-mapping-revival-ARCHIVE、sentiment-gate、
  signal-density、stop-loss-matrix-ARCHIVE、trd-gate、us-treasury-ARCHIVE、
  us-treasury-CROSSCHECK、vix-sentiment-ARCHIVE、vt-grid-ARCHIVE
- **本次新恢复**（26 份，来自 stash 1a321ce）：见 §2.3 清单
- **索引层**：`web/src/data/reportsIndex.ts`（8 条主报告，只读核对，
  未改动）——reportsIndex 未覆盖 docs/experiments/ 全量，是"旗舰报告
  卡片"索引而非实验总账，两者口径不同属正常

---

## 6. 对后续阶段的输入（阶段一/三/四的证据增量）

本次恢复直接改变了后续阶段的证据基础：

- **阶段一**：etf-expansion（沪深300 ETF 是 A 模块唯一稳健子池）、
  final-report（A 不应对指数开放的建议）、b-adaptation（B 模块宽基/
  美股 ETF 默认档 N=0）、breadth-position（宽度仓位 A股 vs 美股）、
  bform-global + m5-final-review（M5 跨市场宽指组合的完整生命周期：
  全场 Calmar 最优 → 两道终审 FAIL → 定格配置型可选）。
- **阶段三**：组合先例从 reportsIndex 的 4 个（两只版/8指数篮子/攻守
  兼备/合体组）扩充到 6 个（新增 M5、portfolio-split 9标的组合级宽度
  预算），且 M5 的"配置型可选"终审结论直接影响纯宽基篮子方向的预期。
- **阶段四**：siphon-detector + rs26-detector 补齐了 RS 虹吸灯从"判负
  → 方向正确强度不足 → 现行 RS120 灯"的方法论演进链；
  regime-gate 的"宽基 ETF 仅横门禁"是四个入场模块在宽基上最重要的一
  手证据；bcd-retrial / b-adaptation 补齐 B/C/D 在 ETF 池的全谱验证。

---

## 7. 元数据

- 执行时间：2026-09-02
- 环境：recovery/lei-round2 @ 1bc54d3（与 origin 一致）
- 恢复来源：`git show 1a321ce:<path>`（stash@{0} 第三 parent）
- 验证：11 份重叠文件 diff=0；3 份抽样 blob hash 一致
- 红线遵守：未改 src/、未改任何现有归档/索引/raw、未 push、恢复仅新增
- 后续：阶段一启动（宽基覆盖清单汇总，纯汇总不跑新回测）
