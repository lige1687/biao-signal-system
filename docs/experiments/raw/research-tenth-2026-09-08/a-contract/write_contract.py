from pathlib import Path
import json, hashlib
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
results=json.loads((OUT/'probe-results.json').read_text())
contract={
 'schema_version':'1.0','date':'2026-09-08','module':'A','provenance':'research_proxy',
 'strategy_layer':'道路条件中的回调触发、结构失效和日线退出；输入资格核对，不是收益实验。',
 'scope':'仅A日线代理；不代表完整A/B/C/D，更不代表完整多周期/筹码系统。生产规则、UI、交易台账和OKR均未改。',
 'limited_account_eligible':False,
 'verdict':'存在追加未来K线改写历史A事件的明确反例，原冻结实现不能进入有限账户模拟；不得用只剩EMA收复的缩小范围冒充完整A。',
 'authority':[
  {'source':'docs/trading-spec-v1.md','sections':['3.1','3.2','6','7.3','9 A1-A6','10','13','14','17'],'role':'最高溯源依据'},
  {'source':'configs/rules.v1.yaml:first_ma_pullback','version':'1.0.0','role':'历史双阈值/3根窗口账本，不是当前执行口径'},
  {'source':'configs/rules.v2.yaml:first_ma_pullback','version':'3.0.0','role':'当前与第八冻结包加载器实际读取；ATR触及等仍标研究代理/待确认，不改参数'}],
 'explicit_original':{
  'A1':'稳定多头趋势、均线平行向上和多头排列。',
  'A2':'回调至20/60/120双均线组或事先形成的筹码/均线密集区；附近距离须配置。',
  'A3_four_alternatives':['底部构造','低一级周期形成多头排列','破线后重新站回','关键位置破底翻'],
  'A4':'早期EMA20向上；确认EMA20与SMA20同时向上；收盘生成、下一根开盘。',
  'A5':'明确支撑结构被破坏的位置作为初始失效。',
  'A6':['收盘同时跌破EMA20和20日抵扣价','顶部构造后出现反向关键波动','仅初始结构失效'],
  'discipline':'已结束周/已确认结构；目标事先存在；预期盈利至少是风险的3倍；亏损后不改原失效位。'},
 'proxy_choices':{
  'environment':'时钟二类+日线20/60/120 SMA和EMA双组排列+已完成周同参数双组排列；平行程度仅记录。',
  'weekly':'默认周一至周五日历；120个已完成周预热；真实短周未向weekly_env_series传入交易所日历，只会延迟，不能称精确交易所短周日历。',
  'touch':'以SMA_N单线代表双均线组；low<=SMA_N+1*ATR20，close>close_lagN；当日站上SMA就能当日触碰。',
  'supported_A3':['本轮内确认的strict底部构造','从<=EMA20重新站上EMA20'],
  'unsupported_A3':['低一级周期多头排列（无分钟线）','关键位置破底翻作为独立A3分支'],
  'unsupported_locations':['既有筹码支撑','既有均线密集区支撑作为A独立输入'],
  'four_analysis_cells':['early×is_first_touch=true','early×is_first_touch=false','confirmed×is_first_touch=true','confirmed×is_first_touch=false'],
  'four_cells_note':'程序只有两个入场版本；首次/非首次组成四个研究分组，并非四套已实现的A3条件。每组再记录ma_period=20/60/120和三种独立退出。',
  'stop':'每个确认事件的stop_price=min(low[touch..confirmation])；早期与稍后的确认可各自冻结不同低点，不能据此移动已经持有的早期交易失效位。'},
 'input_requirements':{
  'raw':['DatetimeIndex按日期升序、唯一、已收盘','同一复权/计价单位的open/high/low/close','volume（虽未列入A._required_columns，周线聚合实际硬依赖）','有效价格及OHLC高低范围','足够的120根已完成周历史'],
  'derived':['signal_color','sma20/sma60/sma120','ema20/ema60/ema120','close_lag20/close_lag60/close_lag120'],
  'computed_inside':['ATR20','clock_series','weekly_env_series','detect_strict_structures'],
  'insufficient_input':'缺显式列返回[]；缺volume抛KeyError；NaN/重复索引/未收盘/复权一致性没有完整入口验证，不能将空事件等同规则未成立。',
  'excluded_input':'净值仅close、open=high=low=close的合成板块、伪造volume=0不符合完整触发所需OHLCV语义。'},
 'event_to_candidate':{
  'filter':{'rule_id':'first_ma_pullback','evidence.sub_rule':'first_ma_pullback_confirmed','evidence.entry_variant':['early','confirmed']},
  'identity':['event_id','rule_version','symbol','available_date','lifecycle_id','evidence.touch_date','evidence.ma_period','evidence.is_first_touch'],
  'entry_fields':{'signal_date':'available_date','signal_position':'frame日期位置','entry_ref_price':'evidence.entry_ref_close','stop_price':'evidence.stop_price','entry_variant':'evidence.entry_variant','ma_period':'evidence.ma_period','is_first_touch':'evidence.is_first_touch','clock_type':'evidence.clock_type','weekly_bull_env':'evidence.weekly_bull_env','entry_reason':'reason_cn'},
  'audit_fields':['evidence.a3_source','evidence.a3_structure_id','evidence.atr20','evidence.ma_value','provenance'],
  'target':'entry_specs_from_events调用reward_risk_filter，以信号时已经确认的候选目标计算；必须保留目标来源/可知日。',
  'frozen_entry_execution':'第八冻结engine在下一根开盘调用qualify_entry_at_open：冻结原目标与失效位，实际盈利/风险比例>=3、价格有效且目标>开盘>失效才接纳。当前生产engine不含此修正，二者不能混用。',
  'mapping_gaps':'EntrySpec不保留lifecycle_id、touch_date、a3_structure_id；有限账户接线必须另保留完整原始事件映射，不能只用EntrySpec解释去重/持仓缘由。'},
 'lifecycle':{
  'start':'episode不存在且clock二类、日线双组多头、周线多头时，以当日作anchor。',
  'first_touch':'每个episode/ma_period第一次触碰为true，失败或两入场版本已发出后false。',
  'reset':'SMA排列破坏、close<SMA120、black，开放中的回撤发failed，episode清空。',
  'clock_weekly_change':'不重置episode；实际clock阻断新触碰及确认，weekly仅阻断确认（新触碰漏检查）。',
  'pre_entry_failure':'close低于此前回撤最低low；或未发任一入场且close离开触碰带；不是持仓平仓指令。',
  'after_both_entries':'cycle关闭，此后不再为该cycle持续发failed。持仓失效必须由账户/退出逻辑以冻结C处理。',
  'same_day':'新触碰日只发touched；即使该日A3/A4满足，A4分支最早下一根日K才评估，这是相对文字口径的代理时序选择。'},
 'exit_contract':{
  'all_three':'收盘<固定stop_price，下一根开盘退出；是收盘确认代理，不是盘中挂单触价。',
  'a6_1_costbasis':'close<EMA20 且 close<close_lag20，下一开盘。',
  'a6_2_top_plus_keywave':'prepare_frame先取全段strict顶部日期；signal_date之后有顶部且当日costbasis条件成立，下一开盘；同一顶部确认日即可满足，未要求更晚一天，未检查顶部是否已失效。',
  'a6_3_structure_stop':'只使用固定初始失效价。',
  'separate_warning':'A6②同样依赖有历史改写问题的strict结构；本轮未单独构造退出收益反例，不宣称退出已通过资格。'},
 'findings':[
  {'id':'A-01','severity':'blocker','status':'reproduced','issue':'未来包含K线改写strict底部确认日，并传播为A历史确认事件消失。','evidence':'probe-results.json:strict_future_contained_bar/a_future_contained_bar'},
  {'id':'A-02','severity':'material','status':'reproduced_isolated','issue':'已记录的A3底部结构失效后，缓存structure_id仍可触发确认。','evidence':'probe-results.json:cached_invalidated_structure'},
  {'id':'A-03','severity':'material','status':'reproduced_isolated','issue':'周线不再多头仍可新触碰，可能消耗首次标签；确认被阻断。','evidence':'probe-results.json:weekly_false_new_touch'},
  {'id':'A-04','severity':'input_contract','status':'reproduced','issue':'缺volume时显式列校验放过，但周线聚合抛错。','evidence':'probe-results.json:volume_implicit_required'},
  {'id':'A-05','severity':'scope','status':'source_verified','issue':'仅两种A3条件，未覆盖分钟线/筹码/独立破底翻；不得宣称完整A原文所有分支。'}],
 'tests':{'existing':'20 passed in 0.60s；weekly_context、strict_structure、weekly_round2；明确指定PYTHONPATH冻结包，禁写字节码/pytest缓存。','custom':'probe.py成功；4类反例含A传播、周线21个截断对照通过；探测脚本断言问题存在，运行成功不表示生产规则合格。','not_tested':['真实基金候选和收益','完整交易所日历覆盖','所有首次/非首次四组的完整历史内容截断不变性','单独A6②退出传播','完整账户去重和持仓流程']},
 'next_step':'向用户呈交问题与最小反例；若获准，研究隔离修复strict前向状态及A缓存失效/触碰环境，再用逐日完整事件字段对照重验；本轮不自动修复、不跑收益。',
 'sources':results['sources']
}
for rel in ['tests/unit/test_first_ma_pullback.py','tests/unit/test_first_ma_pullback_backtest.py','tests/unit/test_strict_structure.py','tests/unit/test_weekly_context.py','tests/no_lookahead/test_weekly_round2.py']:
 p=ROOT/rel; contract['sources'].append({'path':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(OUT/'contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2)+'\n')
