"""Small synthetic definition checks; these are not investment backtests."""
from fractions import Fraction as Q
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
# For a consistent daily SMA20/EMA20 recursion, direction and price tests agree.
color=[]
for old_price in [Q(90),Q(100),Q(110)]:
 for prev_ema in [Q(90),Q(100),Q(110)]:
  for close in [Q(90),Q(100),Q(110)]:
   next_ema=Q(2,21)*close+Q(19,21)*prev_ema
   sma_change=(close-old_price)/20
   by_prices=close>next_ema and close>old_price
   by_slopes=next_ema>prev_ema and sma_change>0
   assert by_prices==by_slopes
   color.append(by_prices)
# Known beta and intercept fixture: lower beta alone can match simply less exposure.
x=list(map(Q,[-2,-1,0,1,2]));y=[Q(1,2)*v+Q(1,10) for v in x]
xbar=sum(x)/len(x);ybar=sum(y)/len(y)
beta=sum((a-xbar)*(b-ybar) for a,b in zip(x,y))/sum((a-xbar)**2 for a in x)
assert beta==Q(1,2)
# Explicitly defined cumulative share conversion: old factor2, new factor1 for 2:1 split.
old_shares,new_shares,old_factor,new_factor=Q(100),Q(200),Q(2),Q(1)
mult=(new_shares*new_factor)/(old_shares*old_factor)-1
div=(new_shares/new_factor)/(old_shares/old_factor)-1
assert mult==0 and div==3
# A 12-row shift is exactly 12 months only if the panel has no missing monthly rows.
months=[m for m in range(1,15) if m!=5]
assert months[-1]-months[-13]==13
result={'synthetic_only':True,'green_price_vs_slope_cases':len(color),'equivalent_cases':len(color),'color_note':'equivalence requires same source, seed, timing and missing handling; state vs transition remains different','known_beta':float(beta),'split_only_example':{'assumed_factor_convention':'convert each historical share count to latest share units: old2/new1','multiplication_net_growth':float(mult),'division_net_growth':float(div),'claim':'demonstrates why conversion convention must be checked; does not adjudicate all vendor definitions'},'missing_month_example':{'lag_rows':12,'actual_elapsed_months':13,'claim':'OSAP AssetGrowth group shift(12) requires upstream complete monthly panel'},'market_returns_evaluated':False}
with (HERE/'definition-invariants.json').open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False))
