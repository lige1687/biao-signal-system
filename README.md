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

## 本轮修复 (2026-08-01 → 2026-08-02)

按 10 项修复要求，10 项语义偏差全部修完。**268 项测试通过，1 项 skip**（等待真实 159915 数据快照）。

### 修复 1：周线计算
- `compute_weekly_long_trend` 不再偷换为 EMA20/40；不足 60/120 根周线时 long_trend = unknown
- `aggregate_weekly` 新增 `is_complete` 列，明确区分「已结束」与「不确定」
- 新增 `tests/no_lookahead/test_weekly_unknown.py`（8 项）

### 修复 2：候选生命周期按时间顺序推进
- 底部：候选 → 确认 → 失效；先触 C → 永久失效，突破颈线也不能复活
- 顶部：先创新高 → 永久作废，跌破颈线也不能再确认
- 新增 `tests/unit/test_lifecycle_order.py`（7 项）

### 修复 3：机会/风险状态分离
- `DayState.opportunity_stage` 与 `risk_state` 独立保存
- EMA 转强按 `structure_id` 绑定，结构失效立即关闭
- 新底部不得继承旧底部早期转强
- 新增 `tests/unit/test_state_machine_v2.py`（5 项）

### 修复 4：Top+Black 组合状态
- 覆盖两种顺序（顶先确认后转黑；先转黑后顶确认）
- 重新进入可产生新事件
- 新增 `tests/unit/test_top_black_combined.py`（5 项）

### 修复 5：事件按真实生命周期分类
- 颜色事件有效到颜色改变；EMA 转强转黑即失效；摆动点不进 active
- 移除 60 天展示窗
- 新增 `tests/unit/test_event_validity.py`（4 项）

### 修复 6：研究统计方向调整
- `raw_forward_return` + `direction_adjusted_return`
- 看空信号以「方向命中」为准，不再误标 0% 胜率
- C 路径优先使用事件自身结构
- 顶部后续按最早发生事件分类
- 资产类别可分组
- 新增 `tests/unit/test_research_direction.py`（7 项）

### 修复 7：量能 / B1
- `volume_up_surge`（不要求颈线） vs `breakout_volume`（必须有结构颈线）
- `pullback_shrink` 明确为简单滚动代理
- B1 默认窗口改为真实两年（`lookback_years=2`）
- 新增 `tests/unit/test_volume_b1.py`（6 项）

### 修复 8：存储 / 缓存接入正常入口
- `analyze()` 成功获取后写入 Parquet 缓存
- 远程失败时按 `cache_max_age_seconds` 降级，UI 显示陈旧警告
- SQLite 持久化事件 / 结构 / 评估 / 运行
- 结构生命周期记录完整转换（None→candidate→实际状态）
- 新增 `tests/integration/test_storage_integration.py`（8 项）

### 修复 9：本地 CSV/Parquet 上传
- UI 侧栏新增上传入口（已实现）
- 真实数据获取失败时不冒充真实数据
- 新增 `tests/integration/test_chinext_replay.py`（2 项；真实快照存在时启用）

### 修复 10：综合 14 项门禁
- `tests/integration/test_final_gates.py`（12 项）
- 所有 14 项均通过其他测试模块覆盖

## 项目结构

```
configs/rules.v1.yaml            19 条规则账本（阈值/版本/来源）
src/lei_signal/
  domain/                  类型、规则加载器、确定性事件 ID
  data/                    代码标准化、Provider、复权校验、Point-in-time
  features/                SMA/EMA、ATR、摆动点、量能、筹码分布代理
  rules/                   19 条原子规则
  events/                  只追加幂等事件日志
  state/                   持续观察状态机（机会/风险分离）
  compose/                 组合解释器 + 完整分析入口
  research/                后续收益、MFE/MAE、Bootstrap、匹配基准、分组
  storage/                 SQLite 迁移 + 幂等事件写入 + 完整生命周期
  ui/                      Streamlit + Plotly（4 个 tab + 上传）
tests/
  unit/ golden/ no_lookahead/ integration/   268 tests
```

## 安装与运行

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest -q                  # 268 passed, 1 skipped
python3 -m streamlit run src/lei_signal/ui/app.py
# 访问 http://localhost:8501
```

## 真实数据获取失败（2026-08-02 状态）

本机多次尝试 `https://push2his.eastmoney.com` 与 `https://query1.finance.yahoo.com`：
- 东方财富：连接被远程断开
- Yahoo：HTTP 403 限流

按修复 8 政策：界面正确显示 `DATA_UNAVAILABLE`，并允许用户使用修复 9 新增的 CSV/Parquet 上传入口。系统**不**把合成数据冒充真实数据。

## 已知数据源、复权、时区和统计限制

- Yahoo Finance 高频请求会被 429 限流；已加入 3 次有界重试（指数退避 + sleep 可注入）
- 东方财富接口偶发 RemoteDisconnected；同样自动重试 + OSError 兜底
- 复权口径：Yahoo `auto_adjust=True`、东方财富 `fqt=1`（前复权），ValidationReport 标注
- 时区：本地交易日（pandas DatetimeIndex，UTC-naive）
- 数据不足：少于 21 根触发 `DataUnavailableError`；前 20 根三色状态必须为 `unknown`
- 统计样本来自单一标的的历史，存在生存偏差；研究页不构成任何买卖建议
- 不模拟仓位：研究层禁止出现 `position`、`shares`、`capital`、`pnl` 等字段（AST 级别门禁）
- 性能：800 根约 5-10 秒；`build_history=True` 逐日构造解释快照，量大会明显变慢
- 资产类别启发式：3-5 全字母视为 `us_equity_or_etf`；非标准格式返回 `unknown`，不猜测
