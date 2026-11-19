"""Compare saved, background-relative salt pulses within each field day."""
from collections import defaultdict
from datetime import date
from textwrap import fill
from typing import NamedTuple

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import numpy as np

from . import plot_discharge_summary as style


class PulseTrace(NamedTuple):
    serial: str
    minutes: np.ndarray
    excess: np.ndarray
    segment: np.ndarray
    diagnostic: bool
    unsettled_tail: bool
    unit_response: str


PROBE_STYLES = ((style.BLUE, '-'), (style.ORANGE, '--'), ('#5F487C', '-.'))
Q_LABELS = {'selected_proposed': 'Proposed', 'selected_conditional': 'Selected conditional',
            'working_conditional': 'Working conditional'}


def record_trace(traces, row, pulse, background, start, *, diagnostic: bool = False) -> None:
    """Keep observed samples and their segment boundaries, never a bridged line."""
    key = (row['recording_edge_id'], row.get('window_id', ''), row['conductivity_basis'])
    traces[row['trial_id']][key] = PulseTrace(
        row['sensor_serial'] or '', (pulse.t_s.to_numpy() - start) / 60,
        pulse.ec.to_numpy() - background, pulse.segment.to_numpy(),
        diagnostic, 'unsettled_tail' in (row.get('capture_status') or ''),
        row.get('q_m3_s_per_delivered_litre') or '',
    )


def _probe_values(values: list[tuple[str, float]]) -> str:
    probes = defaultdict(list)
    for serial, value in sorted(values):
        probes[serial].append(f'{value:.3g}')
    return fill(' · '.join(f'{serial or "Unknown probe"} {" / ".join(readings)}'
                           for serial, readings in probes.items()), width=40)


def _q_caption(release: dict, rows: list[dict], series: list[PulseTrace]) -> str:
    if not rows:
        if 'spilled' in release.get('source_notes', '').lower():
            caption = 'No release Q · delivered dose unknown'
            values = [(v.serial, float(v.unit_response)) for v in series if v.unit_response]
            if values:
                caption += '\nResponse (m³/s per L delivered)\n' + _probe_values(values)
            return caption
        return 'No release Q'
    groups = defaultdict(list)
    for row in rows:
        groups[row['status']].append((row.get('sensor_serial') or '', float(row['q_m3_s'])))
    captions = []
    for status, values in groups.items():
        label = Q_LABELS[status]
        if len(values) == len(rows) == 1:
            captions.append(f'{label} Q · {values[0][1]:.3g} m³/s')
        else:
            captions.append(f'{label} Q (m³/s)\n{_probe_values(values)}')
    return '\n'.join(captions)


def _plot_trace(ax, trace: PulseTrace, color: str, linestyle: str) -> None:
    for group in dict.fromkeys(trace.segment):
        mask = trace.segment == group
        x, y = trace.minutes[mask], trace.excess[mask]
        # Segments are the observed runs. Show sparse samples and mark gap edges.
        markevery = None if len(x) <= 35 else [0, len(x) - 1]
        markers = len(x) <= 35 or trace.segment[0] != trace.segment[-1]
        ax.plot(x, y, color=color, linestyle=linestyle, lw=1.65,
                marker='o' if markers else None, markersize=3.1, markevery=markevery, zorder=3)
        ax.fill_between(x, y, 0, facecolor=color, alpha=.09 if trace.diagnostic else .19, linewidth=0)


def day_figure(site, day, releases, traces, points):
    channels = [c for c in ('specific', 'actual')
                if any(k[2] == c for r in releases for k in traces[r['trial_id']])]
    size = len(releases)
    cols = 2
    rows = (size + cols - 1) // cols
    fig = plt.figure(figsize=(9.15, (3.12 * rows + .5) * max(1, len(channels)) + 1.45),
                     layout='constrained')
    site_name = style.SITE_NAMES.get(site, site)
    fig.suptitle(f'Salt pulses by trial\n{site_name}  ·  {date.fromisoformat(day):%d %B %Y}',
                 x=.035, ha='left', fontsize=20, fontweight='bold', color=style.INK)
    if not channels:
        ax = fig.subplots()
        ax.set_axis_off()
        for i, r in enumerate(releases):
            trial = int(r['trial_id'].rsplit('T', 1)[-1])
            ax.text(.015, 1 - (i + .5) / size, f'Trial {trial}   ·   No saved pulse window or release Q',
                    transform=ax.transAxes, fontsize=14, color=style.INK)
        fig.supxlabel('Source · MORA release inventory', fontsize=11, color='#47545A')
        return fig
    grids = fig.subfigures(len(channels), 1, squeeze=False).ravel()
    for channel, subfig in zip(channels, grids):
        by_trial = {r['trial_id']: [v for k, v in sorted(traces[r['trial_id']].items()) if k[2] == channel]
                    for r in releases}
        serials = sorted({v.serial for series in by_trial.values() for v in series})
        probe_styles = {serial: PROBE_STYLES[i % len(PROBE_STYLES)] for i, serial in enumerate(serials)}
        subfig.suptitle(f'{channel.title()} conductivity excess (µS/cm)', x=.043, ha='left',
                         fontsize=15, fontweight='bold', color=style.INK)
        handles = [Line2D([], [], color=color, linestyle=linestyle,
                          label=f'Probe {serial}' if serial else 'Unknown probe')
                   for serial, (color, linestyle) in probe_styles.items()]
        subfig.legend(handles=handles, loc='upper right', bbox_to_anchor=(.99, 1),
                      ncols=len(serials), fontsize=10.5, frameon=False, columnspacing=1.1)
        axes = subfig.subplots(rows, cols, squeeze=False, sharex=True, sharey=True).ravel()
        for ax, release in zip(axes, releases):
            tid = release['trial_id']
            series = by_trial[tid]
            q_rows = [p for p in points[tid] if p['conductivity_basis'] == channel]
            trial = int(tid.rsplit('T', 1)[-1])
            notes = []
            if any(v.diagnostic for v in series):
                notes.append('Diagnostic pulse')
                if any(v.unsettled_tail for v in series):
                    notes.append('Unsettled tail')
            if any(v.segment[0] != v.segment[-1] for v in series):
                notes.append('Recording gap')
            heading = ' · '.join([f'Trial {trial}', *notes])
            result = _q_caption(release, q_rows, series)
            if not q_rows and points[tid]:
                result += ' on this channel'
            ax.set_title(f'{heading}\n{result}', loc='left', fontsize=12.25, color=style.INK, pad=6)
            if not series:
                ax.text(.5, .5, 'No saved pulse window', transform=ax.transAxes,
                        ha='center', va='center', color=style.GRAY, fontsize=12)
            for v in series:
                _plot_trace(ax, v, *probe_styles[v.serial])
            ax.axhline(0, color='#547078', ls='--', lw=.9, zorder=2)
            ax.yaxis.set_major_locator(MaxNLocator(4, prune='both'))
            ax.xaxis.set_major_locator(MaxNLocator(5))
            ax.spines[['top', 'right']].set_visible(False)
            ax.grid(axis='y', color='#DDE3E6', lw=.65)
            ax.tick_params(labelsize=12)
            ax.tick_params(labelbottom=True)
        axes[0].set_xlim(left=0)
        for ax in axes[size:]:
            ax.set_axis_off()
        subfig.supxlabel('Minutes from the start of each pulse window', fontsize=12, color=style.INK)
    diagnostic = any(v.diagnostic for r in releases for v in traces[r['trial_id']].values())
    note = 'Shading shows signed observed area. Dashed zero marks the background.'
    if diagnostic:
        note += '\nPale shading marks diagnostic windows without a chosen discharge estimate.'
    else:
        note += '\nConditional Q depends on assumptions. All Q awaits scientific acceptance.'
    fig.supxlabel(note + '\nSource · MORA field conductivity recordings and discharge analysis',
                  x=.043, ha='left', fontsize=11, color=style.GRAY)
    return fig


def render_days(releases, traces, points, output):
    by_day = defaultdict(list)
    by_trial = defaultdict(list)
    for p in points:
        by_trial[p['trial_id']].append(p)
    for r in releases:
        if r['category'] != 'excluded_practice':
            by_day[r['site_alias'], r['field_date']].append(r)
    for (site, day), members in sorted(by_day.items()):
        if len(members) == 1:
            continue  # The single-trial figure already answers the day question.
        members.sort(key=lambda r: r['trial_id'])
        path = f'by_day/{site.lower()}_{day}_trials.png'
        style._save(day_figure(site, day, members, traces, by_trial), output / path)
        for r in members:
            yield dict(figure=path, kind='day_comparison', site=site, year=day[:4],
                       date_start=day, trial_id=r['trial_id'],
                       source_table='plot_estimates.csv;release_coverage.csv')
