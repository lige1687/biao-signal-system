"""Apply/rollback only reviewed integration files, with hash preconditions.
No git reset/clean, no database actions, no service actions.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil

LAB=Path('/Users/yongbiaoli/Desktop/lei-signal-lab')
STAGE=Path('/Users/yongbiaoli/lei-signal-integration-20260909')
RAW=Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

parser=argparse.ArgumentParser()
parser.add_argument('action',choices=['apply','rollback'])
parser.add_argument('--group',choices=['backend','frontend','support','all'],required=True)
args=parser.parse_args()
entries=[x for x in json.loads((RAW/'deployment-manifest.json').read_text()) if args.group=='all' or x['group']==args.group]
# Validate every selected file before touching any of them.
for row in entries:
    expected=row['before_sha256'] if args.action=='apply' else row['after_sha256']
    assert digest(LAB/row['path'])==expected,('destination_changed',row['path'])
    if args.action=='apply':assert digest(STAGE/row['path'])==row['after_sha256'],('source_changed',row['path'])
    elif row['before_sha256'] is not None:assert digest(RAW/'backup/runtime'/row['path'])==row['before_sha256'],('backup_mismatch',row['path'])
for row in sorted(entries,key=lambda r:r['before_sha256'] is not None):
    dest=LAB/row['path']
    if args.action=='rollback' and row['before_sha256'] is None:
        dest.unlink();continue
    source=STAGE/row['path'] if args.action=='apply' else RAW/'backup/runtime'/row['path']
    dest.parent.mkdir(parents=True,exist_ok=True)
    temp=dest.with_name(dest.name+'.03b-integration-tmp')
    assert not temp.exists(),str(temp)
    shutil.copy2(source,temp)
    os.replace(temp,dest)
for row in entries:
    assert digest(LAB/row['path'])==row['after_sha256' if args.action=='apply' else 'before_sha256'],row['path']
(RAW/(args.action+'-'+args.group+'.json')).write_text(json.dumps({'action':args.action,'group':args.group,'verified_files':[r['path'] for r in entries]},ensure_ascii=False,indent=2))
print(args.action,args.group,len(entries),'files verified')
