# 图轴范围补充 2026-11-08T19:39:17.089652+08:00
- 实际UI验收发现历史分位图自动缩放到0—18会弱化其0—100绝对含义。追加唯一写MarketTrendChart.tsx可选valueBounds参数，默认undefined保持既有图行为，仅Microstructure分位图传[0,100]。备份当前文件字节；不改首页默认项/布局。

# 范围追加 2026-11-08T19:22:50.656758+08:00
- 首页分类负责人已完成并明确释放，本任务仅追加indicatorCatalog.ts中MICRO_INDICATORS已验收条目；不改变默认四卡、选择持久化、index布局。初始catalog备份在本任务before/。
- root已独立复核derivatives10卡与equity64卡：源hash、同日算术、完整性门禁、复权后逐股相关独立公式、行业56个此前756日分位。融资当前21日仍验收。
- 为完成融资历史分位新增有界工程获取：仅旧于2026-10-08的官方同口径日，最多1500 HTTP/300MiB/12分钟/并发4，目标包含现有21日共271日；原金融实验预算不变。历史获取代理不改当前21日原件或funding代码。

---

# 范围更新 2026-11-08T19:05:46.876786+08:00
- 仍 active，数据与独立组件验收继续；根据用户在首页布局会话的明确协调授权，index.tsx/selection.ts/CandidateShelf.tsx/useSelection.ts/style.css写入权释放给trae-observation-integration-20261108（01a1ba4c-f7c4-7de2-b51d-9552681be8c4）。自己加的index两行已精确撤去，与本任务起点备份相同；未触碰他人修改。
- 本任务只保留MicrostructureObservations/microstructureData/microstructure.css/测试，新3分支数据及后端builder/测试、自己的ops文档；组件提供selectedIds可选过滤。分类/默认首页由指定会话统一集成。
- 工程取数预算调整：equity最多100个公开HTTP对象/50MiB（行业板块多项历史），funding最多130对象/50MiB（必要时SZ单日分页），derivatives仍30对象/50MiB；无收益研究预算扩大。原件只增不删。

---

# 微观结构观察补齐
- task-id microstructure-observations-20261108; owner 01a1ba80-0b9f-77e2-ab15-bc940cb3d22d/root; status active; updated_at 2026-11-08T18:56:36.602952+08:00; scope_released=false.
- 用户明确要求补齐前轮全部辅助观察。服务市场背景层：融资股票占比、换手分位、日集中度、期权IV/PCR、期指年化基差、逐股相关离散；VIX期限直接复用。无交易规则/资金动作/付费/删除/强推。
- checked_coordination_sha 5a4a871be6cb36b11acea74b11d8346e6ee7a109; 已读 COORDINATION、trae-observation-integration-20261108、breadth-reading-aid-20261101、sector-crowding-advice-review-20261102、market-increment-map-20261102、research-dispatch-controller。原前端范围已释放；其他研究不接管。
- 基线 codex/factor-unit-research-20260915@18e64fa632dba5dbad0e5fcae09b4ccc75f119a9 加共享dirty。当前成果尚未产生。无已推源码提交。
- root唯一写上面三共享组件、同目录新增MicrostructureObservations.tsx/microstructureData.ts/microstructure.css/microstructureData.test.mjs；web/public/research/microstructure-observations-20261108/**；src/lei_signal/market_context/microstructure_*.py；tests/unit/test_microstructure_*.py；本任务docs/ops目录与work-progress/microstructure-observations-20261108.md。子任务按唯一后缀分别写derivatives/funding/equity文件；root等待释放再验收。
- 新数据/计算输出 /Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108，已核固定UUID DEBA1C85-6059-3865-B50A-A8EE1F80E4D9；旧原件只读。本机预计新增不超过30MiB，外盘150MiB。来源优先复用登记资料，不扩原历史采集/实验预算。新实施来源获取每分支最多30个HTTP对象（含失败），一操作最多一次重试，失败真实保留；不是新收益实验预算。
- 验收：来源和历史适用范围、同日分子分母、停牌缺失处理、无未来分位、独立算术复核、TS与定向测试、桌面真实UI图表/详情/空缺/收起恢复。不得用有组件替代有合格数据。
- 下一步预检并续派原3个代理，root负责UI接线与独立验收；阻塞只限所缺指标，独立工作继续。

- 追加有界近期美国固定池报价取数：原502成功名单，2026-08-25至11-06，独占equity/us-recent，600 HTTP/30MiB/8分钟/并发4，遇429停止。融资工程上限160对象/50MiB用于21日MA20。原研究预算无扩展。
