import csv,hashlib,importlib.util,json,math,tempfile
from pathlib import Path
import pyarrow as pa, pyarrow.parquet as pq
P=Path(__file__).with_name('qualify_identity_daily_v2.py')
spec=importlib.util.spec_from_file_location('daily_v2',P);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def putcsv(path,fields,rows):
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def sh(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def test_end_to_end():
 with tempfile.TemporaryDirectory() as td:
  root=Path(td); src=root/'sources';src.mkdir();result=root/'result';result.mkdir()
  intervals=[
   {'ticker':'SPY','start':'2010-01-01','end':None},
   {'ticker':'GOOD','start':'2019-12-30','end':None},
   {'ticker':'NAN','start':'2019-12-30','end':None},
   {'ticker':'DUP','start':'2019-12-30','end':None},
   {'ticker':'DUP','start':'2019-12-30','end':None},
   {'ticker':'OUT','start':'2014-01-01','end':'2014-12-31'},
  ]
  pq.write_table(pa.Table.from_pylist([{'ticker':x['ticker'],'start':__import__('datetime').datetime.fromisoformat(x['start']),'end':__import__('datetime').datetime.fromisoformat(x['end']) if x['end'] else None} for x in intervals]),src/'membership_intervals.parquet')
  prices=[]
  def pr(day,ticker,close=10,adj=10,vol=100):return {'date':__import__('datetime').datetime.fromisoformat(day),'ticker':ticker,'close':close,'volume':vol,'adj_close':adj,'source':'synthetic'}
  for day in ['2019-12-31','2020-01-02']:
   prices.append(pr(day,'SPY'))
  prices += [pr('2019-12-31','GOOD'),pr('2020-01-02','GOOD'),pr('2019-12-31','NAN',float('nan')),pr('2020-01-02','NAN'),pr('2019-12-31','DUP'),pr('2019-12-31','DUP'),pr('2020-01-02','DUP')]
  pq.write_table(pa.Table.from_pylist(prices),src/'prices.parquet')
  putcsv(src/'lawcal-data-components_history.csv',['symbol','cik','name','sector','date_added','date_removed','created_at'],[
   {'symbol':'GOOD','cik':'0000000001','name':'Good One','sector':'x','date_added':'2010-01-01*','date_removed':'','created_at':'2010-01-01'},
   {'symbol':'GOOD','cik':'0000000002','name':'Good Two','sector':'x','date_added':'2010-01-01','date_removed':'','created_at':'2010-01-01'},
   {'symbol':'STI','cik':'0000000003','name':'Legacy STI','sector':'x','date_added':'2010-01-01','date_removed':'','created_at':'2010-01-01'},
  ])
  (src/'lawcal-bin-update.py').write_text('# fixture only\n')
  putcsv(src/'renames.csv',['old','new'],[{'old':'OLD','new':'GOOD'},{'old':'STI','new':'STI.A'}])
  putcsv(src/'no_trade_days.csv',['ticker','date','kind'],[])
  putcsv(result/'monthly-members.csv',['month','quote_date','ticker','interval_id','interval_start','interval_end_exclusive'],[
   {'month':'2020-01','quote_date':'2020-01-02','ticker':'GOOD','interval_id':'1','interval_start':'2019-12-30','interval_end_exclusive':''},
   {'month':'2020-01','quote_date':'2020-01-02','ticker':'STI-201912','interval_id':'2','interval_start':'2019-12-30','interval_end_exclusive':'2020-01-01'},
  ])
  files=[src/'lawcal-data-components_history.csv',src/'lawcal-bin-update.py',src/'membership_intervals.parquet',src/'prices.parquet',src/'renames.csv',src/'no_trade_days.csv',result/'monthly-members.csv']
  job={'input_files':[{'path':str(x),'sha256':sh(x)} for x in files],'output':str(root/'out'),'external_device':0,'period':['2019-12-30','2020-01-03']}
  jp=root/'job.json';jp.write_text(json.dumps(job))
  out,manifest=m.run_job(jp)
  daily=list(csv.DictReader((out/'daily-coverage.csv').open()))
  issues=list(csv.DictReader((out/'daily-issues.csv').open()))
  candidates=list(csv.DictReader((out/'monthly-identity-candidates.csv').open()))
  assert len(daily)==2 and daily[0]['date']=='2019-12-31' and daily[1]['date']=='2020-01-02'
  assert all(x['ticker']!='OUT' for x in issues)
  assert sum(int(x['invalid_close_tickers']) for x in daily)==1
  assert any(x['ticker']=='NAN' and 'close_missing_nonfinite_or_nonpositive' in x['issues'] for x in issues)
  assert any(x['ticker']=='DUP' and 'duplicate_price_rows' in x['issues'] for x in issues)
  assert any(x['ticker']=='DUP' and 'duplicate_active_membership_intervals' in x['issues'] for x in issues)
  assert len(candidates)==2 and candidates[0]['status']=='ambiguous'
  assert candidates[1]['ticker']=='STI-201912' and candidates[1]['status']=='rename'
  try:m.run_job(jp)
  except AssertionError as e:assert 'already exists' in str(e)
  else:raise AssertionError('create-only output did not reject overwrite')

def run():
 assert m.date_value('2020-01-01')==m.date_value(__import__('datetime').date(2020,1,1))
 assert not m.finite_positive(float('nan')) and not m.finite_positive(float('inf')) and not m.finite_positive(0)
 assert m.finite_positive(1.25)
 assert m.candidate_aliases('STI-201912') >= {('STI','legacy_month_suffix_candidate')}
 assert m.temporal_eligible({'date_added':'2010-01-01*','date_removed':'2020-01-01*','created_at':'2012-01-01'},__import__('datetime').date(2015,1,1))
 assert not m.temporal_eligible({'date_added':'2010-01-01','date_removed':'2015-01-01','created_at':'2010-01-01'},'2015-01-01')
 assert m.rename_reachable('A',[('A','B'),('B','C')])=={'B','C'}
 assert m.status_for({'1','2'},{'exact'})=='ambiguous' and m.status_for(set(),set())=='no_candidate'
 test_end_to_end()
 print('PASS: helper checks plus end-to-end synthetic fixture (daily coverage, NaN, duplicate, date/string, period filtering, monthly candidate conflict, STI suffix, create-only)')
if __name__=='__main__':run()
