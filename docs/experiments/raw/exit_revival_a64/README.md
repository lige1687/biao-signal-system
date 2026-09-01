# raw/exit_revival_a64 复现清单（Prompt G：a6_3 复活实验）

## 产物

- `exit_revival_results.json`：3 模块 × 7 变体 × 2 费用档全量指标 + 出场原因分布。
  - sha256(规范化 JSON) = `3cdf99608f6e9183f1647b8e8a5101d65748d4bbd0762fd5587808c9b8c84286`
  - 双跑一致：`PYTHONHASHSEED=0` 与 `=42` 两次全量运行哈希相同，复现门槛均为 6/6 OK。
- 脚本：`scripts/run_exit_revival_a64.py`（判定标准预注册于 docstring）。

## 环境重建（2026-09-01 必读——归档数字的可复现性依赖此节）

8-31 出场矩阵 run 所依赖的工作区状态在 2026-09-01 10:52 被分支切换
（feat/timing-backtest → recovery/lei-round2 + pull）覆盖，且当时的未提交
修改以 `git stash -u` 存入 stash。本实验在 `/tmp/a64-worktree` 用
`git archive HEAD` 导出 + 叠加 stash 内容重建了该状态：

- 基底：`recovery/lei-round2 @ 21e2cd9`（git archive 导出，不动主树）
- 叠加 stash `a816485f`（tracked 部分）中全部 `src/` 修改（检测器 v2 状态：
  dense_breakout / first_ma_pullback / two_b_reversal / reward_risk_filter /
  tradability_gate / volume / lei_color / indicators / rules_config 等）
- 叠加 stash^3 `1a321ce6`（untracked 部分）中全部 `src/` 与 `configs/` 文件
  （关键：`configs/rules.v2.yaml`——工作台 overrides 锚点所在账本）
- backtest 包（src/lei_signal/backtest/）：stash^3 与主树磁盘版本 sha1 一致，
  直接复制

**实证验证**：重建状态下复跑 a6_1/a6_3 六个基线，与 8-31 工作台 run 记录
（`~/.lei_signal_lab/backtest_runs/20260831-23*.json`）**逐位一致**（笔数、
expR、PF 到 1e-9），证明重建状态 == 归档状态，a6_4 数字与既有矩阵直接可比。

## 运行

```bash
cd /tmp/a64-worktree   # 上述重建环境
PYTHONHASHSEED=0 python3 scripts/run_exit_revival_a64.py   # ~7 分钟
PYTHONHASHSEED=42 python3 scripts/run_exit_revival_a64.py  # 双跑核对
```

注意：在主树（recovery/lei-round2 当前状态）直接运行会因账本锚点缺失
（rules.v2.yaml 不在主树）而无法应用模块冻结 overrides，且检测器为旧版，
**不能**复现归档基线。若未来要在主树复跑，需先把 stash 的 v2 状态合入。
