## 2026-10-09 已找回原件后的当前状态补充

本补充只更新原件恢复后的事实。下方原目录正文、catalog.json、source-index和SHA256SUMS保留2026-10-07快照；其中“新Ridge仅交接、待原件”已被以下证据接续，不再作为当前阻塞。原目录16条旧结论和失败没有重写。

- **QLIB-ENGINEERING：历史工程保存证据已核。** 官方原包及源包已找到；14项协议输入、55项完成文件逐一大小与SHA相符，99键预测与回放一致。独立核保存预测差最大3.552713678800501e-15、系数差4.996003610813204e-16，低于原1e-10容差。历史预算1次训练、2次预测已用尽，本轮没有重跑。保存日志支持历史执行，未重现当时环境；只证明该工程数值一致，收益增量、预测改善与生产接入均未证明。旧2026-09-13 Alpha158暂缓整体引入的结论及适用范围不变。
- **D与后续不利幅度：原描述问题已完成。** 六准确原件已恢复，75个完整案例与1个未知按原合同计算并独审；五ETF平均排序关联D0.055231、波动基准0.409530，去掉有色同走势两个案例后差值反向。原X/Y各一次封存，不能据此认定稳定优劣、独立作用或交易有效。详见[真实结果报告](native-risk-d-mae20-real-ARCHIVE-2026-10-09.md)。
- **WORKFLOW-ENGINEERING：仍区分两种入口。** 本次独立适配器实际执行通过，native_workflow_contract=false；不能把它写成共享原生入口已完成真实接入，旧8项冻结指纹失败保持。

新证据及指纹入口：[当前补充映射](raw/research-dispatch-controller-2026-10-07/original-recovery-20261009/catalog-current-evidence.json)、[Qlib独审](raw/research-dispatch-controller-2026-10-07/original-recovery-20261009/qlib-independent-review.md)。其他旧条目的资格、预算与恢复条件不因此改变。当前补充新增拟合0、标签0、行情取数0。

---

# 旧研究结论、替代关系与修复影响目录（2026-10-07）

## 一句话结论（大白话）

**旧研究已有可复用的限定结论，不能把“程序通过”“发现关联”和“能改善交易”当成一件事。** 双均线、整理描述和ETF周度PPO目前没有稳定新增帮助的证明；部分风险研究有线索。5211/P26、11对B1及单ETF现金数字来自用户最新交接，本轮没有取得对应效果原件，不能冒称已独立验收，也不能用旧82股数字覆盖它们。已修正的结果用后续版本引用，只追溯真正消费过错误计算的部分。

本轮角色仅证据整理；执行模式report_only。没有新价格/信号/排名/标签/拟合或市场抽样，没有下载、403重试、交易、部署、权限或生产修改。目录JSON仅作导航，不替代definitions/registry权威登记。现有115项跟踪修改保持；当前HEAD不代替历史运行身份。

## 核心效果与新增帮助（均来自保存报告或标明的交接）

平方预测误差表示预测离实际有多远，越低越好；单位是平方百分点，不能换算成账户收益。“排名一致程度”是同一日期的因子名次与随后结果名次是否相符，范围-1至+1；负数不自动授权反向交易。下表范围仅沿原方法引用，不新计算。

| 研究问题 | 基准 / 候选 | 效果或变化 | 覆盖及证据边界 | 本轮处理 |
|---|---|---|---|---|
| 双20预测 | 已有S→加E；已有E→加S | 误差改善-0.2118 / +0.0546；两范围跨0 | 六ETF3474记录、已见历史 | 终版可引用 |
| 整理组合 | 丰富基准R→ALL | 收益72.2262→73.4600；风险16.9084→17.5279，均变差 | 八ETF2536条；旧模型独审 | 保留负结果，环境补充已结清 |
| 四期单项 | R→W/N/path/F | 收益改善-0.2597/-0.1530/-0.1805/+0.0174，调整范围跨0 | 6072条；保存汇总/账本 | 已补单项，不重复实验 |
| ETF周度PPO | B→BX | 配对宽基+4.55百分点只一对；行业-0.23 | 40/44周；至少三候选补充32/28周增量0/-0.00435 | 补充不抹旧指标 |
| B1空间 | 高空间→匹配对照 | 触C 6/11 vs7/11，-9.09百分点只一对 | 11对22案例；仅交接 | 效果原件待核 |
| 个股PPO5211 | PPO vs20日涨幅 | 排名一致-0.08272 vs-0.07870；高低差-1.365百分点 | 147周626092条；仅交接效果 | 输入可核，效果待核 |
| 个股P26 | 同3×3粗组内高持续减低持续 | -0.1701百分点；142周64正，残余PPO秩差+8.47百分点 | 支持622658；仅交接 | 不能证明彻底无增量 |
| 现金回放 | 原规则→筛选 | 终值104353.85→105785.72；回落9.34%→8.02% | 10万元、0.1%费用、6/4往返；仅交接 | 小样本账户描述，原件待核 |
| 工程流程 | 错误/正确合同、原模式 | 9/29限定218通过；10/7新45通过、旧40通过8失败 | 合成与声明边界 | 不称全套全绿或因子有效 |

## 逐项可复用结论目录

每项均列准确问题、池、标签、基准、限制、修复影响和原件路径。下列“核验”指这轮读取范围；原独审的数字比较次数不是这轮重跑次数。

### ETF-DUAL-STATE：六ETF双均线日状态修正版

- **问题 / 池：** 已有SMA或EMA确认后再加另一条，同期多周期共同确认有何变化？；510300/510050/510500/512100/159915/588000。
- **时间、标签 / 对照：** 2022—2026H1；t+1至t+22经济收盘21间隔；已有单线成立，另一条也成立对不成立；不混共同减全部基线。
- **已保存结论：** 双20 S加E六ETF平均+0.38百分点，范围[-4.37,+5.15]；E加S+0.69，[-1.51,+2.99]；均未确认稳定增量。
- **局限与本轮核验：** 每日持续状态、稀少分歧、已见历史，不是入场/账户收益；保存报告与独审已定位；本轮未复算市场数字。
- **计算修复影响：** 四等号日期影响七比较已由1.0.1纠正；35其他比较保留；不能把修正前数字当当前。
- **当前可执行动作：** 直接复用1.0.1；仅尚未桥接的历史消费者先追溯影响。
- **原件 / 版本：** [dual](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/dual-ma-information-findings-2026-09-28.md), [dual_start](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/dual-ma-correction-2026-09-28/started.json), [dual_summary](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/dual-ma-correction-2026-09-28/summary-v1.0.1.json), [dual_review](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/dual-ma-correction-2026-09-28/controller-review.md)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### ETF-DUAL-EVENT：六ETF刚确认事件与多周期

- **问题 / 池：** 20日刚确认时再加60/120确认是否更好？；相同六宽基。
- **时间、标签 / 对照：** 2022-01-01—2026-06-30；原D1冻结协议；主标签t+1至t+22；使用已保存事件；Q20首次确认后H真对H假，每组至少10起点。
- **已保存结论：** 原510300 14/33、差-3.810236，纠正为14/32、-3.779780；其他旧主比较不变，仍四负一正；588000共同8不足10，六ETF主汇总null。
- **局限与本轮核验：** 旧隔开机会辅助表不是主表；不能五ETF替六ETF；不与每日+1.76混为同一问题；保存报告与独审已定位；本轮未复算市场数字。
- **计算修复影响：** 510300 2025-05-29触发身份移除且无替代；旧非重叠辅助/其他Q60起点/账户未全重跑。
- **当前可执行动作：** 只引用纠正后510300行；其余历史分支标待消费链影响映射。
- **原件 / 版本：** [breadth](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/factor-breadth-dual-ma-findings-2026-09-24.md), [dual](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/dual-ma-information-findings-2026-09-28.md), [dual_event_impact](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/dual-ma-correction-2026-09-28/event-impact.json), [d1_protocol](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/dual-ma-resonance-d1-2026-09-23/protocol.json)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### ETF-DUAL-MODEL：双20预测增量终版

- **问题 / 池：** 另一条线是否减少相同未来标签的预测误差？；六宽基ETF。
- **时间、标签 / 对照：** 评价2024-01-02—2026-05-28，3474条；h21；同日/每ETF线性；单S/单E及涨幅波动控制。
- **已保存结论：** S加E误差改善-0.2118平方百分点，[-0.5474,+0.1160]；E加S+0.0546，[-0.2688,+0.3867]；完整输入再加双确认-0.6455。
- **局限与本轮核验：** 未见验证资料不足；组间描述和预测增量不同；n60/120本轮未执行；保存报告与独审已定位；本轮未复算市场数字。
- **计算修复影响：** 最终运行保留名义价等号勘误；开发02/03/终版不是三次独立市场证据。
- **当前可执行动作：** 复用pilot-final；历史入口恢复需原指纹源码，不修改冻结值。
- **原件 / 版本：** [classic](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/classic-benchmarks-dual20-final-2026-09-28.md), [classic_manifest](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/classic-benchmarks-2026-09-28/pilot-final/manifest.json), [classic_protocol](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/archive/handoffs-plans/classic-benchmarks-2026-09-28/protocol-final.json), [classic_old](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/classic-benchmarks-dual20-2026-09-28.md), [classic_r3](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/classic-benchmarks-dual20-r3-2026-09-28.md)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### ETF-COLOR-WNEF：八ETF整理语义与环境补充

- **问题 / 池：** 新增整理描述是否在丰富价格风险基准上有帮助？环境间保存误差改善是否不同？；固定四宽基四行业；2536条/317日期。
- **时间、标签 / 对照：** 2025与2026H1两期；t+1..t+21收盘20间隔，收益及入段收盘风险；R丰富基准；C=R+密集度/60日斜率；WNE/F/ALL各加C；资产与期等权。
- **已保存结论：** R收益/风险误差72.2262/16.9084；ALL73.4600/17.5279；相对C收益改善+0.4559，仍比R差；新增调整范围跨0。
- **局限与本轮核验：** ETF自身趋势；环境组成混杂；LightGBM up-down正主要down组变差；收益环境差额范围均跨0；保存报告与独审已定位；本轮未复算市场数字。
- **计算修复影响：** 旧age独审已排除指定四分支及环境链依赖；slope30名称后续澄清slope60；原数据不改。
- **当前可执行动作：** 停止重复20拟合与环境审查；这批环境缺口已补，不能称代表指数环境。
- **原件 / 版本：** [wn_report](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-semantics-quantification-2026-10-05/technical/REPORT.md), [wn_external](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/strategy-factor-expansion-2026-10-05/external/REPORT.md), [wn_checks](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/strategy-factor-expansion-2026-10-05/external/independent-checks.json), [env_acceptance](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-environment-remediation-2026-10-05/dispatch/coordinator-acceptance.md), [env_report](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-environment-remediation-2026-10-05/technical/REPORT.md), [env_inputs](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-environment-remediation-2026-10-05/technical/inputs.sha256), [env_code](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-environment-remediation-2026-10-05/technical/code.sha256), [env_outputs](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-environment-remediation-2026-10-05/technical/outputs.sha256), [age_review](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-age-impact-2026-10-05/dispatch/external-review.md)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### ETF-WNEF-R2：八ETF四期单项扩测

- **问题 / 池：** 拆开单项并补独立均值后是否有新增帮助？；八ETF，6072条/759日期。
- **时间、标签 / 对照：** 2023/2024/2025/2026H1；28字段R与成熟训练历史均值。
- **已保存结论：** W/N/path/F收益改善-0.2597/-0.1530/-0.1805/+0.0174；八项调整范围含0；历史均值收益/风险67.3816/14.1321低于R69.3086/14.8350。
- **局限与本轮核验：** 原资料已见；不得叠加第一批当独立样本；本轮仅已读登记报告和C4账本，未重新核原独审字节；已保存汇总/来源账本；原逐行成果独审未在本轮重认证。
- **计算修复影响：** 没有证明消费age；如主张修复影响必须绑定具体源码输入。
- **当前可执行动作：** 已有单项/均值问题已回答，不重复启动同族实验。
- **原件 / 版本：** [cloud_catalog](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/lei-cloud-research-consolidation-2026-10-05.md), [c4_ledger](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-cloud-consolidation-2026-10-05/sources/C4-PRIOR-RESULTS-LEDGER.md)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### SPY-WNEF-R3：单SPY限定风险快照

- **问题 / 池：** 同一旧字段在SPY风险目标上表现怎样？；SPY，229/102评价行。
- **时间、标签 / 对照：** 2025/2026H1，close_MAE；限定2021—2026H1供应商输入；R_US21，单加W/N/path/F，独立均值。
- **已保存结论：** R9.305072，path9.250725，F9.248536，均值8.475726平方百分点；path/F改善范围跨0；N条件退步。
- **局限与本轮核验：** 一个标的两期；美国控制与中国不同；没有收益目标；实际到达/行动/许可不完整；保存报告与独审已定位；本轮未复算市场数字。
- **计算修复影响：** 无已证计算修复传播；不能自动用新市场资格重开旧因子。
- **当前可执行动作：** 固定范围引用，停止换切片求正。
- **原件 / 版本：** [r3_report](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-cross-market-round3-2026-10-05/single-spy-technical/REPORT.md), [r3_review](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-cross-market-round3-2026-10-05/single-spy-review/REPORT.md), [c4_ledger](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-cloud-consolidation-2026-10-05/sources/C4-PRIOR-RESULTS-LEDGER.md)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### ETF-WEEKLY-PPO：八ETF周度PPO及排名补充

- **问题 / 池：** 固定绿色候选内PPO增加同周排序信息吗？；四宽基与四行业分别；40/44比较周，RankIC可算32/28。
- **时间、标签 / 对照：** 2025/2026H1；每周末检查，次日到第21日收盘20间隔；B固定40控制；BX加PPO；M4每ETF历史均值；两期等权。
- **已保存结论：** 配对排序BX-B宽基+4.55百分点仅一对；行业-0.23；RankIC增量0/-0.00435；MSE均值更低。
- **局限与本轮核验：** 至少3候选RankIC排除原宽基仅2候选改善周，不能用新指标抹去旧改善；熊市共同绿色0；历史到达未知；保存报告与独审已定位；本轮未复算市场数字。
- **计算修复影响：** 没有新计算修复；指标补充不是替代；来源含后续index绑定，不能继承旧环境包缺指数资料的历史状态断言。
- **当前可执行动作：** 原配对和补充共同引用；不推个股/账户/代表指数所有用途。
- **原件 / 版本：** [weekly_ppo](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/weekly-ppo-information-2026-10-05.md), [weekly_rank](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/weekly-ppo-rankic-addendum-2026-10-05.md), [weekly_ppo_source](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/weekly-ppo-information-2026-10-05/registration-source.json), [weekly_rank_source](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/weekly-ppo-rankic-addendum-2026-10-05/registration-source.json), [weekly_rank_zip](/Users/yongbiaoli/Desktop/lei-signal-lab/data/local-integration/weekly-ppo-rankic-register-20261005/LeiSignal-周度PPO-RankIC补充与完整复核证据-2026-10-05.zip)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### BREADTH-B200：旧沪深300宽度单调描述

- **问题 / 池：** 合格成员站上200日均线的比例越高，后月变化越高吗？；沪深300宽度旧冻结序列。
- **时间、标签 / 对照：** 2019-10-08—2025-12-31，1516日；21收盘间隔；原始宽度与后续价格变化排名一致程度。
- **已保存结论：** 全期-0.007966926；年度方向与总数不等同；未见整体正单调关系。
- **局限与本轮核验：** 原成员未独立重建；重叠标签；未测低宽度反弹/尾部/投入政策；保存报告与独审已定位；本轮未复算市场数字。
- **计算修复影响：** 未绑定到当前结构/age修复，不推定失效。
- **当前可执行动作：** 原用途可引用；配置政策须独立研究，不反向交易。
- **原件 / 版本：** [breadth](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/factor-breadth-dual-ma-findings-2026-09-24.md)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### B1-SPACE-11：六ETF旧B1空间条件

- **问题 / 池：** 上方空间更大是否减少随后触碰结构低点？；交接称六ETF，11对22案例。
- **时间、标签 / 对照：** 未来自然月触碰C；确切期间与匹配/重复归属待原件；高B1空间对匹配对照；100*(B1-A)/A，与D=(A-C)/ATR不同。
- **已保存结论：** 高空间6/11，对照7/11，差-9.09百分点，只有一对造成。
- **局限与本轮核验：** 原件输入/代码/合同/独审本轮未取得；不能当稳定改善；不得混factor_lab的B1基准或momentum-effect-b1目录；仅用户交接数字，原件待核。
- **计算修复影响：** 因依赖顶部/底部，当日有效性及来源需绑定后才能判断修复影响；当前unknown。
- **当前可执行动作：** 请求libfile_57a8793024808191948f5842acd82337原包；先核保存11对身份/触C及修复版本，不先重跑。
- **原件 / 版本：** [handoff](/Users/yongbiaoli/.codex/attachments/be0b188b-c490-4e3d-b46f-819abf3f4bce/已粘贴的文本.txt)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### STOCK-PPO-82：旧82股PPO探索与本地输入

- **问题 / 池：** 旧小池与新5211效果是否同一成果？；82固定缓存候选；原名单选择与遗漏未知。
- **时间、标签 / 对照：** 本机输入979日×82股，2020-12-18..2024-12-31准备+2022—2024正式；效果原件未核；原PPO对20日涨幅效果必须引用原合同。
- **已保存结论：** 本轮仅确认82输入ZIP与既有清单匹配；不把早先对话/记忆中约-0.055/-0.050写为已核效果。
- **局限与本轮核验：** 当前只读输入资格不等于PPO算完；缺上市退出/行动/到达证据；本地82输入可核；旧效果原件未核。
- **计算修复影响：** 不消费LEI结构按名猜测；旧计算源/标签资格需原件。
- **当前可执行动作：** 保留82对象独立身份；取旧效果原件作来源映射，不能替代5211新交接。
- **原件 / 版本：** [stock82_input_check](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/stock-ppo82-cloud-input-2026-10-07/export-verification.json), [stock82_input_zip](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/stock-ppo82-cloud-input-2026-10-07/stock-ppo82-frozen-close-2020-2024-v1.zip), [stock_progress](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/ops/work-progress/stock-universe-data-qualification.md)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### STOCK-PPO-5211：5211缓存PPO新交接

- **问题 / 池：** 大缓存同周PPO排名与后月变化有何关系？；5211当前保存价格列，不是历史全A可投资池。
- **时间、标签 / 对照：** 2022—2024；147配对周/626092有效股票日期（效果交接口径）；PPO12/26对20日涨幅，共同支持。
- **已保存结论：** 交接RankIC-0.08272 vs -0.07870，差-0.00402；高低组差约-1.365百分点，年度方向不一。
- **局限与本轮核验：** 本地已核输入ZIP，不包含效果结果；625720输入端点资格与626092效果不能强行等同或判错，需云端资格表/runner解释；历史池/行动未合格；效果仅用户交接；本地输入指纹已核。
- **计算修复影响：** 与82扩池不同；无证据要求结构bug重跑PPO。
- **当前可执行动作：** 取libfile_c83a1f03c3848191bdf05bf1346c0517原效果/独审；核对应libfile_2b6573053b4c81919b7d5fa119b568d8输入与全部尝试。
- **原件 / 版本：** [handoff](/Users/yongbiaoli/.codex/attachments/be0b188b-c490-4e3d-b46f-819abf3f4bce/已粘贴的文本.txt), [stock5211_input_check](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/stock-large-cloud-input-2026-10-07/export-verification.json), [stock5211_input_zip](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/stock-large-cloud-input-2026-10-07/stock-5211-frozen-close-2020-2024-v1.zip), [stock_progress](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/ops/work-progress/stock-universe-data-qualification.md)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### STOCK-P26-5211：P26持续性粗条件比较

- **问题 / 池：** 控制PPO及20日涨幅粗组后，过去26合格日PPO为正的比例是否还有分离？；同5211代码主题；原645815行、新共同622658（交接）；原P26包另核。
- **时间、标签 / 对照：** P26交接称最早277连续收盘；142周、2022—2024未来月度变化；PPO与20日涨幅3×3粗组，高持续减低持续。
- **已保存结论：** 交接总体-0.1701百分点，64/142周正；年度-0.3414/+0.0203/-0.2058；12预定删季度全负。
- **局限与本轮核验：** 残余PPO秩差+8.47百分点；只能粗条件未见正分离，不能彻底无增量；不能混ETF绿色占比；仅用户交接效果数字；本机新资格只核PPO输入暖机边界，原P26合同未核。
- **计算修复影响：** 一次标签适配错误统计前失败后修复独审重试，失败应保留；本轮未读原件，不能确认全部修复。
- **当前可执行动作：** 取P26一页libfile_1bfc06eaa1e48191af564744fc597687及全包libfile_8bcd654441588191acc07430522f4f6c核共同支持与失败记录；PPO输入包只有252日准备期设计，2022最初四周不足277根，不得直接当P26原输入或据此判云端P26错误。
- **原件 / 版本：** [handoff](/Users/yongbiaoli/.codex/attachments/be0b188b-c490-4e3d-b46f-819abf3f4bce/已粘贴的文本.txt), [stock_qualification_readback](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/stock-data-qualification-2026-10-07/readback.json), [stock_qualification_scope](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/stock-data-qualification-2026-10-07/scope.json)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### CASH-SINGLE-ETF：单ETF旧历史现金回放

- **问题 / 池：** 同一入场规则加筛选后资金路径如何？；交接只称单ETF，精确代码/日期/版本待原件，不猜510300。
- **时间、标签 / 对照：** 起始10万元，费用0.1%；6与4往返；原规则对筛选版本；卖出/再入/现金/约束需完整原合同。
- **已保存结论：** 交接终值104353.85 vs105785.72；最大资金回落9.34% vs8.02%。
- **局限与本轮核验：** 不是信息因子增量，少交易/少暴露本身也能减回撤；当前用户风险预算未确认；效果仅交接；工程修正证据另列，未证明传播到本现金包。
- **计算修复影响：** 与103→99 A3修正的实际上游是否同包unknown；不能拼新事件和旧现金或宣称收益已修正。
- **当前可执行动作：** 先取账户完整事件/成交/现金/费用+原源代码hash，判断实际受影响机会；若需纠错只重放已证受影响分支。
- **原件 / 版本：** [handoff](/Users/yongbiaoli/.codex/attachments/be0b188b-c490-4e3d-b46f-819abf3f4bce/已粘贴的文本.txt), [cache_independent](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/weekly-time-boundary-proposal-2026-10-06/references/cache-independent-audit/REPORT.md)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### WORKFLOW-ENGINEERING：原生研究流程与只审合同入口

- **问题 / 池：** 真实入口能否在计算前检查、保留失败/预算及诚实登记？；9/29人工两对象105日期；10/7合成声明/旧协议检查。
- **时间、标签 / 对照：** 工程用途；不适用金融持有窗口；错误/正确合同、原入口传参及无副作用。
- **已保存结论：** 9/29限定218相关测试通过；10/7新增45通过；旧回归40通过8失败，未全绿。
- **局限与本轮核验：** 新审查不核实际来源或科学设计且execution_authorized=false；云调度试验不能称全部原生接入；保存报告与独审已定位；本轮未复算市场数字。
- **计算修复影响：** 早前漏计拒绝耗时已修正，旧demos由demos-final接续；8失败源于旧冻结CLI指纹，不能改旧指纹凑通过。
- **当前可执行动作：** 复用现有合同/账本/锁；历史恢复用原源码；真实D-MAE接入由流程负责人处理。
- **原件 / 版本：** [workflow_final](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/research-workflow-engineering-final-2026-09-29.md), [workflow_before](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/research-workflow-engineering-2026-09-29.md), [workflow_review](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/workflow-declaration-review-cli-2026-10-07/README.md), [workflow_independent](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/workflow-declaration-review-cli-2026-10-07/independent-review.md), [workflow_failures](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/workflow-declaration-review-cli-2026-10-07/legacy-regression.txt), [workflow_tests](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/workflow-declaration-review-cli-2026-10-07/tests-final.txt)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### QLIB-ENGINEERING：Qlib旧定义审阅与新Ridge交接

- **问题 / 池：** 外部工程可行性有何证明？；旧五类表达式定义；新Ridge具体资料待原件。
- **时间、标签 / 对照：** 旧定义9/12—13；新Ridge时期不猜；旧数学/处理器对照；新预测与参照一致（交接）。
- **已保存结论：** 旧v1.1.0审阅收口、暂不整体引入；新交接称一次Ridge跑通且一致。
- **局限与本轮核验：** 旧暂缓不等于新工程未执行；新安装/预测一致不等于收益增量；旧定义报告可核；新工程运行仅交接。
- **计算修复影响：** 无新计算修复已证明；两层用途不同，不整体互相替代。
- **当前可执行动作：** 取新Ridge合同/输入/预测一致回执后映射，先不安装或重跑。
- **原件 / 版本：** [qlib_old](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/qlib-alpha158-controller-review-2026-09-13.md), [handoff](/Users/yongbiaoli/.codex/attachments/be0b188b-c490-4e3d-b46f-819abf3f4bce/已粘贴的文本.txt)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

### CORE-STRUCTURE-CALENDAR：结构/A3缓存与周线边界修正

- **问题 / 池：** 哪些旧事件/结果确受修复影响，哪些可排除？；第十一历史四基金；后续510300限定1337日/99事件。
- **时间、标签 / 对照：** 5103002020-12-21—2026-06-30；本项不读金融标签；旧结构/退出/缓存对修正版；当日确认与有效性、历史截断。
- **已保存结论：** 第十一366+168限定检查；第十四10检查；510300103→99事件(加1删5、另4引用变化)，入场43→39；去掉末尾不完整周后99不变。
- **局限与本轮核验：** 没有证明现金收益改善；v2日历补丁整包REVISE，F1—F4和D1—D3仍不能当已接入；保存报告与独审已定位；本轮未复算市场数字。
- **计算修复影响：** 旧过期底/确认日确影响指定事件；6/30末周例外对该99无影响；旧age固定八ETF排除但生产/早期unknown。
- **当前可执行动作：** 只列受影响消费者最小追溯；不全仓/不全实验重跑，不把补丁提案当修复完成。
- **原件 / 版本：** [acd_fix](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/acd-repair-validation-2026-09-08.md), [a6_fix](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/a-top-lifecycle-consumer-audit-2026-09-08.md), [cache_independent](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/weekly-time-boundary-proposal-2026-10-06/references/cache-independent-audit/REPORT.md), [calendar_review](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/weekly-time-boundary-proposal-v2-2026-10-06/audit-reference/REPORT.txt), [age_review](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-age-impact-2026-10-05/dispatch/external-review.md), [structure_preflight](/Users/yongbiaoli/Documents/Codex/2026-10-04/task/deliverables/lei-structure-integration-2026-10-05/preflight/REPORT.md)；精确输入、代码和输出身份见catalog.json与source-index.json，不猜缺失SHA。

## 替代关系与反例

| 旧状态 / 数字 | 后续证据 | 应怎样引用 |
|---|---|---|
| dual_review_old受影响7行/旧summary | dual 1.0.1及dual_summary | 七行纠错替代，其他35行保留 |
| breadth中510300旧事件14/33与-3.810236 | dual_event_impact 14/32与-3.779780 | 指定产品指定事件问题替代；旧辅助/Q60/账户未全桥接 |
| classic_old、classic_r3开发报告 | classic/pilot-final | 同问题终版替代，不当独立验证 |
| weekly_ppo配对准确率 | weekly_rank | 补充不替代；可计算周分母不同 |
| env_acceptance当时age影响未核 | age_review | 后续追溯更新；不回写冻结验收 |
| env_acceptance当时代表指数依赖缺失 | weekly_ppo来源中index binding | 后续特定研究有绑定；不能把旧自身环境改成代表指数环境 |
| wn第一批未拆单项/未独立均值 | R2保存报告/C4账本 | 新增回答，第一批旧身份保持，不叠加样本 |
| workflow_before旧拒绝耗时遗漏及旧demo | workflow_final/demos-final | 工程纠正接续，非市场效果提升 |
| 旧82股票结果 | 5211/P26交接 | 不同池和问题，不能互替或混为同一最新已核成果 |
| 9/13 Qlib整体暂缓 | 10/7新Ridge交接 | 新用途不同，旧结论范围保留，新运行原件待核 |

反例必须跟随结论：宽基PPO的+4.55只有一个两资产周，至少三资产排名补充排除了该周；行业同期还退步。LightGBM自身环境风险up-down为正主要来自down组更差，而不是整体风险改善；收益环境差额区间均跨0。P26粗控制后仍有+8.47百分点PPO秩差，不能写完全扣掉已有信息。单ETF少两次交易后的回撤下降不能单独证明筛选有信息。103→99事件证明计算纠错，不证明现金多赚。

代表指数资料状态必须按版本说：旧八ETF环境追加仅按ETF自身趋势；后来周度PPO包已有独立指数输入和日期绑定（原source-and-code-manifest.json中列出精确SHA）。这只解决后一个用途的引用，不能把旧自身环境汇总改称指数牛熊，也不能说全系统代表指数资料永远仍缺。

## 最小受影响追溯 / 重算清单

以下是交回负责人执行的依赖，不是本轮启动新计算。已修七比较、20拟合、固定环境补充、已排除age消费的成果不重跑。

- **R1 旧数值等号修正尚未桥接的非重叠辅助/Q60/账户消费者**：绑定四日期实际状态/事件依赖到准确运行与源码；既有7比较已修不重算。仅在保存消费者实际使用变更状态或事件；保留原样本/参数/预算、新路径时考虑限定纠错。负责人：技术01a0e703-4c27-74e2-bf77-997e1879f967。本目录只列清单，没有重算授权或操作。

- **R2 A3旧103→99及过期结构相关机会/账户**：取得旧现金与B1原件，核是否实际消费这套事件；记录5删除/1新增/4编号变化影响。仅在证实对应信号/筛选/退出变化；再只重放相同输入与原规则的受影响分支，不拼接旧金融数字时考虑限定纠错。负责人：技术01a0e703-4c27-74e2-bf77-997e1879f967。传播unknown，尚不能确定哪份现金数字需重算。

- **R3 旧age可能影响的生产缓存/早期B/D，及日历v2 F1—F4**：先核准确版本、资格条件和输出依赖，区分年龄值变化与事件变化；使用已有反例。仅在已证明有效事件或下游结果实际变；指定八ETF/六B普查/Q01等排除对象不重跑时考虑限定纠错。负责人：技术/中控按原消费链。局部工程依赖；不作为全库金融重跑理由。

- **R4 B1 11对、5211 PPO/P26、单ETF现金、新Qlib Ridge**：由已合法持有方转交合同/清单/结果/独审/失败账本；本机不重试403。仅在先做保存结果核数，只有具体适配修复未落实/输出与合同不一致才请求最小纠错时考虑限定纠错。负责人：中控取得云原件；数据线补资格。原件不可核；先保存证据不启动金融计算。

- **R5 8项旧冻结CLI指纹回归**：隔离恢复绑定旧源码或在新用途合同下明确版本；保留8失败。仅在为恢复真实入口所必需的合成回归，不能改旧pin或重算已封存市场结果时考虑限定纠错。负责人：流程01a0e6d5-4bcf-7bd3-82e4-4961c963d20e。证据目录已定位日志，修复/运行属流程线。

## 缺原件的准确恢复条件

由已合法持有原件的中控/用户转交Library成果及原合同、输入/代码清单、结果、独审和所有失败/尝试记录；这里不下载、不重试暂停的403。B1与现金若只是摘要，仍无法判断结构修复传播到哪个分支；不能为“核验”自行再造实验。5211 PPO输入包本机已存在且指纹已核，缺的是对应效果/审查原件，不应再导出同一输入。P26须核其原输入：本机PPO包的252日准备期不覆盖P26最早277连续收盘资格；最初四周不足，第五周计数边界依原P26合同。这不是云端P26效果错误的证明。

| 缺口 | 查找线索 | 原件到件后最小核验 |
|---|---|---|
| 5211 PPO效果/独审 | libfile_c83a1f03c3848191bdf05bf1346c0517；输入libfile_2b6573053b4c81919b7d5fa119b568d8 | 同ZIP/代码版本；147周、626092支持与保存表；不要强行套用输入资格625720 |
| P26摘要/全复算包 | libfile_1bfc06eaa1e48191af564744fc597687 / libfile_8bcd654441588191acc07430522f4f6c | 277根资格、共同622658、142周与粗组/残余秩差；首标签适配失败及重试 |
| B1 11对 | libfile_57a8793024808191948f5842acd82337；六ETF特征libfile_edf1c944a1108191add900a98a52819f、行情libfile_52d3f93ce4348191bb57344054fc3778 | 11对与重复归属、结构当日资格、自然月触C目标与原源码 |
| 单ETF现金 | 原交接第四节4项，无精确Library ID/代码/日期 | 整体账户/费用/成交/现金及事件身份；先证实是否消费新旧A3 |
| 新Qlib Ridge | 原交接目标7，无精确包ID | 一次运行合同与预测参照一致回执；不拿9/13定义审核代替新运行 |
| D—MAE设计 | raw/native-risk-d-mae-2026-10-07/immutable-handoff/PROPOSED-CONTRACT.json；SHA ace132ddb89de3e45951148d9673524fa9fe448f662f2576221d216bbe9717c6 | 合同已到件核字节，技术线做合成实现；原市场输入与真实运行仍由技术线核，不是旧B1或现金的结果原件 |

## 实际检查、失败与归档状态

本轮只做路径、报告映射、SHA与保存日志核验；没有重新执行独审的市场算术或合成测试。已核classic最终protocol与五输出；周度PPO完整补充ZIP及六个原研究成员；82/5211输入ZIP；WNEF报告/独审指纹及环境三清单自身。逐项结果和当前源码相对旧锁的漂移在verification.json。当前源码漂移不能改写旧金融结果，只表明复现必须用绑定原版本。环境三清单列出的全部产物前轮已有总验收，本轮未再完整重核每个环境输出。

定位中的三个失败保留：先试的结构接入根REPORT.md不存在，实际入口为preflight/REPORT.md；猜的breadth聚合source-manifest.json不存在，改用真实各runner/manifest路径，不伪造总清单；早期批量打印造成输出截断，改为限定文件和局部字段。均不涉及金融实验失败或新计算。

catalog.json所有条目有完整定位字段；缺失合同/代码/结果SHA为null，不用交接文字补造。source-index.json绑定建立目录时的实际文件字节与ZIP成员；其中controller仅为非研究证据的动态进度快照，其旧SHA不代表当前文件仍匹配，详见[定点维护回执](/Users/yongbiaoli/Desktop/lei-signal-lab/docs/experiments/raw/research-evidence-catalog-2026-10-07/snapshot-clarification-2026-10-07.json)；scope-and-start.json保存初始115项改动和保护文件SHA。verification.json保存有限检查，不冒称全仓审计。共享registry/INDEX/definitions未由本任务写入。

## ARCHIVE / 最小决策卡

执行状态completed：目录和最小影响清单已交付；结束依据为report_only边界内问题已回答。已读保存成果可在原问题/合同内复用；未到件效果为证据不足、待原件，不强行接受或否定。目录本身不批准交易、扩池、调参或新训练。

正式实验库登记由中控串行处理，本轮只交registry-candidate.json；**报告交付完成，登记/总归档尚未声称完成**。中控可直接读取catalog.json/source-index.json/verification.json，先取得缺原件并分流最小修复，其他D—MAE/资料/流程任务独立继续。
