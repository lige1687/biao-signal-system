"""Bounded local evidence readback; no market requests or factor/return calculation."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, zipfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
def load(p): return json.loads((ROOT / p).read_text())
def digest(p):
    p = Path(p)
    return {"path": str(p), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
def save(name, value):
    assert shutil.disk_usage(ROOT).free >= 536870912
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

start = datetime.datetime.now(datetime.timezone.utc).isoformat()
zp = ROOT / 'docs/experiments/raw/stock-large-cloud-input-2026-10-07/stock-5211-frozen-close-2020-2024-v1.zip'
zi = digest(zp)
assert zi['bytes'] == 16619603
assert zi['sha256'] == '43ebf06bfe66c79c2fb332fa287db33d49a60f23c4c3da0e4bb39ea9d23fe192'
with zipfile.ZipFile(zp) as z:
    assert z.testzip() is None
    manifest_bytes = z.read('manifest.json')
    assert hashlib.sha256(manifest_bytes).hexdigest() == '01d562a656889f320384ba3176a9636a816ce3b0f72f9882bae6bc46d71b7d79'
    manifest = json.loads(manifest_bytes)
    assert set(z.namelist()) == set(manifest['payloads']) | {'manifest.json'}
    members = []
    for name, expected in manifest['payloads'].items():
        data = z.read(name)
        actual = {'name': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256']
        members.append(actual)
    calendar = json.loads(z.read('calendar.json'))
    pool = json.loads(z.read('pool.json'))
    assert len(pool['codes']) == len(set(pool['codes'])) == 5211
    days = calendar['trading_dates']
    early = [{'date': w, 'available_calendar_rows_including_t': days.index(w)+1,
              'available_calendar_rows_before_t': days.index(w)} for w in calendar['complete_week_ends'][:6]]

sources = []
for rec in manifest['source_files'] + manifest['source_code_pins'] + manifest['strategy_sources_actual']:
    actual = digest(rec['path'])
    actual['expected_sha256'] = rec['sha256']
    actual['matches_export_snapshot'] = actual['sha256'] == rec['sha256'] and actual['bytes'] == rec['bytes']
    sources.append(actual)
assert all(s['matches_export_snapshot'] for s in sources), 'current source differs; preserve failure and inspect before acceptance'

b04p = 'docs/experiments/raw/b04-targeted-gap-batch-2026-10-06/run01-review-01/acceptance.json'
b05p = 'docs/experiments/raw/b05-final-gap-batch-2026-10-06/run01-review-01/selected-34-independent-classification.json'
b04 = load(b04p)['old1944_source_status_after_run01']
b05 = load(b05p)
assert b04 == {'normal_raw_observation':1601,'provider_status0_placeholder':305,'never_queried':34,'queried_no_return':4}
assert b05['categories'] == {'never_queried':0,'normal':0,'placeholder':34,'queried_no_return':0}
assert len({(r['exchange'],r['symbol'],r['date']) for r in b05['keys']}) == 34
assert all(r['category']=='provider_status0_placeholder' and not r['main_table_repaired'] for r in b05['keys'])
merged = {'normal_raw_observation':1601, 'provider_status0_placeholder':339, 'queried_no_return':4, 'never_queried':0}
assert sum(merged.values()) == 1944
receipt = digest(ROOT / 'docs/experiments/raw/b05-final-gap-batch-2026-10-06/run-01/receipt.json')
assert receipt['sha256'] == 'd98632261d2e2750b6a91c248715fd11671328eb7e7127816585b47115312a23'
audit = digest(ROOT / 'docs/experiments/raw/b05-final-gap-batch-2026-10-06/run01-review-01/post-run-audit.json')
assert audit['sha256'] == 'cc47d93606c3fa5068ac581e6ff1d6c54d73e64ca0ef8b8b8d1dd6a7c32c9e7b'
anchor_sources = []
for name, expected in [
    ('announcement-13888.json','f04250fc675f42e487a6091df32971ed4aa2b9b5a4ac7c5f6cc849ecca10a7a9'),
    ('official-20211126-adjustments.xlsx','f6b9d596f3fa6072258aa1eb2c036517bf20cc74c7879eaad1069cb8e1747909'),
    ('current-000300cons.xls','0f9fde0e470ba81bddd0d3e6db05269e1b5077aca778879f3833d04e027fa25d')]:
    a = digest(ROOT / 'docs/experiments/raw/csi300-anchor-acquisition-2026-10-07' / name)
    assert a['sha256'] == expected
    anchor_sources.append(a)

status = subprocess.check_output(['git','status','--porcelain'], cwd=ROOT,text=True).splitlines()
space = [{'path': str(p), **shutil.disk_usage(p)._asdict()} for p in [ROOT,Path('/Volumes/win+mac通用')] if p.exists()]
processes = []
for line in subprocess.check_output(['ps','-axo','pid=,etime=,pcpu=,rss=,comm='],text=True).splitlines():
    fields = line.strip().split(None,4)
    if len(fields)==5 and any(s in Path(fields[4]).name.lower() for s in ['python','codex','exec-server']):
        processes.append({'pid':int(fields[0]),'elapsed':fields[1],'cpu_percent':fields[2], 'rss_kib':int(fields[3]), 'executable_basename':Path(fields[4]).name})
result = {
    'checked_at_utc':start,'zip':zi,'zip_members_verified':len(members)+1,
    'payload_hashes':members,'export_sources_and_code_and_strategy_unchanged':sources,
    'input_shape':manifest['shape'],'weekly_availability':manifest['weekly_availability'],
    'null_cells':manifest['slice_quality']['arrow_null_cells'],
    'source_partition_1944':merged,'source_partition_method':'B04 accepted exact-key classification plus B05 final34; not all returned raw rows',
    'source_partition_evidence':[digest(ROOT/b04p),digest(ROOT/b05p),receipt,audit],
    'main_price_repairs':0,'anchor_sources_hash_verified':anchor_sources,
    'historical_complete_anchor_acquired':False,
    'warmup_compatibility':{'handoff_P26_requires_277_contiguous_closes':True,
        'P26_original_contract_verified_here':False,'first_six_weekly_dates':early,
        'first_four_weekly_dates_insufficient_under_either_counting_convention':True,
        '2022_02_11_boundary_requires_original_contract':True,
        'not_an_assertion_that_original_P26_input_is_wrong':True},
    'environment':{'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        'tracked_dirty_paths':sum(not s.startswith('??') for s in status),'untracked_paths':sum(s.startswith('??') for s in status),
        'space_bytes':space,'process_snapshot':processes,'process_arguments_captured':False,
        'cloud_scratch_present_local':Path('/workspace/scratch/3b760ccd9853').exists()},
    'activity':{'new_market_or_web_requests':0,'library_downloads':0,'factor_or_return_calculations':0,'new_fits':0,'subagents':0,'external_writes':0},
    'local_search_scope_for_PPO_P26_originals':'docs/experiments/raw and docs/research/proposals filenames; no original large-stock effect bundle found in that bounded scope',
    'not_qualified_for':['historical all-A inference','historical CSI300 full membership','cash-dividend total wealth','live execution','historical industry comparisons','volume or OHLC-dependent stock factors']
}
save('readback.json',result)
print(json.dumps({'status':'local_readback_passed','sources_unchanged':len(sources),'zip_members':len(members)+1,'partition':merged,'tracked_dirty':result['environment']['tracked_dirty_paths'],'local_free_gib':round(space[0]['free']/2**30,2)},ensure_ascii=False))
