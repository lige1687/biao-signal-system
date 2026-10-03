# 市场理解基础与宏观解读实施计划

> 执行者：本负责人按已获用户授权在当前隔离工作树执行，不新派代理。

Goal：可信参考、指数对照、宏观解读和三项有界发散形成可使用流程。
Architecture：React Query只读旧API，纯模型完成对齐/统计；ECharts显示；Agent入口复用同一模型。
Tech：React18/TS5/Vite5/ECharts5，无新依赖。

- [x] 基础：reference-evidence.ts提供官方定义/来源和历史分位；dashboard-model.referencesFor(key,series?)撤无证据固定线；MarketDashboard读法显示来源/历史位置。
- [x] 对照：comparison-model.ts校验四指数、同频对齐、相邻变化、独立轴；IndexComparison.tsx复用旧API和新模型；navigation及页面增加分区。
- [x] 发散：events.ts为核过BLS事件与时区；组合、不一致事实和空缺说明在comparison；不引入新因子阈值。
- [x] 解读：macro-reading.ts/MacroReadingPanel.tsx提供有界自然问题/证据；AgentWorkspacePage仅面板入口，用户上下文不改写。
- [x] 验收：run-market-foundation-regression.mjs检查分位、日期、断档、异常、问句/缺数/事件时区；已有3套回归按新证据口径更新，npm run build；浏览器数据总览/对照/散点/事件/Agent/手机/错误。记录准确结果，未运行标未验证。
- [ ] 交付：dated报告/raw来源账、registry/INDEX本条、两进度；准确路径提交推本task分支并远端SHA读回；自己协调文件同步。无main/部署/收费任务。

命令（根目录参数为本工作树）：cd web && node run-market-foundation-regression.mjs；npm run test:market-dashboard；npm run test:market-understanding；npm run test:market-integration；npm run build。根目录python3 scripts/check_repo_hygiene.py（既存误报保留）；git diff --check。

2026-10-04：前五项按实际软件证据完成；真实接口故障未主动注入，合成异常检查通过。交付项提交/推送核对尚在执行，准确提交由协调记录写入。数据资格缺口见本轮报告，不把完整源恢复计为完成。
