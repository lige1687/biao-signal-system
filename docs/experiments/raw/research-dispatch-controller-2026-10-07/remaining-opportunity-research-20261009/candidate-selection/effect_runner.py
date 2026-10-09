"""Frozen saved-result comparison; support stage cannot access Y.

The effect stage requires a root-issued byte-bound release and an unused external
route. No feature, label, price, or model calculation is performed here.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
BASE = Path(__file__).resolve().parent
PARENT = BASE.parent
CONTRACT = PARENT / 'native-overhead-contract.json'
OUTPUT_PLAN = PARENT / 'native-overhead-output-plan.json'
MANIFEST = BASE / 'source-manifest.json'
QUALIFICATION = BASE / 'qualification-receipt.json'
SUPPORT = BASE / 'v-group-support.json'
SOURCE_LOCK = BASE / 'effect-source-lock.json'
DEFINITION_AMENDMENT = PARENT / 'weekly-definition-binding-amendment.json'
RELEASE = BASE / 'effect-release.json'
ATTEMPT = BASE / 'effect-attempt.json'
REQUIRED_RELEASE = (
    Path(__file__).resolve(), CONTRACT, OUTPUT_PLAN, MANIFEST, QUALIFICATION,
    SUPPORT, SOURCE_LOCK, DEFINITION_AMENDMENT, ROOT / 'docs/research/definitions.v1.json',
    ROOT / 'src/lei_signal/__init__.py', ROOT / 'src/lei_signal/research/output_storage.py',
    ROOT / 'src/lei_signal/research/__init__.py',
    ROOT / 'configs/storage-policy.v1.json',
    ROOT / 'configs/storage-resources.v1.json',
    ROOT / 'configs/research-output-policy.v1.json',
)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def need(ok, why):
    if not ok:
        raise ValueError(why)


def finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def ranks(values):
    """Average 1-based ranks for exact ties; preserve input order."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [None] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        r = ((i + 1) + j) / 2
        for pos in order[i:j]:
            out[pos] = r
        i = j
    return out


def rho(xs, ys):
    need(len(xs) == len(ys), 'unpaired ranks')
    if len(xs) < 2 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    a, b = ranks(xs), ranks(ys)
    ma, mb = statistics.mean(a), statistics.mean(b)
    da = sum((v-ma)**2 for v in a)
    db = sum((v-mb)**2 for v in b)
    return sum((x-ma)*(y-mb) for x, y in zip(a, b, strict=True)) / math.sqrt(da*db)


def prepared_sources():
    contract = read(CONTRACT)
    m = read(MANIFEST)
    lock=read(SOURCE_LOCK)
    need(sha(Path(__file__))==lock['script_sha256'], 'runner drift')
    need(sha(QUALIFICATION) == contract['qualification_sha256'], 'qualification drift')
    need(sha(MANIFEST) == contract['source_manifest_sha256'], 'manifest drift')
    need(sha(CONTRACT) == lock['contract_sha256'], 'contract plan drift')
    need(sha(OUTPUT_PLAN) == lock['output_plan_sha256'], 'output plan drift')
    need(sha(DEFINITION_AMENDMENT)==lock['definition_amendment_sha256'],'amendment drift')
    amendment=read(DEFINITION_AMENDMENT)['records'][0]
    need(amendment['old_sha256']==m['definition']['sha256'] and
         amendment['new_sha256']==lock['current_definition_sha256'] and
         sha(ROOT/'docs/research/definitions.v1.json')==amendment['new_sha256'],
         'authorized definition amendment mismatch')
    objects=read(ROOT/'docs/research/definitions.v1.json')['objects']
    need(len(objects)==174 and sum(o.get('id')=='research.volume_profile.overhead120' for o in objects)==1 and
         sum(o.get('id')=='research.multitimeframe.daily_stage3_at_completed_week' for o in objects)==1,
         'definition object set mismatch')
    x_path = Path(contract['saved_x']['path'])
    need(sha(x_path) == contract['saved_x']['sha256'], 'saved X drift')
    feature_path = ROOT / m['saved_feature']['path']
    need(sha(feature_path) == m['saved_feature']['sha256'], 'saved feature drift')
    return contract, m, read(QUALIFICATION), read(x_path), feature_path


def build_support(qualification, x, feature_path):
    need(x.get('schema') == 'native-risk-d-mae-real-x/1', 'saved X schema')
    xrows = x.get('rows')
    need(isinstance(xrows, list) and len(xrows) == 76 and len({r['case_id'] for r in xrows}) == 76,
         'saved X identity')
    qr = qualification['cases']
    need(len(qr) == 76 and len({r['case_id'] for r in qr}) == 76, 'qualification identity')
    qby = {r['case_id']: r for r in qr}
    need(set(qby) == {r['case_id'] for r in xrows}, 'X qualification membership')
    fs = {}
    with feature_path.open(newline='', encoding='utf-8') as f:
        for raw in csv.DictReader(f):
            key = (raw['asset'], raw['date'])
            need(key not in fs, 'duplicate saved feature')
            fs[key] = {k: raw[k] for k in ('asset','date','profile_known','overhead_supply_ratio')}
    allrows, selected = [], []
    for r in xrows:
        q = qby[r['case_id']]
        need((q['asset'], q['signal_date'], q['lifecycle']) ==
             (r['asset'], r['signal_date'], r['lifecycle']), 'X qualification identity mismatch')
        mature = r['window_metadata']['calendar_mature_by_20260626'] is True
        why = None
        if not q['qualified']:
            why = 'feature_unqualified'
        elif not mature:
            why = 'saved_X_calendar_immature'
        record = {'case_id':r['case_id'],'asset':r['asset'],'signal_date':r['signal_date'],
                  'lifecycle':r['lifecycle'],'selected':why is None,'reason':why}
        allrows.append(record)
        if why:
            continue
        f = fs.get((r['asset'],r['signal_date']))
        need(f is not None and f['profile_known']=='True', 'selected feature absent')
        xx, v, d = float(f['overhead_supply_ratio']),r['V_volatility_pct'],r['D_frozen']
        need(finite(xx) and 0 <= xx <= 1 and finite(v) and v > 0 and finite(d), 'selected X/V/D invalid')
        selected.append({**record,'X':xx,'V':v,'D':d})
    byasset = defaultdict(list)
    for r in selected:
        byasset[r['asset']].append(r)
    for asset, group in byasset.items():
        vs = [r['V'] for r in group]
        n = len(vs)
        for row, rank in zip(group, ranks(vs), strict=True):
            row['v_rank'] = rank
            row['v_group'] = min(2, math.floor(3*(rank-0.5)/n))
    support = {}
    for asset, group in sorted(byasset.items()):
        support[asset] = {'n':len(group),'lifecycle_count':len({r['lifecycle'] for r in group}),
                          'v_groups':{str(i):{'n':sum(r['v_group']==i for r in group),
                          'lifecycle_count':len({r['lifecycle'] for r in group if r['v_group']==i}),
                          'distinct_X':len({r['X'] for r in group if r['v_group']==i})}
                          for i in range(3)}}
    return {'schema':'native-overhead-v-support/1','status':'no_y_read',
            'all_cases':allrows,'selected':selected,'by_asset':support,
            'selected_count':len(selected),'exclusion_reasons':dict(Counter(r['reason'] for r in allrows if r['reason'])),
            'limitations':['V grouping uses frozen saved X only','group support does not establish Y support']}


def supported(rows, field, yfield='Y'):
    return (len(rows)>=4 and len({r['lifecycle'] for r in rows})>=2 and
            len({r[field] for r in rows})>=2 and len({r[yfield] for r in rows})>=2)


def evaluate(rows, fixed_marginal=None, fixed_conditional=None):
    assets = sorted({r['asset'] for r in rows})
    per = {}
    for asset in assets:
        group = [r for r in rows if r['asset']==asset]
        marginal = {k:rho([r[k] for r in group],[r['Y'] for r in group]) if supported(group,k) else None
                    for k in ('X','V','D')}
        conditional = {}
        for i in range(3):
            sub = [r for r in group if r['v_group']==i]
            conditional[str(i)] = {'n':len(sub),'lifecycle_count':len({r['lifecycle'] for r in sub}),
                                    'V_min':min((r['V'] for r in sub), default=None),
                                    'V_max':max((r['V'] for r in sub), default=None),
                                    'rho_X_Y':rho([r['X'] for r in sub],[r['Y'] for r in sub])
                                    if supported(sub,'X') else None}
        vals = [conditional[str(i)]['rho_X_Y'] for i in range(3)]
        per[asset] = {'n':len(group),'lifecycle_count':len({r['lifecycle'] for r in group}),
                      'marginal':marginal,'conditional':conditional,
                      'conditional_mean3':statistics.mean(vals) if all(v is not None for v in vals) else None}
    if fixed_marginal is None:
        fixed_marginal = [a for a in assets if all(per[a]['marginal'][k] is not None for k in ('X','V','D'))]
    if fixed_conditional is None:
        fixed_conditional = [a for a in assets if per[a]['conditional_mean3'] is not None]
    agg = {}
    for k in ('X','V','D'):
        vals = [per.get(a,{}).get('marginal',{}).get(k) for a in fixed_marginal]
        agg[k] = statistics.mean(vals) if len(vals)>=2 and all(v is not None for v in vals) else None
    vals = [per.get(a,{}).get('conditional_mean3') for a in fixed_conditional]
    agg['conditional_mean3'] = statistics.mean(vals) if len(vals)>=2 and all(v is not None for v in vals) else None
    return {'per_asset':per,'fixed_marginal_assets':fixed_marginal,
            'fixed_conditional_assets':fixed_conditional,'equal_asset_mean':agg}


def effect_result(support, y):
    need(y.get('schema')=='native-risk-d-mae-real-y/1' and y.get('mature_count')==75,
         'saved Y schema/count')
    yr = y.get('rows')
    need(isinstance(yr,list) and len(yr)==76 and len({r['case_id'] for r in yr})==76,'saved Y cases')
    ys = {r['case_id']:r for r in yr}
    need(set(ys)=={r['case_id'] for r in support['all_cases']},'Y identity set')
    rows=[]
    for s in support['selected']:
        yrow=ys[s['case_id']]
        need((yrow['asset'],yrow['signal_date'],yrow['lifecycle'])==
             (s['asset'],s['signal_date'],s['lifecycle']),'Y identity mismatch')
        need(yrow.get('label_reason') is None and finite(yrow.get('Y')) and yrow['Y']>=0,
             'selected Y unknown or invalid')
        need(yrow['V_volatility_pct']==s['V'] and yrow['D_frozen']==s['D'], 'Y carried X drift')
        rows.append({**s,'Y':yrow['Y']})
    main=evaluate(rows)
    removed=[]
    allgroups=sorted({(r['asset'],r['lifecycle']) for r in yr})
    need(len(allgroups)==33,'original lifecycle count')
    for asset,life in allgroups:
        kept=[r for r in rows if (r['asset'],r['lifecycle'])!=(asset,life)]
        trial=evaluate(kept,main['fixed_marginal_assets'],main['fixed_conditional_assets'])
        removed.append({'asset':asset,'lifecycle':life,'affected_case_ids':
                        [r['case_id'] for r in rows if (r['asset'],r['lifecycle'])==(asset,life)],
                        'fixed_groups_preserved':True,
                        'affected':len(kept)!=len(rows),
                        'per_asset':trial['per_asset'],
                        'fixed_marginal_assets':trial['fixed_marginal_assets'],
                        'fixed_conditional_assets':trial['fixed_conditional_assets'],
                        'equal_asset_mean':trial['equal_asset_mean']})
    return {'schema':'native-overhead-saved-effect/1','case_count':len(rows),
            'case_ids':[r['case_id'] for r in rows], 'main':main,'delete_33':removed,
            'limitations':['historical already seen','V thirds are coarse grouping not exact control',
                           'no fit or prediction increment','overlapping cases and 20-session paths']}


def support_main():
    need(not SUPPORT.exists(),'saved support pass already exists')
    contract,m,q,x,fp=prepared_sources()
    result=build_support(q,x,fp)
    result['contract_sha256']=sha(CONTRACT)
    result['saved_X_sha256']=contract['saved_x']['sha256']
    result['feature_csv_sha256']=m['saved_feature']['sha256']
    with SUPPORT.open('x',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')


def _external_fd(plan):
    mount=Path(plan['external_mount'])
    need(mount.is_mount() and mount.stat().st_dev==plan['external_device'],'external mount changed')
    base=Path(plan['run_directory']).parent.parent
    flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
    fds=[]
    try:
        fd=os.open(base,flags);fds.append(fd)
        need(os.fstat(fd).st_dev==plan['external_device'],'external base device')
        for name in (Path(plan['run_directory']).parent.name,Path(plan['run_directory']).name,'result'):
            try:os.mkdir(name,dir_fd=fd)
            except FileExistsError:
                need(name==Path(plan['run_directory']).parent.name,'result route exists')
            nextfd=os.open(name,flags,dir_fd=fd);fds.append(nextfd)
            need(os.fstat(nextfd).st_dev==plan['external_device'],'external route device')
            fd=nextfd
        return fds,fd
    except BaseException:
        for fd in reversed(fds):os.close(fd)
        raise


def accepted_single_pass(release):
    return (release.get('status')=='accepted_once' and
            type(release.get('effect_passes')) is int and release['effect_passes']==1)


def effect_main():
    need(RELEASE.is_file(),'root release missing')
    release=read(RELEASE)
    need(accepted_single_pass(release),
         'effect release status')
    fixed=release.get('fixed_files')
    need(isinstance(fixed,dict) and set(map(str,REQUIRED_RELEASE)).issubset(fixed),
         'release missing dependency closure')
    need(str(read(CONTRACT)['saved_x']['path']) in fixed and
         str(read(MANIFEST)['native_y']['result_path']) in fixed and
         str(ROOT/read(MANIFEST)['saved_feature']['path']) in fixed,
         'release missing saved X/Y/feature')
    for path,expected in fixed.items():
        need(sha(Path(path))==expected,f'release source drift: {path}')
    contract,m,qualification,x,feature_path=prepared_sources()
    need(fixed[str(Path(contract['saved_x']['path']))]==contract['saved_x']['sha256'] and
         fixed[str(Path(m['native_y']['result_path']))]==m['native_y']['sha256'] and
         fixed[str(feature_path)]==m['saved_feature']['sha256'],
         'saved result source binding mismatch')
    plan=read(OUTPUT_PLAN)
    sys.path.insert(0,str(ROOT/'src'))
    from lei_signal.research.output_storage import recheck_saved_plan
    recheck_saved_plan(ROOT,plan,plan['task_id'],plan['estimated_bytes'],
                       internal_bytes=plan['internal_metadata_bytes'])
    need(not ATTEMPT.exists(),'effect pass already consumed')
    attempt={'schema':'native-overhead-effect-attempt/1','status':'started',
             'started_at_utc':datetime.now(timezone.utc).isoformat(),
             'release_sha256':sha(RELEASE),'plan_sha256':sha(OUTPUT_PLAN)}
    with ATTEMPT.open('x',encoding='utf-8') as f:json.dump(attempt,f,indent=2);f.write('\n')
    fds=[]
    try:
        fds,outfd=_external_fd(plan)
        support=read(SUPPORT)
        need(support['schema']=='native-overhead-v-support/1' and support['status']=='no_y_read',
             'support schema')
        y=read(read(MANIFEST)['native_y']['result_path'])
        result=effect_result(support,y)
        blob=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
        need(Path(plan['external_mount']).is_mount() and os.fstat(outfd).st_dev==plan['external_device'],
             'external lost before write')
        fd=os.open('effect-result.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=outfd)
        with os.fdopen(fd,'wb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        rd=os.open('effect-result.json',os.O_RDONLY|os.O_NOFOLLOW,dir_fd=outfd)
        with os.fdopen(rd,'rb') as f:back=f.read()
        need(hashlib.sha256(back).digest()==hashlib.sha256(blob).digest(),'external readback mismatch')
        attempt.update(status='executed_pending_independent_review',
                       result_path=str(Path(plan['output'])/'effect-result.json'),
                       result_sha256=hashlib.sha256(blob).hexdigest(),result_bytes=len(blob),
                       finished_at_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as e:
        attempt.update(status='failed_no_automatic_retry',error=repr(e),traceback=traceback.format_exc(),
                       finished_at_utc=datetime.now(timezone.utc).isoformat())
        raise
    finally:
        for fd in reversed(fds):os.close(fd)
        ATTEMPT.write_text(json.dumps(attempt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    if sys.argv[1:]==['--support']:
        support_main()
    elif sys.argv[1:]==['--effect']:
        effect_main()
    else:
        raise SystemExit('usage: effect_runner.py --support|--effect')
