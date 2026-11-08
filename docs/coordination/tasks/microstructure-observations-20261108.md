# 微观结构观察补齐
- task-id microstructure-observations-20261108; owner 01a1ba80-0b9f-77e2-ab15-bc940cb3d22d/root; status active; updated_at 2026-11-08T18:56:36.602952+08:00; scope_released=false.
- 用户明确要求补齐前轮全部辅助观察。服务市场背景层：融资股票占比、换手分位、日集中度、期权IV/PCR、期指年化基差、逐股相关离散；VIX期限直接复用。无交易规则/资金动作/付费/删除/强推。
- checked_coordination_sha 5a4a871be6cb36b11acea74b11d8346e6ee7a109; 已读 COORDINATION、trae-observation-integration-20261108、breadth-reading-aid-20261101、sector-crowding-advice-review-20261102、market-increment-map-20261102、research-dispatch-controller。原前端范围已释放；其他研究不接管。
- 基线 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9 加共享dirty。当前成果尚未产生。无已推源码提交。
- root唯一写上面三共享组件、同目录新增MicrostructureObservations.tsx/microstructureData.ts/microstructure.css/microstructureData.test.mjs；web/public/research/microstructure-observations-20261108/**；src/lei_signal/market_context/microstructure_*.py；tests/unit/test_microstructure_*.py；本任务docs/ops目录与work-progress/microstructure-observations-20261108.md。子任务按唯一后缀分别写derivatives/funding/equity文件；root等待释放再验收。
- 新数据/计算输出 /Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108，已核固定UUID DEBA1C85-6059-3865-B50A-A8EE1F80E4D9；旧原件只读。本机预计新增不超过30MiB，外盘150MiB。来源优先复用登记资料，不扩原历史采集/实验预算。新实施来源获取每分支最多30个HTTP对象（含失败），一操作最多一次重试，失败真实保留；不是新收益实验预算。
- 验收：来源和历史适用范围、同日分子分母、停牌缺失处理、无未来分位、独立算术复核、TS与定向测试、桌面真实UI图表/详情/空缺/收起恢复。不得用有组件替代有合格数据。
- 下一步预检并续派原3个代理，root负责UI接线与独立验收；阻塞只限所缺指标，独立工作继续。
