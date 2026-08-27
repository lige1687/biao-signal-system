# 宽度择时回测（B20/B50/B200）设计

日期：2026-08-27 ｜ 分支：`feat/timing-backtest`（基于 `recovery/lei-round2` @ a0c08b5）

## 背景与目标

用户想验证**基本面宽度指标**（个股站上 MA20/50/200 的比例，下称 B20/B50/B200）作为择时工具的有效性：

- 策略形态：阶段性顶部分批卖出 / 底部分批买入；极值反转式买底卖顶；以及与趋势闸门的排列组合
- 标的：沪深300、创业板指（配全A宽度）；标普500、纳指（配 SP500 成分宽度）
- 时间：各标的数据范围内最近约 20 年；核心指标为**年化收益**（对比买入持有）
- 附加交付：**参数扫描**——批量测试不同档位数/阈值/极值/分批方式，找出表现最好的一批参数，并做稳健性检查防止过拟合

宽度择时属于**资产配置研究**，与现有 LEI 技术信号回测（R 口径、禁资金字段）是两类问题。因此做成本模块 `src/lei_signal/timing_backtest/`，完全独立，互不污染。AST 门禁（`test_acceptance_gates.py`）禁的是下单类标识符，本模块不触碰。

## 数据层

新脚本 `scripts/backfill_timing_data.py`（仿 `backfill_breadth_full.py`：绕沙箱代理、断点续传）：

1. **指数/ETF 日线**：`000300`（2005起）、`399006`（2010起）、`^GSPC`、`^IXIC`、`SPY`、`QQQ`、`510300`（2012起）、`159915`（2011起）
   → `~/.lei_signal_lab/cache/timing/<symbol>.parquet`（date, open, close；A股 akshare 新浪/东财，美股 yfinance，均为可调整口径中最接近真实持仓的复权价）
2. **全A B20/B50/B200 长历史**：从 `~/.lei_signal_lab/cache/a_share_klines_full.parquet`（5207 只，1990→2026）重算
   → `~/.lei_signal_lab/cache/timing/breadth_cn_all.parquet`（date, b20, b50, b200, n_eligible_{20,50,200}；各窗口独立分母，个股须有 ≥N 根K线才计入）
3. **SP500 宽度**：读现成 `sp500_ma_breadth_history.json`（1986-01→2026-08），转成同结构 parquet：`breadth_sp500.parquet`

数据诚实声明（页面展示 + 文档）：
- 全A宽度早年含**幸存者偏差**（底表为当前存续个股回算）
- 全A底表来自新浪不复权价，除权对 MA 上方判断有微小影响
- 宽度序列截至最近一次回填日（重跑脚本即刷新）

## 回测引擎

`src/lei_signal/timing_backtest/` 模块：

- `data.py`：读指数 parquet + 宽度 parquet，按日期**交集**对齐，返回统一 DataFrame（date, open, close, b20, b50, b200）
- `strategies.py`：纯函数，输入对齐后的 DataFrame 与参数，输出逐日**目标仓位**序列（0~100%）
  - **阶梯 ladder**：B 值 → 目标仓位映射，穿越档位即调仓（档位触发式分批）
    - 参数：`indicator`(b20/b50/b200)、`n_bands`(3/5/9)、`edge_mode`(fixed / pre-window-quantile：用回测起点前历史分位数定档，无前视)、`direction`(contrarian 逆势默认 / momentum 顺势对照)
    - 默认 5 档固定阈值：B<20→100%、20-40→75%、40-60→50%、60-80→25%、≥80→0%
  - **极值反转 reversal**：B ≤ `low_extreme`(默认20) 后上穿 `low_extreme+confirm`(默认+5) 触发分批买入；B ≥ `high_extreme`(默认80) 后下穿 `high_extreme-confirm` 触发分批卖出
    - 分批模式 `batch_mode`：`time`（N 日每日 1/N）/ `band`（B 每回升/回落 10 个点调一批）
  - **趋势闸门 trend_gate**(off / ma200)：指数收盘 < MA200 时仓位上限压到 `gate_cap`(默认0%)，与上两者组合
- `engine.py`：逐日模拟。**T 日收盘出信号 → T+1 开盘成交**（无未来函数，单测锁死；open 缺失回退收盘价）。单边费用默认 A股 5bp / 美股 1bp（可调）。现金零收益。输出逐日净值/仓位/宽度 + 调仓记录
- `metrics.py`：年化收益（策略/买入持有/超额）、最大回撤、Calmar、Sharpe、年化波动、平均仓位、调仓次数、逐年收益表

## 参数扫描（用户明确要求的交付）

`scripts/sweep_timing_backtest.py`：直接调引擎批量跑网格（不经 API）：

- 维度：标的 × 指标 × 策略 × 档位数 × 阈值模式 × 极值/确认 × batch_mode/N × 趋势闸门
- 输出：CSV + Markdown 报告（按超额年化排序的 Top 表）
- **稳健性防护**：每组参数同时报告前半/后半窗口的超额年化与最大回撤；只有全窗口和两个半窗口都稳定占优的参数才进 Top 推荐；报告中明示「历史最优≠未来最优」
- Top 参数组预置到页面 `presets`，标注来源（扫描日期与窗口）

## API

`src/lei_signal/api/routes/timing_backtest.py`（同步执行，向量化秒级）：

- `GET /api/timing-backtest/options`：标的列表（各自数据起始日、宽度配对、幸存者提示）、策略参数 schema、预设
- `POST /api/timing-backtest/runs`：执行一次回测，返回全部结果；落盘 `~/.lei_signal_lab/timing_backtest_runs/<id>.json`
- `GET /api/timing-backtest/runs`：历史列表（参数 + 核心指标，供前端对比篮子）

## 前端

- `BacktestPage.tsx` 顶部加 tab：**「技术信号回测 | 宽度择时回测」**；新组件 `BreadthTimingPanel.tsx` + 净值曲线图（ECharts）
- 参数区：市场/标的下拉（显示数据范围与宽度配对，如「创业板指 ← 全A宽度，2010起」）、宽度指标、策略卡片、档位/阈值模式/极值/确认/分批参数、趋势闸门、费用、起止日期、预设按钮
- 结果区：指标卡（年化 vs 持有、超额、回撤、Calmar、Sharpe、暴露率）、净值双曲线（log 坐标）、指数+B值+仓位叠加图（仓位作背景色带）、逐年收益表、调仓明细；历史运行勾选叠加（≤5条）
- 页面显著标注数据诚实声明与研究用途

## 测试

- 引擎单测：T+1 执行无未来函数、阶梯映射边界、反转触发与确认逻辑、两种分批模式、费用计入、指标手算对拍（CAGR/MDD/Sharpe 小算例）
- API smoke：fixture parquet 走通 options/runs
- 全仓现有测试不破坏

## 非目标

- 不做自动交易、不下单、不接实盘；不与 LEI 技术信号耦合
- 不做日内/分钟级；不做多资产组合再平衡（单标的择时）
