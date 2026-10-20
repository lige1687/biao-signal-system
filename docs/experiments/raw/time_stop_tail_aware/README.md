# raw/time_stop_tail_aware 复现清单（任务 M：时间止损接受右尾——前置持仓分类器）

## 产物

- `time_stop_tail_aware_results.json`：全量结果（G0 价格基准预检、覆盖账目、
  Step1 主检验/θ 网格/K 敏感性/斜率变体/冻结组/分模块/机制描述、
  Step2 条件时间止损 4 格 + 无条件 N 参照 2 格 + 分模块分解）。
  - md5(规范化 JSON) = `f73cc041e08c393eeb14c3cfd57eb557`
  - 双跑一致：`PYTHONHASHSEED=0` 与 `=42` 两次 `--dump-hash` 输出相同。
- `events_per_trade.csv`：291 行逐笔事件表（sample/module/group/symbol/
  signal_date/entry_date/entry_price/stop_price/exit_date/exit_reason/
  holding_bars/r_net/is_tail/src/r_at_{5,10,15}/peak_r_at_{5,10,15}/
  slope5_r_at_10）。**解读注意**：holding_bars<K 的行其 r_at_K 是
  离场后路径（仅供 exited_before_K 统计），分类检验只用 alive@K10
  （holding_bars≥10）子集。
- `hash.json`：双跑哈希记录。
- 脚本：`scripts/run_time_stop_tail_aware.py`（判定标准预注册于 docstring）。

## 数据来源（2026-09-02 数据工程现状，必读）

stop_loss_matrix 所用的 175 标的全池逐笔（`~/.lei_signal_lab/backtest_runs/
20260831-*.json`）与池数据（`~/.lei_signal_lab/backtest_pool/`）在本实验
开机排查时已确认**丢失**（目录不存在、stash 已清、原服务进程已停，
rules.v2.yaml 仅存活于原进程内存，不可恢复）。本实验改用仓库内已归档的
其他实验逐笔 run（同为引擎 a6_1_costbasis 出场口径）：

| 样本键 | 文件 | 模块 | 组别 |
|---|---|---|---|
| A_cn | raw/lifecycle_combo/T2_A_ETF_cm05_shrink.json | A | frozen |
| Bp_cn | raw/lifecycle_combo/T1_Bp_a61.json | B | frozen |
| C_cn | raw/lifecycle_combo/T2_C_stocks_v3_b15.json | C | frozen |
| A_us | raw/stage_b200/A_us.json | A | frozen |
| B_us | raw/stage_b200/B_us.json | B | variant(cb20/cl10) |
| A_noshrink | raw/breadth_overlay/wf_a_noshrink.json | A | variant(去量缩) |
| A_cm10 | raw/breadth_overlay/wf_a_cm10.json | A | variant(cm1.0) |
| Bp202 | raw/breadth_overlay/wf_bp_202.json | B | variant(cb20/cl2) |
| Bp404 | raw/breadth_overlay/wf_bp_404.json | B | variant(cb40/cl4) |

K 线（离线，不重跑信号、不依赖 src/backtest）：
- OHLCV：`~/.lei_signal_lab/cache/*.bars.parquet` ∪ `tests/*.bars.parquet`
  （39 标的，按更长者取一）
- close-only：`~/.lei_signal_lab/cache/a_share_klines.parquet`
  （5208 只 CN 股，仅 close，2023-05-05 起；用于 B/C 模块股票）

## 运行

```bash
# 解释器必须带 pandas/numpy（系统 python3 无 pandas）：
cd /Users/liyongbiao/Desktop/biao-signal-system-recovery
PYTHONHASHSEED=0  /Users/liyongbiao/Desktop/biao-signal-system/.venv/bin/python scripts/run_time_stop_tail_aware.py --dump-hash
PYTHONHASHSEED=42 /Users/liyongbiao/Desktop/biao-signal-system/.venv/bin/python scripts/run_time_stop_tail_aware.py --dump-hash
# 两次 HASH 均应为 f73cc041e08c393eeb14c3cfd57eb557（约 40 秒/次）
```

## 已知口径声明（与归档主报告一致，此处备查）

1. 价格基准预检（G0）：structure_stop_C 可核验 101 笔，确认 bar 收盘
   <stop_price 失配 0 笔。
2. close-only 源无开盘价：Step2 触发离场退化为触发日收盘成交
   （OHLCV 源仍按引擎次根开盘 + CN 跳空护栏）。
3. 事件表统一要求 entry 后 15 根 K 线可得且第 10 根距入场 ≤60 自然日
   （停牌防护）；不满足者计入 no_coverage_or_guard，不进样本。
