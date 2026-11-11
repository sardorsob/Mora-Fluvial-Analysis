import unittest

import matplotlib.pyplot as plt
import pandas as pd

from salt_dilution.scripts.processing import plot_discharge_working as plots


class WorkingDischargePlotTests(unittest.TestCase):
    def fixture(self):
        release=dict(trial_id='NISQ-20250805-T01',field_date='2025-08-05',site_alias='NISQ',category='not_estimable')
        estimate=dict(trial_id=release['trial_id'],recording_edge_id='E1',sensor_serial='123',
            conductivity_basis='specific',calibration_id='C01',calibration_series_alias='probe_01',
            window_id='w1',recipe_id='r1',q_m3_s='4',mass_g='4000',k='.5',integral_us_cm_s='2000',
            coefficient_unit='(mg/L) / (uS/cm)',result_class='assumption_conditional')
        return release,estimate

    def test_every_calibration_and_channel_kept_without_averaging(self):
        release,row=self.fixture()
        second=dict(row,calibration_id='C02',k='1',q_m3_s='2')
        actual=dict(row,conductivity_basis='actual',k='.8',q_m3_s='2.5')
        points=plots.combine_estimates([], [row,second,actual], [release])
        self.assertEqual([p['q_m3_s'] for p in points],[4,2,2.5])
        self.assertTrue(all(p['status']=='working_conditional' for p in points))

    def test_unit_response_never_becomes_discharge(self):
        release,row=self.fixture();row.update(result_class='unit_response',q_m3_s='',q_m3_s_per_delivered_litre='4')
        self.assertEqual(plots.combine_estimates([],[row],[release]),[])
        row['q_m3_s']='4'
        with self.assertRaisesRegex(ValueError,'Unit response'):
            plots.combine_estimates([],[row],[release])

    def test_duplicate_overlapping_and_inconsistent_estimates_rejected(self):
        release,row=self.fixture()
        with self.assertRaisesRegex(ValueError,'Duplicate estimate'):
            plots.combine_estimates([],[row,row],[release])
        with self.assertRaisesRegex(ValueError,'overlap'):
            plots.combine_estimates([row],[row],[release])
        with self.assertRaisesRegex(ValueError,'Saved Q'):
            plots.combine_estimates([],[dict(row,q_m3_s='5')],[release])
        with self.assertRaisesRegex(ValueError,'Unknown coefficient'):
            plots.combine_estimates([],[dict(row,coefficient_unit='unknown')],[release])

    def test_solution_volume_route_uses_cubic_metres(self):
        release,row=self.fixture();row.update(coefficient_unit='(mL/mL) / (uS/cm)',k='.000002',
            injection_solution_volume_ml='12000',mass_g='',q_m3_s='3')
        self.assertEqual(plots.combine_estimates([],[row],[release])[0]['q_m3_s'],3)

    def test_plot_omits_missing_q_marks_and_keeps_conditional_mark_open(self):
        release,row=self.fixture();points=plots.combine_estimates([],[row],[release])
        missing=dict(release,trial_id='NISQ-20250903-T02',field_date='2025-09-03')
        fig=plots.comparison(points,[release,missing],'NISQ','2025');self.addCleanup(plt.close,fig)
        self.assertEqual(len(fig.axes[0].collections),1)
        self.assertEqual(len(fig.axes[0].collections[0].get_facecolors()),0)
        self.assertTrue(any('Delivered dose unknown' in t.get_text() for t in fig.axes[0].texts))
        self.assertEqual(fig.axes[0].get_xlim()[0],0)

    def test_selected_conditional_is_not_labelled_as_working(self):
        release,row=self.fixture();row['estimate_support']='conditional_calibration_variant'
        points=plots.combine_estimates([row],[],[release])
        fig=plots.comparison(points,[release],'NISQ','2025');self.addCleanup(plt.close,fig)
        self.assertEqual([t.get_text() for t in fig.legends[0].texts],['Selected · conditional'])

    def test_two_calibrations_get_named_subrows(self):
        release,row=self.fixture();other=dict(row,calibration_id='C02',k='1',q_m3_s='2')
        points=plots.combine_estimates([],[row,other],[release])
        fig=plots.comparison(points,[release],'NISQ','2025');self.addCleanup(plt.close,fig)
        self.assertEqual([t.get_text() for t in fig.axes[0].get_yticklabels()],['05 Aug · T01 / C01','05 Aug · T01 / C02'])

    def test_post_background_line_uses_post_mean(self):
        _,row=self.fixture()
        times=pd.date_range('2025-08-05 12:00:00',periods=8,freq='s')
        frame=pd.DataFrame(dict(timestamp=times,t_s=range(8),ec=[10,10,13,16,14,12,12,12],segment=[0]*8))
        window=dict(pre=[str(times[0]),str(times[1])],pulse=[str(times[2]),str(times[4])],post=[str(times[5]),str(times[7])])
        row.update(background_mode='post',gap_mode='reject',integral_us_cm_s='5.5',
            sensor_applicability='trial_specific_native_match',event_link_status='source_linked',
            unresolved_requirements='[]',capture_limitations='',capture_status='reviewed_observed_window')
        fig=plots.pulse_figure(frame,window,[row]);self.addCleanup(plt.close,fig)
        baseline=next(line for line in fig.axes[0].lines if line.get_linestyle()=='--')
        self.assertEqual(list(baseline.get_ydata()),[12,12,12])


if __name__=='__main__':
    unittest.main()
