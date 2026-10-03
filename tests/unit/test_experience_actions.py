"""Native scoped recommendation and source/identity boundaries; no factor fits."""
import copy,json,os,tempfile,unittest
from pathlib import Path
from lei_signal.research.experience_actions import recommend

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'docs/experiments/raw/factorminer-experience-actions-2026-10-04'

@unittest.skipUnless(os.environ.get('LEI_FACTORMINER_SOURCE'),'Requires explicit frozen upstream source and Python3.12')
class TestExperienceActions(unittest.TestCase):
    def setUp(self):
        self.payload=json.loads((RAW/'example-input.json').read_text())
        self.kw={'upstream':os.environ['LEI_FACTORMINER_SOURCE'],'provenance':RAW/'component-provenance.json','skill_pack':RAW/'core/skill-pack.json'}
    def test_scoped_source_matches_native_result(self):
        result=recommend(self.payload,**self.kw)
        expected=json.loads((RAW/'core/results.json').read_text())['with_scoped_memory']
        self.assertEqual(result['guidance'],expected)
        self.assertEqual(result['status'],'research_unqualified')
    def test_foreign_target_is_uniform(self):
        self.payload['context']['scope']='foreign-target'
        g=recommend(self.payload,**self.kw)['guidance']
        self.assertEqual([v['probability'] for v in g['variants']],[.25]*4)
    def test_native_rmse_substitution_rejected(self):
        self.payload['context']['quality_scope']='project_rmse'
        with self.assertRaisesRegex(ValueError,'IC'):recommend(self.payload,**self.kw)
    def test_source_hash_mismatch_rejected_before_import(self):
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as d:
            spec=json.loads((RAW/'component-provenance.json').read_text());spec['files'][0]['sha256']='0'*64;p=Path(d)/'manifest.json';p.write_text(json.dumps(spec));kw={**self.kw,'provenance':p}
            with self.assertRaisesRegex(ValueError,'source differs'):recommend(self.payload,**kw)
    def test_inconsistent_context_even_with_recomputed_pack_digest_rejected(self):
        from factorminer.architecture.research_skills import digest
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as d:
            pack=json.loads((RAW/'core/skill-pack.json').read_text());pack['observations'][0]['context']['scope']='other';pack['pack_id']=digest({k:v for k,v in pack.items() if k!='pack_id'});p=Path(d)/'pack.json';p.write_text(json.dumps(pack));kw={**self.kw,'skill_pack':p}
            with self.assertRaisesRegex(ValueError,'context fingerprint'):recommend(self.payload,**kw)
    def test_dataset_id_excludes_same_source(self):
        from factorminer.architecture.research_skills import digest
        with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as d:
            pack=json.loads((RAW/'core/skill-pack.json').read_text());pack['observations']=[r for r in pack['observations'] if r['dataset_id']=='artificial-0'];pack['pack_id']=digest({k:v for k,v in pack.items() if k!='pack_id'});p=Path(d)/'pack.json';p.write_text(json.dumps(pack));self.payload['dataset_id']='artificial-0'
            g=recommend(self.payload,**{**self.kw,'skill_pack':p})['guidance'];self.assertEqual([v['probability'] for v in g['variants']],[.25]*4)

if __name__=='__main__':unittest.main()
