"""Synthetic checks only. Never prepare market observations or fit models."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import sys
from unittest import mock

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / 'synthetic-fixtures'
spec = importlib.util.spec_from_file_location('aaii_dynamics_analysis', HERE / 'analysis.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class SyntheticFeatures(unittest.TestCase):
    @staticmethod
    def frame(values, missing=()):
        dates = pd.date_range('2020-01-02', periods=len(values) + len(missing), freq='7D')
        dates = dates.delete(list(missing))
        return pd.DataFrame({'date': dates.strftime('%Y-%m-%d'),
                             'bull_bear': np.asarray(values, dtype=float) / 100})

    def test_continuous_prefix_and_threshold_equality(self):
        values = [0] * 20 + [-25, -24.999999999, -25, -26, -24.999999999, 4]
        frame = self.frame(values)
        got = analysis.dynamic_features(frame)
        self.assertTrue(got.m20.iloc[:19].isna().all())
        self.assertEqual(got.m20.iloc[19], 0)
        self.assertEqual(got.d4.iloc[19], 0)
        self.assertEqual(got.exit_pessimism.iloc[20], 0)
        self.assertEqual(got.exit_pessimism.iloc[21], 1)
        self.assertEqual(got.exit_pessimism.iloc[22], 0)
        self.assertEqual(got.exit_pessimism.iloc[24], 1)
        self.assertEqual(got.exit_pessimism.iloc[25], 0)
        self.assertEqual(got.neg_run.iloc[20], 1)
        self.assertEqual(got.neg_run.iloc[21], 2)
        self.assertEqual(got.neg_run.iloc[25], 0)
        extended = pd.concat([frame, self.frame([100, 101]).assign(
            date=['2020-07-02', '2020-07-09'])], ignore_index=True)
        future = analysis.dynamic_features(extended)
        for col in ['m20', 'd4', 'neg_run', 'exit_pessimism']:
            np.testing.assert_allclose(got[col], future[col].iloc[:len(frame)], equal_nan=True)

    def test_initial_left_censor_and_gap_anchor(self):
        values = [-2, -3, 0, -1, -2, -5, -6, 0, -1] + [1] * 20
        frame = self.frame(values, missing=(5,))
        got = analysis.dynamic_features(frame)
        self.assertTrue(np.isnan(got.neg_run.iloc[0]))
        self.assertTrue(np.isnan(got.neg_run.iloc[1]))
        self.assertEqual(got.neg_run.iloc[2], 0)
        self.assertEqual(got.neg_run.iloc[3], 1)
        self.assertEqual(got.neg_run.iloc[4], 2)
        self.assertTrue(np.isnan(got.neg_run.iloc[5]))
        self.assertTrue(np.isnan(got.neg_run.iloc[6]))
        self.assertEqual(got.neg_run.iloc[7], 0)
        self.assertEqual(got.neg_run.iloc[8], 1)
        self.assertTrue(np.isnan(got.exit_pessimism.iloc[5]))
        self.assertTrue(np.isnan(got.d4.iloc[5:9]).all())
        self.assertTrue(np.isnan(got.m20.iloc[19:24]).all())
        self.assertTrue(np.isfinite(got.m20.iloc[24]))

    def test_single_old_archive_missing_quote_label_mapping(self):
        f = analysis.old_extremes_exclusion_equal
        self.assertTrue(f('no_observation_quote', 'no_quote_after_assumed_date', 2037))
        self.assertTrue(f('nonfinite_x_or_baseline', 'nonfinite_x_or_baseline', 10))
        self.assertFalse(f('no_observation_quote', 'no_quote_after_assumed_date', 2036))
        self.assertFalse(f('other', 'no_quote_after_assumed_date', 2037))
        self.assertFalse(f('no_observation_quote', 'other', 2037))

    def test_duplicate_or_unordered_week_rejected(self):
        frame = self.frame([1, 2, 3])
        frame.loc[1, 'date'] = frame.loc[0, 'date']
        with self.assertRaises(ValueError):
            analysis.dynamic_features(frame)

    def test_intercept_only_kernel_on_synthetic_rows(self):
        train = pd.DataFrame({'asset': ['SPY'] * 4, 'y': [1.0, 2.0, 3.0, 4.0],
                              'features': [{}] * 4})
        evaluation = pd.DataFrame({'asset': ['SPY'], 'features': [{}]})
        design = analysis._ols_design(train, evaluation, [], 'equal_asset')
        self.assertEqual(design['rank'], 0)
        prediction, detail = analysis._ols_fit(train, design)
        self.assertAlmostEqual(float(prediction[0]), 2.5)
        self.assertEqual(detail['training_rows'], 4)

    def test_fit_refuses_missing_freeze_before_any_market_work(self):
        with mock.patch.object(analysis, 'prepare', return_value=({'sources': []}, None, None, None, None)):
            with mock.patch.object(analysis, 'require_freeze', side_effect=RuntimeError('freeze missing')):
                with self.assertRaisesRegex(RuntimeError, 'freeze missing'):
                    analysis.fit()

    def test_prepare_only_does_not_create_run_or_fit(self):
        FIXTURES.mkdir(exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix='synthetic-prepare-', dir=FIXTURES))
        with mock.patch.object(analysis, 'HERE', root), mock.patch.object(analysis, 'OUT', root / 'run-01'):
                with mock.patch.object(analysis, 'prepare', return_value=({'models': {'I': []}}, None, None, [], {})):
                    with mock.patch.object(analysis, 'fit', side_effect=AssertionError('fit called')):
                        with mock.patch.object(sys, 'argv', ['analysis.py', '--prepare-only']):
                            analysis.main()
        self.assertFalse((root / 'run-01').exists())

    def test_new_output_will_not_overwrite(self):
        FIXTURES.mkdir(exist_ok=True)
        root = Path(tempfile.mkdtemp(prefix='synthetic-output-', dir=FIXTURES))
        path = root / 'preflight.json'
        analysis.write_new(path, {'status': 'prepared_no_fit'})
        with self.assertRaises(FileExistsError):
            analysis.write_new(path, {'status': 'overwrite'})


if __name__ == '__main__':
    unittest.main()
