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

研究坐标与时间/目标合同校验（B0集中修复版）。结构/身份/参数非法抛 ValueError
（含数据篡改、必需键缺失/错哈希）；资料不足返回 `status=restricted` +
`reasons`（阻断）/`notes`（信息）。

- 本轮固定：`theme=trend, type=state_signal, use=historical_description,
  lookback=20, e_offset=1, x_offset=22, regime=none`；合同必须显式给出
  `evaluation_window` 与带时区 `research_cutoff`；
- 必需代码键 `REQUIRED_CODE_KEYS`（新模块+CLI+均线/颜色/双均线/配置加载器/
  规则v2/交易日历）与必需规范集合（准确版本+指纹）是模块常量，合同不可裁剪；
- 价格证据必须结构化 `{path, sha256}` 且逐产品记录与输入哈希/档位/data_mode
  逐项一致；证据记录与来源裁定CSV每symbol唯一（重复冲突拒绝，不选首条/末条）；
  CSV必须给完整 sha256 精确相等（sha256_16 前缀不再接受），模式/档位/输入
  身份必须一致；矛盾拒绝；真实verified缺可回查供应商材料 → 降级
  producer_candidate_only 继续 restricted，不编造；
- 被消费的 `vendor_response_ref` 必须结构化 `{path, sha256}`、文件存在、指纹
  一致，且记录绑定同产品/输入哈希/请求参数/价格语义；空字符串、假路径、
  错产品/输入全部拒绝（不只检查 vendor_traceable 布尔）；
- **真实目标闸（2026-09-15 四项修复）**：snapshot_provenance_bound /
  price_basis_verified 只证明供应商调整价/快照溯源的生成过程，不证明含分红
  财富构造；本轮真实目标没有经过主控确认的资料，一律 `target=blocked` 并注明
  `manual_target_review_required`；来源检查完成只入 notes，不称「含分红目标
  资格齐备」。本轮没有自行批准真实目标的开关；
- 日历做内容级核验：真实日历用 TradingCalendar 逐日检查（声明范围不替代
  实际days；本地CN日历实际覆盖 2019-09-01—2026-06-30），合成日历须逐日
  session/close_at；缺一天可定位；
- R2：available_at 未知 → null；真实身份的 `point_in_time_verified=true`
  本B0一律拒绝（逐行真实历史资格未实现）；
- 主候选目标 `total_return_wealth`；替代提案 `vendor_adjusted_price_change`
  须主控确认，两者不可混榜；辅助下行 = `min(0, min(I(s)/I(e)-1, s∈(e,x]))`。

## 3. `state_description.describe_states(values, schedule, contract) -> dict`

**仅 synthetic 夹具**已验证；真实来源身份不能靠传 synthetic=True 字符串改写。

- 合同必填（无默认掩盖）：`object_ref / data_mode / 20/1/22 / evaluation_window /
  research_cutoff（带时区）/ sparse_anchor_session（每产品锚点）/ sparse_step=23`
  （0/负/1/其他值一律拒绝）；
- 输入严校：(symbol,session) 唯一；state 接受真布尔/空——上游可空布尔
  （pd.BooleanDtype 的 pd.NA）及显式 None/NaN 一律视为未知；字符串false、
  空字符串、数字0/1/2拒绝，不自动转布尔；I 只接受正有限或显式缺失；
  close_at 逐日带时区且日期与 session 对应；
- 成熟按标签结束格点的**逐日 close_at ≤ research_cutoff** 判定（同日盘前未成熟、
  正好收盘成熟）；观察必须落在评价窗内；
- 主比较只用共同合法集合（状态已知∧主目标合法∧成熟），`n_true+n_false=
  comparison.n`；全资产背景单列 background（含未知状态，不混称）；辅助路径
  缺失独立 `aux_n`；逐年分列（空年份 n=0）；
- 连续状态段按完整日程序列，缺整行或未知均断开；稀疏锚点来自合同，未知/缺格
  跳过不顺延；空输入/全部日期窗外返回结构化零计数，不抛 KeyError；
- **稀疏格与主比较共用同一合法集合**（2026-09-15 四项修复）：不合格格保留
  日期与 `skipped_reason`（missing_row/tail_immature/e_missing/x_missing/
  not_mature/state_unknown），main/aux 置 null、skipped=true，不展示成已可
  观察结果，不计 `true_slots_up/false_slots_down`；辅助路径不全但主目标合法
  时主值保留，aux 缺失由稀疏 `aux_n` 独立表达；
- 窗口重叠固定标注；不产生策略收益、年化、IC、显著性、α。

## 4. `scripts/check_factor_unit_readiness.py --contract PATH --out NEW_DIR`

只校验与冻结候选包，**不算真实表现**。退出 0=资格齐备（也不自动启动 B1）；
2=资料不足（restricted，不打印资料齐备）；3=合同/身份错误（含数据篡改、
必需键缺失/错哈希、JSON错误、缺源文件、目录已存在）。

- 运行合同**原字节**随包保存（contract.source.json），contract_sha256 反查一致；
- 必需代码键在生成任何结果前逐项核哈希；源码原字节、候选卡、实际采用规范、
  环境版本、两市场被引用证据、来源表全部入包；
- 合同直接引用的每份 `price_basis_evidence` 原字节及被消费的
  `vendor_response_ref` 原件一并入包（`evidence/`，相对路径改名避免同名碰撞）；
  应包含依赖集合从合同与实际消费清单预先推导，`dependency_closure` 与实际
  归档双向核对——缺失/错哈希拒绝，不默默漏包；
- `file_hashes` 用包内相对路径并与实际集合双向核对；
- manifest 最后写，字段区分 `package_completed`（打包完成）/ 
  `qualification_status`（ok/restricted）/ `exit_code`；restricted 也可打包完成，
  但不称资料齐备。

## 能力边界（勿越界引用）

| 已实现 | 未实现/未授权 |
|---|---|
| close-only 状态适配（复用生产公式） | 真实数据上的任何状态/目标计算（B1 未授权） |
| 合同校验与资格诊断（证据/日历/身份闭合） | available_at 的真实来源证据 |
| 合成状态—目标描述统计（共同集合/截止消费） | 美股交易日历与半日市表；CN日历仅覆盖2019-09起 |
| 冻结候选包（合同原字节+必需键闭合） | 含分红财富目标的价格基础 |

## 复现

```sh
python3 -m pytest tests/unit/test_factor_unit_close_state.py \
  tests/unit/test_factor_unit_study_contract.py \
  tests/unit/test_factor_unit_state_description.py \
  tests/unit/test_factor_unit_b0_controller_cases.py \
  tests/unit/test_factor_unit_four_fixes.py \
  tests/integration/test_factor_unit_readiness_cli.py -q
```
