import json
from lei_signal.fundamentals.valuation_context import read_concentration

def test_concentration_uses_qualified_fallback_and_preserves_gaps(tmp_path):
    base=read_concentration(tmp_path)
    assert len(base['points'])==129
    assert sum(p['value'] is None for p in base['points'])==45
    base['pendingMonth']='2026-10'
    (tmp_path/'turnover_concentration_live.json').write_text(json.dumps(base))
    current=read_concentration(tmp_path)
    assert current['asOf']=='2026-09-30' and current['pendingMonth']=='2026-10'
    assert current['points']==base['points']
