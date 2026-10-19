"""Small decision-time fixtures; no saved market outcome is opened."""
import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

path=Path(__file__).with_name('summarize_joint_cell_support.py')
spec=importlib.util.spec_from_file_location('joint_cell_support',path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def sample(n=45,constant_financial=False):
    return [{'code':f'sz.{i:06d}','industry':'C26','vol60':float(i),
             'amount20':float(i%15),'momentum':float(i%5),
             'financial':0. if constant_financial else float(4-i%5)} for i in range(n)]

class JointCellSupportTests(unittest.TestCase):
    def test_remainder_to_early_thirds_and_nested_partition(self):
        self.assertEqual([len(g) for g in mod.thirds(list(range(5)))],[2,2,1])
        self.assertEqual([len(g) for g in mod.thirds(list(range(4)))],[2,1,1])
        rows=sample(10)
        groups=mod.old_nine(rows)
        self.assertEqual(sum(groups[c]==(1,1) for c in groups),2)
        self.assertEqual(sum(groups[c][0]==1 for c in groups),4)

    def test_tiny_intersection_holds_all_and_preserves_both_margins(self):
        rows=sample()
        # Split one of nine 5-name cells across industries: 4 and 1 both hold all.
        rows[0]['industry']='C27'
        result=mod.joint_diagnostics(rows)
        self.assertEqual(result['pool_n'],45)
        self.assertTrue(any(c['n']==1 and c['tiny_hold_all'] for c in result['cells']))
        self.assertTrue(any(c['n']==4 and c['tiny_hold_all'] for c in result['cells']))
        self.assertGreater(result['tiny_hold_all_weight'],0)
        self.assertLessEqual(result['share_max_abs_error'],1e-10)
        for method in mod.METHODS:
            self.assertTrue(math.isclose(sum(result['weights'][method].values()),1.))

    def test_constant_financial_score_cannot_change_ranked_list(self):
        result=mod.joint_diagnostics(sample(constant_financial=True))
        self.assertEqual(result['nonconstant_financial_weight'],0)
        self.assertEqual(result['actual_B_minus_M_weight_change_mass'],0)
        self.assertEqual(result['actual_changed_joint_cell_weight'],0)
        changed=mod.joint_diagnostics(sample())
        self.assertGreater(changed['actual_B_minus_M_weight_change_mass'],0)
        self.assertGreater(changed['nonconstant_financial_weight'],0)

    def test_price_projection_discards_future_field(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'price.csv'
            p.write_text('month,code,eligibility_reason,momentum,vol60,amount20,future_return\n'
                         '2015-01,sz.000001,eligible,0.1,0.2,100,SECRET_OUTCOME\n')
            row=mod.project_csv(p,mod.PRICE_COLUMNS)['2015-01','sz.000001']
            self.assertEqual(set(row),set(mod.PRICE_COLUMNS))
            self.assertNotIn('future_return',row)

if __name__=='__main__':unittest.main()
