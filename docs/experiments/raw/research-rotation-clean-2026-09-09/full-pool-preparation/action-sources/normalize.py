from pathlib import Path
import json,urllib.request,hashlib,re
B=Path(__file__).resolve().parent
urls={'512890':'https://www.sse.com.cn/disclosure/fund/announcement/c/new/2021-10-25/512890_20211025_1_lJ5GeyLb.pdf','515050':'https://pdf.dfcfw.com/pdf/H2_AN202605061821993513_1.pdf','515880':'https://stockmc.xueqiu.com/202601/515880_20260128_CJ9L.pdf'}
sources=[]
for s,u in urls.items():
 raw=urllib.request.urlopen(u,timeout=25).read();p=B/f'{s}-official-split.pdf';p.write_bytes(raw);sources.append({'symbol':s,'url':u,'path':str(p),'sha256':hashlib.sha256(raw).hexdigest()})
raw=json.loads((B/'index.json').read_text());events=[];excluded=[]
for r in raw:
 for tab in r.get('tables',[]):
  for row in tab:
   if not str(row.get('年份',''))[:4].isdigit():continue
   if '除息日' in row:
    d=row['除息日'];a={'symbol':r['symbol'],'type':'cash_dividend','record_date':row['权益登记日'],'ex_date':d,'effective_date':d,'pay_date':row['分红发放日'],'cash_per_unit':float(re.search(r'现金([\d.]+)元',row['每10份分红']).group(1))/10,'source_url':r['url'],'source_path':str(B/f"{r['symbol']}.html"),'source_sha256':r['sha256'],'qualification':'secondary table; 510300/512400 additionally qualified in existing official package'}
   else:
    # Ignore secondary split dates here; map official record/effective dates separately.
    excluded.append({'symbol':r['symbol'],'row':row,'reason':'listing conversion or split dates must use official market effective date; explicit mapping below'});continue
   a['event_id']=f"{a['symbol']}-{a['type']}-{d}"
   if '2019-01-01'<=d<='2026-06-30':events.append(a)
   else:excluded.append(a)
for s,ann,rec,eff,ratio in [('512890','2021-10-13','2021-10-21','2021-10-22',2),('515050','2026-05-07','2026-05-12','2026-05-13',3),('515880','2026-01-28','2026-02-02','2026-02-03',3)]:
 src=next(x for x in sources if x['symbol']==s);events.append({'event_id':s+'-split-'+eff,'symbol':s,'type':'split','announcement_date':ann,'record_date':rec,'effective_date':eff,'split_ratio':ratio,'source_url':src['url'],'source_path':src['path'],'source_sha256':src['sha256'],'qualification':'official manager notice'})
src=sources[0];events.append({'event_id':'512890-halt-2021-10-22','symbol':'512890','type':'trading_halt','effective_date':'2021-10-22','halt':{'start_date':'2021-10-22','end_date':'2021-10-22','resume_date':'2021-10-25','blocks_open_buy':True,'blocks_open_sell':True,'close_mark_allowed':False},'source_url':src['url'],'source_path':src['path'],'source_sha256':src['sha256']})
(B/'normalized-actions.json').write_text(json.dumps({'schema_version':1,'events':sorted(events,key=lambda a:(a['effective_date'],a['symbol'])),'excluded':excluded,'official_sources':sources,'limitations':['No continuous official absence-of-other-actions assurance','515300 dividend amounts/dates are from secondary compilation; require additional official validation before adoption','515050/515880 agreement-repurchase suspension is not ordinary secondary-market trading suspension','Listing conversions prior to first actual trading quote excluded']},ensure_ascii=False,indent=2)+'\n')
print('events',len(events),'official PDF',len(sources))
