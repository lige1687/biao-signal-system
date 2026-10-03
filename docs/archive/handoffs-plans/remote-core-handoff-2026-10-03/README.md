# 远端核心交付：验收及后续实证研究交接

冻结时间：2026-10-03T12:57:24.870216+08:00（Asia/Shanghai）。本包使用既有 `docs/archive/handoffs-plans/` 交接归置与 `docs/ops/work-progress/` 阶段规范，不另建权威研究登记系统。

验收已经完成，结论为有条件接受。后续报告/工具返修未确认启动；候选规则效果研究只完成资料去重和方法评议，**没有新脚本、实验、收益结果或预注册预算**。当前暂停研究，正在交接；原执行者交接后不再推进本问题，接手者先核版本和资料。

仓库：<https://github.com/lige1687/biao-signal-system>。本包分支：`codex/remote-core-handoff-20261003`；内容基线完整提交：`ef063a7a234185e78f6e6bdb4c20c5ba90e3b8ca`；原验收对象：`4155b4db7ccd14674eff2e29dfaf102d2ac3e5f9`。包含本包的准确提交用 `git log -1 --format=%H -- docs/archive/handoffs-plans/remote-core-handoff-2026-10-03` 定位，并与远端分支核对。最终发布回执为同级 `remote-core-handoff-publication-2026-10-03.json`，它在发布阶段填写实际提交，避免在提交自身内容里伪造自指SHA。

## 阅读顺序与第一步

1. 本文件、`ORIGINAL_GOALS.md`、`sources/USER-REQUESTS.md`、`sources/current-policy/AGENTS.md`。
2. `STATUS.md`、`DECISIONS.md`、`DO_NOT_REPEAT.md`；不要从旧报告“待用户决定”推断最新授权。
3. 原队列README/OWNERSHIP/TASKS/RESEARCH-DECISIONS-ARCHITECTURE；原验收提示词、交付总报告、母体报告与验收报告（路径见EVIDENCE）。
4. `ENVIRONMENT.md`、`ARTIFACTS.md`、`manifest.json`、`SHA256SUMS`、`VALIDATION.md`。
5. 执行 `python3 docs/archive/handoffs-plans/remote-core-handoff-2026-10-03/tools/verify_handoff.py --root .`；它核全部随Git交付文件，**有资料缺口时不会授予完整研究准入**。
6. 按ENVIRONMENT建立独立环境，运行只读最小检查；再读NEXT_STEPS/RESUME_PROMPT接管。不要重跑504条审计或旧账户。

包内有完整任务证据索引及关键原文/策略只读原件；数据沿用Git已经跟踪的冻结输入，不重复上传大包。缺小时行情、正式六ETF现期资料资格和定义证据闭包，见ARTIFACTS。本包不是交易规则批准、实时环境备份或正在运行进程的迁移。
