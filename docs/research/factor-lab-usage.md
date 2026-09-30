# factor_lab 使用手册（v1，2026-09-14）

> 用大白话讲清楚：这个工具是干什么的、怎么用一步、结果怎么读、什么不能说。
> 所有正式输出都是**合成算法验证，非真实收益/有效性证据**；没有任何生产授权。

## 这是什么

`src/lei_signal/research/factor_lab/` 是一个离线研究工具包：用**同一套接口**计算
已登记的定义对象（或已声明的候选）、做预测/状态检验、检查"反复挑优"的风险、
并把策略的钱账分成三层来解释。它复用既有实现（`definitions.py`、
`momentum_prototype.py`、`factor_diagnostics.py`、`dual_ma.py` 等），
不复制第二套公式。

### 现有 API 与 Agent 调用边界（2026-09-22）

- `GET /api/factors/panel` 已存在：`api/routes/factors.py` → `FactorPanelService` → 磁盘快照；只读观测结果，不是任意因子运行接口。无需再做第二个同类面板 API。
- 面板中的评级是带历史研究日期的留痕，不是 `definitions.v1.json` 某个精确版本的新验证结论；不能直接把它当作 Agent 的因子资格证明。
- `calculate_batch` 等是本地 Python 研究入口；`scripts/run_factor_lab.py` 需要冻结协议，CLI 也不是自由运行授权。读取结果与启动研究要分开。
- 本次检查的 Copilot/Agent 路由未发现 `factor_lab` 或上述面板的专用调用绑定，不能说网页 Agent 已接通整套研究。后续优先复用现有函数/快照入口并补少量格式与权限对接，不重建计算服务。
- 外部 REST API 是数据接口；MCP 是把接口包装成 Agent 工具。包装成功不等于其数据适合 ETF 研究，也不自动允许它执行回测。FactorHub 本轮状态与证据见[复核报告](../experiments/factor-reuse-refresh-2026-09-22.md)。

## 一、当前支持的对象（分列，不含未支持项）

### 已登记卡（可直接引用，参数与登记表逐一核对）

| 引用 | 含义 | 说明 |
|---|---|---|
| `mixed.momentum.raw@1.0.0` | 252天前到21天前的涨幅 | 第253条首次可算 |
| `mixed.rv20@1.0.0` | 20期收益的样本波动（年化） | ddof=1 |
| `trend.distance50@1.0.0` | 价格相对50日均线的距离 | SMA含当日 |
| `trend.distance200@1.0.0` | 价格相对200日均线的距离 | 同上 |
| `breadth.csi300.b50.common@1.0.0` | 宽度B50（共同合格分母） | 需要**逐日成员名单**；合成输入不得称真实沪深300 |
| `breadth.csi300.b200.common@1.0.0` | 宽度B200 | 同上 |

### 候选卡（只表示源代码绑定，不是登记对象）

| 引用 | 含义 | 边界 |
|---|---|---|
| `candidate:lei.dual_ma.bull_state@draft-1` | 双均线共同确认状态：Close>EMA20 且 Close>SMA20、两均线上升、颜色为绿 | 只读调用生产函数；未就绪行记 `warmup_not_ready`，不混成有效看空样本；无任何有效性证据 |

### 未支持（登记了但没有 factor_lab 实现；调用会拒绝）

上表是2026-09-14首批接口快照，不再以“其余约75张”描述当前支持范围。
**登记不等于已接入**；还要分清统一入口、独立研究函数和CLI是否支持。

### 2026-09-22 当前入口补充（历史首批表保留）

`adapters.calculate_batch` 在首批之外已有以下精确引用，均只按当前合成协议调用：

| 引用（均为1.0.0） | 含义与限制 |
|---|---|
| `trend.sma50`、`trend.sma200` | 50/200期简单均线；已有人工作例证据，不代表投资有效 |
| `trend.above50`、`trend.above200` | 严格站上均线的状态；不是当天上穿 |
| `trend.cross_up50`、`trend.cross_up200` | 从上一有效报价的未站上变为当前严格站上；不是持仓规则 |
| `trend.recovered200` | 当前价格大于或等于200期均线；是状态，不是必须发生穿越 |
| `mixed.rv_percentile` | 波动在自身历史中的位置；v1仍为exists，存在价格整体缩放后排名大变的已知限制，不能因为可调用而称已验证 |

另有独立入口，**不自动包含在calculate_batch或CLI支持范围中**：

- `b3a_registered_v2.calculate_registered_b3a_v2`：仅 `trend.cost_basis_distance20@2.0.0`、`mixed.pullback_ma_distance@2.0.0`，合成输入；旧1.0.0不继承新版本验证。
- `b3b_ma_cluster_width.ma_cluster_width`：六均线密集宽度；数值描述，不自行套阈值或构造突破信号。
- `b3b_swing_rr_distance.swing_rr_from_bars` / `swing_rr_distance`：已确认结构间的距离比例；不能把它称为可直接交易的盈亏比。

`mixed.momentum.rank@1.0.0` 是有序名单定义，当前没有calculate_batch分支；`select_mixed` 还会筛波动并截前三，不能冒充仅按动量排序的相同对象。其他对象应逐一核实际入口，不用旧总数推断支持或不支持。

### 完整动量排序：复用已有阶段，不另建引擎（2026-09-22）

已有 `factor_runtime.monthly_decisions(..., variant="E10")` 的 **`ranked`** 字段保留所有合格对象，按动量降序、精确相等再按代码升序；不是该函数的 `selected`（前三），也不是E11的波动筛选后名单。返回值是`|`分隔文本，空文本应解码为`[]`，不能得到`[""]`。这不是`calculate_batch`/CLI新增支持，也没有新增网页Agent绑定。

调用前由研究协议保证：

- 分数与`valid_count`来自获准的同一输入；当天行只代表真实有效报价，不用旧报价前填。排序阶段本身不会从原始价格重算这些字段。
- `(date, symbol)`唯一，`symbols`唯一且为统一约定的字符串、不能含`|`；重复行会被旧入口取第一条，不会自动拒绝。
- `completed_months`由完整月份和声明的交易日历确定，不能拿截到月中的最后一行冒充月末；旧函数只使用调用者传入的日期。
- 精确解析`mixed.momentum.rank@1.0.0`及`mixed.eligible@1.0.0`、`mixed.momentum.raw@1.0.0`，留输入/代码/定义身份；仅调用`monthly_decisions`不会自动做这一项或研究用途检查。

上述是使用者义务，**不是声称已加自动校验**。人工分数检查只证明这个排序阶段能复用，不证明原始ETF输入合格、因子有效或可用于交易。调用与独立反例见[本轮报告](../experiments/factor-momentum-rank-reuse-2026-09-22.md)。

## 二、一次完整用法（五步）

### 1. 引用/准备定义

已登记对象直接写精确 `id@版本`（不写 latest）。全新因子先写候选卡草案
（放本轮 raw 目录），不进登记表。

### 2. 提供合法输入

```python
import pandas as pd
from lei_signal.research.factor_lab.adapters import calculate_batch

protocol = {
    "protocol_id": "my-study", "version": "1.0.0",
    "kind": "predictive_diagnostic",   # 或 calculation_only/state_diagnostic/strategy_explanation
    "data_mode": "synthetic",          # 本轮只接受 synthetic
    "synthetic": True,
    "timezone": "Asia/Shanghai",
    "evaluation_cutoff": "2030-01-01T15:00:00+08:00",  # 必须带时区
    "diagnostics": {"type": "cross_section_ic"},
}
prices = pd.DataFrame(...)   # 行=交易日（唯一递增），列=产品
batch = calculate_batch("trend.distance50@1.0.0", {"prices": prices}, protocol=protocol)
```

- 输入缺值**保留不删**：缺值行 `value=NaN` + `missing_reason`（如
  `warmup_history_insufficient` / `price_missing`）。
- 行键唯一：`(observation_date, entity_id)`。
- 宽度需要 `{"prices": 收盘面板, "membership_by_date": {日期: [成员]}}`；
  成员缺失/覆盖不足会给出缺失原因，不会伪装成零宽度。

### 3. 选研究问题（诊断分流）

> 返修后语义（v1.1.0 协议起）：时间资格**实际控制统计**——目标可得时间
> 未知（None/NaT）、晚于评价截止、未成熟、跨段时间段的样本一律从干净集
> 剔除，n、IC、状态均值与分组只消费干净行；全部观察日保留（无目标日 n=0）；
> `min_pairs` 用声明值实际执行；时间倒挂（label_start > label_end）与
> 无时区时刻是格式错误；标签成熟按标签窗结束日的**决策时刻**（收盘15:00）
> 判定，不以日期相等默许。特征时间语义为**合成即时可得假设**
> （synthetic_immediate_at_decision）：未做逐行历史可得时间核验，
> `feature_available_lag_days` 只是声明式排除开关，不是历史时点核验。

| 值的类型 | 正确的检查 | 错误请求会得到 |
|---|---|---|
| 连续分数（横截面） | `cross_section_ic`（逐日排名相关） | — |
| 二元状态（如双均线） | `state_outcomes`（真/假时后续结果的均值差） | 请求IC → `not_applicable` |
| 共同宽度（universe轴） | `time_series_state`（对**明确点名的目标实体**做跨日期诊断） | 请求横截面IC → `not_applicable` |

```python
from lei_signal.research.factor_lab.diagnostics import evaluate_predictive

targets = pd.DataFrame([...])  # 列：observation_date, entity_id, label_start,
                               # label_end, label_available_at(带时区), target
result = evaluate_predictive(batch, targets, protocol=protocol)
```

目标时间合同：标签窗必须晚于观察日；没成熟或评价截止时还不可知的目标
不进统计（逐行给出剔除原因）。

### 4. 检查"反复挑优"风险

```python
from lei_signal.research.factor_lab.validation import audit_validation

audit = audit_validation(pairs, trials, protocol=protocol)
```

- 协议先固定开发/验证/保留三段（按时间顺序、不许乱序重叠）与**每段带时区的
  评价截止**（`validation.segment_cutoffs`，必填、不晚于全局截止）；
  标签窗跨段、截止时未成熟、可得时刻晚于截止的样本一律从干净集剔除（边界接触也算跨段）。
- `trials` 记录每一次尝试（成功/失败/放弃）；**没有试验史按 unknown 处理，
  不当作只试过1次**；已用过的保留段不能恢复成未知。
- 输出永远包含 `overfit_risk_status: "not_excluded"`——本工具**不能**
  证明"没有过拟合"，它只把风险摆出来。

### 5. 执行与读证据（推荐用协议文件+CLI）

> 运行前冻结合同核对（R2）：协议必须携带**必需代码键全集哈希**（不可删减）、
> 登记表版本与规范化哈希、所用对象卡的规范化指纹、合成数据声明
> （价格尺度/日历/时间/币种）、目标端点（仅支持 1/22）、`required_checks`
> 非空且与期望一致、容差只允许 {0, 1e-9, 1e-6, 0.01}、独立期望来源文件
> 哈希——任何不符在计算前以退出 3 拒绝。**必查集合不可由协议声明或裁剪**：
> 协议携带 `required_checks` 字段即被拒绝；期望必须与独立期望产物
> （independent-expectations 文件的 protocol_expectations[案例] 段）
> **值级完全一致**（缺项/多项/改值都拒绝）。manifest 区分协议**文件 SHA**与
> **规范化 SHA**，保存协议原字节副本；每个值文件带旁置元数据。

```sh
python3 scripts/run_factor_lab.py --protocol <不可变协议.json> --out <新目录>
```

- 退出码：`0`=合成检查完成；`2`=合法资料不足（原因写全）；`3`=身份/格式失败
  （对象不存在、协议带 current 指针、输入哈希不符、输出目录已存在等）；
  `1`=期望核对失败（实现和手算期望不一致，不许放行）。
- 产物：`manifest.json`（规范/对象/代码/输入/协议哈希）、`values_*.csv`、
  `targets_*.csv`、`diagnostics_*.json`、`validation.json`、`attribution.json`、
  `quality.json`（期望逐项对照）、`run.log`、`summary.md`（标题常驻
  "合成算法验证，非真实收益/有效性证据"）。

## 三、结果怎么读（重要边界）

- **IC 是什么**：当天的分数排序和之后一段时间实际结果排序的吻合程度，
  −1 到 1。它**不等于能赚钱**，不等于策略价值，也没有通用及格线。
- **每期都看**：输出带每期的 n、剔除原因和日期，不只给均值；重叠标签窗
  让各期互不独立，相关系数只是描述，不是"不是巧合"的证明。
- **宽度一条观测就是一条**：同一天所有产品共用的宽度，复制成横截面
  不是独立证据（工具会拒绝）。
- **等权分组只是诊断**：q=2 固定分组、并列不拆散；均值差不是可投资的
  因子收益。
- **三层归因不能相加**：资金贡献（钱在哪赚到）＋决策增量（只改一个动作
  时差多少）＋风险/模型解释（结果依赖什么共同特征）回答不同问题；
  没有模型卡时第三层如实 `not_run`，剩余收益**不自动叫独特alpha或运气**。
- 现金零息是无风险利率的**声明**，不是它为零的证明。

## 四、后续新因子准入清单（全部满足才接；不自动注册、不扫参挖掘）

1. 假设：它为什么可能有用？对应交易体系哪一层？
2. 定义：公式、参数、端点、单位、方向、缺失规则；精确 `id@版本` 或候选卡草案。
3. 适用实体：哪些产品/池；先声明假设范围，不能事后挑池再证明。
4. 合法时点：观察时点、可得时点、最早决策时点；未知就是未知。
5. 简单对手：和什么比才能说明增量？
6. 冻结尝试：试验史协议、失败也保存、不只存赢家。
7. 失败证据：算错了、资料不足、没增量都要留记录。
8. 采用边界：定义正确≠数据合格≠算法核验过≠有效≠获准生产。

## 五、明确未实现（不伪称通过）

- 双均线候选的正式对象登记与真实有效性研究；
- 相关性稳健的置信区间、多重试验校正；
- 风险模型回归（本轮只做模型卡与输入资格检查）；
- Alphalens/Qlib 等外部库安装；
- 前端研究台、生产接入、真实交易授权。

## 六、完整参考

2026-09-29新增受控技术研究分支：
[一页说明与真实命令](research-workflow-usage.md)。新任务由
`--workflow-draft`演练冻结、`--workflow-contract`检查后计算、同分支的
`--register-report`重新核验后登记。下面的原workbench-v1规格和上面的历史
未实现清单是旧批次边界，不据此推断新分支能力；新分支也不迁移旧协议。

- 执行规格：`docs/superpowers/plans/2026-09-14-factor-research-workbench-v1.md` v1.0.0
- 执行报告：`docs/experiments/factor-research-workbench-v1-2026-09-14.md`
- 协议/夹具/独立期望：`docs/experiments/raw/factor-research-workbench-v1-2026-09-14/`
- 候选卡草案：同目录 `candidate-card-dual-ma-bull-state-draft-1.md`
