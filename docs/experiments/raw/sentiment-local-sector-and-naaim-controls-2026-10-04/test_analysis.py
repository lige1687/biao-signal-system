"""Artificial inputs only; no market fits, output mutation or network."""
import importlib.util
import unittest
from pathlib import Path
import numpy as np

spec=importlib.util.spec_from_file_location("current_analysis",Path(__file__).with_name("analysis.py"))
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)


class PriceBoundaryTests(unittest.TestCase):
    def test_geometric_path_units(self):
        c=100*1.001**np.arange(310)
        f=analysis.price_features(c,270)
        self.assertAlmostEqual(f['r20'],100*(1.001**20-1))
        self.assertAlmostEqual(f['r63'],100*(1.001**63-1))
        self.assertAlmostEqual(f['dd252'],0)
        self.assertAlmostEqual(f['rv20'],0,places=10)
        self.assertAlmostEqual(f['dma200'],100*(c[270]/np.mean(c[71:271])-1))

    def test_appending_future_keeps_inputs_fixed(self):
        c=100+np.sin(np.arange(310)/3)+np.arange(310)*.02
        expected=analysis.price_features(c,270)
        altered=c.copy();altered[271:]=np.nan
        self.assertEqual(expected,analysis.price_features(altered,270))

    def test_original_position_missing_is_rejected(self):
        c=np.full(310,100.);c[70]=np.nan
        with self.assertRaises(ValueError):analysis.price_features(c,270)
        with self.assertRaises(ValueError):analysis.price_features(np.full(310,100.),250)
        c[70]=0
        with self.assertRaises(ValueError):analysis.price_features(c,270)

    def test_constant_price_backgrounds_are_zero(self):
        self.assertEqual(analysis.price_features(np.full(310,100.),270),{k:0 for k in analysis.PRICE})


if __name__=='__main__':unittest.main()
