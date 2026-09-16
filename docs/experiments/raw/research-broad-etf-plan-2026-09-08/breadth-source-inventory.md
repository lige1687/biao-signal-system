# 旧 B9 宽度择时：来源与隔离复现清单（只读盘点，2026-09-08）

## 一句话结论（大白话）

旧 B9 的九条指数收盘价和全 A 股宽度历史都还在本仓，足够按现存公共底座重建“始终持有”和“宽度三档”两条基准线；但终审点名的三支脚本已经缺失，结果文件也没有把完整参数和输入指纹写进去，所以现在不能声称能把 walk-forward、安慰剂和压力测试原样复算。旧报告中的 `passed` 只是历史记录，不是本次独立验收。第一批应只复现 A/B 两臂，并用按份额记账的独立账户核对现存模拟器，暂不重跑参数搜索。

这里的“宽度 B200”是：全 A 股中，收盘价站在各自 200 日均线上方的股票占比。它是市场环境层的仓位预算，不改变道路、路牌或 A/B/C/D 触发判定，符合“市场环境独立研究、不硬挡单一信号”的边界。

## 可复制包的最小边界

### 代码与结果

| 状态 | 路径 | 证据与用途 |
|---|---|---|
| 存在 | `scripts/run_portfolio_split.py` | SHA256 `af5cae26…ab1d17`。本地文件读取 B200 与九条指数；定义 2015-06-16→2026-08-18、公用三档、周频、次一交易日生效、5% 调仓带、单边 10bp、现金零收益。|
| 存在 | `scripts/run_siphon_detector.py` | SHA256 `f2d71db8…ef07d0`。`run_portfolio_split.py` 从这里导入 `COST/MID/HIGH/tier_weight/weekly_last`；导入本身不刷新数据。|
| 缺失 | `scripts/run_bform_walkforward.py` | 报告点名，但本仓、全部 Git 历史和 `/Users/yongbiaoli/lei-signal-sync` 的普通文件搜索均未找到。|
| 缺失 | `scripts/run_bform_placebo.py` | 同上。|
| 缺失 | `scripts/run_bform_stress.py` | 同上。|
| 存在 | `docs/experiments/raw/portfolio_split/bform_walkforward_results.json` | SHA256 `c1b94cf4…098e9`；只有汇总结果，没有输入路径、输入哈希、参数网格、分段日期算法或代码版本。|
| 存在 | `docs/experiments/raw/portfolio_split/bform_placebo_results.json` | SHA256 `b72efae9…17fe7`；只有 500 次汇总分位数，没有平移抽样实现与随机种子记录。|
| 存在 | `docs/experiments/raw/portfolio_split/bform_stress_results.json` | SHA256 `18d8fb52…a4360`；只有汇总结果，没有五档权重表和精确延迟实现。|

同步仓中的宽度文件和 `run_portfolio_split.py` 与本仓哈希一致，因此同步仓不是缺失三支脚本的备用来源。Git 提交 `21e2cd9` 只归档了结果 JSON 和行情文件，没有归档这三支脚本。

旧 A/B 的导入链已经查完整：入口只直接依赖 Python 标准库、`numpy`、`pandas` 和 `scripts/run_siphon_detector.py`；后者为这条链提供的四个常量/函数也只使用 `numpy/pandas`，没有再调用项目包、用户缓存或网络。读取 parquet 还需要 pandas 可用的 parquet 引擎（通常是 `pyarrow`）；仓库没有为这次旧实验单独保存环境锁定快照。因此复制包应包含这两支源码和 `pyproject.toml`，并在第一次运行时另记实际 Python、numpy、pandas、pyarrow 版本。

### 宽度序列

| 状态 | 路径 | 证据与口径 |
|---|---|---|
| 存在 | `docs/experiments/raw/breadth_overlay/a_share_breadth_33y_snapshot.json` | SHA256 `8fabf188…b33ca`；8109 行，1993-04-22→2026-08-18，字段 `date/ma20_pct/ma50_pct/ma200_pct`。`load_breadth()` 只读 `ma200_pct`，不访问缓存、不联网。|
| 未核验 | 生成 B200 的逐股原始面板及当时成分范围 | 现存 B9 运行不需要逐股面板，但若要独立证明宽度本身无幸存者偏差、复权一致、分母正确，则仍缺“当时用于生成该 JSON 的原始面板 + 生成脚本版本 + 股票池清单 + 哈希”。|

注意：报告记录该宽度在 2026-08-18 停止，不能拿它当实时信号。第一批历史复现应冻结此文件，禁止从 `~/.lei_signal_lab/cache` 动态替换或在线刷新。

### 九个对象及收盘价

九个身份在 `run_portfolio_split.py:59-70` 写死；所有文件只有一列 `close`、无缺值，且 B9 公共窗口内可用。它们是指数点位，不是可直接成交的 ETF 价格；指数点位没有分红收益，不能把结果直接当成 ETF 实盘收益。

| 对象 | 路径 | SHA256 | 文件覆盖 |
|---|---|---|---|
| 沪深300 | `docs/experiments/raw/portfolio_split/sh000300_close.parquet` | `e8f51bfc…9d7863` | 2002-01-04→2026-08-27 |
| 上证50 | `docs/experiments/raw/portfolio_split/sh000016_close.parquet` | `d90b7878…def57` | 2004-01-02→2026-08-27 |
| 中证白酒 | `docs/experiments/raw/portfolio_split/sz399997_close.parquet` | `c5393658…77e7` | 2015-06-16→2026-08-27 |
| 国证地产 | `docs/experiments/raw/portfolio_split/sz399393_close.parquet` | `fc3075ee…4bfbe` | 2012-08-20→2026-08-27 |
| 创业板指 | `docs/experiments/raw/siphon_detector/cyb_399006_close.parquet` | `04e199c1…1adc` | 2010-06-01→2026-08-27 |
| 证券公司 | `docs/experiments/raw/siphon_detector/sec_399975_close.parquet` | `6b229cc0…1f83ca` | 2015-05-19→2026-08-27 |
| 新能车 | `docs/experiments/raw/portfolio_split/sz399976_close.parquet` | `12fead5a…87b5` | 2015-05-19→2026-08-27 |
| 中证医疗 | `docs/experiments/raw/portfolio_split/sz399989_close.parquet` | `ca12b1f3…fdaf` | 2015-05-19→2026-08-27 |
| 国证有色 | `docs/experiments/raw/portfolio_split/sz399395_close.parquet` | `4e8cbac3…35bd61` | 2012-10-29→2026-08-27 |

行情文件止于 2026-08-27，但代码强制截到宽度末日 2026-08-18，并对九列 `dropna(any)`，所以公共窗口由中证白酒首日和宽度末日确定。相邻报告称这些指数来自 akshare、按不复权指数处理；现存 B9 底座只读落盘 parquet，不会自动下载。精确的下载调用、供应商响应和下载时哈希没有随 B9 脚本记录，来源链只能评为“文件存在，原始下载过程未核验”。

## 信号、成交、费用与现金

- 三档：`B200 < 43.3 → 100%`，`43.3 ≤ B200 < 56.7 → 50%`，`B200 ≥ 56.7 → 0%`。边界比较符号来自 `tier_weight` 与报告；第一批必须把边界值单独造例核对。
- 周频：每个自然周取最后一个有宽度观测的交易日。`tier_daily()` 用该信号日在九对象公共交易日中的位置，再向后一行生效。因此实际记账是“信号日收盘知道档位，下一共同交易日收盘收益结束后持有新档位”；这与策略规格的“收盘信号，下一根开盘执行”不是同一个成交价口径，应明确标为组合研究代理。
- 成本：目标权重变化绝对值之和 × 0.001，按单边 10bp；5 个百分点以内不调。没有买卖价差、滑点、税费差异或 ETF 申赎成本。
- 现金：核心 `run_portfolio_split.py` 为零收益。报告中的“现金 2% 后年化 13.4%”来自附录口径，不是 11.99% 核心结果的现金设定，第一批不可混用。
- 收益：九指数简单日收益；不是含分红总回报。缺失值以公共交易日交集消除。

## 已证实的记账差异（不能据此推断宽度超额消失）

`simulate()` 在每天收益之后没有按各指数当天涨跌更新每条持仓的实际权重；它只在超过 5 个百分点时把权重直接写回目标，且只对这次写回收费（`scripts/run_portfolio_split.py:117-139`）。根任务随后用原函数 AST 做了两资产最小反例，证实它与按真实份额持有的账户不一致；证据在 `weight-drift-check.json`。

反例是两资产都从 100 起步，随后到 104/96，再回 100/100；真实权重最大漂移 2 个百分点，低于 5% 调仓带，因此不该下单。现存算法终值 `1.0006009615`，按恒定份额并扣初始费用的账户终值 `0.999`，相差 `0.0016009615`。单资产往返和双资产恒价控制一致，说明差异确实来自多资产权重未随价格漂移。这个小例只证明记账实现有差异；B9 全窗的差异方向和大小仍须第一批 A/B 双账实跑，不能据此宣布旧宽度优势消失。

## 隔离复现步骤（可执行说明，本次未运行收益）

1. 新建只读输入快照目录，仅复制上表 1 个 B200 JSON、9 个 parquet、`run_portfolio_split.py`、`run_siphon_detector.py`，写完整 SHA256 清单；禁止链接用户缓存和网络。
2. 固定 Python、pandas、numpy、pyarrow 版本与时区；先验证每个文件的列、首末日期、重复日期、非正价格和哈希。
3. 只实现 A“始终持有”和 B“全体使用宽度三档”两臂，冻结 2015-06-16→2026-08-18、43.3/56.7、周频、下一共同交易日生效、5% 调仓带、10bp、现金 0%。不做参数网格、walk-forward、安慰剂或五档扫描。
4. 同时跑两本账：一条逐字复刻现存 `simulate()`；一条记录每个对象真实份额、现金和每笔调仓，价格变化后让权重自然漂移。每日输出日期、信号档位、目标权重、实际权重、成交额、费用、现金和总资产。
5. 两资产小例已经确认记账差异；正式九对象运行仍须先锁版本与哈希。将旧 A 年化 `-0.48%`、旧 B 年化 `11.99%` / 最大回撤 `-34.73%` 仅列为对账参照，不作为通过标准。
6. 只有复刻账能逐日或在可解释舍入误差内重现旧 A/B，且真实份额账差异可量化后，才制定第二批协议。缺失的三支终审脚本在找回原文件或依据预注册文档重新实现并另标版本前，不做“原样复算”声明。

## 复现状态判定

- **A/B 基准复刻：有条件可做。** 本地输入齐全，公共底座代码存在；仍需版本环境和逐日账本核对。
- **A/B 独立可信核验：待做。** 最小反例已证实旧模拟器与真实份额账不同；下一步是九对象双账量化差异，以及核对指数替代 ETF 的可交易差异。
- **三项终审原样复算：当前不可做。** 精确缺少 `run_bform_walkforward.py`、`run_bform_placebo.py`、`run_bform_stress.py`；结果 JSON 不足以无歧义重建实现。
- **宽度源头重建：未核验。** B200 成品序列存在，但逐股源面板、当时股票池和生成版本未绑定。
