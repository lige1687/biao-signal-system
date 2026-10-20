# factor_evidence 能力映射（Task 0 交付）

日期：2026-09-16。本文件说明新包 `src/lei_signal/research/factor_evidence/` 的可复用
接口范围、明确不调用与尚未接入的能力。旧 `factor_lab`、`factor_unit`、规则、定义登记表
与全部旧 raw 只读（开工基线见 `baseline/freeze-baseline.json`，121 文件指纹）。

## 本包是什么、不是什么

- **是**：对"已存在的观察表（日期、二元状态、未来结果、合法性）"做事后可靠性统计的
  隔离研究模块——年份稳定性、留一年、标签区间重叠审计、成对循环区块重抽的**条件性**
  敏感范围。服务于交易规格 §2.2/§4–5"道路"状态研究的结果可信度评估。
- **不是**：因子/标签生成器、回测框架、收益账户引擎或对象登记表。本包不生成因子、
  不重算状态、不重算未来结果、不读价格序列、不联网、不装依赖（仅 numpy/pandas/pytest/ruff）。

## 复用边界（对旧代码）

| 旧接口 | 本包是否使用 | 说明 |
|---|---|---|
| `research/trading_calendar.py::TradingCalendar` | **使用（只读）** | 仅 `from_file` 读取 B1 封存日历 `calendar.json` 并推导评价窗应有观察日；不调用其任何写入/推断回退路径 |
| `factor_unit/b1_contract.py` | 不 import | 新包自带独立协议 `factor_evidence/contract.py`（身份 `factor-evidence-reliability@1.0.0`），常量独立定义；参考其校验模式但不共用代码 |
| `factor_unit/description_core.py` 统计函数 | 不 import | 稳定性统计在 `factor_evidence/stability.py` 独立实现，口径由本任务书 §2.2 固定 |
| `factor_unit/close_state.py`、`b1_description.py` | 不调用 | 旧因子/目标真实计算入口一律不调用（0 次）；状态与标签只从已封存 `observations.csv` 读取 |
| `factor_lab/**` | 不调用 | 全部只读 |
| 规则账本 rules.v1/v2、`definitions.v1.json` | 只读指纹 | 作为保护基线冻结指纹，不解析、不修改 |
| B1 真实运行入口 / 任何 CLI | 不调用 | 本轮真实计算仅限本包 CLI 对观察表的新统计汇总 |

## 首版支持的观察类型

- **仅二元状态（binary_state）**：`state` 列为真布尔或缺失（缺失=状态未知，不入组）。
  本轮真实接入只有 `candidate:lei.dual_ma.bull_state@draft-1`（候选卡
  `docs/experiments/raw/factor-research-workbench-v1-2026-09-14/candidate-card-dual-ma-bull-state-draft-1.md`，
  SHA `907d1763…0dc1`）。候选对象不在 `definitions.v1.json`，本包不建第二份对象登记表。

## 明确未接入（不得声称已支持）

- **feature / 排序（IC/RankIC）**：连续数值特征与横截面相关诊断未实现、未接入。
- **factor_return / 因子收益序列构造**：未实现；本包不构造多空组合或因子收益。
- **风险模型 / 归因回归**：未实现；`models` 类能力不在本包。
- **真实时点（point-in-time）验证、冻结观察、生产/OKR 写入**：未接入。
- 宽度水平（如 B200）等数值特征**不自动强转布尔**；其他二元状态须由调用方提供
  合法观察表（见使用手册 `docs/research/factor-evidence-reliability-usage.md`）。

## 输入契约（摘要）

- 观察表规范列：`symbol/session/state/main/aux/legal/e_date/x_date`（另有 `legal_reason`）。
- `load_b1_observations(root, protocol)` 适配 B1 run-02 `observations.csv`：
  严格解析 CSV 布尔字符串（`true`/`false`，拒绝其他真值转换），`legal` 取
  `flag_state_known ∧ flag_main_legal`（B1 共同合法集合），非法行保留原因。
- `validate_observations(frame, schedule)` 为纯函数入口（合成/测试用），与真实 CLI
  的协议校验分离；真实 B1 数据不得靠合成入口绕过身份检查。
