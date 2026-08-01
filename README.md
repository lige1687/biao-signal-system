# LEI 技术信号研究系统（lei-signal-lab）

> LEI 双均线与顶底结构的**技术信号识别、解释与历史有效性研究系统**。
> **不是自动交易系统**——不下单、不计算仓位、不管理资金、不输出确定性买卖建议。

旧 `licai` 项目继续保留为只读参考；本项目按 `2026-08-01-lei-full-signal-system-architecture.md`
重新实现，**仅移植**确认摆动点、point-in-time、canonical hash、东方财富适配器与
SQLite 迁移模式，**不移植**任何账户、资金、下单、Plan Guardian 或旧策略参数。

## 核心规则

- 颜色：绿色 = Close > EMA20 且 Close > 20日前收盘；黑色 = 两者均小于；灰色 = 已就绪但两组条件均不成立（方向分歧，需要关注，不等于卖出）。
- 共同确认：读取**当前状态**，不要求 EMA20 穿越与 SMA20 确认在同一天发生。
- 长周期背景：日线/周线 EMA60 vs EMA120，**不得**作为底部识别硬门槛。
- C 生命周期：触及 C 永久失效，后续上涨不能复活。
- B1：信号发生时已确认、过去两年内、最近的摆动高点；不存在仍产生信号。
- 顶底可并存：界面显示冲突而不是静默覆盖。

## 目录结构

```
configs/
  rules.v1.yaml            规则账本(全部阈值/版本/来源)
src/lei_signal/
  domain/                  类型、规则账本加载器、确定性事件 ID
  data/                    代码标准化、Provider、复权校验、Point-in-time
  features/                SMA/EMA、ATR、摆动点、量能、筹码分布代理
  rules/                   19 条原子规则(颜色/双均线/长趋势/反包/顶底/关键性波动/量能/筹码/B1)
  events/                  只追加事件日志(幂等)
  state/                   持续观察状态机
  compose/                 组合解释器(支持/冲突/风险)+ 完整分析入口
  research/                后续收益、MFE/MAE、Bootstrap、匹配基准、分组
  storage/                 SQLite 迁移 + 幂等事件写入
  ui/                      Streamlit + Plotly 界面
tests/
  unit/                    单元测试
  golden/                  黄金样例
  no_lookahead/            无未来函数门禁
  integration/             集成测试 + 12 项验收门禁
```

## 安装与运行

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest -q                  # 全部测试
python3 -m streamlit run src/lei_signal/ui/app.py
# 访问 http://localhost:8501
```

## 验收门禁

`tests/integration/test_acceptance_gates.py` 对应架构第 13 节 12 项验收：

1. 追加未来行情不改变旧日期特征/事件/状态
2. 摆动点使用确认日，不使用实际拐点日
3. 反包在 60/120 日线空头时仍被记录
4. 6 月短期转强 + 8 月长趋势改善 → 升级为趋势增强，不要求新交叉
5. 触及 C 后永久失效，后续上涨不复活
6. 顶部被新高解除后不能再参与 Top+Black
7. 黑色与 `Close < EMA20 and Close < Close(t-20)` 逐日一致
8. 前 20 根为未知，不误标灰色
9. B1 不存在仍产生信号，且 B1 永远不是 3R 门槛
10. 周线不会把周五数据泄漏到周一至周四
11. 同样数据重复运行产生完全相同的事件 ID
12. 每条界面提示都能追溯到规则、版本、输入值和数据日期

## 工程纪律

- 阈值全部来自 `configs/rules.v1.yaml`，必须同时提升 `version`。
- `research_proxy` 必须在界面与 reason_cn 中明确标注。
- 不得为了回测结果修改公式。
- 数据错误显式 `DATA_UNAVAILABLE`，不得静默当作「无信号」。
- 不实施自动交易、仓位、资金与账户系统。

## 已知限制

- Yahoo Finance 在高频请求下会被限流。已加入有界重试（3 次、指数退避）。
- 东方财富接口也偶有 `RemoteDisconnected`，同样自动重试。
- 一次性分析时间随样本量增大而增长（800 根约 5-10 秒）。
- 筹码分布是**代理**：把成交量按价格区间均匀分配，不代表真实持仓成本。
- 东方财富 fqt=1 前复权；Yahoo auto_adjust=True。复权口径已在 ValidationReport 标注。
- 时间戳按本地交易日（pandas DatetimeIndex, UTC-naive）口径。
- 统计样本来自单一标的的历史，存在生存偏差；研究页不构成任何买卖建议。
