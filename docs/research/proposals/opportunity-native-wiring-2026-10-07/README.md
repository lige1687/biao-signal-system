# 机会特征接线：一页排队建议（2026-10-07）

## 一句话结论（大白话）

**先把“离失效位多远”和“上方目标多远”说准，再接PPO强度；当前三项都不能直接启动新的机会研究。** 旧S01周度合同原样通过了声明审查，但它代表旧的两指数研究，不能替本轮A3机会取得执行资格。

范围沿用最近[六ETF输入交接](../../../experiments/raw/six-etf-x-only-input-package-2026-10-06/README.md)：510300、510050、510500、588000、512400、512800，试点截至2026-06-26；输入为接续分红拆分的研究价格，单位/币种仍有未知。这里是接线建议，不是新冻结合同。

| 顺序及金融用途 | 已有精确定义 | 原生映射与当前能进入的验证 |
| --- | --- | --- |
| **1 风险距离**：离原失效位还有多远 | 原规则A取事件`evidence.close`；C取A3触碰日至触发日最低价`evidence.stop_price`；原始价差=A−C。C缺失或C≥A不可算。ATR20简单平均口径已有，但本轮选价差、百分比还是ATR倍数尚未固定。 | 没有对应的`feature.kind`或本轮独立定义ID；`mixed.swing_rr_distance@1.0.0`使用另一组摆动点，不能替代。现在可做定义核对；下一步先确认输出单位，再提出读取原生事件字段的最小适配草案。生产缺失占位0不得变成研究观测。 |
| **2 B1空间**：上方已知目标有多远 | 730自然日内、截至当日已确认且高于收盘的严格三左三右高点，取时间最近者；无目标保留null。旧对象`research.space.prior_upper_pivot@1.0.0`主量为(B1−close)/ATR20。 | `space_prior_target`只与旧周度、252连续资料及旧ATR递推版相符；机会版采用原生A3与ATR20简单平均，不能直接套用。旧合同可审声明；机会版先写清事件时点/ATR差异，再设计人工边界检查。 |
| **3 趋势PPO**：比较两条均线分散的强弱 | 原包身份`research.selection.ema12_26_normalized_spread@0.1.0`，日线有符号值=100×(EMA12−EMA26)/EMA26。旧用途在完整周末、同类绿色候选中比较；强度不等于转折，破线和均线拐头仍需另看。 | 当前原生kind和全局定义登记均无此对象；本机只有原研究登记及另一种补充评价合同。先补原计算器/目录/完整合同，再核EMA起算、缺口恢复及252连续报价资格；不把特征ID填进kind。 |

**合同四项盘点。** 风险距离：本轮未来观察目标（target）、已有信息对照（baseline）、训练/评价日期（split）及机会资料资格/数量（qualification）均未固定。B1：旧S01已固定下一日至第21日收盘变化、四项对照（过去60日最高价距离/20日涨幅/20日波动/60日均线距离）、2025及2026上半年两期，以及两指数356条/178日的资格声明；这些不是六ETF机会字段。PPO：旧研究已固定同样20个收盘间隔目标、40项对照、2025和2026上半年两期；本机补充合同保留了具体日期与原件指纹，但缺原40项明细和完整计算定义。本轮三项的四类合同字段均保留未知，不搬用旧样本量。

**最小下一步。** 先补原510300机会适配器/事件到去重案例的映射，以及已验收机会质量定义草案；六ETF的新事件、B1/C/ATR字段资格和数量仍未核定。原PPO材料缺`weekly_ppo.py`、`research-feature-catalog.json`、原`contract.json`及`model-metadata.json`实体，已知出处/指纹见[gaps.json](gaps.json)。共享缺口补齐并确认风险距离单位后，才适合提出单字段接线和人工边界检查；新的完整workflow运行另待授权。旧PPO结果未确认稳健增量，保留原结论，不据此调阈值。

本次只对[旧S01完整合同](../../../experiments/raw/space-prior-target-2026-09-30/return-freeze/contract.json)调用已验收`--review-workflow-contract`：退出0，`declaration_valid=true`、`execution_authorized=false`；[原输出](declaration-review.json)。其余两项及机会版B1只列缺口，没有制造合同。定义依据：[机会字段边界](../../../experiments/raw/native-opportunity-eight-etf-input-inventory-2026-10-06/README.md)、[S01旧协议](../../../experiments/raw/space-prior-target-2026-09-30/protocol.md)、[PPO已完成报告](../../../experiments/weekly-ppo-information-2026-10-05.md)；代码行号、指纹和精确未知项见附带JSON。
