"""Independent standard-library reconciliation of counts, input fingerprints and dates."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--root', type=Path, required=True)
ap.add_argument('--cache-root', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
here = Path(__file__).resolve().parent
p = json.loads((here/'protocol.json').read_text())
r = json.loads((here/'result.json').read_text())
checked = []
for entry in p['inputs']+p['code']:
    path = (args.cache_root if entry['location']=='CACHE' else args.root)/entry['path']
    assert path.stat().st_size == entry['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
    checked.append(entry['path'])
with (args.root/p['aaii_panel']).open() as f:
    dates = [row['t'] for row in csv.DictReader(f)]
assert sum(r['us_aaii_dates']['three_class_dates'].values()) == len(set(dates)) == len(dates)
assert r['us_aaii_dates']['date_range'] == [min(dates),max(dates)]
for state, count in r['us_aaii_dates']['three_class_dates'].items():
    assert sum(v['three_class_dates'][state] for v in r['us_aaii_dates']['eras'].values()) == count
history = json.loads((args.cache_root/'sector_trend_history.json').read_text())
codes = set().union(*(set(row['boards']) for row in history))
cn = r['cn_board_input_support']; assert len(history)==cn['distinct_dates']
assert codes == set(cn['per_board']) and len(codes)==cn['distinct_boards']
def valid(v):
    return isinstance(v,(int,float)) and math.isfinite(v)
flows = json.loads((args.cache_root/'tx_sector_flow_pilot.json').read_text())['boards']
for code, s in cn['per_board'].items():
    prices = {row['date'] for row in history if valid(row['boards'].get(code,{}).get('close')) and row['boards'][code]['close']>0}
    flow_dates = {row['date'][:10] for row in flows.get(code,[]) if valid(row.get('small_yi'))}
    assert len(prices)==s['finite_close']
    assert len(prices & flow_dates)==s['same_date_flow_close']
    assert sum(s['three_class_dates'].values())==len(history)
    assert sum(s['five_class_dates'].values())==len(history)
    assert s['b200_dates']==sum(valid(row['boards'].get(code,{}).get('b200')) for row in history)
assert cn['boards_with_all_three_states']==sum(all(s['three_class_dates'][k]>0 for k in ['up','sideways','down']) for s in cn['per_board'].values())
assert cn['boards_with_140_same_date_flow_close']==sum(s['same_date_flow_close']>=140 for s in cn['per_board'].values())
assert r['model_fits']==0 and not r['future_targets_read']
assert not args.output.exists()
args.output.write_text(json.dumps({'status':'passed','verified_inputs_and_code':checked,'US_dates':len(dates),
    'CN_boards':len(codes),'CN_dates':len(history),'checks':'source SHA, group/era denominators, board union, price-flow date intersections, b200 field absence',
    'limitation':'core scalar oracle checks labels; this independent script checks persisted counts and dates, not factor effectiveness'},ensure_ascii=False,indent=2)+'\n')
print('saved counts and input hashes verified')
