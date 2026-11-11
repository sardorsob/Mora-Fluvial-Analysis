"""Calibration math and a complete run, independent of stream-event windows."""

import csv
import hashlib
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

    def test_cumulative_entry_below_known_incremental_doses_requires_new_preparation(self):
        rows = observations((0, 2, 6, 12), kind='incremental')
        rows[-1].update(addition_kind='cumulative', recorded_added_volume_ml='6')
        with self.assertRaisesRegex(ValueError, 'Cumulative volume decreases'):
            calibration.fit_calibration(preparation(), rows)

    def test_cumulative_entry_reestablishes_dose_after_missing_increment(self):
        rows = observations((0, 2, 6, 12, 14))
        rows[2].update(addition_kind='incremental', recorded_added_volume_ml='')
        fit, derived = calibration.fit_calibration(preparation(), rows)
        self.assertAlmostEqual(fit['k'], .25)
        self.assertIsNone(derived[2]['concentration'])
        self.assertEqual(derived[3]['cumulative_added_volume_ml'], 12)

    def test_recovery_reads_paired_native_values_without_replacing_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            records = Path(directory)
            original = records / 'calibration_points.csv'
            original.write_text('calibration_id,probe_alias,step_no,actual_conductivity_us_cm,'
                                'specific_conductivity_us_cm,temperature_c\nC01,,0,17.15,,8\n')
            source = records / 'native.csv'
            source.write_text('Device SN = 680530\nDate Time,Temperature (°C) (680530),'
                              'Actual Conductivity (µS/cm) (680530),Specific Conductivity (µS/cm) (680530)\n'
                              '2025-07-31 09:02:49,8.1,17.148,21.904\n')
            recovery = records / 'calibration_recovered_points.json'
            recovery.write_text(json.dumps({'schema_version': 1, 'sequences': [{
                'calibration_id': 'C01', 'probe_alias': '', 'sensor_serial': '680530',
                'source_csv': {'path': 'native.csv', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()},
                'points': [{'step_no': '0', 'source_line': 3, 'local_timestamp': '2025-07-31 09:02:49'}],
            }]}))
            rows, pins = calibration.read_calibration_points(records, recovery_path=recovery, root=records)
            self.assertEqual(rows[0]['actual_conductivity_us_cm'], '17.15')
            self.assertEqual(rows[0]['specific_conductivity_us_cm'], '21.904')
            self.assertEqual(rows[0]['temperature_c'], '8')
            self.assertEqual(rows[0]['native_temperature_c'], '8.1')
            self.assertEqual(rows[0]['native_measurement_source'], 'native.csv#L3')
            self.assertEqual(set(pins), {recovery.resolve(), source.resolve()})
            self.assertTrue(original.read_text().endswith('C01,,0,17.15,,8\n'))
            source.write_text(source.read_text().replace('21.904', '22.904'))
            with self.assertRaisesRegex(ValueError, 'Native calibration source hash mismatch'):
                calibration.read_calibration_points(records, recovery_path=recovery, root=records)

    def test_recovered_recipes_keep_notebook_and_worksheet_dose_series_separate(self):
        records = calibration.DEFAULT_RECORDS
        prep = calibration._read_csv(records / 'calibrations.csv')
        original = calibration._read_csv(records / 'calibration_points.csv')
        provenance = json.loads((records / 'provenance.json').read_text())
        updated, points, pins, identities = calibration.apply_recipe_recovery(
            prep, original, provenance, calibration.RECIPE_RECOVERY)
        by_id = {p['calibration_id']: p for p in updated}

        def series(identity):
            return [p for p in points if p['calibration_id'] == identity]

        pr03 = 'PAR-20260903-C01'
        fit, derived = calibration.fit_calibration(by_id[pr03], series(pr03))
        self.assertEqual(fit['stock_concentration'], 5000)
        self.assertAlmostEqual(fit['k'], .439262763056772)
        self.assertEqual(derived[-1]['calculated_vessel_volume_ml'], 324.6)
        self.assertFalse(by_id[pr03]['incompatible_notebook_version'])

        pr06 = 'PAR-20260903-C04'
        fit, derived = calibration.fit_calibration(by_id[pr06], series(pr06))
        self.assertEqual([p['cumulative_added_volume_ml'] for p in derived], [0, 2, 6, 10, 14, 18, 22, 26])
        self.assertAlmostEqual(derived[-1]['concentration'], 130000 / 409.3)
        self.assertTrue(by_id[pr06]['incompatible_notebook_version'])
        self.assertEqual(identities[pr06]['device_serial'], '607927')
        self.assertEqual(len([p for p in original if p['calibration_id'] == pr06]), 7)
        self.assertEqual(len(pins), 2)

        nisq = 'NISQ-20250717-C01'
        fit, _ = calibration.fit_calibration(by_id[nisq], series(nisq))
        self.assertEqual(fit['concentration_unit'], 'mg/L')
        self.assertEqual(fit['stock_concentration'], 2000)
        self.assertEqual(by_id[nisq]['stock_water_source'], 'unknown')
        self.assertEqual(next(p for p in prep if p['calibration_id'] == nisq)['procedure_id'], 'solution_secondary')

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
