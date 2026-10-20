# factor_lab 能力盘点（Task 0，2026-09-14）

任务：`docs/superpowers/plans/2026-09-14-factor-research-workbench-v1.md` v1.0.0。
范围：只盘点本轮要复用/薄适配/延后的能力，不重查全部历史日志。

## 1. 已核到的复用面（实际 API 与范围）

| 能力 | 实际代码 | 已实现范围（本次核对） | 本轮做法 |
|---|---|---|---|
| 定义解析 | `research/definitions.py::load_registry / resolve / validate_registry` | 81 张卡；结构/身份/依赖/容差/时区校验；production 强制 not_authorized | 只读调用；候选卡不进登记表 |
| 数值特征 | `definitions.quote_features` | momentum（第253条首算）、sma50/200、distance50/200、rv20（ddof=1、√252 年化）、rv_rank | 薄适配列暴露，不复制公式 |
| 均线状态 | `definitions.trend_state` | above/cross_up/recovered（严格大于） | 经 quote_features 间接复用 |
| 宽度 | `definitions.breadth` | E200 共同合格分母、coverage≥0.9（等于有效）、缺成员/零分母/覆盖不足返回缺失原因 | 薄适配；合成成员链 |
| 统一计算入口 | `definitions.calculate` | 仅 momentum、trend.sma50/200、breadth.*.common；**不含 rv20/distance50/distance200 的直接分发** | factor_lab 自建 reference→列绑定分发，参数绑定逐一核对卡 |
| 未来目标 | `momentum_prototype.build_targets` | e=t+1 交易日、x=e 后第21（t+22）；缺端点不顺延、reason 分列 | 复用；外层加通用列/时点合同 |
| 排名诊断 | `momentum_prototype.rank_diagnostic` | 并列平均名次 Spearman 等价；<3 对/常数返回缺失原因 | 作为 IC 数学核薄映射 |
| 时点资格 | `momentum_prototype.decision_moment / parse_available_at / signal_time_violations / target_label_incomplete` | Asia/Shanghai 15:00 决策时点；无时区拒绝 | 复用于目标成熟性检查 |
| 资金归因 | `factor_diagnostics.capital_contributions / reconcile / phase_contributions / compare_accounts` | 净卖出−含费买入＋已付分红＋期末应收＋期末市值；容差 0.01 元 | 层1/层2 复用；合成台账 |
| 双均线状态 | `rules/dual_ma.py::dual_ma_bull_state` | Close>EMA20 且 Close>SMA20、两均线上升、signal_color=green；读当前状态不要求同日上穿；未就绪输出 False | 只读调用；readiness 另行记录 |
| EMA | `features/indicators.py::seeded_ema` | 首窗口 SMA 种子、alpha=2/(n+1)、前 n-1 根 NaN | 复用种子/预热规则 |
| 颜色 | `rules/lei_color.py::classify_colors` | 绿=Close>EMA20 且 Close>Close(t-20)；黑对称；灰=分歧；未知=不足21根 | 候选绑定，不由调用者填 green |
| 行动适配 | `momentum_prototype.adapt_company_events` | 未知字段（含账户字段 fee/amount）拒绝、同义字段冲突拒绝、重复/缺失 event_id 拒绝 | 层1 actions 校验复用 |
| 经济指数 | `factor_runtime.reconstructed_economic_index` | 严格 available_at 语义 | 本轮不调用（合成案例不含分红重建） |
| 数据资格 | `data_snapshot.py / data_quality.py / input_preflight.py` | 旧拒绝原因、不放宽、未知 available_at 不回填 | 保留；本轮仅最多1批真实只读资格检查（可不做） |
| manifest | `definitions.make_manifest / fingerprint / verify_sources` | 规范/代码/输入/协议指纹；registry 字节一致要求 | runner 自建同构 manifest（含候选身份），注册对象场景沿用其精神 |

## 2. 缺口（本轮补齐 = factor_lab 新包）

1. 通用"一份定义、多种用途"批次接口（ResearchBatch + metadata 合同）——缺。
2. 逐日横截面 IC 的通用列/时点输入合同（rank_diagnostic 只吃 momentum/target 两列固定名）——薄映射补齐。
3. 二元状态"状态真/假后续结果"诊断、共同宽度跨日期诊断、not_applicable 分流——缺。
4. 固定分组（仅 q=2、并列不拆散）——缺。
5. 试验史/时间切分/标签重叠检查（audit_validation）——缺。
6. 三层归因的受控协议入口（层2 结构一致性核对、层3 模型卡资格检查）——缺。
7. 统一协议运行器与 CLI、退出码合同（0/2/3）——缺。

## 3. 明确延后（本轮不做，不伪称已实现）

- 正式双均线对象登记、真实有效性研究；稳健统计推断/多重试验调整；
- 适配风险模型回归（本轮只做模型卡与输入资格检查，缺料即 not_run）；
- Alphalens/Qlib/vectorbt 安装（复核结论保留：候选"第二算盘"需另行授权）；
- 前端研究台、生产接入、真实 ETF 池资料补齐（40请求/20材料计划后置）。

## 4. 现状结论

- 上轮 S1–S3 已收口（controller-review v1.5.0 §13：必修项无），本轮无返修义务。
- "全仓没有 IC 工具"的旧路线图表述已过时：rank_diagnostic 已存在，须复用。
- `definitions.calculate` 不支持 rv20/distance 卡 ≠ 未登记；本轮以参数绑定核对方式接入，不新增登记对象。
