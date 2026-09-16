from pathlib import Path
import json,hashlib,copy,datetime
from lei_signal.research.definitions import load_registry,resolve,validate_registry
R=Path(__file__).resolve().parents[5];W=Path(__file__).resolve().parents[1];p=R/'docs/research/definitions.v1.json';r=load_registry();before=copy.deepcopy(r)
props=json.loads((W/'execution/definition-proposal.json').read_text())['objects'];cards=[]
for i,prop in enumerate(props):
 c=resolve(r,'etf.trend.above50@1.0.0' if i==0 else 'baseline.etf_price200@1.0.0');c.pop('profile',None)
 for key in ['id','version','name','type','uses','not_for','scope','definition','validation']:c[key]=copy.deepcopy(prop[key])
 c['input']['price_basis']='etf.price.continuous@1.0.0的冻结ETF连续价算法；账户用名义开收盘与独立公司行动。只在有报价日连接恰好该日生效的动作；非报价日行动尚未泛化支持。'
 c['input']['fields']=['date','symbol','nominal_open','nominal_close','actions','restrictions','price_limit_regimes']
 c['universe'].update(version='first12冻结510300/159915名义行情及行动；固定2018-07-05—2026-06-30',warmup='含当日最近50条有效连续收盘；不足返回缺失且不发指令',missing='信号不填缺报价；账户缺开盘/受限订单延期；同日新收盘状态改变替换旧订单；其余沿冻结B1执行',quality_gate='有限冻结ETF输入；历史到达时间未知，不依赖股票宽度覆盖率',degrade='未覆盖的公司行动/报价异常阻断适用性；不能自动推广至其他产品')
 c['time'].update(observation_time='ETF有效报价日收盘后',available_at='冻结输入实际到达时间未知；本次重算时已取得，不伪造历史available_at',decision_at='有效收盘后，首次或二元状态变化时',execution_at='严格晚于信号日的下一允许开盘',effective_from='2026-09-09研究定义登记；不追溯改生产')
 c['dependencies']=['etf.price.continuous@1.0.0'] if i==0 else ['etf.trend.price50.state@1.0.0','cash.zero@1.0.0']
 c['sources']=['price50_protocol','etf_510300','etf_159915','etf_actions','etf_restrictions','etf_limits']
 c['status']={'definition_clarity':'explicit','data_qualification':'limited_frozen_etf_inputs_historical_availability_unknown','implementation':'isolated_adapter_pre_result_definition','effectiveness':'not_yet_evaluated_at_definition_freeze','production':'not_authorized'}
 c['validation']['limitations']='仅绑定本轮两ETF冻结输入；纯50日跌回均线会退出，W3价格确认转负本身不退出。完整方案差不能全部归于宽度；旧消费者未迁移。'
 if i==1:
  c['policy'].update(weights='状态1目标100%，状态0目标0%；=SMA50为0；不足50条不发指令',rebalance='首次有效收盘及其后状态改变后生成订单；不每日恢复比例，分红到账不单独触发买入',exit='收盘状态变0后下一允许开盘全部退出；不假设当天收盘成交',reentry='以后收盘状态变1后下一允许开盘重新投入',execution='本批execution/run_price50.py隔离适配；名义开盘、现金费用、100份、停牌限价延期；新状态可替换受限旧单',investability='真实ETF历史账户近似；价差/容量/历史到达时间未验，不授权交易')
 cards.append(c)
source=W/'protocol.md';r['sources']['price50_protocol']={'path':str(source.relative_to(R)),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
assert not any(x['id'] in [c['id'] for c in cards] for x in r['objects'])
r['objects'].extend(cards);r['version']='1.1.0';r['changelog'].append({'version':'1.1.0','date':'2026-09-09','change':'新增纯50有效报价状态及完整ETF二元账户两个研究定义；旧对象版本、公式、来源保持。'})
validate_registry(r)
(W/'controller/registry-before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n');p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
(W/'controller/price50-resolved-definition-cards.json').write_text(json.dumps({c['id']+'@'+c['version']:resolve(r,c['id']+'@'+c['version']) for c in cards},ensure_ascii=False,indent=2)+'\n')
print('Registered two new objects, preserving all old objects:',r['version'])
