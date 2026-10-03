# 市场理解合并与彩色参考线

2026-10-03，Asia/Shanghai。用户本轮要求“参考线也要表明是机会还是风险……颜色来一点”并“和……基本面页面合并……统一搞到市场理解”。原负责人继续；本轮基础58baf916d14fbf536a024cced48edd3f118111f6；成果commit以本文件所在提交和协调记录为准。

本轮完成的是展示与入口：原基本面五个内容区与数据总览统一成六分区。旧/fundamentals保留搜索参数和合法分区hash跳转，默认保留原市场区；新入口默认总览。浏览器前后退、刷新均根据URL切换。资讯与认知下重复入口移除；原宽度、情绪、ETF强弱、长周期叠加、利率、位置/相关性卡、中国/美国宏观组件保留。

总览参考线继续使用MARKLINES原数值，增加颜色、方向和原因：绿为机会观察/环境支持、橙为留意、红为风险压力、蓝为分界/结合判断；值低与值高哪一侧有含义写在线上。图下与大图说明解释如何结合资料，定义/经验/固定历史分位身份保留。VIX恐慌机会不等于抄底，利率与通胀须结合经济背景；没有新增买卖规则或已验证收益结论。

旧美国CPI卡和抽屉不再沿用CPI2“联储目标”或旧误导分区；用已有总览解释，抽屉标题直接注明2%经验参考。共享zones与源未改。旧中国宏观“美国就业尚未接/需FRED key”占位改为现有美国宏观链接。其他历史口径未做全量科学重审，不能宣称全部旧研究已验证。

恢复：核本阶段SHA256SUMS后，在成果commit的web目录执行 `npm ci`（本轮未新装）、`npm run test:market-dashboard`、`npm run test:market-understanding`、`npm run test:market-integration`、`npm run build`。运行 `LEI_API_PROXY=http://127.0.0.1:8000 LEI_WEB_PORT=5185 npm run dev -- --host 127.0.0.1 --strictPort`，需要自己有权使用的原市场API；无数据时保留空项。Node22.22.1/npm10.9.4，Darwin；不承诺后台、干净安装或跨OS恢复已验证。

验收见validation.md；实现顺序及准确文件见docs/superpowers/plans/2026-10-03-market-unification.md。跨任务先读取最新coordination/lei:COORDINATION.md与docs/coordination/tasks/investor-observation-map.md。范围登记453a4efbde5c4d636339972f76045bf6703f6552、CPI补充e415137fb2fa559480555290d40bdfeee90d8244均先推并读回才实施。

代码/小文档/合成测试入Git；市场截图仅本地不公开，数据库/原行情/策略原件/密钥/权重没有复制。旧封存结果不变；0新金融实验/拟合/外部来源研究/付费。本轮无新子代理。上轮预览PID49578/session59800仍供本地阅图，仅127.0.0.1:5185；用户5173/8000未动。没有研究checkpoint或接管授权。

仍有数据缺口：A股PE与股债收益差历史、商品、部分ETF/位置/相关性源；不同原接口更新链路和口径没有改，不能当作所有快照/历史值已逐项对齐。FINRA/CFTC等新源未加。下一步仅此统一页的具体阅图反馈；新增来源需先登记具体范围和资格，未认领全部缺项。
