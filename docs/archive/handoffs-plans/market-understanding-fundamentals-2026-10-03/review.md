# 独立核对与修正

基础157b09a3c5fc8515b587049b633d3a0d95c10830，实施范围协调b8abece953e9ce8aaf3c46dfe806ef1f121466a9；所有助手为Sol medium，0网络/0市场实验/0提交。主控检查关键差异，不重跑投资研究。

1. fundamentals_reuse_audit只读现有FundamentalsPage:1961–1985、2093–2143，核五个hash页签；SectorsPage:57–64、125–168、319–405为A股重点/自选，不是美国行业。美国11行业ETF相对SPY在FundamentalsPage:1637–1689。已按市场分链接。hash只选页签，不选单图；原页挂载时读取，因此用普通内部链接进入。
2. fundamentals_reading_content只写新fundamentals-reading.json，8卡/4来源，自核JSON与字段；主控修了PMI改善但仍收缩、现金流与余额、未接指数收入的表达，没有修改旧50条证据。
3. six_layer_review独立检查spec/代码/读法发现2个Important：01技术底座与48–50个人计划不应被强归资金/产品；13融资余额泛链落在没有融资图的market分区。已修为上述4项仅all可见、13指向overlay，33项最终测试覆盖，实际浏览器看见对应链接与目标分区。02/03市场宽度仍属于“谁在参与”的问题，不称其为杠杆。无其他Critical/Important。没有反复增加审查轮次。

## 验证中遇到的失败

- 一次编辑命令以web/为工作目录却使用web/前缀，文件未找到，未发生预期编辑；随后测试只执行旧22项。明确不把它当新增检查通过。纠正根目录并加set -e，之后33项通过。
- 浏览器以button角色定位原生summary失败；读回DOM后用可见文本+Enter，展开成功。不是产品缺少键盘支持。
- 旧browser-fixture.py只服务/market-understanding，首次图表跳转无法验收。新phase复制夹具仅增加/fundamentals路由，其他API仍503禁用；美国宏观、长周期叠加页签导航验证成功，真实图表数据未验证。旧夹具与证据未改。
- 归置检查仍exit1：原生worktree的.git文件和用户指定既有docs/progress目录触发旧白名单。检查器SHA与基线一致，没有新增归置警告，没有冒称全绿。
- 构建仍有既有大包警告；本轮不扩展打包重构。
