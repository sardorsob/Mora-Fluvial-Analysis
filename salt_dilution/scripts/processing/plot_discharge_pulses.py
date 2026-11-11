"""Render pulse evidence from the pinned mass-slug run without recomputing Q."""
from __future__ import annotations

import csv
import json
import textwrap
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from . import mass_slug, matching
from .plot_discharge_summary import CONDITIONAL_SUPPORT, SITE_NAMES, METHOD_NAMES


BLOCKED_LABELS = {
    'no_pre_pulse_background': 'Pre-pulse background window not established',
    'pulse_truncated': 'Pulse end not established',
    'tail_not_settled': 'Pulse end not established',
    'pulse_start_missing': 'Pulse start not established',
    'release_alignment_unresolved': 'Release and pulse timing unresolved',
    'calibration_not_mass_compatible': 'Calibration recipe or units unresolved',
    'coefficient_unit_method_mismatch': 'Calibration units do not match the method',
    'no_compatible_coefficient_for_sensor': 'Calibration unavailable for this sensor',
    'edge_calibration_identity_disagrees_with_native_audit': 'Calibration sensor identity conflicts',
    'delivered_solution_volume_unavailable': 'Delivered solution volume unavailable',
    'solution_volume_source_unresolved': 'Solution volume source unresolved',
    'pulse_or_background_crosses_segment_gap': 'Sampling gap inside pulse or background',
    'missing_cells_in_windows': 'Pulse or background readings missing',
}


def _clock_label(evidence):
    if (evidence.get('effective_measurement_basis') == 'participant_confirmed_fixed_field_offset'
            and evidence.get('effective_offset_seconds') == -28800):
        return 'Field time (PST, UTC−08:00)'
    return 'Recorded field clock'


def _blocked_label(reason):
    code = reason.strip().split(';', 1)[0]
    return BLOCKED_LABELS.get(code, code.replace('_', ' ').capitalize() if code else 'Discharge unavailable')


def _estimate_caption(estimate):
    support = estimate.get('estimate_support')
    status = 'Conditional' if support in CONDITIONAL_SUPPORT else 'Proposed'
    notes = []
    if support == 'conditional_calibration_variant':
        notes.append('Uses an alternate calibration worksheet.')
    if str(estimate.get('nominal_equals_delivered_mass_assumed', '')).lower() == 'true':
        notes.append('Nominal salt mass assumed delivered.')
    if support == 'conditional_reported_volume' or estimate.get('solution_volume_basis') == 'reported_delivery_assumed':
        notes.append('Reported solution volume assumed delivered.')
    notes.append('Field acceptance pending.')
    return status, ' '.join(notes)


def _rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def _capture_scenarios(rows):
    result = {}
    for row in rows:
        key = row['trial_id'], row['logical_recording_id'], row['conductivity_basis']
        if key in result:
            raise ValueError(f'Duplicate capture scenario: {key}')
        result[key] = row
    return result


def render_pulses(bundle: Path, figure_dir: Path, *, root: Path, mass_dir: Path) -> set[Path]:
    """Render available recording/channel traces and return their relative paths."""
    bundle, root = Path(bundle).resolve(), Path(root).resolve()
    source = json.loads((bundle/'provenance/source_bundles.json').read_text())['mass']
    mass = Path(mass_dir).resolve()
    if matching._hash(mass/'run_info.json') != source['run_info_sha256']:
        raise ValueError('Mass run provenance mismatch')
    info = json.loads((mass/'run_info.json').read_text())
    pins = {item['path']: item['sha256'] for item in info['outputs']}
    for name, stable in [('recording_outcomes.csv', 'tables/recording_outcomes.csv'),
                         ('discharge_estimates.csv', 'tables/discharge_estimates.csv'),
                         ('pulse_windows_used.json', 'settings/pulse_windows.json')]:
        if matching._hash(mass/name) != pins[name] or matching._hash(bundle/stable) != pins[name]:
            raise ValueError(f'Saved mass output mismatch: {name}')
    candidates = [item for item in info['inputs']
                  if Path(item['path']).name == 'recording_candidates.csv']
    if len(candidates) != 1:
        raise ValueError('Mass manifest must pin exactly one recording candidates table')
    candidate_path = matching._path(candidates[0]['path'], root).resolve()
    if not candidate_path.is_relative_to(root) or matching._hash(candidate_path) != candidates[0]['sha256']:
        raise ValueError('Pairing table outside root or differs from mass manifest')
    pair_path = candidate_path.with_name('run_info.json')
    pair_pins = [item for item in info['inputs'] if matching._path(item['path'], root).resolve() == pair_path]
    if len(pair_pins) != 1 or matching._hash(pair_path) != pair_pins[0]['sha256']:
        raise ValueError('Pairing manifest differs from mass manifest')
    pair = json.loads(pair_path.read_text())
    if {'path': candidate_path.name, 'sha256': candidates[0]['sha256']} not in pair['outputs']:
        raise ValueError('Recording candidates do not match the saved pairing manifest')
    recordings = {r['recording_edge_id']: r for r in _rows(candidate_path)}
    decisions = mass_slug._read_windows(mass/'pulse_windows_used.json')
    trial_estimates = [r for r in _rows(mass/'discharge_estimates.csv') if r['coefficient_source'] == 'trial_specific']
    estimates = {(r['trial_id'], r['logical_recording_id'], r['conductivity_basis']): r for r in trial_estimates}
    if len(estimates) != len(trial_estimates):
        raise ValueError('Duplicate trial-specific estimate for a recording/channel')
    outcomes = _rows(mass/'recording_outcomes.csv')
    releases = {r['trial_id']: r for r in _rows(bundle/'tables/discharge_by_release.csv')}
    scenario_path = bundle/'tables/conditional_discharge.csv'
    scenarios = _capture_scenarios(_rows(scenario_path) if scenario_path.is_file() else [])
    background_notes = {r['trial_id']: r for r in _rows(bundle/'tables/field_note_comparison.csv')
                        if r['quantity'] == 'specific_conductivity_background'}
    dest = Path(figure_dir)/'mass/pulses'
    dest.mkdir(parents=True, exist_ok=True)
    rendered = set()
    for row in outcomes:
        key = row['trial_id'], row['logical_recording_id'], row['channel']
        edge = recordings[row['recording_edge_id']]
        if (edge['trial_id'], edge['logical_recording_id']) != key[:2]:
            raise ValueError(f'Pulse outcome does not match its recording: {key}')
        samples = mass_slug._recording_samples(edge, pair, root/'salt_dilution/data/processed', root)
        computed = row['outcome'] == 'computed'
        try:
            frame, _ = mass_slug.prepare_series(samples, row['channel'])
        except ValueError:
            if computed:
                raise
            continue
        decision = decisions.get(key, {})
        release = releases[key[0]]
        site = SITE_NAMES.get(release['site_alias'], release['site_alias'])
        day = date.fromisoformat(release['field_date'])
        trial = key[0].rsplit('-', 1)[-1]
        trial_label = f'Trial {int(trial[1:])}' if trial.startswith('T') and trial[1:].isdigit() else trial
        title = f'{site}, {day.day} {day:%B %Y} · {trial_label}'
        channel_label = f"{key[2].title()} conductivity"
        fig, ax = plt.subplots(figsize=(8.2, 5.4), layout='constrained')
        for _, part in frame.groupby('segment', sort=True):
            ax.plot(part.timestamp, part.ec, color='#176080', linewidth=1.5)
        if computed:
            estimate = estimates[key]
            if estimate['recording_edge_id'] != row['recording_edge_id']:
                raise ValueError(f'Pulse estimate does not match its recording: {key}')
            if estimate['recording_origin_local'] != str(frame.timestamp.iloc[0]):
                raise ValueError(f'Pulse estimate does not match its recording origin: {key}')
            windows = json.loads(estimate['windows'])
            pre, pulse, post = mass_slug._window_parts(frame, windows)
            mode = estimate.get('background_mode') or 'linear'
            ax.axvspan(pre.timestamp.iloc[0], pre.timestamp.iloc[-1], color='#8b8f92', alpha=.19, label='Background windows')
            ax.axvspan(post.timestamp.iloc[0], post.timestamp.iloc[-1], color='#8b8f92', alpha=.19)
            for i, (_, part) in enumerate(pulse.groupby('segment', sort=True)):
                background = mass_slug._background(part.t_s.to_numpy(), pre, post, mode)
                ax.plot(part.timestamp, background, color='#30383b', linestyle='--', linewidth=1.3,
                        label=f'{mode.title()} background' if i == 0 else None)
                ax.fill_between(part.timestamp, background, part.ec.to_numpy(), color='#176080', alpha=.20,
                                label='Signed pulse area' if i == 0 else None)
            status, note = _estimate_caption(estimate)
            title += f"\n{status} Q = {float(estimate['q_m3_s']):.3f} m³/s"
            method = METHOD_NAMES.get(estimate.get('discharge_method') or 'mass_slug', '')
            channel_label += f' · {method}' if method else ''
            ax.legend(loc='best', frameon=False, fontsize=12)
        else:
            title += '\n' + _blocked_label(row['reason'])
        ax.set_title(title, loc='left', fontsize=15, weight='bold')
        ax.text(1, 1.015, channel_label, transform=ax.transAxes, ha='right', va='bottom',
                fontsize=12, color='#424b50')
        ax.set_ylabel('Conductivity (µS/cm)', fontsize=12)
        ax.tick_params(labelsize=12)
        dates = frame.timestamp.dt.strftime('%Y-%m-%d').unique()
        date_label = dates[0] if len(dates) == 1 else f'{dates[0]} to {dates[-1]}'
        time_evidence = json.loads(edge.get('time_evidence') or '{}')
        ax.set_xlabel(f'{_clock_label(time_evidence)} · {date_label}', fontsize=12)
        start, end = mdates.date2num([frame.timestamp.iloc[0], frame.timestamp.iloc[-1]])
        ax.set_xticks([start + (end-start)*i/4 for i in range(5)])
        tick_format = '%H:%M:%S' if len(dates) == 1 else '%d %b\n%H:%M'
        ax.xaxis.set_major_formatter(mdates.DateFormatter(tick_format, tz=frame.timestamp.dt.tz))
        ax.grid(axis='y', color='#d9dfe2', linewidth=.7)
        ax.spines[['top', 'right']].set_visible(False)
        if computed:
            chronology = json.loads(edge.get('chronology_evidence') or '{}')
            if chronology.get('clock_basis') in ('reviewed_whole_file_relationship', 'source_confirmed_file_relationship'):
                note += ' File match established. Release-to-pulse timing unverified.'
        else:
            if key in scenarios:
                note = (f"No selected Q. Capture-assumed scenario Q = {float(scenarios[key]['q_m3_s']):.3f} m³/s; "
                        'full pulse capture is unverified. See the conditional-discharge figure.')
            else:
                note = 'No selected Q. ' + (row.get('detail') or decision.get('reason', ''))
        if release.get('source_background_discrepancy', '').lower() == 'true' and key[0] in background_notes:
            comparison = background_notes[key[0]]
            notebook = float(comparison['notebook_numeric_value'])
            measured = float(comparison['native_measurement_us_cm'])
            note += f'\nSpecific background (µS/cm) was {notebook:g} in the notebook and {measured:.2f} in the recording.'
        footer = (note + '\nSource · Saved Aqua TROLL recording and pulse review\n'
                  + 'Recording · ' + key[1])
        fig.text(.08, -.02, '\n'.join('\n'.join(textwrap.wrap(line, 63))
                                      for line in footer.split('\n')),
                 fontsize=13, va='top', color='#424b50')
        name = f"{key[0]}_{key[1].replace(':', '-')}_{key[2]}.png"
        path = Path('mass/pulses') / name
        if path in rendered:
            raise ValueError(f'Duplicate pulse outcome: {key}')
        fig.savefig(dest/name, dpi=150, bbox_inches='tight')
        plt.close(fig)
        rendered.add(path)
    return rendered
