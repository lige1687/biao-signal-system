"""Independent, synthetic verification. No production DB or service startup."""
import hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
DEV=Path('/Users/yongbiaoli/lei-agent-ux-20260913')
RUN=Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
OUT=Path(__file__).parent
sys.path.insert(0,str(DEV/'src'))
import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lei_signal.backtest import engine
from lei_signal.domain.rules_config import ruleset_version
from lei_signal.plans.monitor import MonitorContext
from lei_signal.plans.store import create_plan, get_plan
from lei_signal.storage.sqlite_store import connect
from lei_signal.api.routes import plans as route
from lei_signal.research.module_backtest import module_of
files=['web/src/utils/agentUx.ts','web/src/components/CreatePlanDialog.tsx','web/src/components/PlanDraftCard.tsx','web/src/components/PlanCreateFlow.tsx','web/src/components/ReviewDrawer.tsx','src/lei_signal/backtest/engine.py','src/lei_signal/api/routes/plans.py','src/lei_signal/plans/conformance.py','src/lei_signal/research/module_backtest.py']
def hashes(root): return {f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files}
before=hashes(DEV)
frame=pd.DataFrame({'close':[105.,95.,95.,85.],'ema20':[100.,100.,90.,100.],'close_lag20':[100.,90.,100.,90.]})
with patch.object(engine,'average_true_range',return_value=None),patch.object(engine,'detect_strict_structures',return_value=[]),patch.object(engine,'clock_series',return_value=None):
    truth=engine.prepare_frame(frame)['costbasis_cond'].tolist()
assert truth == [False,False,False,True]
text=(DEV/'web/src/utils/agentUx.ts').read_text()
assert '收盘价同时低于20日指数均线（EMA20）和20个交易日前的收盘价' in text
assert '下一交易日开盘退出；初始结构止损仍独立生效' in text
assert module_of('ema20_reclaim_rising') is None
old=re.search(r'const RULESET = "([^"]+)"', (DEV/'web/src/components/CreatePlanDialog.tsx').read_text()).group(1)
version=ruleset_version()
ctx=MonitorContext(last_bar_date='2026-09-11',cache_fallback_used=False,current_close=10.,ema20=9.,tradability_tradable=True,tradability_blocking_reasons=(),ruleset_version=version,opportunities=(),exit_signals=(),new_event_rule_ids=())
results=[]
with tempfile.TemporaryDirectory(prefix='lei-plan-controller-') as tmp:
    db=Path(tmp)/'plans.db'
    conn=connect(db)
    app=FastAPI();app.state.plans_db_path=str(db)
    app.state.analysis_service=SimpleNamespace(get=lambda _:SimpleNamespace(result=object()))
    app.include_router(route.router)
    with TestClient(app) as client,patch.object(route,'context_from_result',return_value=ctx):
        for name,v,rule,expected in [('detail-hardcoded',old,'first_ma_pullback',409),('conversation-early-signal',version,'ema20_reclaim_rising',422),('valid-control',version,'first_ma_pullback',200)]:
            p=create_plan(conn,symbol='SYNTHETIC',module='A',direction='long',reason='主控合成确认对照',ruleset_version=v,entry_rule_id=rule,invalidation_price=9.,entry_price_ref=10.,target_b_price=14.,valid_until='2099-12-31',entry_trigger_cn='合成入场',thesis_cn='合成理由',invalidation_criteria_cn='合成失效',drawdown_playbook_cn='合成回撤',take_profit_plan_cn='合成止盈',stop_plan_cn='合成止损')
            r=client.post(f'/api/plans/{p.plan_id}/confirm')
            assert r.status_code==expected,(name,r.text)
            data=r.json(); state=get_plan(conn,p.plan_id).state
            assert state==('armed' if expected==200 else 'draft')
            results.append({'case':name,'http':r.status_code,'state':state,'response':data})
    conn.close()
preexisting={}
for f in files[1:]:
    baseline=subprocess.check_output(['git','show',f'a61fc671:{f}'],cwd=DEV)
    preexisting[f]=hashlib.sha256(baseline).hexdigest()==before[f]
manifest=json.loads((RUN/'docs/prompts/agent-user-experience-phase1-2026-09-13.inputs.json').read_text())
protection={f:hashlib.sha256((RUN/f).read_bytes()).hexdigest()==h for f,h in manifest['files'].items()}
assert hashes(DEV)==before
out={'dev_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=DEV,text=True).strip(),'engine_truth':truth,'ui_rule_version':old,'active_rule_version':version,'confirm_cases':results,'baseline_identical':preexisting,'runtime_protected':protection,'dev_hashes':before,'source_unchanged':True,'limits':'Synthetic analysis context injected; actual confirm route/conformance/store. No full browser rerun or real model.'}
(OUT/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({k:out[k] for k in ['engine_truth','ui_rule_version','active_rule_version','baseline_identical','runtime_protected','source_unchanged']},ensure_ascii=False,indent=2))
print('HTTP:',[(r['case'],r['http'],r['state']) for r in results])
