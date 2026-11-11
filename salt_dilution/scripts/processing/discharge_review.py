"""Build source-pinned diagnostics and release outcomes from an immutable slug run."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import pairwise, product
import json
import math
from pathlib import Path
import re
from statistics import mean

import numpy as np
import pandas as pd

from ..parsers import aquatroll, parse_data
from . import calibration, calibration_quality, calibration_reuse as reuse, mass_slug as slug, matching

ROOT = matching.ROOT
PROCESSED = Path('salt_dilution/data/processed')
NOTEBOOK = PROCESSED/'field_notes/2026-10-12/field_observations.csv'
STAGE_LABEL = re.compile(r'^(Pressure|Depth|Level)\s*\(([^()]+)\)(?:\s*\([^()]+\))?$')
DESIGN = dict(
    background_durations_s=[15, 30, 45, 60], start_shifts_s=[-10, 0, 10],
    end_shifts_s=[-30, -15, 0], background_modes=['linear', 'pre', 'post'],
    validation='Use sampled windows and preserve documented pre-injection pauses. No gap interpolation or tail extrapolation.',
    interpretation='Sensitivity to local window and background choices. Fit, delivery, mixing, and recipe uncertainties are separate.',
    source_discrepancy_triage_us_cm=10,
)


def _scalar_integral(times, excess):
    return math.fsum((b - a) * (y + x) / 2 for (a, x), (b, y) in pairwise(zip(times, excess)))


def _excess(pre, pulse, post, mode):
    a, b = mean(pre.ec), mean(post.ec)
    x, y = mean(pre.t_s), mean(post.t_s)
    if mode == 'pre':
        return [v - a for v in pulse.ec]
    if mode == 'post':
        return [v - b for v in pulse.ec]
    if mode != 'linear':
        raise ValueError('Unknown background mode')
    return [v - (a + (b - a) * (t - x) / (y - x)) for t, v in zip(pulse.t_s, pulse.ec)]


def _q_m3_s(estimate, area):
    method = estimate.get('discharge_method') or 'mass_slug'
    if method == 'solution_slug':
        numerator = float(estimate['injection_solution_volume_ml']) / 1e6
        unit = '(mL/mL) / (uS/cm)'
    elif method == 'mass_slug':
        numerator = float(estimate['mass_g'])
        unit = '(mg/L) / (uS/cm)'
    else:
        raise ValueError(f'Unknown discharge method: {method}')
    k = float(estimate['k'])
    if estimate['coefficient_unit'] != unit or any(not math.isfinite(v) or v <= 0 for v in (area, numerator, k)):
        raise ValueError('Review requires positive area, quantity and K in method-compatible units')
    q = numerator / (k * area)
    if not math.isfinite(q) or q <= 0:
        raise ValueError('Discharge must be finite and positive')
    return q


def recompute_estimate(frame, windows, estimate):
    pre, pulse, post = slug._window_parts(frame, windows)
    excess = _excess(pre, pulse, post, estimate['background_mode'])
    area = _scalar_integral(pulse.t_s, excess)
    q = _q_m3_s(estimate, area)
    for field, value in [('integral_us_cm_s', area), ('q_m3_s', q), ('q_l_s', 1000 * q)]:
        if not math.isclose(value, float(estimate[field]), rel_tol=1e-12):
            raise ValueError(f"Independent {field} disagrees for {estimate['trial_id']}")
    return area, q, excess


def window_sensitivity(frame, windows, estimate):
    # Keep alternatives inside the reviewed ambient spans. Shorten the pre
    # window towards its end and the post window towards its beginning.
    pre, post = windows['pre'], windows['post']
    pre_variants = sorted({tuple(pre)} | {(max(pre[0], pre[1] - d), pre[1]) for d in DESIGN['background_durations_s']})
    post_variants = sorted({tuple(post)} | {(post[0], min(post[1], post[0] + d)) for d in DESIGN['background_durations_s']})
    results, rejected = [], Counter()
    for p, q, start, end, mode in product(pre_variants, post_variants, DESIGN['start_shifts_s'],
                                          DESIGN['end_shifts_s'], DESIGN['background_modes']):
        candidate = dict(windows, pre=list(p), post=list(q),
                         pulse=[windows['pulse'][0] + start, windows['pulse'][1] + end])
        try:
            before, pulse, after = slug._window_parts(frame, candidate)
            area = _scalar_integral(pulse.t_s, _excess(before, pulse, after, mode))
            value = _q_m3_s(estimate, area)
        except ValueError as error:
            rejected[str(error)] += 1
            continue
        results.append(dict(**candidate, start_shift_s=start, end_shift_s=end, background_mode=mode,
                            integral_us_cm_s=area, q_m3_s=value, relative_change=value / float(estimate['q_m3_s']) - 1))
    return results, dict(rejected)


def observed_area(frame, pre, pulse):
    if (len(pre) != 2 or len(pulse) != 2 or not all(math.isfinite(v) for v in (*pre, *pulse))
            or not pre[0] < pre[1] <= pulse[0] < pulse[1]):
        raise ValueError('Invalid observed scenario windows')
    before, observed = [frame[frame.t_s.between(*span)] for span in (pre, pulse)]
    for part, span in [(before, pre), (observed, pulse)]:
        if len(part) < 2 or [part.t_s.iloc[0], part.t_s.iloc[-1]] != list(span) or not np.isfinite(part.ec).all():
            raise ValueError('Observed scenario requires sampled endpoints and finite observations')
    if frame[frame.t_s.between(pre[0], pulse[1])].segment.nunique() != 1:
        raise ValueError('Observed scenario crosses a sampling gap')
    background = mean(before.ec)
    return _scalar_integral(observed.t_s, (v - background for v in observed.ec)), background


def stage_diagnostics(samples, windows=None):
    """Summarize native stage-related channels in their explicitly labelled units."""
    times = matching._times(samples.timestamp)
    elapsed = (times - times.min()).dt.total_seconds()
    before = elapsed.between(*windows['pre']) if windows else elapsed <= 30
    after = elapsed.between(*windows['post']) if windows else elapsed >= elapsed.max() - 30
    for column in samples:
        label = STAGE_LABEL.fullmatch(column)
        if not label:
            continue
        values = pd.to_numeric(samples[column], errors='coerce')
        first, last = values[before], values[after]
        a, b = [mean(part) if len(part) and np.isfinite(part).all() else None for part in (first, last)]
        yield dict(parameter=label[1], unit=label[2], source_column=column,
                   first_local=str(times.min()), last_local=str(times.max()), pre_mean=a, post_mean=b,
                   change=b - a if a is not None and b is not None else None,
                   pre_sample_count=len(first), post_sample_count=len(last),
                   comparison_window='selected_backgrounds' if windows else 'first_last_30s',
                   interpretation='Within-placement comparison only. Probe movement, barometric effects and hydraulic response are unverified.')


def _read(path, *fields):
    return matching._read_table(path, fields)


def _index(rows, *fields):
    result = {tuple(row[k] for k in fields): row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f'Duplicate keys: {fields}')
    return result


def _native_comparisons(inventory, pins, root):
    for item in inventory:
        files = item['files']
        raw, processed = [files.get(key, {}) for key in ('raw', 'processed')]
        if not raw or item.get('instrument_family') != 'aquatroll' or not item.get('conductivity_bases'):
            continue
        paths = [matching._path(record['path'], root).resolve() for record in (raw, processed)]
        if any(pins.get(str(path)) != record['sha256'] for path, record in zip(paths, (raw, processed))):
            raise ValueError(f"Native comparison has unpinned data: {item['content_ref']}")
        saved = pd.read_csv(paths[1], float_precision='round_trip')
        channels = [matching.CHANNELS[b] for b in item['conductivity_bases']]
        comparison, detail = 'all_timestamps_and_channel_cells_equal', ''
        try:
            parsed, _ = parse_data.read_data(paths[0])
            if not matching._times(parsed.timestamp).equals(matching._times(saved.timestamp)):
                comparison = 'timestamp_or_row_count_mismatch'
            elif any(c not in parsed or c not in saved or not np.array_equal(
                    pd.to_numeric(parsed[c], errors='raise'), pd.to_numeric(saved[c], errors='raise'),
                    equal_nan=True) for c in channels):
                comparison = 'conductivity_cells_differ'
        except ValueError as error:
            comparison, detail = 'native_reparse_unavailable', str(error)
        yield dict(raw_path=raw['path'], processed_path=processed['path'], device_serial=item['device_serial'],
                   rows=len(saved), channels=channels, first_local=item['first_local'], last_local=item['last_local'],
                   comparison=comparison, detail=detail)


def channel_consistency(fits, temperatures):
    for (cid, alias, basis), actual in fits.items():
        other = (cid, alias, 'specific')
        if basis != 'actual' or other not in fits:
            continue
        before = temperatures.get((cid, alias, 'actual'), {})
        after = temperatures.get(other, {})
        same_steps = bool(before) and before.keys() == after.keys()
        paired = [t if t == after.get(step) else None for step, t in sorted(before.items())]
        yield dict(calibration_id=cid, probe_alias=alias, actual_k=actual['k'], specific_k=fits[other]['k'],
                   calibration_basis=actual['calibration_basis'], same_step_sets=same_steps,
                   actual_source_variant=actual.get('source_variant', ''),
                   specific_source_variant=fits[other].get('source_variant', ''),
                   **calibration_quality.paired_channel_diagnostic(actual, fits[other], paired, same_step_sets=same_steps))


def _calibration_quality(records, cal, pair, fits, skips, temperatures):
    if fits.keys() & skips.keys():
        raise ValueError('A calibration series is both fitted and skipped')
    preparations = _read(records/'calibrations.csv', 'site_alias')
    rows = []
    for site in sorted({row['site_alias'] for row in preparations}):
        audit, _ = reuse.audit_calibrations(records, cal, pair, site=site)
        rows.extend(row for row in audit if row['site_alias'] == site)
    if set(_index(rows, 'calibration_id', 'alias_label', 'conductivity_basis')) != fits.keys() | skips.keys():
        raise ValueError('Calibration audit does not cover all fitted and skipped series')
    profiles = json.loads(calibration.PROFILES.read_text())
    for row in rows:
        key = tuple(row[k] for k in ('calibration_id', 'alias_label', 'conductivity_basis'))
        basis = profiles.get(row['procedure_id'], {}).get('calibration_basis')
        expected = {'mass_concentration': '(mg/L) / (uS/cm)', 'relative_concentration': '(mL/mL) / (uS/cm)'}.get(basis, '')
        temps = set(temperatures.get(key, {}).values())
        known = temps - {None}
        temperature = next(iter(known)) if len(temps) == len(known) == 1 else None
        reference = calibration_quality.reference_diagnostic(dict(row, temperature_c=temperature))
        yield dict(row, fit_status='fitted' if key in fits else 'skipped',
                   skip_reason=skips.get(key, {}).get('reason', ''), expected_coefficient_unit=expected,
                   fit_se_status='available' if row['k_se'] not in ('', None) else 'unavailable',
                   recipe_uncertainty='unquantified', temperature_c=temperature,
                   temperature_min_c=min(known) if known else None, temperature_max_c=max(known) if known else None,
                   **reference)


def _conditional_cases(path, attempts, frames, summaries, trials, edges, fits, recordings, inventory, cal, pins, root):
    document = json.loads(path.read_text())
    if document.get('schema_version') != 1 or not isinstance(document.get('cases'), list):
        raise ValueError('Invalid conditional windows schema')
    keys = ('trial_id', 'logical_recording_id', 'channel')
    for key, case in _index(document['cases'], *keys).items():
        tid, logical, channel = key
        attempt = attempts[key]
        edge = recordings[(attempt['recording_edge_id'],)]
        source = case['source_processed']
        members = slug._decoded(edge, 'member_refs', [])
        if (attempt['outcome'] != 'blocked' or summaries[(tid,)]['category'] == 'computed'
                or case['background_mode'] != 'pre' or case['scenario'] != 'capture_assumed_observed_interval'
                or not case.get('qualification') or not case.get('evidence') or len(members) != 1
                or source != inventory[members[0]]['files']['processed']
                or pins.get(str(matching._path(source['path'], root).resolve())) != source['sha256']):
            raise ValueError(f'Conditional scenario lacks matching blocked-attempt or source evidence: {key}')
        fit_edge = edges[(attempt['calibration_edge_id'],)]
        fit = slug._selected_fit(fit_edge, fits, cal)
        if (fit_edge['trial_id'] != tid or fit_edge['recording_edge_id'] != attempt['recording_edge_id']
                or fit_edge.get('status') != 'supported' or fit['conductivity_basis'] != channel
                or summaries[(tid,)]['mass_confirmation_status'] != 'confirmed_delivered'):
            raise ValueError(f'Conditional scenario lacks a compatible fitted edge or confirmed mass: {key}')
        frame = frames[key]
        integral, background = observed_area(frame, case['pre'], case['pulse'])
        mass = summaries[(tid,)]['confirmed_delivered_mass_g']
        q = _q_m3_s(dict(fit, mass_g=mass), integral)
        reference_fields = slug.calibration_reference_fields(fit)
        origin = frame.timestamp.iloc[0]
        yield dict(trial_id=tid, field_date=matching._date(trials[(tid,)]['field_date']),
                   logical_recording_id=logical, conductivity_basis=channel, calibration_id=fit['calibration_id'],
                   k=fit['k'], coefficient_unit=fit['coefficient_unit'], mass_g=mass,
                   integral_us_cm_s=integral, pre_mean=background, q_m3_s=q, q_l_s=1000*q,
                   interval_start_local=str(origin+pd.to_timedelta(case['pulse'][0], unit='s')),
                   interval_end_local=str(origin+pd.to_timedelta(case['pulse'][1], unit='s')),
                   pre=case['pre'], pulse=case['pulse'], scenario=case['scenario'], qualification=case['qualification'],
                   evidence=case['evidence'], source_processed=source, scientifically_accepted=False,
                   flags=reference_fields['calibration_reference_flags'], **reference_fields)


def _review_capture(frame, attempt, edge, related, windows):
    first = frame[frame.t_s <= 30]
    last = frame[frame.t_s >= frame.t_s.max() - 30]
    a, b = float(first.ec.mean()), float(last.ec.mean())
    changes = frame.loc[frame.segment.diff() > 0, 't_s']
    pause = windows.get('pre_injection_pause', {}) if windows else {}
    gaps = []
    for idx, end in changes.items():
        start = float(frame.t_s.iloc[idx - 1])
        location = 'uncertain_relative_to_pulse'
        if windows:
            lo, hi = windows['pulse']
            location = ('documented_pre_injection_pause' if pause and end <= pause['release_offset_s'] else
                        'before_pulse' if end <= lo else 'after_pulse' if start >= hi else 'inside_pulse')
        gaps.append(dict(start_s=start, end_s=end, position=location))
    lo, hi = frame.timestamp.iloc[0], frame.timestamp.iloc[-1]
    same_day = [(r, pd.Timestamp(r['first_local']), pd.Timestamp(r['last_local'])) for r in related
                if r['first_local'] and r['last_local'] and pd.Timestamp(r['first_local']).date() == lo.date()]
    return dict(trial_id=attempt['trial_id'], logical_recording_id=attempt['logical_recording_id'],
                channel=attempt['channel'], device_serial=edge.get('device_serial', ''), first_local=str(lo),
                last_local=str(hi), sample_count=len(frame), duration_s=float(frame.t_s.iloc[-1]),
                pre_30s_samples=len(first), post_30s_samples=len(last), pre_30s_mean_us_cm=a,
                post_30s_mean_us_cm=b, post_minus_pre_us_cm=b-a, peak_us_cm=float(frame.ec.max()),
                post_30s_slope_us_cm_per_s=float(np.polyfit(last.t_s, last.ec, 1)[0]) if len(last) >= 3 else '',
                outcome=attempt['outcome'], reason_code=attempt.get('reason', ''), detail=attempt.get('detail', ''),
                sample_gaps=gaps, pre_injection_pause=pause,
                longer_same_sensor_recordings=[r['path'] for r, start, end in same_day if start <= hi < end],
                later_same_day_records=[dict(path=r['path'], start_local=str(start), gap_s=(start-hi).total_seconds(),
                                             activity=r.get('activity', 'unknown')) for r, start, _ in same_day if start > hi],
                diagnostic_scope='First/last 30s summarize observed samples. Tail and post-background identity require separate evidence.')


def _review_channel(frame, row, fit, windows, alternate, rejected, area, q, excess):
    pre, pulse, post = slug._window_parts(frame, windows)
    a, b = float(fit['ec_min']), float(fit['ec_max'])
    peak, span = max(excess), b - a
    high = _scalar_integral(pulse.t_s, (max(v-span, 0) for v in excess))
    changes = [v['relative_change'] for v in alternate]
    pre_noise = float(pre.ec.std())
    return dict(trial_id=row['trial_id'], conductivity_basis=row['conductivity_basis'], estimate_role=row['estimate_role'],
                q_primary_m3_s=q, logical_recording_id=row['logical_recording_id'],
                discharge_method=row.get('discharge_method') or 'mass_slug', estimate_support=row.get('estimate_support', ''),
                independently_recomputed_integral_us_cm_s=area, tested_scenarios=len(alternate), rejected_scenarios=rejected,
                q_sensitivity_min_m3_s=min(v['q_m3_s'] for v in alternate), q_sensitivity_max_m3_s=max(v['q_m3_s'] for v in alternate),
                sensitivity_min_relative=min(changes), sensitivity_max_relative=max(changes),
                window_numerical_review='completed_observed_windows_only',
                calibration_id=row['calibration_id'], identity_status=row['identity_status'], k=row['k'],
                k_fit_se=row['k_se'], k_fit_se_relative=row['u_k_fit_relative'], calibration_r_squared=fit['r_squared'],
                calibration_ec_min=a, calibration_ec_max=b, river_pulse_ec_min=float(pulse.ec.min()),
                river_pulse_ec_max=float(pulse.ec.max()), absolute_ec_below_calibration=bool((pulse.ec < a).any()),
                absolute_ec_above_calibration=bool((pulse.ec > b).any()), calibration_added_ec_span=span,
                river_peak_added_ec=peak, added_ec_span_exceeded=peak > span,
                peak_added_ec_to_calibration_span_ratio=peak / span if span > 0 else '',
                area_above_added_ec_span_fraction=high/area, pre_background_ec=float(pre.ec.mean()),
                post_background_ec=float(post.ec.mean()), pre_noise_us_cm=pre_noise,
                peak_to_pre_noise=peak/pre_noise if pre_noise > 0 else '',
                post_slope_us_cm_s=float(np.polyfit(post.t_s, post.ec, 1)[0]),
                pulse_end_excess_us_cm=excess[-1], pulse_end_excess_to_peak_ratio=excess[-1]/peak,
                source_calibration_note=fit['source_note'], calibration_applicability='see_calibration_quality',
                mixing_check='not_independently_established', tracer_recovery='not_independently_established',
                mass_basis=row['mass_basis'], solution_volume_basis=row.get('solution_volume_basis', ''),
                q_status=row['q_status'], scientifically_accepted=False, total_uncertainty='not_quantified', window_user_signoff=False,
                **slug.calibration_reference_fields(dict(fit, k=row['k'])))


def _release_rows(trial, summary, source, estimates, review, notes, attempts, bundle_name):
    tid = trial['trial_id']
    primaries = [r for r in estimates if r['estimate_role'] == 'primary']
    if len(primaries) != int(summary['category'] == 'computed') or len(estimates) != int(summary['estimate_count']):
        raise ValueError(f'Release summary and estimates disagree: {tid}')
    primary = primaries[0] if primaries else {}
    actual = [r for r in estimates if r['conductivity_basis'] == 'actual' and r['coefficient_source'] == 'trial_specific']
    confirmed = summary['mass_confirmation_status'] == 'confirmed_delivered'
    reasons = slug._decoded(summary, 'reasons', [])
    source_flag = any(r['quantity'] == 'specific_conductivity_background'
                      and r['native_minus_notebook_us_cm'] != ''
                      and abs(r['native_minus_notebook_us_cm']) > DESIGN['source_discrepancy_triage_us_cm'] for r in notes)
    master = dict(trial_id=tid, field_date=matching._date(trial['field_date']), site_alias=trial['site_alias'],
                  category=summary['category'], q_primary_m3_s=primary.get('q_m3_s', ''),
                  q_primary_l_s=primary.get('q_l_s', ''), q_actual_comparison_m3_s=actual[0]['q_m3_s'] if len(actual) == 1 else '',
                  **{k: primary.get(k, '') for k in ('conductivity_basis', 'logical_recording_id', 'sensor_serial',
                     'calibration_id', 'k', 'coefficient_unit', 'integral_us_cm_s', 'window_status', 'discharge_method',
                     'injection_solution_volume_ml', 'solution_volume_basis', 'estimate_support')},
                  mass_g=primary.get('mass_g', summary['confirmed_delivered_mass_g']),
                  mass_basis=primary.get('mass_basis', 'user_confirmed_delivered' if confirmed else ''),
                  mass_confirmation_status=summary['mass_confirmation_status'],
                  confirmed_delivered_mass_g=summary['confirmed_delivered_mass_g'],
                  source_nominal_mass_g=source.get('nominal_salt_mass_g', ''),
                  source_delivered_mass_g=source.get('delivered_salt_mass_g', ''),
                  q_status=primary.get('q_status', 'not_calculated'), scientifically_accepted=False,
                  missing_requirements=reasons, source_notes=source.get('notes', ''),
                  evidence_result=bundle_name, mass_route_candidate=bool(attempts) and
                  (primary.get('discharge_method') or 'mass_slug') == 'mass_slug',
                  source_record_id=source.get('record_id', ''), pairing_status=summary['pairing_status'])
    master.update(flags=slug._decoded(primary, 'flags', []),
                  calibration_reference_flags=slug._decoded(primary, 'calibration_reference_flags', []),
                  calibration_reference_status=primary.get('calibration_reference_status', ''),
                  calibration_reference_assumptions=primary.get('calibration_reference_assumptions', ''))
    primary_review = next((r for r in review if r['estimate_role'] == 'primary'), {})
    gaps = []
    if primary:
        gaps = ['field_mixing_and_recovery_not_independently_validated',
                'calibration_temperature_settings_and_recipe_uncertainty_unquantified', 'staff_scientific_acceptance_not_recorded']
        if source_flag:
            gaps.append('notebook_background_disagrees_with_recording')
        if primary_review['added_ec_span_exceeded']:
            gaps.append('added_conductivity_span_exceeds_calibration_span')
    return master, dict(trial_id=tid, source_category=summary['category'], q_primary_m3_s=master['q_primary_m3_s'],
                        recommendation=('source_background_reconciliation_required' if source_flag else
                                        'usable_as_proposed_with_documented_limits' if primary else 'resolve_recorded_blockers'),
                        window_numerical_review='completed' if primary else
                        'blocked_capture_review_completed' if attempts else 'no_window_review_upstream_blocker',
                        local_sensitivity_min_relative=primary_review.get('sensitivity_min_relative', ''),
                        local_sensitivity_max_relative=primary_review.get('sensitivity_max_relative', ''),
                        mass_confirmation_status=summary['mass_confirmation_status'],
                        remaining_evidence_gaps=gaps or reasons, user_window_signoff=False, scientifically_accepted=False)


def run_review(mass_dir, pairing_dir, calibration_dir, output_dir, *,
               records_dir=calibration.DEFAULT_RECORDS, conditional_windows_path=None, root=ROOT):
    """Review every saved outcome and publish a fresh hash-verified bundle."""
    mass, pair, cal, records, root = [Path(p).resolve() for p in
                                      (mass_dir, pairing_dir, calibration_dir, records_dir, root)]
    output = Path(output_dir)
    if any(output.resolve().is_relative_to(p) or p.is_relative_to(output.resolve()) for p in (mass, pair, cal, records)):
        raise ValueError('Review output must be separate from inputs')
    mass_info, pins = reuse.verify_bundle(mass, root)
    mass_inputs = {matching._path(p['path'], root).resolve(): p['sha256'] for p in mass_info['inputs']}
    pair_info, cal_info = None, None
    for dependency in (pair, cal):
        path = dependency/'run_info.json'
        if path not in mass_inputs:
            raise ValueError(f'Mass run does not pin the selected dependency: {dependency}')
        info, extra = reuse.verify_bundle(dependency, root)
        if dependency == pair:
            pair_info = info
        else:
            cal_info = info
        pins.update(extra)
    reuse.pin_record_tables(records, cal_info, pins, root)
    notes_path = root/NOTEBOOK
    conditional = Path(conditional_windows_path).resolve() if conditional_windows_path else None
    for path in [notes_path, calibration.PROFILES] + ([conditional] if conditional else []):
        pins.setdefault(str(path.resolve()), matching._hash(path))

    def read_pinned(path, *fields):
        if str(path.resolve()) not in pins:
            raise ValueError(f'Table is not pinned by the source run: {path}')
        return _read(path, *fields)

    trials = _index(read_pinned(records/'trials.csv', 'trial_id'), 'trial_id')
    summaries = _index(read_pinned(mass/'release_summary.csv', 'trial_id'), 'trial_id')
    if trials.keys() != summaries.keys():
        raise ValueError('Slug outcomes must account for every release exactly once')
    provenance = json.loads((records/'provenance.json').read_text())['trials']
    observations = defaultdict(list)
    for note in read_pinned(notes_path, 'trial_id', 'quantity'):
        observations[note['trial_id']].append(note)
    by_trial = defaultdict(list)
    by_recording = defaultdict(list)
    for row in read_pinned(mass/'discharge_estimates.csv', 'trial_id', 'q_l_s'):
        if (row['trial_id'],) not in trials or row['scientifically_accepted'] != 'false':
            raise ValueError('Estimate lacks a known release or has unsupported acceptance')
        by_trial[row['trial_id']].append(row)
        by_recording[row['trial_id'], row['logical_recording_id'], row['conductivity_basis']].append(row)
    keys = ('trial_id', 'logical_recording_id', 'channel')
    attempts = _index(read_pinned(mass/'recording_outcomes.csv', 'trial_id', 'outcome'), *keys)
    if set(by_recording) != {key for key, row in attempts.items() if row['outcome'] == 'computed'}:
        raise ValueError('Computed recording outcomes and estimates disagree')
    recordings = _index(read_pinned(pair/'recording_candidates.csv', 'recording_edge_id'), 'recording_edge_id')
    edges = _index(read_pinned(pair/'calibration_candidates.csv', 'calibration_edge_id'), 'calibration_edge_id')
    fit_keys = ('calibration_id', 'probe_alias', 'conductivity_basis')
    fits = _index(read_pinned(cal/'calibration_fits.csv', *fit_keys), *fit_keys)
    skips = _index(read_pinned(cal/'calibration_skips.csv', *fit_keys), *fit_keys)
    temperatures = defaultdict(dict)
    for point in read_pinned(cal/'calibration_points.csv', *fit_keys, 'used_in_fit', 'step_no'):
        if point['used_in_fit'].lower() == 'true':
            steps = temperatures[tuple(point[k] for k in fit_keys)]
            if point['step_no'] in steps:
                raise ValueError('Duplicate fitted calibration step')
            steps[point['step_no']] = calibration_quality._finite(point.get('temperature_c') or point.get('native_temperature_c'))
    inventory = {r['content_ref']: r for r in pair_info['inventory']}
    sensors = defaultdict(list)
    for item in inventory.values():
        if item['device_serial']:
            sensors[item['device_serial']].append(item)

    master, release, capture, channel_review, scenarios, notes, blocked, stage_rows = ([] for _ in range(8))
    channel_by_trial, notes_by_trial, attempt_by_trial = defaultdict(list), defaultdict(list), defaultdict(list)
    frames = {}
    code = [__file__, calibration.__file__, calibration_quality.__file__, reuse.__file__,
            slug.__file__, matching.__file__, aquatroll.__file__, parse_data.__file__]
    with reuse.staged_run(output, pins, code) as (stage, pins):
        native = list(_native_comparisons(inventory.values(), pins, root))
        for key, attempt in attempts.items():
            tid, logical, channel = key
            trial = trials[(tid,)]
            edge = recordings[(attempt['recording_edge_id'],)]
            if (edge['trial_id'], edge['logical_recording_id']) != (tid, logical):
                raise ValueError(f'Recording edge does not match attempt: {key}')
            attempt_by_trial[tid].append(attempt)
            samples = slug._recording_samples(edge, pair_info, root/PROCESSED, root)
            coverage = {k: attempt.get(k, '') for k in (*keys, 'outcome', 'detail')}
            coverage['reason_code'] = attempt.get('reason', '')
            estimates = by_recording[key]
            windows = slug._decoded(estimates[0], 'windows', {}) if estimates else {}
            try:
                frame, issues = slug.prepare_series(samples, channel)
            except ValueError as error:
                if estimates:
                    raise
                frame, issues = None, [str(error)]
            if frame is not None:
                frames[key] = frame
                coverage.update(_review_capture(frame, attempt, edge, sensors[edge.get('device_serial')], windows))
            coverage['series_issues'] = issues
            capture.append(coverage)
            stage_rows.extend(dict(**{k: attempt[k] for k in keys},
                                   field_date=matching._date(trial['field_date']),
                                   member_refs=slug._decoded(edge, 'member_refs', []), **row)
                              for row in stage_diagnostics(samples, windows))
            if not estimates:
                end = frame.t_s.iloc[-1] if frame is not None else 0
                blocks = [frame.loc[frame.t_s.between(end-90+i*30, end-60+i*30, inclusive='right'), 'ec']
                          for i in range(3)] if frame is not None else []
                blocked.append(dict(trial_id=tid, logical_recording_id=logical, conductivity_basis=channel,
                                    reason=coverage['reason_code'], detail=coverage['detail'],
                                    end_local=coverage.get('last_local', ''), final_three_30s_block_means=[
                                        mean(v) if len(v) and np.isfinite(v).all() else None for v in blocks],
                                    recovery='not_established', series_issues=issues, scientifically_accepted=False))
                continue
            source = provenance.get(tid, {}).get('source_record', {}).get('record_id', '')
            fit = slug._selected_fit(edges[(attempt['calibration_edge_id'],)], fits, cal)
            for row in estimates:
                if (row['calibration_id'] != fit['calibration_id'] or row['recording_edge_id'] != attempt['recording_edge_id']
                        or row['coefficient_unit'] != fit['coefficient_unit']
                        or (row['coefficient_source'] == 'trial_specific' and float(row['k']) != float(fit['k']))):
                    raise ValueError(f'Saved estimate differs from its fitted edge: {key}')
                row_windows = slug._decoded(row, 'windows', {})
                area, q, excess = recompute_estimate(frame, row_windows, row)
                alternate, rejected = window_sensitivity(frame, row_windows, row)
                check = _review_channel(frame, row, fit, row_windows, alternate, rejected, area, q, excess)
                channel_review.append(check)
                channel_by_trial[tid].append(check)
                scenarios.extend(dict(trial_id=tid, logical_recording_id=logical, conductivity_basis=channel,
                                      estimate_role=row['estimate_role'], **scenario) for scenario in alternate)
                if row['coefficient_source'] != 'trial_specific' or not source:
                    continue
                for note in observations[source]:
                    quantity = note['quantity']
                    if quantity not in (channel+'_conductivity_background', channel+'_conductivity_peak'):
                        continue
                    measured = check['pre_background_ec'] if quantity.endswith('background') else float(frame.ec.max())
                    comparison = dict(trial_id=tid, logical_recording_id=logical, conductivity_basis=channel,
                                      source_record_id=source, observation_id=note['observation_id'], quantity=quantity,
                                      notebook_value_raw=note['value_raw'], notebook_numeric_value=note['value'],
                                      notebook_qualifier=note['value_qualifier'], native_measurement_us_cm=measured,
                                      native_minus_notebook_us_cm=measured-float(note['value']) if note['value'] else '',
                                      interpretation='Compare notebook transcription with native observations; approximate values retain their qualifier.')
                    notes.append(comparison)
                    notes_by_trial[tid].append(comparison)
        for (tid,), trial in trials.items():
            summary, checked = _release_rows(trial, summaries[(tid,)], provenance.get(tid, {}).get('source_record', {}),
                                             by_trial[tid], channel_by_trial[tid], notes_by_trial[tid], attempt_by_trial[tid], mass.name)
            master.append(summary)
            release.append(checked)
        quality = list(_calibration_quality(records, cal, pair, fits, skips, temperatures))
        consistency = list(channel_consistency(fits, temperatures))
        conditional_rows = list(_conditional_cases(conditional, attempts, frames, summaries, trials, edges,
                                                   fits, recordings, inventory, cal, pins, root)) if conditional else []
        for name, rows, empty in [
            ('discharge_by_release', master, ['trial_id', 'category']),
            ('native_export_comparison', native, ['raw_path', 'comparison']),
            ('capture_coverage', capture, ['trial_id', 'channel', 'reason_code']),
            ('review_by_release', release, ['trial_id']),
            ('review_by_channel', channel_review, ['trial_id', 'conductivity_basis']),
            ('window_sensitivity_scenarios', scenarios, ['trial_id', 'conductivity_basis', 'q_m3_s']),
            ('notebook_native_comparison', notes, ['trial_id', 'quantity']),
            ('blocked_release_review', blocked, ['trial_id', 'reason']),
            ('calibration_quality', quality, ['calibration_id', 'conductivity_basis', 'fit_status']),
            ('channel_consistency', consistency, ['calibration_id', 'probe_alias', 'diagnostic_status']),
            ('stage_diagnostics', stage_rows, ['trial_id', 'logical_recording_id', 'channel', 'field_date',
                                               'first_local', 'last_local', 'parameter', 'unit', 'pre_mean',
                                               'post_mean', 'change', 'interpretation']),
            ('conditional_discharge', conditional_rows, ['trial_id', 'field_date', 'logical_recording_id',
                                                        'conductivity_basis', 'calibration_id', 'k', 'integral_us_cm_s',
                                                        'pre_mean', 'q_m3_s', 'scenario', 'qualification', 'scientifically_accepted']),
        ]:
            slug._table(stage/f'{name}.csv', rows, empty)
        references = [dict(title=key, url=url) for key, url in calibration_quality.SOURCE_URLS.items()]
        (stage/'references.json').write_text(matching._json(references)+'\n')
        (stage/'review_design.json').write_text(matching._json(DESIGN)+'\n')
        return reuse.write_run_info(stage, pins, scope='Independent numerical review and evidence accounting',
                                    release_count=len(master), category_counts=dict(Counter(r['category'] for r in master)),
                                    reviewed_channel_count=len(channel_review), sensitivity_scenarios=len(scenarios),
                                    reviewed_primary_release_count=sum(bool(r['q_primary_m3_s']) for r in master),
                                    calibration_series_count=len(quality), conditional_scenario_count=len(conditional_rows),
                                    native_comparison_counts=dict(Counter(r['comparison'] for r in native)),
                                    stage_diagnostic_count=len(stage_rows))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('mass-run', 'pairing', 'calibrations', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--records', type=Path, default=calibration.DEFAULT_RECORDS)
    parser.add_argument('--conditional-windows', type=Path)
    args = parser.parse_args(argv)
    run_review(args.mass_run, args.pairing, args.calibrations, args.output,
               records_dir=args.records, conditional_windows_path=args.conditional_windows)


if __name__ == '__main__':
    main()
