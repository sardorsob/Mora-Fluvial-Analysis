import unittest

import matplotlib.pyplot as plt

from salt_dilution.scripts.processing import plot_discharge_pulses as pulses
from salt_dilution.scripts.processing import plot_discharge_summary as summary


class DischargePlotTests(unittest.TestCase):
    def test_actual_primary_is_one_release_and_one_channel_point(self):
        primary = [dict(trial_id='PAR-20260901-T01', logical_recording_id='REC-a',
                        conductivity_basis='actual', q_primary_m3_s='1.25', q_actual_comparison_m3_s='1.25')]
        self.assertEqual(summary._channel_points(primary), [(0, 'actual', 1.25)])

    def test_specific_primary_keeps_actual_comparison_without_adding_a_release(self):
        primary = [dict(trial_id='NISQ-20261004-T02', logical_recording_id='REC-a',
                        conductivity_basis='specific', q_primary_m3_s='2.04', q_actual_comparison_m3_s='2.19')]
        self.assertEqual(summary._channel_points(primary), [(0, 'specific', 2.04), (0, 'actual', 2.19)])
        with self.assertRaisesRegex(ValueError, 'duplicate release'):
            summary._channel_points(primary * 2)

    def test_no_q_counts_are_separate_from_proposed_and_practice(self):
        common = dict(site_alias='PAR', field_date='2026-09-01')
        rows = [dict(common, trial_id='T01', q_primary_m3_s='1.25', case_disposition='estimated_proposed'),
                dict(common, trial_id='T02', q_primary_m3_s='', case_disposition='capture_blocked'),
                dict(common, trial_id='T03', q_primary_m3_s='', case_disposition='excluded_practice'),
                dict(common, trial_id='T04', q_primary_m3_s='.05', case_disposition='estimated_proposed',
                     estimate_support='conditional_calibration_variant')]
        self.assertEqual(summary._recovery_counts(rows), {('2026-09-01', 'PAR'): (1, 1, 1, 1)})

    def test_sites_get_independent_scales_and_conditional_worksheet_marks_are_open(self):
        primary = [
            dict(trial_id='PAR-20260901-T01', site_alias='PAR', field_date='2026-09-01',
                 conductivity_basis='specific', q_primary_m3_s='.05', q_actual_comparison_m3_s='.06',
                 estimate_support='conditional_calibration_variant'),
            dict(trial_id='NISQ-20261004-T02', site_alias='NISQ', field_date='2026-10-04',
                 conductivity_basis='specific', q_primary_m3_s='2.04', q_actual_comparison_m3_s='2.19'),
        ]
        fig = summary._comparison(primary)
        self.addCleanup(plt.close, fig)
        nisqually, paradise = fig.axes
        self.assertGreater(nisqually.get_xlim()[1], 2.19)
        self.assertLess(paradise.get_xlim()[1], .1)
        self.assertEqual(len(paradise.collections), 2)
        self.assertTrue(all(len(mark.get_facecolors()) == 0 for mark in paradise.collections))

    def test_pulse_caption_names_both_worksheet_and_nominal_mass_assumptions(self):
        status, note = pulses._estimate_caption(dict(estimate_support='conditional_calibration_variant',
                                                    nominal_equals_delivered_mass_assumed='true'))
        self.assertEqual(status, 'Conditional')
        self.assertIn('alternate calibration worksheet', note)
        self.assertIn('Nominal salt mass assumed delivered', note)
        status, note = pulses._estimate_caption(dict(estimate_support='conditional_reported_volume'))
        self.assertEqual(status, 'Conditional')
        self.assertIn('Reported solution volume assumed delivered', note)

    def test_pulse_clock_label_requires_explicit_effective_evidence(self):
        self.assertEqual(pulses._clock_label({}), 'Recorded field clock')
        evidence = dict(effective_measurement_basis='participant_confirmed_fixed_field_offset',
                        effective_offset_seconds=-28800, encoded_offset_conflict=True)
        self.assertEqual(pulses._clock_label(evidence), 'Field time (PST, UTC−08:00)')

    def test_blocked_capture_headline_uses_plain_language(self):
        self.assertEqual(pulses._blocked_label('pulse_truncated'), 'Pulse end not established')
