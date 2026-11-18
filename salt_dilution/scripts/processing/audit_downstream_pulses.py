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

PILOT = 'NISQ-20250903-T02'


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


def pilot_figure(traces, release):
    fig, axes = plt.subplots(len(traces), 1, sharex=True, figsize=(9, 8.1), layout='constrained')
    fig.suptitle('Nisqually · 3 September 2025\nFour recordings around Trial 2',
                 x=.04, ha='left', fontsize=16, fontweight='bold', color=style.INK)
    fig.supxlabel('Recorded local time · clock alignment unverified\nSource · MORA field recordings and release notebook', fontsize=11)
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
        ax.spines[['right', 'top']].set_visible(False)
        ax.grid(axis='y', color='#DDE3E6', lw=.65)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    axes[0].text(.99, .93, f'Notebook release · {release:%H:%M:%S}', transform=axes[0].transAxes,
                 ha='right', va='top', fontsize=10, color='#984116')
    axes[-1].set_xlim(release-pd.Timedelta(minutes=30), release+pd.Timedelta(minutes=30))
    fig.text(.99, .99, 'Diagnostic · reach order and\nGeneral pulse identity unresolved',
             color='#47545A', fontsize=9, ha='right', va='top')
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
    pins = dict(pin(p) for p in [records, info_path, candidates, *found])
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
            if path.name.startswith('20250903'):
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
    traces = []
    for edge in edges:
        if edge['trial_id'] != PILOT or edge['selected_for_pairing'] != 'true':
            continue
        for ref in json.loads(edge['member_refs']):
            item = next(x for x in info['inventory'] if x['content_ref'] == ref)
            for f in item['files'].values():
                file = matching._path(f['path'], root)
                pins[str(file.resolve())] = f['sha256']
        data = mass_slug._recording_samples(edge, info, root/'salt_dilution/data/processed', root)
        frame = mass_slug.prepare_series(data, 'actual')[0].rename(columns={'segment': 'session'})
        traces.append((f"Aqua TROLL {edge['device_serial']} · main recording candidate", 'Actual µS/cm', frame))
    for name, frame in sorted(general.items()):
        label = 'General1' if 'general1' in name.lower() else 'General2'
        bank = 'left bank' if 'Left' in name else 'right bank'
        native_units = set(frame.unit.dropna())
        if len(native_units) != 1:
            raise ValueError(f'Mixed native EC units in {name}')
        traces.append((f'{label} · {bank}, candidate monitoring record', f'{next(iter(native_units))} (logged)', frame))
    if len(traces) != 4:
        raise ValueError('Expected two Aqua TROLL and two General pilot records')
    provenance = json.loads(records.read_text())
    release = pd.Timestamp('2025-09-03 ' + provenance['trials'][PILOT]['source_record']['injection_time_local'])
    with reuse.staged_run(output, pins, [__file__, mass_slug.__file__, matching.__file__, style.__file__]) as (stage, pins):
        mass_slug._table(stage/'recording_audit.csv', rows, ['source', 'session'])
        pilot_frames = []
        for label, unit, frame in traces:
            samples = frame.loc[frame.timestamp.between(release-pd.Timedelta(minutes=30),
                                                         release+pd.Timedelta(minutes=30)),
                                ['timestamp', 'ec', 'session']].copy()
            samples.insert(0, 'recording', label.split(' · ')[0])
            samples['conductivity_unit'] = unit
            pilot_frames.append(samples)
        pd.concat(pilot_frames, ignore_index=True).to_csv(stage/'pilot_traces.csv', index=False)
        style._save(pilot_figure(traces, release), stage/'nisq_2025-09-03_recording_alignment.png')
        return reuse.write_run_info(stage, pins, scope='Native-clock monitoring diagnostic',
                                    candidate_files=len(found), inventory_rows=len(rows), verified_pairs=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matching', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({k: v for k, v in run(args.matching, args.output).items()
                      if k in ('candidate_files', 'inventory_rows', 'verified_pairs')}))


if __name__ == '__main__':
    main()
