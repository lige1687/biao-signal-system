#!/usr/bin/env python3
"""Daily historical membership/quote coverage and unresolved CIK candidates; no effects."""
import argparse, csv, datetime as dt, hashlib, json, re
from collections import defaultdict, deque
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def norm(s):
    return re.sub(r'[.-]', '', (s or '').strip().upper())

def candidate_aliases(symbol):
    s=(symbol or '').strip().upper()
    out={(s,'exact')}
    out.add((norm(s),'exact' if norm(s)==s else 'normalized_dot_hyphen'))
    m=re.fullmatch(r'(.+)-(\d{6})',s)
    if m:
        out.add((m.group(1),'legacy_month_suffix_candidate'))
        out.add((norm(m.group(1)),'legacy_month_suffix_candidate_normalized'))
    return out

def temporal_eligible(rec, day):
    d=dt.date.fromisoformat(day)
    def parse(v):
        return dt.date.fromisoformat(v.rstrip('*')) if v else None
    added, removed, created = parse(rec.get('date_added','')),parse(rec.get('date_removed','')),parse(rec.get('created_at',''))
    return (added is None or added<=d) and (removed is None or d<removed) and (created is None or created<=d)

def rename_reachable(start, edges):
    # Return every endpoint reachable in either direction, retaining no preferred path.
    graph=defaultdict(set)
    for a,b in edges: graph[a.upper()].add(b.upper()); graph[b.upper()].add(a.upper())
    seen={start.upper()}; q=deque([start.upper()])
    while q:
        for nxt in graph[q.popleft()]:
            if nxt not in seen: seen.add(nxt); q.append(nxt)
    return seen-{start.upper()}

def status_for(ciks, modes):
    if not ciks: return 'no_candidate'
    if len(ciks)>1: return 'ambiguous'
    return 'exact' if 'exact' in modes else 'rename'

def validate_contract(contract, raw):
    job=json.loads((raw/'identity-daily-job.json').read_text())
    storage=json.loads((raw/'storage-plan.json').read_text())
    assert job['output']==str(Path(contract['write_paths'][-1]))
    assert storage['external_device']==job['external_device']
    assert not Path(job['output']).exists(), 'output already exists; refusing overwrite'
    for b in job['input_files']:
        p=Path(b['path']); assert p.exists(),f'missing {p}'
        assert sha(p)==b['sha256'],f'input hash mismatch {p}'
    return job,storage

def run(contract_path):
    import pyarrow.parquet as pq
    cp=Path(contract_path).resolve(); raw=cp.parent
    c=json.loads(cp.read_text()); job,storage=validate_contract(c,raw)
    # ensure exact mounted external identity
    import os
    assert os.stat(Path(storage['external_mount'])).st_dev==storage['external_device']
    base=Path(job['input_files'][0]['path']).parent
    out=Path(job['output']); out.mkdir(parents=True,exist_ok=False)
    lo,hi=map(dt.date.fromisoformat,job['period'])
    tab=pq.read_table(base/'membership_intervals.parquet').to_pylist()
    intervals=[]
    for row in tab:
        s=row['start'].date() if row['start'] else dt.date.min
        e=row['end'].date() if row['end'] else dt.date.max
        intervals.append((row['ticker'],s,e))
    tickers=sorted({x[0] for x in intervals})
    prices=pq.read_table(base/'prices.parquet',columns=['date','ticker','close','volume','adj_close','source']).to_pandas()
    prices['day']=prices['date'].dt.date
    prices=prices[(prices.day>=lo)&(prices.day<=hi)]
    # Keep exact ticker/date identity; duplicates are retained and reported.
    pmap=defaultdict(list)
    for r in prices.itertuples(index=False): pmap[(r.day,str(r.ticker))].append(r)
    spy_days=sorted({d for (d,t) in pmap if t=='SPY'})
    spy_days=[d for d in spy_days if lo<=d<=hi]
    if not spy_days: raise ValueError('no SPY observed dates in requested period')
    no_trade=defaultdict(list)
    with open(base/'no_trade_days.csv',newline='') as f:
        for r in csv.DictReader(f): no_trade[(r['date'],r['ticker'])].append(r.get('kind',''))
    daily_rows=[]; issue_rows=[]; yearly=defaultdict(lambda:defaultdict(int))
    for day in spy_days:
        active=sorted(t for t,s,e in intervals if s<=day<e)
        # Preserve duplicate interval ticker rows in membership key accounting.
        counts=defaultdict(int)
        for t in active: counts[t]+=1
        npos=nmiss=ndup=nvolmiss=nvolzero=nnote=0
        for ticker,multiplicity in sorted(counts.items()):
            rows=pmap.get((day,ticker),[])
            flags=[]
            if multiplicity>1: flags.append('duplicate_active_membership_interval')
            if not rows: flags.append('missing_exact_ticker_quote')
            else:
                if len(rows)>1: flags.append('duplicate_price_rows')
                if any(x.volume is None for x in rows): flags.append('volume_missing')
                if any(x.volume == 0 for x in rows): flags.append('volume_zero')
                if any(x.close is None for x in rows): flags.append('close_missing')
            nt=no_trade.get((day.isoformat(),ticker),[])
            if nt: flags.append('no_trade_day_record')
            if rows and len(rows)==1 and rows[0].close is not None and rows[0].close>0 and rows[0].volume is not None and rows[0].volume>0 and not nt: npos+=1
            if not rows: nmiss+=1
            if len(rows)>1: ndup+=1
            if rows and any(x.volume is None for x in rows): nvolmiss+=1
            if rows and any(x.volume==0 for x in rows): nvolzero+=1
            if nt: nnote+=1
            if flags:
                issue_rows.append({'date':day.isoformat(),'ticker':ticker,'active_interval_count':multiplicity,'price_row_count':len(rows),'no_trade_kinds':'|'.join(nt),'issues':'|'.join(flags),'quote_rows_json':json.dumps([{'close':x.close,'volume':x.volume,'adj_close':x.adj_close,'source':x.source} for x in rows],ensure_ascii=False)})
        item={'date':day.isoformat(),'active_member_rows':len(active),'unique_active_tickers':len(counts),'positive_exact_quotes':npos,'missing_exact_quote_tickers':nmiss,'duplicate_price_tickers':ndup,'volume_missing_tickers':nvolmiss,'volume_zero_tickers':nvolzero,'no_trade_record_tickers':nnote}
        daily_rows.append(item)
        y=str(day.year)
        for k,v in item.items():
            if k!='date': yearly[y][k]+=v
    # CIK records and evidence, preserving original date strings including *.
    law=[]
    with open(base/'lawcal-data-components_history.csv',newline='') as f:
        for r in csv.DictReader(f):
            r['_symbol_norm']=norm(r.get('symbol',''))
            r['_date_added_star']=r.get('date_added','').endswith('*')
            r['_date_removed_star']=r.get('date_removed','').endswith('*')
            law.append(r)
    exact_index=defaultdict(list)
    for r in law: exact_index[r['_symbol_norm']].append(r)
    edges=[]
    with open(base/'renames.csv',newline='') as f:
        for r in csv.DictReader(f): edges.append((r['old'],r['new']))
    identity=[]
    for ticker in tickers:
        aliases=candidate_aliases(ticker)
        rename_nodes=rename_reachable(ticker,edges)
        matches=[]; observed_dates=[d for d in spy_days if any(t==ticker and s<=d<e for t,s,e in intervals)]
        sample_dates=[d.isoformat() for d in observed_dates[:1]+observed_dates[-1:]]
        for alias,mode in aliases:
            for rec in exact_index.get(norm(alias),[]):
                eligible=[d.isoformat() for d in observed_dates if temporal_eligible(rec,d)]
                if eligible: matches.append((rec,mode,eligible))
        for node in sorted(rename_nodes):
            for rec in exact_index.get(norm(node),[]):
                eligible=[d.isoformat() for d in observed_dates if temporal_eligible(rec,d)]
                if eligible: matches.append((rec,'rename',eligible))
        # Do not collapse records; candidate CIK uniqueness is only used for status.
        ciks={m[0].get('cik','') for m in matches if m[0].get('cik','')}
        modes={m[1] for m in matches}
        st=status_for(ciks,modes)
        identity.append({'membership_ticker':ticker,'status':st,'candidate_rows':len(matches),'candidate_ciks':'|'.join(sorted(ciks)),'candidate_symbols':'|'.join(sorted({m[0]['symbol'] for m in matches})),'candidate_evidence_json':json.dumps([{'symbol':r['symbol'],'cik':r['cik'],'name':r['name'],'sector':r['sector'],'date_added':r['date_added'],'date_removed':r['date_removed'],'created_at':r['created_at'],'date_added_star':r['_date_added_star'],'date_removed_star':r['_date_removed_star'],'match_mode':mode,'eligible_membership_dates':dates[:5]} for r,mode,dates in matches],ensure_ascii=False,separators=(',',':'))})
    # Case-focused records, retaining all lawcal rows for requested symbols/CIKs plus candidate output.
    focus_symbols={'GOOG','GOOGL','IR','TT','AGN','ACT','CB','ACE','STI'}
    focus=[r for r in law if r['symbol'].upper() in focus_symbols or r['cik']=='1652044']
    # STI legacy tagged ticker: exact rows around its membership interval end, up to five either side.
    sti=[(t,s,e) for t,s,e in intervals if t=='STI-201912']
    sti_examples=[]
    if sti:
        _,s,e=sti[0]; end=e if e!=dt.date.max else max(spy_days)
        near=prices[(prices.ticker=='STI') & (prices.day<=end+dt.timedelta(days=30))].sort_values('day')
        before=near[near.day<end].tail(5); after=near[near.day>=end].head(5)
        sti_examples={'interval_start':str(s),'interval_end_exclusive':str(e),'price_ticker_used':'STI','before':before[['day','close','volume','adj_close','source']].assign(day=lambda x:x.day.astype(str)).to_dict('records'),'after':after[['day','close','volume','adj_close','source']].assign(day=lambda x:x.day.astype(str)).to_dict('records'),'interpretation':'price observations only; no payout or identity conclusion'}
    def write_csv(name,rows):
        p=out/name
        if rows:
            with p.open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        else: p.write_text('',encoding='utf-8')
    write_csv('daily-coverage.csv',daily_rows); write_csv('daily-issues.csv',issue_rows); write_csv('identity-candidates.csv',identity)
    examples={'required_symbols':{s:[r for r in focus if r['symbol'].upper()==s] for s in sorted(focus_symbols)},'cik_1652044':[r for r in focus if r['cik']=='1652044'],'sti_201912':sti_examples,'identity_status_note':'candidate-only; no historical identity is confirmed'}
    (out/'identity-examples.json').write_text(json.dumps(examples,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={'identity_status':'candidate_only_not_validated','period':[str(lo),str(hi)],'spy_trading_days':len(spy_days),'membership_interval_rows':len(tab),'unique_membership_tickers':len(tickers),'daily_membership_rows':sum(x['active_member_rows'] for x in daily_rows),'daily_unique_ticker_rows':sum(x['unique_active_tickers'] for x in daily_rows),'daily_positive_exact_quotes':sum(x['positive_exact_quotes'] for x in daily_rows),'daily_missing_exact_quote_tickers':sum(x['missing_exact_quote_tickers'] for x in daily_rows),'daily_duplicate_price_ticker_days':sum(x['duplicate_price_tickers'] for x in daily_rows),'daily_no_trade_record_ticker_days':sum(x['no_trade_record_tickers'] for x in daily_rows),'yearly':yearly,'identity_status_counts':{k:sum(1 for x in identity if x['status']==k) for k in ['exact','rename','ambiguous','no_candidate']},'lawcal_records':len(law),'lawcal_focus_records':len(focus),'network_requests':0,'returns_or_op_calculated':False,'outputs':{}}
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    files=[]
    for p in sorted(out.iterdir()):
        if p.is_file(): files.append({'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'rows':sum(1 for _ in p.open(encoding='utf-8'))-1 if p.suffix=='.csv' and p.stat().st_size else None})
    manifest={'contract_sha256':sha(cp),'job_sha256':sha(raw/'identity-daily-job.json'),'storage_plan_sha256':sha(raw/'storage-plan.json'),'input_hashes':{Path(b['path']).name:sha(b['path']) for b in job['input_files']},'files':files,'summary':summary}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return out,manifest

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--contract',required=True); a=ap.parse_args(); out,m=run(a.contract); print(json.dumps({'output':str(out),'manifest_sha256':sha(out/'manifest.json'),'summary':m['summary']},ensure_ascii=False))
