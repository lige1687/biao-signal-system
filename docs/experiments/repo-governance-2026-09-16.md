# 仓库目录治理（2026-09-16）

## 一句话结论（大白话）

给整个仓库做了一次大扫除：根目录、脚本目录、测试目录、文档目录从
「什么都在一层」收拾成「每类东西有固定抽屉」，生产和研究系统全程没有
被弄坏；并且立了新规矩写进 AGENTS.md——以后每个 AI 干完活都得跑一个
自检脚本，文件放错地方会报警，从根上防止再乱回去。

## 做了什么

五个阶段，每阶段独立提交（分支 `chore/repo-governance-2026-09-16`）：

| 阶段 | 内容 | 提交 |
|---|---|---|
| 0 | 治理前先「保存现场」：把约 470 项未提交在制工作一次性入库；补 .gitignore 漏洞（`*.db-shm`/`*.db-wal`/根层 `*.log`/`.workbuddy/`） | `1d431137` |
| 1 | 根目录清空到白名单：删 8 个同步残留 JSON、ROUND 报告归档、运维手册进 docs/ops/、删根目录残留旧库、config/ 并入 configs/ | `af8b3f6c` |
| 2 | scripts/ 分家：根层 213 文件收敛到 59 个白名单（生产+研究工具链+backfill 运维）；15 个 plist 迁入 scripts/launchd/ 并回填 4 个只存在本机的外部 plist；141 个一次性脚本 + 26 个 agent 工作目录 + round3/4_repro 归档进 scripts/archive/ | `62bca8df` |
| 3 | tests/ 根层 85 项收敛到 7 个标准条目：在用夹具（000001.SS/000300.SS）进 fixtures/kline/ 并改 14 处引用；37 组无用夹具进 fixtures/archive/ | `a5a0b5d8` |
| 4 | docs/ 根层 35 个文档收敛到 16 个权威文档：19 个交接/计划类过程文档进 archive/handoffs-plans/ | `910ebfbb` |
| 5 | 长效规约：AGENTS.md 新增「文件归置规约」、docs/README.md 重写为目录地图、新增 scripts/check_repo_hygiene.py 自检脚本、本报告 | 本次 |

## 长效规约（本次治理的核心产出）

1. **AGENTS.md「文件归置规约」**（对当前和后续所有 agent 生效）：
   目录地图（什么放哪）+ 生命周期（做完了删子代理工作区和临时脚本、
   留报告和 raw 数据）+ 四层白名单 + 破坏性边界。
2. **scripts/check_repo_hygiene.py**：结案前必跑，检查根层/scripts/docs/tests
   四层白名单 + 关键配置是否入库，违规非零退出。已验证能抓白名单外新文件。
3. **docs/README.md**：重写为目录地图与导航（规约的展开版）。

## 验证证据

- 全量 pytest（治理前后同一基线对比）：**2574 通过**；
- 治理引入的新失败：**0**。既有失败 7 个，逐一核实为治理前已存在：
  - `test_rule_ledger::test_ruleset_version_is_present`——规则账本升 2.1.0
    但测试停在 2.0.0（9-07 功能提交遗留漂移）；
  - `test_agent_chat_e2e` 两个用例、`test_agent_name_resolve`、
    `test_symbol_extraction`、`test_discussion_backtest_03b`——在制
    agent/LLM 工作的未完成部分（快照提交上同样失败；其中
    discussion_backtest 单独跑通过，属顺序/环境敏感）；
  - `test_newsfeed_push::test_push_only_macro_risk_and_importance`——推送
    阈值过滤逻辑，同样快照上复现。
- 生产依赖链验证：`paper_account.py → run_final_form_v2 → …` 全链 import 通过；
- 保留脚本全部通过 `py_compile` / `bash -n` 语法检查；
- 归档文件名全仓 grep：活代码/配置/测试零残留引用（注释级已同步改路径）；
- launchd 已加载任务不受影响（生产脚本全部原地未动，~/Library/LaunchAgents
  副本引用的是脚本绝对路径）。

## 已知遗留与风险

1. `export_flagship_data.py` 因 2026-09-01 源码丢失事故缺 4 个依赖模块
  （仅剩 .pyc），本来就不可运行，本次保留在根层（UI 引用其产物）待重建。
2. 归档移动使旧实验报告中记录的复现命令路径失效
  （`scripts/x.py` → `scripts/archive/x.py`），映射关系见
  `scripts/archive/README.md`；git 历史可完整追溯。
3. 4 个回填进仓库的 plist（module.e.weekly/paper.daily/sentiment.weekly/
  timing.daily）源自本机 ~/Library/LaunchAgents 快照，内容未改动。
4. 全量测试中 7 个既有失败建议按归属线修复（不属于本次治理范围）。
5. 本机磁盘几乎满（228GB 用了 100%，剩 1.3GB）——与治理无关但影响
  任何大文件操作，建议用户清理。

## 决策卡

- 动机：用户指出目录组织混乱，授权治理；要求建立长效机制让后续 agent
  知道文件放哪、做完删什么。
- 边界：不动 docs/experiments 结构（850 份被扫描/登记/契约钉死）、不动
  生产脚本、不改业务逻辑（唯一代码改动：config_loader 一行路径、
  install 脚本 plist 源路径、夹具路径常量、advisor.py 坏链修复）。
- 回退：每阶段独立 commit，可单独 revert。
