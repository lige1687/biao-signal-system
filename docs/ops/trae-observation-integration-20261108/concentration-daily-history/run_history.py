"""Replay the accepted source-qualified build with only an earlier daily start."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import os
import plistlib

here = Path(__file__).resolve().parent
contract = json.loads((here / 'run-contract.json').read_text())
plan = json.loads((here / 'storage-plan.json').read_text())
original = Path(contract['script'])
out = Path(contract['out'])
assert str(out) == plan['output'] and not out.parent.exists()
mount = Path(plan['external_mount'])
disk = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', str(mount)]))
assert disk['VolumeUUID'] == plan['external_uuid'] and mount.stat().st_dev == plan['external_device']
assert out.resolve().is_relative_to(mount.resolve())
for path_key, hash_key in [('script','scriptSha'), ('calendar','calendarSha'), ('witnesses','witnessesSha'), ('baselineCards','baselineCardsSha')]:
    assert hashlib.sha256(Path(contract[path_key]).read_bytes()).hexdigest() == contract[hash_key]
source = original.read_text()
marker = "daily_start='2026-09-01'"
assert source.count(marker) == 1
patched = source.replace(marker, "daily_start='2016-01-01'")
out.parent.mkdir(parents=True, exist_ok=False)
(out.parent / 'effective-rebuild.py').write_text(patched)
# The original function resolves its inputs relative to its file, so preserve that context.
program = ('import sys\nfrom pathlib import Path\n'
           f'sys.path.insert(0, {str(original.parent)!r})\n'
           f'__file__ = {str(original)!r}\n'
           f'exec(compile(Path({str(out.parent / "effective-rebuild.py")!r}).read_text(), __file__, "exec"))\n')
args = [sys.executable, '-B', '-c', program, '--calendar', contract['calendar'],
        '--calendar-sha', contract['calendarSha'], '--positive-witnesses', contract['witnesses'], '--out', str(out)]
with (out.parent / 'run.log').open('x') as log:
    subprocess.run(args, check=True, stdout=log, stderr=subprocess.STDOUT,
                   env=dict(os.environ, TMPDIR=str(out.parent)))
print(out)
