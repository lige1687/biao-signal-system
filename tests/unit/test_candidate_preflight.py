"""Independent small counterexamples; no market results supplied to preflight."""
from copy import deepcopy
import unittest

from lei_signal.research.candidate_preflight import PreflightRegistry, remap_result


def identity():
    return {k: 'fixture-' + k for k in ['data', 'contract', 'target', 'baseline',
                                      'horizon', 'evaluator', 'thresholds', 'features']}

def row(idx, a, b=False, x=True, eligible=True, stratum='2025'):
    return {'id':str(idx),'question':'M','symbol':'ETF','date':str(idx),
            'stratum':stratum,'x':x,'eligible':eligible,'features':{'a':a,'b':b}}

def candidate(cid='c',terms=None,logic='and'):
    return {'candidate_id':cid,'question':'M','context':{'logic':logic,
             'terms':terms or [{'field':'a','value':True}]}}

def registry(rows,ident=None,menu=None):
    return PreflightRegistry(ident or identity(),menu or {'M':{'a':[True,False],'b':[True,False]}},
                             {'M':2},rows)


class PreflightTests(unittest.TestCase):
    def test_unknown_logic_and_global_complement(self):
        r=registry([row(1,None,False),row(2,True,None),row(3,False,True)])
        a=r.inspect(candidate('a',[{'field':'a','value':True},{'field':'b','value':True}]))
        b=r.inspect(candidate('b',[{'field':'a','value':False},{'field':'b','value':False}],'or'))
        self.assertEqual(a['partition_ids'],{'context':[],'complement':['1','3'],'unknown':['2']})
        self.assertEqual(b['reuse']['relation'],'global_complement')
        self.assertEqual(b['reuse']['orientation'],-1)
        self.assertEqual(b['partition_ids']['unknown'],['2'])

    def test_result_fields_rejected_recursively(self):
        for key in ['return_pct','risk_pct','up','label','response','expected_return']:
            value=row(1,True);value[key]=100
            with self.subTest(key=key),self.assertRaises(ValueError):registry([value])
        value=row(1,True);value['features']['return_pct']=2
        with self.assertRaises(ValueError):registry([value])
        value=row(1,True);value['features']['a']={'return_pct':2}
        with self.assertRaises(ValueError):registry([value])

    def test_optional_date_cannot_carry_nested_result_data(self):
        value=row(1,True);value['date']={'return_pct':2}
        with self.assertRaises(ValueError):registry([value])

    def test_one_side_description_survives_sparse_other_side(self):
        rows=[row(i,True,x=i<2) for i in range(4)]+[row(5,False,x=True)]
        p=registry(rows).inspect(candidate())
        self.assertEqual(p['readiness'],'description_only')
        self.assertEqual(p['eligible_layers']['context'],[['ETF','2025']])
        self.assertEqual(p['common_layers'],[])
        self.assertEqual(p['counts']['context']['all'],4)

    def test_qualification_counts_and_common_layers(self):
        rows=[row(i,i<4,x=i%4<2) for i in range(8)]+[row(9,None,eligible=False)]
        p=registry(rows).inspect(candidate())
        self.assertEqual(p['readiness'],'background_comparison')
        self.assertEqual(p['common_layers'],[['ETF','2025']])
        self.assertEqual(p['counts']['unknown']['all'],1)
        self.assertEqual(p['counts']['unknown']['eligible'],0)

    def test_identity_changes_prevent_cache_reuse(self):
        r=registry([row(1,True)])
        first=r.inspect(candidate('a'))
        for key in identity():
            changed=identity();changed[key]+='-other'
            other=registry([row(1,True)],changed).inspect(candidate('b'))
            self.assertNotEqual(first['cache_identity'],other['cache_identity'])
        changed=r.inspect(candidate('other'))
        self.assertEqual(changed['reuse']['relation'],'exact')

    def test_dataset_coincidence_not_global_equivalence(self):
        r=registry([row(1,True,True),row(2,False,False)])
        a=r.inspect(candidate('a'))
        b=r.inspect(candidate('b',[{'field':'b','value':True}]))
        self.assertEqual(b['reuse']['relation'],'dataset_equivalent')
        self.assertEqual(b['reuse']['orientation'],1)
        self.assertNotEqual(a['truth_signature'],b['truth_signature'])

    def test_menu_and_type_validation(self):
        with self.assertRaises(ValueError):registry([row(1,1)])
        r=registry([row(1,True)])
        with self.assertRaises(ValueError):r.inspect(candidate(terms=[{'field':'a','value':1}]))
        with self.assertRaises(ValueError):r.inspect(candidate(terms=[{'field':'a','value':True},{'field':'a','value':False}]))
        with self.assertRaises(ValueError):registry([row(1,True),row(1,False)])

    def test_candidate_id_cannot_be_reused_for_a_revision(self):
        r=registry([row(1,True),row(2,False)])
        r.inspect(candidate('same'))
        with self.assertRaises(ValueError):
            r.inspect(candidate('same',[{'field':'a','value':False}]))
        revised=r.inspect(candidate('same-v2',[{'field':'a','value':False}]))
        self.assertEqual(revised['reuse']['source_candidate_id'],'same')
        self.assertEqual(revised['reuse']['orientation'],-1)

    def test_complete_evaluation_orientation_metadata_and_no_mutation(self):
        source={'candidate':{'candidate_id':'old','question':'M','context':{'logic':'and','terms':[{'field':'a','value':True}]}},
                'semantic_key':'old','partition_counts':{'context':3,'complement':4,'unknown':1},
                'partition_ids':{'context':['a'],'complement':['b'],'unknown':['u']},
                'context':{'primary':{'delta_pp':-2,'covered_ids':['a']}},
                'complement':{'primary':{'delta_pp':5,'covered_ids':['b']}},
                'common_strata_interaction':{'keys':[['s','y']],'delta_difference_pp':-7,'weight':7},
                'limitations':['x']}
        copy=deepcopy(source)
        new=candidate('new',[{'field':'a','value':False}]);new['expected_pattern']='opposite expectation retained'
        result=remap_result(source,new,-1)
        self.assertEqual(source,copy)
        self.assertEqual(result['candidate'],new)
        self.assertEqual(result['context'],source['complement'])
        self.assertEqual(result['partition_ids']['unknown'],['u'])
        self.assertEqual(result['common_strata_interaction']['delta_difference_pp'],7)
        self.assertEqual(result['common_strata_interaction']['weight'],7)
        self.assertEqual(remap_result(source,new,1)['context'],source['context'])
        source['common_strata_interaction']['delta_difference_pp']=None
        self.assertIsNone(remap_result(source,new,-1)['common_strata_interaction']['delta_difference_pp'])


if __name__=='__main__':unittest.main()
