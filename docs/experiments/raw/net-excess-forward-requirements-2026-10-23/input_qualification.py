"""Inventory existing price inputs; do not compute factor effects or infer availability."""
from pathlib import Path
from datetime import datetime
import hashlib,json
import pandas as pd

MAIN=Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
D=Path(__file__).resolve().parent
spec=[('close_only','docs/experiments/raw/sentiment-aaii-risk-2026-09-29/inputs/px_SPY.csv'),('older_ohlc','docs/experiments/raw/agent_BC/pool/SPY.bars.parquet')]
rows=[]
for key,rel in spec:
    p=MAIN/rel
    f=pd.read_csv(p,index_col=0) if p.suffix=='.csv' else pd.read_parquet(p)
    dates=pd.to_datetime(f.index)
    rows.append({'id':key,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'rows':len(f),'columns':list(f.columns),'start':str(dates.min().date()),'end':str(dates.max().date()),'version_arrival_history':'not_verified','next_open_in_file':any(str(x).lower()=='open' for x in f.columns),'late_2026_formation_month_complete':False,'usable_for_strict_forward_effect':False})
output={'at':datetime.now().astimezone().isoformat(),'purpose':'qualify_inputs_only_no_effects','sources':rows,'decision':'do_not_assign_current_market_state_from_incomplete_stale_inputs','missing':['qualified historical version/publication and actual acquisition times','complete September 2026 formation close for current decision','bound benchmark/currency/dividend basis and execution inputs','personal fee profile and executed turnover'],'real_effect_runs':0,'new_market_requests':0,'storage_current':'passed_independent_preflight; prior failure not current blocker'}
(D/'input-qualification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(output,ensure_ascii=False))
