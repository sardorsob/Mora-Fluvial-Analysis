"""Review tests use hand-computed pulses and independently written source bundles."""
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from salt_dilution.scripts.processing import discharge_review as review
from salt_dilution.scripts.processing import matching


def pulse_frame():
    return pd.DataFrame(dict(
        timestamp=pd.date_range('2026-10-04 09:00', periods=7, freq='s'),
        t_s=[0., 1., 2., 3., 4., 5., 6.], ec=[10., 10., 10., 16., 10., 10., 10.],
        segment=[0] * 7,
    ))


class NumericalReviewTests(unittest.TestCase):
    def test_observed_area_is_saved_without_inventing_quantity_or_q(self):
        windows = dict(pre=[0, 1], pulse=[2, 4], post=[5, 6])
        result = review.diagnostic_pulse_area(pulse_frame(), windows)
        self.assertEqual(result['integral_us_cm_s'], 6.)
        self.assertEqual(result['background_pre_integral_us_cm_s'], 6.)
        self.assertNotIn('q_m3_s', result)
        self.assertFalse(result['scientifically_accepted'])
        frame = pulse_frame(); frame.loc[3:, 'segment'] = 1
        with self.assertRaisesRegex(ValueError, 'gap'):
            review.diagnostic_pulse_area(frame, windows)

    def test_release_requirements_cover_every_blank_without_overwriting_first_stop(self):
        master = [dict(trial_id='T1', category='computed', q_primary_m3_s='4'),
                  dict(trial_id='T2', category='blocked_no_pre_pulse_background', q_primary_m3_s='')]
        source = dict(trial_id='T2', blocking_factors=['delivered_quantity_unknown'],
                      quantity_evidence='Spill recorded', calibration_evidence='Unverified serial',
                      capture_evidence='Local pulse recovered', needed_for_selected_q='Delivered amount',
                      recoverable_now='Observed area only', evidence_refs=['records.csv#T2'])
        row, = review.release_requirements([source], master)
        self.assertEqual(row['pipeline_first_stop'], 'blocked_no_pre_pulse_background')
        self.assertEqual(row['blocking_factors'], ['delivered_quantity_unknown'])
        with self.assertRaisesRegex(ValueError, 'missing'):
            review.release_requirements([], master)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            review.release_requirements([source, source], master)

    def test_capture_assumed_scenario_retains_exact_fit_reference_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            for name in ('calibration_fits.csv','run_info.json','observed.csv'):
                (root/name).write_text('source fixture')
            source=dict(path='observed.csv',sha256=matching._hash(root/'observed.csv'))
            case=dict(trial_id='T',logical_recording_id='R',channel='specific',pre=[0,1],pulse=[2,4],
                background_mode='pre',scenario='capture_assumed_observed_interval',
                qualification='Capture assumed, not established',evidence='Reviewed waveform',source_processed=source)
            path=root/'conditional.json';path.write_text(json.dumps(dict(schema_version=1,cases=[case])))
            fit=dict(calibration_id='C',probe_alias='',conductivity_basis='specific',calibration_basis='mass_concentration',
                concentration_unit='mg/L',coefficient_unit='(mg/L) / (uS/cm)',k='.4')
            edge=dict(fit,trial_id='T',recording_edge_id='E',status='supported',fit_reference=json.dumps(dict(
                key=['C','','specific'],fit_table_sha256=matching._hash(root/'calibration_fits.csv'),
                run_info_sha256=matching._hash(root/'run_info.json'))))
            key=('T','R','specific')
            row,=review._conditional_cases(path,
                {key:dict(recording_edge_id='E',calibration_edge_id='K',outcome='blocked')},
                {key:pulse_frame()},
                {('T',):dict(category='blocked_tail',mass_confirmation_status='confirmed_delivered',confirmed_delivered_mass_g='12')},
                {('T',):dict(field_date='2026-10-04')},{('K',):edge},{('C','','specific'):fit},
                {('E',):dict(member_refs='["F"]')},{'F':dict(files=dict(processed=source))},
                root,{str(root/'observed.csv'):source['sha256']},root)
            self.assertEqual(row['k'],'.4')
            self.assertAlmostEqual(row['q_m3_s'],5)
            self.assertIn('below_ideal_nacl_reference',row['flags'])
            self.assertIn('not a correction',row['calibration_reference_assumptions'])
            self.assertEqual(row['scenario'],'capture_assumed_observed_interval')
            self.assertFalse(row['scientifically_accepted'])

    def test_recompute_mass_and_original_injectate_q(self):
        windows = dict(pre=[0, 1], pulse=[2, 4], post=[5, 6])
        for method, quantity, unit in (
            ('mass_slug', dict(mass_g='12', k='.5'), '(mg/L) / (uS/cm)'),
            ('solution_slug', dict(injection_solution_volume_ml='12000', k='.0005'), '(mL/mL) / (uS/cm)'),
        ):
            with self.subTest(method=method):
                row = dict(trial_id='trial', discharge_method=method, coefficient_unit=unit,
                           background_mode='linear', integral_us_cm_s='6', q_m3_s='4',
                           q_l_s='4000', **quantity)
                area, q, _ = review.recompute_estimate(pulse_frame(), windows, row)
                self.assertEqual((area, q), (6, 4))
                with self.assertRaisesRegex(ValueError, 'disagrees'):
                    review.recompute_estimate(pulse_frame(), windows, dict(row, q_m3_s='3'))

    def test_documented_pause_is_retained_in_window_scenarios(self):
        frame = pulse_frame()
        frame['t_s'] = [0., 1., 32., 33., 34., 35., 36.]
        frame['segment'] = [0, 0, 1, 1, 1, 1, 1]
        windows = dict(pre=[0, 1], pulse=[32, 34], post=[35, 36],
                       pre_injection_pause=dict(release_offset_s=32, evidence='logger note', background_applicable=True))
        estimate = dict(trial_id='trial', mass_g='12', k='.5', q_m3_s='4',
                        coefficient_unit='(mg/L) / (uS/cm)')
        scenarios, _ = review.window_sensitivity(frame, windows, estimate)
        self.assertTrue(scenarios)
        self.assertTrue(all(row['pre_injection_pause'] == windows['pre_injection_pause'] for row in scenarios))

    def test_conditional_observed_area_preserves_signed_excess_and_rejects_gap(self):
        frame = pulse_frame()
        frame.loc[4, 'ec'] = 8.
        area, background = review.observed_area(frame, [0, 1], [2, 4])
        self.assertEqual((area, background), (5, 10))
        frame.loc[4:, 'segment'] = 1
        with self.assertRaisesRegex(ValueError, 'gap'):
            review.observed_area(frame, [0, 1], [2, 4])

    def test_stage_diagnostic_preserves_native_parameter_unit_and_missingness(self):
        samples = pulse_frame().drop(columns='t_s')
        samples['Pressure (psi) (790481)'] = [1., 1., 1., 2., 3., 3., 3.]
        samples['Depth (ft)'] = [1., 1., 1., 2., 3., None, 3.]
        samples['Unknown pressure correction (psi)'] = 5.
        windows = dict(pre=[0, 1], pulse=[2, 4], post=[5, 6])
        diagnostics = list(review.stage_diagnostics(samples, windows))
        self.assertEqual([r['parameter'] for r in diagnostics], ['Pressure', 'Depth'])
        self.assertEqual((diagnostics[0]['unit'], diagnostics[0]['change']), ('psi', 2.))
        self.assertIsNone(diagnostics[1]['change'])


class BundlePinTests(unittest.TestCase):
    def test_review_evidence_must_match_its_source_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'source.csv'; source.write_text('amount\n12\n')
            item = dict(path='source.csv', sha256=matching._hash(source))
            pins = {}; review.pin_review_sources([item], pins, root)
            self.assertEqual(pins[str(source.resolve())], item['sha256'])
            source.write_text('amount\n13\n')
            with self.assertRaisesRegex(ValueError, 'source hash'):
                review.pin_review_sources([item], pins, root)

    def test_mass_run_must_reference_selected_pairing_and_calibration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cal, pair, mass, output = [root / name for name in ('cal', 'pair', 'mass', 'review')]
            for path in (cal, pair, mass):
                path.mkdir()
                (path / 'run_info.json').write_text(json.dumps(dict(inputs=[], outputs=[])))
            with self.assertRaisesRegex(ValueError, 'Mass run does not pin.*pair'):
                review.run_review(mass, pair, cal, output, root=root)
            self.assertFalse(output.exists())

    def test_changed_bundle_fails_before_writing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mass = root / 'mass'
            mass.mkdir()
            table = mass / 'discharge_estimates.csv'
            table.write_text('trial_id\n')
            (mass / 'run_info.json').write_text(json.dumps(dict(inputs=[], outputs=[
                dict(path=table.name, sha256=matching._hash(table)),
            ])))
            table.write_text('trial_id\nchanged\n')
            output = root / 'review'
            with self.assertRaisesRegex(ValueError, 'Stale.*hash'):
                review.run_review(mass, root/'pair', root/'cal', output, root=root)
            self.assertFalse(output.exists())


class CalibrationChannelTests(unittest.TestCase):
    def test_temperature_comparison_requires_matched_measured_dose_sets(self):
        key = ('C01', 'probe')
        actual = dict(conductivity_basis='actual', calibration_basis='mass_concentration',
                      k='0.5', n_points='3')
        specific = dict(actual, conductivity_basis='specific', k='0.4')
        fits = {(*key, 'actual'): actual, (*key, 'specific'): specific}
        temperatures = {(*key, 'actual'): {'1': 15., '2': 15., '3': 15.},
                        (*key, 'specific'): {'1': 15., '2': 15., '4': 15.}}
        row, = review.channel_consistency(fits, temperatures)
        self.assertEqual(row['diagnostic_status'], 'not_comparable')
        self.assertIn('different_or_unverified_step_sets', row['flags'])
        temperatures[(*key, 'specific')] = {'1': 15., '2': 15., '3': 15.}
        row, = review.channel_consistency(fits, temperatures)
        self.assertEqual(row['paired_temperature_c'], 15.)
        self.assertAlmostEqual(row['implied_temperature_c'], 14.52879581)
        temperatures[(*key, 'specific')]['1'] = None
        row, = review.channel_consistency(fits, temperatures)
        self.assertIn('paired_temperature_unavailable', row['flags'])
