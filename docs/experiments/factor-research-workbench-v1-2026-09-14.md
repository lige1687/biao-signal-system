# LeiSignal 通用因子研究能力首轮（factor-research-workbench-v1）-2026-09-14

> 适用：`docs/research/experiment-report-template.md` v1.1.0。
> 执行者：ZCode/GLM（`builtin:bigmodel-coding-plan/GLM-5.3-Flash`）；主控：当前 Codex 任务（回调后独立复核）。
> 状态：**执行者交付，待主控回调复核；复核通过前不构成验收。**

规范版本：`experiment-backtest-principles.md` v1.1
策略规格版本：不适用（方法论与验证类任务，不改交易规则）
规则账本版本：不适用（未改 `configs/rules.v1.yaml`；生产规则只读）
冻结协议：`docs/superpowers/plans/2026-09-14-factor-research-workbench-v1.md` v1.0.0；
任务合同与保护基线见 `docs/experiments/raw/factor-research-workbench-v1-2026-09-14/task-contract.md`
与 `protection-baseline.json`
定义规范与登记表：`definition-standard.md` v1.1.0；`definitions.v1.json` v1.2.0
（SHA-256：`baseline` 中逐文件记录，登记表本轮只读）
对象引用：`mixed.momentum.raw@1.0.0`、`mixed.rv20@1.0.0`、`trend.distance50@1.0.0`、
`trend.distance200@1.0.0`、`breadth.csi300.b50.common@1.0.0`、
`breadth.csi300.b200.common@1.0.0`（全部经 `resolve()` 解析展开卡）；候选
`candidate:lei.dual_ma.bull_state@draft-1`（不登记，卡草案在 raw）
实验 manifest：三次正式运行各带 `manifest.json`（路径见 §8）
定义清晰程度 / 数据资格 / 实现核验 / 有效性证据 / 生产授权：
explicit（登记卡）/ synthetic_only（真实资料未消费）/ 已核（见 §8.1）/
**无（本轮不证明任何因子有效）** / **not_authorized**
研究状态：探索（工具建设）
生产与真实交易授权：无

## 一句话结论（大白话）

我们自己的因子研究工具第一轮建成了：一套通用接口能算已登记的 6 个技术指标加
双均线候选状态，按对象类型自动选择正确的检验方法（横截面排名、状态真/假对比、
宽度跨日期对照），把"反复挑参数、偷看未来"的风险逐项摆出来，并把策略的钱账
分成资金贡献、单动作对比、风险模型三层解释。全部用合成的假数据验证：三类
端到端案例共 50 项手算期望全部对上，94 项测试和 316 项相关回归通过。它只是
证明"算法没算错"，**不证明任何因子能赚钱**，没有真实资料结论，没有生产授权。

## 1. 决策问题与停止条件

- 资金用途：不直接涉及资金；为后续"该相信哪个特征"提供可核查工具。
- 本轮要改变的决策：消除"没有通用检验工具"这一决策障碍（原则 §1 基础研究）。
- 通过条件（规格 §7 完成条件）：同一 API 适配不同合成实体集合；数值/状态/宽度
  三类完整输出；诊断分流；尝试史/切分/重叠可见；归因可核；不适配项诚实不运行。
- 停止条件：政策歧义、需新资料/依赖、保护文件变化、预算耗尽（均未触发）。

## 2. 冻结范围与当时可知的信息

| 项目 | 冻结内容 |
|---|---|
| 产品池 | 合成实体（alpha/beta/gamma/delta/epsilon；m1–m4）；固定池是实验协议不是平台边界；库不写死14产品 |
| 规则与参数 | 全部引用登记卡参数并逐一绑定核对；候选绑定生产函数源码哈希 |
| 数据与区间 | 合成等比价格/合成日K/合成成员链，输入文件 SHA-256 冻结于协议 |
| 信号与成交时点 | 观察日收盘可知；目标是 t+1→t+22 的**测量目标**，非可成交开盘或账户收益 |
| 尝试史 | 见 §6；协议 `attempt_history` 记录夹具 v1 放弃原因 |
| 主要评价方式 | 协议冻结的手算期望逐项对照（`quality.json`），不用被测输出生成期望 |

## 3. 对照设计

工程核验类任务：无收益对照（不适用，未检验收益）。实现与期望的独立性靠
`derive_expectations.py`（不 import lei_signal 的独立算术）保证；等价于
"独立期望值来源"合同。三类案例互为接口对照（3实体 vs 5实体同一API）。

## 4. 结果与完整账户核对（合成）

第三类案例按规格 §4 独立手算例核对（人民币元，容差0.01）：

| 账户 | 期末总资产 | 净损益 | 产品净贡献 | 核对 |
|---|---:|---:|---:|---|
| base（100本金，买1份@50费1，分红2到账，期末价55） | 106.00 | 6.00 | 6.00 | 通过（差额<容差） |
| receivable（分红仍应收） | 106.00 | 6.00 | 6.00（含期末应收2） | 通过 |
| variant_exit_on_d3（d3以55卖出，费率1%→0.55） | 105.45 | 5.45 | 5.45 | 通过 |

受控比较：唯一动作差异=d3卖出，净损益差 −0.55 全部归给该动作；
年化差/回撤差仅作描述，不并入资金贡献。全现金、映射冲突、账户字段混入
actions 的拒绝分支均有测试。

## 5. 收益、风险与代价解释

不适用（合成算法验证）。三类诊断输出的解释边界见
`docs/research/factor-lab-usage.md` §三：IC≠赚钱、无通用及格线、宽度一条
观测是一条证据、等权分组只是诊断、剩余收益不自动叫独特alpha。

## 6. 证据强度与反例（失败史，全部保留）

**正式运行计数（规格预算：3类×初跑1+纠错1）**：

- `runs/case-*-run-01`（初跑×3）：全部退出0、期望全过。
- `runs/case-*-run-02`（纠错×3）：因 manifest 缺候选卡修正后重跑，全部退出0。
- 预算内计数用满：3 初跑 + 3 纠错，无超支。

**开发期修复（正式运行前，计入失败史）**：

1. 夹具v1：合成代码 `X` 与复用 `build_marks` 的6位代码 zfill 假设冲突 →
   改 `100001` 重建（协议 attempt_history 已记）。
2. 期望核对两处手算错误被运行暴露：跨段计数应为样本对（8观察日×3实体=24）；
   宽度 SMA 是"有效收盘"滚动（成员缺1天报价不使后续200天失效，我方推导
   脚本原按日历窗建模是错的）→ 修正推导脚本与协议后重新冻结。
3. 代码缺陷4处：merge indicator 字符串真值判断、bars 实体名前缀、NaT
   available_at 误拒、CSV symbol 被读成 int——均有对应修复与测试。

**反例/负向测试已固化**：未知对象、错版本、用途不符、输入缺列、重复键、
乱序/重叠切分、非 none 预处理、未带时区时刻、标签未晚于观察、目标未成熟、
常数分数、并列拆散请求、q≠2、误用横截面IC于宽度/布尔、已看过保留段、
重复试验ID、映射冲突、账户字段混入 actions、覆盖已存在输出目录、current 指针、
输入哈希篡改。

**局限**：合成验证只证明算法与合同正确；未接入真实资料（只读资格检查批次
未使用，理由见 §8）；"风险尚未排除"是常驻输出，本工具不能证明没有过拟合。

## 7. 真实资金可执行性

不适用（无真实信号、无账户运行、无交易建议）。

## 8. 限制、复核与复现

- 不能支持的结论：任何"某因子有效/可交易"的表述；真实资料资格结论；
  生产授权。
- 未实现（明确列出，不伪称通过）：双均线候选正式登记与真实有效性研究、
  稳健统计推断/多重试验校正、风险模型回归、外部库安装、前端研究台、
  生产接入。
- 真实资料只读资格检查（≤1批）：**未执行**。规格定义为可选项且非前置；
  本轮无其结论产出，三类合成示例按计划完整交付。
- 复核性质：待主控回调独立复核（本报告为执行者交付）。
- 保护核对：29个受保护文件 + 上轮 raw（408文件）哈希与开工基线一致；
  允许修改的 registry/INDEX 以追加方式更新，registry 261条 JSON 校验通过。

### 8.1 本轮实际调用的定义绑定与运行证据

**实际计算绑定（对象→代码函数）**：

| 对象/候选 | 实际函数（只读复用） |
|---|---|
| mixed.momentum.raw@1.0.0 | `definitions.quote_features` 列 momentum |
| mixed.rv20@1.0.0 | 同上列 rv20（ddof=1、√252） |
| trend.distance50/200@1.0.0 | 同上列 distance50/200 |
| breadth.csi300.b50/b200.common@1.0.0 | `definitions.breadth`（E200 共同分母） |
| candidate:lei.dual_ma.bull_state@draft-1 | `indicators.compute_features` + `lei_color.classify_colors` + `dual_ma.dual_ma_bull_state`（未改生产） |
| 未来目标 t+1→t+22 | `momentum_prototype.build_targets`（缺端点不顺延） |
| Rank IC 数学核 | `momentum_prototype.rank_diagnostic`（并列平均名次） |
| 资金贡献/核对/账户比较 | `factor_diagnostics.capital_contributions / reconcile / compare_accounts` |

**运行证据（命令与退出码）**：

```sh
# 三次正式运行（另有一次同命令的 run-01 初跑与 run-02 纠错，均退出0）
python3 scripts/run_factor_lab.py --protocol <raw>/protocol-1-numerical.json --out <raw>/runs/case-1-numerical-run-02   # exit 0
python3 scripts/run_factor_lab.py --protocol <raw>/protocol-2-state.json     --out <raw>/runs/case-2-state-run-02       # exit 0
python3 scripts/run_factor_lab.py --protocol <raw>/protocol-3-attribution.json --out <raw>/runs/case-3-attribution-run-02 # exit 0
# 测试与回归（相关回归第1次即通过，第2次未使用）
python3 -m pytest tests/unit/test_factor_lab_*.py tests/integration/test_factor_lab_cli.py -q   # 94 passed
python3 -m pytest <9份既有相关测试 + 6份新测试> -q                                                # 316 passed in 28.43s
ruff check <新包+新测试+CLI>   # All checks passed
```

`<raw>` = `docs/experiments/raw/factor-research-workbench-v1-2026-09-14`。
每目录含 `manifest.json`（规范绑定、registry 规范化哈希、展开卡、13个代码文件
SHA-256、输入哈希、目标/切分协议、attempt_history、执行模型、
production_authorization=not_authorized）与 `quality.json`（16/23/11 项手算期望
逐项对照全过）、中文 `summary.md`（常驻合成验证标题）、完整 `run.log`。

**资金核对最大差异**：合成三层案例 0.00 元（容差 0.01）。
**限制**：全部输入为合成；历史到达时间证实不适用；无成交容量验收；
`definitions.calculate` 的其他登记对象仍为未接入（factor_lab 同样拒绝）。

## 9. ARCHIVE（结案时保留——本轮为交付待复核，登记 verdict=mixed）

- 结案日期：2026-09-14（交付日；验收待主控）
- 最终结论：保留继续验证（工具可用；有效性零声明）
- 生产采用：未授权
- 原始数据与复现入口：raw 目录协议/夹具/独立期望/运行产物
- `registry.json`：已登记（方法论与验证 / mixed）
- `INDEX.md`：已补 §7 表行；路线图已追加交付入口

## 10. 给主控的逐里程碑证据建议（OKR 由主控写入，执行者不写、不勾完成）

方向 `okr-cd1a0bd5532c`、任务 `okr-3fa8363be729`（5项完成标准初始均 false）。
建议主控回调后按以下证据独立复核再决定进展：

1. **通用计算与元数据**：`tests/unit/test_factor_lab_contracts.py` +
   `test_factor_lab_adapters.py`（55项）；3/5实体同一API、参数绑定、
   缩放/追加不变性。
2. **IC与状态诊断分流**：`test_factor_lab_diagnostics.py`（17项）；
   `runs/case-1.../diagnostics_mom3.json`（每期IC=1.0, n=3）、
   `runs/case-2.../diagnostics_*.json`（state_outcomes / not_applicable /
   time_series_state 三分支）。
3. **试验史/切分/重叠**：`test_factor_lab_validation.py`（18项）+
   `runs/case-1.../validation.json`（dev/validation 各24对标签跨段被点出、
   trials 全保存、holdout 未见标记）。
4. **三层归因入口**：`test_factor_lab_attribution.py`（14项）+
   `runs/case-3.../attribution.json`（106/6/6 手算核对、受控 −0.55、层3 not_run）。
5. **端到端与回归**：CLI 重跑任一协议至新目录应退出0且50项期望全过；
   316项相关回归；保护基线逐文件哈希比对。

建议措辞边界：以上只能支持"通用研究工具已建成且算法可核"，
**不能**支持"已有有效因子"，不构成生产或真实交易权限。

> **2026-09-15 主控纠正指针（追加，不改原文）**：本报告为首轮交付记录。主控初审（mixed）发现 R1–R4 必修问题：时间资格未实际消费统计（NaT 仍出 IC、跨段/未成熟样本仍计 clean）、冻结合同未在运行前核对、账户条件未核齐即宣称「only」、空期望可空转为通过。全部返修见 [factor-lab-concentrated-repair-2026-09-14](factor-lab-concentrated-repair-2026-09-14.md)（含主控复核 [factor-lab-controller-review-2026-09-14](factor-lab-controller-review-2026-09-14.md)）。本报告 §8.1 的运行与回归证据保留为历史；其中 50 项期望、部分断言与「attributable only」表述按返修后语义已被取代，以返修报告为准。

## 最小决策卡

| 必答项 | 本轮答案 |
|---|---|
| 决策与资金用途 | 建成自有因子研究通用工具，消除"无检验工具"障碍；不涉真实资金 |
| 基准与增量 | 对照=手算独立期望与既有函数复用（不复制公式）；增量=同一API覆盖定义→计算→检验→审计→归因全链 |
| 收益解释 | 不适用：零真实收益运行；合成资金核对106/6/6通过 |
| 代价与执行 | 预算：3初跑+3纠错用满、回归1/2次、真实检查0/1批；未安装外部库 |
| 证据与结论 | 50项期望+94测试+316回归全过；结论=保留继续验证（工具可用，有效性零声明） |
| 下一步与边界 | 主控回调复核→真实资料只读资格检查另批授权→候选卡登记另议；无生产授权 |
