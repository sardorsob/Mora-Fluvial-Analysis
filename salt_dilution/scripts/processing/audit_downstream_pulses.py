"""Inventory probable monitoring records and render a native-clock diagnostic."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from . import calibration_reuse as reuse, mass_slug, matching
from . import plot_discharge_summary as style

# For repeated releases, use the first notebook clock and mark the second
# on the same panels. The windows are diagnostic crops, not integration bounds.
PILOTS = {
    'NISQ-20250903-T02': ('', None),
    'NISQ-20250808-T01': ('', None),
    'NISQ-20250917-T01': ('_am', 'NISQ-20250917-T02'),
    'NISQ-20250917-T03': ('_pm', 'NISQ-20250917-T04'),
}
LEFT_BANK_CANDIDATES = {
    'NISQ-20250808-T01': ('790481', 'Single written release and a distinct rise and fall on both records'),
    'NISQ-20250917-T01': ('680530', 'Two ordered morning pulses in both records'),
    'NISQ-20250917-T02': ('680530', 'Two ordered morning pulses in both records'),
    'NISQ-20250917-T03': ('680530', 'Two ordered afternoon pulses in both records'),
    'NISQ-20250917-T04': ('680530', 'Two ordered afternoon pulses in both records'),
}


def general_samples(path):
    """Read native readings as stored, with a separate session after long breaks."""
    raw = pd.read_excel(path, dtype=str)
    timestamp = pd.to_datetime(raw['Date'].str.slice(0, 10) + ' ' + raw['Time'].str.strip(),
                               format='mixed', errors='coerce')
    frame = pd.DataFrame(dict(timestamp=timestamp,
                              ec=pd.to_numeric(raw['Ch1_Value'], errors='coerce'),
                              unit=raw['Ch1_Unit'].str.strip()))
    delta = frame.timestamp.diff().dt.total_seconds()
    # Segment gaps and clock reversals before sorting so repeated sessions remain visible.
    frame['session'] = (delta.gt(300) | delta.lt(0) |
                        frame.timestamp.isna() | frame.timestamp.shift().isna()).cumsum()
    return frame


def pilot_figure(traces, release, trial, next_release=None):
    fig, axes = plt.subplots(len(traces), 1, sharex=True, figsize=(9, 8.1), layout='constrained')
    title = f'Trials {int(trial[-2:])} and {int(trial[-2:])+1}' if next_release else f'Trial {int(trial[-2:])}'
    fig.suptitle(f'Nisqually · {release.day} {release:%B %Y}\nFour recordings around {title}',
                 x=.04, ha='left', fontsize=16, fontweight='bold', color=style.INK)
    releases = f'{release:%H:%M:%S} and {next_release:%H:%M:%S}' if next_release else f'{release:%H:%M:%S}'
    fig.supxlabel('Recorded local time · clock alignment unverified\n'
                  f'Dashed lines: notebook releases at {releases}\n'
                  'Source · MORA field recordings and release notebook', fontsize=11)
    for ax, (label, unit, frame) in zip(axes, traces):
        frame = frame.loc[frame.timestamp.between(release - pd.Timedelta(minutes=30),
                                                   release + pd.Timedelta(minutes=30))]
        ax.set_title(label, loc='left', fontsize=11, fontweight='bold', color=style.INK)
        ax.set_ylabel(unit, fontsize=10)
        for _, segment in frame.groupby('session', sort=False):
            # Avoid drawing across even short holes in this native-clock check.
            delta = segment.timestamp.diff().dt.total_seconds()
            for _, part in segment.groupby((delta.gt(5) | delta.le(0)).cumsum()):
                ax.plot(part.timestamp, part.ec, color=style.BLUE, lw=1.25,
                        marker='.' if len(part) == 1 else None)
        ax.axvline(release, color='#984116', lw=1.4, linestyle='--')
        if next_release is not None:
            ax.axvline(next_release, color='#984116', lw=1.4, linestyle='--')
        ax.spines[['right', 'top']].set_visible(False)
        ax.grid(axis='y', color='#DDE3E6', lw=.65)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    axes[-1].set_xlim(release-pd.Timedelta(minutes=30), release+pd.Timedelta(minutes=30))
    fig.text(.99, .99, 'Diagnostic · reach order and\nGeneral pulse identity unresolved',
             color='#47545A', fontsize=9, ha='right', va='top')
    return fig


def clock_review(rows, provenance, edges):
    """Compare unadjusted clocks for the date-labelled attenuation exports."""
    by_date = {}
    for row in rows:
        name = Path(row['source']).name
        if row['file_label_role'] == 'attenuation' and (match := re.match(r'(\d{8})_general([12])', name, re.I)):
            observed_date = str(row.get('first_recorded', ''))[:10].replace('-', '')
            if observed_date == match[1]:
                by_date.setdefault(match[1], {}).setdefault(match[2], []).append(row)
    reviews = []
    for trial_id, entry in sorted(provenance['trials'].items()):
        day = trial_id.split('-')[1]
        if day not in by_date:
            continue
        note = entry['source_record']
        release = pd.Timestamp(f"{note['field_date']} {note['injection_time_local']}")
        selected = sorted(e['recording_edge_id'] for e in edges
                          if e['trial_id'] == trial_id and e['selected_for_pairing'] == 'true')
        for logger in ('1', '2'):
            sessions = by_date[day].get(logger, [])
            overlapping = [f"{Path(r['source']).name}#{r['session']}" for r in sessions
                           if r['first_recorded'] <= release <= r['last_recorded']]
            reviews.append(dict(
                trial_id=trial_id, notebook_local_release=release.isoformat(sep=' '),
                notebook_source=entry['current_csv_values']['sourcebook_reference'],
                general_case_label=f'General{logger}', same_clock_face_overlap=bool(overlapping),
                overlapping_sessions=';'.join(overlapping), aqua_troll_edges=';'.join(selected),
                longitudinal_order='unverified', pulse_pair_status='unverified',
            ))
    return reviews, by_date


def coverage_figure(reviews, by_date):
    fig, axes = plt.subplots(len(by_date), 1, figsize=(8.9, 9.8), layout='constrained')
    fig.suptitle('Date-labelled General exports\n'
                 'Recording spans and notebook releases',
                 x=.065, ha='left', fontsize=16, fontweight='bold', color=style.INK)
    for (day, logs), ax in zip(sorted(by_date.items()), axes):
        releases = {r['trial_id']: pd.Timestamp(r['notebook_local_release']) for r in reviews
                    if r['trial_id'].split('-')[1] == day}
        ax.set_title(f'{pd.Timestamp(day):%d %B %Y}', loc='left', fontsize=12, fontweight='bold')
        for logger, y in [('1', 1), ('2', 0)]:
            for row in logs.get(logger, []):
                ax.hlines(y, row['first_recorded'], row['last_recorded'], color=style.BLUE, lw=5)
        for i, (trial, when) in enumerate(releases.items()):
            # Stagger labels for releases only minutes apart.
            height = 1.38 + .28 * (i % 2)
            ax.vlines(when, -.22, height - .03, color='#984116', linestyle='--', lw=1)
            ax.text(when, height, trial.rsplit('-', 1)[-1], ha='center', va='bottom',
                    fontsize=9.5, color='#984116')
        ax.set(yticks=[1, 0], yticklabels=['General1', 'General2'], ylim=(-.37, 2.05))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=7))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.grid(axis='x', color='#DDE3E6', lw=.65)
        ax.spines[['top', 'right', 'left']].set_visible(False)
        ax.tick_params(labelsize=10)
    fig.supxlabel('Recorded local time · clock alignment unverified\n'
                  'Blue spans: source file sessions  |  Dashed marks: notebook releases\n'
                  'Source · MORA field notebooks and native General workbooks', fontsize=10.5)
    return fig


def run(matching_dir, output, root=matching.ROOT):
    raw_dir = root / 'salt_dilution/data/raw'
    records = root / 'salt_dilution/data/records/provenance.json'
    pin = lambda path: (str(path.resolve()), matching._hash(path))
    info_path = matching_dir / 'run_info.json'
    candidates = matching_dir / 'recording_candidates.csv'
    info = json.loads(info_path.read_text())
    if {'path': candidates.name, 'sha256': matching._hash(candidates)} not in info['outputs']:
        raise ValueError('Candidate table does not match its pairing manifest')
    with candidates.open(newline='') as f:
        edges = list(csv.DictReader(f))
    inventory = {Path(x['files']['raw']['path']).as_posix(): x for x in info['inventory'] if 'raw' in x['files']}
    # Keep these candidates out of the Q-input layer until field role is reviewed.
    found = sorted(p for p in raw_dir.rglob('*') if p.is_file()
                   and not p.stem.lower().endswith('_metadata')
                   and (re.search(r'atten(?:t)?uat', p.name, flags=re.I)
                        or ('general' in p.name.lower() and p.suffix.lower() in {'.xls', '.xlsx'})))
    sop = raw_dir / 'README_Dilution_Data_Download_SOP.txt'
    pins = dict(pin(p) for p in [records, sop, info_path, candidates, *found])
    rows, general, sessions = [], {}, {}
    for path in found:
        rel = path.relative_to(root).as_posix()
        entry = inventory.get(rel, {})
        ref = entry.get('content_ref', '')
        links = sorted({e['trial_id'] for e in edges if ref in json.loads(e['member_refs'])})
        filename = path.name.lower()
        role = ('attenuation' if re.search(r'atten(?:t)?uat', filename) else
                'mixing' if 'mixing' in filename else
                'practice' if 'test' in filename else 'unspecified')
        common = dict(source=rel, raw_sha256=pins[str(path.resolve())],
                      sensor_serial=entry.get('device_serial', ''),
                      file_label_role=role, verified_reach_order='',
                      candidate_releases=';'.join(links), verified_release='',
                      disposition='unresolved')
        if 'general' in path.name.lower():
            try:
                frame = general_samples(path)
            except (ValueError, KeyError) as exc:
                if not ('format cannot be determined' in str(exc) or isinstance(exc, KeyError)):
                    raise
                rows.append(dict(common | {'disposition': 'unsupported_format'}, session=''))
                continue
            if path.name.startswith(tuple(t.split('-')[1] for t in PILOTS)):
                general[path.name] = frame
            for session, f in frame.groupby('session'):
                t = f.timestamp.dropna()
                key = hashlib.sha256(f[['timestamp', 'ec', 'unit']].to_csv(index=False).encode()).hexdigest()
                previous = sessions.setdefault(key, f'{rel}#{session}')
                recorded_dates = set(t.dt.strftime('%Y%m%d'))
                dated_links = ';'.join(tid for tid in links if tid.split('-')[1] in recorded_dates)
                rows.append(dict(common | {'candidate_releases': dated_links}, session=session,
                                 duplicate_of=previous if previous != f'{rel}#{session}' else '', native_units=';'.join(sorted(f.unit.dropna().unique())),
                                 first_recorded=t.min() if len(t) else '', last_recorded=t.max() if len(t) else '',
                                 readings=len(f), zero_readings=int(f.ec.eq(0).sum()),
                                 invalid_readings=int((f.ec.isna() | f.timestamp.isna()).sum()),
                                 duplicate_timestamps=int(t.duplicated().sum())))
        else:
            # Native Aqua TROLL file may be another export of the same physical session.
            key = (entry.get('device_serial'), entry.get('first_local'), entry.get('last_local'),
                   entry.get('files', {}).get('processed', {}).get('sha256'))
            previous = sessions.setdefault(key, rel) if all(key) else rel
            rows.append(dict(common, session='', native_units='µS/cm',
                             duplicate_of=previous if previous != rel else '',
                             first_recorded=entry.get('first_local', ''), last_recorded=entry.get('last_local', ''),
                             readings='', zero_readings='', invalid_readings='', duplicate_timestamps=''))
    traces = {trial: [] for trial in PILOTS}
    for edge in edges:
        if edge['trial_id'] not in traces or edge['selected_for_pairing'] != 'true':
            continue
        for ref in json.loads(edge['member_refs']):
            item = next(x for x in info['inventory'] if x['content_ref'] == ref)
            for f in item['files'].values():
                file = matching._path(f['path'], root)
                pins[str(file.resolve())] = f['sha256']
        data = mass_slug._recording_samples(edge, info, root/'salt_dilution/data/processed', root)
        frame = mass_slug.prepare_series(data, 'actual')[0].rename(columns={'segment': 'session'})
        traces[edge['trial_id']].append(
            (f"Aqua TROLL {edge['device_serial']} · main recording candidate", 'Actual µS/cm', frame))
    for name, frame in sorted(general.items()):
        label = 'General1' if 'general1' in name.lower() else 'General2'
        bank = 'left bank' if 'Left' in name else 'right bank'
        native_units = set(frame.unit.dropna())
        if len(native_units) != 1:
            raise ValueError(f'Mixed native EC units in {name}')
        for trial in PILOTS:
            if trial.split('-')[1] == name[:8]:
                traces[trial].append(
                    (f'{label} · {bank}, candidate monitoring record', f'{next(iter(native_units))} (logged)', frame))
    if any(len(series) != 4 for series in traces.values()):
        raise ValueError('Expected two Aqua TROLL and two General records per pilot')
    provenance = json.loads(records.read_text())
    reviews, by_date = clock_review(rows, provenance, edges)
    provisional = []
    for review in reviews:
        trial = review['trial_id']
        if trial not in LEFT_BANK_CANDIDATES or review['general_case_label'] != 'General1':
            continue
        serial, evidence = LEFT_BANK_CANDIDATES[trial]
        aqua_edges = [e['recording_edge_id'] for e in edges if e['trial_id'] == trial
                      and e['selected_for_pairing'] == 'true' and e['device_serial'] == serial]
        if len(aqua_edges) != 1 or not review['same_clock_face_overlap']:
            raise ValueError(f'Provisional association lost its source evidence: {trial}')
        provisional.append(dict(trial_id=trial, aqua_troll_serial=serial, aqua_troll_edge=aqua_edges[0],
                                general_session=review['overlapping_sessions'],
                                notebook_source=review['notebook_source'], temporal_evidence=evidence,
                                pairing_status='provisional', longitudinal_order='unverified',
                                clock_alignment='unverified'))
    with reuse.staged_run(output, pins, [__file__, mass_slug.__file__, matching.__file__, style.__file__]) as (stage, pins):
        mass_slug._table(stage/'recording_audit.csv', rows, ['source', 'session'])
        mass_slug._table(stage/'trial_clock_review.csv', reviews, ['trial_id', 'general_case_label'])
        mass_slug._table(stage/'candidate_pairs.csv', provisional, ['trial_id'])
        style._save(coverage_figure(reviews, by_date), stage/'general_recording_coverage.png')
        for i, (trial, (session_label, next_trial)) in enumerate(PILOTS.items()):
            note = provenance['trials'][trial]['source_record']
            release = pd.Timestamp(f"{note['field_date']} {note['injection_time_local']}")
            pilot_frames = []
            for label, unit, frame in traces[trial]:
                samples = frame.loc[frame.timestamp.between(release-pd.Timedelta(minutes=30),
                                                             release+pd.Timedelta(minutes=30)),
                                    ['timestamp', 'ec', 'session']].copy()
                samples.insert(0, 'recording', label.split(' · ')[0])
                samples['conductivity_unit'] = unit
                pilot_frames.append(samples)
            name = f'nisq_{release:%Y-%m-%d}{session_label}'
            data_name = 'pilot_traces.csv' if i == 0 else f'{name}_traces.csv'
            pd.concat(pilot_frames, ignore_index=True).to_csv(stage/data_name, index=False)
            next_release = None
            if next_trial:
                follow = provenance['trials'][next_trial]['source_record']
                next_release = pd.Timestamp(f"{follow['field_date']} {follow['injection_time_local']}")
            style._save(pilot_figure(traces[trial], release, trial, next_release),
                        stage/f'{name}_recording_alignment.png')
        return reuse.write_run_info(stage, pins, scope='Native-clock monitoring diagnostic',
                                    candidate_files=len(found), inventory_rows=len(rows),
                                    provisional_pairs=len(provisional), verified_pairs=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matching', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({k: v for k, v in run(args.matching, args.output).items()
                      if k in ('candidate_files', 'inventory_rows', 'verified_pairs')}))


if __name__ == '__main__':
    main()
