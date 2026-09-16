"""Pure synthetic edge probes. Does not edit/call run_e01 main or save helpers."""
from pathlib import Path
import ast,json,hashlib
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parent;P=R.parent;src=P/'run_e01.py';source=src.read_text();tree=ast.parse(source);tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['risk_stats','account']];ns={'np':np,'pd':pd};exec(compile(tree,'frozen_account_edge_probe','exec'),ns)
idx=pd.bdate_range('2020-01-01',periods=900);base=pd.DataFrame({'open':1.,'close':1.},index=idx);ev=[{'e':0,'decision_at':idx[0]+pd.Timedelta(hours=16)}]
d=base.copy();d.iloc[3,d.columns.get_loc('open')]=np.nan;s,days,plans,events,actions=ns['account'](d,0,ev,0.,'missing_buy_open');buys=[a for a in actions if a['action']=='buy']
buy={'scheduled':'2020-01-05 23:59:00','first_quote_invalid':str(idx[3].date()),'first_valid_open_after_schedule':str(idx[4].date()),'actual_first_buy':buys[0]['date'],'expected_schedule_retained':buys[0]['date']==str(idx[4].date())}
d=base.copy();d.iloc[252,d.columns.get_loc('close')]=2.;d.iloc[253,d.columns.get_loc('open')]=np.nan;s,days,plans,events,actions=ns['account'](d,0,ev,0.,'missing_sell_open');sells=[a for a in actions if a['action']=='sell']
sell={'known_target_after_close':str(idx[252].date()),'first_quote_open_invalid':str(idx[253].date()),'first_valid_open_after_signal':str(idx[254].date()),'actual_sell_date':sells[0]['date'],'actual_reason':sells[0]['reason'],'expected_signal_retained':sells[0]['date']==str(idx[254].date())}
out={'scope':'Synthetic missing-open cases only; frozen real E01 price inputs have no such null values.','source_sha256':hashlib.sha256(source.encode()).hexdigest(),'source_unchanged':source==src.read_text(),'buy':buy,'sell':sell};(R/'missing-open-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))
