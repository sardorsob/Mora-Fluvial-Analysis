"""Compare saved, background-relative salt pulses within each field day."""
from collections import defaultdict
from datetime import date

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from . import plot_discharge_summary as style


def record_trace(traces, row, pulse, background, start):
    """Keep observed samples and their segment boundaries, never a bridged line."""
    key = (row['recording_edge_id'], row.get('window_id', ''), row['conductivity_basis'])
    traces[row['trial_id']][key] = (
        row['sensor_serial'], (pulse.t_s.to_numpy() - start) / 60,
        pulse.ec.to_numpy() - background, pulse.segment.to_numpy(),
    )


def day_figure(site, day, releases, traces, points):
    channels = [c for c in ('specific', 'actual')
                if any(k[2] == c for r in releases for k in traces[r['trial_id']])]
    size = len(releases)
    cols = 2
    rows = (size + cols - 1) // cols
    fig = plt.figure(figsize=(8.8, 2.6 * rows * max(1, len(channels)) + 1.55),
                     layout='constrained')
    site_name = {'NISQ': 'Nisqually', 'PAR': 'Paradise'}.get(site, site)
    fig.suptitle(f'{site_name} · {date.fromisoformat(day):%d %B %Y}\n'
                 'Salt pulses by trial',
                 x=.035, ha='left', fontsize=17, fontweight='bold', color=style.INK)
    if not channels:
        ax = fig.subplots()
        ax.set_axis_off()
        for i, r in enumerate(releases):
            trial = int(r['trial_id'].rsplit('T', 1)[-1])
            ax.text(.015, .73 - i * .22, f'Trial {trial}   ·   No chosen pulse window or Q',
                    transform=ax.transAxes, fontsize=14, color=style.INK)
        fig.supxlabel('Source · MORA release inventory', fontsize=11, color='#47545A')
        return fig
    grids = fig.subfigures(len(channels), 1, squeeze=False).ravel()
    for channel, subfig in zip(channels, grids):
        subfig.suptitle(f'{channel.title()} conductivity above background  (µS/cm)', x=.045, ha='left',
                         fontsize=13, fontweight='bold', color=style.INK)
        axes = subfig.subplots(rows, cols, squeeze=False, sharex=True, sharey=True).ravel()
        for ax, release in zip(axes, releases):
            tid = release['trial_id']
            series = [v for k, v in sorted(traces[tid].items()) if k[2] == channel]
            q_rows = [p for p in points[tid] if p['conductivity_basis'] == channel]
            values = sorted({float(p['q_m3_s']) for p in q_rows})
            if not values:
                result = 'No release Q for this channel'
            elif len(values) == 1:
                status = 'Proposed' if all(p['status'] == 'selected_proposed' for p in q_rows) else 'Conditional'
                result = f'{status} Q {values[0]:.3g} m³/s'
            else:
                result = f'Q alternatives {values[0]:.3g}–{values[-1]:.3g} m³/s'
            trial = int(tid.rsplit('T', 1)[-1])
            gap = ' · Recording gap' if any(len(set(v[3])) > 1 for v in series) else ''
            ax.set_title(f'Trial {trial}{gap}\n{result}', loc='left', fontsize=12, color=style.INK)
            if not series:
                ax.text(.5, .5, 'No saved pulse window', transform=ax.transAxes,
                        ha='center', va='center', color='#47545A', fontsize=11)
            labels = defaultdict(int)
            for i, (serial, x, ec, segment) in enumerate(series):
                labels[serial] += 1
                label = f'{serial or "Unknown probe"}'
                if labels[serial] > 1:
                    label += f' · window {labels[serial]}'
                for j, group in enumerate(dict.fromkeys(segment)):
                    mask = segment == group
                    ax.plot(x[mask], ec[mask], color=(style.BLUE, '#974311', '#5F487C')[i % 3],
                            linestyle=('-', '--', '-.', ':')[i % 4], lw=1.5,
                            marker='.' if mask.sum() == 1 else None,
                            label=label if j == 0 else None)
            if len(series) > 1:
                ax.legend(loc='upper right', fontsize=10, frameon=False)
            ax.axhline(0, color='#547078', lw=.7)
            ax.yaxis.set_major_locator(MaxNLocator(5))
            ax.xaxis.set_major_locator(MaxNLocator(5))
            ax.spines[['top', 'right']].set_visible(False)
            ax.grid(axis='y', color='#DDE3E6', lw=.65)
            ax.tick_params(labelsize=11)
            ax.set_xlim(left=0)
            if ax in axes[max(0, size-cols):size]:
                ax.tick_params(labelbottom=True)
        for ax in axes[size:]:
            ax.set_axis_off()
        subfig.supxlabel('Minutes from the start of each saved pulse window', fontsize=11.5)
    fig.supxlabel('Source · MORA field recordings · Q awaits field acceptance',
                  fontsize=11.5, color='#47545A')
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
