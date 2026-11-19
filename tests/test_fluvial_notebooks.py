"""Regression checks for arrival-pick screening in both calibration notebooks."""

import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd


NOTEBOOKS = (
    "estimate_greens_velocities.ipynb",
    "estimate_n11_hammer_p_wave_velocity.ipynb",
)
CALIBRATION = (
    Path(__file__).resolve().parents[1]
    / "fluvial_seismology/notebooks/instrument_calibration"
)


def residual_screening_cell(notebook: str) -> str:
    """Read the executable cell from the saved notebook."""
    cells = json.loads((CALIBRATION / notebook).read_text(encoding="utf-8"))["cells"]
    return next(
        "".join(cell["source"])
        for cell in cells
        if cell["cell_type"] == "code" and "slope_qc, intercept_qc = np.polyfit" in "".join(cell["source"])
    )


class ResidualScreeningTests(unittest.TestCase):
    def screen(self, notebook: str, dx: list[float], *, fixed_fit: bool = True) -> dict:
        """Run the screening cell with synthetic, aligned shot inputs."""
        count = len(dx)
        times = pd.date_range("2025-01-01", periods=count, freq="s")
        namespace = {
            "np": np,
            "pd": pd,
            "plt": Mock(),
            "dt": pd.Series(np.arange(count) * 0.005),
            "dx": pd.Series(dx, dtype=float),
            "og_node_t": pd.DataFrame({"t1": times}),
            "calib_node_t": pd.DataFrame({"t2": times}),
            "og_node_x": pd.DataFrame({"x1": np.arange(count)}),
            "calib_node_x": pd.DataFrame({"x2": 10 - np.arange(count)}),
        }
        with redirect_stdout(io.StringIO()), patch.object(pd.DataFrame, "to_csv"):
            if fixed_fit:
                with patch.object(np, "polyfit", return_value=(0.0, 0.0)):
                    exec(residual_screening_cell(notebook), namespace)
            else:
                exec(residual_screening_cell(notebook), namespace)
        return namespace

    def test_zero_residuals_produce_zero_scores(self):
        for notebook in NOTEBOOKS:
            with self.subTest(notebook=notebook):
                result = self.screen(notebook, [0.0] * 4, fixed_fit=False)
                self.assertEqual(result["mad_resid"], 1e-9)
                np.testing.assert_array_equal(result["modified_z"], [0.0] * 4)
                self.assertTrue(result["flagged"].empty)

    def test_constant_residuals_use_median_magnitude(self):
        for notebook in NOTEBOOKS:
            with self.subTest(notebook=notebook):
                result = self.screen(notebook, [-2.0] * 4)
                self.assertEqual(result["mad_resid"], 2.0)
                np.testing.assert_array_equal(result["modified_z"], [0.0] * 4)

    def test_primary_scale_and_flagging_threshold_are_preserved(self):
        for notebook in NOTEBOOKS:
            with self.subTest(notebook=notebook):
                result = self.screen(notebook, [0.0, 0.0, 0.0, 4.0])
                self.assertEqual(result["mad_resid"], 1.0)
                self.assertEqual(result["mad_threshold"], 1.75)
                np.testing.assert_array_equal(result["modified_z"], [0.0, 0.0, 0.0, 4.0])
                self.assertEqual(result["flagged"]["shot_index"].tolist(), [3])

    def test_nonfinite_primary_scale_uses_finite_median_magnitude(self):
        for notebook in NOTEBOOKS:
            with self.subTest(notebook=notebook), np.errstate(over="ignore"):
                result = self.screen(notebook, [-1e308, -1e308, 0.0, 1e308, 1e308])
                self.assertEqual(result["mad_resid"], 1e308)
                np.testing.assert_array_equal(result["modified_z"], [1.0, 1.0, 0.0, 1.0, 1.0])

    def test_missing_or_infinite_residuals_stop_screening(self):
        for notebook in NOTEBOOKS:
            for invalid in (np.nan, np.inf):
                with self.subTest(notebook=notebook, invalid=invalid):
                    with self.assertRaisesRegex(ValueError, "finite residuals"):
                        self.screen(notebook, [0.0, 1.0, 2.0, invalid])


class ArrivalPickerTests(unittest.TestCase):
    def test_aic_pickers_skip_undefined_splits(self):
        path = CALIBRATION / "test_arrival_pickers.ipynb"
        cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
        definitions = [
            node
            for cell in cells
            if cell["cell_type"] == "code" and "def aic_picker(" in "".join(cell["source"])
            for node in ast.parse("".join(cell["source"])).body
            if isinstance(node, ast.FunctionDef) and node.name == "aic_picker"
        ]
        self.assertEqual(len(definitions), 3)
        counts = np.array([0, 8, 0, 8, 100, 170, -100, 20])
        candidates = range(2, len(counts) - 1)
        expected = min(candidates, key=lambda i: (
            i * np.log(np.var(counts[:i]))
            + (len(counts) - i - 1) * np.log(np.var(counts[i:]))
        ))
        for index, definition in enumerate(definitions):
            with self.subTest(definition=index):
                namespace = {"np": np}
                exec(compile(ast.Module(body=[definition], type_ignores=[]), str(path), "exec"), namespace)
                picker = namespace["aic_picker"]
                pick, scores = picker(counts)
                self.assertEqual(pick, expected)
                self.assertTrue(np.isinf(scores[[0, 1, -1]]).all())
                pick, scores = picker(np.full(8, 20))
                self.assertIsNone(pick)
                self.assertTrue(np.isinf(scores).all())
