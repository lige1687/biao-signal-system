"""Independent artificial-only audit. Does not import author's tests or read prices.

Run python3 -B independent_check.py; all writes are beside this checker.
"""
import ast
import copy
import hashlib
import itertools
import json
import math
import numbers
from datetime import date, timedelta, datetime, timezone
from fractions import Fraction
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p / 'pyproject.toml').is_file())
AUTHOR = ROOT / 'docs/experiments/raw/native-risk-d-mae-2026-10-07'
STUDY = AUTHOR / 'study.py'
EXPECTED = '84f4fee2a538a918352bca099ec9c9b4a38f6d6a19dab5faa564b668c0bd8745'
assert hashlib.sha256(STUDY.read_bytes()).hexdigest() == EXPECTED
S = {}
exec(compile(STUDY.read_bytes(), str(STUDY), 'exec'), S)
checks, observations = [], []


def check(name, condition, details=None):
    checks.append({'name': name, 'pass': bool(condition), 'details': details})


def near(a, b):
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def rejects(name, fn):
    try:
        fn()
    except ValueError as exc:
        check(name, True, str(exc)[:600])
    else:
        check(name, False, 'unexpected acceptance')


def independent_ranks(x):
    # Pairwise count, not author's sorted-index/tie-block implementation.
    return [Fraction(2 * sum(z < v for z in x) + sum(z == v for z in x) + 1, 2)
            for v in x]


def independent_rho(x, y):
    if len(x) != len(y) or len(x) < 2:
        return None
    rx, ry = independent_ranks(x), independent_ranks(y)
    n = len(rx)
    sx, sy = sum(rx), sum(ry)
    xx = n * sum(v*v for v in rx) - sx*sx
    yy = n * sum(v*v for v in ry) - sy*sy
    if xx == 0 or yy == 0:
        return None
    cov = n * sum(v*w for v,w in zip(rx, ry)) - sx*sy
    return float(cov) / math.sqrt(float(xx*yy))


def artificial_population():
    counts = [15,17,12,5,26,1]
    groups = [5,7,5,3,12,1]
    cases, windows, dates, prices = [], {}, {}, {}
    for ai, (asset, count, ng) in enumerate(zip(S['ASSETS'], counts, groups)):
        start = date(2025,1,6) if ai < 5 else date(2026,6,16)
        axis = [(start+timedelta(days=k)).isoformat() for k in range(100 if ai < 5 else 11)]
        dates[asset] = axis
        prices[asset] = {d: 100+(k%13)-2*(k%4) for k,d in enumerate(axis)}
        for j in range(count):
            cid = f'artificial-{ai}-{j}'
            known = ai < 5
            cases.append({'case_id':cid,'asset':asset,'signal_date':axis[j],
                          'lifecycle':f'artificial-L{j%ng}', 'D':j%4-2,
                          'V':(j*3)%7+1, 'Y':j%5 if known else None,
                          'A':987.0, 'C':-123.0, 'ATR':999.0})
            windows[cid] = {'asset':asset,'signal_date':axis[j],
                            'label_start':axis[j+1],
                            'label_end':axis[j+21] if known else None,
                            'calendar_mature_by_20260626':known}
    return cases, windows, dates, prices


def mutate_and_reject(name, mutation):
    args = artificial_population()
    mutation(*args)
    rejects(name, lambda:S['validate_windows'](*args))


def arithmetic_checks():
    examples = [([100]*21, 0), ([100]+[130]*19+[95], 5),
                ([100]+[110]*10+[105]*10, 0), ([100,80]+[110]*19,20),
                ([80]+[100]*20,0)]
    for i,(path, expected) in enumerate(examples):
        check(f'mae_example_{i}', near(S['close_mae20'](path),expected))
    for i,bad in enumerate([None,0,-1,True,False,float('inf'),float('-inf'),float('nan'),'100']):
        rejects(f'mae_invalid_close_{i}',lambda bad=bad:S['close_mae20']([100]*20+[bad]))
    for size in [0,1,20,22,23]:
        rejects(f'mae_length_{size}',lambda size=size:S['close_mae20']([100]*size))
    check('V_formula', near(S['volatility_scale'](80,2),2.5))
    for a,b in [(0,1),(1,0),(-1,1),(1,-1),(True,1),(1,None),(float('inf'),1)]:
        check(f'V_invalid_{a}_{b}',S['volatility_scale'](a,b) is None)
    # Isolated source math, not native preflight or a real-data run.
    path=ROOT/'src/lei_signal/research/workflow_inputs.py'
    raw=path.read_bytes()
    check('native_source_SHA',hashlib.sha256(raw).hexdigest()=='43a0683c13132fa34c73d4ce618d37746b5a8aa8da89e2967d132f59bee777ad')
    funcs=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in {'_number','_label'}]
    ns={'math':math,'Real':numbers.Real}
    exec(compile(ast.Module(body=funcs,type_ignores=[]),str(path),'exec'),ns)
    target={'kind':'mae','start_offset':1,'end_offset':21,'entry_field':'close',
            'path_field':'close','unit':'percentage_point','price_measure':'economic_price'}
    for index,(closes,expected) in enumerate(examples):
        rows=[{'date':f'artificial-{k}','close':p,'low':0.001,'status':'quoted','action_known':True}
              for k,p in enumerate([1e6]+closes+[0.001])]
        value,end,reason=ns['_label'](rows,0,target)
        check(f'native_full_path_{index}',near(value,expected) and near(value,S['close_mae20'](closes)) and reason is None and end=='artificial-21')
        rows[0]['close']=1e-6;rows[22]['close']=1e6
        check(f'outside_window_{index}',ns['_label'](rows,0,target)[0]==value)
    rows=[{'date':f'artificial-{k}','close':100,'status':'quoted','action_known':True} for k in range(22)]
    rows[8]['close']=20;rows[8]['status']='halt'
    value,_,reason=ns['_label'](rows,0,target)
    check('native_halt_skipped_not_equivalent_qualification',value==0 and reason is None and S['path_close'](rows[8]) is None)
    observations.append({'name':'halt_counterexample','native_result':value,'native_reason':reason,'complete_path_accepts_halt':False,'meaning':'only arithmetic agrees on fully qualified rows'})
    for val in [None,0,'false']:
        accepted=S['path_close']({'close':100,'status':'quoted','action_known':val})
        observations.append({'name':'non_boolean_action_known','input':val,'output':accepted,'boundary':'schema/type qualification not implemented here; only literal False rejected'})
    observations.append({'name':'V_extreme_numeric_overflow','input':[1e308,1e308], 'output':str(S['volatility_scale'](1e308,1e308)), 'mathematical_value':100, 'boundary':'finite positive arguments alone do not guarantee finite V; not realistic qualified ETF anchors'})


def path_checks():
    args=artificial_population(); before=copy.deepcopy(args)
    paths=S['validate_windows'](*args)
    check('75_complete_paths',len(paths)==75 and all(len(p['closes'])==21 and len(p['dates'])==21 for p in paths.values()))
    check('unknown_retained_unlabelled','artificial-5-0' not in paths and len(args[0])==76 and args[0][-1]['Y'] is None)
    check('prevalidation_no_input_mutation',args==before)
    a=S['ASSETS'][0]; p=paths['artificial-0-0']
    check('exact_t1_t21',p['dates']==args[2][a][1:22] and p['closes']==[args[3][a][d] for d in args[2][a][1:22]])
    args[3][a][args[2][a][0]]=None
    # t+22 for first case overlaps later cases; inspect the first returned path only.
    args[3][a][args[2][a][22]]=0.001
    check('signal_and_t22_excluded_first_case',S['validate_windows'](*args)['artificial-0-0']==p)
    def invalid_price(c,w,d,p,value):p[a][d[a][8]]=value
    for k,v in enumerate([None,0,-2,True,float('inf'),float('nan'),{'close':100,'status':'halt'},
                           {'close':100,'status':'action_unknown'},{'close':100,'action_known':False}]):
        mutate_and_reject(f'window_invalid_price_{k}',lambda c,w,d,p,v=v:invalid_price(c,w,d,p,v))
    mutate_and_reject('missing_price_not_skipped',lambda c,w,d,p:p[a].pop(d[a][8]))
    mutate_and_reject('duplicate_calendar',lambda c,w,d,p:d[a].insert(8,d[a][8]))
    mutate_and_reject('unordered_calendar',lambda c,w,d,p:d[a].reverse())
    mutate_and_reject('missing_calendar_session_changes_endpoint',lambda c,w,d,p:d[a].pop(8))
    mutate_and_reject('wrong_window_end',lambda c,w,d,p:w['artificial-0-0'].update(label_end=d[a][20]))
    mutate_and_reject('mature_boolean_type',lambda c,w,d,p:w['artificial-0-0'].update(calendar_mature_by_20260626=1))
    mutate_and_reject('unexpected_mature_to_unknown',lambda c,w,d,p:w['artificial-0-0'].update(calendar_mature_by_20260626=False,label_end=None))
    mutate_and_reject('unknown_declared_mature',lambda c,w,d,p:w['artificial-5-0'].update(calendar_mature_by_20260626=True))
    mutate_and_reject('population_75_rejected',lambda c,w,d,p:c.pop())
    mutate_and_reject('duplicate_case_id',lambda c,w,d,p:c[0].update(case_id=c[1]['case_id']))
    mutate_and_reject('wrong_asset',lambda c,w,d,p:c[0].update(asset='FAKE'))
    mutate_and_reject('asset_count_changed',lambda c,w,d,p:c[0].update(asset=S['ASSETS'][1]))
    mutate_and_reject('duplicate_asset_date',lambda c,w,d,p:c[0].update(signal_date=c[1]['signal_date']))
    mutate_and_reject('identity_mismatch',lambda c,w,d,p:w['artificial-0-0'].update(asset='FAKE'))
    rejects('changed_cutoff',lambda:S['validate_windows'](*artificial_population(),cutoff='2026-06-30'))
    last=S['ASSETS'][4]
    mutate_and_reject('last_mature_path_atomic_failure',lambda c,w,d,p:p[last].pop(d[last][46]))
    # C and D are irrelevant to target arithmetic, and unchanged by prevalidation.
    args=artificial_population(); path_before=S['validate_windows'](*args)
    for r in args[0]:r.update(C=1e20,D=-987654,V=999999,A=0,ATR=-1)
    check('C_D_V_anchors_not_used_in_Y_path',S['validate_windows'](*args)==path_before)
    # Counterexample for future binding integration: arbitrary IDs pass count/consistency guards.
    observations.append({'name':'exact_membership_not_enforced','artificial_76_pass':len(paths)==75,
                         'aliases_84':'not consumed or returned by pure module','unknown_id':'artificial-5-0 accepted',
                         'boundary':'Requires original six files and exact frozen identity/hash binding upstream; not completed here'})


def statistical_checks():
    max_error=0.0; comparisons=0
    vectors=list(itertools.product([0,1,2],repeat=3))
    for i,x in enumerate(vectors):
        check(f'average_ties_{i}',S['rank_average'](x)==independent_ranks(x))
        for j,y in enumerate(vectors):
            actual,expected=S['spearman'](x,y),independent_rho(x,y)
            comparisons+=1
            if actual is not None and expected is not None:max_error=max(max_error,abs(actual-expected))
            check(f'rho_oracle_{i}_{j}',near(actual,expected))
    check('empty_rank_null',S['spearman']([],[]) is None)
    check('unequal_lengths_null',S['spearman']([1,2],[1,2,3]) is None)
    check('single_null',S['spearman']([1],[2]) is None)
    rows,*_=artificial_population(); before=copy.deepcopy(rows)
    # Contradictory A/C/ATR in factory: must use saved D/V, not recompute them.
    result=S['summarize_and_delete_one_lifecycle'](rows)
    check('stats_do_not_mutate_original_D_V',rows==before)
    check('all_33_deletions',len(result['leave_one_lifecycle'])==33)
    fixed=result['primary']['fixed_assets']
    check('baseline_five_assets',fixed==list(S['ASSETS'][:5]))
    scopes=[('baseline',rows,result['per_asset'],result['primary'])]
    groups=sorted({(r['asset'],r['lifecycle']) for r in rows})
    for idx,sc in enumerate(result['leave_one_lifecycle']):
        removed=[r for r in rows if (r['asset'],r['lifecycle'])==groups[idx]]
        remaining=[r for r in rows if r not in removed]
        check(f'delete_members_{idx}',sc['deleted_case_ids']==[r['case_id'] for r in removed] and sc['remaining_case_count']==len(remaining))
        check(f'fixed_assets_{idx}',sc['fixed_asset_summary']['fixed_assets']==fixed)
        scopes.append((str(idx),remaining,sc['per_asset'],sc['fixed_asset_summary']))
    for tag, rr, stats, summary in scopes:
        rd,rv=[],[]
        for asset in S['ASSETS']:
            allrows=[r for r in rr if r['asset']==asset]
            complete=[r for r in allrows if all(type(r[k]) in (int,float) and math.isfinite(r[k]) for k in ['D','V','Y'])]
            dr=independent_rho([r['D'] for r in complete],[r['Y'] for r in complete])
            vr=independent_rho([r['V'] for r in complete],[r['Y'] for r in complete])
            st=stats[asset]
            check(f'{tag}_{asset}_D_rho',near(st['rho_D_Y'],dr))
            check(f'{tag}_{asset}_V_rho',near(st['rho_V_Y'],vr))
            check(f'{tag}_{asset}_signed_difference',near(st['rho_D_minus_V'],None if dr is None or vr is None else dr-vr))
            check(f'{tag}_{asset}_counts',st['all_cases']==len(allrows) and st['complete_cases']==len(complete) and st['complete_case_ids']==[r['case_id'] for r in complete])
            if asset in fixed:rd.append(dr);rv.append(vr)
        if any(v is None for v in rd+rv):
            check(f'{tag}_fixed_null',summary['rho_D_Y'] is None and summary['rho_V_Y'] is None and summary['rho_D_minus_V'] is None)
        else:
            dr=sum(rd)/len(rd);vr=sum(rv)/len(rv)
            check(f'{tag}_global',near(summary['rho_D_Y'],dr) and near(summary['rho_V_Y'],vr) and near(summary['rho_D_minus_V'],dr-vr))
    unknown=[s for s in result['leave_one_lifecycle'] if s['deleted_asset']==S['ASSETS'][-1]][0]
    check('unknown_group_not_dropped',unknown['remaining_case_count']==75 and unknown['fixed_asset_summary']==result['primary'])
    # Only two complete records in asset 0; all the rest still retained as rows.
    for r in rows:
        if r['asset']==S['ASSETS'][0]:r['Y']=None
    rows[0].update(D=2,V=9,Y=5);rows[1].update(D=1,V=8,Y=0)
    result=S['summarize_and_delete_one_lifecycle'](rows)
    check('n2_flag',result['per_asset'][S['ASSETS'][0]]['n2_degenerate'] is True)
    broken=[s for s in result['leave_one_lifecycle'] if 'artificial-0-0' in s['deleted_case_ids']][0]
    check('real_deletion_makes_fixed_asset_null',broken['fixed_asset_summary']['reason']=='fixed_asset_became_uncomputable' and broken['fixed_asset_summary']['asset_count']==5)
    # Restore fresh rows: asymmetric missing inputs must use common D,V,Y rows.
    rows,*_=artificial_population();rows[0]['D']=None;rows[1]['V']=float('nan');rows[2]['Y']=None
    st=S['per_asset_stats'](rows)[S['ASSETS'][0]]
    ids=[r['case_id'] for r in rows[3:15]]
    check('same_complete_rows',st['complete_cases']==12 and st['complete_case_ids']==ids and st['labelled_cases']==14)
    expectedD=independent_rho([r['D'] for r in rows[3:15]],[r['Y'] for r in rows[3:15]])
    expectedV=independent_rho([r['V'] for r in rows[3:15]],[r['Y'] for r in rows[3:15]])
    check('missing_common_rhos',near(st['rho_D_Y'],expectedD) and near(st['rho_V_Y'],expectedV))
    for r in rows:r['D']=1
    check('constant_common_empty_null',S['equal_asset_summary'](S['per_asset_stats'](rows))['reason']=='no_common_computable_asset')
    observations.append({'name':'independent_rank_oracle','vector_pairs':comparisons,'max_abs_difference':max_error})
    # Save artificial diagnostics so the controller can inspect actual 33 scenarios.
    (OUT/'artificial-delete-diagnostics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    arithmetic_checks();path_checks();statistical_checks()
    result={'at_utc':datetime.now(timezone.utc).isoformat(),'artificial_only':True,
            'independent_checker':True,'author_test_imported':False,
            'checks':checks,'observations':observations,'passed':sum(r['pass'] for r in checks),
            'failed':sum(not r['pass'] for r in checks),
            'new_real_X':0,'new_real_V':0,'new_real_Y':0,'fits':0,
            'resampling':0,'real_price_files_opened':0}
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['passed','failed','new_real_X','new_real_Y','fits']}))
    if result['failed']:raise SystemExit(1)
