# factor_evidence 使用手册（因子证据可靠性 v1）

版本：1.0.0；对应冻结协议 `factor-evidence-reliability@1.0.0`（2026-09-16）。
本模块是**状态研究结果的可靠性体检工具**：对"日期、二元状态、未来结果、
合法性"观察表做年份稳定性、留一年、标签区间重叠审计与成对循环区块重抽的
条件性敏感范围。它不生成因子、不重算状态/标签、不读价格、不做收益账户。

## 1. 能力与边界（先读）

- **首版只支持二元状态**（`state` 为真布尔或缺失）。数值特征、宽度水平
  （如 B200）**不会**被自动强转成布尔——把数值变成"成立/不成立"是研究
  定义决策，必须由调用方先明确并自行负责，本模块不做隐式转换。
- 未接入（不得声称已支持）：相关性 IC/RankIC、factor_return 构造、风险模型
  归因、真实时点（point-in-time）验证、冻结观察生命周期、生产/OKR 写入。
- 全部输出是**事后描述与敏感性诊断**：不报"因子有效概率"、p 值、显著通过、
  独立样本数；"条件性95%重抽范围"不是有效概率，范围跨零与否不作机械判决。

## 2. 观察表怎么给（合法输入契约）

规范列（`validate_observations` 纯函数校验，合成/测试入口）：

```text
symbol, session(YYYY-MM-DD), state(True/False/缺失), main(float或缺失),
aux(float或缺失), legal(bool), legal_reason(None或非空), e_date, x_date
```

硬规则：state 只收真布尔或缺失（字符串 "true"/数字 0/1 一律拒绝）；
main/aux 缺失用 None（CSV 文本 'nan'/'inf' 拒绝；inf 拒绝）；legal 行必须有
目标与两端日期且 legal_reason 为空，非法行必须给原因；session 唯一升序且
与评价窗交易日轴**严格相等**；session < e_date < x_date 且都在日程内。
真实 B1 数据没有合成旁路：`load_b1_observations` 恒做六项固定 SHA 核验。

## 3. 可运行合成例（不含任何真实数据）

```python
import pandas as pd
from lei_signal.research.factor_evidence.observations import validate_observations
from lei_signal.research.factor_evidence.resampling import (
    circular_indices, paired_block_deltas)
from lei_signal.research.factor_evidence.stability import (
    state_summary, year_stability, overlap_audit)

# 80 个合成交易日：50 个观察各需 e=t+1、x=t+22，最深下标 49+22=71 < 80
days = [d.strftime("%Y-%m-%d")
        for d in pd.bdate_range("2020-01-02", periods=80)]
schedule = pd.DataFrame({"session": days,
                         "in_window": [i < 50 for i in range(80)]})
rows = []
for i in range(50):
    state = bool(i % 2)                     # 交替的合成二元状态
    rows.append({"symbol": "SYN", "session": days[i], "state": state,
                 "main": 0.01 * (1 if state else -1), "aux": -0.01,
                 "legal": True, "legal_reason": None,
                 "e_date": days[i + 1], "x_date": days[i + 22]})
frame = pd.DataFrame(rows)

# 先纯校验（键集/布尔/日期倒挂/合法性与理由矛盾都会在这里被拒绝），再计算
frame, audit = validate_observations(frame, schedule)
print(audit["counts"])

print(state_summary(frame)["delta"])        # 全期差（小数）
print(year_stability(frame)["sign_counts"]) # 逐年正/零/负计数
print(overlap_audit(frame, schedule, days[0], 23)["adjacent_shared_histogram"])
# 固定起点看纯索引：n=5, L=3, starts=[4,1] → [4,0,1,1,2]（绕回+尾部截断）
print(circular_indices(5, 3, [4, 1]).tolist())
# 成对重抽（小规模演示；正式口径 L63/126、2000次、seed 20260916 见协议）
out = paired_block_deltas(frame, block_length=10, reps=8, seed=20260916,
                          min_valid_reps=1)
print(out["quantile_lower"], out["quantile_upper"])
```

## 4. 其他二元状态如何接入

1. 先固定状态定义（候选卡/协议），自行产出观察表（每行一个交易日，含
   state/main/legal 与两端日期），main 的含义与端点必须在协议里写死；
2. 用 `validate_observations(frame, schedule)` 做纯校验（合成入口）；
3. 统计与重抽函数（`state_summary` / `year_stability` / `overlap_audit` /
   `paired_block_deltas`）可直接复用——它们只看规范列，不关心状态来源；
4. 正式运行仍需新建协议版本（身份、输入、代码哈希逐值绑定），
   `factor-evidence-reliability@1.0.0` 只绑定 B1 输入，不能改个路径就复用。

## 5. 固定方法参数（协议 `fixed_params`，改动需新版本）

- 重抽：L=63 与 126（主控固定研究设定，非最优参数）、每种 2000 次、
  `numpy.random.Generator(PCG64(20260916))` 每种 L 分别新建、
  一次性 `integers(0, n, size=(reps, k))` 抽全部起点、k=ceil(n/L)、
  `(start+j)%n` 拼接截到 n 行、同一索引用于 state/main/合法性；
- 有效重复 <1900/2000 不输出区间（本轮质量约定）；分位 = linear 2.5%/97.5%，
  名称"条件性95%重抽范围"；起点矩阵全部保存（`*-starts.npy`），配合逐次
  CSV 可在不依赖随机库版本的情况下完整复算；
- 区间重叠审计以**相邻交易日价格区间**为单位（不是共同日期点数）；
  稀疏锚点只审计原规则（2019-10-08、步长 23），不扫描其他起点。

## 6. 参考实现说明

方法定义参考 arch 8.0.0 官方文档（循环区块重抽的动机与边界，见任务书
§2.1 主控实读记录）。本实现用 numpy 自写索引核心并独立核算，
**未**与 arch 引擎做逐值兼容核验，不声称运行过 arch；未安装任何新依赖。
首个真实实例（B1 双均线候选状态）的结果与限制见
`docs/experiments/factor-evidence-reliability-v1-2026-09-16.md`。
