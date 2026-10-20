# 能力事实表（capability-map）

日期：2026-09-16。性质：本轮只读盘点的结论，供主控复核。
证据标注约定：【代码】=本轮直接核对过代码/文件；【裁决】=主控复核报告结论；
【声明】=执行者报告中的完成声明（未经本轮独立复算）；【推断】=我的判断；
【未确认】=找不到证据或无法核验。

核对基线：分支 `codex/factor-unit-research-20260915`，HEAD
`8ba16576b75e605aa1b0d0902568c760c4b99095`，与任务书一致；工作区有大量既有
未提交改动（只读记录，未处理）。

## 一、能力总表

| # | 能力 | 实际入口 | 证据与等级 | 当前限制 | 是否有并行计划覆盖 |
|---|---|---|---|---|---|
| 1 | 对象定义登记与解析 | `docs/research/definitions.v1.json`（容器 v1.2.0，81 个对象：feature / state_signal / factor_return / risk_metric / benchmark / policy 六类）；`src/lei_signal/research/definitions.py::validate_registry/resolve/make_manifest` | 【代码】本轮枚举全部 81 个对象 ID；解析与校验函数存在且有单测（research 原则 v1.1 引用） | models 当前为空（事实：没有任何收益解释模型卡，不能估计 α/β 意义上的因子暴露）；候选对象（双均线）不在登记表 | 否（是否引入模型卡按具体问题另行决策，见 reuse-decisions） |
| 2 | 生产双均线"道路"状态 | `src/lei_signal/rules/dual_ma.py::dual_ma_bull_state`；参数在 `configs/rules.v1.yaml`（dual_ma_bull_confirmed 等） | 【代码】函数与规则账本存在；factor_unit 的 close_state 复用该生产公式（factor-unit-usage.md §1） | 是状态描述，不含预测有效性证据 | B1 已做第一次真实描述（见 #4） |
| 3 | factor_unit 研究管线（B0） | `src/lei_signal/research/factor_unit/`：close_state / study_contract / state_description；CLI `scripts/check_factor_unit_readiness.py` | 【裁决】factor-unit-interpretation-closeout-2026-09-16（解释线收口）；factor-unit-usage.md 手册 | 合同校验、合成统计、冻结打包已验证；真实数据状态/目标计算资格逐载体走 B1 式证据链；available_at 逐行真实历史资格未实现；CN 日历仅覆盖 2019-09-01—2026-06-30 | 否 |
| 4 | B1：双均线状态首次真实历史描述 | raw：`docs/experiments/raw/b1-dual-ma-first-real-description-2026-09-16/run-02/`；报告 `b1-dual-ma-first-real-description-2026-09-16.md` §12 | 【裁决】b1-closeout-controller-2026-09-16：限定收口。核心数字（510300，2019-10-08—2025-12-31，1516 个有效观察）：状态成立组（590 次）t+1→t+22 供应商调整价平均 +1.04%、不成立组（926 次）+0.34%；但七个年份只有 2 年成立组更好；观察窗口互相重叠；快照 2026-09-08 取得 | 单一载体、单一目标（供应商调整价变化，含分红财富资格未核）、历史描述而非预测证明、含分红等价性未核 | 是：factor-evidence-reliability-v1（见 #5） |
| 5 | 因子证据可靠性工具（年份稳定性/重叠审计/整段重抽） | `src/lei_signal/research/factor_evidence/`：主控复核时已见六个模块文件（contract / observations / resampling / stability / runner / \_\_init\_\_） | 【代码+裁决】计划已授权（用户 2026-09-16"可以的，那开整吧"）。**时点说明**：本表 v1.0 撰写时该目录尚不存在且派发两次失败，故记"未启动"；主控同日复核时已见模块文件，任务进入实现阶段。**目录/文件存在不等于运行、交付或验收完成**，实现状态以该任务实际交付为准 | 首版设计只支持二元状态观察表；产物未交付前不得当作已实现能力引用 | 本身即并行计划 |
| 6 | factor_lab 通用研究原型（v1.2.0） | `src/lei_signal/research/factor_lab/`：contracts/adapters/diagnostics/validation/attribution/runner | 【裁决】factor-lab-final-controller-decision-2026-09-15：限定收口，**仅供合成研究的通用原型**。可算 6 个已登记对象+双均线候选；按对象类型分流检验（数值横截面 IC、状态真假对比、宽度跨日期对照）；有尝试史/时间切分/标签成熟检查；归因入口（合成账户）已具备 | 合成验证≠真实资格：逐行真实历史特征可得时间、稳健统计推断、多次尝试校正、风险收益回归、真实资料消费者均未授予使用资格 | 部分：真实二元状态的可靠性由 #5 覆盖；IC 真实数据使用无并行计划 |
| 7 | 宽度：生产计算与登记对象 | 生产：`src/lei_signal/market_context/a_share_breadth.py`、`breadth.py`、`us_breadth.py`；登记：breadth.all_a/csi300/chinext × b50/b200（共同分母版）+ delta 特征 + three_tier，共 16 个对象 | 【代码】模块与登记对象存在。**universe 科创板缺口已修**：`a_share_breadth.py:132-140` P0 修复代码在，缓存 `a_share_codes.json` 现 5564 码含 618 只 sh68（本轮实测） | 早年全A宽度序列有存续成分幸存者偏差（情绪线交接 §4）；历史序列是否已回算修复【未确认】；指数宽度受历史成员变更影响（definition-standard §4） | 板块工作台 P0-P1 已落地（sector_trend.py 存在）【代码】 |
| 8 | 宽度择时既有实验结论 | `midzone-breadth-timing-2026-09-07.md`、`breadth-price50-decision-2026-09-09.md`、`etf-breadth-source-confirmation-backtest-2026-09-09.md` 等 | 【裁决→已归档实验】中间地带（宽度 20-80）择时 16 组参数 21 年全跑输持有；宽度与价格是"同步"而非"提前"关系；159915 宽度+价格确认保留为有限研究候选 | 这些是择时/政策问题；"宽度与双均线是否重复信息"这一因子库问题**未被回答**（candidate-directions C2） | 否 |
| 9 | 情绪/市场环境叙事层 | `src/lei_signal/market_context/`：market_mood（CN 三票+US 三成分）、retail_heat（档位结构分化）、sentiment（NAAIM/AAII 加载器，字段含 available_at）、sentiment_signals；情绪线交接指定的证据账本 `configs/sentiment_evidence.json`；前向存证机制（交接称 2026-09-06 起每日自动） | 【代码+转引】模块存在为【代码】；"冰点机会 CONFIRMED（4/4 事件盈利）""强热 DOWNGRADED"、证伪清单与前向账本运行状态均为**旧交接标注的局部研究状态，本轮转引未复验**（未独立重审其设计、尝试史、时间资格与事件间独立性），不能升级为当前统一因子标准下的有效性证明。available_at 字段存在不等于真实发布时间已逐条核验。注意区分：**"生产在用"（代码与页面在跑）≠"研究数据合格"（资格/口径/连续性经审计）** | 定位是叙事标注层；旧文所称"环境加权"用法是旧交接的工作表述，本轮未获任何影响仓位或判定的授权；情绪对象**不在 definitions.v1.json 登记表**，证据账本与登记表是两套权威；板块热度分位约 9 月底才满窗口（交接声明）；文本情绪、期权信息（CN）无数据 | 情绪线增量候选在其交接 §7（前向对账优先），与因子库方向相邻但不重复 |
| 10 | 板块趋势工作台 | `src/lei_signal/market_context/sector_trend.py`（等权指数合成/RS/板块宽度） | 【代码】模块存在，方案 `docs/plan-sector-trend-page.md` P0-P4 | 以当前成分回溯（含前视偏差，仅形态参考）；MA200 留痕中 | 已落地，非本提案范围 |
| 11 | 混合池动量/波动 v0 | 登记对象 mixed.momentum.raw/rv20/eligible/top3 及 6 个 policy 卡；v0 计划 `docs/superpowers/plans/2026-09-09-factor-library-v0.md` | 【裁决】v0 冻结任务（4 只以上产品实际等权成交测试等），按原协议保留 | 冻结范围，不中途扩项 | 否 |
| 12 | 宽基/ETF 专项主战场 | `docs/superpowers/plans/2026-09-08-broad-index-etf-research.md` | 【裁决→计划】阶段二部分完成（300/创业板 12 账户；H1 简化候选保留、H2 不作通用升级）；下一步补 510050/510500 | 与因子库方向是两条线：专项做政策/账户比较，因子库做对象级证据；共享数据与定义 | 独立推进 |
| 13 | 外部工具审阅积累 | `factor-library-external-backlog-2026-09-09.md`（v1.1.0）、`research-tool-reuse-shortlist-2026-09-14.md`（v1.1.0）、`qlib-alpha158-definition-review-2026-09-12.md`、`factorhub-api-reuse-review-2026-09-14.md` | 【裁决→审阅文档】Alphalens 优先适配候选；Qlib/Alpha158 五类公式已对照（无一可直接替换）；FactorHub 13 次真实只读调用（scores 是汇总绩效非逐股值、ETF 空表、限流） | 全部是"读过文档/源码"级证据，无本地安装运行、无逐值一致、无已接入消费者（本轮新增一次 PyPI 版本核验，见 reuse-decisions） | 否 |

## 二、按"用途"看的空白（我的推断，供比较候选时参考）

登记表 81 个对象按机器用途分布：description/diagnostic 占绝大多数，
ranking 只有动量族，attribution 的两个 factor_return 是
`mixed.asset.total_return@1.0.0`（混合池单产品经济总回报）与
`cash.zero@1.0.0`（零息现金），models 为空（事实陈述；是否引入模型卡按
问题另行决策，本轮不对其作"有意设计"的因果判断）。结合 B1/情绪线/宽度线
的已有结论，当前最真实的空白不是"因子数量"，而是：

1. **单一证据的稳定性**——B1 全期差 2 正 5 负的年份分布还没有量化的
   敏感性范围（并行任务 #5 将补）；
2. **跨载体证据**——本轮未找到双均线 B1 同合同的第二载体正式结果（其他
   对象未做穷尽检索，不声称"任何对象都没有"）（C1）；
3. **对象间重复度**——宽度/双均线/情绪三票都在描述"市场冷热"，"谁包含谁"
   在指定对象/载体/目标组合上从未正式检验过（C2；结论只约束被检组合）；
4. **横截面排序的真实数据使用**——factor_lab 的 IC 能力只吃过合成数据。

## 三、找不到/未确认清单

- factor_lab"真实数据 IC 诊断"的任何已执行记录：**未找到**（合成案例之外）。
- 双均线候选升级为登记对象的记录：**未找到**（仍是 candidate@draft-1，与
  factor-unit-usage.md 一致）。
- 全A宽度历史序列在 P0 修复后是否回算：**未确认**。
- B1 目标"含分红财富"资格：主控裁定 blocked（manual_target_review_required），
  未解除。
- 美股交易日历/半日市表：factor-unit-usage.md 明示未实现。

## 修订记录

| 版本 | 日期 | 变化 |
|---|---|---|
| v1.0 | 2026-09-16 | 初版 |
| v1.1 | 2026-09-16 | 按主控复核 R1–R4 修订：#5 时点更新（factor_evidence 六模块已出现，存在≠运行/验收）；#9 情绪状态改为"旧交接标注的局部研究状态，本轮转引未复验"，生产在用与研究合格分列，available_at 字段≠已核发布时间，"环境加权"限定为旧文表述；§二 跨载体断言收窄为"未找到双均线 B1 同合同第二载体结果（其他对象未穷尽）"，factor_return 身份更正为 mixed.asset.total_return 与 cash.zero，删去 models 为空的"有意设计"因果判断。原字节封存 history-v1/，逐项对照见 revision-response.md |
