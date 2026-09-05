# 情绪面数据模块 → Agent 超级入口·接入说明

> 写给：Agent 超级入口的实现 agent（plan-agent-superentry-v1 §4.I 情绪面插槽，
> 决策 D8）。写于 2026-09-05，情绪数据模块已就绪并提交，本文是接线指引。
> 上游实验：`docs/experiments/retail-mania-threshold-2026-09-04.md`（散户热度
> 口径与阈值回测，进行中）。

## 1. 一句话

情绪面插槽的数据源已就绪：`src/lei_signal/copilot/sentiment.py`（纯只读模块，
独立可用、已带降级），你只需把它接到推荐卡 DTO、一个新端点、/ops 区块三处；
**它只做叙事标注，不参与评分、不硬过滤**（红线同消息面/基本面）。

## 2. 数据模块 API（已提交，勿重复实现）

```python
from lei_signal.copilot import sentiment

sentiment.load_sector_sentiment() -> dict
# {"available": bool, "as_of": str, "heat_meta": {metric, window_days,
#   rule_version, n_pool}, "by_board": {BK代码: {name, level, stage,
#   heat_pctile, state: warning|hot|cold|neutral, state_cn, note_cn}},
#  "hot_boards": [...最多8], "cold_boards": [...最多8], "note_cn": str}
# 数据缺失（快照无热度）时 available=False，by_board={}，不抛异常。

sentiment.build_symbol_index(sentiment包=None) -> {个股代码: 板块热度记录}
# 个股→所属板块（成分股反查，多板块取热度状态最极端的）。前缀格式 sh600519。

sentiment.symbol_sentiment_cn(symbol, index=None) -> str | None
# 单标的标注文案，如 "电子：散户情绪偏热（80分位）"。未覆盖返回 None。

sentiment.margin_regime_cn() -> dict | None
# 大盘融资环境（两融余额20日变化）：{"rzye_yi", "chg_20d_pct",
#  "regime": expansion|contraction, "regime_cn"}。网络失败返回 None。
```

## 3. 三个接入点（建议实现，改动都很小）

**① 推荐流水线（§4.A 排序层情绪槽）**
- `RecommendItemDTO` 加 `sentiment_cn: str | None = None`；
- `build_recommendation(...)` 加可选参 `sentiment_index: dict | None = None`，
  循环内 `sentiment_cn=sentiment.symbol_sentiment_cn(it.symbol, sentiment_index)`；
- **不要把 sentiment 状态加进 score 公式**（回测阈值未定案，V1 只标注；
  定案后是否参与排序另开会话决策，见 §5）。
- `SectorPickDTO` 可加 `heat_state_cn: str | None = None`，pick_sectors 直读
  sector_rows 的 heat_warning/heat_hot/heat_cold + heat_pctile 生成。

**② 新端点 `GET /api/copilot/sentiment`**
```python
@router.get("/copilot/sentiment")
def get_sentiment():
    s = sentiment.load_sector_sentiment()
    s["margin"] = sentiment.margin_regime_cn()
    return s  # dict 直返（本路由风格）
```
前端 AgentConsole/工作台/板块页均可消费（工作台右栏可加热度小卡）。

**③ /ops 清单页情绪区块（§E）**
- 组装时调 `load_sector_sentiment()` + `margin_regime_cn()`；
- 区块内容建议三行：融资环境一句话｜过热警示板块 Top3（名称+分位+阶段）｜
  持仓相关板块状态（板块代码来自 portfolio_groups 赛道→BK 映射，可复用
  板块页 FOCUS_SEED 的映射思路：cn_info→BK1215/BK1036 等）；
- `available=False` 时整块显示「情绪面：数据累积中（约需 20 个交易日资金流）」。

## 4. 红线与措辞纪律（验收时自查）

- 只标注/排序参考，**不硬过滤、不进技术判定、不出买卖点**（AGENTS.md）；
- 文案中性：「散户偏热/过热警示/冰点/中性」，**禁止**「大概率下跌/该卖/见顶」
  ——回测中间结果显示过热≠必跌（见实验报告 §4.1 发现 C），措辞由
  rules.v2.yaml retail_heat 段阈值终案后统一升级，代码里不要写死结论句；
- 所有输出标 research_proxy；数值只直读快照字段，不推算不冒充。

## 5. 数据现状与恢复时间线（2026-09-05）

| 数据 | 状态 |
|---|---|
| 板块热度（heat_*） | **暂时空**：资金流历史因东财接口封禁清零重建中，每日 clist 快照通道正常累积，约 20 个交易日后 n_pool 恢复至 ~140（一二级板块）；东财解封后重拉可立即恢复 120 日 |
| 两融环境 | ✅ 已可用（800 日历史，东财 datacenter 通道不受封禁影响） |
| 阈值（hot 90/cold 10） | 占位值，rules.v2.yaml retail_heat v0.3.0；回测终案后升版，你的代码读账本/快照字段即自动跟随，无需改 |

## 6. 验收建议

- truth table：快照无热度 → available=False + 「暂未接入/累积中」不阻塞推荐；
  有热度 → 标注文案出现且含分位数；未覆盖标的 → sentiment_cn=None。
- 接地：sentiment 文案不新增数值判定（分位数直读快照）。
