"""Pinned native integration, optional unless explicit source paths supplied."""
import copy,json,os,unittest,tempfile
from pathlib import Path
from lei_signal.research.candidate_fingerprints import inspect_candidates,CONTEXT_FIELDS

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'docs/experiments/raw/external-candidate-diversity-2026-10-04'
SOURCE=os.environ.get('LEI_FACTORMINER_SOURCE')

@unittest.skipUnless(SOURCE, 'Optional pinned upstream: set LEI_FACTORMINER_SOURCE')
class CandidateFingerprintsTests(unittest.TestCase):
    def setUp(self):
        self.payload=json.loads((RAW/'example-input.json').read_text())
        self.provenance=RAW/'provenance.json'
    def call(self,payload=None,provenance=None):
        return inspect_candidates(payload or self.payload,upstream=SOURCE,provenance=provenance or self.provenance)
    def test_real_entry_keeps_all_and_distinguishes(self):
        result=self.call();self.assertEqual(len(result['candidates']),5);self.assertEqual(result['automatic_deletions'],0)
        r=result['candidates'];self.assertEqual(r[1]['duplicate_of'],'parent')
        self.assertEqual([r[i]['status'] for i in [0,2,3]],['unreviewed_candidate']*3)
        self.assertEqual(r[4]['status'],'invalid_formula')
    def test_every_context_field_separates(self):
        parent=self.payload['candidates'][0]
        for key in CONTEXT_FIELDS:
            other=copy.deepcopy(parent);other['candidate_id']='changed'
            other['context'][key]='b'*64 if key=='data_sha256' else 'other'
            p={'schema':'candidate-fingerprints/1','candidates':[parent,other]}
            self.assertIsNone(self.call(p)['candidates'][1]['duplicate_of'],key)
    def test_order_nesting_and_safe_division_not_collapsed(self):
        cases=json.loads((RAW/'cases.json').read_text())
        for c in cases:
            if c['kind'] not in ['different','edge_different']:continue
            ctx=self.payload['candidates'][0]['context']
            p={'schema':'candidate-fingerprints/1','candidates':[{'candidate_id':str(i),'formula':f,'context':ctx} for i,f in enumerate([c['left'],c['right']])]}
            self.assertIsNone(self.call(p)['candidates'][1]['duplicate_of'],c['id'])
    def test_all_revisions_retained(self):
        p=copy.deepcopy(self.payload);p['candidates']=[copy.deepcopy(p['candidates'][0]) for _ in range(3)]
        for i,r in enumerate(p['candidates']):r['candidate_id']=str(i)
        r=self.call(p)['candidates'];self.assertEqual([x['duplicate_of'] for x in r],[None,'0','0'])
    def test_missing_context_results_or_duplicate_id_rejected(self):
        for mode in ['missing','result','id']:
            p=copy.deepcopy(self.payload)
            if mode=='missing':p['candidates'][0]['context'].pop('available_at')
            elif mode=='result':p['candidates'][0]['y']=99
            else:p['candidates'][1]['candidate_id']='parent'
            with self.assertRaises(ValueError):self.call(p)
    def test_changed_or_incomplete_source_rejected(self):
        spec=json.loads(self.provenance.read_text())
        with tempfile.TemporaryDirectory(dir=ROOT/'.biao') as tmp:
            p=Path(tmp)/'provenance.json'
            for mode in ['sha','missing']:
                bad=copy.deepcopy(spec)
                if mode=='sha':bad['files'][0]['sha256']='0'*64
                else:bad['files']=[]
                p.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):self.call(provenance=p)

if __name__=='__main__':unittest.main()
