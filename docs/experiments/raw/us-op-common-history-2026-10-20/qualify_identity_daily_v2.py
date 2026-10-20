#!/usr/bin/env python3
"""Daily price-input coverage and unresolved monthly CIK candidates; no effects."""
import argparse,csv,datetime as dt,hashlib,json,math,os,re
from collections import defaultdict,deque
from pathlib import Path


def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def norm(s): return re.sub(r'[.-]','',(s or '').strip().upper())
def date_value(v):
 if isinstance(v,dt.datetime): return v.date()
 if isinstance(v,dt.date): return v
 if isinstance(v,str): return dt.date.fromisoformat(v.strip())
 raise TypeError(f'unsupported date type: {type(v).__name__}')
def parse_bound(v):
 v=(v or '').strip(); star=v.endswith('*')
 if star: v=v[:-1]
 try: return (dt.date.fromisoformat(v) if v else None),star
 except ValueError: return None,star
def temporal_eligible(rec,day):
 d=date_value(day)
 added,_=parse_bound(rec.get('date_added','')); removed,_=parse_bound(rec.get('date_removed','')); created,_=parse_bound(rec.get('created_at',''))
 return (added is None or added<=d) and (removed is None or d<removed) and (created is None or created<=d)
def candidate_aliases(symbol):
 s=(symbol or '').strip().upper(); out={(s,'exact')}
 canonical=norm(s)
 if canonical!=s: out.add((canonical,'normalized_dot_hyphen'))
 m=re.fullmatch(r'(.+)-(\d{6})',s)
 if m:
  stem=m.group(1); out.add((stem,'legacy_month_suffix_candidate'))
  if norm(stem)!=stem: out.add((norm(stem),'legacy_month_suffix_candidate_normalized'))
 return out
def rename_reachable(start,edges):
 graph=defaultdict(set)
 for a,b in edges: graph[a.upper()].add(b.upper()); graph[b.upper()].add(a.upper())
 seen={start.upper()}; q=deque([start.upper()])
 while q:
  for x in graph[q.popleft()]:
   if x not in seen: seen.add(x); q.append(x)
 return seen-{start.upper()}
def status_for(ciks,modes):
 if not ciks:return 'no_candidate'
 if len(ciks)>1:return 'ambiguous'
 return 'exact' if 'exact' in modes else 'rename'
def finite_positive(v):
 try:return v is not None and math.isfinite(float(v)) and float(v)>0
 except (TypeError,ValueError):return False

def load_job(job_path, output_override=None, verify_hashes=True):
 job_path=Path(job_path); job=json.loads(job_path.read_text())
 for b in job['input_files']:
  p=Path(b['path']); assert p.exists(),f'missing input {p}'
  if verify_hashes: assert sha(p)==b['sha256'],f'input hash mismatch {p}'
 out=Path(output_override or job['output'])
 assert not out.exists(),f'output already exists: {out}'
 return job,out

def build_monthly_candidates(monthly_path,law,edges):
 idx=defaultdict(list)
 for rec in law: idx[norm(rec['symbol'])].append(rec)
 rows=[]; rename_cache={}
 with open(monthly_path,newline='',encoding='utf-8') as f:
  for m in csv.DictReader(f):
   ticker=m['ticker']; day=date_value(m['quote_date']); found={}
   aliases=candidate_aliases(ticker)
   def add(rec,mode):
    key=id(rec)
    if key not in found:found[key]={'record':rec,'modes':set()}
    found[key]['modes'].add(mode)
   for alias,mode in aliases:
    for rec in idx.get(norm(alias),[]):
     if temporal_eligible(rec,day): add(rec,mode)
   if ticker not in rename_cache:rename_cache[ticker]=rename_reachable(ticker,edges)
   for node in sorted(rename_cache[ticker]):
    for rec in idx.get(norm(node),[]):
     if temporal_eligible(rec,day):add(rec,'rename')
   pairs=[(x['record'],x['modes']) for x in found.values()]
   ciks={r['cik'] for r,_ in pairs if r.get('cik')}; modes=set().union(*(ms for _,ms in pairs)) if pairs else set()
   evidence=[{'symbol':r['symbol'],'cik':r['cik'],'name':r['name'],'sector':r['sector'],'date_added':r['date_added'],'date_removed':r['date_removed'],'created_at':r['created_at'],'match_modes':sorted(ms)} for r,ms in pairs]
   rows.append({'month':m['month'],'quote_date':m['quote_date'],'ticker':ticker,'interval_id':m.get('interval_id',''),'interval_start':m.get('interval_start',''),'interval_end_exclusive':m.get('interval_end_exclusive',''),'status':status_for(ciks,modes),'candidate_record_count':len(pairs),'candidate_ciks':'|'.join(sorted(ciks)),'candidate_symbols':'|'.join(sorted({r['symbol'] for r,_ in pairs})),'candidate_evidence_json':json.dumps(evidence,ensure_ascii=False,separators=(',',':'))})
 return rows

def run_job(job_path,output_override=None,verify_hashes=True):
 import pyarrow.parquet as pq
 job,out=load_job(job_path,output_override,verify_hashes)
 base=Path(job['input_files'][0]['path']).parent
 period_start,period_end=map(dt.date.fromisoformat,job['period'])
 intervals=pq.read_table(base/'membership_intervals.parquet').to_pylist()
 tickers=set();period_tickers=set()
 for row in intervals:
  t=row['ticker']; tickers.add(t)
  s=row['start'].date() if row['start'] else dt.date.min; e=row['end'].date() if row['end'] else dt.date.max
  if s<=period_end and e>period_start:period_tickers.add(t)
  
 prices=pq.read_table(base/'prices.parquet',columns=['date','ticker','close','volume','adj_close','source']).to_pandas()
 prices['day']=prices['date'].dt.date
 prices=prices[(prices.day>=period_start)&(prices.day<=period_end)]
 pmap=defaultdict(list)
 for r in prices.itertuples(index=False):pmap[(r.day,str(r.ticker))].append(r)
 spy_days=sorted({d for (d,t) in pmap if t=='SPY'})
 if not spy_days:raise ValueError('no SPY price dates in requested period')
 # Map interval boundaries to observed SPY sessions so intervals beginning between
 # sessions are active on the next observed session; end remains exclusive.
 import bisect
 starts=defaultdict(list); ends=defaultdict(list)
 for row in intervals:
  t=row['ticker']; s=row['start'].date() if row['start'] else dt.date.min; e=row['end'].date() if row['end'] else dt.date.max
  if e<=spy_days[0] or s>spy_days[-1]:continue
  si=bisect.bisect_left(spy_days,max(s,period_start))
  if si<len(spy_days):starts[spy_days[si]].append(t)
  ei=bisect.bisect_left(spy_days,e)
  if ei<len(spy_days):ends[spy_days[ei]].append(t)
 no_trade=defaultdict(list)
 with open(base/'no_trade_days.csv',newline='',encoding='utf-8') as f:
  for r in csv.DictReader(f):
   d=r.get('date','')
   if period_start.isoformat()<=d<=period_end.isoformat(): no_trade[(d,r['ticker'])].append(r.get('kind',''))
 active=defaultdict(int); daily=[]; issues=[]; year_totals=defaultdict(lambda:defaultdict(int))
 for day in spy_days:
  for t in ends.get(day,[]):
   active[t]-=1
   if active[t]<=0:active.pop(t,None)
  for t in starts.get(day,[]):active[t]+=1
  miss=dupprice=dupmember=close_bad=adj_bad=vol_missing=vol_nonfinite=vol_nonpositive=notradekeys=good=0
  for ticker,multiplicity in sorted(active.items()):
   rows=pmap.get((day,ticker),[]); flags=[]
   if multiplicity>1:dupmember+=1;flags.append('duplicate_active_membership_intervals')
   if not rows:miss+=1;flags.append('missing_exact_ticker_price_row')
   if len(rows)>1:dupprice+=1;flags.append('duplicate_price_rows')
   nt=no_trade.get((day.isoformat(),ticker),[])
   if nt:notradekeys+=1;flags.append('no_trade_day_record')
   if rows:
    if any(not finite_positive(x.close) for x in rows):close_bad+=1;flags.append('close_missing_nonfinite_or_nonpositive')
    if any(not finite_positive(x.adj_close) for x in rows):adj_bad+=1;flags.append('adj_close_missing_nonfinite_or_nonpositive')
    if any(x.volume is None for x in rows):vol_missing+=1;flags.append('volume_missing')
    if any(x.volume is not None and not math.isfinite(float(x.volume)) for x in rows):vol_nonfinite+=1;flags.append('volume_nonfinite')
    if any(finite_positive(x.volume)==False and x.volume is not None and math.isfinite(float(x.volume)) for x in rows):vol_nonpositive+=1;flags.append('volume_nonpositive')
   eligible=(len(rows)==1 and multiplicity==1 and not nt and finite_positive(rows[0].close) and finite_positive(rows[0].adj_close) and finite_positive(rows[0].volume))
   if eligible:good+=1
   if flags: issues.append({'date':day.isoformat(),'ticker':ticker,'active_interval_count':multiplicity,'price_row_count':len(rows),'no_trade_kinds':'|'.join(nt),'issues':'|'.join(flags),'price_rows_json':json.dumps([{'close':x.close,'adj_close':x.adj_close,'volume':x.volume,'source':x.source} for x in rows],allow_nan=True,separators=(',',':'))})
  item={'date':day.isoformat(),'active_member_rows':sum(active.values()),'unique_active_tickers':len(active),'eligible_exact_price_rows':good,'missing_exact_price_tickers':miss,'duplicate_price_tickers':dupprice,'duplicate_active_membership_tickers':dupmember,'invalid_close_tickers':close_bad,'invalid_adj_close_tickers':adj_bad,'volume_missing_tickers':vol_missing,'volume_nonfinite_tickers':vol_nonfinite,'volume_nonpositive_tickers':vol_nonpositive,'no_trade_record_tickers':notradekeys}
  daily.append(item)
  for k,v in item.items():
   if k!='date':year_totals[str(day.year)][k]+=v
 law=[]
 with open(base/'lawcal-data-components_history.csv',newline='',encoding='utf-8') as f:
  for r in csv.DictReader(f): law.append(r)
 edges=[]
 with open(base/'renames.csv',newline='',encoding='utf-8') as f:
  for r in csv.DictReader(f):edges.append((r['old'],r['new']))
 monthly_path=next(Path(x['path']) for x in job['input_files'] if Path(x['path']).name=='monthly-members.csv')
 monthly_rows=build_monthly_candidates(monthly_path,law,edges)
 # STI label and current ticker kept separate; observations are not payout/identity proof.
 sti_intervals=[r for r in intervals if r['ticker']=='STI-201912']
 sti_detail=[]
 if sti_intervals:
  e=sti_intervals[0]['end'].date() if sti_intervals[0]['end'] else period_end
  for ticker in ['STI-201912','STI']:
   q=prices[prices.ticker==ticker].sort_values('day')
   before=q[q.day<e].tail(5); after=q[q.day>=e].head(5)
   def vals(df):return [{'date':str(x.day),'close':x.close,'adj_close':x.adj_close,'volume':x.volume,'source':x.source} for x in df.itertuples(index=False)]
   sti_detail.append({'ticker':ticker,'before':vals(before),'after':vals(after)})
 focus={'GOOG','GOOGL','IR','TT','AGN','ACT','CB','ACE','STI'}
 law_focus=[r for r in law if r['symbol'].upper() in focus or str(r['cik']).lstrip('0')=='1652044']
 out.mkdir(parents=True,exist_ok=False)
 def write_csv(name,rows):
  p=out/name
  if not rows:p.write_text('',encoding='utf-8');return
  with p.open('w',newline='',encoding='utf-8') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 write_csv('daily-coverage.csv',daily);write_csv('daily-issues.csv',issues);write_csv('monthly-identity-candidates.csv',monthly_rows)
 (out/'identity-examples.json').write_text(json.dumps({'lawcal_focus_records':law_focus,'monthly_focus_rows':[r for r in monthly_rows if r['ticker'].split('-')[0].upper() in focus or '1652044' in r['candidate_ciks']],'sti_201912_price_observations':sti_detail,'identity_status_note':'all links are candidates; no historical identity is confirmed'},ensure_ascii=False,indent=2),encoding='utf-8')
 counts=defaultdict(int)
 for r in monthly_rows:counts[r['status']]+=1
 summary={'identity_status':'candidate_only_not_validated','period':[str(period_start),str(period_end)],'spy_trading_days':len(spy_days),'monthly_member_rows':len(monthly_rows),'monthly_identity_status_counts':dict(counts),'period_tickers':len(period_tickers),'source_unique_tickers_all_history':len(tickers),'source_interval_rows':len(intervals),'daily_member_days':sum(r['active_member_rows'] for r in daily),'daily_unique_ticker_days':sum(r['unique_active_tickers'] for r in daily),'eligible_exact_price_rows':sum(r['eligible_exact_price_rows'] for r in daily),'daily_issue_rows':len(issues),'daily_year_totals':year_totals,'lawcal_records':len(law),'network_requests':0,'returns_or_op_calculated':False}
 (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
 files=[]
 for p in sorted(out.iterdir()):
  if p.is_file():files.append({'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size,'rows':sum(1 for _ in p.open(encoding='utf-8'))-1 if p.suffix=='.csv' and p.stat().st_size else None})
 manifest={'job_sha256':sha(job_path),'input_hashes':{Path(x['path']).name:sha(x['path']) for x in job['input_files']},'files':files,'summary':summary}
 (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 return out,manifest

def run_contract(contract_path):
 cp=Path(contract_path).resolve();c=json.loads(cp.read_text());job_path=Path(c['job_path']).resolve()
 assert job_path.exists() and str(job_path) in {str(Path(p).resolve()) for p in c['read_only_paths']},'job path not declared read-only'
 job=json.loads(job_path.read_text());storage=json.loads(Path(c['read_only_paths'][1]).read_text())
 assert job['output']==c['write_paths'][-1]
 assert job['external_device']==storage['external_device']
 assert os.stat(storage['external_mount']).st_dev==storage['external_device']
 assert not Path(job['output']).exists(),'bound output already exists; refusing overwrite'
 return run_job(job_path)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--contract',required=True);a=ap.parse_args();out,m=run_contract(a.contract);print(json.dumps({'output':str(out),'manifest_sha256':sha(out/'manifest.json'),'summary':m['summary']},ensure_ascii=False))
