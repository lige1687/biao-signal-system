"""Read-only qualification of fixed saved evidence; originals must be present locally."""
from pathlib import Path
import hashlib,json,re
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    f=json.loads((BASE/'qualified-facts.json').read_text())
    m=json.loads((BASE/'source-manifest.json').read_text())
    checks=[]
    def check(name,condition):
        checks.append({'check':name,'passed':bool(condition)})
    texts={}
    for s in m['sources']:
        raw=ROOT/s['raw_path']; txt=ROOT/s['text_path']
        check(s['id']+'_raw_original_hash',sha(raw)==s['raw_sha256'])
        check(s['id']+'_text_hash',sha(txt)==s['text_sha256'])
        text=txt.read_text(); begin=text.index(s['announcement_id']); section=text[begin:]; section=section[:section.index('特此公告。')]
        texts[s['id']]=re.sub(r'\s+','',section)
        check(s['id']+'_issuer_identity','海通证券股份有限公司' in section and '600837' in section)
    check('halt_explicit_at_open','2024年9月6日（星期五）开市时起开始停牌' in texts['halt'])
    check('resume_explicit_at_open','2024年10月10日（星期四）开市时起复牌' in texts['resume'])
    check('resume_reconfirms_halt','自2024年9月6日（星期五）开市起停牌' in texts['resume'])
    source=ROOT/f['vendor_input']['path']; before=sha(source)
    check('fixed_vendor_hash',before=='3595b420f1831cbd51a298482c18bd2c88d3c2fd413162ebb6e9887fc27c82ae')
    rows=json.loads(source.read_text())['records']; chosen=[r for r in rows if '2024-09-06'<=r['date']<'2024-10-10']; dates=[r['date'] for r in chosen]
    check('exact17_rows_unique',len(chosen)==len(set(dates))==17)
    check('sidecar_dates_match',dates==f['matched_dates'])
    check('identity_and_nontrading',all(r['code']=='sh.600837' and r['tradestatus']=='0' for r in chosen))
    check('blank_volume_amount_preserved',all(r['volume']==r['amount']=='' for r in chosen))
    check('constant_placeholder_OHLC',all(all(r[k]=='8.7700' for k in ('open','high','low','close','preclose')) for r in chosen))
    bydate={r['date']:r for r in rows}
    check('prehalt_trading_observation',bydate['2024-09-05']['tradestatus']=='1' and int(bydate['2024-09-05']['volume'])>0)
    check('resumption_trading_observation',bydate['2024-10-10']['tradestatus']=='1' and int(bydate['2024-10-10']['volume'])>0)
    check('fixed_source_not_modified',sha(source)==before)
    result={'scope':f['scope'],'checks':checks,'passed':all(x['passed'] for x in checks),'count':len(checks),'matched_rows':len(chosen),'script_sha256':sha(Path(__file__)),'independent_agent_review':False,'price_repairs':0}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['passed'] else 1
if __name__=='__main__': raise SystemExit(main())
