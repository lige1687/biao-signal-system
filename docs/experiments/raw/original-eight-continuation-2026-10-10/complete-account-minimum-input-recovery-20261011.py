"""Copy the two exact remaining originals; recover using a separate process."""
from pathlib import Path
import datetime, hashlib, json, os, plistlib, shutil, subprocess, sys

RAW = Path(__file__).parent
ROOT = RAW.parents[3]
plan = json.loads((RAW / 'complete-account-core-output-plan-20261011.json').read_text())
mount = Path(plan['external_mount'])
info = plistlib.loads(subprocess.check_output(['diskutil', 'info', '-plist', str(mount)]))
assert info['VolumeUUID'] == plan['external_uuid']
assert info['MountPoint'] == str(mount) and info['Writable'] and not info['Internal']
assert mount.stat().st_dev == plan['external_device']
assert shutil.disk_usage(mount).free > plan['external_reserve_bytes'] + 400000
assert shutil.disk_usage(ROOT).free > plan['internal_reserve_bytes'] + 100000
proof = Path(plan['run_directory']) / 'recovery-proof'
backup = proof / 'remaining-input-backup'
restored = proof / 'remaining-input-restored'
manifest = proof / 'remaining-input-copy-manifest.json'
assert proof.is_dir() and not backup.exists() and not restored.exists() and not manifest.exists()
expected = [
 ('docs/research/current-standards.json', 1209, 'd1293a6c4536b0b440f8260d91e5a8d8d1485a0ccbd0fc3801d478baec68ce71'),
 ('docs/experiments/raw/research-eighth-2026-09-08/product-qualification/bars-helper-native/sz159915-nominal.csv', 148806, 'dc15f1c722114cf0f67d3c63d123b91fce27d60a9c41c4796a058b7b05fdece0'),
]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def stat(p):
 s = p.stat()
 return dict(bytes=s.st_size, mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns, inode=s.st_ino, device=s.st_dev)
items = []
for i, (name, size, fingerprint) in enumerate(expected):
 p = ROOT / name
 assert p.is_file() and p.stat().st_size == size and sha(p) == fingerprint
 items.append(dict(source=str(p), backup=str(backup / f'{i:02d}-{p.name}'), restored=str(restored / f'{i:02d}-{p.name}'), sha256=fingerprint, source_stat_before=stat(p)))
backup.mkdir()
for x in items:
 shutil.copy2(x['source'], x['backup'])
 assert sha(Path(x['backup'])) == x['sha256']
manifest.write_text(json.dumps(dict(items=items), ensure_ascii=False, indent=2) + '\n')
child = "from pathlib import Path;import json,os,shutil,sys;d=json.loads(Path(sys.argv[1]).read_text());r=Path(d['items'][0]['restored']).parent;r.mkdir();[shutil.copy2(x['backup'],x['restored']) for x in d['items']];print(os.getpid())"
pid = int(subprocess.check_output([sys.executable, '-c', child, str(manifest)], text=True).strip())
assert pid != os.getpid()
for x in items:
 p, b, r = map(Path, (x['source'], x['backup'], x['restored']))
 assert stat(p) == x['source_stat_before']
 assert sha(p) == sha(b) == sha(r) == x['sha256']
 assert b.stat().st_size == r.stat().st_size == x['source_stat_before']['bytes']
 assert b.stat().st_dev == r.stat().st_dev == plan['external_device']
out = dict(status='two_minimum_exact_original_input_copies_and_separate_process_recovery_verified', checked_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(), files_checked=2, bytes_per_set=150015, items=items, controller_pid=os.getpid(), restore_process_pid=pid, restore_reads_backup_only=True, original_paths_and_content_and_stat_unchanged=True, device=plan['external_device'], uuid=plan['external_uuid'], actual_three_paths_content_equal=True, other_seventeen_inputs_reused=True, no_git_reconstruction_or_replacement=True, no_deletion_or_migration=True, limits='Same healthy physical external disk. Other computer or physical disk failure recovery remains unproved.')
(RAW / 'complete-account-minimum-input-recovery-readback-20261011.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k:v for k,v in out.items() if k != 'items'}, ensure_ascii=False))
