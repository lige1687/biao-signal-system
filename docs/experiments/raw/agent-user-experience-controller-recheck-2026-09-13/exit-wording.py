"""Read-only, synthetic truth table for the engine's actual prepare_frame function."""
import sys,json
from unittest.mock import patch
from pathlib import Path
import pandas as pd
root=Path('/Users/yongbiaoli/lei-agent-ux-20260913');sys.path.insert(0,str(root/'src'))
from lei_signal.backtest import engine
frame=pd.DataFrame({'close':[105.,95.,95.,85.],'ema20':[100.,100.,90.,100.],'close_lag20':[100.,90.,100.,90.]})
# Unrelated prepare_frame work is stubbed; costbasis_cond is executed unchanged.
with patch.object(engine,'average_true_range',return_value=None),patch.object(engine,'detect_strict_structures',return_value=[]),patch.object(engine,'clock_series',return_value=None):
 actual=engine.prepare_frame(frame)['costbasis_cond'].tolist()
rows=[]
for i,r in frame.iterrows():
 wording=(r['close']<r['ema20']) or (r['close']<r['close_lag20'])
 rows.append({'close':r['close'],'ema20':r['ema20'],'lag20':r['close_lag20'],'actual_engine_exit_condition':actual[i],'new_wording_any_one_breaks':bool(wording),'matches':actual[i]==bool(wording)})
print(json.dumps({'rows':rows,'verdict':'PASS' if all(x['matches'] for x in rows) else 'FAIL'},ensure_ascii=False,indent=2))
