# 已审问题落地：回测记录状态计数纠正

- task-id：dot-trade-state-accounting（新独立修复项；不替换三条 Pro 研究记录）
- 负责人：当前 dot LEI 接续主控；本线实施与独立验收，协调记录由本方唯一写入者维护。
- 状态：blocked（候选v2已通过局部功能复核；完整验收等待测试依赖安装授权，代码尚未发布）
- 更新时间：2026-10-03T12:09:00Z，Etc/UTC
- 目标：修正已审 IR-R02 的状态计数缺口：未实际入场/无效记录不能被显示为真实持仓，旧历史载入不能把不确定记录装作已核准。
- 用途：回测摘要和历史显示准确性；不改变策略、入场退出、收益或资金路径，不开展新策略研究。
- 验收：总数守恒，真实open与invalid/skipped/unknown分开；收益closed样本及全部R/回撤等其他指标保持；旧JSON无写盘、旧API数值字段兼容；UI准确显示纠正计数或“未核实”。

## 基线、成果与精确写入范围

计划工作分支：codex/lei-trade-state-accounting-20261003（尚未创建）。
实现基础完整commit：3e348e6fa49cdd399e9838f252a2c0c1f411c8c1，task/technical-factor-sequence-progress最新ref已核相同；较3deaad7a1724228780a62af49cf34fc046b0640a仅12文档/JSON变化。实现者已逐项核service、metrics、engine、BacktestPage及types五个blob未变，缺陷仍存在。
最近已推本任务代码成果commit：无；六文件候选v2仅本地，远端不可复现；没有已推代码或可合并结论。候选manifest SHA256 248fa928679a6612c20ca9beb39781b86dd05af99c61e8a3d6c78ad33c0a3b08，补丁SHA256 3fd893e1585cdb3ff6544024e14aadec6fa31be48eb855d4a8513944f1e56f27。协调自身commit按本路径Git历史定位。

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

登记a8c54ea0141e00b9f7ee45f4b068301b0524cb2a成功读回后实施，当前仍严格六文件。v1独立检查发现两个阻断：矛盾结束状态误判为确定类别、只核closed漏检非closed记录被截断；v2均已修并复验，失败历史保留，没有改收益样本或引擎语义。

已通过：20项专测及独立7项合成对照（有覆盖重合，不相加成27种保证）；110组新旧其他财务指标对照；10个原测试函数体用等价合成fixture直接断言（不是完整pytest）；实际UI helper的独立6输入/两使用点检查；补丁在准确基线上apply --check；六路径、原后SHA/Gitblob核对。旧JSON前后字节和旧open_count保持，新增纠正字段可解释unknown/未核实。回执文件名为candidate-v2-manifest.json、command-receipt-v2.json及独立review-result.json，均仅本地，未作为代码成果公开。

未运行/受阻：完整pytest收集、TypeScript/Vite构建、React/浏览器实际渲染及完整Git检出的归置检查。原尝试分别因pytest/tsc缺失、非完整Git检出失败，日志保留，不能写通过。已请求在自有云端安装锁定依赖的授权，当前待答复；未安装、未运行市场数据或部署。局部功能复核仅接受为草稿候选，不是completed/ready-to-merge/生产可用。

当前只整理六文件待发布材料；等待依赖授权及主控明确发布安排后再做被允许的完整验证。若失败需返修，仍限六路径和原兼容合同；范围变化先登记。无授权不绕行安装，不因等待转开新任务，不扩大市场计算。

## 归属、规范、预算与同步

fresh协调基线b2bcdb6d11d43835a474400f985bbd2acaa38d9b，COORDINATION.md v1.0/blob126a1a01cd09439536c69fdd7264e3e292e4b852未变，本task未有第二写入者。最新technical只新增独立风险research适配/定义卡，明确避让本backtest六路径；external在其人工搜索目录，sentiment在AAII研究目录，market-observation已archived。其增量全部保留，不把暂停/归档视作接管授权；本线不宣告remote-core R1—R8关闭。未登记活动未知，记录不是锁。

原dot-pro-strategy-definition和dot-pro-increment-review继续paused；宏观只补到旧CSV而资格blocked。公式/时间独立工具已交，不因本项重开旧审查。适用技术基线AGENTS、现行current-standards实际索引及COORDINATION.md；这是已审缺陷修复，不改研究合同、定义、报告登记或原冻结结果。

新增市场实验/拟合/行情下载/付费为0；仅合成记录及现有测试，不上传行情、账户资料、原文、凭据或大包，无模型权重。历史预算与负结果保持。
技术基线.github/workflows读取404；协调既有根树无.github，外部自动化未知。发布前核准确路径、diff/大小/敏感形态及自动化；非force推送，竞态先fetch再审差异，不改其他任务，不推main/master、不合并、不部署。推后核完整commit及原文读回后才开始实施或声称同步。

本版新增：登记候选v2、两项实际失败及修复、局部通过证据和完整验收待授权；代码未发布，工作未结案。下一步等明确授权/发布安排，不新增报告或项目。
