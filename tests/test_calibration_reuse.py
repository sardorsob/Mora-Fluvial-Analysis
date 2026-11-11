"""Independent-session calibration reuse must not confuse precision with applicability."""
import copy
import unittest
import numpy as np
from salt_dilution.scripts.processing import calibration_reuse as reuse
from salt_dilution.scripts.processing.calibration import fit_calibration


class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.fit=dict(calibration_id='C',conductivity_basis='specific',calibration_basis='mass_concentration',
                      concentration_unit='mg/L',coefficient_unit='(mg/L) / (uS/cm)',k='0.5')
        self.prep=dict(calibration_id='C',site_alias='NISQ',procedure_id='mass_stock_river',stock_salt_mass_g='2',
                       stock_water_initial_ml='1000',stock_solution_final_ml='',calibration_water_initial_ml='2000',stock_water_source='river')
        self.evidence=dict(source_table_status='recorded',source_record={'method_family':'mass_stock'})
        self.device=dict(status='verified',device_serial='sensor-A',basis='within_trial_continuity')

    def test_alias_never_supplies_identity(self):
        self.fit['probe_alias']='sensor-A'
        c,why=reuse.classify_fit(self.fit,self.prep,self.evidence,{},site='NISQ')
        self.assertEqual(c,'mass_trial_only')

    def test_relative_never_library_eligible(self):
        self.fit.update(calibration_basis='relative_concentration',concentration_unit='mL/mL',coefficient_unit='(mL/mL) / (uS/cm)')
        self.evidence['source_record']['method_family']='unspecified'
        self.assertEqual(reuse.classify_fit(self.fit,self.prep,self.evidence,self.device)[0],'relative_only')

    def test_out_of_scope_reported(self):
        self.prep['site_alias']='PAR'
        self.assertEqual(reuse.classify_fit(self.fit,self.prep,self.evidence,self.device)[0],'out_of_scope_site')

    def test_all_site_audit_keeps_site_identity_without_excluding_paradise(self):
        self.prep['site_alias']='PAR'
        self.assertEqual(reuse.classify_fit(self.fit,self.prep,self.evidence,self.device,site=None)[0],'mass_library_eligible')

    def test_abandoned_does_not_enter(self):
        self.evidence['source_table_status']='abandoned'
        self.assertEqual(reuse.classify_fit(self.fit,self.prep,self.evidence,self.device)[0],'abandoned_or_supporting')

    def test_complete_mass_and_native_evidence_eligible(self):
        self.assertEqual(reuse.classify_fit(self.fit,self.prep,self.evidence,self.device)[0],'mass_library_eligible')

    def test_bad_units_cannot_enter_library(self):
        self.fit['coefficient_unit']='unknown'
        self.assertEqual(reuse.classify_fit(self.fit,self.prep,self.evidence,self.device)[0],'not_fitted')

    def test_relative_fit_requires_relative_coefficient_units(self):
        self.fit.update(calibration_basis='relative_concentration', concentration_unit='mL/mL')
        result, _ = reuse.classify_fit(self.fit, self.prep, self.evidence, self.device)
        self.assertEqual(result, 'not_fitted')

    def test_leave_one_dose_sensitivity_preserves_the_fit_and_step_identity(self):
        points = [dict(step_no=str(i), conductivity_us_cm=i, concentration=y, residual=r,
                       used_in_fit='True', exclusion_reason='')
                  for i, (y, r) in enumerate(zip((0, 1, 2, 5), (.4, -.2, -.8, .6)))]
        points.insert(2, dict(step_no='4', used_in_fit='False', exclusion_reason='missing_specific'))
        result = reuse.point_selection_diagnostics(points, 1.6)
        self.assertEqual(result['used_dose_steps'], ['0', '1', '2', '3'])
        self.assertEqual(result['excluded_dose_steps'], {'4': 'missing_specific'})
        self.assertAlmostEqual(result['leave_one_dose_k']['3'], 1.0)
        self.assertAlmostEqual(result['max_abs_leave_one_dose_k_relative_effect'], .375)
        self.assertIsNone(result['quadratic_sse_reduction_fraction'])

    def test_leave_one_dose_preserves_minimum_primary_point_count(self):
        points = [dict(step_no=str(i), conductivity_us_cm=i, concentration=i, residual=0,
                       used_in_fit='True', exclusion_reason='') for i in range(3)]
        result = reuse.point_selection_diagnostics(points, 1)
        self.assertEqual(result['leave_one_dose_k'], {})
        self.assertIsNone(result['max_abs_leave_one_dose_k_relative_effect'])

    def test_slope_se_hand_dataset(self):
        # x=0,1,2; y=0,1,3 gives residuals1/6,-1/3,1/6, SSE1/6, Sxx2.
        self.assertAlmostEqual(reuse.slope_se([0,1,2],[1/6,-1/3,1/6]),np.sqrt(1/12))

    def test_method_candidate_exact_and_inputs_unchanged(self):
        prep=dict(self.prep,procedure_id='solution_secondary',injectate_aliquot_ml='10',secondary_water_initial_ml='1000')
        points=[dict(calibration_id='C',step_no=str(i),probe_alias='',recorded_added_volume_ml=str(i),addition_kind='cumulative',
                     specific_conductivity_us_cm=str(30+10*i)) for i in range(4)]
        saved,_=fit_calibration(prep,points)
        before=copy.deepcopy((prep,points,saved))
        candidate=reuse.method_candidate(prep,points,saved)
        self.assertAlmostEqual(candidate['k_candidate_direct_mass']/saved['k'],2000/(10/1010),places=7)
        self.assertEqual(candidate['candidate_label'],'unresolved_method_candidate_not_for_use')
        self.assertEqual((prep,points,saved),before)


class ReuseTests(unittest.TestCase):
    def rows(self,values=None,channel='specific'):
        vals=values if values is not None else [.5,.501,.499,.5,.501,.499,.5,.501,.499]
        return [dict(calibration_id=f'C{i}',conductivity_basis=channel,sensor_serial='A',site_alias='NISQ',
          field_date=f'2026-10-{2+i//3:02}',k=str(k),compat_class='mass_library_eligible',stock_water_source='river',
          procedure_id='mass_stock_river',temperature_available=False,receiver_background_ec=30,stock_lineage='synthetic_independent_days',
          reuse_conditions_confirmed=True) for i,k in enumerate(vals)]

    def test_stable_passes_under_declared_independence_assumptions(self):
        row=reuse.evaluate_reuse(self.rows())[0]
        self.assertEqual(row['outcome'],'pass')
        self.assertEqual(row['session_count'],9)
        self.assertIn('conditional',row['interpretation'].lower())

    def test_large_drift_fails(self):
        vals=[.45]*3+[.5]*3+[.55]*3
        self.assertEqual(reuse.evaluate_reuse(self.rows(vals))[0]['outcome'],'fail')

    def test_two_days_insufficient(self):
        self.assertEqual(reuse.evaluate_reuse(self.rows()[:6])[0]['outcome'],'insufficient_evidence')

    def test_actual_without_temperature_insufficient(self):
        self.assertEqual(reuse.evaluate_reuse(self.rows(channel='actual'))[0]['outcome'],'insufficient_evidence')

    def test_stability_does_not_verify_unknown_conditions(self):
        rows=self.rows()
        for row in rows:row['reuse_conditions_confirmed']=False
        result=reuse.evaluate_reuse(rows)[0]
        self.assertEqual(result['outcome'],'insufficient_evidence')
        self.assertIn('stock_settings_or_independence_unverified',result['reasons'])

    def test_temperature_presence_alone_is_not_a_temperature_model(self):
        rows=self.rows(channel='actual')
        for row in rows:row['temperature_available']=True
        self.assertEqual(reuse.evaluate_reuse(rows)[0]['outcome'],'insufficient_evidence')

    def test_isolated_rows_never_change_metrics(self):
        rows=self.rows();first=reuse.evaluate_reuse(rows)
        rows.append(dict(rows[0],calibration_id='ISOLATED',k='500',compat_class='method_conflict_isolated'))
        self.assertEqual(reuse.evaluate_reuse(rows),first)

    def test_channels_separate(self):
        self.assertEqual(len(reuse.evaluate_reuse(self.rows()+self.rows(channel='actual'))),2)

    def test_lodo_hand_example(self):
        rows=self.rows([1]*3+[2]*3+[4]*3)
        result=reuse.evaluate_reuse(rows)[0]
        self.assertAlmostEqual(result['lodo_effects'][0]['q_relative_effect'],1/np.sqrt(8)-1)

    def test_application_pi_wider_than_mean_ci(self):
        r=reuse.evaluate_reuse(self.rows())[0]
        self.assertGreater(r['session_prediction_upper_ratio']-1,r['mean_ci_upper']/r['k_reference']-1)

    def test_one_bad_session_cannot_pass_through_day_averaging(self):
        vals=[.49,.5,.51]*2+[.4,.5,.6]
        self.assertNotEqual(reuse.evaluate_reuse(self.rows(vals))[0]['outcome'],'pass')

    def test_background_association_is_reported_from_day_groups(self):
        rows=self.rows([np.exp(.01*(30+i//3)) for i in range(9)])
        for i,row in enumerate(rows):row['receiver_background_ec']=30+i//3
        result=reuse.evaluate_reuse(rows)[0]
        self.assertAlmostEqual(result['background_association_log_slope_per_us_cm'],.01)
        self.assertEqual(result['background_association_day_count'],3)
