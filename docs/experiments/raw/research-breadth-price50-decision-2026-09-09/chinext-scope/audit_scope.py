"""Bounded structural audit of the frozen ChiNext membership candidate chain."""
from pathlib import Path
import hashlib,json
import pandas as pd
import re
from bs4 import BeautifulSoup

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[4]
OLD=ROOT/'docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09'; PREP=OLD/'prepared'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    sources=[ROOT/'docs/research/experiment-backtest-principles.md',ROOT/'docs/research/definition-standard.md',
      ROOT/'docs/experiments/raw/research-breadth-price50-decision-2026-09-09/protocol.md',OLD/'prepare_data.py',
      PREP/'chinext_adjustments_candidate.json',PREP/'chinext_current_snapshot.csv',PREP/'chinext_chain_failure.json']
    changes=json.loads((PREP/'chinext_adjustments_candidate.json').read_text());snap=pd.read_csv(PREP/'chinext_current_snapshot.csv',dtype={'品种代码':str})
    members={"300114" if x=="302132" else x for x in snap['品种代码'].str.zfill(6)}; rows=[]
    for x in sorted(changes,key=lambda z:z['effective_date'],reverse=True):
        adds=set(x['additions']);deletes=set(x['deletions']);post=set(members)
        missing=sorted(adds-post);already=sorted(deletes&post);members=(members-adds)|deletes
        rows.append(dict(effective_date=x['effective_date'],filename=x['filename'],post_size=len(post),pre_size=len(members),
          additions=len(adds),deletions=len(deletes),missing_additions_in_post='|'.join(missing),deletions_already_in_post='|'.join(already),
          structural_pass=len(post)==100 and len(members)==100 and not missing and not already,
          announcement_date=x.get('announcement_date') or '',source_sha256=x['sha256']))
    out=pd.DataFrame(rows);out.to_csv(HERE/'reverse-chain-checks.csv',index=False)
    first_failure=out[~out.structural_pass].iloc[0]
    assert first_failure.effective_date=='2017-10-09' and first_failure.post_size==100 and first_failure.pre_size==101 and first_failure.missing_additions_in_post=='300075'
    suffix=out[out.effective_date>='2018-01-02'];assert suffix.structural_pass.all() and len(suffix)==20
    # Published file hashes must match the candidate metadata.
    evidence=[]
    for x in changes:
        p=PREP/'sources'/x['filename']; evidence.append(dict(filename=x['filename'],exists=p.exists(),expected_sha256=x['sha256'],actual_sha256=sha(p) if p.exists() else '',match=p.exists() and sha(p)==x['sha256']))
    ev=pd.DataFrame(evidence);ev.to_csv(HERE/'source-file-checks.csv',index=False);assert ev.match.all()
    recovered=[]
    for x in changes:
        if x.get('announcement_date'): continue
        p=PREP/'sources'/x['filename']; text=' '.join(BeautifulSoup(p.read_bytes().decode('utf-8',errors='replace'),'lxml').stripped_strings)
        m=re.search(r'时间：\s*(20\d{2}-\d{2}-\d{2})',text)
        recovered.append({'filename':x['filename'],'effective_date':x['effective_date'],'stored_page_display_date':m.group(1) if m else '',
          'in_main_window':x['effective_date']>='2018-07-05','evidence':'stored page 时间 field','historical_available_at_proven':False})
    pd.DataFrame(recovered).to_csv(HERE/'missing-announcement-date-review.csv',index=False)
    summary={'principles_version':'v1.0','definition_standard_version':'v1.0.0','current_snapshot_size':len(snap),'current_unique':snap['品种代码'].nunique(),
      'events':len(changes),'suffix_events_2018_01_02_onward':len(suffix),'suffix_structurally_closed':True,
      'main_window_start':'2018-07-05','canonical_code_mapping':'302132 current code -> 300114 historical identity from frozen prepare_data.py',
      'bad_event':'2017-10-09','bad_reverse_size':'100_to_101','missing_post_addition':'300075',
      'bad_event_affects_suffix_reconstruction':False,'source_files_hash_matched':int(ev.match.sum()),
      'missing_announcement_dates':sum(not x.get('announcement_date') for x in changes),'missing_dates_in_main_window':sum(not x.get('announcement_date') and x['effective_date']>='2018-07-05' for x in changes),
      'stored_page_display_dates_recovered':sum(bool(x['stored_page_display_date']) for x in recovered),
      'qualification':'structurally reconstructable from the frozen current anchor for 2018-01-02 onward; announcement completeness and historical availability remain unproven'}
    (HERE/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    locked={str(p):sha(p) for p in sources};(HERE/'source-lock.json').write_text(json.dumps({'files':locked},ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
