from pathlib import Path
import csv,importlib.util,json,sys
H=Path(__file__).resolve().parent;A=H/'attempt-e2'
s=importlib.util.spec_from_file_location('analysis_base',H/'analyze.py');b=importlib.util.module_from_spec(s);sys.modules[s.name]=b;s.loader.exec_module(b)
def main():
 profiles=[];annual=[];periods=[]
 for m in b.read(A/'summary.json'):
  aid=m['account_id'];folder=A/'accounts'/aid;p,a=b.invested(folder,{k:m[k] for k in ('account_id','symbol','group','exit','fee')});profiles.append(p);annual+=a
  rows=list(csv.DictReader((folder/'daily.csv').open()))
  for label,lo,hi in [('2015-2019','2015-01-01','2019-12-31'),('2020-2026H1','2020-01-01','2026-06-30')]:
   g=[r for r in rows if lo<=r['date']<=hi];before=100000. if lo.startswith('2015') else float([r for r in rows if r['date']<lo][-1]['equity']);periods.append({'account_id':aid,'period':label,'return':float(g[-1]['equity'])/before-1})
 b.save(H/'e2-invested-results.json',profiles);b.save(H/'e2-invested-annual.json',annual);b.save(H/'e2-fixed-periods.json',periods)
if __name__=='__main__':main()
