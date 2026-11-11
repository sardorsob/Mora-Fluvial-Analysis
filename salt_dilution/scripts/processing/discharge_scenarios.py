"""Compare explicit recipe and capture assumptions without replacing observations."""
from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import pairwise, product
import json
import math
import hashlib
from pathlib import Path
import re
import subprocess
from datetime import datetime

import numpy as np
import pandas as pd

from . import calibration_reuse as reuse, discharge_review as review, mass_slug as slug, matching


def verify_baseline(directory, root):
    """Check saved data bytes and identify old code by its recorded Git blob."""
    info = json.loads((directory/'run_info.json').read_text())
    pins = {str(directory/'run_info.json'): matching._hash(directory/'run_info.json')}
    historical = []
    for group, base in (('inputs', root), ('outputs', directory)):
        for item in info[group]:
            path = matching._path(item['path'], base).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError(f'Missing or outside-root baseline source: {path}')
            if matching._hash(path) == item['sha256']:
                pins[str(path)] = item['sha256']
                continue
            relative = path.relative_to(root).as_posix()
            if group != 'inputs' or not relative.startswith('salt_dilution/scripts/') or path.suffix != '.py':
                raise ValueError(f'Changed baseline data: {path}')
            blob = subprocess.run(['git','show',f'{info["git_commit"]}:{relative}'],cwd=root,capture_output=True,check=True).stdout
            if hashlib.sha256(blob).hexdigest() != item['sha256']:
                raise ValueError(f'Historical code does not match baseline hash: {path}')
            historical.append(dict(item,git_commit=info['git_commit']))
    return info, pins, historical


def positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and positive')
    return value


def recipe_fit(points, recipe):
    """Refit the recorded doses; changing stock scale cannot resolve its identity."""
    receiver = positive(recipe['receiver_initial_ml'], 'receiver_initial_ml')
    selected = [p for p in points if str(p['used_in_fit']).lower() == 'true']
    if len(selected) < 2:
        raise ValueError('Fewer than two usable calibration observations')
    if len({p['step_no'] for p in selected}) != len(selected):
        raise ValueError('Duplicate calibration steps')
    ec = np.array([float(p['conductivity_us_cm']) for p in selected])
    doses = np.array([float(p['cumulative_added_volume_ml']) for p in selected])
    if not np.isfinite(ec).all() or not np.isfinite(doses).all() or (doses < 0).any():
        raise ValueError('Nonfinite or negative calibration input')
    fractions = doses / (receiver + doses)
    dx, dy = ec - ec.mean(), fractions - fractions.mean()
    if np.dot(dx, dx) <= 0 or np.dot(dy, dy) <= 0:
        raise ValueError('Calibration observations must vary')
    slope = positive(np.dot(dx, dy) / np.dot(dx, dx), 'dose_fraction_slope')
    intercept = fractions.mean() - slope * ec.mean()
    residual = fractions - (slope * ec + intercept)
    aliquot, water = recipe.get('secondary_aliquot_ml'), recipe.get('secondary_water_ml')
    if (aliquot is None) != (water is None):
        raise ValueError('Secondary aliquot and water must be specified together')
    dilution = 1. if aliquot is None else positive(aliquot, 'secondary aliquot') / (
        positive(aliquot, 'secondary aliquot') + positive(water, 'secondary water'))
    if recipe['basis'] == 'mass':
        scale = positive(recipe['stock_mass_g'], 'stock_mass_g') * 1e6 / positive(
            recipe['stock_volume_ml'], 'stock_volume_ml') * dilution
        unit = '(mg/L) / (uS/cm)'
    elif recipe['basis'] == 'relative':
        scale, unit = dilution, '(mL/mL) / (uS/cm)'
    else:
        raise ValueError('Unknown calibration basis')
    se = math.sqrt(np.dot(residual, residual) / (len(ec)-2) / np.dot(dx, dx)) * scale if len(ec) > 2 else None
    return dict(k=slope * scale, k_se=se, coefficient_unit=unit, dose_fraction_slope=slope,
                concentration_scale=scale, secondary_fraction=dilution, n_points=len(ec),
                r_squared=float(1-np.dot(residual, residual)/np.dot(dy, dy)),
                ec_min=float(ec.min()), ec_max=float(ec.max()),
                fit_note='OLS on recorded cumulative doses; stock scaling leaves R-squared unchanged. K SE excludes recipe, delivery and field uncertainty.')


def scenario_area(frame, windows, background_mode, gap_mode='reject'):
    """Replay observed intervals; any unobserved in-pulse area stays explicit."""
    if background_mode not in ('pre', 'post', 'linear') or gap_mode not in ('reject', 'linear', 'endpoint_low', 'endpoint_high'):
        raise ValueError('Unknown background or gap model')
    parts = {}
    origin = frame.timestamp.iloc[0]
    for name in ('pre', 'pulse', 'post'):
        bounds = windows.get(name)
        if bounds is None:
            parts[name] = frame.iloc[:0]
            continue
        start, end = [(pd.Timestamp(t)-origin).total_seconds() for t in bounds]
        if start >= end:
            raise ValueError('Window bounds must increase')
        if start < frame.t_s.min() or end > frame.t_s.max():
            raise ValueError('Window is outside observed recording')
        parts[name] = frame.loc[frame.t_s.between(start, end)]
    pre, pulse, post = (parts[name] for name in ('pre', 'pulse', 'post'))
    if any(not np.isfinite(part.ec).all() for part in (pre, pulse, post)):
        raise ValueError('Nonfinite conductivity in scenario window')
    if len(pre) < 2 or len(pulse) < 2 or (background_mode != 'pre' and len(post) < 2):
        raise ValueError('Insufficient observed background or pulse support')
    if pre.t_s.iloc[-1] > pulse.t_s.iloc[0] or (len(post) and pulse.t_s.iloc[-1] > post.t_s.iloc[0]):
        raise ValueError('Background and pulse windows overlap')
    if pre.segment.nunique() != 1 or (background_mode != 'pre' and post.segment.nunique() != 1):
        raise ValueError('Background window crosses an acquisition gap')
    bg0 = float(pre.ec.mean())
    bg1 = float(post.ec.mean()) if len(post) else None
    t = pulse.t_s.to_numpy(float)
    if background_mode == 'linear':
        background = np.interp(t, [pre.t_s.mean(), post.t_s.mean()], [bg0, bg1])
    else:
        background = np.full(len(t), bg0 if background_mode == 'pre' else bg1)
    excess = pulse.ec.to_numpy(float) - background
    segments = pulse.segment.to_numpy()
    observed, gap_area, gap_seconds, gaps = 0., 0., 0., 0
    for i, ((a, x), (b, y)) in enumerate(pairwise(zip(t, excess))):
        dt = b-a
        if dt <= 0:
            raise ValueError('Pulse timestamps must increase')
        area = dt*(x+y)/2
        if segments[i] != segments[i+1]:
            gaps += 1; gap_seconds += dt
            if gap_mode == 'reject':
                raise ValueError('In-pulse acquisition gap requires an explicit model')
            if gap_mode == 'endpoint_low':
                area = dt*min(x, y)
            elif gap_mode == 'endpoint_high':
                area = dt*max(x, y)
            gap_area += area
        else:
            observed += area
    area = positive(observed + gap_area, 'signed pulse area')
    return dict(integral_us_cm_s=area, observed_interval_integral_us_cm_s=observed,
                modelled_gap_integral_us_cm_s=gap_area, modelled_gap_seconds=gap_seconds,
                in_pulse_gap_count=gaps, background_pre_us_cm=bg0, background_post_us_cm=bg1,
                pre_samples=len(pre), pulse_samples=len(pulse), post_samples=len(post),
                pre_duration_s=float(pre.t_s.iloc[-1]-pre.t_s.iloc[0]),
                post_duration_s=float(post.t_s.iloc[-1]-post.t_s.iloc[0]) if len(post) else None,
                pulse_peak_us_cm=float(pulse.ec.max()), background_mode=background_mode,
                gap_mode=gap_mode, gap_interpretation='Endpoint alternatives are model sensitivity, not guaranteed bounds on an unobserved pulse.')


def scenario_q(recipe, k, area):
    k, area = positive(k, 'k'), positive(area, 'area')
    if recipe.get('quantity_kind') == 'per_liter_response_not_release' and (
            recipe['basis'] != 'relative' or float(recipe.get('solution_volume_ml', 0)) != 1000.):
        raise ValueError('Per-liter response requires relative calibration and exactly 1000 mL')
    if recipe['basis'] == 'mass':
        return positive(recipe['mass_g'], 'mass_g') / (k*area)
    return positive(recipe['solution_volume_ml'], 'solution_volume_ml') / 1e6 / (k*area)


def working_tables(config, rows, requirements=None):
    """Apply source-led protocol choices; never rank recipes by the resulting Q."""
    selections = config.get('working_protocol')
    if selections is None:
        return [], [], []
    cases = review._index(config['cases'], 'trial_id')
    choices = review._index(selections['cases'], 'trial_id')
    if choices.keys() != cases.keys():
        raise ValueError('Working protocol must cover every scenario release exactly once')
    window_index = review._index(config['windows'], 'id')
    parameters, estimates, summaries = [], [], []
    for (tid,), choice in choices.items():
        known = {r['id'] for r in cases[(tid,)]['recipes']}
        selected = choice['preferred_recipe_ids']
        if len(set(selected)) != len(selected) or not set(selected).issubset(known):
            raise ValueError('Unknown or duplicate working recipe')
        if choice['selection_status'] == 'stock_stage_unresolved' and selected:
            raise ValueError('Unresolved stock hypotheses cannot be working recipes')
        target_date = datetime.strptime(tid.split('-')[1], '%Y%m%d').date()
        decision_keys = set()
        for decision in choice['field_decisions']:
            key = (decision['field'], decision.get('calibration_id', ''))
            if key in decision_keys or not decision.get('source_refs') or not decision.get('reason'):
                raise ValueError('Duplicate or unsupported working parameter')
            decision_keys.add(key)
            expected_unit = {'stock_mass_g':'g', 'nominal_salt_mass':'g', 'delivered_salt_mass':'g',
                'stock_volume_ml':'mL', 'receiver_initial_volume':'mL', 'working_solution_volume':'mL',
                'reported_solution_volume':'mL'}.get(decision['field'])
            if expected_unit and decision['unit'] != expected_unit:
                raise ValueError('Working parameter unit differs from calculation unit')
            values = {'stock_mass_g': decision['value']} if decision['field'] == 'stock_mass_g' else (
                {'stock_volume_ml': decision['value']} if decision['field'] == 'stock_volume_ml' else {})
            if decision['field'] == 'calibration_stock':
                values = dict(stock_mass_g=decision['value']['salt_mass_g'], stock_volume_ml=decision['value']['starting_water_ml'])
            elif decision['field'] == 'relative_stock_stage':
                values = dict(secondary_aliquot_ml=decision['value']['primary_aliquot_ml'], secondary_water_ml=decision['value']['starting_water_ml'])
            elif decision['field'] == 'receiver_initial_volume':
                values = dict(receiver_initial_ml=decision['value'])
            elif decision['field'] in ('working_solution_volume', 'reported_solution_volume'):
                values = dict(solution_volume_ml=decision['value'])
            elif decision['field'] in ('nominal_salt_mass', 'delivered_salt_mass'):
                values = dict(mass_g=decision['value'])
            applied = []
            for recipe in cases[(tid,)]['recipes']:
                if recipe['id'] not in selected or decision.get('calibration_id', recipe['calibration_id']) != recipe['calibration_id']:
                    continue
                used = {k: v for k, v in values.items() if recipe.get(k) is not None}
                if any(float(recipe[k]) != float(v) for k, v in used.items()):
                    raise ValueError(f'Working parameter differs from calculation recipe: {tid} {decision["field"]}')
                if used:
                    applied.append(recipe['id'])
            days = {}
            for donor in decision['donor_ids']:
                donor_date = datetime.strptime(donor.split('-')[1], '%Y%m%d').date()
                if donor.split('-')[0] != tid.split('-')[0] or donor_date.year != target_date.year or donor_date > target_date:
                    raise ValueError('Recipe precedent must be same site/year and not a future date')
                days[donor] = (target_date-donor_date).days
            basis = decision['basis']
            source_status = ('unresolved' if decision['value'] is None else 'participant_confirmed' if basis.startswith(('participant_confirmed', 'field_participant_confirmed'))
                else 'reviewed_nominal' if basis.startswith('user_reviewed') else 'recorded' if basis.startswith(('observed_', 'recorded_')) else 'inferred')
            parameters.append(dict(trial_id=tid, **decision, donor_age_days=days,
                                   parameter_source_status=source_status, used_by_working_recipes=applied))
        adopted = []
        for row in rows:
            if row['trial_id'] != tid or row['recipe_id'] not in selected:
                continue
            window = window_index[(row['window_id'],)]
            preferred_mode = window.get('working_background_mode', 'linear' if window.get('post') else 'pre')
            preferred_gap = 'linear' if 'linear' in window.get('gap_modes', []) else 'reject'
            if row['background_mode'] != preferred_mode or row['gap_mode'] != preferred_gap:
                continue
            adopted.append(dict(row, working_recipe_status=choice['selection_status'],
                protocol_source_decisions=choice['field_decisions'], protocol_exceptions=choice['known_exceptions'],
                working_choice_is_measurement=False))
        estimates.extend(adopted)
        qs = [r['q_m3_s'] for r in adopted if r['q_m3_s'] is not None]
        unit_count = sum(r['result_class'] == 'unit_response' for r in adopted)
        limits = (requirements or {}).get((tid,), {})
        summaries.append(dict(trial_id=tid, recipe_status=choice['selection_status'],
            working_recipe_count=len(selected), working_recipe_ids=selected,
            retained_hypothesis_ids=choice.get('retained_hypothesis_ids', []),
            working_channel_estimates=len(qs), working_q_min_m3_s=min(qs) if qs else None,
            working_q_max_m3_s=max(qs) if qs else None, unit_response_count=unit_count,
            disposition='working_conditional_q' if qs else ('unit_response_only' if unit_count else 'working_recipe_unresolved' if not selected else 'working_window_unavailable'),
            interpretation='Separate instruments/channels and calibration attempts are retained. Their range is not a confidence interval.',
            unresolved_requirements=limits.get('blocking_factors', []),
            calibration_limitations=limits.get('calibration_evidence', ''),
            capture_limitations=limits.get('capture_evidence', ''),
            quantity_limitations=limits.get('quantity_evidence', ''),
            known_exceptions=choice['known_exceptions'], scientifically_accepted=False))
    return parameters, estimates, summaries


def run_scenarios(config_path, pairing_dir, calibration_dir, baseline_dir, output, *, root=matching.ROOT):
    root = Path(root).resolve()
    config_path, pairing_dir, calibration_dir, baseline_dir = [Path(p).resolve() for p in
        (config_path, pairing_dir, calibration_dir, baseline_dir)]
    config = json.loads(config_path.read_text())
    if config.get('schema_version') != 1:
        raise ValueError('Unsupported scenario schema')
    pins = {str(config_path): matching._hash(config_path)}
    infos = []
    for directory in (pairing_dir, calibration_dir):
        info, extra = reuse.verify_bundle(directory, root)
        pins.update(extra); infos.append(info)
    baseline_info, extra, historical = verify_baseline(baseline_dir, root)
    pins.update(extra)
    pair_info, cal_info = infos
    baseline_inputs = {matching._path(p['path'], root).resolve(): p['sha256'] for p in baseline_info['inputs']}
    for directory in (pairing_dir, calibration_dir):
        path = directory/'run_info.json'
        if baseline_inputs.get(path) != matching._hash(path):
            raise ValueError('Baseline must reference the exact selected calibration and pairing runs')
    review.pin_review_sources(config['sources'], pins, root)
    for choice in config.get('working_protocol', {}).get('cases', []):
        for decision in choice['field_decisions']:
            for ref in decision['source_refs']:
                path = matching._path(re.split(r' row | cell |#', ref, maxsplit=1)[0], root).resolve()
                if not path.is_relative_to(root) or str(path) not in pins:
                    raise ValueError(f'Working parameter source is not pinned: {ref}')
    cases = review._index(config['cases'], 'trial_id')
    recordings = review._index(review._read(pairing_dir/'recording_candidates.csv', 'recording_edge_id'), 'recording_edge_id')
    pairing = review._index(review._read(pairing_dir/'pairing_summary.csv', 'trial_id'), 'trial_id')
    baseline = review._index(review._read(baseline_dir/'tables/discharge_by_release.csv', 'trial_id'), 'trial_id')
    requirements = review._index(review._read(baseline_dir/'tables/recovery_requirements.csv', 'trial_id'), 'trial_id')
    missing = {tid for tid, row in baseline.items() if not row['q_primary_m3_s'] and row['category'] != 'excluded_practice'}
    if set(cases) != missing:
        raise ValueError('Scenario cases must cover every non-practice missing release exactly once')
    points = defaultdict(list)
    for point in review._read(calibration_dir/'calibration_points.csv', 'calibration_id'):
        points[point['calibration_id'], point['probe_alias'], point['conductivity_basis']].append(point)
    windows = defaultdict(list)
    seen = set()
    for window in config['windows']:
        key = (window['trial_id'], window['recording_edge_id'], window['channel'], window['id'])
        if key in seen or (window['trial_id'],) not in cases:
            raise ValueError('Duplicate or unknown scenario window')
        seen.add(key)
        edge = recordings[(window['recording_edge_id'],)]
        if edge['trial_id'] != window['trial_id'] or window['recording_edge_id'] not in slug._decoded(
                pairing[(window['trial_id'],)], 'selected_recording_edge_ids', []):
            raise ValueError('Scenario must use a selected release-recording edge')
        for extra_id in window.get('additional_recording_edge_ids', []):
            extra_edge = recordings[(extra_id,)]
            if (extra_id == window['recording_edge_id'] or extra_id not in slug._decoded(pairing[(window['trial_id'],)], 'selected_recording_edge_ids', [])
                    or not edge['device_serial'] or extra_edge['device_serial'] != edge['device_serial']):
                raise ValueError('Composite window must join distinct selected edges from the same instrument')
        if window['channel'] not in matching.CHANNELS or not window.get('evidence') or not window.get('assumptions'):
            raise ValueError('Scenario window lacks channel or evidence')
        windows[window['trial_id']].append(window)
    rows, rejected, fits, summaries = [], list(config.get('excluded_candidates', [])), [], []
    frames = {}
    code = [__file__, slug.__file__, review.__file__, reuse.__file__, matching.__file__]
    with reuse.staged_run(Path(output), pins, code) as (stage, pins):
        for (tid,), case in cases.items():
            recipe_ids = [r['id'] for r in case['recipes']]
            if len(set(recipe_ids)) != len(recipe_ids):
                raise ValueError('Duplicate recipe IDs')
            for recipe in case['recipes']:
                if not recipe.get('source_refs') or not recipe.get('assumptions'):
                    raise ValueError('Recipe lacks source references or explicit assumptions')
                for ref in recipe['source_refs']:
                    path = matching._path(re.split(r' row | cell |#', ref, maxsplit=1)[0], root).resolve()
                    if not path.is_relative_to(root) or str(path) not in pins:
                        raise ValueError(f'Recipe reference is not pinned: {ref}')
                # Keep physical quantities and units explicit; no fitted-Q selection score.
                for key, selected_points in points.items():
                    if key[0] != recipe['calibration_id']:
                        continue
                    try:
                        fit = recipe_fit(selected_points, recipe)
                    except (ValueError, TypeError) as error:
                        rejected.append(dict(trial_id=tid, recipe_id=recipe['id'], stage='calibration', reason=str(error)))
                        continue
                    fit.update(trial_id=tid, recipe_id=recipe['id'], calibration_id=key[0],
                               probe_alias=key[1], conductivity_basis=key[2])
                    fits.append(fit)
                    for window in windows[tid]:
                        if window['channel'] != key[2]:
                            continue
                        edge = recordings[(window['recording_edge_id'],)]
                        edge_ids = [window['recording_edge_id']] + window.get('additional_recording_edge_ids', [])
                        frame_key = (tuple(edge_ids), key[2])
                        if frame_key not in frames:
                            samples = pd.concat([slug._recording_samples(recordings[(eid,)], pair_info,
                                root/'salt_dilution/data/processed', root) for eid in edge_ids], ignore_index=True)
                            frames[frame_key] = slug.prepare_series(samples, key[2])
                        frame, series_issues = frames[frame_key]
                        for mode, gap in product(window['background_modes'], window.get('gap_modes', ['reject'])):
                            identity = dict(trial_id=tid, recipe_id=recipe['id'], window_id=window['id'],
                                            recording_edge_id=edge['recording_edge_id'], conductivity_basis=key[2],
                                            background_mode=mode, gap_mode=gap)
                            try:
                                area = scenario_area(frame, window, mode, gap)
                                q = scenario_q(recipe, fit['k'], area['integral_us_cm_s'])
                            except (ValueError, TypeError) as error:
                                rejected.append(dict(identity, stage='integration_or_quantity', reason=str(error)))
                                continue
                            unit_response = recipe['quantity_kind'] == 'per_liter_response_not_release'
                            rows.append(dict(identity, calibration_id=key[0], calibration_series_alias=key[1],
                                sensor_serial=edge['device_serial'], **{k: v for k, v in fit.items() if k not in ('trial_id','recipe_id','calibration_id','probe_alias','conductivity_basis')},
                                **{k: v for k, v in area.items() if k not in ('background_mode', 'gap_mode')},
                                q_m3_s=None if unit_response else q, q_m3_s_per_delivered_litre=q if unit_response else None,
                                quantity_kind=recipe['quantity_kind'], mass_g=recipe.get('mass_g'),
                                injection_solution_volume_ml=recipe.get('solution_volume_ml'),
                                result_class='unit_response' if unit_response else 'assumption_conditional',
                                capture_status=window['capture_status'], additional_recording_edge_ids=window.get('additional_recording_edge_ids', []),
                                recipe_evidence=recipe.get('evidence_class','source_ambiguous_alternative'),
                                unresolved_requirements=requirements[(tid,)]['blocking_factors'],
                                calibration_limitations=requirements[(tid,)]['calibration_evidence'],
                                capture_limitations=requirements[(tid,)]['capture_evidence'],
                                quantity_limitations=requirements[(tid,)]['quantity_evidence'],
                                source_refs=recipe['source_refs'], donor_ids=recipe.get('donor_ids', []),
                                recipe_assumptions=recipe['assumptions'], capture_assumptions=window['assumptions'],
                                event_link_status=window.get('event_link_status','source_linked'),
                                sensor_applicability=window.get('sensor_applicability','unverified_transfer_assumed'),
                                series_issues=series_issues, selected_for_primary=False, scientifically_accepted=False))
            candidates = [r for r in rows if r['trial_id'] == tid]
            qs = [r['q_m3_s'] for r in candidates if r['q_m3_s'] is not None]
            summaries.append(dict(trial_id=tid, recipe_count=len(case['recipes']), window_count=len(windows[tid]),
                scenario_count=len(candidates), q_min_m3_s=min(qs) if qs else None,
                q_max_m3_s=max(qs) if qs else None, unit_response_count=sum(r['result_class']=='unit_response' for r in candidates),
                disposition='conditional_scenarios' if qs else ('unit_response_only' if candidates else 'no_computable_scenario'),
                unresolved_requirements=requirements[(tid,)]['blocking_factors'],
                calibration_limitations=requirements[(tid,)]['calibration_evidence'],
                capture_limitations=requirements[(tid,)]['capture_evidence'],
                quantity_limitations=requirements[(tid,)]['quantity_evidence'],
                selection='All source-admissible alternatives retained; no selection by proximity to other Q values.',
                range_interpretation='Range of explicit assumptions, not a confidence interval or validated discharge range.',
                scientifically_accepted=False))
        parameters, working, working_summary = working_tables(config, rows, requirements)
        for name, values, empty in [('scenario_estimates', rows, ['trial_id','q_m3_s']),
                                    ('scenario_calibrations', fits, ['trial_id','recipe_id','k']),
                                    ('scenario_rejections', rejected, ['trial_id','reason']),
                                    ('scenario_by_release', summaries, ['trial_id','disposition'])]:
            slug._table(stage/f'{name}.csv', values, empty)
        if config.get('working_protocol'):
            for name, values, empty in [('working_parameters', parameters, ['trial_id','field','value']),
                                       ('working_estimates', working, ['trial_id','q_m3_s']),
                                       ('working_by_release', working_summary, ['trial_id','disposition'])]:
                slug._table(stage/f'{name}.csv', values, empty)
        (stage/'scenario_settings.json').write_text(matching._json(config)+'\n')
        (stage/'historical_code.json').write_text(matching._json(historical)+'\n')
        return reuse.write_run_info(stage, pins, scope='Assumption-explicit discharge recovery experiments',
            release_count=len(summaries), scenario_count=len(rows), rejected_scenarios=len(rejected),
            conditional_q_releases=sum(s['disposition']=='conditional_scenarios' for s in summaries),
            unit_response_releases=sum(s['disposition']=='unit_response_only' for s in summaries),
            working_q_releases=sum(s['disposition']=='working_conditional_q' for s in working_summary),
            working_protocol_releases=sum(s['working_recipe_count'] > 0 for s in working_summary),
            primary_q_promotions=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('config', 'pairing', 'calibration', 'baseline', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(argv)
    info = run_scenarios(args.config, args.pairing, args.calibration, args.baseline, args.output)
    print(matching._json({k: info[k] for k in ('release_count','scenario_count','conditional_q_releases','unit_response_releases')}))


if __name__ == '__main__':
    main()
