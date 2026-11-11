"""Conditional physical references, never coefficient corrections or acceptance gates."""
import math

SOURCE_URLS = {
    'salt_calibration': 'https://confluence-jwsm.ca/index.php/jwsm/article/download/1/2',
    'temperature_defaults': 'https://in-situ.com/uk/pub/media/support/documents/Con_TROLL_PRO_Operation_Manual_After_May_2012.pdf',
    'nacl_solubility': 'https://srdata.nist.gov/solubility/IUPAC/SDS-47/SDS-47.pdf',
}
NACL_IDEAL_K = 58.44 / 126.4  # Infinite dilution, true conductivity at 25°C.
DEFAULT_ALPHA = 0.0191
REFERENCE_TEMPERATURE_C = 25.0
NACL_SATURATION_25C_MG_L = 0.2646 * 1.1992 * 1e6  # Mass fraction × kg/L final solution.


def _finite(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def reference_diagnostic(row):
    """Read audit fields; actual-channel comparison also needs temperature_c in °C."""
    result = dict(
        diagnostic_status='unavailable', flags=[], nacl_reference_k=None,
        nacl_reference_unit='(mg/L) / (uS/cm)',
        reference_assumptions='Ideal dilute NaCl at 25°C; instrument response and chemistry unverified; not a correction.',
        q_ratio_if_reference_k_and_fixed_integral=None, relative_deviation_from_reference=None,
        implied_original_injectate_mg_l=None, nacl_saturation_reference_mg_l=None,
    )
    k = _finite(row.get('k'))
    if k is None or k <= 0:
        result['flags'].append('coefficient_unavailable_or_nonpositive')
        return result
    channel = row.get('conductivity_basis')
    basis = row.get('calibration_basis')
    if channel not in ('actual', 'specific') or basis not in ('mass_concentration', 'relative_concentration'):
        result['diagnostic_status'] = 'not_applicable'
        result['flags'].append('unsupported_reference_basis')
        return result
    expected_unit = '(mL/mL) / (uS/cm)' if basis == 'relative_concentration' else '(mg/L) / (uS/cm)'
    if row.get('coefficient_unit') not in (None, '', expected_unit):
        result.update(diagnostic_status='not_applicable', flags=['coefficient_unit_basis_mismatch'])
        return result
    reference = NACL_IDEAL_K
    if channel == 'actual':
        temperature = _finite(row.get('temperature_c'))
        if temperature is None:
            result['flags'].append('calibration_temperature_unavailable')
            return result
        factor = 1 + DEFAULT_ALPHA * (temperature - REFERENCE_TEMPERATURE_C)
        if factor <= 0:
            result['flags'].append('nonpositive_temperature_compensation_factor')
            return result
        reference /= factor
        result['flags'].append('default_compensation_unverified')
        result['reference_assumptions'] += ' Linear alpha=0.0191/°C, Tref=25°C assumed, not verified settings or a universal temperature law.'
    if not all(math.isfinite(v) for v in (reference, reference / k, k / reference)):
        result['flags'].append('nonfinite_reference_comparison')
        return result
    result.update(diagnostic_status='conditional_reference', nacl_reference_k=reference)
    if basis == 'relative_concentration':
        implied = reference / k
        result.update(implied_original_injectate_mg_l=implied,
                      nacl_saturation_reference_mg_l=NACL_SATURATION_25C_MG_L)
        result['reference_assumptions'] += ' Relative concentration must refer to original injectate; saturation benchmark is NaCl/water at 25°C final solution, not g per litre of starting water.'
        if implied > NACL_SATURATION_25C_MG_L:
            result['flags'].append('relative_nacl_strength_inconsistent')
        return result
    result.update(q_ratio_if_reference_k_and_fixed_integral=reference / k,
                  relative_deviation_from_reference=k / reference - 1)
    if k < reference:
        result['flags'].append('below_ideal_nacl_reference')
    return result


def paired_channel_diagnostic(actual, specific, temperatures, *, same_step_sets):
    """Use paired dose temperatures (°C); caller must verify identical fitted step sets."""
    result = dict(diagnostic_status='not_comparable', flags=[], implied_temperature_c=None,
                  paired_temperature_c=None, temperature_residual_c=None,
                  reference_assumptions='Identical dose sets and fit method, constant temperature; default alpha=0.0191/°C and Tref=25°C unverified; not a measured temperature or an acceptance tolerance.')
    reason = None
    a, s = _finite(actual.get('k')), _finite(specific.get('k'))
    temps = [_finite(t) for t in temperatures] if temperatures is not None else []
    if same_step_sets is not True:
        reason = 'different_or_unverified_step_sets'
    elif actual.get('conductivity_basis') != 'actual' or specific.get('conductivity_basis') != 'specific':
        reason = 'channel_basis_mismatch'
    elif actual.get('calibration_basis') not in ('mass_concentration', 'relative_concentration') or actual.get('calibration_basis') != specific.get('calibration_basis'):
        reason = 'concentration_basis_mismatch'
    elif actual.get('fit_method') != specific.get('fit_method'):
        reason = 'fit_method_mismatch'
    elif any(row.get('coefficient_unit') not in (None, '', '(mL/mL) / (uS/cm)' if row.get('calibration_basis') == 'relative_concentration' else '(mg/L) / (uS/cm)') for row in (actual, specific)):
        reason = 'coefficient_unit_basis_mismatch'
    elif a is None or s is None or min(a, s) <= 0:
        reason = 'coefficient_unavailable_or_nonpositive'
    elif len(temps) < 2 or any(t is None for t in temps):
        reason = 'paired_temperature_unavailable'
    elif any(row.get('n_points') not in (None, '') and _finite(row['n_points']) != len(temps) for row in (actual, specific)):
        reason = 'point_count_mismatch'
    elif max(temps) != min(temps):
        # No invented stability tolerance converts variable-temperature fits into thermometers.
        reason = 'variable_paired_temperature'
    elif 1 + DEFAULT_ALPHA * (temps[0] - REFERENCE_TEMPERATURE_C) <= 0:
        reason = 'nonpositive_temperature_compensation_factor'
    if reason:
        result['flags'].append(reason)
        return result
    implied = REFERENCE_TEMPERATURE_C + (s / a - 1) / DEFAULT_ALPHA
    if not math.isfinite(implied):
        result['flags'].append('nonfinite_implied_temperature')
        return result
    result.update(diagnostic_status='conditional_reference', flags=['default_compensation_unverified'],
                  implied_temperature_c=implied, paired_temperature_c=temps[0],
                  temperature_residual_c=implied - temps[0])
    return result
