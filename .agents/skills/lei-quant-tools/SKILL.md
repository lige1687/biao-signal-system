---
name: lei-quant-tools
description: 在 LeiSignal 研究中读取归档预测、辅助比较多个候选的共同误差、检查平均差额、预览固定tsfresh表达或核对交易日。用于只读研究辅助计算，不输出交易判断。
---

# 量化资源的小组件入口

服务于研究的计算和资料核对层。先读项目 `AGENTS.md` 和
`docs/research/current-standards.json`，沿用已有合同、资格、预算与研究入口。
对当前技能已有明确任务时直接执行本轮需要的工具；它不自行开展市场研究。

## 先接已有研究产物

已有新研究入口的结果目录含 `contract.json`、`preflight.json`、
`result.json`、`receipt.json` 时，优先用 `workflow-check` 检查，避免手工
抄表或压缩日期。工具核对归档文件指纹及原执行日志，复用项目对预测、
目标身份和日期的验证；不重新拟合、不写入原目录。

```bash
python3 .agents/skills/lei-quant-tools/scripts/quant_tools.py workflow-check RUN_DIR
```

当前可计算范围：日频、原合同明确使用评价期时间轴（`axis_scope: evaluation`）、
单个拟合时期、每天同一组ETF且资料完整。其他时间轴范围返回不适用。
在完整日期和固定资产集合下，原 `equal_asset` 与 `equal_date` 权重一致，
工具才按日期汇总。缺日期、每日资产不同或跨多个拟合时期时，返回
`not_applicable` 与具体原因，退出码2，不能填零、删空档或换权重求一个数。

需要检查明确的辅助时期时，可给 `--start YYYY-MM-DD --end YYYY-MM-DD`。
两端必须明确，不自动缩期。选取时期和相邻间隔数的理由先记入本轮合同；
已经看过的资料标为探索。适用后再执行：

```bash
python3 .agents/skills/lei-quant-tools/scripts/quant_tools.py workflow-hac RUN_DIR --start START --end END --nlags N
```

这里的差额固定为“旧预测误差平方减新预测误差平方”，正值表示预测误差
减小；连续目标单位是“百分点的平方”，不是百分点或收益。原研究主指标
若是RMSE（与原数据同单位的预测误差大小），仍看原报告，不拿本工具替换。
归档指纹一致只证明读取的是那次产物，不表示当前代码、来源和全套研究
资格已经重新验收。新研究仍走原冻结与发布入口。

## 计算平均差额的误差

“误差”指平均差额受波动和相邻日期联系影响的不稳定程度。
`mean-hac` 调用从 statsmodels 0.15.0 原样复用的数值核心；仅用于已经
定义的一条、等间隔观察序列，返回平均值、估计误差和资料数量。

1. 先确认同日期的候选与参照按同一口径配对，差额方向、单位与权重明确。
   多ETF资料在每个日期按冻结权重汇总，再传一条日期序列；不逐资产堆行。
2. 声明完整观察日历、等间隔频率和计算口径。缺一个计划日期时拒绝，
   不删掉缺失日期后把相隔多期的记录当相邻。
3. 显式给 `nlags`，即考虑多少个相邻观察间隔，理由写在合同里。
   结果跨度、观察频率和既有规范决定方法，不套默认长度或通用通过线。
4. 这个计算不修正已经看过资料和反复挑方案的影响；误差既可能增大也可能
   减小。固定相同差额返回零估计误差，不代表现实中已无不确定性。

下面是通用 `mean-hac` 的手填示例，差额方向和单位由调用者声明。
归档读取 `workflow-hac` 则固定使用“旧减新平方误差”；使用时分别沿用
各自的方向和单位，不将下面示例的“百分点”套到归档平方误差。

```json
{
  "metric": "同日候选预测误差减参照预测误差",
  "unit": "百分点",
  "frequency": "qualified_session",
  "calendar": ["2026-03-02", "2026-03-03", "2026-03-04"],
  "observations": [
    {"date": "2026-03-02", "difference": 1},
    {"date": "2026-03-03", "difference": -1},
    {"date": "2026-03-04", "difference": 0}
  ],
  "nlags": 1
}
```

```bash
python3 .agents/skills/lei-quant-tools/scripts/quant_tools.py mean-hac INPUT.json
```

已存在的预测及按历史片段重抽检查仍使用原评价器，本工具没有接管报告
发布验收。这里只估计给定序列平均值的误差，不输出“有效概率”或买卖判断。

## 多个候选一起比较

多个候选属于同一已冻结问题、同目标且有完整保存预测时，使用独立入口
`scripts/multiple_comparison.py compare-workflows`。先读取
[多方案使用说明](references/multiple-comparison.md)，明确候选集合、简单对手、
时间区间、抽取长度及尝试史范围。输入条件不满足时保留不适用原因。

它复用原归档收据与资料检查，同日ETF先汇总，再共同抽取连续日期片段。
只补“多个方案里挑最好者”的限定辅助计算，不重训或接管报告发布。
调用时仍沿用本轮预算；一个输入能放64列不意味着获准试64个因子。
本轮采用arch8.0.0有限Python组件及许可，使用未按方差缩放的同单位误差比较，
不支持完整arch平台或自动筛出交易信号；需要已有NumPy、Pandas和可选SciPy。

## 外部时序表达预览

`candidate-preview` 复用 tsfresh 0.21.2 的两个计算正文，先检查输入，再返回
指定日每只ETF的候选值及已有20日涨跌和波动比较列。它服务于候选公式核算，
没有正式因子ID；新效果研究仍需走现有定义、资料与冻结入口。

```bash
python3 .agents/skills/lei-quant-tools/scripts/quant_tools.py candidate-preview INPUT.json --as-of YYYY-MM-DD
```

输入字段：`schema: tsfresh-candidate-input/1.0`、`data_mode: synthetic`
或 `historical_reconstruction`、`price_series: economic_price`、非空
`source_note`、完整有序不重复的 `calendar`、明确的 `assets`、`bars`。
每行报价含 `date`、`asset`、`status: quoted`、`action_known: true` 和正数
`close`。必须使用含公司行动处理说明的价格，工具不自行复权或认定来源合格。

- `mean_abs_log_change20`：21个连续有效收盘价先取 `100*log(price)`，再用
  `mean_abs_change` 求20次相邻变化的绝对值平均，单位是每日对数变化百分点。
- `return_autocorrelation20_lag1`：这20次变化代入 `autocorrelation(lag=1)`，
  描述相邻变化的联系。使用全20项的均值和总体方差，分母为19倍方差；
  不是分别重算两个错位序列的普通相关系数，不强行限制在[-1,1]。

窗口20用于与现有表达对齐，没有按结果挑窗口。上游 `np.isclose(var, 0)`
判近零时第二项返回 `null` 及原因，绝不填0。第一项使用的对数变化与普通
涨跌百分比略有区别；`ret20_pct` 比较列仍是简单涨跌，波动列是20次对数
变化的样本标准差乘根号252，与既有口径一致。

缺报价、停牌、行动未知或无效价格会中断历史，重新积累21个价格后才可算。
每只ETF分开处理，不删缺失日期拼接；`--as-of` 必须在声明日历里，不自动
回退到较早日期。只使用截至该日的价格；读取行为不证明历史到达时间已知。
完整日历和价格口径仍需调用者先核查，输出始终标为候选预览。

实际四ETF只读示例及来源绑定见
`docs/experiments/raw/tsfresh-adoption-2026-10-02/preview-input-1.json`；
结果、人工反例和采用范围见 `docs/experiments/tsfresh-adoption-2026-10-02.md`。
这两项保留了原价格轨迹的不同表达，未证明多了有效预测信息。

## 日历辅助核对

`xshg-date` 核对 exchange_calendars 4.13.2 的上交所2026年日期快照，
已与上交所年度通知比对。它返回年度安排里的开休市状态，不替代本地
已合格官方日历，也不证明当日产品能成交、交易时段或临时变更。
超出2026年返回未知；不借用上交所日历判美国、香港或场外基金。
公布日内时刻未知，本工具不判断“某次盘中预测是否已知安排”。

```bash
python3 .agents/skills/lei-quant-tools/scripts/quant_tools.py xshg-date 2026-10-02
```

来源、范围和许可证见 [references/provenance.md](references/provenance.md)。
基础数值工具使用项目已有 NumPy；归档读取还复用项目已有 pandas 和研究模块。
多方案入口使用SciPy，本机已有1.17.1；`quant-comparison`可选依赖组记录该版本。
本轮没有安装新依赖或完整arch库；有限组件的范围见相应使用说明。
