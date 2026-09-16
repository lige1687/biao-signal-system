import sys,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.path.insert(0,str(P/'snapshot/src'))
import pandas as pd
from lei_signal.rules.clock_classifier import clock_series
from lei_signal.rules.dense_breakout import _state_age_series
out=P/'s02-age-diagnostic.json'
assert not out.exists()
f=pd.read_csv(P/'attempt-01/synthetic-full-features.csv',index_col='date',parse_dates=True)
e=json.loads((P/'attempt-01/synthetic-full-events.json').read_text());watch=next(x for x in e if x['sub']=='dense_breakout_watch')['date'];pos=f.index.get_loc(pd.Timestamp(watch))
c=clock_series(f);age=_state_age_series(c==3,exit_bars=20);first=next(i for i,v in enumerate(c) if v==3)
obj={'diagnostic_of':'S02 same existing synthetic frame, no new case','checked_at_utc':datetime.now(timezone.utc).isoformat(),'plan_sha256':hashlib.sha256((P/'s02-diagnostic-plan.md').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'input_sha256':hashlib.sha256((P/'attempt-01/synthetic-full-features.csv').read_bytes()).hexdigest(),'first_valid_clock3_position':first,'first_valid_clock3_date':str(f.index[first].date()),'age_at_first_valid_clock3':int(age.iloc[first]),'watch_position':int(pos),'watch_date':watch,'age_at_watch':int(age.iloc[pos]),'actual_clock3_bars_until_watch':int((c.iloc[:pos+1]==3).sum()),'initial_insufficient_rows':int((c.iloc[:first]==0).sum()),'finding':'初始化无有效横盘状态时的False也计入寿命；此例126寿命只有112根有效横盘，预热期计入14根。不能将S02突破行为通过解释为126有效横盘已验证。'}
out.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');print(json.dumps(obj,ensure_ascii=False))
