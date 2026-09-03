# raw/exit_three_piece 复现清单（任务 J：a6_5 三件套实验）

## 产物

- `exit_three_piece_results.json`：3 模块 × 12 变体 × 2 费用档全量指标 +
  出场原因分布 + 锚定统计 + J1–J4 判定。
  - sha256(canonical JSON) = `52e67206f84f6072c067db09a484c63e20064b7ca5161aa5059db913d8d51861`
  - 双跑一致：`PYTHONHASHSEED=0` 与 `=42` 两次全量运行哈希相同；
    锚定门槛 VALID（A/B 模块重放与归档逐笔 Δ=0.000，C 模块 ΔexpR=−0.006）。
- 脚本：`scripts/run_exit_three_piece.py`（判定标准预注册于 docstring）。
- `fetch_pool.py`：重建池抓取脚本（腾讯 qfq 分页回填）。
- `pool_manifest.json` / `pool_rows.json`：池成分与逐标的行数。
- `pool/`：127 标的 `{symbol}.bars.parquet` + `.meta.json`（provider=tencent，
  2016-08-24 → 2026-09-01 原始抓取，主脚本统一截到 2026-08-25）。

## 环境重建（2026-09-02 必读——本实验的锚定方式与 9-1 两轮不同）

**数据工程现状（与 9-1 配方相比的灭失清单）**：

1. 回测深池 `~/.lei_signal_lab/backtest_pool`（175 标的、东财 10 年回填、
   截至 2026-08-28）从磁盘消失，池成分未入 git，无法按 8-31 口径复建；
2. stash `a816485f`（v2 检测器）/ `stash^3 1a321ce6`（rules.v2.yaml）对象
   不存在（仓库为 fresh clone，`git reflog` 仅 clone/checkout/pull 三条），
   exit_revival_a64 README 的「git archive + stash 叠加」配方不可执行；
3. 工作台历史 run 记录 `~/.lei_signal_lab/backtest_runs/*.json` 已删除，
   stop_loss_matrix 的「8-31 run 逐笔反构」数据源同样灭失。

**替代锚（本实验采用）**：specs 从 git 归档的 2026-08-27 工作台 run 逐笔行
反构（`../lifecycle_combo/`，三 run 与 8-31 出场矩阵的模块冻结配置逐字段
一致），行情用腾讯 qfq 分页接口重建（东财源本机不可达、web.ifzq 被 WAF
拦截后切 `proxy.finance.qq.com`；8 只高股息个股腾讯减法复权早期年份非正
价，已裁前缀——其参考信号全部在 2018+，远离截断点）。引擎/费用/指标全部
走 HEAD `52f5cb3` 已提交生产代码；账本为 rules.v1 + 代码默认条目的进程内
重建（仅 fees 参与模拟数值）。重建忠实性由预注册锚定门槛 AG0–AG3 验证
（A/B 模块逐笔完美复现 Δ=0.000；C 模块 172/177 入场价 1% 内、175/176
出场日一致，ΔexpR −0.006——漂移全部定位在 000568.SZ/002326.SZ 两只
高股息标的的复权因子差异）。

## 运行

```bash
cd <repo>
PYTHONHASHSEED=0  python scripts/run_exit_three_piece.py   # ~4 分钟
PYTHONHASHSEED=42 python scripts/run_exit_three_piece.py  # 双跑核对
```

注意：需带 pandas/numpy/yaml 的 Python（9 月实验沿用
`~/Desktop/biao-signal-system/.venv`）；池已在 `pool/`，无网络也可复跑。
