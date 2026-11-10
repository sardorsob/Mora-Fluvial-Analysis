"""Render pulse evidence from the pinned mass-slug run without recomputing Q."""
from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from . import calibration_reuse, mass_slug, matching


def _rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def render_pulses(bundle: Path, figure_dir: Path, *, root: Path, mass_dir: Path):
    """Render the saved recording/channel attempts into figure_dir/mass/pulses."""
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
    pairing = candidate_path.parent
    pair, _ = calibration_reuse.verify_bundle(pairing, root)
    recordings = {r['recording_edge_id']: r for r in _rows(pairing/'recording_candidates.csv')}
    decisions = mass_slug._read_windows(mass/'pulse_windows_used.json')
    estimates = {(r['trial_id'], r['logical_recording_id'], r['conductivity_basis']): r
                 for r in _rows(mass/'discharge_estimates.csv') if r['coefficient_source'] == 'trial_specific'}
    outcomes = _rows(mass/'recording_outcomes.csv')
    flagged = {r['trial_id'] for r in _rows(bundle/'tables/discharge_by_release.csv')
               if r['source_background_discrepancy'].lower() == 'true'}
    background_notes = {r['trial_id']: r for r in _rows(bundle/'tables/field_note_comparison.csv')
                        if r['quantity'] == 'specific_conductivity_background'}
    dest = Path(figure_dir)/'mass/pulses'
    dest.mkdir(parents=True, exist_ok=True)
    for row in outcomes:
        key = row['trial_id'], row['logical_recording_id'], row['channel']
        edge = recordings[row['recording_edge_id']]
        frame, _ = mass_slug.prepare_series(mass_slug._recording_samples(
            edge, pair, root/'salt_dilution/data/processed', root), row['channel'])
        decision = decisions[key]
        fig, ax = plt.subplots(figsize=(8.2, 5.4), layout='constrained')
        for _, part in frame.groupby('segment', sort=True):
            ax.plot(part.timestamp, part.ec, color='#176080', linewidth=1.5)
        if row['outcome'] == 'computed':
            estimate = estimates[key]
            windows = json.loads(estimate['windows'])
            pre, pulse, post = mass_slug._window_parts(frame, windows)
            background = mass_slug._background(pulse.t_s.to_numpy(), pre, post, 'linear')
            ax.axvspan(pre.timestamp.iloc[0], pre.timestamp.iloc[-1], color='#8b8f92', alpha=.19, label='Background windows')
            ax.axvspan(post.timestamp.iloc[0], post.timestamp.iloc[-1], color='#8b8f92', alpha=.19)
            ax.plot(pulse.timestamp, background, color='#30383b', linestyle='--', linewidth=1.3, label='Linear background')
            ax.fill_between(pulse.timestamp, background, pulse.ec.to_numpy(), color='#176080', alpha=.20, label='Signed pulse area')
            status = f"Proposed Q = {float(estimate['q_m3_s']):.3f} m³/s"
            ax.legend(loc='best', frameon=False, fontsize=12)
        else:
            status = 'Blocked: ' + row['reason'].replace('_', ' ')
        ax.set_title(f"{row['trial_id']} · {row['channel'].title()} conductivity\n{status}", loc='left', fontsize=15, weight='bold')
        ax.set_ylabel('Conductivity (µS/cm)', fontsize=12)
        ax.tick_params(labelsize=12)
        dates = frame.timestamp.dt.strftime('%Y-%m-%d').unique()
        date_label = dates[0] if len(dates) == 1 else f'{dates[0]} to {dates[-1]}'
        ax.set_xlabel(f'Recorded clock · {date_label}\nTimezone alignment unresolved', fontsize=12)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.grid(axis='y', color='#d9dfe2', linewidth=.7)
        ax.spines[['top', 'right']].set_visible(False)
        note = ('Proposed windows. Field sign-off pending.'
                if row['outcome'] == 'computed' else
                'No Q calculated. ' + (row['detail'] or decision.get('reason', 'Capture blocked.')))
        if key[0] in flagged:
            comparison = background_notes[key[0]]
            notebook = float(comparison['notebook_numeric_value'])
            measured = float(comparison['native_measurement_us_cm'])
            note += f'\nSpecific background differs: notebook {notebook:g}, recording {measured:.2f} µS/cm.'
        footer = (note + '\nSource: saved Aqua TROLL recording and pulse review.\n'
                  + 'Recording: ' + key[1])
        fig.text(.08, -.02, '\n'.join('\n'.join(textwrap.wrap(line, 63))
                                      for line in footer.split('\n')),
                 fontsize=13, va='top', color='#424b50')
        name = f"{key[0]}_{key[1].replace(':', '-')}_{key[2]}.png"
        fig.savefig(dest/name, dpi=150, bbox_inches='tight')
        plt.close(fig)
