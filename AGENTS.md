# 项目级约束（对所有 agent 生效）

## 第零步：任何技术改造之前，先读策略文档

本系统是**规则型主观趋势交易系统**的技术实现，不是通用行情工具。任何改造
（新功能、改规则、改 UI、改预计算、改数据层）动手前，必须先读策略文档，
说清这次改动服务于策略体系的哪一层，否则不得写代码：

- `docs/trading-spec-v1.md` — 交易系统规格，**最高溯源依据**。体系分层：
  道路（双均线方向，EMA 预警 + SMA 确认）→ 路牌（顶底构造 / 关键性波动 /
  量能异常，只预警不必然反向）→ 入场触发（A 回调 / B 密集突破 / C 2B 破底翻 /
  D 假突破，四模块独立，进出同一逻辑）→ 过滤纪律（盈亏比 ≥3、九条无交易条件）。
  一切 `research_proxy` 规则必须可追溯至本文档某一节。
- `configs/rules.v1.yaml` — 规则账本（阈值 / 版本 / 来源），不硬编码、不擅自调参。
- `.claude/skills/macd-reading/SKILL.md` — MACD 唯一合法口径（强度非转折）。
- `docs/plan-sector-trend-page.md` — 板块层方案（阶段 / RS / 宽度口径与红线）。

两条推论：
- 判定与 UI 输出必须用策略自己的语言（阶段、路牌、触发条件、失效位），
  不得发明与策略体系无关的新概念。
- 基本面 / 消息面只做**叙事标注层**（解释「为什么」），永不参与技术判定、
  不做硬过滤——与 Round 4 市场环境层「独立分组研究、不硬挡信号」同一原则。

## UI 层：只改 web/，不改 Streamlit

- **Streamlit UI 已冻结**（`src/lei_signal/ui/`，含 `app.py`、`echarts_kline.py`、Plotly 相关）。
  用户已不看 Streamlit 界面：任何新需求、修复、重构都**不要动这个目录**。
- 一切 UI 开发在 **`web/`**（React + Vite + ECharts 前端）进行。
- `src/lei_signal/ui/echarts_kline.py::serialize_result` 被 Web API 复用为 K 线
  JSON 序列化口径，但它属于冻结目录。**需要扩展图表数据时不要改该文件**：
  在 `src/lei_signal/api/` 层新建纯函数计算，再在 `routes/symbols.py::_detail_dto`
  里合并进 chart dict（先例：`macdEvents`，见 `src/lei_signal/api/macd_events.py`）。

## 其他既有约束（提醒）

- 判定权在 Python 规则层；UI 只做展示，不在前端重新计算信号。
- MACD 口径唯一来源：`.claude/skills/macd-reading/SKILL.md`（强度非转折、
  金叉/死叉不是买卖点、必带盲区补齐、必标研究代理）。
