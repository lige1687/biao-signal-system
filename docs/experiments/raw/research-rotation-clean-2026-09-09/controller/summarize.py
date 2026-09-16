from pathlib import Path
import json,pandas as pd
B=Path(__file__).resolve().parents[1];X=B/'full-execution';s=json.loads((X/'summary.json').read_text())['accounts'];e=pd.read_csv(X/'equity.csv',parse_dates=['date']);a=pd.read_csv(X/'annual.csv');p=pd.read_csv(X/'per_symbol.csv',dtype={'symbol':str})
comparisons=[]
for pool in ('full14','industry7'):
 d={r['config']:r for r in s if r['account_id'].startswith(pool) and r['fee']==.001}
 for new,ref,label in [('momentum_top3','equal','选强与波动过滤'),('equal_sma200','equal','平均配置增加退出及月度等待'),('momentum_top3_sma200','momentum_top3','选强增加退出及月度等待'),('momentum_top3_sma200','equal_sma200','已有退出时增加选强与波动过滤'),('momentum_top3_sma200','equal','完整候选相对简单平均配置')]:
  comparisons.append({'pool':pool,'comparison':label,'new':new,'reference':ref,'cagr_difference_pp':100*(d[new]['cagr']-d[ref]['cagr']),'drawdown_reduction_pp':100*(d[new]['max_drawdown']-d[ref]['max_drawdown']),'terminal_difference':d[new]['final']-d[ref]['final']})
pd.DataFrame(comparisons).to_csv(B/'controller/comparisons.csv',index=False)
periods=[]
for r in s:
 if r['fee']!=.001:continue
 g=e[e.account_id==r['account_id']].set_index('date');v=float(g.loc['2024-12-31','equity']);years=(pd.Timestamp('2024-12-31')-pd.Timestamp('2020-12-01')).days/365.2425
 periods.append({'account_id':r['account_id'],'equity_end_2024':v,'return_through_2024':v/1e6-1,'annualized_through_2024':(v/1e6)**(1/years)-1,'gain_after_2024':r['final']-v,'post_2024_gain_fraction_of_full_gain':(r['final']-v)/(r['final']-1e6)})
pd.DataFrame(periods).to_csv(B/'controller/period-concentration.csv',index=False)
q=e[e.account_id.str.startswith('full14')&e.account_id.str.endswith('0.001')].pivot(index='date',columns='account_id',values='equity');m=q.resample('ME').last().pct_change();m.loc['2024'].to_csv(B/'controller/2024-monthly.csv')
e[(e.account_id=='full14-equal_sma200-fee0.001')&e.date.between('2024-09-20','2024-10-10')][['account_id','date','equity','exposure']].to_csv(B/'controller/waiting-example.csv',index=False)
print(pd.DataFrame(periods).to_string(index=False))
print(p[p.account_id=='full14-momentum_top3_sma200-fee0.001'].sort_values('net_pnl',ascending=False)[['symbol','net_pnl']].to_string(index=False))
