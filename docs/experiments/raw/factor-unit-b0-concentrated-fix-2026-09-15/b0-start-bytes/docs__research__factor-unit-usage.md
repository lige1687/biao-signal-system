# factor_unit 使用手册（B0，2026-09-15）

新消费者：`src/lei_signal/research/factor_unit/`。权威规范仍是
`docs/research/experiment-backtest-principles.md` v1.1、`docs/research/definition-standard.md` v1.1.0、
`docs/research/ai-execution-contract.md` v1.0.1、`docs/research/experiment-report-template.md` v1.1.0；
本手册只是新模块的接口说明，**不是另一份总纲**。

## 对象与身份

- 唯一引用：`candidate:lei.dual_ma.bull_state@draft-1`（候选卡：
  `docs/experiments/raw/factor-research-workbench-v1-2026-09-14/candidate-card-dual-ma-bull-state-draft-1.md`）。
  **未进入登记表**，无任何有效性证据，无生产授权。
- 本模块不改 factor_lab v1.2.0 合成原型；不修改登记表；不改生产规则。

## 1. `close_state.compute_close_state(close: pd.Series) -> pd.DataFrame`

R1 裁定的收盘价适配：共同确认状态只依赖 close/EMA20/SMA20/滞后收盘/颜色，
不需要成交量、高低价。完整公式仍调用生产函数 `dual_ma_bull_state`，
只剥离无关计算——不是删减策略条件。

- 返回列（精确 7 列）：`close / ema20 / sma20 / close_lag20 / signal_color / state / missing_reason`；
- `state` 是**可空布尔**：True/False/缺失。false 不是看空；未就绪不是 false；
- `missing_reason`：`price_missing`（当日缺价）/ `warmup_not_ready`（任一输入未就绪；
  含内部 NaN 对 EMA 的永久污染——诚实传播，不跳过不重启）；
- 索引原样保留；重复/乱序日期、非正/无穷值直接报错，不静默修复；
- 公式不变（R3）：非浮点临界处 state ⟺ 绿色且 close>SMA20——这仅是公式等价解释，
  不产生预测价值结论。

```python
from lei_signal.research.factor_unit.close_state import compute_close_state
frame = compute_close_state(close_series)   # 只要 close，别造假成交量
```

## 2. `study_contract.validate_study_contract(contract: dict) -> dict`

研究坐标与时间/目标合同校验。结构/身份/参数非法抛 ValueError；
资料不足返回 `status=restricted/blocked` + `reasons`（阻断）/`notes`（信息）。

- 本轮固定：`theme=trend, type=state_signal, use=historical_description,
  lookback=20, e_offset=1, x_offset=22, regime=none`；
- R2：`session_close`（当地收盘）≠ `fetched_at`（抓取时刻）≠ `available_at`（实际可得）。
  available_at 未知 → null 且 `point_in_time_verified=false`（仅事后描述资格）；
- R4：`price_basis_status` 三档 `producer_candidate_only < snapshot_provenance_bound <
  price_basis_verified`，自填无效，必须附证据；
- 无可靠日历的市场：交易日目标保持 blocked——不从报价日期或周一至周五反推日历；
- 主候选目标 `total_return_wealth`；替代提案 `vendor_adjusted_price_change` 须主控确认，
  两者不可混榜；辅助下行 = `min(0, min(I(s)/I(e)-1, s∈(e,x]))`。

## 3. `state_description.describe_states(values, schedule, contract) -> dict`

**仅 synthetic=True 夹具**已验证；真实来源身份不能靠传 synthetic=True 改写
（data_mode=real 会被拒绝——不是放行开关）。

- values 最小字段 `symbol/session/state/I`；schedule 含 `session/close_at`（带时区）；
- 目标按**日历位置**（t+1、t+22 格）定位，不按删行后的第几行；
- 输出：逐日有效/未就绪/缺失原因；真/假两组 n/均值/中位数/上涨比例/辅助下行；
  同一可评价全集的无条件参照；逐年分列（空年份 n=0）；连续状态段；
  每 23 格固定稀疏视角（缺格跳过不补选）；
- 窗口重叠是事实：输出固定标注"不得当独立多次成功"；
- 不产生策略收益、年化、IC、显著性、α。

## 4. `scripts/check_factor_unit_readiness.py --contract PATH --out NEW_DIR`

只校验与冻结候选包，**不算真实表现**。退出 0=资料齐备（也不自动启动 B1）；
2=资料不足；3=合同/身份错误。输出含 verdict.json、code-freeze/（源码原字节，
读取未提交工作区而非只记 git HEAD）、environment.json、manifest.json（最后写，
completed 仅成功时为 true）。输出目录已存在则拒绝。

## 能力边界（勿越界引用）

| 已实现 | 未实现/未授权 |
|---|---|
| close-only 状态适配（复用生产公式） | 真实数据上的任何状态/目标计算（B1 未授权） |
| 合同校验与资格诊断 | available_at 的真实来源证据 |
| 合成状态—目标描述统计 | 美股交易日历与半日市表 |
| 冻结候选包与来源裁定表 | 含分红财富目标的价格基础 |

## 复现

```sh
python3 -m pytest tests/unit/test_factor_unit_close_state.py \
  tests/unit/test_factor_unit_study_contract.py \
  tests/unit/test_factor_unit_state_description.py \
  tests/integration/test_factor_unit_readiness_cli.py -q
```
