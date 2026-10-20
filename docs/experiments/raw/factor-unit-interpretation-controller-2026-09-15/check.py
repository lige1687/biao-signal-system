"""Independent synthetic checks only; no real prices or strategy runs."""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT/'src'))
import pandas as pd
from lei_signal.research.factor_unit.state_description import describe_states

w0 = list(range(1,23))
w1 = list(range(2,24))
edges0 = set(zip(w0[:-1],w0[1:]))
edges1 = set(zip(w1[:-1],w1[1:]))
assert len(set(w0)&set(w1)) == 21
assert len(edges0&edges1) == 20
dates = pd.date_range('2020-01-01',periods=100)
schedule = pd.DataFrame({'session':dates,'close_at':dates.tz_localize('Asia/Shanghai')+pd.Timedelta(hours=15)})
values = pd.DataFrame({'symbol':'SYN','session':dates,'state':[True]*100,'I':[100.]*100})
contract = {'data_mode':'synthetic','object_ref':'candidate:lei.dual_ma.bull_state@draft-1',
            'lookback':20,'e_offset':1,'x_offset':22,'evaluation_window':{'start':str(dates[0].date()),'end':str(dates[79].date())},
            'research_cutoff':'2030-01-01T15:00:00+08:00','sparse_anchor_session':{'SYN':str(dates[0].date())},'sparse_step':23}
result = describe_states(values,schedule,contract)['symbols']['SYN']
slots = result['sparse_view']['slots']
assert slots[-1]['session'] == str(dates[92].date())
assert slots[-1]['skipped_reason'] == 'missing_row'
assert sum(result[k] for k in ['state_true','state_false','state_unknown']) == result['observations_in_window']
out = {'overlap':{'shared_price_points':21,'shared_intervals':20,'interval_fraction':20/21},
       'F1_last_slot':slots[-1], 'state_count_sum':result['state_true']+result['state_false']+result['state_unknown'],
       'observations_in_window':result['observations_in_window'],
       'sparse_valid_true_denominator':sum(s['state'] is True and not s['skipped'] for s in slots),
       'mean_median_counterexample':{'negative_count':51,'positive_count':49,'mean':statistics.mean([-.01]*51+[.02]*49),'median':statistics.median([-.01]*51+[.02]*49)},
       'real_data_used':False}
text = json.dumps(out,ensure_ascii=False,indent=2)
print(text)
if len(sys.argv)>1:
    with Path(sys.argv[1]).open('x') as f:
        f.write(text+'\n')
