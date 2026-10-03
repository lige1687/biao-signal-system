# 图表优先修订：恢复与证据入口

更新时间：2026-10-03T20:55:00+08:00（Asia/Shanghai）。原负责人继续，非移交接管。基础commit `959971e30893c0894837b4c2b35442e4bedb1aac`；准确成果commit见本文件所在提交及唯一协调记录，不把基础当成果。

用户纠正：页面应与原基本面一致，直接看当前数据图和阈值，A股/美股分别看。已替换引导为主体的页面；原50组目录和20项读法数据文件保留，旧页面可从基础commit找回。本轮未增加行情源或技术买卖条件。

阅读顺序：本文件 → [需求修订](../../../superpowers/specs/2026-10-03-market-dashboard-revision.md) → [实际验证](validation.md) → [进展](../../../progress/investor-observation-map.md)。后续开始前读取远端 `coordination/lei:COORDINATION.md` 与任务记录；不要重启封存研究。

实现：`web/src/features/market-understanding/{dashboard-model.ts,MarketDashboard.tsx,dashboard.css}`，页面入口 `web/src/pages/MarketUnderstandingPage.tsx`。复用共享TrendChart及MARKLINES数值，但不改原文件，也不使用其买卖暗示色带。24唯一指标，A股9项/美股16项（中美利差共用）；按市场隔离、自己的日期和单位显示。当前服务A股7项、美股16项可画；A股PE与股债收益差接口空缺，不填假值。最新已取得不代表首发时间或最新市场确认。

## 复现命令与前置条件

在本仓库正确成果commit，先校验本目录 `SHA256SUMS`（路径相对仓库根）。需Node22/npm10与项目已授权市场API服务。依赖由 `web/package-lock.json` 固定；本轮版本22.22.1/10.9.4，Darwin。新安装用 `cd web && npm ci`，**本阶段未新安装或验证Linux/Windows**。

```sh
# 从仓库根执行
shasum -a 256 -c docs/archive/handoffs-plans/market-understanding-dashboard-2026-10-03/SHA256SUMS
cd web
npm run test:market-dashboard
npm run test:market-understanding
npm run build
# 使用自己已有授权的市场API；没有则页面会明确缺数
LEI_API_PROXY=http://127.0.0.1:8000 LEI_WEB_PORT=5185 npm run dev -- --host 127.0.0.1 --strictPort
```

打开 `http://127.0.0.1:5185/market-understanding`。三个只读请求：`/api/fundamentals/rates-history?lookback_days=1095`、`/api/fundamentals/macro-history?page_size=60`、`/api/fundamentals/us-macro`。不传强制刷新参数。真实backend的安装、数据许可、缓存和源访问不能假定由本前端交付继承；完整后端离线恢复未验证。

## 材料、预算与边界

代码/小文档/合成测试入Git。实时响应正文、市场曲线截图未上传公开仓库；本地截图仅供本用户查看，非恢复必需。未复制账户、密钥、数据库、权重或桌面策略原件。无新模型/训练数据。本轮两名Sol中思考助手只核接口、阈值及合成测试/一次实现审查，已结束；无新的金融拟合、全量回测、网络资料研究或付费预算，旧封存预算保持。

自有前端预览5185（PID49578/session59800）仍运行，只监听127.0.0.1，留给用户阅图，非上线；原用户服务5173/8000未动。没有研究进程/checkpoint。未来维护仅本图表页/模型/测试；FINRA、CFTC、情绪、宏观源资格、技术因子等未认领。唯一协作记录为 `docs/coordination/tasks/investor-observation-map.md`，进展文件不是锁。线上收益与用户理解效果均未测量。
