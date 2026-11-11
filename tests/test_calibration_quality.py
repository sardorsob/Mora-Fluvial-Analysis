"""Physical references flag assumptions without replacing empirical calibrations."""
import copy
import unittest

from salt_dilution.scripts.processing import calibration_quality as quality


class ReferenceTests(unittest.TestCase):
    def test_low_mass_factor_is_a_conditional_comparison_not_a_correction(self):
        row = dict(k='0.4', conductivity_basis='specific', calibration_basis='mass_concentration')
        original = copy.deepcopy(row)
        result = quality.reference_diagnostic(row)
        self.assertEqual(row, original)
        self.assertEqual(result['diagnostic_status'], 'conditional_reference')
        self.assertIn('below_ideal_nacl_reference', result['flags'])
        self.assertAlmostEqual(result['nacl_reference_k'], 0.4623417722)
        self.assertAlmostEqual(result['q_ratio_if_reference_k_and_fixed_integral'], 1.1558544304)
        self.assertIn('not a correction', result['reference_assumptions'])

    def test_unusable_coefficients_and_unsupported_bases_do_not_generate_ratios(self):
        for k in ('', None, 'nan', 'inf', 0, -1, 'bad'):
            with self.subTest(k=k):
                result = quality.reference_diagnostic(dict(k=k, conductivity_basis='specific', calibration_basis='mass_concentration'))
                self.assertEqual(result['diagnostic_status'], 'unavailable')
                self.assertIsNone(result['q_ratio_if_reference_k_and_fixed_integral'])
        result = quality.reference_diagnostic(dict(k=.5, conductivity_basis='salinity', calibration_basis='mass_concentration'))
        self.assertEqual(result['diagnostic_status'], 'not_applicable')

    def test_actual_requires_recorded_temperature_and_labels_default_compensation(self):
        row = dict(k=.7, conductivity_basis='actual', calibration_basis='mass_concentration')
        self.assertEqual(quality.reference_diagnostic(row)['diagnostic_status'], 'unavailable')
        row['temperature_c'] = 10
        result = quality.reference_diagnostic(row)
        self.assertAlmostEqual(result['nacl_reference_k'], .6479912715)
        self.assertIn('default_compensation_unverified', result['flags'])
        self.assertIn('alpha=0.0191', result['reference_assumptions'])
        row['temperature_c'] = -30
        self.assertIsNone(quality.reference_diagnostic(row)['q_ratio_if_reference_k_and_fixed_integral'])

    def test_low_k_does_not_establish_q_bias_when_instrument_gain_cancels(self):
        true_k, true_integral, mass = .5, 1000, 4
        gain = 1.4
        observed_k, observed_integral = true_k / gain, true_integral * gain
        diagnostic = quality.reference_diagnostic(dict(k=observed_k, conductivity_basis='specific', calibration_basis='mass_concentration'))
        self.assertGreater(diagnostic['q_ratio_if_reference_k_and_fixed_integral'], 1)
        self.assertAlmostEqual(mass / (observed_k * observed_integral), .008)
        self.assertAlmostEqual(mass / (true_k * true_integral), .008)

    def test_relative_reference_uses_final_solution_solubility_not_water_volume(self):
        row = dict(k=1.2154308403784417e-8, conductivity_basis='specific', calibration_basis='relative_concentration')
        result = quality.reference_diagnostic(row)
        self.assertAlmostEqual(result['nacl_saturation_reference_mg_l'], 317308.32)
        self.assertGreater(result['implied_original_injectate_mg_l'], 38_000_000)
        self.assertIn('relative_nacl_strength_inconsistent', result['flags'])
        self.assertIsNone(result['q_ratio_if_reference_k_and_fixed_integral'])
        self.assertIsNone(result['relative_deviation_from_reference'])
        self.assertIn('25°C final solution', result['reference_assumptions'])
        row['k'] = 1.5e-6
        self.assertNotIn('relative_nacl_strength_inconsistent', quality.reference_diagnostic(row)['flags'])

    def test_wrong_explicit_units_are_not_compared(self):
        result = quality.reference_diagnostic(dict(k=.5, conductivity_basis='specific',
            calibration_basis='relative_concentration', coefficient_unit='(mg/L) / (uS/cm)'))
        self.assertEqual(result['diagnostic_status'], 'not_applicable')
        self.assertIn('coefficient_unit_basis_mismatch', result['flags'])

    def test_extreme_finite_input_does_not_emit_infinite_reference_ratios(self):
        result = quality.reference_diagnostic(dict(k=5e-324, conductivity_basis='specific', calibration_basis='relative_concentration'))
        self.assertEqual(result['diagnostic_status'], 'unavailable')
        self.assertIsNone(result['implied_original_injectate_mg_l'])


class PairedChannelTests(unittest.TestCase):
    def setUp(self):
        self.actual = dict(k=.7007708479, conductivity_basis='actual', calibration_basis='mass_concentration', n_points=2)
        self.specific = dict(k=.5, conductivity_basis='specific', calibration_basis='mass_concentration', n_points=2)

    def test_paired_constant_temperature_is_a_model_diagnostic_not_measured_temperature(self):
        result = quality.paired_channel_diagnostic(self.actual, self.specific, [10, 10], same_step_sets=True)
        self.assertEqual(result['diagnostic_status'], 'conditional_reference')
        self.assertAlmostEqual(result['implied_temperature_c'], 10, places=6)
        self.assertAlmostEqual(result['temperature_residual_c'], 0, places=6)
        self.assertIn('not a measured temperature', result['reference_assumptions'])

    def test_different_steps_variable_temperature_or_invalid_k_never_imply_temperature(self):
        for actual, specific, temperatures, same, reason in [
            (self.actual, self.specific, [10, 10], False, 'different_or_unverified_step_sets'),
            (self.actual, self.specific, [10, 11], True, 'variable_paired_temperature'),
            (self.actual, self.specific, [10, float('nan')], True, 'paired_temperature_unavailable'),
            (dict(self.actual, n_points=3), self.specific, [10, 10], True, 'point_count_mismatch'),
            (dict(self.actual, k=float('inf')), self.specific, [10, 10], True, 'coefficient_unavailable_or_nonpositive'),
            (dict(self.actual, fit_method='weighted'), dict(self.specific, fit_method='ols'), [10, 10], True, 'fit_method_mismatch'),
            (dict(self.actual, coefficient_unit='mS/cm'), self.specific, [10, 10], True, 'coefficient_unit_basis_mismatch'),
        ]:
            with self.subTest(reason=reason):
                result = quality.paired_channel_diagnostic(actual, specific, temperatures, same_step_sets=same)
                self.assertEqual(result['diagnostic_status'], 'not_comparable')
                self.assertIn(reason, result['flags'])
                self.assertIsNone(result['implied_temperature_c'])


if __name__ == '__main__':
    unittest.main()
