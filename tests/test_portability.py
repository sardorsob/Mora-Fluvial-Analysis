"""Checks for relocated imports, configuration inputs, and run output paths.

Run from the repository root: python -m unittest discover -s tests -v
"""

import ast
import contextlib
import importlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class PortabilityTests(unittest.TestCase):
    def test_public_acquisition_setup_needs_no_embedded_credentials(self):
        # Exercise the real function with a network-boundary stand-in because
        # ObsPy and live acquisition are not needed for this empty interval.
        source = ROOT / 'fluvial_seismology/scripts/processing/download_waveforms.py'
        function = next(n for n in ast.parse(source.read_text()).body
                        if isinstance(n, ast.FunctionDef) and n.name == 'get_iris_data')

        class PublicClient:
            def __init__(self, **kwargs):
                pass

            def set_credentials(self, *args):
                raise AssertionError('Public acquisition must not apply credentials')

        namespace = {'os': os, 'fdsn': SimpleNamespace(client=SimpleNamespace(Client=PublicClient))}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {}, clear=True):
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                namespace['get_iris_data'](0, 0, ['ZE.2411..GPZ'], temp)
            self.assertIn('Data retrieval and saving completed.', captured.getvalue())

    def test_parser_module_can_be_launched(self):
        folder = ROOT / 'salt_dilution/scripts/parsers'
        self.assertTrue(folder.is_dir(), 'The relocated parsers are missing')
        result = subprocess.run(
            [sys.executable, '-m', 'salt_dilution.scripts.parsers.parse_data', '--help'],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--output', result.stdout)

    def test_output_paths_stay_within_the_named_run(self):
        self.assertTrue((ROOT / 'project_paths.py').is_file(), 'The portable path helper is missing')
        paths = importlib.import_module('project_paths')
        with tempfile.TemporaryDirectory() as temp, patch.object(paths, 'ROOT', Path(temp)):
            with patch.dict(os.environ, {'MORA_RUN_ID': 'test_run'}):
                output = Path(paths.result_path('salt_dilution', 'figures/calibration.png'))
                self.assertEqual(output, Path(temp).resolve() / 'salt_dilution/results/test_run/figures/calibration.png')
                self.assertTrue(output.parent.is_dir())
                self.assertTrue((output.parents[1] / 'run_info.json').is_file())
                with self.assertRaises(ValueError):
                    paths.result_path('salt_dilution', '../../outside.csv')
            with patch.dict(os.environ, {'MORA_RUN_ID': '../outside'}):
                with self.assertRaises(ValueError):
                    paths.result_path('salt_dilution', 'tables/discharge.csv')


if __name__ == '__main__':
    unittest.main()
