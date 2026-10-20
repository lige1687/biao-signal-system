"""Isolated audit, not a new strategy; protocol.md fixes scope before this run."""
from pathlib import Path
import hashlib, importlib.util, json, math, socket, sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / 'inputs/docs/experiments/raw'
sys.dont_write_bytecode = True
def no_network(*args, **kwargs):
    raise RuntimeError('Offline research only')
socket.create_connection = no_network
socket.socket.connect = no_network

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def fill_position(bars, entry_pos, n, cn):
    """Reproduce legacy fill behavior, including its final-row restriction limitation."""
    if not cn:
        return entry_pos+n-1, 'close'
    p = entry_pos+n
    if p >= len(bars):
        return None, 'missing_next_open'
    while p+1 < len(bars) and bars.close.iloc[p] > 0 and bars.open.iloc[p] <= bars.close.iloc[p-1]*.905:
        p += 1
    return p, 'open'

def main():
    lock = json.loads((HERE/'input-lock.json').read_text())
    assert digest(HERE/'protocol.md') == lock['protocol_sha256']
    assert all(digest(Path(x['snapshot_path'])) == x['sha256'] for x in lock['files'])
    path = HERE/'inputs/scripts/run_time_stop_tail_aware_full_pool.py'
    spec = importlib.util.spec_from_file_location('frozen_old', path)
    old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    df = pd.read_csv(RAW/'time_stop_tail_aware_full_pool/events_per_trade.csv')
    assert not df.duplicated(['module','symbol','signal_date']).any()
    events = []
    checks = []
    cache = {}
    for symbol in sorted(set(df.symbol)):
        bars = pd.read_parquet(RAW/'pool-snapshot-2026-08-25'/f'{symbol}.bars.parquet')
        if 'date' in bars:
            bars = bars.set_index(pd.to_datetime(bars.date))
        assert bars.index.is_monotonic_increasing and not bars.index.duplicated().any(), symbol
        cache[symbol] = bars
    for record in df.to_dict('records'):
        bars = cache[record['symbol']]
        p = int(bars.index.get_loc(pd.Timestamp(record['entry_date'])))
        end = max(p+14,int(bars.index.get_loc(pd.Timestamp(record['exit_date']))))
        assert np.isfinite(bars[['open','close']].iloc[p:end+1].to_numpy()).all(), record
        risk = record['entry_price']-record['stop_price']
        assert risk > 0
        for k in (5,10,15):
            actual = (float(bars.close.iloc[p+k-1])-record['entry_price'])/risk
            assert math.isclose(actual, record[f'r_at_{k}'], abs_tol=1e-9), (record,k)
        record.update(risk=risk,_pos=p,_bars=bars,_ser_close=bars.close.to_numpy())
        events.append(record)
    alive = [e for e in events if e['holding_bars'] >= 10]
    assert len(alive) == 899
    historical = {}; old.run_step2(events, historical)
    archived = json.loads((RAW/'time_stop_tail_aware_full_pool/time_stop_tail_aware_full_pool_results.json').read_text())
    for got, expected in zip(historical['step2_cells'], archived['step2_cells'], strict=True):
        for key in ('n','triggered','triggered_tail','expR','delta_expR'):
            assert math.isclose(got[key], expected[key], abs_tol=1e-10), (key,got,expected)
    rows = []; summaries = []
    for cell in historical['step2_cells']:
        n = cell.get('N',10+cell.get('M',0)); conditional = cell['kind']=='conditional'
        arm = f"conditional_{cell['theta']}_{n}" if conditional else f'plain_{n}'
        fixed = []; flawed = []; trigger_count = 0; dup_count = 0; blocked_final = 0
        for e in alive:
            bars=e['_bars']; p=e['_pos']; ep=e['entry_price']; risk=e['risk']; base=e['r_net']
            triggered=False; fill=None; price=None; new=base
            if e['holding_bars'] >= n:
                trigger = (e['r_at_10']<=cell['theta'] and (bars.close.iloc[p+n-1]-ep)/risk<=cell['theta']) if conditional else bars.close.iloc[p:p+n].max()<=ep
                if trigger:
                    fill, side = fill_position(bars,p,n,e['symbol'].endswith(('.SS','.SZ')))
                    if fill is not None:
                        price=float(bars[side].iloc[fill]); assert math.isfinite(price)
                        new=(price-ep-2*max(.0005,.005/ep)*ep)/risk
                        triggered=True
                        if side=='open' and fill==len(bars)-1 and price<=bars.close.iloc[fill-1]*.905:
                            blocked_final+=1
            fixed.append(new); flawed.append(new)
            duplicate=triggered and not conditional and not e['is_tail']
            if duplicate: flawed.append(base); dup_count+=1
            trigger_count+=int(triggered)
            rows.append({'arm':arm,'module':e['module'],'symbol':e['symbol'],'signal_date':e['signal_date'],'entry_date':e['entry_date'],'old_exit_date':e['exit_date'],'new_exit_date':str(bars.index[fill].date()) if fill is not None else e['exit_date'],'triggered':triggered,'old_duplicate_append':duplicate,'old_r':base,'new_r':new,'delta_r':new-base,'old_effective_one_side_bps':max(5,50/ep),'new_price':price})
        assert len(fixed)==len(alive)
        assert trigger_count==cell['triggered']
        assert math.isclose(float(np.mean(flawed)),cell['expR'],abs_tol=1e-10)
        summaries.append({'arm':arm,'opportunities':len(alive),'old_mean_vector_length':len(flawed),'corrected_vector_length':len(fixed),'duplicate_appends':dup_count,'triggered':trigger_count,'triggered_tail':cell['triggered_tail'],'base_mean_r':cell['base_expR'],'old_mean_r':cell['expR'],'corrected_mean_r':float(np.mean(fixed)),'old_delta_r':cell['delta_expR'],'corrected_delta_r':float(np.mean(fixed)-cell['base_expR']),'old_row_resampling_interval_reproduction_only':cell['boot_ci95'],'last_row_restricted_fill_count':blocked_final})
    detail=pd.DataFrame(rows)
    assert not detail.duplicated(['arm','module','symbol','signal_date']).any()
    detail.to_csv(HERE/'time-exit-paired-ledger.csv',index=False)
    report={'scope':'legacy calculation audit; no new profitability certification','event_rows':len(events),'alive10':len(alive),'symbols':len(cache),'all_six_old_means_and_triggers_match_archive':True,'all_old_observation_prices_match':True,'cells':summaries,'protocol_sha256':digest(HERE/'protocol.md'),'code_sha256':digest(Path(__file__)),'input_lock_sha256':digest(HERE/'input-lock.json'),'ledger_sha256':digest(HERE/'time-exit-paired-ledger.csv')}
    (HERE/'time-exit-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
