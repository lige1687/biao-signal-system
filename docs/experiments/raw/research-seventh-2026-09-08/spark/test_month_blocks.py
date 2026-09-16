"""Tests for month_blocks.draw_indices."""

from __future__ import annotations

import unittest

import numpy as np

from month_blocks import draw_indices


class TestMonthBlocks(unittest.TestCase):
    def test_validation_non_integer_and_bool(self) -> None:
        self.assertRaises(TypeError, draw_indices, False, 3, 2, 0)
        self.assertRaises(TypeError, draw_indices, 6, True, 2, 0)
        self.assertRaises(TypeError, draw_indices, 6, 3, 2.0, 0)
        self.assertRaises(TypeError, draw_indices, 6, 3, 2, True)
        self.assertRaises(TypeError, draw_indices, 6.0, 3, 2, 0)
        self.assertRaises(TypeError, draw_indices, 6, 3, "2", 0)

    def test_validation_ranges(self) -> None:
        self.assertRaises(ValueError, draw_indices, 0, 3, 2, 0)
        self.assertRaises(ValueError, draw_indices, 3, 0, 2, 0)
        self.assertRaises(ValueError, draw_indices, 3, 4, 2, 0)
        self.assertRaises(ValueError, draw_indices, 3, 1, 0, 0)

    def test_seed_deterministic(self) -> None:
        a = draw_indices(12, 4, 3, seed=123)
        b = draw_indices(12, 4, 3, seed=123)
        c = draw_indices(12, 4, 3, seed=124)
        self.assertTrue(np.array_equal(a, b))
        self.assertFalse(np.array_equal(a, c))

    def test_shape_dtype_and_bounds(self) -> None:
        months = 10
        block_length = 3
        repetitions = 4
        seed = 7
        result = draw_indices(months, block_length, repetitions, seed)
        self.assertEqual(result.shape, (repetitions, months))
        self.assertEqual(result.dtype, np.int64)
        self.assertTrue(np.issubdtype(result.dtype, np.integer))
        self.assertTrue(np.all((result >= 0) & (result < months)))

    def test_contiguous_blocks_property(self) -> None:
        months = 13
        block_length = 5
        reps = 2
        seed = 42
        result = draw_indices(months, block_length, reps, seed)
        blocks_per_row = int(np.ceil(months / block_length))

        for row in result:
            for block_idx in range(blocks_per_row):
                block = row[block_idx * block_length : (block_idx + 1) * block_length]
                if len(block) == 0:
                    continue
                # Last block may be truncated after concat.
                if block_idx == blocks_per_row - 1 and len(block) != block_length:
                    self.assertLessEqual(len(block), block_length)
                    self.assertTrue(np.all(block[1:] - block[:-1] == 1))
                else:
                    expected = np.arange(block[0], block[0] + len(block))
                    self.assertTrue(np.array_equal(block, expected))

    def test_last_block_truncated(self) -> None:
        months = 5
        block_length = 3
        reps = 1
        seed = 17
        expected = draw_indices(months, block_length, reps, seed)

        import numpy as np

        rng = np.random.default_rng(seed)
        starts = rng.integers(0, months - block_length + 1, size=(reps, 2))
        offsets = np.arange(block_length)
        direct = np.concatenate([starts[0, 0] + offsets, starts[0, 1] + offsets])[:months]

        self.assertTrue(np.array_equal(expected, direct[None, :]))

    def test_block_length_equal_months_full_range(self) -> None:
        months = 9
        block_length = months
        reps = 3
        seed = 9
        result = draw_indices(months, block_length, reps, seed)
        self.assertTrue(np.all(result[0] == np.arange(months)))
        self.assertTrue(np.all(result[1] == np.arange(months)))
        self.assertTrue(np.all(result[2] == np.arange(months)))

    def test_block_length_one(self) -> None:
        months = 1
        block_length = 1
        reps = 5
        seed = 11
        result = draw_indices(months, block_length, reps, seed)
        self.assertEqual(result.shape, (reps, months))
        self.assertTrue(np.all(result == 0))
