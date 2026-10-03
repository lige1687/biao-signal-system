"""Recover this known frozen source without editing active code or receipts."""
import hashlib,json
from pathlib import Path
RAW=Path(__file__).resolve().parent
ROOT=RAW.parents[3]
p=Path('src/lei_signal/research/question_contract.py')
c=json.loads((RAW/'run-joint/contract.json').read_text())
s=(ROOT/p).read_text().replace('left_censor_unknown_start','left_unknown_until_spell_ends')
assert hashlib.sha256(s.encode()).hexdigest()==c['bindings']['files'][str(p)]
t=RAW/'frozen-source-copy'/p;t.parent.mkdir(parents=True,exist_ok=True)
if t.exists():assert t.read_text()==s
else:t.write_text(s)
print('Exact frozen source bytes; shared source, old contracts and receipts unchanged.')
