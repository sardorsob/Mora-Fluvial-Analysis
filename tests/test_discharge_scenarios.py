"""Hand-computed checks for conditional recipes and unobserved pulse intervals."""
import unittest

import pandas as pd

from salt_dilution.scripts.processing import discharge_scenarios as scenarios


class ScenarioTests(unittest.TestCase):
    def points(self):
        return [dict(step_no=str(i), used_in_fit='true', cumulative_added_volume_ml=v,
                     conductivity_us_cm=10+100*v/(1000+v)) for i,v in enumerate([0,10,20,30])]

    def recipe(self, **changes):
        return dict(dict(basis='mass', receiver_initial_ml=1000, stock_mass_g=2,
                         stock_volume_ml=1000, mass_g=4000), **changes)

    def frame(self):
        return pd.DataFrame(dict(timestamp=pd.date_range('2025-07-09',periods=7,freq='s'),
            t_s=[0.,1.,2.,3.,4.,5.,6.],ec=[10.,10.,10.,16.,10.,10.,10.],segment=[0]*7))

    def windows(self):
        return dict(pre=['2025-07-09 00:00:00','2025-07-09 00:00:01'],
                    pulse=['2025-07-09 00:00:02','2025-07-09 00:00:04'],
                    post=['2025-07-09 00:00:05','2025-07-09 00:00:06'])

    def test_stock_scaling_changes_q_but_not_r_squared(self):
        direct=scenarios.recipe_fit(self.points(), self.recipe())
        secondary=scenarios.recipe_fit(self.points(), self.recipe(secondary_aliquot_ml=10,secondary_water_ml=1000))
        self.assertAlmostEqual(direct['k'],20.)
        self.assertAlmostEqual(direct['k']/secondary['k'],101.)
        self.assertAlmostEqual(direct['r_squared'],secondary['r_squared'])
        self.assertAlmostEqual(scenarios.scenario_q(self.recipe(),direct['k'],1000),.2)
        self.assertAlmostEqual(scenarios.scenario_q(self.recipe(),secondary['k'],1000),20.2)

    def test_mass_and_relative_routes_have_explicit_units(self):
        relative=self.recipe(basis='relative',solution_volume_ml=12000)
        fit=scenarios.recipe_fit(self.points(),relative)
        self.assertEqual(fit['coefficient_unit'],'(mL/mL) / (uS/cm)')
        self.assertAlmostEqual(scenarios.scenario_q(relative,fit['k'],6),.2)
        self.assertAlmostEqual(scenarios.scenario_q(dict(relative,solution_volume_ml=12900),fit['k'],6)/.2,1.075)
        with self.assertRaisesRegex(ValueError,'together'):
            scenarios.recipe_fit(self.points(),self.recipe(secondary_aliquot_ml=10))

    def test_two_points_do_not_claim_slope_precision(self):
        fit=scenarios.recipe_fit(self.points()[:2],self.recipe())
        self.assertIsNone(fit['k_se'])
        self.assertEqual(fit['n_points'],2)

    def test_per_liter_response_cannot_be_mislabeled_as_a_full_release(self):
        recipe=self.recipe(basis='relative',solution_volume_ml=1000,quantity_kind='per_liter_response_not_release')
        self.assertAlmostEqual(scenarios.scenario_q(recipe,.01,10),.01)
        for invalid in (dict(recipe,solution_volume_ml=12900),dict(recipe,basis='mass')):
            with self.assertRaisesRegex(ValueError,'exactly 1000'):
                scenarios.scenario_q(invalid,.01,10)

    def test_signed_integral_and_no_implicit_gap_bridge(self):
        frame=self.frame(); windows=self.windows()
        self.assertEqual(scenarios.scenario_area(frame,windows,'linear')['integral_us_cm_s'],6.)
        frame.loc[3:,'segment']=1
        with self.assertRaisesRegex(ValueError,'explicit model'):
            scenarios.scenario_area(frame,windows,'pre')
        expected={'linear':6.,'endpoint_low':3.,'endpoint_high':9.}
        for mode,area in expected.items():
            out=scenarios.scenario_area(frame,windows,'pre',mode)
            self.assertEqual(out['integral_us_cm_s'],area)
            self.assertEqual(out['observed_interval_integral_us_cm_s'],3.)
            self.assertEqual(out['in_pulse_gap_count'],1)
            self.assertEqual(out['modelled_gap_seconds'],1.)

    def test_outside_or_overlapping_windows_are_not_silently_used(self):
        window=self.windows(); window['pre'][1]='2025-07-09 00:00:03'
        with self.assertRaisesRegex(ValueError,'overlap'):
            scenarios.scenario_area(self.frame(),window,'linear')
        window=self.windows(); window['pre'][0]='2025-07-08 23:59:59'
        with self.assertRaisesRegex(ValueError,'outside'):
            scenarios.scenario_area(self.frame(),window,'linear')


class WorkingProtocolTests(unittest.TestCase):
    def fixture(self):
        tid='NISQ-20250805-T01'
        decision=dict(field='stock_mass_g',value=2,unit='g',basis='inherited_preceding_same_method',
            donor_ids=['NISQ-20250731-C02'],source_refs=['stocks.csv#row=6'],reason='Same dry-stock protocol')
        choice=dict(trial_id=tid,preferred_recipe_ids=['direct'],selection_status='working_protocol_adopted',
                    field_decisions=[decision],known_exceptions=['Instrument compatibility assumed'])
        config=dict(cases=[dict(trial_id=tid,recipes=[dict(id='direct',calibration_id='C01',stock_mass_g=2),dict(id='secondary',calibration_id='C01',stock_mass_g=2)])],
            windows=[dict(id='window',post=[1,2],gap_modes=['reject'])],working_protocol=dict(cases=[choice]))
        rows=[dict(trial_id=tid,recipe_id=recipe,window_id='window',background_mode=mode,gap_mode='reject',
            q_m3_s=q,result_class='assumption_conditional') for recipe,q in [('direct',100.),('secondary',4.)]
              for mode in ('pre','linear','post')]
        return config,rows

    def test_protocol_choice_does_not_follow_smaller_or_more_familiar_q(self):
        config,rows=self.fixture()
        parameters,working,summary=scenarios.working_tables(config,rows)
        self.assertEqual(len(working),1)
        self.assertEqual(working[0]['q_m3_s'],100.)
        self.assertEqual(working[0]['background_mode'],'linear')
        self.assertEqual(parameters[0]['donor_age_days'],{'NISQ-20250731-C02':5})
        self.assertEqual(parameters[0]['parameter_source_status'],'inferred')
        self.assertEqual(summary[0]['working_recipe_count'],1)

    def test_unresolved_hypotheses_do_not_enter_working_q(self):
        config,rows=self.fixture();choice=config['working_protocol']['cases'][0]
        choice.update(preferred_recipe_ids=[],retained_hypothesis_ids=['direct','secondary'],selection_status='stock_stage_unresolved')
        _,working,summary=scenarios.working_tables(config,rows)
        self.assertEqual(working,[])
        self.assertEqual(summary[0]['disposition'],'working_recipe_unresolved')
        choice['preferred_recipe_ids']=['direct']
        with self.assertRaisesRegex(ValueError,'Unresolved'):
            scenarios.working_tables(config,rows)

    def test_future_cross_site_and_cross_year_donors_rejected(self):
        for donor in ('NISQ-20250806-C01','PAR-20250731-C01','NISQ-20240731-C01'):
            config,rows=self.fixture();config['working_protocol']['cases'][0]['field_decisions'][0]['donor_ids']=[donor]
            with self.assertRaisesRegex(ValueError,'precedent'):
                scenarios.working_tables(config,rows)

    def test_working_parameter_must_equal_the_recipe_used_for_calculation(self):
        config,rows=self.fixture()
        config['working_protocol']['cases'][0]['field_decisions'][0]['value']=4
        with self.assertRaisesRegex(ValueError,'differs from calculation'):
            scenarios.working_tables(config,rows)
        config,rows=self.fixture()
        config['working_protocol']['cases'][0]['field_decisions'][0]['unit']='mg'
        with self.assertRaisesRegex(ValueError,'unit differs'):
            scenarios.working_tables(config,rows)

    def test_distinct_calibration_receivers_cannot_be_silently_merged(self):
        config,rows=self.fixture();decisions=config['working_protocol']['cases'][0]['field_decisions']
        decisions.append(dict(decisions[0]))
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            scenarios.working_tables(config,rows)
        decisions[0]['calibration_id']='C01';decisions[1]['calibration_id']='C02'
        parameters,_,_=scenarios.working_tables(config,rows)
        self.assertEqual(len(parameters),2)

    def test_reported_solution_quantity_is_checked_and_summary_preserves_limits(self):
        config,rows=self.fixture();decision=config['working_protocol']['cases'][0]['field_decisions'][0]
        decision.update(field='reported_solution_volume',value=12900,unit='mL')
        config['cases'][0]['recipes'][0]['solution_volume_ml']=12000
        with self.assertRaisesRegex(ValueError,'differs from calculation'):
            scenarios.working_tables(config,rows)
        config['cases'][0]['recipes'][0]['solution_volume_ml']=12900
        limits={('NISQ-20250805-T01',):dict(blocking_factors=['pipette_dose_uncertainty'],
            calibration_evidence='Broken pipette',capture_evidence='Tail assumed complete',quantity_evidence='Nominal delivery')}
        _,_,summary=scenarios.working_tables(config,rows,limits)
        self.assertEqual(summary[0]['calibration_limitations'],'Broken pipette')
        self.assertEqual(summary[0]['capture_limitations'],'Tail assumed complete')
        self.assertEqual(summary[0]['quantity_limitations'],'Nominal delivery')


if __name__=='__main__':
    unittest.main()
