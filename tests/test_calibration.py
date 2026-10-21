"""Calibration math and a complete run, independent of stream-event windows."""

import csv
import json
from pathlib import Path
import tempfile
import unittest

from salt_dilution.scripts.processing import calibration


def preparation(identity='C01', procedure='mass_stock_river'):
    return dict(calibration_id=identity, procedure_id=procedure, stock_salt_mass_g='1',
                stock_water_initial_ml='1000', stock_solution_final_ml='',
                calibration_water_initial_ml='2000', injectate_aliquot_ml='10',
                secondary_water_initial_ml='1000', review_status='needs_review')


def observations(volumes=(0, 2, 6, 12), *, identity='C01', kind='cumulative'):
    total = 0
    rows = []
    for step, volume in enumerate(volumes):
        total = total + volume if kind == 'incremental' else volume
        concentration = 1000 * total / (2000 + total)
        ec = 40 + concentration / .25
        rows.append(dict(calibration_id=identity, step_no=str(step), probe_alias='',
                         recorded_added_volume_ml=str(volume), addition_kind=kind,
                         recorded_vessel_volume_ml=str(2000 + total),
                         specific_conductivity_us_cm=str(ec),
                         actual_conductivity_us_cm=str(ec * .8), sourcebook_reference='test'))
    return rows


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(calibration, 'fit_calibration', None)),
                        'calibration.py needs the calibration fitting function')

    def test_mass_fit_uses_recorded_water_when_final_volume_is_blank(self):
        fit, points = calibration.fit_calibration(preparation(), observations())
        self.assertAlmostEqual(fit['k'], .25)
        self.assertAlmostEqual(fit['intercept'], -10)
        self.assertAlmostEqual(fit['r_squared'], 1)
        self.assertEqual(fit['stock_volume_basis'], 'stock_water_initial_ml')
        self.assertEqual(fit['concentration_unit'], 'mg/L')
        self.assertAlmostEqual(points[-1]['concentration'], 1000 * 12 / 2012)

    def test_current_mass_profiles_do_not_require_measured_final_volume(self):
        profiles = json.loads(calibration.PROFILES.read_text())
        for name in ('mass_stock_river', 'mass_stock_deionized'):
            self.assertNotIn('stock_solution_final_ml', profiles[name]['required_calibration_fields'])
            self.assertIn('stock_water_initial_ml', profiles[name]['required_calibration_fields'])

    def test_measured_final_volume_can_be_used_without_changing_input(self):
        prep = preparation(); prep['stock_solution_final_ml'] = '2000'
        fit, _ = calibration.fit_calibration(prep, observations())
        self.assertAlmostEqual(fit['k'], .125)
        self.assertEqual(fit['stock_volume_basis'], 'stock_solution_final_ml')
        self.assertEqual(prep['stock_water_initial_ml'], '1000')

    def test_relative_concentration_uses_secondary_dilution(self):
        prep = preparation(procedure='solution_secondary')
        points = observations()
        for row in points:
            volume = float(row['recorded_added_volume_ml'])
            relative = (10 / 1010) * volume / (2000 + volume)
            row['specific_conductivity_us_cm'] = str(20 + relative / 2e-6)
        fit, derived = calibration.fit_calibration(prep, points)
        self.assertAlmostEqual(fit['k'], 2e-6, places=12)
        self.assertEqual(fit['concentration_unit'], 'mL/mL')
        self.assertAlmostEqual(derived[-1]['concentration'], (10 / 1010) * 12 / 2012)

    def test_unequal_increments_include_additions_without_conductivity(self):
        rows = observations((0, 2, 6, 6, 6, 6, 6, 6, 4, 4), kind='incremental')
        rows[2]['specific_conductivity_us_cm'] = ''
        fit, derived = calibration.fit_calibration(preparation(), rows)
        self.assertEqual(fit['n_points'], 9)
        self.assertEqual(derived[3]['cumulative_added_volume_ml'], 14)
        self.assertEqual(derived[-1]['cumulative_added_volume_ml'], 46)
        self.assertAlmostEqual(fit['k'], .25)

    def test_cumulative_additions_are_not_summed_again(self):
        _, derived = calibration.fit_calibration(preparation(), observations())
        self.assertEqual([p['cumulative_added_volume_ml'] for p in derived], [0, 2, 6, 12])

    def test_specific_channel_never_borrows_actual_observations(self):
        rows = observations()
        for row in rows:
            row['specific_conductivity_us_cm'] = ''
        with self.assertRaisesRegex(ValueError, 'specific'):
            calibration.fit_calibration(preparation(), rows)
        fit, _ = calibration.fit_calibration(preparation(), rows, conductivity_basis='actual')
        self.assertAlmostEqual(fit['k'], .3125)

    def test_missing_probe_does_not_block_a_provisional_fit(self):
        fit, _ = calibration.fit_calibration(preparation(), observations())
        self.assertEqual(fit['probe_alias'], '')
        self.assertEqual(fit['status'], 'provisional')

    def test_invalid_volumes_semantics_and_degenerate_fits_are_rejected(self):
        cases = []
        prep = preparation(); prep['stock_water_initial_ml'] = '0'
        cases.append((prep, observations()))
        rows = observations(); rows[1]['addition_kind'] = 'unconfirmed'
        cases.append((preparation(), rows))
        rows = observations(); rows[1]['recorded_added_volume_ml'] = '-1'
        cases.append((preparation(), rows))
        cases.append((preparation(), observations()[:2]))
        rows = observations()
        for row in rows: row['specific_conductivity_us_cm'] = '40'
        cases.append((preparation(), rows))
        rows = observations()
        for row in rows: row['specific_conductivity_us_cm'] = str(100 - float(row['specific_conductivity_us_cm']))
        cases.append((preparation(), rows))
        for prep, rows in cases:
            with self.subTest(preparation=prep, readings=rows), self.assertRaises(ValueError):
                calibration.fit_calibration(prep, rows)

    def test_vessel_disagreement_is_visible_without_replacing_observations(self):
        rows = observations(); rows[-1]['recorded_vessel_volume_ml'] = '2013'
        _, derived = calibration.fit_calibration(preparation(), rows)
        self.assertEqual(derived[-1]['vessel_volume_difference_ml'], 1)
        self.assertEqual(rows[-1]['recorded_vessel_volume_ml'], '2013')

    def test_runner_needs_no_trial_input_table_and_records_skips(self):
        self.assertTrue(callable(getattr(calibration, 'run_calibrations', None)))
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory); records = folder / 'records'; records.mkdir()
            preps = [preparation(), preparation('C02')]
            points = observations() + observations(identity='C02')
            for name, rows in [('calibrations', preps), ('calibration_points', points)]:
                with (records / (name + '.csv')).open('w', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                    writer.writeheader(); writer.writerows(rows)
            (records / 'provenance.json').write_text(json.dumps({'calibrations': {
                'C01': {'probe_alias': 'probe_01'},
                'C02': {'source_table_status': 'abandoned'}}}))
            output = folder / 'run'
            result = calibration.run_calibrations(records, output, conductivity_basis='both')
            self.assertEqual(result['fits'], 2)
            self.assertEqual(result['skipped_series'], 2)
            self.assertTrue((output / 'calibration_fits.csv').is_file())
            self.assertTrue((output / 'calibration_points.csv').is_file())
            self.assertTrue((output / 'calibration_skips.csv').is_file())
            self.assertTrue((output / 'figures/C01.png').is_file())
            with (output / 'calibration_points.csv').open(newline='') as stream:
                self.assertEqual({r['probe_alias'] for r in csv.DictReader(stream)}, {'probe_01'})
            info = json.loads((output / 'run_info.json').read_text())
            self.assertEqual(info['status'], 'complete_with_skips')
            self.assertTrue(info['inputs'])
            self.assertTrue(info['outputs'])
            with self.assertRaises(FileExistsError):
                calibration.run_calibrations(records, output)


if __name__ == '__main__':
    unittest.main()
