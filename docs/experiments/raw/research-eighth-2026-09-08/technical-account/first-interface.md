# 第八批研究账户接口与反例规范

日期：2026-09-08。研究引擎，未运行真实策略成绩。仅服务交易规格§2.3、§3、§9、§10的候选执行和会计检验；不是生产账户。

`engine.simulate(prices, actions, candidates, exit_observations, *, start, end, weekly_per_symbol=250, fee=.001, config_id, limits, limit_changes=None, blocked_dates=None, exit_rule=None)` 返回包含 `daily/trades/orders/events/roundtrips` 的字典。

- prices：`{symbol:{YYYY-MM-DD:{open,high,low,close,volume}}}`，无报价可不列日或整行OHLC均空；部分残缺或非正价拒绝。每产品须有开始前有效收盘。拆分/除息可在无报价日作用于持份与旧估值。
- actions：第五批 `event_id,symbol,type`，type为`cash_dividend/split`；cash事件含`announcement_date,record_date,ex_date,pay_date,cash_per_share`；split含`announcement_date,ex_date,ratio`。拒绝重复经济事件。公告必须早于生效日开盘假设（公告日<ex_date）。同一产品同日混合行动顺序未约定，拒绝。
- candidates：`symbol,signal_date,candidate_id,stop,target,upper,variant`，价格均信号日名义基准。ID全局唯一；技术候选必须有该日有效收盘。所有候选按日期、symbol、candidate_id确定顺序，保留拒绝原因。P4/P7一律variant=breakout。start以前仅预热，不入场。
- exit_observations：`{symbol:{date:{ema20,cost20,ema20_slope,sma20_slope,sma20,sma60}}}`，均为当日名义基准。技术持仓有效收盘日需要该配置退出所需字段，缺字段停止而非假定不退出。
- limits：`{symbol:ratio}`；limit_changes沿第五`{symbol:[(effective_date,ratio)]}`，另兼容日期到比例的dict。blocked_dates为各symbol的日期集合/列表。沿用第五开盘价格上下限对称保守限制与0.00051容差，研究近似，不声称可实际成交。

每日顺序：公司行动及到账→周一各产品独立入金→之前待卖订单尝试→指定日买单一次尝试→按有效收盘估值/形成次日待卖→登记日持份锁权→日账。入金按前日投资净值发行账户单位，剔除入金后的净值用于回撤。各产品现金不互借。

技术买单的指定日为四产品报价日期键并集内，严格晚于信号日的首日；指定日缺该产品报价、禁止开盘、没钱或已有持仓即作废。所有技术买单在开盘复核`(target-open)/(open-stop)>=3`，目标缺失、距离非正拒绝，不创建替代目标。买入100份整数手；单产品不加仓，当天卖后不买。P6可在任何报价开盘现金足够时买整手并加仓。

P7数量为可用现金含买入费用上限，与前一日该产品总财富1%除以(open-stop)的整手数之小者；这里总财富含现金、持仓和应收，不是单位净值。首日没有过去账户财富时风险预算为0。不代表个人损失上限，费用和跳空可导致更多损失。

固定收盘确认后下一可开盘卖；不实现新的独立开盘硬止损，不按日内低价同日卖。close<stop最高优先。P0/P1/P2/P3/P5其次close<ema20且close<cost20；P4/P7其次close<upper且ema20_slope、sma20_slope均<0，breakout版本不追加埋伏条件。可选`exit_rule(position, observation, close)`仅替换结构失效以外的规则判断，返回reason字符串或None，不能改变结构优先级。买入日收盘可触发，但卖出日必须严格晚于买入日；待卖持续至可执行，卖出不会因条件恢复撤销。

公司行动：登记日按持份锁权并绑定持仓身份；除息日记应收；发放日即使休市也转可用现金。卖出之后仍保留原持仓分红权。拆分换份、技术水平线除以ratio；除息技术水平线乘以前日名义参考价扣股息后的比例，旧现金账户估值则减每份现金，两者分开。持仓及跨行动待买候选的stop/target/upper都转换。拆分增加后的零股卖出允许全部清仓，买入仍100份整手。

roundtrips每个技术持仓独立记录入场本金、买卖费、应计股息、已到账股息、退出款、已完成状态。已卖后除息或到账更新原持仓，不把旧持仓股息归给新持仓。未结束保留有据估值及陈旧日期，不虚构退出；额外末价清算只能单独列为估计。

实现前固定的必要反例：跳空使比例不足3；缺目标；已有持仓重复；买入当天触发但次日才卖；卖出缺价/禁开盘持续等待；分红卖出后形成应收再到账；无价拆分同时换份和水平线；尾部空价不填成交；周一休市仍入金、支付日休市仍到账；整手无钱不成交；P7前日财富尺寸；结构和趋势同日只生成一张结构退出；卖出当天不重买；公司行动不凭空创造或丢失财富；入金不伪造投资收益。
