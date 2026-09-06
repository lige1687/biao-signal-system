# 经验索引（experience.json）· 格式规范与维护约定

> 建立日：2026-09-05。目的：把回测/实验的定案结论变成**机器可查的
> 条件→胜率经验**，供推荐流水线与 Agent 讨论引用（自主模式的依据层）。
> 设计取舍：当前规模（定案几十条）用**结构化索引 + 键值匹配**即可，
> 不引入向量检索/RAG——等条目过千再考虑，避免过度工程（省 AI 调用纪律）。

## 一、检索模型

一条「经验」= 一个 finding：**在什么条件下（match），历史结果如何
（direction/metrics_cn/conclusion_cn）**。查询方传入条件字典
（如 `{"signal": "module_A_stable", "pool": "industry_etf"}`），
索引层做**情境匹配**：查询与经验的 match **共有的键**取值必须一致；
match 缺失的键视为通配（该经验与此键无关，仍适用）。命中即返回该
finding（含来源报告，可溯源）。空查询不返回任何经验（不兜底全量）。

## 二、受控词表（match 的键与取值，不许自造）

### signal（信号/规则）
| 值 | 含义 |
|---|---|
| `module_A_stable` | A 稳健档（稳定上升趋势回调，spec §9 模块A） |
| `module_A_early` | A 早期档（EMA20 拐头即入） |
| `module_B_breakout` | B 模块（均线密集区突破） |
| `module_C_2b` | C 模块（2B/破底翻反转） |
| `module_D_fakeout` | D 模块（假突破反向） |
| `exit_rule` | 退出/止损规则 |
| `breadth_regime` | 宽度档位（B200 三档等环境规则） |
| `sentiment_regime` | 散户情绪状态（追涨/冰点等） |
| `combo_overlay` | 多腿组合叠加 |

### pool（标的池）
| 值 | 含义 |
|---|---|
| `index` | 指数本体 |
| `broad_base_etf` | 宽基 ETF（沪深300 等） |
| `industry_etf` | 行业 ETF |
| `etf_mixed` | ETF 混合池 |
| `single_stock` | 个股 |
| `overseas` | 海外 |
| `a_share_basket` | A股指数等权篮子 |

### 其他可选键
`market`（A股/美股）、`dimension`（exit/entry/risk）、
`regime`（牛市/熊市/横盘——报告切片时用）。

**新键需先在本文件登记**（写清含义与取值），再用于条目。

## 三、条目 schema（experience.json 顶层）

```json
{
  "version": 1,
  "note_cn": "……",
  "entries": [
    {
      "id": "exp-2026-08-25-a-pool-expansion",
      "report": "docs/experiments/etf-expansion-report-2026-08-25.md",
      "date": "2026-08-25",
      "verdict": "mixed",
      "one_liner_cn": "……",
      "findings": [
        {
          "match": {"signal": "module_A_stable", "pool": "industry_etf"},
          "direction": "negative",
          "confidence": "defined",
          "metrics_cn": "全段 -0.353R / 样本外 -0.764R（191 笔）",
          "conclusion_cn": "A 稳健档在行业 ETF 池整体亏损，关闭推荐"
        }
      ]
    }
  ]
}
```

字段约定：
- `direction`：`positive`（历史支持）/ `negative`（历史反对）/ `neutral`（无差异）；
- `confidence`：`defined`（预注册定案）/ `observed`（观察级，未定案）；
- `metrics_cn`：大白话指标（「每笔平均赚多少倍风险金额」口径），**禁止裸写
  黑话缩写**——expR/PF/Calmar 等必须带中文注解或换算说法；
- `conclusion_cn`：一句话，给 Agent 直接引用；
- findings 可多条：一份报告的不同切片各成一条。

## 四、维护约定（对后续所有回测生效）

1. **新回测结案时**：在 registry.json 登记之余，**必须**同时把核心结论
   拆成 findings 补进 experience.json（预注册判定的用 `defined`，
   探索性观察用 `observed`）。缺这一步视为归档未完成（与实验归档
   规约同级）。
2. **存量补充**：非定案报告暂不入索引；某条经验被推翻时，**不改旧条目**，
   新增条目并注明取代关系（`supersedes: "旧条目id"`），保留审计链。
3. **词表演进**：新信号类型/新池类型先登记 §二 词表，再写条目。
4. 本文件与 experience.json 一起提交，INDEX.md 不强制同步（人读导航）。
