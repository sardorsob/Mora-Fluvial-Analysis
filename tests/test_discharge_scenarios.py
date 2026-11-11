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


if __name__=='__main__':
    unittest.main()
