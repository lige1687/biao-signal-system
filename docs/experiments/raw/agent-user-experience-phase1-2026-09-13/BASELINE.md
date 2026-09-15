# 开工基线记录（2026-09-13）

- 权威基线仓库：`/Users/yongbiaoli/Desktop/lei-signal-lab`（运行目录，未改动）
- 上游 HEAD：`8ba16576b75e605aa1b0d0902568c760c4b99095`
- 上游工作区状态：304 个未提交/未跟踪条目（git status --porcelain），任务书输入清单 15 个关键文件 SHA256 全部比对一致（见 `docs/prompts/agent-user-experience-phase1-2026-09-13.inputs.json`，核对时间 2026-09-13 13:20 前后）。
- 实际开发路径：`/Users/yongbiaoli/lei-agent-ux-20260913`（独立开发副本，本目录）
- 副本基线提交：`a61fc67194f4e9b25b44012283f2e823bf252730`（含上游未提交改动与未跟踪源码；排除密钥 .env*、真实业务库 lab.db* 与根目录真实台账 JSON、logs/、miniapp/、docs/experiments 大体积数据与 raw/、pyc、web/dist）
- 任务书：`docs/prompts/agent-user-experience-phase1-2026-09-13.md`
- 用户授权原话（任务书 §6）：“对，结果失真方面后续再讨论吧，我这边在做因子库……有继续让执行agent做的，可以给我prompt，我去给他做。”

## 复制排除清单（副本中不存在）

`.env`、`.env.bak.*`、`lab.db`、`lab.db-shm`、`lab.db-wal`、根目录 `trade_plans.json`、`trade_plan_revisions.json`、`sentiment_observations.json`、`plan_action_items.json`、`plan_annotations.json`、`watchlist_groups.json`、`watchlist_items.json`、`logs/`、`miniapp/`、`.workbuddy/`、`docs/experiments/raw/`、`docs/**/*.parquet|gz|csv`、`__pycache__`、`web/dist/`。

预览/测试使用合成数据时会明确标注，不以演示数据冒充真实行情。
