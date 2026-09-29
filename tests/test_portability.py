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

    def test_config_resolves_inputs_from_an_unrelated_working_directory(self):
        module_file = ROOT / 'salt_dilution/scripts/processing/dilution_calculations.py'
        self.assertTrue(module_file.is_file(), 'The relocated dilution module is missing')
        dilution = importlib.import_module('salt_dilution.scripts.processing.dilution_calculations')
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as temp:
            try:
                os.chdir(temp)
                files, _, _ = dilution.load_config(ROOT / 'salt_dilution/config/2025-07-24_trial_01.ini')
                inputs = dilution.get_file_paths(files['data_folder'], files['search_string'])
                self.assertEqual([Path(p).name for p in inputs], ['20250724_162611_840058.csv'])
                self.assertTrue(Path(files['calibration_file']).is_file())
            finally:
                os.chdir(previous)

    def test_parser_modules_can_be_launched(self):
        folder = ROOT / 'salt_dilution/scripts/parsers'
        self.assertTrue(folder.is_dir(), 'The relocated parsers are missing')
        for name in ['parse_aquatroll_filename_cli', 'parse_aquatroll_metadata_cli']:
            result = subprocess.run(
                [sys.executable, '-m', f'salt_dilution.scripts.parsers.{name}', '--help'],
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
