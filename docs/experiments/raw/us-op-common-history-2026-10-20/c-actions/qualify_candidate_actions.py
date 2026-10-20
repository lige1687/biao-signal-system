#!/usr/bin/env python3
"""Link saved corporate-action rows to annual accounting candidates by exact ticker/date windows.
Source-only qualification. No network, price access, OP, or return calculation.
"""
from __future__ import annotations
import argparse, csv, hashlib, json
from collections import defaultdict
from datetime import date
from pathlib import Path

FOCUS={('A','KEYS'),('VAR','VREX'),('APTV','DLPH'),('BWA','PHIN'),('JCI','ADNT')}

def sha(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()
def read_csv(p):
    with p.open(newline='',encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def parse_dates(r):
    endpoints=json.loads(r['mom_endpoint_dates_json'])
    return date.fromisoformat(endpoints[0]),date.fromisoformat(endpoints[-1]),date.fromisoformat(r['formation_date']),date.fromisoformat(r['target_month_end_date'])
def is_between(d,lo,hi): return lo < d <= hi

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--raw',required=True); ap.add_argument('--output',required=True); ap.add_argument('--candidates',required=True); ap.add_argument('--expected-candidate-sha',required=True); a=ap.parse_args()
    raw=Path(a.raw); out=Path(a.output); cand=Path(a.candidates)
    if out.exists(): raise SystemExit(f'create-only output already exists: {out}')
    if not raw.is_dir() or not cand.is_file(): raise SystemExit('required source path missing')
    candidate_sha=sha(cand)
    if candidate_sha != a.expected_candidate_sha: raise SystemExit(f'candidate SHA mismatch: {candidate_sha}')
    tables=[('spinoff','johnbrick-spinoffs.csv','ex_date'),('corporate_action_override','johnbrick-corporate_action_overrides.csv','date')]
    actions=[]; input_hashes={}
    for kind,name,field in tables:
        p=raw/'sources'/name
        if not p.is_file(): raise SystemExit(f'missing source: {p}')
        input_hashes[name]=sha(p)
        for row_i,r in enumerate(read_csv(p),1):
            if not r.get('ticker') or not r.get(field): continue
            try: d=date.fromisoformat(r[field])
            except ValueError: continue
            actions.append({'kind':kind,'source_file':name,'source_row':row_i,'date_field':field,'event_date':d.isoformat(),'ticker':r['ticker'],'fields':r})
    rescale_path=raw/'sources'/'johnbrick-dividend_rescale.csv'
    if not rescale_path.is_file(): raise SystemExit(f'missing source: {rescale_path}')
    input_hashes[rescale_path.name]=sha(rescale_path)
    rescale=read_csv(rescale_path)
    cand_rows=read_csv(cand)
    if len(cand_rows)!=2181: raise SystemExit(f'candidate row count changed: {len(cand_rows)}')
    # Build indexed exact-ticker action list.
    by_ticker=defaultdict(list)
    for e in actions: by_ticker[e['ticker']].append(e)
    links=[]
    for c in cand_rows:
        m0,m1,form,target=parse_dates(c)
        for e in by_ticker.get(c['ticker'],[]):
            d=date.fromisoformat(e['event_date'])
            in_mom=is_between(d,m0,m1); in_target=is_between(d,form,target)
            if not (in_mom or in_target): continue
            # preserve actual source columns without reshaping or recalculating any values
            links.append({
                'target_month':c['target_month'],'ticker':c['ticker'],'candidate_cik':c['candidate_cik'],'adsh':c['adsh'],
                'mapping_status':c['mapping_status'],'sourcequalified':c['sourcequalified'],'automatic_scoring_eligible_input':c['automatic_scoring_eligible'],
                'mom_first_endpoint':m0.isoformat(),'mom_last_endpoint':m1.isoformat(),'formation_date':form.isoformat(),'target_month_end_date':target.isoformat(),
                'action_source':e['source_file'],'action_kind':e['kind'],'action_source_row':e['source_row'],'action_date_field':e['date_field'],'action_date':e['event_date'],
                'action_fields':e['fields'],'mom_window_match':in_mom,'formation_to_target_window_match':in_target,
                'mom_overlay':'not_yet_qualified' if in_mom else 'no_action_date_match',
                'outcome_overlay':'outcome_pending' if in_target else 'not_implicated_by_action_date',
                'formation_pool_overlay':'retain_candidate; no automatic removal'
            })
    # Monthly counts: distinct candidate rows/tickers and matched source event rows by source/window.
    month_stats=defaultdict(lambda:{'candidate_rows':0,'distinct_candidate_tickers':set(),'sources':defaultdict(lambda:{'mom_candidate_rows':set(),'mom_event_links':0,'target_candidate_rows':set(),'target_event_links':0})})
    for c in cand_rows:
        m0,m1,form,target=parse_dates(c); s=month_stats[c['target_month']]; s['candidate_rows']+=1;s['distinct_candidate_tickers'].add(c['ticker'])
        for e in by_ticker.get(c['ticker'],[]):
            d=date.fromisoformat(e['event_date']); st=s['sources'][e['source_file']]
            if is_between(d,m0,m1): st['mom_candidate_rows'].add(c['ticker']);st['mom_event_links']+=1
            if is_between(d,form,target): st['target_candidate_rows'].add(c['ticker']);st['target_event_links']+=1
    monthly=[]
    for month,s in sorted(month_stats.items()):
        item={'target_month':month,'candidate_rows':s['candidate_rows'],'distinct_candidate_tickers':len(s['distinct_candidate_tickers']),'by_source':{}}
        for source,st in sorted(s['sources'].items()):
            if st['mom_event_links'] or st['target_event_links']:
                item['by_source'][source]={'mom_distinct_tickers':len(st['mom_candidate_rows']),'mom_event_links':st['mom_event_links'],'formation_to_target_distinct_tickers':len(st['target_candidate_rows']),'formation_to_target_event_links':st['target_event_links']}
        monthly.append(item)
    # Historical rescale is a rule row with 'before' cutoff, not an individual ex-date.
    rescale_rule=[]
    for i,r in enumerate(rescale,1):
        ticker=r.get('ticker',''); before=r.get('before','')
        matched=[c for c in cand_rows if c['ticker']==ticker]
        rescale_rule.append({'source_file':rescale_path.name,'source_row':i,'ticker':ticker,'before_cutoff':before,'divide_by':r.get('divide_by'),'note':r.get('note'),'date_semantics':'No per-distribution event date. `before` is a historical dividend-value basis cutoff; do not treat as an ex-date or single event.', 'candidate_month_rows_for_ticker':len(matched),'candidate_months_for_ticker':sorted({c['target_month'] for c in matched}),'window_linkage':'Not assigned to either event-date window because the table has no event date. It describes dividend scaling before the cutoff; it does not say to scale adjusted-close prices.'})
    focus_hits=[]
    for x in links:
        key=(x['ticker'],x['action_fields'].get('spinco',''))
        if key in FOCUS: focus_hits.append(x)
    out.mkdir(parents=True,exist_ok=False)
    def dumpj(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
    with (out/'action-window-links.jsonl').open('x',encoding='utf-8') as f:
        for x in links: f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    with (out/'monthly-impact-counts.jsonl').open('x',encoding='utf-8') as f:
        for x in monthly: f.write(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n')
    dumpj(out/'historical-rescale-rule.json',rescale_rule)
    dumpj(out/'focus-case-links.json',focus_hits)
    summary={
      'schema':'candidate-action-qualification-summary/1','candidate_rows':len(cand_rows),'candidate_sha256':candidate_sha,
      'action_inputs':input_hashes,'action_input_rows':{name:len(read_csv(raw/'sources'/name)) for name in input_hashes},
      'matched_action_window_links':len(links),'candidate_months_with_any_match':sum(bool(any(s['by_source'].values())) for s in monthly),
      'monthly_rows':len(monthly),'historical_rescale_rules':len(rescale_rule),'focus_matches':len(focus_hits),
      'qualifying_policy':'Every exact-ticker event row in a momentum window is marked not_yet_qualified pending independent source confirmation; every event row in formation-to-target window is outcome_pending. Formation candidate remains in the pool. This is an overlay for root review, not a final eligibility ruling.',
      'limits':['Only exact ticker joins; no identity or successor mapping inferred.','No network, price reads, accounting values, OP values, momentum values, or returns computed.','Manual records are retained as source rows, not independently verified corporate-action truth.','Rescale row is a historical dividend basis rule, not a dated corporate action.']}
    dumpj(out/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
