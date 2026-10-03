# 市场理解第一版：代码与验证入口

## 一句话结论（大白话）

市场观察清单已经做成独立页面：主导航的“市场理解”可按A股/美股、趋势/定投/价值阅读50组目录和12项详细解释，明确哪些只有说明、哪些真的有数据。页面和合成检查已完成；新的真实数据源、此分支观察后端整合及上线没有完成，使用理解和投资收益未测量。

## 已交功能

- 新路由 `/market-understanding`、看盘旁常驻入口；8主题、10类投资者目的、50组目录、搜索与三种阅读顺序。
- 12项完整解释：高低位置、升降、组合检查、反例、阈值身份、定义/频率/来源限制。事件采用不同标签。
- 对已发布9项观察接口的只读兼容层：CN/US分别处理，零与缺失分开，所属期/发布/取得时间分开，固定历史标记；错市场、错单位、不一致状态拒绝展示。
- ETF按显式资产范围、交易币种、结构给检查顺序；默认未知，未读取私人账户或冒充核实具体ETF。

## 版本与分工

实施基线 `d58a0740502207ca6dfeb9c9f18b1c135aa54632`；本目录属于 `task/investor-observation-map-progress`，准确成果提交用 `git log -1 -- docs/archive/handoffs-plans/market-understanding-ui-2026-10-03/README.md` 查询。规则读取8778bd3f、范围登记c4ec1ccd，推前增量核至6b9861b2，完整值见validation.json。

原market-observation的观察组件/CPI/日期、情绪/宽度因子与完整技术策略研究均未改动。两名Sol medium助手分别整理既有内容和定点审阅，内容助手另修已发现边界；没有新市场研究。计划、审查问题与修复记录一并保存。所有源头策略原件留在原位置，指纹与实施计划一致。

## 恢复与验证（工作目录均为本仓库）

在独立检出本分支、先核commit与manifest/SHA后执行：

```sh
cd web
npm ci --ignore-scripts --no-audit --no-fund
npm run test:market-understanding
npm run build
cd ..
python3 docs/archive/handoffs-plans/market-understanding-ui-2026-10-03/browser-fixture.py --root . --port 8773
```

浏览器打开 `http://127.0.0.1:8773/market-understanding?fixture=normal`。这是实际构建页面搭配**人工测试资料**，顶部有提示。另可选empty、missing、wrong、failure、inconsistent、slow场景。只监听本机，不接真实服务/数据库/外部网站。用该服务的`/__finish`正常结束；复制文件不会迁移进程。脚本依赖Python标准库，前端按package-lock安装；Node22.22.1、npm10.9.4、Python3.11.7与Darwin已测，其他系统未测。

本次22项边界检查和最终构建退出0，浏览器检查通过，证据见validation.json、原始可访问性文本及图片。较早缺陷修复后只重验受影响内容，没有重新跑金融实验。通用归置检查**未全绿**：旧检查器将原生worktree的.git文件及用户要求的既有docs/progress目录报错；检查器与基线字节相同，本次不越界改公共工具。新增文件按本计划准确路径审阅，无新增归置问题，不把此事实改写成通用检查通过。

## 接现有服务的边界

本页消费 `GET /api/fundamentals/observations?market=cn|us`，兼容契约来自market-observation的 `55d8aa96b45d97b09901ded4ebf78f490bbb7f6b`。当前任务分支**未包含该后端**；启动此分支后端不能据此声称资料接通。页面遇404会说明未接通，静态说明可正常阅读。未来与原负责人整合需核准确版本和最小接口检查，不直接复制共享脏文件或自动合入main。

真实服务可用并明确允许取数时，可在`web/`使用`LEI_WEB_PORT=5177 LEI_API_PROXY=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1`。这会访问指定后端，其可能触发上游取数；本次未执行真实来源冒烟，不能把人工接口检查当真实数据验收。无需向Git提供密钥；来源许可另核。

## 尚未完成与下一步

1. 与原观察接口负责人核整合点并验证真实只读响应；保留双方原模块职责。
2. FINRA月度余额、CFTC分类头寸、具体ETF成本/跟踪资料和事件日历仍只有说明及来源规格，尚无新实时接入。逐项核范围、时点、持续取得及使用许可，不能把候选全部圈为独占任务。
3. 五组混合市场目录保留原文A/美标签、按整组显示；以后如拆子项须保留50组原ID与证据，不改封存原件。
4. 用户理解改善未测；真实投资增量未测。此页不产生买卖操作或LEI硬过滤。

旧源调用12/12、市场实验/拟合/付费0不重置；本轮新源调用0。AAII/NAAIM原始资料、策略原件、数据库、权重与任何凭证未上传。仅代码、自写小文档和人工界面证据入Git。最终预览服务已正常结束，无本任务运行中的实验或checkpoint，原任务责任仍active。

## 证据文件

- validation.json：实际命令/退出码、环境、通过和未验证项。
- review.md、task-1-report.md：缺陷、修复与内容出处。
- manifest.json、SHA256SUMS：交付文件内容指纹，不覆盖旧阶段manifest。
- market-understanding-preview.png、mobile-map-preview.png：最终知识页面；其他带synthetic的截图均为人工资料场景。

未纳入发布的review-package.txt是临时重复源码审查包；mobile-synthetic.png为初次视口调整时无完整正文的中间截图，不作为验收证据。二者仅本地保留，未删除资料。
