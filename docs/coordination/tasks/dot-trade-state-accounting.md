# 已审问题落地：回测记录状态计数纠正

- task-id：dot-trade-state-accounting（新独立修复项；不替换三条 Pro 研究记录）
- 负责人：当前 dot LEI 接续主控；本线实施与独立验收，协调记录由本方唯一写入者维护。
- 状态：active（仅六文件工程修复；范围成功推送并读回后才实施）
- 更新时间：2026-10-03T11:49:00Z，Etc/UTC
- 目标：修正已审 IR-R02 的状态计数缺口：未实际入场/无效记录不能被显示为真实持仓，旧历史载入不能把不确定记录装作已核准。
- 用途：回测摘要和历史显示准确性；不改变策略、入场退出、收益或资金路径，不开展新策略研究。
- 验收：总数守恒，真实open与invalid/skipped/unknown分开；收益closed样本及全部R/回撤等其他指标保持；旧JSON无写盘、旧API数值字段兼容；UI准确显示纠正计数或“未核实”。

## 基线、成果与精确写入范围

计划工作分支：codex/lei-trade-state-accounting-20261003（尚未创建）。
实现基础完整commit：3e348e6fa49cdd399e9838f252a2c0c1f411c8c1，task/technical-factor-sequence-progress最新ref已核相同；较3deaad7a1724228780a62af49cf34fc046b0640a仅12文档/JSON变化。实现者已逐项核service、metrics、engine、BacktestPage及types五个blob未变，缺陷仍存在。
最近已推本任务代码成果commit：无；当前没有本任务已实现或已推的修复。只读材料和后续测试回执仅本地时均标远端不可复现，不借其他任务SHA冒称本方成果。协调自身commit按本路径Git历史定位。

预计只写以下六个文件：
1. src/lei_signal/backtest/trade_state_counts.py（新增，纯状态计数）
2. src/lei_signal/backtest/metrics.py
3. src/lei_signal/backtest/service.py
4. tests/unit/test_backtest_trade_state_counts.py（新增）
5. web/src/types.ts
6. web/src/pages/BacktestPage.tsx

不改Trade.is_open、回测engine、策略规则或旧保存JSON。新增任务无旧阶段记录需迁移；代码/测试留独立工作分支，当前摘要只有本task。范围外必要变动先报告并重新登记，不夹带共享修改。

## 本轮已明确的兼容合同

- invalid_nonpositive_risk独列；skipped_limit_up_at_entry与signal_at_end_not_entered列未入场。真正open仅明确open_at_end，或引擎已知退出原因且数据末尾未执行的记录；不识别则unknown，不倒推成持仓。
- 新运行metrics使用正确true-open计数，但保持原closed收益样本和全部其他收益指标。service新保存只补既有Trade分组字段；不改变交易过程。
- 旧历史JSON只读；旧legacy open_count数值及number类型保持。新增带版本/归属范围的trade_state_counts派生字段，明确旧计数legacy；不是把旧API number改为nullable。
- 旧记录缺clock_type/weekly_bull_env等、组归属无法核准时，只在新增纠正字段中使用null并给出原因。UI读取新字段，无法核准显示“未核实”，不把null当0、不覆盖旧文件，也不依赖未保存字段猜分组。
- 新旧记录均保留unknown；分类互斥、总数守恒。合成测试证明工程行为，不证明旧市场效果正确或策略更有收益。

## 已有检查、待验证与停止条件

已完成只读：最新协调规则/任务归属、稳定ID不存在、技术准确ref/12文件差异、相关源码未变及缺陷仍在。本轮未实施代码、未跑测试。
实施后限定验证：合成各种结束原因、无效/未入场/未知、守恒、收益不变、旧JSON前后字节不变与旧字段兼容；单元测试及受影响既有backtest测试；现有环境可用的前端类型检查。分别记录通过、失败、未运行及工具版本，不以部分测试当全站/生产通过。
阻塞/停止：若分类需改交易语义、旧字段兼容无法保持、发现同文件实际实施者、或六路径不足，暂停相应变动交回主控；不得凭本任务授权扩大市场计算、安装、部署或权限。目标是修复可核缺陷，资料不足留unknown，不另建平台。

## 归属、规范、预算与同步

fresh协调基线6b6be6266fd06e06afc3c9d39e61996edc3f5a1a；COORDINATION.md v1.0，blob126a1a01cd09439536c69fdd7264e3e292e4b852未变。本task在原13项中不存在。推前增量f3c5d414d31abf1df88b234ef228de75aee19b98只新增市场理解页面完成状态，相关入口块和本六路径无登记写入交集，保留其全部记录。technical现已交小时准备、src只读且效果blocked；remote-core已paused并保留T5/T6等未解决证据，本修复不宣告其R1—R8关闭。reader暂停研究；地图/市场观察维护各自页面块，本线只改BacktestPage状态显示，不进入App/TopNav或市场页。未登记任务状态未知，记录不是锁，后续发现重叠先协调。

原dot-pro-strategy-definition和dot-pro-increment-review继续paused；宏观只补到旧CSV而资格blocked。公式/时间独立工具已交，不因本项重开旧审查。适用技术基线AGENTS、现行current-standards实际索引及COORDINATION.md；这是已审缺陷修复，不改研究合同、定义、报告登记或原冻结结果。

新增市场实验/拟合/行情下载/付费为0；仅合成记录及现有测试，不上传行情、账户资料、原文、凭据或大包，无模型权重。历史预算与负结果保持。
技术基线.github/workflows读取404；协调既有根树无.github，外部自动化未知。发布前核准确路径、diff/大小/敏感形态及自动化；非force推送，竞态先fetch再审差异，不改其他任务，不推main/master、不合并、不部署。推后核完整commit及原文读回后才开始实施或声称同步。

本版新增：只登记已审状态计数缺口、六文件及保持旧API数值字段的兼容方案。下一步：读回本登记→按上述范围实施→交最小独立验收和准确小文件清单→授权分支发布并更新证据索引；不得以“已登记”冒称修复完成。
