"""Describe known entry geometry; never calculate future price returns."""
from pathlib import Path
from decimal import Decimal
import gzip, json, hashlib

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'research-broad-etf-technical-2026-09-08/execution/inputs/source-candidates/precision-candidates.json.gz'

def main():
    with gzip.open(SOURCE, 'rt') as f:
        candidates = json.load(f)
    candidates = [c for c in candidates if c['config_id'] == 'C1' and c['symbol'] in ('sh510300', 'sz159915')]
    rows = []
    for c in candidates:
        ev = c['source_event']['evidence']
        ref, stop = Decimal(str(c['signal_ref'])), Decimal(str(c['stop']))
        target = Decimal(str(c['target'])) if c.get('target') is not None else None
        # With fixed target and stop, this is the highest entry consistent with >=3.
        max_entry = (target + 3 * stop) / 4 if target is not None else None
        rows.append(dict(candidate_id=c['candidate_id'],symbol=c['symbol'],signal_date=c['signal_date'],
            l1=ev['l1_price'],l2=ev['l2_price'],signal_close=float(ref),target=c.get('target'),
            signal_accepted=c['signal_accepted'],reject_reason=c['signal_reject_reason'],
            direction_confirmed=ev['dual_ma_bull_state'],signal_reward_risk=c['signal_rr'],
            signal_distance_to_invalidation_pct=float(ref/stop-1),
            maximum_entry_for_original_three_to_one=float(max_entry) if max_entry is not None else None,
            close_above_maximum_pct=float(ref/max_entry-1) if max_entry is not None and max_entry>0 else None,
            target_known_date=c.get('target_confirmed_at'),
            interpretation='Known geometry only; maximum entry is arithmetic, not an executable order or tested pullback strategy.'))
    out=ROOT/'controller-entry-diagnosis.json'
    assert not out.exists(), 'Preserve prior diagnostic'
    out.write_text(json.dumps(dict(source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),rows=rows),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps([r for r in rows if r['direction_confirmed']],ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
