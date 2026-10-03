# 六类市场理解：阶段成果与恢复入口

本轮把“专业投资者在看什么”整理成可操作的六类问题，并补了宏观、行业、经营与估值的读法。现在保留50组原目录，共20张详细解释；用户可以按A股/美股、趋势/定投/价值找到组合读法、反例、频率和已有图表入口。**这代表页面与说明完成，未代表新增市场数据接通、投资效果或线上收益。**

仓库 https://github.com/lige1687/biao-signal-system ，分支 `task/investor-observation-map-progress`。基础完整commit `157b09a3c5fc8515b587049b633d3a0d95c10830`。本文件所在成果commit由 `git log -1 --format=%H -- docs/archive/handoffs-plans/market-understanding-fundamentals-2026-10-03/README.md`定位；发布后的准确SHA以coordination/lei的investor-observation-map.md为准，须再次核实际远端。同步不是接管，原负责人继续。

阅读顺序：本页 → validation.json → review.md → manifest.json/SHA256SUMS → spec/plan → 自身进度。原始需求原文和旧证据沿 docs/progress/investor-observation-map.md、第一版阶段目录保留。本轮确认原文：“你说的这些感觉没啥问题，去推进的做哈”。

## 已完成与未完成

- 六类问题：宏观、行业、企业经营与估值、资金与杠杆、ETF产品、事件；每类中美重点、三个组合问题、更新节奏、图表入口和缺项。五个共同阅读问题：位置、方向、预期、相互验证、价格反应。
- 新增M13–M20：PMI/订单、利率、物价、行业供需库存、收入利润、现金流负债、估值分母、盈利预期。基本定义引用官方公开教育资料；组合建议与反例是人工编写的解释，未作投资有效性实验。
- 现有图表通过准确页签复用；A股行业页与美股11行业ETF图分别链接。原页面/接口无修改。01与48–50只在全部目录展示，不伪装为资金或ETF产品属性。
- 真实observations后端尚未在本任务分支整合，接口缺失时明示未接通。FINRA/CFTC、行业经营/指数财报/历史盈利预期、事件日历等真实数据未新接入。不能从20张说明卡推断有20项实时读数。
- 本轮未整合他人分支、未合main、未上线；全新依赖安装、Linux/Windows、真实上游与用户效果未验证。生产或付费权限不继承。

## 恢复与最小检查

在已核目标远端的独立干净检出目录恢复此工作分支，不切换其他任务脏区。先fetch最新coordination/lei，核本任务准确成果SHA和范围，确认新版是否已解决旧缺口。以下以仓库根目录为工作目录，不依赖Air路径：

```sh
git rev-parse HEAD
shasum -a 256 -c docs/archive/handoffs-plans/market-understanding-fundamentals-2026-10-03/SHA256SUMS
cd web
npm ci --ignore-scripts
npm run test:market-understanding
npm run build
node ../docs/archive/handoffs-plans/market-understanding-fundamentals-2026-10-03/restore-smoke.mjs ..
cd ..
python3 docs/archive/handoffs-plans/market-understanding-fundamentals-2026-10-03/browser-fixture.py --root . --port 8774
```

预期：文件校验相符、33项检查通过、构建退出0。恢复smoke把独立内容模块和原目录复制/编译到仓内.biao的独立临时目录，离开源码目录用Node内置模块验证两市场目录、现金流搜索、FINRA隔离、融资入口、个人计划分类；不依赖浏览器/服务/API。它不证明全新Node依赖安装或全应用跨系统可用。

浏览器访问 `http://127.0.0.1:8774/market-understanding?fixture=missing`（观察接口未接）或`?fixture=normal`（人工数据，有横幅）。实际页面在六类间切换，搜索现金流/两融，切换美股行业，点美国宏观入口；仅目标页签被验证，其他数据API故意禁用，不能用空图冒充真实图表通过。结束自有夹具可访问 `http://127.0.0.1:8774/__finish`。复制文件不会迁移其他进程或登录态。

环境实测：Darwin、Node22.22.1、npm10.9.4、Python3.11.7；web/package-lock.json SHA256 `f3e7050e244c4dd3dfae0d3f4b6545aaf5e8e92e07e784b52d81b7ed4cbd8013`。本轮复用此前正确lock安装的node_modules，不写全局环境。纯内容与合成检查无需密钥、环境变量或数据授权；真实服务所需配置仍按项目原规范提供，未交任何密钥。

## 证据与后续

validation.json记录退出码/限制；software-checks.txt为最后一次回归与构建输出；浏览器TXT为页面实际内容，PNG为桌面/390px；review.md记录两项修复及三类验证失败。manifest每项含路径、大小、SHA，SHA256SUMS另包含manifest本身。旧第一版的原目录/12卡/观察adapter及证据原封不动。

原策略两SHA本轮与configs批准值一致：技术体系`df92d85b3b04ed3ab71d56bc108d0effe8eb31051b7a1531eda59edcbf0aab20`、技术实现`85e0e3270ff96fe85247756805c58c650a0e83b21ea15c9feccea84d31aaf903`。不上传原件。无数据库/权重/受限行情交付；本轮不需要这些材料。旧仅本地两个中间文件仍未上传，旧包与数据缺口沿原清单。

下一步限定为先核已发布观察后端与本分支的依赖差异，再确定一个有来源许可、可用时间和口径依据的数据缺口；尚未启动真实取数、合并或新实验。情绪三用途、技术风险、dot状态计数、外部工具与经典学习继续避让。不得重跑旧AAII/QQQ/VXN/宽度/技术结论。

本阶段公开来源4次（3成功、NBS1失败，无重试）、新市场实验/拟合/付费0。旧12/12预算不重置，前一轮讨论2批网页请求单列而不猜页面次数；其他任务18/18不可挪用。三个Sol助手已结束，两个自有预览服务已通过/__finish退出0，无实验checkpoint或后台推进。原共享HEAD/分支/index/AGENTS指纹与开工一致。
