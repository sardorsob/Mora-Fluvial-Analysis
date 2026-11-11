"""Plot saved selected and working discharge estimates without choosing new Q values."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd

from . import calibration_reuse as reuse, discharge_scenarios as scenarios
from . import mass_slug as slug, matching, plot_discharge_summary as style


def read_rows(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def combine_estimates(selected, working, releases):
    """Keep one row per saved estimate; a unit response is never a release Q."""
    release_index = {r['trial_id']: r for r in releases}
    if len(release_index) != len(releases):
        raise ValueError('Duplicate release ID')
    selected_ids = {r['trial_id'] for r in selected}
    if selected_ids & {r['trial_id'] for r in working}:
        raise ValueError('Selected and working releases overlap')
    result, seen = [], set()
    for source, rows in [('selected', selected), ('working', working)]:
        for row in rows:
            tid = row['trial_id']
            if tid not in release_index or release_index[tid]['category'] == 'excluded_practice':
                raise ValueError('Unknown or practice release in estimates')
            if source == 'working' and row['result_class'] == 'unit_response':
                if row['q_m3_s']:
                    raise ValueError('Unit response must not have release Q')
                continue
            q = scenarios.positive(row['q_m3_s'], 'Q')
            k = scenarios.positive(row['k'], 'K')
            area = scenarios.positive(row['integral_us_cm_s'], 'area')
            unit = row['coefficient_unit']
            if unit == '(mg/L) / (uS/cm)':
                quantity = scenarios.positive(row['mass_g'], 'salt mass')
            elif unit == '(mL/mL) / (uS/cm)':
                quantity = scenarios.positive(row['injection_solution_volume_ml'], 'solution volume') / 1e6
            else:
                raise ValueError('Unknown coefficient unit')
            if not math.isclose(q, quantity/k/area, rel_tol=1e-10):
                raise ValueError('Saved Q does not agree with quantity, K and area')
            key = (tid, row['recording_edge_id'], row['conductivity_basis'], row['calibration_id'],
                   row.get('calibration_series_alias', ''), row.get('window_id', ''), row.get('recipe_id', ''))
            if key in seen:
                raise ValueError('Duplicate estimate')
            seen.add(key)
            if row['conductivity_basis'] not in style.CHANNEL_STYLE:
                raise ValueError('Unknown conductivity channel')
            status = 'working_conditional' if source == 'working' else (
                'selected_conditional' if row.get('estimate_support', '').startswith('conditional_') else 'selected_proposed')
            result.append(dict(trial_id=tid, field_date=release_index[tid]['field_date'],
                site=release_index[tid]['site_alias'], status=status, q_m3_s=q,
                recording_edge_id=row['recording_edge_id'], sensor_serial=row['sensor_serial'],
                conductivity_basis=row['conductivity_basis'], calibration_id=row['calibration_id'],
                calibration_series_alias=row.get('calibration_series_alias', ''),
                window_id=row.get('window_id', ''), recipe_id=row.get('recipe_id', ''),
                source_table='working_estimates.csv' if source == 'working' else 'tables/discharge_estimates.csv',
                scientifically_accepted=False))
    return result


def comparison(points, releases, site, year, *, period_label=None):
    rows = sorted([r for r in releases if r['site_alias'] == site and r['field_date'].startswith(year)
                   and r['category'] != 'excluded_practice'], key=lambda r: r['trial_id'])
    groups = defaultdict(list)
    for p in points:
        groups[p['trial_id']].append(p)
    count = sum(bool(groups[r['trial_id']]) for r in rows)
    title = f'{style.SITE_NAMES[site]} discharge · {period_label or year}'
    displayed=[]
    for row in rows:
        calibrations=sorted({p['calibration_id'] for p in groups[row['trial_id']]})
        for cal in calibrations or [None]:
            displayed.append((row,cal,len(calibrations)>1))
    fig, ax = style._base(title, f'{count} of {len(rows)} releases have Q estimates · awaiting scientific acceptance',
                          row_count=len(displayed), extra_line=True, width=8.2, left=.29)
    colors = {'selected_proposed': style.BLUE, 'working_conditional': style.ORANGE,
              'selected_conditional': style.ORANGE}
    values = []
    labels=[]
    statuses=set()
    for i, (row,cal,multiple) in enumerate(displayed):
        members = sorted([p for p in groups[row['trial_id']] if p['calibration_id']==cal], key=lambda p: (p['sensor_serial'], p['conductivity_basis']))
        offsets = np.linspace(-.3, .3, len(members)) if len(members) > 1 else [0.]
        label=f"{datetime.fromisoformat(row['field_date']):%d %b} · {row['trial_id'].rsplit('-',1)[-1]}"
        labels.append(label+(' / '+cal.rsplit('-',1)[-1] if multiple else ''))
        for p, offset in zip(members, offsets):
            color = colors[p['status']]
            statuses.add(p['status'])
            ax.scatter(p['q_m3_s'], i+offset, s=36, marker=style.CHANNEL_STYLE[p['conductivity_basis']][1],
                       facecolors=color if p['status']=='selected_proposed' else 'none', edgecolors=color, linewidth=1.5, zorder=3)
            values.append(p['q_m3_s'])
        if not members:
            reason = 'Delivered dose unknown' if row['trial_id'].endswith('20250903-T02') else 'Stock stage unresolved'
            ax.text(.03, i, reason, transform=ax.get_yaxis_transform(), fontsize=12, color=style.GRAY, va='center')
    ax.set_yticks(range(len(displayed)), labels)
    ax.set_ylim(len(displayed)-.5, -.5)
    ax.set_xlim(0, max(values)*1.12)
    ax.set_xlabel('Discharge Q (m³/s) · linear scale', fontsize=12)
    names={'selected_proposed':'Selected · proposed','selected_conditional':'Selected · conditional','working_conditional':'Working · conditional'}
    handles=[Line2D([],[],color=colors[s],marker='o',linestyle='',markerfacecolor=colors[s] if s=='selected_proposed' else 'none',label=names[s]) for s in names if s in statuses]
    style._legend(fig, ax, handles=handles)
    style._footer(fig, 'Circles: specific conductivity. Squares: actual conductivity.\n'
                  'Instrument and calibration estimates stay separate.\n'
                  'Spread is not a confidence interval.\n'
                  'Total uncertainty is unquantified. No estimates are averaged.\n'
                  'Conditional values depend on recipe, sensor or capture assumptions.',
                  'Source · MORA salt-dilution selected and working estimate tables')
    return fig


def coverage(points, releases):
    groups = defaultdict(set)
    for p in points:
        groups[p['status']].add(p['trial_id'])
    nisq = {r['trial_id'] for r in releases if r['site_alias']=='NISQ' and r['category']!='excluded_practice'}
    counts = [len(groups['selected_proposed'] & nisq), len(groups['working_conditional'] & nisq)]
    counts.append(len(nisq)-sum(counts))
    fig, ax = style._base(f'{sum(counts[:2])} of {len(nisq)} Nisqually releases have Q estimates',
                          'Selected and working results · 2025–2026', left=.31, width=8.2)
    labels = ['Selected · proposed', 'Working · conditional', 'No chosen release Q']
    for y, (n, color) in enumerate(zip(counts, [style.BLUE, style.ORANGE, style.GRAY])):
        ax.barh(y, n, color=color, height=.55)
        ax.text(n+.5, y, str(n), va='center', fontsize=13, color=style.INK)
    ax.set_yticks(range(3), labels)
    ax.set_ylim(2.6, -.6)
    ax.set_xlim(0, max(counts)*1.18)
    ax.set_xticks([])
    ax.set_xlabel('Number of releases', fontsize=12)
    practice = sum(r['site_alias']=='NISQ' and r['category']=='excluded_practice' for r in releases)
    style._footer(fig, f'{practice} practice releases excluded. Counts are releases, not channel fits.\n'
                  'Two unresolved stock stages and one spilled dose have no chosen Q.\n'
                  'All estimates await scientific acceptance.',
                  'Source · MORA release, selected-Q and working-Q tables')
    return fig


def pulse_figure(frame, window, rows):
    row = rows[0]
    area = scenarios.scenario_area(frame, window, row['background_mode'], row['gap_mode'])
    for item in rows:
        if not math.isclose(area['integral_us_cm_s'], float(item['integral_us_cm_s']), rel_tol=1e-10):
            raise ValueError('Rendered pulse integral differs from saved working estimate')
    parts = {name: frame.loc[frame.timestamp.between(*pd.to_datetime(window[name]))]
             if window.get(name) else frame.iloc[:0] for name in ('pre','pulse','post')}
    origin = pd.Timestamp(window['pulse'][0])
    minutes = lambda timestamps: (timestamps-origin).dt.total_seconds()/60
    left = pd.Timestamp(window['pre'][0]);right = pd.Timestamp((window.get('post') or window['pulse'])[1])
    shown = frame.loc[frame.timestamp.between(left-pd.Timedelta(seconds=10), right+pd.Timedelta(seconds=10))]
    tid = row['trial_id'];day = datetime.strptime(tid.split('-')[1], '%Y%m%d')
    title = f"Nisqually · {day:%d %b %Y} · {tid.rsplit('-',1)[-1]}"
    unit_response = row['result_class']=='unit_response'
    readings = ' · '.join(f"{r['calibration_id'].rsplit('-',1)[-1]}: {float(r['q_m3_s_per_delivered_litre'] if unit_response else r['q_m3_s']):.3f}" for r in rows)
    subtitle = ('Response per delivered litre' if unit_response else 'Conditional Q') + f' · {readings}' + (' m³/s per L' if unit_response else ' m³/s')
    fig, ax = plt.subplots(figsize=(8.2,6.4), dpi=180)
    fig.subplots_adjust(left=.13, right=.96, top=.74, bottom=.30)
    fig.text(.05,.96,title,fontsize=16,weight='bold',color=style.INK,va='top')
    fig.text(.05,.905,subtitle,fontsize=13,color=style.INK,va='top')
    fig.text(.05,.855,f"{row['conductivity_basis'].title()} conductivity · instrument {row['sensor_serial']}",fontsize=12,color=style.INK,va='top')
    for _, part in shown.groupby('segment', sort=True):
        ax.plot(minutes(part.timestamp),part.ec,color=style.BLUE,linewidth=1.5)
    for name in ('pre','post'):
        part=parts[name]
        if len(part):ax.axvspan(minutes(part.timestamp).iloc[0],minutes(part.timestamp).iloc[-1],color='#E1E5E8',zorder=0)
    pulse=parts['pulse'];t=pulse.t_s.to_numpy()
    bg = np.interp(t,[parts['pre'].t_s.mean(),parts['post'].t_s.mean()],
                   [area['background_pre_us_cm'],area['background_post_us_cm']]) if row['background_mode']=='linear' else np.full(len(t),area['background_post_us_cm'] if row['background_mode']=='post' else area['background_pre_us_cm'])
    x=minutes(pulse.timestamp).to_numpy();ec=pulse.ec.to_numpy();segments=pulse.segment.to_numpy()
    ax.plot(x,bg,color=style.INK,ls='--',lw=1.3)
    for segment in np.unique(segments):
        mask=segments==segment
        ax.fill_between(x[mask],bg[mask],ec[mask],color=style.BLUE,alpha=.18)
    for i in np.flatnonzero(segments[1:]!=segments[:-1]):
        ax.plot(x[i:i+2],ec[i:i+2],color=style.ORANGE,ls=':',lw=2)
        ax.fill_between(x[i:i+2],bg[i:i+2],ec[i:i+2],facecolor='none',edgecolor=style.ORANGE,hatch='///',linewidth=0)
    ax.set_xlabel('Time from pulse-window start (min)',fontsize=12)
    ax.set_ylabel('Conductivity (µS/cm)',fontsize=12)
    ax.tick_params(labelsize=12)
    ax.xaxis.set_major_locator(MaxNLocator(6))
    ax.yaxis.set_major_locator(MaxNLocator(5))
    ax.grid(axis='y',color='#DDE3E6',lw=.7)
    ax.spines[['top','right']].set_visible(False)
    handles=[Line2D([],[],color=style.BLUE,label='Observed'),Line2D([],[],color=style.INK,ls='--',label='Baseline'),Patch(facecolor='#E1E5E8',label='Background windows')]
    if area['in_pulse_gap_count']:handles.append(Line2D([],[],color=style.ORANGE,ls=':',label='Gap model'))
    fig.legend(handles=handles,loc='upper left',bbox_to_anchor=(.04,.815),ncols=len(handles),frameon=False,fontsize=12)
    notes=['Recipe and full capture are conditional; total uncertainty is unquantified.']
    if unit_response:notes=['Spilled dose unknown: this is not release Q. Multiply only by a known delivered volume.']
    if row['sensor_applicability']!='trial_specific_native_match':notes.append('Sensor response transfer assumed.')
    if row['event_link_status']!='source_linked':notes.append('Release-to-pulse association unconfirmed.')
    if area['in_pulse_gap_count']:notes.append(f"{area['modelled_gap_seconds']:g} s of the pulse use linear interpolation.")
    flags=json.loads(row['unresolved_requirements'])
    if 'pipette_dose_uncertainty' in flags:notes.append('Pipette dosing uncertain.')
    if 'incompletely mixed' in row['capture_limitations']:notes.append('Calibration stock mixing uncertain.')
    if 'unsettled_tail' in row['capture_status']:notes.append('Tail capture assumed.')
    if 'overlapping' in row['capture_status']:notes.append('Overlapping pulses; background assumed.')
    if 'drifting' in row['capture_status']:notes.append('Drifting background assumed.')
    note='\n'.join(textwrap.wrap(' '.join(notes),85))
    fig.text(.05,.205,note,fontsize=12,color=style.INK,va='top')
    fig.text(.05,.067,f"Pulse window · {origin:%H:%M:%S}–{pd.Timestamp(window['pulse'][1]):%H:%M:%S} PST (UTC−08:00)",fontsize=12,color=style.INK)
    fig.text(.05,.025,'Source · MORA Aqua TROLL recordings and working estimate tables',fontsize=12,color=style.INK)
    return fig


def run_figures(scenario_dir, baseline_dir, output, *, root=matching.ROOT):
    root=Path(root).resolve();scenario_dir=Path(scenario_dir).resolve();baseline_dir=Path(baseline_dir).resolve()
    if any(Path(output).resolve().is_relative_to(p) or p.is_relative_to(Path(output).resolve()) for p in (scenario_dir,baseline_dir)):
        raise ValueError('Build figures separately from source bundles')
    pins,historical={},[]
    for folder in (scenario_dir,baseline_dir):
        info,current,old=scenarios.verify_baseline(folder,root);pins.update(current);historical.extend(old)
    source_info=json.loads((scenario_dir/'run_info.json').read_text())
    candidates=[matching._path(x['path'],root) for x in source_info['inputs'] if Path(x['path']).name=='recording_candidates.csv']
    if len(candidates)!=1:raise ValueError('Expected one source-pinned recording candidate table')
    pair_path=candidates[0].with_name('run_info.json')
    if str(pair_path.resolve()) not in pins:raise ValueError('Pairing manifest is not pinned')
    pair_info=json.loads(pair_path.read_text())
    recordings={r['recording_edge_id']:r for r in read_rows(candidates[0])}
    releases=read_rows(baseline_dir/'tables/discharge_by_release.csv')
    working=read_rows(scenario_dir/'working_estimates.csv')
    selected=read_rows(baseline_dir/'tables/discharge_estimates.csv')
    points=combine_estimates(selected,working,releases)
    windows={w['id']:w for w in json.loads((scenario_dir/'scenario_settings.json').read_text())['windows']}
    groups=defaultdict(list)
    for row in working:groups[row['trial_id'],row['recording_edge_id'],row['window_id'],row['conductivity_basis']].append(row)
    code=[__file__,scenarios.__file__,style.__file__,slug.__file__,reuse.__file__,matching.__file__]
    with reuse.staged_run(Path(output),pins,code) as (stage,pins):
        index=[]
        slug._table(stage/'plot_estimates.csv',points,['trial_id','q_m3_s'])
        coverage_rows=[]
        for release in releases:
            members=[p for p in points if p['trial_id']==release['trial_id']]
            status=members[0]['status'] if members else ('excluded_practice' if release['category']=='excluded_practice' else 'no_chosen_q')
            coverage_rows.append(dict(trial_id=release['trial_id'],field_date=release['field_date'],site=release['site_alias'],
                                      plot_status=status,plotted_q_count=len(members),scientifically_accepted=False))
        slug._table(stage/'release_coverage.csv',coverage_rows,['trial_id'])
        for site,year in sorted({(r['site'],r['field_date'][:4]) for r in points}):
            name=f'{site.lower()}_{year}_discharge.png'
            style._save(comparison(points,releases,site,year),stage/name)
            index.append(dict(figure=name,kind='comparison',site=site,year=year,source_table='plot_estimates.csv'))
        early=[r for r in releases if '2025-07-01' <= r['field_date'] < '2025-09-01']
        if any(p['site']=='NISQ' and '2025-07-01' <= p['field_date'] < '2025-09-01' for p in points):
            name='nisq_2025_early_detail.png'
            style._save(comparison(points,early,'NISQ','2025',period_label='July–August 2025'),stage/name)
            index.append(dict(figure=name,kind='comparison_detail',site='NISQ',year='2025',
                              date_start='2025-07-01',date_end_exclusive='2025-09-01',source_table='plot_estimates.csv'))
        style._save(coverage(points,releases),stage/'nisqually_coverage.png')
        index.append(dict(figure='nisqually_coverage.png',kind='coverage',site='NISQ',source_table='release_coverage.csv;plot_estimates.csv'))
        frames={}
        for (tid,eid,wid,channel),rows in groups.items():
            window=windows[wid]
            if (window['trial_id'],window['recording_edge_id'],window['channel'])!=(tid,eid,channel):
                raise ValueError('Working pulse does not match its window')
            edges=[eid]+window.get('additional_recording_edge_ids',[])
            key=tuple(edges),channel
            if key not in frames:
                samples=pd.concat([slug._recording_samples(recordings[e],pair_info,root/'salt_dilution/data/processed',root) for e in edges],ignore_index=True)
                frames[key]=slug.prepare_series(samples,channel)[0]
            name=f'pulses/{tid}_{wid}_{channel}.png'
            style._save(pulse_figure(frames[key],window,rows),stage/name)
            for row in rows:index.append(dict(figure=name,kind='pulse',trial_id=tid,window_id=wid,recording_edge_id=eid,conductivity_basis=channel,calibration_id=row['calibration_id'],recipe_id=row['recipe_id'],source_table='working_estimates.csv'))
        slug._table(stage/'figure_index.csv',index,['figure','kind'])
        (stage/'historical_code.json').write_text(matching._json(historical)+'\n')
        return reuse.write_run_info(stage,pins,scope='Selected and protocol-conditional discharge figures',
            figure_count=len({r['figure'] for r in index}),plotted_q_rows=len(points),
            working_q_releases=len({r['trial_id'] for r in working if r['q_m3_s']}),
            selected_releases=len({r['trial_id'] for r in selected}),unit_response_rows=sum(r['result_class']=='unit_response' for r in working),
            interpretation='All saved estimates retained; no averaging or field acceptance. Unit responses are separate from release Q.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('scenarios','baseline','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(argv)
    info=run_figures(args.scenarios,args.baseline,args.output)
    print(matching._json({k:info[k] for k in ('figure_count','plotted_q_rows','working_q_releases')}))


if __name__=='__main__':
    main()
