# 第八批研究技术账户引擎

日期：2026-09-08。交付可导入的研究引擎及合成测试，没有运行真实策略成绩，没有改生产、旧封存或目标台账。

## 一句话结论（大白话）
研究账户已能按固定候选逐日记钱：买单只在指定开盘试一次，卖单持续等待可成交，分红和拆分归回正确持仓，新入金不冒充投资收益。23个合成例子全部通过。它证明这些限定行为能够被核对，仍需主负责人独立重建真实输入的现金和持份后才能解释本批结果。

## 接口和文件

- `engine.py`：纯Python，导入不读写文件、不联网、不引用生产代码。使用标准库。
- `INTERFACE.md`：最终输入、时间顺序和输出契约。`first-interface.md`保存最初B3措辞，不能拿来覆盖最终契约。
- `test_engine.py`：23个合成例子，用实际模拟而不是模拟替身。
- `tests-red.txt`：只有空接口时，原15个例子全部失败。
- `tests-green-first.txt`：第一实现14通过，拆分例子失败；原因是测试仍把拆分前名义均线当作拆分后的观察输入，改为同日正确名义单位后通过，没有改变期望财富。
- `tests-red-b3-clarification.txt`：原负责人澄清B3真实定义后，两个区分价格条件与斜率条件的例子失败；同时发现已闭仓估值日期错误随日账推进。
- `tests-green-b3.txt`：纠正B3条件、固定真实退出估值日后17个例子通过。
- `tests-boundaries.txt`：再检查旧分红不归给新持仓、除息财富守恒、P7当日入金、不开独立开盘止损及产品现金隔离，共22个全部通过。

运行合成测试：进入本目录运行 `python3 test_engine.py`。主负责人用 `importlib.util.spec_from_file_location` 或临时模块路径导入 `engine.py` 后调用 `simulate`；不运行测试文件获取真实成绩。

## 输出字段约定

返回普通Python字典，包含五个列表，可直接JSON序列化：

- daily：一行一个民用日。含 equity/assets/cash/receivable/total_funding/deposit/account_units/nav/drawdown/fees/stale_symbols/accounting_difference，以及每产品 units_/cash_/mark_/mark_date_/receivable_/equity_/previous_equity_/funding_/fees_前缀字段。
- trades：实际成交，含date、symbol、side、shares、price、notional、fee、order_id、position_id；买入另留risk_budget、previous_product_equity、stop、target。
- orders：每个技术候选一行及每个退出指令一行，候选原字段保留。status为filled/rejected/pending_at_end；attempts完整保留每次尝试日期、失败原因和开盘风险比。卖单一次成交后不再尝试。
- events：外部入金、拆分换份、分红登记、应收、到账。登记和除息记录带原持仓身份，以支持卖出之后的权益核对。
- roundtrips：每个技术持仓一行；P6同产品的连续加仓保留一个未结束记录。含独立入场金额、买卖费用、应计/已付股息、退出金额、实际退出日、末估值、净损益。闭仓valuation_date固定实际退出日；accounting_updated_date可以因后续股息会计更新推进。split不改entry_notional或历史费用。

净损益 = 退出总额 + 尚持市值 + 应计股息 − 累计入场总额 − 买入费 − 卖出费。股息已支付不会再加一次收益。技术持仓的stop/target/upper为当前有效名义单位；initial_对应成交时初始单位，原候选仍在orders保存，level_actions记录转换事件。

## 最终规则及研究限制

P4/P7最终使用冻结B3突破研究定义：收盘低于原锁定上沿，同时低于SMA20和20根前收盘。两条均线斜率不是这一版的退出条件。结构失效先判，统一收盘确认后再找下一可成交开盘；不根据开盘跌穿结构位新加一个独立立即卖出条件。价格跌过已经挂出的退出时，按实际可成交开盘计损失。

所有技术配置保留信号与指定开盘两次潜在盈利/预设亏损比例至少3；signal_accepted=false不能被后来低开复活。真实数据必须带signal_ref等完整字段；兼容缺少信号检查字段只用于合成例子，不是对真实研究免除信号纪律。P6不套目标风险要求。

P7用前一民用日该产品总财富的1%作计划风险预算，包含当时已有现金与应收，但不包含当天刚到账的钱。买入仍受现金含费上限及100份整手限制。计划风险不包含所有费用和跳空损失，不代表真实个人损失保证。

比例技术水平线、名义成交和现金股息分开处理。无报价拆分照样换份及转换旧估值；陈旧估值带日期，不是可成交价。已知开盘禁止和价格限制按输入执行，缺失正式交易日历、日内可交易性、真实费用与全部公司行为公告的限制没有因此消失。

本引擎始终对全部产品使用保守“买入当天不能卖”约定，支付日资金开盘前可用，无最低收费，无现金利息，卖出份额全部清仓（允许拆分产生的零股），买入100份整手。均为本轮近似。回撤用外部入金发行份额后的投资净值，不能用新增收入抬高账户价值掩盖损失。

主负责人仍需用独立算法重建每个真实配置的持份、现金、应收、费用、净值，并核对真实B3候选/目标与输入指纹。23个有限例子不替代这一步，也不宣称完整B或整个系统已有效。

最后接口反例还验证了真实候选所含config_id、candidate_id、目标来源等字段，以及seedmeta扩展元数据。上游order_id不会覆盖账户订单ID，完整上游字段另存candidate_metadata。tests-red-metadata.txt保留修复前重复关键字错误，tests-final.txt为最终23项全部通过。
