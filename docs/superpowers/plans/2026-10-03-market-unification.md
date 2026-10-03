# 市场理解统一入口与彩色参考说明 Implementation Plan

**Goal:** 按用户明确要求，把原基本面五分区统一到市场理解，并给现有参考线添加机会/风险/条件解释与颜色。
**Architecture:** 统一页负责URL分区；原FundamentalsPage增加受控嵌入方式，保留内部五分区组件。数据总览沿用已有图表模型，参考解释独立为小模块。旧URL保留search/hash跳转，新旧入口不是两套页面。
**Tech Stack:** 现有React、React Router、React Query、ECharts；不加依赖。

范围来源：用户本轮原话“参考线也要表明是机会还是风险……颜色来一点”“和……基本面页面合并……统一搞到市场理解”。已明确实施授权，不再重复请求布局批准。基础58baf916d14fbf536a024cced48edd3f118111f6，scope已登记并读回453a4efbde5c4d636339972f76045bf6703f6552。

## 约束与设计选择

- 采用六分区：数据总览、市场宽度与情绪、利率与估值、长周期叠加、中国宏观、美国宏观。复用全部五个旧分区；只放一个链接不足以合并，整页重写则增加丢功能风险，均不采用。
- `/fundamentals` 默认跳到原市场分区；带合法旧hash时保持相同内容。新页无hash默认总览。刷新、浏览器前进/后退从URL读真实选择；未知hash回到各入口默认分区。保留search。
- 绿色代表机会观察/环境支持，橙色留意，红色风险压力，蓝色定义/双向条件。文字给出方向及配套判断，不能仅靠颜色。估值低与收益差高方向相反；VIX高既有高波动风险，也可能有恐慌后的机会，不能直接标买入。基本面仍为叙事层。
- 数值复用MARKLINES，不调整阈值、技术规则、共享zones或已有研究。身份保留定义线/经验线/固定历史分位。原基本面已有的历史口径保留，不能声称全页旧科学措辞已审完。
- 权威策略指纹沿本轮实读与上一阶段相同；服务策略3.7宏观仪表盘和4.1基本面定性。0新金融实验/来源研究/付费；只读本地现有数据，不强制刷源。

## 执行与验收

- [x] 路由/导航：新增features/market-understanding/navigation.ts映射纯函数，MarketUnderstandingPage使用useLocation/useNavigate；App的旧路由改兼容redirect；TopNav移除重复基本面链接。合成核全部旧hash、未知/空hash、search。
- [x] 嵌入原页：FundamentalsPage增加section属性，受控时隐藏旧标题/nav，用小刷新条保留刷新功能；查询按所属分区enabled，保留原内部组件、抽屉和日期源。各分区只显示自己错误。
- [x] 参考解释：新增reference-reading.ts返回tone/label/explanation；dashboard-model.referencesFor沿原数值与身份附加解释；总览图线/图例/展开说明使用同一对象和颜色。缺数卡仅显示参考定义，不能给当前机会状态。
- [x] 验证：`cd web && npm run test:market-dashboard && npm run test:market-understanding && npm run test:market-integration && npm run build`；浏览器核原链接→对应区、新页总览中美、五旧区可达、前后退、放大、颜色和390px。旧归置器问题原样报告。
- [ ] 只把本任务准确代码/小文档推独立工作分支；协调仅更新自身记录并读回。真实截图只本地，原共享工作区和运行服务保持。

下一步只按以上范围内联执行；没有新代理派发。结果、失败、未验证项写本阶段证据和原两进度文件，不覆盖旧封存证据。
