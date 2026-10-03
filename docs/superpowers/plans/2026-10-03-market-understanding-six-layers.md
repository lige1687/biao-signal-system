# 市场理解六类问题实施计划

> 按 subagent-driven-development 分工执行：主控写页面/分组；独立助手只写新解释JSON；只读助手核现有图表入口。用户已批准实施，不重复询问。

**Goal:** 让读者从六类问题找到专业投资者常看的资料、读法与系统现有图表。

**Architecture:** 旧内容与观察适配保持；新six-layers.ts做明确目录映射与纯筛选，新fundamentals-reading.json提供8张解释。页面前置六类问题与组合阅读，再展示事实和完整目录，深链复用基本面。

**Tech Stack:** 现有React/TypeScript/Vite、React Router；无新依赖。

## 全局约束

只做解释展示层；不触发交易/来源抓取/数据修订/冻结研究。基线157b09a3c5fc8515b587049b633d3a0d95c10830。旧证据目录不改。源码、策略指纹及协调证据绑定spec与新phase README。

## 1. 解释材料与可复用入口

- [x] 只读核当前FundamentalsPage的fund-sec-market/rates/overlay/macro/usmacro及市场限制，记录行号。
- [x] 新增JSON：schema为cards[]及sources[]；卡保留原Card字段并加layer宏观/行业/经营分组。ID M13—M20，不碰旧JSON。
- [x] 每卡：指标定义/更新周期/高低与变化/组合/反例/阈值/覆盖及限制；明确文字建议与来源定义的区别，缺数据不展示数值。

## 2. 六类组织与页面

- [x] 新增six-layers.ts，导出LayerId、layers、layerOrder、catalogueLayers、readingCards、readingSources、filterCatalogue、filterCards。旧50行可多重索引，全部模式保留全部。
- [x] 页面使用六类按钮，默认macro；方法切换按既定order选首类，用户可再选任一类。all恢复完整目录。搜索从全部开始检索，避免隐藏所搜内容；市场不匹配仍过滤。
- [x] 类目面板包含问题、三个组合检查、更新节奏、现有图表链接、明确缺项；五个阅读问题用同一小型说明区。新增解释使用既有details卡，不重造图表。
- [x] 现有observations请求/单位/日期不变；重排事实区，保留错误、0、空资料状态。

## 3. 验证与同步

- [x] 回归增加：单市场不可渗漏、事件有卡无旧目录也不误报、搜索两融/现金流、方法顺序变化不改内容、所有链接指向现存页签、50原目录ID/证据未变。
- [x] 在web执行 `npm run test:market-understanding`、`npm run build`，保存退出码；旧22检查纳入同次运行。
- [x] 用旧browser-fixture.py服务新dist，检查六类/搜索/市场/方法/展开/失联/390px；合成数据标注，无生产数据调用。新证据落docs/archive/handoffs-plans/market-understanding-fundamentals-2026-10-03/。
- [x] 只核有意义的实现风险，修复后跑相关检查；生成manifest及SHA256SUMS，独立临时恢复最小静态检查。
- [ ] 更新自己的两进度，精准暂存/检查大小与敏感资料；推工作分支核完整SHA，更新自己的协调记录并读回。保留旧失败及未验证项；不合并、不部署。

实施/检查已完成；最后同步回执由coordination/lei自己的任务记录给出准确commit，不能凭本地勾选当作已推。两项审查修复、夹具路径失败和检查器限制见本阶段review.md。
