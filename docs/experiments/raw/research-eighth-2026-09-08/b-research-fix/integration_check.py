"""Fresh-process import isolation and scalar integration verification."""
import sys,json,hashlib,platform
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).resolve().parent;sys.dont_write_bytecode=True;sys.path.insert(0,str(P/'research-package/src'))
import pandas,numpy,yaml
from lei_signal.features.indicators import compute_features
from lei_signal.rules.dense_breakout import detect_dense_breakout_events
from lei_signal.backtest.engine import entry_specs_from_events,b3_exit_triggered,simulate_trade
from lei_signal.backtest.entry_qualification import qualify_entry_at_open
from lei_signal.domain.rules_config import load_ruleset,_default_config_path
mods={n:str(Path(m.__file__).resolve()) for n,m in sys.modules.items() if n.startswith('lei_signal') and getattr(m,'__file__',None)}
expected=(P/'research-package/src').resolve()
wrong={n:p for n,p in mods.items() if not Path(p).is_relative_to(expected)}
q=qualify_entry_at_open(open_price=10.,stop_price=9.,target_price=13.)
b=b3_exit_triggered(close=102.,sma20=100.,sma60=100.1,close_lag20=100.,breakout_reference=101.,entry_variant='breakout')
obj={'time_utc':datetime.now(timezone.utc).isoformat(),'loaded_lei_modules':mods,'outside_package':wrong,'config_path':str(_default_config_path()),'config_matches_package':_default_config_path()==P/'research-package/configs/rules.v2.yaml','exact3_accepted':q.accepted,'breakout_alignment_only_no_exit':not b,'passed':not wrong and q.accepted and not b}
(P/'integration-check.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
(P/'environment.json').write_text(json.dumps({'python':platform.python_version(),'executable':sys.executable,'pandas':pandas.__version__,'numpy':numpy.__version__,'PyYAML':yaml.__version__,'network_calls':0,'installs':0},indent=2)+'\n')
r=load_ruleset();(P/'effective-config.json').write_text(json.dumps({'research_implementation_id':'b-research-fix-2026-09-08-v1','original_ruleset_version':r['ruleset_version'],'configuration_changed':False,'dense_breakout':r['rules']['dense_breakout'],'tradability_gate':r['rules']['tradability_gate'],'reward_risk_filter':r['rules']['reward_risk_filter'],'note':'YAML为冻结来源，不代表其旧文字已描述本次代码修复；以protocol与patch记录研究覆盖。'},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'imported_modules':len(mods),'outside_package':wrong,'passed':obj['passed']}))
