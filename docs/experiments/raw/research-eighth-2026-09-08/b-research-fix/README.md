# 修正后的 B 研究代理

研究实现标识：`b-research-fix-2026-09-08-v1`。日期：2026-09-08。

## 一句话结论（大白话）

已在独立研究复制件修复三处具体差异：突破版不再误用埋伏版的排列退出；下一根开盘必须仍满足目标收益至少为风险3倍；整理寿命从首次有效横盘才开始。原来的16项检查与新增16项边界检查均通过。九条无交易纪律仍未完整实现，因此只能称“修正后的B研究代理”，不是完整系统。

## 安装与隔离

不安装进生产环境。`research-package/src` 是27个原Python模块及其包初始化文件构成的依赖闭包，另新增实际开盘检查模块；原v1/v2 YAML复制保留，当前加载仍为v2总版本2.1.0。来源和变化分别见source-manifest.json、research.patch、effective-config.json。

在新的Python进程中，将本目录的`research-package/src`放在搜索路径第一位，并设`sys.dont_write_bytecode=True`。不要在已经导入在线`lei_signal`模块的进程内切路径，Python可能继续使用旧模块缓存。可用integration-check.json核对本次实际导入路径。每次研究必须保存研究实现标识和manifest指纹；事件自身原rule_version仍是复制来的2.0.0，不能靠这个字段区别修复版本。

依赖是Python、pandas、numpy、PyYAML，具体本次版本见environment.json。没有网络、数据库、线程服务或安装步骤。`frozen-provenance/`下的服务/API仅供调用链静态核对，不能作为这个最小包的执行入口。

## 根研究的调用接口

### 1. 计算特征及B事件

```python
from lei_signal.features.indicators import compute_features
from lei_signal.rules.dense_breakout import detect_dense_breakout_events
from lei_signal.backtest.engine import entry_specs_from_events

frame = compute_features(bars)
events = detect_dense_breakout_events(frame, symbol)
specs, filtered_rr, no_target = entry_specs_from_events(
    frame, events, symbol,
    module="B", entry_variant="breakout", rr_min=3.0,
    pivots=confirmed_pivots,
)
```

上例仅展示接口，本目录没有用四只基金执行它。`bars`须包含已完成的open/high/low/close/volume、递增且无重复的交易日期和足够预热。指标/目标价格必须使用当时可用、口径一致的历史，不能把日后分红复权提前带入。确认高点列表必须有pivot_date和available_date；缺口目标默认关闭，未擅自打开。必须显式写breakout或ambush，空值默认会取ambush。

本包不会生成上方均线密集区目标，也不会补九条未实现的禁止规则。保留`rr_min=3`的信号参考价筛选后，实际开盘还要再检查一次。

### 2. 下一根实际开盘复核

```python
from lei_signal.backtest.entry_qualification import qualify_entry_at_open

q = qualify_entry_at_open(
    open_price=actual_next_open,
    stop_price=locked_stop_in_execution_units,
    target_price=locked_target_in_execution_units,
)
if not q.accepted:
    # 留下未入场记录及q.reason，不能计成一笔已成交的零收益交易。
    pass
```

返回冻结dataclass字段：`accepted`、`reason`、`entry_price`、`stop_price`、`target_price`、`actual_reward_risk`。最后一项就是“按实际开盘，目标收益是风险的几倍”。阈值读取未修改账本`reward_risk_filter.rr_min_ideal=3`；恰好3接受、低于3拒绝，无目标、无效价格、开盘等于/低于失效位或目标不高于开盘也拒绝。

三项价格必须在**实际成交时同一计价单位**。如果期间有拆分或分红造成价格坐标变化，根研究负责用已冻结、当时生效的转换将既定目标与stop换算后传入。换算不等于重新选择目标。函数不接交易日历，不知道停牌、涨跌幅限制、可用现金或既有持仓，因此accepted只表示这一项技术检查通过。

拒绝原因：`skipped_invalid_entry_price`、`skipped_invalid_stop_price`、`skipped_open_at_or_below_stop`、`skipped_target_unavailable_at_entry`、`skipped_invalid_target_price`、`skipped_target_not_above_entry`、`skipped_actual_reward_risk_below_3`。成功是`accepted`。

### 3. 每日 B3 退出复核

```python
from lei_signal.backtest.engine import b3_exit_triggered

# 先用同一口径的close和锁定stop判断结构失效；它仍优先。
# 结构尚未失效时，调用以下B3判断。
failed = b3_exit_triggered(
    close=close,
    sma20=sma20,
    sma60=sma60,
    close_lag20=close_lag20,
    breakout_reference=locked_upper_in_current_units,
    entry_variant="breakout",
)
```

突破版精确条件为：`close < breakout_reference`且`close < sma20`且`close < close_lag20`。埋伏版另允许`sma20 <= sma60`单独触发。返回True表示该日收盘确认退出，实际卖出仍由账户层按下一可交易开盘处理。

**这里保留的是原B3研究定义，只用SMA20和抵扣价（20根之前的收盘价），不能称为EMA与SMA真实同时向下弯曲。** 函数没有EMA20或EMA斜率输入，也没有新增斜率算法。最高规格只说“20均线组向下弯曲”，这个具体代理定义仍有局限。本批根研究已明确选择沿用它，避免在修复过程中另换算法。

调用者必须提供明确的`entry_variant`和有效的已锁定`breakout_reference`；为保持旧双动作行为，函数仍保留reference=None时原分支语义，不能把缺参考位作为一笔合格突破交易传入。本函数不替代输入有效性检查。

### 4. 单笔研究引擎兼容入口

复制件`engine.simulate_trade`也使用同一个实际开盘检查和B3函数，适合合成核验。拒绝的记录没有exit_date、exit_price或风险收益结果；`meta.entry_accepted=False`。真正接受时在meta留下`actual_reward_risk`，原`Trade.reward_risk`仍是信号价参考值，二者不要混用。数据最后一根没有下一开盘时保留`signal_at_end_not_entered`。

这是研究复制件的单笔工具，本次实际开盘筛选对其所有调用生效，不应擅自拿去重算A/C/D并称原样复现。旧费用和9.5%限制模型没有在这里升级；根研究的真实账户应使用上面两个纯函数，而不是拿本引擎替代资金会计或真实成交规则。

## 测试证据与未完成范围

- `before-replay16/`：原16项行为中14确认、2反例。
- `before-boundaries/`：16项边界中3通过、13失败，含缺少公开接口；没有测试脚本错误。
- `after-replay16/`和`after-boundaries/`：同一测试脚本修后各16通过，无失败或脚本错误。
- 初始寿命补充：旧版首个watch为112根有效横盘；修后为126根。20根暂离仍延续，第21根归零，归零后离开期不重新计龄。
- `integration-check.json`、`self-check.json`：实际导入隔离、原配置和第七批封存来源完整性、授权修改范围。

“32项通过”仅说明这些明确行为与边界检查满足约定，其中还包括确认九条缺口仍存在；不代表全部系统纪律、历史收益、现金账户或实盘可交易性通过。未做参数优化、四基金历史候选或收益运行，未改生产、旧封存、注册和OKR。埋伏false→true等其他未授权语义保持原样。
