from pathlib import Path
import pandas as pd,json
B=Path(__file__).resolve().parents[1];X=B/'execution';O=B/'review'
d=pd.read_csv(X/'reentry_diagnostics.csv');s=pd.read_csv(X/'signals.csv'); fails=[]; summary={}
for aid,g in d.groupby('account_id'):
 x={'reentries':len(g),'mature5':int(g.mature5.sum()),'stop5':int(g[g.mature5].stop_again_within5.sum()),'mature20':int(g.mature20.sum()),'stop20':int(g[g.mature20].stop_again_within20.sum())};summary[aid]=x
 if x != {'reentries':49,'mature5':36,'stop5':23,'mature20':26,'stop20':26}:fails.append({'type':'diagnostic_counts','account':aid,'actual':x})
 for r in g[g.end_reason=='monthly_reset'].itertuples():
  nxt=s[(s.account_id==aid)&(s.eligible_date>r.reentry_date)&(s.trend_states!='daily_below_sma200')].eligible_date.min()
  if r.boundary_date!=nxt:fails.append({'type':'monthly_boundary','account':aid,'reentry':r.reentry_date,'boundary':r.boundary_date,'expected':nxt})
result={'passed':not fails,'accounts':summary,'failures':fails,'interpretation':'Only mature chains are denominators: 36 for 5 sessions and 26 for 20 sessions per fee; 49 total reentries is not the denominator.'};(O/'diagnostic-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(result)
