"""Read frozen artifacts and independently check selected exact monetary invariants."""
from pathlib import Path
from fractions import Fraction as F
import hashlib,json
ROOT=Path(__file__).resolve().parents[4];RAW=Path(__file__).parent
HERE=ROOT/'docs/experiments/raw/weekly-two-etf-complete-account-2026-10-11'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
contract=json.loads((RAW/'complete-account-engineering-contract-20261011.json').read_text())
for path,b in contract['source_fingerprints'].items():
    p=ROOT/path;assert sha(p)==b['sha256'] and p.stat().st_size==b['bytes']
delivery=json.loads((HERE/'engineering-delivery.json').read_text())
for name,h in delivery['code'].items():assert sha(HERE/name)==h
loc=json.loads((HERE/'result-location.json').read_text())
actual=[]
for item in loc['results']:
    p=Path(item['path']);assert sha(p)==item['sha256'] and p.stat().st_dev==loc['external_device']
    actual.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'device':p.stat().st_dev})
r=json.loads(Path(loc['results'][1]['path']).read_text())
cases={x['name']:x['evidence'] for x in r['cases']}
assert r['case_count']==10 and r['historical_policy_paths']==0
checks=[]
def equal(label,a,b):
    assert F(a)==F(b),(label,a,b)
    checks.append({'check':label,'actual':str(a),'expected_fraction':str(F(b))})
c2=cases['case2_zero_start_paired']
for p in ('P0','P1'):
    t=c2[p]['terminal']
    equal(p+' triple cash',t['free_cash'],F(750)-6*(100+F('5.1')))
    equal(p+' triple equity',t['equity'],F(750)-6*F('5.1'))
    equal(p+' fees',t['fees'],6*F('5.1'))
    assert t['shares']=={'sh510300':'300','sz159915':'300'}
sellfee=F(5)+F(181)*F('.001')
net=181-sellfee
buyfee=5+400*F('.001')
c4=cases['case4_actual_sale_later_buy']['terminal']
equal('sale net',net,F('175.819'))
equal('sell-laterbuy cash',c4['free_cash'],250+net-400-buyfee)
equal('sell-laterbuy fees',c4['fees'],sellfee+buyfee)
equal('sell-laterbuy equity',c4['equity'],250+net-400-buyfee+400*2+500)
c7=cases['case7_cross_week_expiry']['terminal_sale']['terminal']
equal('terminal sale freecash',c7['free_cash'],250)
equal('terminal sale restrictedcash',c7['restricted_cash'],net)
equal('terminal sale equity',c7['equity'],250+net+400*2+100)
c10=cases['case10_duplicate_save_recover_nav']
assert c10['duplicate_deposit_rejected'] and c10['recovered_money_equal']
assert abs(F(c10['prior_nav'])-F(550,450))<F(1,10**22)
checks.append({'check':'priorNAV after known price gain','actual':c10['prior_nav'],'expected_fraction':'11/9'})
assert abs(F(c10['units_after_second_deposit'])-F(7200,11))<F(1,10**22)
out={'status':'frozen_artifacts_and_independent_cash_accepted','code_manifest':delivery['code'],
'protected_source_count':len(contract['source_fingerprints']),'extra_dependency_policy_zero_sale_sha256':sha(ROOT/'docs/experiments/raw/weekly-portfolio-zero-sale-cash-2026-10-11/policy_zero_sale.py'),
'artifacts':actual,'checks':checks,'independent_cash_fraction_checks':True,'author_program_rerun':False,
'accounting_implementation':'new isolated Account, not old dated_ledger.py source reuse',
'historical_policy_paths_executed':0,'newcore_requires_fresh_unique_resultplan':True}
p=RAW/'complete-account-engineering-root-readback-20261011.json';p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':out['status'],'protected_sources':out['protected_source_count'],'cash_checks':len(checks),'result_files_readback':len(actual),'historical_policy_paths':0}))
