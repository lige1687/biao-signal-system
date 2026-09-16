"""Run exactly the eight locked technical-account configurations, without fitting."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import json
import gzip
import hashlib
import importlib.util
from datetime import datetime, timezone
import pandas as pd

P = Path(__file__).resolve().parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text())

def main():
    out = P / 'account-results'
    assert not out.exists(), 'Do not overwrite existing results; preserve each attempt'
    out.mkdir()
    settings = read(P/'product-qualification/execution-parameters.json')
    prices = {}
    for s in settings['symbols']:
        rows = pd.read_csv(Path(settings['prices_directory'])/f'{s}-nominal.csv').to_dict('records')
        prices[s] = {r['date']: {k: r[k] for k in ('open','high','low','close','volume')} for r in rows}
    native_actions = read(Path(settings['actions_file']))
    actions = []
    for a in native_actions:
        e = dict(a, ex_date=a['effective_date'])
        if a['type'] == 'cash_dividend': e['cash_per_share'] = float(a['cash'])
        else: e['ratio'] = float(a['ratio'])
        actions.append(e)
    with gzip.open(P/'candidate-study/candidates.json.gz','rt') as f: candidates=json.load(f)
    with gzip.open(P/'candidate-study/exit-observations.json.gz','rt') as f: observations=json.load(f)
    files = [P/'technical-account/engine.py', Path(__file__), P/'protocol.md', P/'protocol-addendum-01.md',
             P/'product-qualification/execution-parameters.json', Path(settings['actions_file']),
             P/'candidate-study/candidates.json.gz', P/'candidate-study/exit-observations.json.gz',
             P/'candidate-study/forward-checks.json']
    files += list(Path(settings['prices_directory']).glob('*.csv'))
    for f,h in read(P/'candidate-study/run-lock.json')['files'].items():
        assert sha(Path(f)) == h, ('candidate input changed', f)
    assert all(x['matched'] for x in read(P/'candidate-study/forward-checks.json'))
    lock = {'started_at_utc':datetime.now(timezone.utc).isoformat(), 'configs':['P'+str(i) for i in range(8)],
            'files':{str(f):sha(f) for f in files}, 'settings':settings,
            'weekly_per_symbol':250, 'fee_per_side':.001, 'cash_interest':0,
            'start':'2015-01-01', 'end':'2026-06-30', 'full_B_qualified':False,
            'scope':'known-event daily-price approximate research accounts'}
    (out/'run-lock.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2)+'\n')
    spec=importlib.util.spec_from_file_location('isolated_technical_account',P/'technical-account/engine.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for cfg in lock['configs']:
        selected=[c for c in candidates if c['config_id']==cfg]
        result=module.simulate(prices,actions,selected,observations,
            start=lock['start'],end=lock['end'],weekly_per_symbol=250,fee=.001,config_id=cfg,
            limits=settings['limits'],limit_changes=settings['limit_changes'],blocked_dates=settings['blocked_dates'])
        folder=out/cfg; folder.mkdir()
        for name in ['daily','trades']:
            pd.DataFrame(result[name]).to_csv(folder/(name+'.csv'),index=False)
        for name in ['orders','events','roundtrips']:
            (folder/(name+'.json')).write_text(json.dumps(result[name],ensure_ascii=False,indent=2,allow_nan=False)+'\n')
        assert all(abs(r['accounting_difference'])<1e-7 for r in result['daily'])
        assert all(sha(Path(f))==h for f,h in lock['files'].items()), 'input changed during simulation'
        print(cfg, 'completed',len(result['daily']), 'dates',len(result['trades']),'trades', flush=True)
    (out/'completion.json').write_text(json.dumps({'finished_at_utc':datetime.now(timezone.utc).isoformat(),
         'configs_completed':lock['configs'],'all_input_hashes_unchanged':True},indent=2)+'\n')

if __name__=='__main__': main()
