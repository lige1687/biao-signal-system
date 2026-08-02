# LEI 技术信号研究系统（lei-signal-lab）

> LEI 双均线与顶底结构的**技术信号识别、解释与历史有效性研究系统**。
> **不是自动交易系统**——不下单、不计算仓位、不管理资金、不输出确定性买卖建议。

## 重要声明

本系统仍为**技术信号研究工具**：
- **不**实现自动交易、仓位、资金、账户管理
- **不**通过回测结果调参；不为了历史表现优化任何技术参数
- **不**将长周期趋势重新用于 Block 底部、反包或短周期事件
- 数据错误必须显式 `DATA_UNAVAILABLE`，不得静默处理为「无信号」
- 任何 `research_proxy` 规则必须在界面明确标注「研究代理」，不冒充 LEI 原始公式
- 市场环境层（Round 4）只做**独立分组研究**，不硬挡单标的技术信号

## 当前状态 (2026-08-02)

**代码门禁：** 496 passed / 1 skipped（159915 真实数据快照）、mypy clean、ruff 13 项工程债。

**已完成的研发回合：**

| 回合 | 内容 | 状态 |
|---|---|---|
| Round 2 | 10 项语义修复（周线、生命周期、机会/风险分离、Top+Black、量能/B1 等） | 完成 |
| Round 3 | 状态机改为事件档位投影器、多结构独立推进/观察/失效/重开与真实日历注入 | 完成 |
| Round 4 | 独立市场环境层（A股六市场+美股三指数宽度、NAAIM/AAII 情绪、点单成分股） | 代码完成，缺真实数据验收 |

**待完成：**
- 真实 `159915` 历史行情快照（解锁 Round 3 集成回放）
- A 股 6 个市场 point-in-time 历史成分股与行情（解锁 Round 4 市场宽度实盘验证）
- NAAIM/AAII 合法来源历史数据（含 `available_at` 发布时间）
- 真正未参与规则选择的样本外验证

**确认已证伪的设计：**
- ❌ 同一日所有条件必须全满足的硬门槛 → 已被生命周期分层替代
- ❌ B1 必须 ≥ 3R 的硬入场门槛 → 已移除（C 较远、B1 较近，几乎所有信号被过滤）
- ❌ 候选结构越级抬升 + 升级日要求重新 EMA20 交叉 → Round 3 已封堵
- ❌ 单一全局阶段覆盖多结构 → 已改为逐 `structure_id` + `lifecycle_id` 独立推进

## 项目结构

```
configs/rules.v1.yaml            19 条规则账本（阈值/版本/来源）
src/lei_signal/
  domain/                  类型、规则加载器、确定性事件 ID
  data/                    代码标准化、Provider（腾讯/东财/Yahoo/新浪）、复权校验、交易日历
  features/                SMA/EMA、ATR、摆动点、量能、筹码分布代理
  rules/                   19 条原子规则（颜色、双均线、顶底、关键性波动、B1、量能）
  events/                  只追加幂等事件日志
  state/                   Round 3 状态机（逐结构 observations + 机会/风险独立分离）
  compose/                 组合解释器 + 完整分析入口
  research/                后续收益、MFE/MAE、Bootstrap、匹配基准、分组 + 市场环境研究
  storage/                 SQLite 迁移 + 幂等事件写入 + 完整生命周期
  market_context/          Round 4 市场环境层（宽度/回撤/情绪，独立于技术信号）
  ui/                      Streamlit + Plotly（5 个 tab）
tests/
  unit/ golden/ no_lookahead/ integration/  496 tests
```

## K线两种颜色模式

| 模式 | 说明 |
|---|---|
| **红绿**（A股惯例） | 涨红跌绿；K线下方小方块显示当日 LEI 绿/灰/黑状态（三色叠加在涨跌之上） |
| **绿灰黑**（LEI 三色） | 每根 K线本体按当日 `signal_color` 上色——绿色=强势、灰色=关注、黑色=弱势。颜色直接画在 K线上，K线整体就是信号视图 |

两种模式只影响**展示**，不改变任何 LEI 计算、生命周期或风险判断。在「当前观察」页可随时切换。

## 行情数据源

| 源 | 代码 | 复权 | 优先级 | 说明 |
|---|---|---|---|---|
| 腾讯财经 | `tencent` | 前复权（`qfq`） | A股第1 | 稳定、不需要 token |
| 东方财富 | `eastmoney` | 前复权（`fqt=1`） | A股第2 | 与腾讯互为对照 |
| Yahoo Finance | `yahoo` | 复权（`auto_adjust`） | 兜底 | 美股/港股首选；A 股偶发 429 |
| 新浪财经 | `sina` | **不复权** | 已退出默认链 | 不复权会污染 LEI 信号；仅作备用 |

A 股链路：腾讯 → 东方财富 → Yahoo。美股/港股直接走 Yahoo。

## 安装与运行

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest -q                  # 496 passed, 1 skipped
python3 -m streamlit run src/lei_signal/ui/app.py
# 访问 http://localhost:8501
```

## UI 五页说明

| Tab | 内容 |
|---|---|
| **当前观察** | K线主图（顶部）+ metrics + 三色判断依据 + 五维度 + 结构/B1 + 风险 + 支持/冲突 + 事件三栏 |
| **技术事件时间轴** | 所有信号按 `available_date` 排列，区分今日新增/仍有效/已失效 |
| **结构诊断** | 每个结构的生命周期链（candidate → early_watch → confirmed → joint → trend），转黑/触C等状态 |
| **历史信号研究** | 逐笔统计、Bootstrap、资产分组、基准比较（研究用，不构成买卖建议） |
| **市场环境** | A股/美股宽度、回撤、NAAIM/AAII 情绪、顺风/逆风摘要（独立展示，不挡技术信号） |

## 真实数据获取失败（2026-08-02 状态）

本机多次尝试 `https://push2his.eastmoney.com` 与 `https://query1.finance.yahoo.com`：
- 东方财富：连接被远程断开
- Yahoo：HTTP 403 限流

**腾讯 `web.ifzq.gtimg.cn` 在同等网络环境下可正常工作。** 如遇不可用，可使用 CSV/Parquet 上传入口。系统**不**把合成数据冒充真实数据。

## 已知数据���、复权、时区和统计限制

- 腾讯/东方财富 A 股前复权口径；Yahoo `auto_adjust=True`；ValidationReport 标注
- 时区：本地交易日（pandas DatetimeIndex，UTC-naive）
- 数据不足：少于 21 根触发 `DataUnavailableError`；前 20 根三色状态必须为 `unknown`
- 统计样本来自单一标的的历史，存在生存偏差；研究页不构成任何买卖建议
- 不模拟仓位：研究层禁止出现 `position`、`shares`、`capital`、`pnl` 等字段（AST 级别门禁）
- 性能：800 根约 5-10 秒；`build_history=True` 逐日构造解释快照，量大会明显变慢
- 资产类别启发式：3-5 全字母视为 `us_equity_or_etf`；非标准格式返回 `unknown`，不猜测
