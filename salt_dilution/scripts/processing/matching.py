"""Propose release/recording/K links; never select windows or calculate Q.

Run with ``python -m salt_dilution.scripts.processing.matching --help``.
Unresolved evidence is retained in the output rather than filled from ID order.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import numpy as np
import pandas as pd

from salt_dilution.scripts.parsers.parse_data import read_data

ROOT = Path(__file__).resolve().parents[3]
CHANNELS = {b: f'{b}_conductivity_us_cm' for b in ('actual', 'specific')}


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def _ref(path, root):
    path = Path(path).resolve()
    return str(path.relative_to(root)) if path.is_relative_to(root) else str(path)


def _path(value, root):
    path = Path(value)
    if not path.is_absolute():
        return root / path
    if path.is_relative_to(root):
        return path
    # Older metadata includes the machine's original checkout prefix.
    if 'salt_dilution' in path.parts:
        return root.joinpath(*path.parts[path.parts.index('salt_dilution'):])
    return path


def _times(series, utc=False):
    return pd.to_datetime(series, format='mixed', errors='coerce', utc=utc)


def _date(value):
    time = pd.to_datetime(value, errors='coerce')
    return '' if pd.isna(time) else time.date().isoformat()


def inventory_recordings(processed_dir, provenance, root=ROOT):
    """Inspect every local CSV/metadata pair, recovering old metadata read-only."""
    root, processed_dir = Path(root).resolve(), Path(processed_dir).resolve()
    registry = provenance.get('probe_registry', {})
    by_path = {}
    for identity, evidence in provenance.get('datasets', {}).items():
        key = _path(evidence['processed_path'], root).resolve()
        if key in by_path:
            raise ValueError(f'Duplicate registered dataset path: {key}')
        by_path[key] = (identity, evidence)
    paths = set()
    for candidate in processed_dir.rglob('*.csv'):
        with candidate.open(encoding='utf-8-sig', newline='') as stream:
            header = next(csv.reader(stream), [])
        if 'timestamp' in header and any(c in header for c in CHANNELS.values()):
            paths.add(candidate)
    paths.update(p.with_name(p.name[:-len('_metadata.json')] + '.csv')
                 for p in processed_dir.rglob('*_metadata.json'))
    paths.update(p for p in by_path if p.is_relative_to(processed_dir))
    recordings = []
    for path in sorted(paths):
        identity, evidence = by_path.get(path, ('', {}))
        meta_path = path.with_name(path.stem + '_metadata.json')
        rec = dict(dataset_id=identity, path=_ref(path, root), files={}, issues=[],
                   evidence=evidence, members=[], conductivity_bases=[], probe_alias='',
                   recorded_probe_alias=evidence.get('probe_alias',''), alias_qualifications=[],
                   device_serial='', role='', site_alias='', activity='unknown',
                   clock_basis='', samples=pd.DataFrame(), metadata={})
        issues = rec['issues']
        for kind, file in (('processed', path), ('metadata', meta_path)):
            if file.is_file():
                rec['files'][kind] = dict(path=_ref(file, root), sha256=_hash(file))
                if evidence.get(kind + '_sha256') and evidence[kind + '_sha256'] != _hash(file):
                    issues.append(kind + '_hash_mismatch')
            else:
                issues.append(kind + '_missing')
        rec['content_ref'] = identity or 'FILE-' + hashlib.sha256(
            (rec['path'] + rec['files'].get('processed', {}).get('sha256', '')).encode()).hexdigest()[:16]
        rec['members'] = [rec['content_ref']]
        try:
            meta = json.loads(meta_path.read_text()) if meta_path.is_file() else {}
            df = pd.read_csv(path) if path.is_file() else pd.DataFrame()
        except (ValueError, OSError) as exc:
            issues.append('unreadable_processed_pair')
            rec['error'] = str(exc)
            recordings.append(rec)
            continue
        source = evidence.get('source_path') or meta.get('source_file')
        if source:
            raw = _path(source, root)
            if raw.is_file():
                rec['files']['raw'] = dict(path=_ref(raw, root), sha256=_hash(raw))
                if evidence.get('source_sha256') and evidence['source_sha256'] != _hash(raw):
                    issues.append('source_hash_mismatch')
                elif meta.get('source_type') != 'calibration' and (not meta.get('channels') or 'timestamp_utc' not in df):
                    try:
                        fresh, recovered = read_data(raw)
                        common = [c for c in ('timestamp', *CHANNELS.values()) if c in df and c in fresh]
                        if len(df) != len(fresh):
                            raise ValueError('Changed normalized row count')
                        if not common:
                            raise ValueError('No comparable timestamp/EC series')
                        for column in common:
                            left, right = df[column], fresh[column]
                            if column == 'timestamp':
                                equal = _times(left).reset_index(drop=True).equals(_times(right).reset_index(drop=True))
                            else:
                                equal = np.allclose(pd.to_numeric(left, errors='coerce'),
                                                    pd.to_numeric(right, errors='coerce'), rtol=1e-12,
                                                    atol=0, equal_nan=True)
                            if not equal:
                                raise ValueError(f'Changed normalized measurements: {column}')
                        df, meta = fresh, recovered
                        rec['metadata_recovered'] = True
                    except (ValueError, OSError, ImportError) as exc:
                        issues.append('raw_recovery_failed')
                        if 'Changed normalized' in str(exc):
                            issues.append('source_data_conflict')
                        rec['error'] = str(exc)
            else:
                issues.append('raw_source_missing')
        if not source:
            issues.append('raw_source_unavailable')
        rec['metadata'] = meta
        serials = set()
        for basis, column in CHANNELS.items():
            channels = [c for c in meta.get('channels', []) if c.get('column') == column]
            if column not in df:
                continue
            if not channels or any(str(c.get('unit', '')).replace('µ', 'u').replace('μ', 'u') != 'uS/cm' for c in channels):
                issues.append('unknown_conductivity_units')
                continue
            rec['conductivity_bases'].append(basis)
            for channel in channels:
                serial = channel.get('sensor_serial_number') or channel.get('device_serial_number')
                if not serial:
                    suffix = re.search(r'\((\d+)\)\s*$', channel.get('source_column', ''))
                    serial = suffix.group(1) if suffix else None
                if serial:
                    serials.add(str(serial))
        properties = meta.get('embedded_metadata', {}).get('Device Properties', {})
        if 'aqua troll' in str(properties.get('Device', '')).lower():
            if properties.get('Serial Number'):
                serials.add(str(properties['Serial Number']))
        if len(serials) == 1:
            rec['device_serial'] = next(iter(serials))
            aliases = [a for a, serial in registry.items() if str(serial) == rec['device_serial']]
            if len(aliases) > 1:
                raise ValueError('Duplicate physical device in probe registry')
            rec['probe_alias'] = aliases[0] if aliases else ''
        elif len(serials) > 1:
            issues.extend(('multiple_conductivity_devices','physical_device_identity_conflict'))
        if rec['device_serial'] and evidence.get('probe_alias') and str(registry.get(evidence['probe_alias'], '')) != rec['device_serial']:
            rec['alias_qualifications'].append('recorded_probe_alias_disagrees_with_native_label')
        if not rec['probe_alias']:
            issues.append('unknown_probe_identity')
        rec['site_alias'] = meta.get('site_alias', '')
        filename = meta.get('filename_metadata', {})
        for site in ('NISQ', 'PAR'):
            if re.search(rf'(^|[_ /-]){site.lower()}([_ /-]|$)', path.stem.lower()):
                if rec['site_alias'] and rec['site_alias'] != site:
                    issues.append('site_identity_conflict')
                rec['site_alias'] = site
        activity_text = (path.stem + ' ' + str(meta.get('source_type', ''))).lower()
        for activity in ('calibration', 'attenuation', 'background'):
            if activity in activity_text:
                rec['activity'] = activity
                break
        if rec['activity'] == 'attenuation':
            rec['role'] = 'attenuation'
        rec['instrument_family'] = meta.get('instrument_family', '')
        rec['clock_basis'] = meta.get('timestamp_basis', '') if 'timestamp_utc' in df else ''
        rec['source_offset_seconds'] = meta.get('utc_offset_seconds')
        if 'timestamp' not in df or not len(df):
            issues.append('measurement_times_unavailable')
        else:
            local = _times(df['timestamp'])
            if local.isna().any():
                issues.append('missing_timestamps')
            if not local.is_monotonic_increasing:
                issues.append('nonmonotonic_timestamps')
            if local.duplicated().any():
                issues.append('duplicate_timestamps')
            samples = df[[c for c in ('timestamp', 'timestamp_utc', *CHANNELS.values()) if c in df]].copy()
            samples['timestamp'] = local
            if 'timestamp_utc' in samples:
                samples['timestamp_utc'] = _times(samples['timestamp_utc'], utc=True)
                if samples['timestamp_utc'].isna().any():
                    issues.append('missing_utc_timestamps')
                basis = meta.get('timestamp_basis')
                if basis in ('explicit_report_numeric_offset','offset_in_source_timestamps'):
                    expected = _times(samples['timestamp'], utc=True)
                    if basis == 'explicit_report_numeric_offset':
                        offset = meta.get('utc_offset_seconds')
                        if not isinstance(offset,(int,float)) or not math.isfinite(offset) or abs(offset)>86400:
                            issues.append('utc_clock_conflict')
                        else:
                            expected = expected - pd.to_timedelta(offset,unit='s')
                    if not expected.equals(samples['timestamp_utc']):
                        issues.append('utc_clock_conflict')
            samples['sample_source'] = [f"{rec['content_ref']}:{i}" for i in range(len(samples))]
            rec['samples'] = samples
            valid = local.dropna()
            rec['dates'] = sorted(set(valid.dt.date.astype(str)))
            rec['first_local'] = str(valid.min()) if len(valid) else ''
            rec['last_local'] = str(valid.max()) if len(valid) else ''
            delta = local.diff().dt.total_seconds()
            rec['cadence_seconds'] = float(delta[delta > 0].median()) if (delta > 0).any() else None
            rec['gaps'] = [dict(after_row=int(i-1), seconds=float(v)) for i, v in delta.items()
                           if rec['cadence_seconds'] and v > 1.5 * rec['cadence_seconds']]
            rec['signal_summary'] = {}
            for basis in rec['conductivity_bases']:
                values = pd.to_numeric(df[CHANNELS[basis]], errors='coerce')
                if not np.isfinite(values).all():
                    issues.append('nonfinite_conductivity')
                finite = values[np.isfinite(values)]
                if len(finite):
                    rec['signal_summary'][basis] = dict(min_us_cm=float(finite.min()), max_us_cm=float(finite.max()),
                        maximum_sample_timestamp=str(local.loc[finite.idxmax()]))
        rec['issues'] = sorted(set(issues))
        recordings.append(rec)
    return recordings


def reconcile_recordings(recordings):
    """Coalesce verified equal overlaps/adjacent pieces; never average conflicts."""
    groups = []
    for rec in recordings:
        rec = dict(rec, members=list(rec['members']), issues=list(rec['issues']))
        rec['member_files'] = dict(rec.get('member_files', {rec['content_ref']: rec['files']}))
        combined = False
        for group in groups:
            if not rec['device_serial'] or rec['device_serial'] != group['device_serial']:
                continue
            if rec['site_alias'] != group['site_alias'] or rec['activity'] != group['activity']:
                continue
            # Equal native serials establish device identity without a registry
            # nickname. Other source and measurement issues still prevent merging.
            blockers = (set(rec['issues']) | set(group['issues'])) - {'unknown_probe_identity'}
            if blockers or rec['conductivity_bases'] != group['conductivity_bases']:
                continue
            if rec['clock_basis'] != group['clock_basis'] or rec.get('source_offset_seconds') != group.get('source_offset_seconds'):
                continue
            left, right = group['samples'], rec['samples']
            if left.empty or right.empty:
                continue
            common = left.merge(right, on='timestamp', suffixes=('_left', '_right'))
            columns = [CHANNELS[b] for b in rec['conductivity_bases']]
            overlap_equal = all(np.array_equal(common[c+'_left'], common[c+'_right'], equal_nan=True) for c in columns)
            if len(common) and not overlap_equal:
                group['issues'].append('conflicting_overlap')
                rec['issues'].append('conflicting_overlap')
                continue
            distance = max((right.timestamp.min()-left.timestamp.max()).total_seconds(),
                           (left.timestamp.min()-right.timestamp.max()).total_seconds())
            cadence = min(v for v in (rec.get('cadence_seconds'), group.get('cadence_seconds')) if v) if rec.get('cadence_seconds') and group.get('cadence_seconds') else 0
            if len(common) or (rec['clock_basis'] and 0 < distance <= cadence):
                group['members'].extend(rec['members'])
                group['member_files'].update(rec['member_files'])
                group['alias_qualifications'] = sorted(set(group.get('alias_qualifications',[]) + rec.get('alias_qualifications',[])))
                group['samples'] = pd.concat([left, right]).drop_duplicates('timestamp').sort_values('timestamp').reset_index(drop=True)
                group['dates'] = sorted(set(group.get('dates', []) + rec.get('dates', [])))
                combined = True
                break
        if not combined:
            groups.append(rec)
    if len(groups) < len(recordings):
        return reconcile_recordings(groups)
    for group in groups:
        samples = group['samples']
        if not samples.empty:
            group['first_local'], group['last_local'] = str(samples.timestamp.min()), str(samples.timestamp.max())
            group['signal_summary'] = {}
            for basis in group['conductivity_bases']:
                values = pd.to_numeric(samples[CHANNELS[basis]], errors='coerce')
                finite = values[np.isfinite(values)]
                if len(finite):
                    group['signal_summary'][basis] = dict(min_us_cm=float(finite.min()), max_us_cm=float(finite.max()),
                        maximum_sample_timestamp=str(samples.loc[finite.idxmax(), 'timestamp']))
        group['members'] = sorted(set(group['members']))
        group['logical_recording_id'] = 'REC-' + hashlib.sha256(_json(group['members']).encode()).hexdigest()[:16]
    return sorted(groups, key=lambda r: r['logical_recording_id'])


OVERRIDE_FIELDS = {
    'recordings': {'content_ref', 'site_alias', 'role', 'activity', 'clock_correction_seconds', 'clock_basis'},
    'trial_clocks': {'trial_id', 'utc_offset_seconds'},
    'recording_links': {'trial_id', 'content_ref'},
    'calibration_links': {'trial_id', 'calibration_id', 'probe_alias'},
    'expected_roles': {'trial_id', 'roles'},
}


def _validate_overrides(overrides, trials, calibrations, recordings):
    if overrides is None:
        return {key: [] for key in OVERRIDE_FIELDS}
    if not isinstance(overrides, dict) or overrides.get('schema_version') != 1:
        raise ValueError('Overrides require schema_version 1')
    if set(overrides) - {'schema_version', *OVERRIDE_FIELDS}:
        raise ValueError('Unknown override section')
    trial_ids = {t['trial_id'] for t in trials}
    cal_ids = {c['calibration_id'] for c in calibrations}
    refs = {m for r in recordings for m in r['members']}
    result = {}
    for kind, fields in OVERRIDE_FIELDS.items():
        entries = overrides.get(kind, [])
        if not isinstance(entries, list):
            raise ValueError(f'{kind} must be a list')
        seen = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) - fields - {'evidence', 'source_ref'}:
                raise ValueError(f'Unknown fields in {kind} override')
            if not all(isinstance(entry.get(k), str) and entry[k].strip() for k in ('evidence', 'source_ref')):
                raise ValueError('Every override needs evidence and source_ref')
            required = {'recordings': ('content_ref',), 'trial_clocks': ('trial_id','utc_offset_seconds'),
                        'recording_links': ('trial_id','content_ref'),
                        'calibration_links': ('trial_id','calibration_id','probe_alias'),
                        'expected_roles': ('trial_id','roles')}[kind]
            if any(k not in entry for k in required):
                raise ValueError(f'Missing required fields in {kind}')
            if 'trial_id' in entry and entry['trial_id'] not in trial_ids:
                raise ValueError('Unknown override trial_id')
            if 'calibration_id' in entry and entry['calibration_id'] not in cal_ids:
                raise ValueError('Unknown override calibration_id')
            if 'content_ref' in entry and entry['content_ref'] not in refs:
                raise ValueError('Unknown override content_ref')
            for key in ('utc_offset_seconds', 'clock_correction_seconds'):
                if key in entry and (isinstance(entry[key], bool) or not isinstance(entry[key], (int,float)) or
                                     not math.isfinite(entry[key]) or abs(entry[key]) > 86400):
                    raise ValueError('Invalid clock correction/offset')
            if 'clock_correction_seconds' in entry and not entry.get('clock_basis'):
                raise ValueError('Clock correction requires clock_basis')
            if 'roles' in entry and (not isinstance(entry['roles'], list) or not entry['roles'] or
                any(not isinstance(r,str) or not r.strip() for r in entry['roles']) or
                len(set(entry['roles'])) != len(entry['roles'])):
                raise ValueError('Expected roles must be a nonempty unique list')
            if 'activity' in entry and entry['activity'] not in ('river','calibration','background','attenuation','unknown'):
                raise ValueError('Invalid recording activity')
            identity = tuple(_json(entry[k]) for k in required if k not in ('roles','utc_offset_seconds'))
            if identity in seen:
                raise ValueError(f'Duplicate override in {kind}')
            seen.add(identity)
        result[kind] = entries
    # A source session cannot be corrected differently merely to fit each release.
    sessions = {}
    for entry in result['trial_clocks']:
        trial = next(t for t in trials if t['trial_id'] == entry['trial_id'])
        key = (trial.get('site_alias'), _date(trial.get('field_date')))
        offset = entry['utc_offset_seconds']
        if key in sessions and sessions[key] != offset:
            raise ValueError('Inconsistent release clock offsets within a site/day')
        sessions[key] = offset
    recording_corrections = {}
    for rec in recordings:
        corrections = [o.get('clock_correction_seconds',0) for o in result['recordings'] if o['content_ref'] in rec['members']]
        correction = corrections[0] if corrections else 0
        for day in rec.get('dates',[]):
            key = (rec.get('device_serial'), day)
            if not key[0]:
                continue
            if key in recording_corrections and recording_corrections[key] != correction:
                raise ValueError('Clock corrections must agree for a physical device/day')
            recording_corrections[key] = correction
    return result


def _release_time(trial, provenance, overrides):
    explicit = trial.get('dump_timestamp_utc', '')
    if explicit:
        value = pd.Timestamp(explicit)
        if value.tzinfo is not None:
            return value.tz_convert('UTC'), 'trials.dump_timestamp_utc'
    clock = next((o for o in overrides['trial_clocks'] if o['trial_id'] == trial['trial_id']), None)
    source = provenance.get('trials', {}).get(trial['trial_id'], {}).get('source_record', {})
    local = _local_release_clock(trial, provenance)
    if clock and local is not None:
        return (local - pd.to_timedelta(clock['utc_offset_seconds'],unit='s')).tz_localize('UTC'), clock['source_ref']
    return None, 'unresolved_notebook_clock:' + source.get('timezone_label_raw', '')


def _sequence_evidence(calibration_id, evidence, points, root):
    """Recheck pinned electronic sequence rows; no free search across river data."""
    review = evidence.get('probe_identity_review', {})
    matches = review.get('matches', {})
    if not any(channel in CHANNELS.values() and len(rows) >= 2 for channel, rows in matches.items()):
        return dict(status='unavailable', reason='no_pinned_electronic_sequence')
    files = review.get('files', [])
    for item in files:
        path = _path(item['path'], root)
        if not path.is_file():
            return dict(status='unavailable', reason='sequence_source_missing', path=item['path'])
        if _hash(path) != item.get('sha256'):
            return dict(status='conflicting', reason='sequence_source_hash_mismatch', path=item['path'])
    source = next((_path(f['path'], root) for f in files if f['path'].endswith('.csv')
                   and '_metadata' not in f['path'] and '/processed/' in f['path']), None)
    tolerance = review.get('tolerance_us_cm')
    if source is None or not isinstance(tolerance, (int,float)) or not math.isfinite(tolerance) or tolerance < 0:
        return dict(status='unavailable', reason='sequence_source_or_tolerance_missing')
    frame = pd.read_csv(source)
    checked = {}
    for channel, rows in matches.items():
        indices = [int(row['row_index']) for row in rows]
        if channel not in CHANNELS.values() or indices != sorted(set(indices)):
            return dict(status='conflicting', reason='invalid_sequence_order_or_channel')
        for row, index in zip(rows, indices):
            notebook = [p for p in points if p['calibration_id'] == calibration_id
                        and str(p['step_no']) == str(row['step_no'])]
            if (len(notebook) != 1 or not notebook[0].get(channel) or index < 0 or index >= len(frame)
                    or channel not in frame):
                return dict(status='conflicting', reason='sequence_point_not_found')
            actual, target = float(frame.iloc[index][channel]), float(notebook[0][channel])
            if not math.isfinite(actual) or abs(actual-target) > tolerance:
                return dict(status='conflicting', reason='sequence_value_disagreement')
            if 'timestamp' in frame and pd.Timestamp(frame.iloc[index]['timestamp']) != pd.Timestamp(row['timestamp']):
                return dict(status='conflicting', reason='sequence_timestamp_disagreement')
        checked[channel] = len(rows)
    return dict(status='reproduced', counts=checked, tolerance_us_cm=tolerance,
                scope='Pinned ordered observations only; not a new identity search or calibration acceptance')



def _split_sessions(recordings, gap_seconds=60.0, gap_factor=10.0):
    """Expose acquisition breaks without treating them as pulse boundaries."""
    segments = []
    for rec in recordings:
        samples = rec['samples']
        if samples.empty or not samples.timestamp.is_monotonic_increasing:
            segments.append(rec)
            continue
        delta = samples.timestamp.diff().dt.total_seconds()
        cadence = delta[delta > 0].median()
        threshold = max(gap_seconds, gap_factor * cadence) if pd.notna(cadence) else gap_seconds
        boundaries = [0, *np.flatnonzero((delta > threshold).to_numpy()), len(samples)]
        for number, (start, end) in enumerate(zip(boundaries, boundaries[1:]), 1):
            piece = samples.iloc[start:end].copy()
            segment = dict(rec, samples=piece, source_logical_recording_id=rec['logical_recording_id'],
                           acquisition_start_local=str(piece.timestamp.min()),
                           acquisition_end_local=str(piece.timestamp.max()),
                           acquisition_gap_threshold_seconds=float(threshold))
            if len(boundaries) > 2:
                segment['logical_recording_id'] = rec['logical_recording_id'] + f':S{number:02}'
            segment['dates'] = sorted(set(piece.timestamp.dropna().dt.date.astype(str)))
            segments.append(segment)
    return segments


def _local_release_clock(trial, provenance):
    source = provenance.get('trials', {}).get(trial['trial_id'], {}).get('source_record', {})
    raw = str(source.get('injection_time_raw') or '')
    value = str(source.get('injection_time_local') or raw)
    # A question mark is evidence of uncertainty, not punctuation to discard.
    if '?' in raw or not re.fullmatch(r'\d{1,2}:\d{2}(:\d{2})?', value):
        return None
    try:
        return pd.Timestamp(_date(trial['field_date']) + ' ' + value)
    except ValueError:
        return None


def _calibration_device(evidence, recordings):
    """Resolve native identity from pinned evidence, never from a guessed alias."""
    review = evidence.get('probe_identity_review',{})
    sequence = evidence.get('_matching_sequence',{})
    electronic = (sequence.get('status')=='reproduced' and any(
        channel in CHANNELS.values() and len(rows) >= 2 and sequence.get('counts',{}).get(channel,0) >= 2
        for channel,rows in review.get('matches',{}).items()))
    continuity = (review.get('basis')=='confirmed_trial_association_and_user_confirmed_within_trial_probe_continuity'
                  and review.get('trial_id')==evidence.get('source_trial_id') and bool(review.get('dataset_id')))
    result = dict(status='unverified',device_serial='',basis='placeholder_alias_not_identity',files=[])
    if not (electronic or continuity):
        return result
    pins = review.get('files',[])
    if not pins:
        return result
    # Match the exact processed/raw/metadata bundle whose observations were
    # reproduced. A path or registry alias alone cannot identify a sensor.
    candidates = []
    for rec in recordings:
        for ref, files in rec['member_files'].items():
            if continuity and ref != review['dataset_id']:
                continue
            processed = files.get('processed',{})
            if any(Path(pin['path'])==Path(processed.get('path','')) for pin in pins):
                candidates.append((rec,files))
    if not candidates:
        return dict(result,basis='native_identity_sources_unavailable')
    serials = set()
    for rec,files in candidates:
        if any('conflict' in i or 'mismatch' in i for i in rec['issues']):
            return dict(result,status='conflicting',basis='native_identity_source_conflict')
        for pin in pins:
            found = [f for f in files.values() if Path(f['path'])==Path(pin['path'])]
            if not found:
                return dict(result,basis='native_identity_sources_unavailable')
            if any(f['sha256']!=pin.get('sha256') for f in found):
                return dict(result,status='conflicting',basis='native_identity_hash_mismatch')
        if not all(kind in files and any(Path(pin['path'])==Path(files[kind]['path']) for pin in pins)
                   for kind in ('processed','metadata','raw')):
            return dict(result,basis='native_identity_bundle_incomplete')
        if rec.get('device_serial'):
            serials.add(rec['device_serial'])
    if len(serials)>1:
        return dict(result,status='conflicting',basis='multiple_native_calibration_devices')
    if len(serials)==1:
        return dict(status='verified',device_serial=next(iter(serials)),
                    basis='electronic_sequence' if electronic else 'within_trial_continuity',files=pins)
    return dict(result,basis='native_calibration_serial_unavailable')


def _reconcile_existing_links(result, trials, preparations, provenance, recordings, associations):
    """Audit current CSV links separately from whether a fitted K can be used.

    Source-confirmed file identity can identify an event with an uncertain clock.
    It cannot identify a segment within that file, transfer K across sensors, or
    settle competing preparations. Original records remain unchanged.
    """
    rows = []
    by_trial = {t['trial_id']: t for t in trials}
    for number, claim in enumerate(associations, 2):
        trial_id, dataset = claim['trial_id'], claim.get('dataset_id','')
        trial = by_trial[trial_id]
        matching = [r for r in recordings if dataset and dataset in r['members']]
        registered = provenance.get('datasets',{}).get(dataset,{})
        sources = [a for a in provenance.get('trial_inputs',[]) if a['trial_id']==trial_id and a.get('dataset_id')==dataset]
        reasons = []
        confirmed = any(a.get('field_status',{}).get('recording_identity')=='confirmed_file_and_probe; scientific_use_pending'
                        and a.get('evidence') for a in sources)
        if not matching or not confirmed:
            reasons.append('recording_source_relationship_unresolved')
        if dataset and claim.get('processed_path') != registered.get('processed_path'):
            reasons.append('current_dataset_path_conflict')
        measurement_issues = sorted({i for rec in matching for i in rec['issues'] if i=='nonfinite_conductivity'})
        for rec in matching:
            # Missing EC cells affect use of a known file, not its identity.
            reasons.extend(i for i in rec['issues'] if i not in ('unknown_probe_identity','nonfinite_conductivity'))
            if not rec.get('device_serial'):
                reasons.append('native_probe_identity_unresolved')
            if _date(trial['field_date']) not in rec.get('dates',[]):
                reasons.append('recording_date_conflict')
            if rec.get('site_alias') and rec['site_alias'] != trial['site_alias']:
                reasons.append('recording_site_conflict')
            if rec['activity'] in ('calibration','background','attenuation'):
                reasons.append('nonriver_activity')
            files = rec['member_files'].get(dataset,{})
            for kind, pin in (('processed','processed_sha256'),('metadata','metadata_sha256'),('raw','source_sha256')):
                if not registered.get(pin) or files.get(kind,{}).get('sha256') != registered.get(pin):
                    reasons.append(kind+'_identity_pin_unresolved')
        conflict = any('conflict' in r or 'mismatch' in r for r in reasons)
        recording_status = 'conflicting' if conflict else 'unresolved' if reasons else 'source_confirmed'
        recording_probe = matching[0].get('probe_alias','') if matching else ''
        calibration_id = claim.get('calibration_id','')
        source_calibrations = sorted(c for c,e in provenance.get('calibrations',{}).items()
                                     if e.get('source_trial_id')==trial_id and c in preparations)
        if not calibration_id and len(source_calibrations)==1:
            calibration_id = source_calibrations[0]
        calibration_status = ('source_linked' if calibration_id in source_calibrations else
                              'conflicting' if calibration_id else 'ambiguous' if source_calibrations else 'missing')
        calibration_probe = provenance.get('calibrations',{}).get(calibration_id,{}).get('probe_alias','')
        basis = claim.get('conductivity_basis','')
        fits = [c for c in result['calibration_candidates'] if c['trial_id']==trial_id and c['calibration_id']==calibration_id
                and c['conductivity_basis']==basis
                and any(c['recording_edge_id']==trial_id+':'+r['logical_recording_id'] for r in matching)]
        options = {(c['calibration_id'],c['probe_alias'],c['conductivity_basis']):c for c in fits}
        fit = next(iter(options.values())) if len(options)==1 else {}
        if calibration_status != 'source_linked':
            applicability = 'calibration_relationship_unresolved'
        elif len(options)>1:
            applicability = 'competing_calibration_series'
        elif not fit:
            applicability = 'missing_fit_or_channel'
        elif fit['identity_status']=='native_conflict':
            applicability = 'native_device_conflict'
        elif 'conductivity_channel_unavailable' in fit['reasons']:
            applicability = 'unavailable_channel'
        elif 'competing_calibration_preparations' in fit['reasons']:
            applicability = 'competing_calibrations'
        elif fit['status']!='supported' or recording_status!='source_confirmed' or measurement_issues:
            applicability = 'evidence_requires_review'
        else:
            applicability = {'native_match':'native_identity_and_channel_supported',
                             'source_protocol_match':'source_linked_within_trial_protocol'}.get(
                                 fit['identity_status'],'source_linked_identity_unverified')
        # A confirmed whole-file relationship is not enough to choose between
        # acquisition segments. A clear clock may still resolve these below.
        if len(matching)>1:
            reasons.append('acquisition_segment_unresolved')
        reasons.extend(measurement_issues)
        citations = [a for a in sources if a.get('evidence')]
        if recording_status=='source_confirmed' and len(matching)==1:
            for edge in result['recording_candidates']:
                if edge['trial_id']==trial_id and edge['logical_recording_id']==matching[0]['logical_recording_id']:
                    edge['source_link_evidence'] = citations
        rows.append(dict(csv_row_number=number,trial_id=trial_id,dataset_id=dataset,
            processed_path=claim.get('processed_path',''),original_calibration_id=claim.get('calibration_id',''),
            calibration_id=calibration_id,source_calibration_candidates=source_calibrations,
            recording_probe_alias=recording_probe,calibration_probe_alias=calibration_probe,
            recorded_probe_alias=claim.get('probe_alias',''),
            recording_device_serial=matching[0].get('device_serial','') if matching else '',
            calibration_device_serial=fit.get('calibration_device_serial',''),
            identity_status=fit.get('identity_status','unverified'),identity_evidence=fit.get('identity_evidence',{}),
            fit_candidate_references=[c.get('fit_reference',{}) for c in options.values()],
            conductivity_basis=basis,k=fit.get('k',''),calibration_basis=fit.get('calibration_basis',''),
            concentration_unit=fit.get('concentration_unit',''),coefficient_unit=fit.get('coefficient_unit',''),
            fit_reference=fit.get('fit_reference',{}),recording_link_status=recording_status,
            calibration_link_status=calibration_status,applicability_status=applicability,
            reasons=sorted(set(reasons)),source_evidence=citations))
    result['trial_associations'] = rows
    for summary in result['pairing_summary']:
        related = [r for r in rows if r['trial_id']==summary['trial_id']]
        summary['source_confirmed_recording_rows'] = [r['csv_row_number'] for r in related if r['recording_link_status']=='source_confirmed']
        summary['source_linked_calibration_ids'] = sorted({r['calibration_id'] for r in related if r['calibration_link_status']=='source_linked'})
        source = provenance.get('trials',{}).get(summary['trial_id'],{}).get('source_record',{})
        summary['trial_disposition'] = 'practice' if source.get('treatment_label')=='practice' else 'field_release'


def _infer_chronology(result, trials, provenance, recordings, tolerance_seconds, overrides):
    """Apply the reported local-clock/trial protocol, retaining qualifications."""
    segments = {r['logical_recording_id']: r for r in recordings}
    trials_by_id = {t['trial_id']: t for t in trials}
    for edge in result['recording_candidates']:
        edge.update(selected_for_pairing=False, chronology_evidence={}, qualifications=[])
        rec = segments[edge['logical_recording_id']]
        trial = trials_by_id[edge['trial_id']]
        local = _local_release_clock(trial, provenance)
        samples = rec['samples']
        technical = [i for i in rec['issues'] if i != 'unknown_probe_identity']
        eligible = (rec.get('instrument_family') == 'aquatroll' and rec['conductivity_bases']
                    and rec['activity'] not in ('calibration','background','attenuation')
                    and not technical and not samples.empty and edge['status'] != 'conflicting')
        if not eligible:
            continue
        # Prefer explicit UTC when both sides have it. Otherwise compare the
        # written civil clocks under the reported field protocol; do not create UTC.
        release_utc, effective_release_basis = _release_time(trial, provenance, overrides)
        correction = edge['time_evidence'].get('correction_seconds',0)
        basis = 'reported_local_field_clock'
        if release_utc is not None:
            if 'timestamp_utc' not in samples or samples.timestamp_utc.isna().any():
                continue
            release = pd.Timestamp(release_utc)
            if release.tzinfo is None:
                continue
            release = release.tz_convert('UTC')
            times = samples.timestamp_utc + pd.to_timedelta(correction,unit='s')
            basis = 'explicit_utc'
        elif local is not None:
            release = local
            times = samples.timestamp + pd.to_timedelta(correction,unit='s')
            if times.dt.tz is not None:
                times = times.dt.tz_localize(None)
        elif edge.get('source_link_evidence'):
            # The notebook and measured device already identify this file.
            # Retain the uncertain clock instead of manufacturing an exact time.
            edge['chronology_evidence'] = dict(clock_basis='source_confirmed_file_relationship',
                eligible_for_protocol_pairing=True,release_clock='',source_link_evidence=edge['source_link_evidence'])
            edge['qualifications'] = list(edge['reasons']) + ['uncertain_release_clock_retained']
            continue
        else:
            continue
        first, last = times.min(), times.max()
        separation = max((first-release).total_seconds(), (release-last).total_seconds(), 0.0)
        edge['chronology_evidence'] = dict(release_clock=str(release),clock_basis=basis,
            acquisition_start_local=str(samples.timestamp.min()),acquisition_end_local=str(samples.timestamp.max()),
            reviewed_clock_correction_seconds=correction,effective_release_basis=effective_release_basis,
            separation_from_acquisition_seconds=float(separation),tolerance_seconds=tolerance_seconds,
            source_logical_recording_id=rec.get('source_logical_recording_id',rec['logical_recording_id']),
            user_protocol='Same field date; trial chronology and acquisition breaks normally identify trials.')
        if separation > tolerance_seconds:
            continue
        edge['chronology_evidence']['within_association_tolerance'] = True
        edge['qualifications'] = list(edge['reasons']) + edge.get('alias_qualifications',[])
        if basis == 'reported_local_field_clock':
            edge['qualifications'].append('local_clock_alignment_assumed_not_utc_conversion')
        if not rec['site_alias']:
            sites = {t['site_alias'] for t in trials if _date(t['field_date']) == _date(trial['field_date'])}
            if len(sites) != 1:
                edge['qualifications'].append('multiple_sites_on_day')
                continue
            edge['qualifications'].append('site_assumed_from_single_site_field_day')
        edge['chronology_evidence']['eligible_for_protocol_pairing'] = True
    for trial in trials:
        identity = trial['trial_id']
        edges = [e for e in result['recording_candidates'] if e['trial_id']==identity]
        possible = [e for e in edges if e['chronology_evidence'].get('eligible_for_protocol_pairing')]
        selected, competing = [], []
        by_device = {}
        for edge in possible:
            key = edge['device_serial'] or 'unidentified_device'
            by_device.setdefault(key, []).append(edge)
        for device_edges in by_device.values():
            reviewed = [e for e in device_edges if e['status']=='supported']
            sourced = [e for e in device_edges if e.get('source_link_evidence')]
            if len(reviewed)==1:
                selected.extend(reviewed)
            elif len(sourced)==1:
                selected.extend(sourced)
            elif len(device_edges)==1:
                selected.extend(device_edges)
            else:
                competing.extend(e['recording_edge_id'] for e in device_edges)
                for edge in device_edges:
                    edge['qualifications'].append('competing_sessions_for_same_device')
        for edge in selected:
            edge['selected_for_pairing'] = True
            if edge['status'] != 'supported':
                edge['status']='inferred'
                edge['reasons']=['source_confirmed_file_relationship' if edge.get('source_link_evidence') else 'date_and_local_clock_protocol']
        summary = next(s for s in result['pairing_summary'] if s['trial_id']==identity)
        summary.update(selected_recording_edge_ids=[e['recording_edge_id'] for e in selected],
                       selected_calibration_edge_ids=[],pairing_assumptions=[])
        if not selected:
            continue
        # Keep the legacy explicitly reviewed path intact; this revision adds
        # protocol-based proposals rather than weakening a review decision.
        reasons=[]
        for edge in selected:
            compatible=[c for c in result['calibration_candidates'] if c['recording_edge_id']==edge['recording_edge_id'] and c['status']=='supported']
            summary['selected_calibration_edge_ids'].extend(c['calibration_edge_id'] for c in compatible)
            if not compatible:
                reasons.append('compatible_k_unresolved:'+edge['recording_edge_id'])
            summary['pairing_assumptions'].extend(edge['qualifications'])
        if competing:
            reasons.append('competing_sessions_for_same_device')
        expected=summary.get('expected_main_roles',[])
        for role in expected:
            if not any(e['role']==role for e in selected):
                reasons.append('missing_role:'+role)
        selected_ids={e['logical_recording_id'] for e in selected}
        for check in summary.get('curated_claim_checks',[]):
            claim=check['claim']
            claimed_ids={r['logical_recording_id'] for r in recordings if claim.get('dataset_id') in r['members'] or
                (claim.get('processed_path') and any(f.get('processed',{}).get('path')==claim['processed_path'] for f in r['member_files'].values()))}
            if claimed_ids and not (claimed_ids & selected_ids):
                check['reasons']=sorted(set(check['reasons']+['curated_recording_differs_from_protocol_pairing']))
        substantive=[r for r in summary['reasons'] if r.startswith('curated_') or 'conflict' in r]
        substantive.extend(r for check in summary.get('curated_claim_checks',[]) for r in check['reasons'])
        reasons.extend(substantive)
        if any('conflict' in r for r in substantive):
            status='conflicting'
        elif competing or any(any(reason in c['reasons'] for reason in ('competing_calibration_preparations','competing_calibration_series')) for c in result['calibration_candidates']
                              if c['recording_edge_id'] in summary['selected_recording_edge_ids']):
            status='ambiguous'
        elif reasons:
            status='partial'
        else:
            status='complete_proposal' if all(e['status']=='supported' for e in selected) and expected else 'inferred_proposal'
        summary.update(status=status,reasons=sorted(set(reasons)),pairing_assumptions=sorted(set(summary['pairing_assumptions'])))


def match_records(trials, calibrations, fits, provenance, recordings, overrides=None, *, associations=None, protocol=True, gap_seconds=60.0, gap_factor=10.0, tolerance_seconds=120.0):
    """Return recording edges, calibration edges and a status for every release."""
    if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<=0 for v in (gap_seconds,gap_factor,tolerance_seconds)):
        raise ValueError('Session and association tolerances must be finite and positive')
    recordings = _split_sessions(recordings,gap_seconds,gap_factor) if protocol else recordings
    overrides = _validate_overrides(overrides, trials, calibrations, recordings)
    associations = provenance.get('trial_inputs', []) if associations is None else associations
    preparations = {c['calibration_id']: c for c in calibrations}
    if len(preparations) != len(calibrations) or len({t['trial_id'] for t in trials}) != len(trials):
        raise ValueError('Duplicate authoritative trial/calibration ID')
    fit_keys = [(f['calibration_id'],f.get('probe_alias',''),f['conductivity_basis']) for f in fits]
    if len(set(fit_keys)) != len(fit_keys):
        raise ValueError('Duplicate calibration fit key')
    native_calibrations = {c['calibration_id']:_calibration_device(provenance.get('calibrations',{}).get(c['calibration_id'],{}),recordings)
                           for c in calibrations}
    record_edges, cal_edges, summaries, exclusions = [], [], [], []
    for trial in sorted(trials, key=lambda t: t['trial_id']):
        trial_id, day = trial['trial_id'], _date(trial['field_date'])
        if not day:
            raise ValueError(f'Invalid trial date: {trial_id}')
        release_time, release_basis = _release_time(trial, provenance, overrides)
        for recording in recordings:
            rec = dict(recording, issues=list(recording['issues']))
            applicable = [o for o in overrides['recordings'] if o['content_ref'] in rec['members']]
            for key in ('site_alias','role','activity','clock_correction_seconds','clock_basis'):
                values = {o[key] for o in applicable if key in o}
                if len(values) > 1:
                    raise ValueError('Conflicting overrides for one logical recording')
                if values:
                    value = next(iter(values))
                    if key in ('site_alias','role','activity') and rec.get(key) not in ('', None, 'unknown', value):
                        rec['issues'].append(key + '_override_conflict')
                    rec['clock_correction_basis' if key=='clock_basis' else key] = value
            reject = []
            if rec.get('site_alias') and rec['site_alias'] != trial['site_alias']:
                reject.append('different_site')
            if rec.get('dates') and day not in rec['dates']:
                # UTC-midnight releases may share a recording on a different local date.
                times = rec['samples'].get('timestamp_utc', pd.Series(dtype='datetime64[ns, UTC]'))
                if release_time is None or times.empty or not (times.min() <= release_time <= times.max()):
                    reject.append('different_date' if rec.get('dates') else 'measurement_date_unavailable')
            if rec.get('activity') in ('calibration','background'):
                reject.append('nonriver_activity')
            if reject:
                exclusions.append(dict(trial_id=trial_id,logical_recording_id=rec['logical_recording_id'], reasons=reject))
                continue
            links = [o for o in overrides['recording_links'] if o['trial_id'] == trial_id and o['content_ref'] in rec['members']]
            existing = [a for a in associations
                        if a['trial_id'] == trial_id and a.get('dataset_id') in rec['members']]
            reasons = list(rec['issues'])
            if not rec.get('site_alias'):
                reasons.append('site_unresolved')
            if not rec.get('role'):
                reasons.append('recording_role_unresolved')
            if rec.get('activity') == 'unknown':
                reasons.append('recording_activity_unresolved')
            clock_ok = bool(rec.get('clock_basis') in ('explicit_report_numeric_offset','offset_in_source_timestamps') and 'timestamp_utc' in rec['samples'])
            if not clock_ok:
                reasons.append('measurement_clock_unresolved')
            if release_time is None:
                reasons.append('release_clock_unresolved')
            time_evidence = dict(release_utc=str(release_time) if release_time is not None else '', release_basis=release_basis,
                                 measurement_basis=rec.get('clock_basis', ''),
                                 source_offset_seconds=rec.get('source_offset_seconds'),
                                 correction_seconds=rec.get('clock_correction_seconds',0),
                                 correction_basis=rec.get('clock_correction_basis',''))
            if clock_ok and release_time is not None:
                times = rec['samples']['timestamp_utc'] + pd.to_timedelta(rec.get('clock_correction_seconds',0),unit='s')
                time_evidence['release_within_recording'] = bool(times.min() <= release_time <= times.max())
                # Outside coverage is not proof of a wrong link: a downstream pulse may arrive later.
                if not time_evidence['release_within_recording']:
                    reasons.append('release_outside_recording_requires_travel_evidence')
            if not links:
                reasons.append('no_reviewed_release_recording_relationship')
            status = 'supported' if not reasons else 'ambiguous'
            if any('conflict' in r or 'mismatch' in r for r in reasons):
                status = 'conflicting'
            if rec['samples'].empty:
                status = 'unavailable'
            edge_id = trial_id + ':' + rec['logical_recording_id']
            edge = dict(recording_edge_id=edge_id,trial_id=trial_id,logical_recording_id=rec['logical_recording_id'],
                        member_refs=rec['members'],probe_alias=rec.get('probe_alias',''),role=rec.get('role',''),
                        device_serial=rec.get('device_serial',''),alias_qualifications=rec.get('alias_qualifications',[]),
                        activity=rec['activity'],status=status,reasons=sorted(set(reasons)),time_evidence=time_evidence,
                        reviewed_evidence=links,existing_associations=existing,
                        source_link_evidence=[],
                        provenance_associations=[a for a in provenance.get('trial_inputs', []) if a['trial_id']==trial_id and a.get('dataset_id') in rec['members']],
                        source_site_alias=recording.get('site_alias',''),source_activity=recording.get('activity',''),
                        signal_summary=rec.get('signal_summary', {}))
            record_edges.append(edge)
            for fit in fits:
                cal_id = fit['calibration_id']
                prep = preparations.get(cal_id)
                if prep is None:
                    raise ValueError(f'Fit references unknown calibration: {cal_id}')
                evidence = provenance.get('calibrations', {}).get(cal_id, {})
                source_trial = evidence.get('source_trial_id')
                reviewed = [o for o in overrides['calibration_links'] if o['trial_id'] == trial_id
                            and o['calibration_id'] == cal_id and o['probe_alias'] == fit.get('probe_alias')]
                explicit_relationship = source_trial == trial_id or bool(reviewed)
                if not explicit_relationship and (source_trial or _date(prep['field_date']) != day
                                                  or prep.get('site_alias') != trial['site_alias']):
                    continue
                cal_reasons = []
                if not explicit_relationship:
                    cal_reasons.append('no_trial_calibration_source_relationship')
                native = native_calibrations[cal_id]
                identity_status = 'unverified'
                if native['status']=='conflicting':
                    cal_reasons.append('native_identity_evidence_conflict')
                    identity_status='evidence_conflict'
                elif native['device_serial'] and rec.get('device_serial'):
                    if native['device_serial']!=rec['device_serial']:
                        cal_reasons.append('native_calibration_device_conflict')
                        identity_status='native_conflict'
                    else:
                        identity_status='native_match' if native['basis']=='electronic_sequence' else 'source_protocol_match'
                if any('mismatch' in i or 'conflict' in i for i in rec['issues']):
                    cal_reasons.append('recording_evidence_conflict')
                if fit['conductivity_basis'] not in rec['conductivity_bases']:
                    cal_reasons.append('conductivity_channel_unavailable')
                expected_unit = {'mass_concentration':'mg/L','relative_concentration':'mL/mL'}.get(fit.get('calibration_basis'))
                if expected_unit is None or fit.get('concentration_unit') != expected_unit or fit.get('coefficient_unit') != f'({expected_unit}) / (uS/cm)':
                    cal_reasons.append('incompatible_fit_units')
                try:
                    if not math.isfinite(float(fit['k'])) or float(fit['k']) <= 0:
                        raise ValueError('nonpositive K')
                except (ValueError,TypeError,KeyError):
                    cal_reasons.append('invalid_k')
                if fit.get('fit_method') != 'OLS concentration on conductivity; free intercept' or fit.get('status') not in ('provisional','accepted'):
                    cal_reasons.append('unsupported_fit_method_or_status')
                sequence = evidence.get('_matching_sequence', {'status':'unavailable','reason':'not_checked_in_this_call'})
                if sequence['status'] == 'conflicting':
                    cal_reasons.append('electronic_sequence_conflict')
                cal_status = 'supported' if not cal_reasons else 'ambiguous'
                if any(r in cal_reasons for r in ('native_calibration_device_conflict','native_identity_evidence_conflict','recording_evidence_conflict',
                                                 'incompatible_fit_units','invalid_k','electronic_sequence_conflict')):
                    cal_status = 'conflicting'
                elif 'conductivity_channel_unavailable' in cal_reasons:
                    cal_status = 'unavailable'
                cal_edges.append(dict(calibration_edge_id=edge_id + ':' + ':'.join((cal_id,fit.get('probe_alias',''),fit['conductivity_basis'])),
                    recording_edge_id=edge_id,trial_id=trial_id,calibration_id=cal_id,probe_alias=fit.get('probe_alias',''),
                    conductivity_basis=fit['conductivity_basis'],calibration_basis=fit.get('calibration_basis',''),
                    concentration_unit=fit.get('concentration_unit',''),coefficient_unit=fit.get('coefficient_unit',''),k=fit.get('k'),
                    recording_device_serial=rec.get('device_serial',''),calibration_device_serial=native['device_serial'],
                    identity_status=identity_status,identity_evidence=native,
                    alias_qualification='record_aliases_are_placeholders_not_physical_evidence',
                    fit_reference=fit.get('_fit_reference',{}),status=cal_status,reasons=cal_reasons,
                    mass_route_eligible=expected_unit=='mg/L' and cal_status=='supported',
                    source_relationship=source_trial or '',reviewed_evidence=reviewed,electronic_sequence=sequence))
    # Conflicting positive preparations are ties, not an opportunity to select the highest R².
    for edge in record_edges:
        candidates = [c for c in cal_edges if c['recording_edge_id'] == edge['recording_edge_id'] and c['status']=='supported']
        for basis in CHANNELS:
            choices = [c for c in candidates if c['conductivity_basis']==basis]
            if len(choices) > 1:
                for candidate in choices:
                    candidate['status']='ambiguous';candidate['mass_route_eligible']=False
                    candidate['reasons'].append('competing_calibration_preparations' if len({c['calibration_id'] for c in choices})>1
                                                else 'competing_calibration_series')
    for trial in sorted(trials, key=lambda t: t['trial_id']):
        identity=trial['trial_id']
        edges=[e for e in record_edges if e['trial_id']==identity]
        calibrations_for_trial=[c for c in cal_edges if c['trial_id']==identity]
        reasons=[]
        expected=next((o['roles'] for o in overrides['expected_roles'] if o['trial_id']==identity), None)
        main=[e for e in edges if e['role']!='attenuation']
        if not edges:
            status='unmatched';reasons.append('no_plausible_recording')
        elif any(e['status']=='conflicting' for e in main):
            status='conflicting';reasons.append('recording_conflict')
        elif any(e['status']=='ambiguous' for e in main):
            status='ambiguous';reasons.append('recording_assignment_unresolved')
        elif main and all(e['status']=='unavailable' for e in main):
            status='unavailable';reasons.append('recording_data_unavailable')
        else:
            status='complete_proposal'
            if expected is None:
                status='partial';reasons.append('expected_main_roles_unresolved')
            else:
                for role in expected:
                    supported=[e for e in main if e['role']==role and e['status']=='supported']
                    if not supported:
                        status='partial';reasons.append('missing_role:'+role)
                    if len({e['device_serial'] for e in supported}) > 1:
                        status='ambiguous';reasons.append('competing_devices_for_role:'+role)
                    for e in supported:
                        compatible=[c for c in calibrations_for_trial if c['recording_edge_id']==e['recording_edge_id'] and c['status']=='supported']
                        if not compatible:
                            status='ambiguous' if any(c['status']=='ambiguous' for c in calibrations_for_trial) else 'partial'
                            reasons.append('compatible_k_unresolved:'+e['recording_edge_id'])
                if any(e['role'] not in expected for e in main):
                    status='partial';reasons.append('unexpected_main_role')
        claim_checks = []
        for claim in [a for a in associations if a['trial_id']==identity]:
            if not claim.get('dataset_id') and not claim.get('processed_path'):
                continue
            dataset_matches=[r for r in recordings if claim.get('dataset_id') in r['members']]
            path_matches=[r for r in recordings if claim.get('processed_path') and any(
                str(Path(f.get('processed',{}).get('path',''))) == str(Path(claim['processed_path']))
                for f in r['member_files'].values())]
            candidates=dataset_matches or path_matches
            problems=[]
            if not candidates:
                problems.append('curated_recording_unavailable')
            if claim.get('dataset_id') and not dataset_matches:
                problems.append('curated_dataset_id_unavailable')
            if claim.get('processed_path') and not path_matches:
                problems.append('curated_path_unavailable')
            if dataset_matches and path_matches and {r['logical_recording_id'] for r in dataset_matches} != {r['logical_recording_id'] for r in path_matches}:
                problems.append('curated_dataset_path_conflict')
            for recording in candidates:
                associated=[e for e in edges if e['logical_recording_id']==recording['logical_recording_id']]
                if not associated:
                    problems.append('curated_recording_excluded_by_independent_evidence')
                for edge in associated:
                    if claim.get('recording_role') and edge.get('role') and claim['recording_role'] != edge['role']:
                        problems.append('curated_role_conflict')
                    if claim.get('calibration_id'):
                        comparisons=[c for c in calibrations_for_trial if c['recording_edge_id']==edge['recording_edge_id'] and c['calibration_id']==claim['calibration_id']
                            and (not claim.get('conductivity_basis') or c['conductivity_basis']==claim['conductivity_basis'])]
                        if not comparisons:
                            problems.append('curated_calibration_fit_unavailable')
                        elif all(c['status']=='conflicting' for c in comparisons):
                            problems.append('curated_calibration_conflict')
                        elif not any(c['status']=='supported' for c in comparisons):
                            problems.append('curated_calibration_unresolved')
                if claim.get('conductivity_basis') and claim['conductivity_basis'] not in recording['conductivity_bases']:
                    problems.append('curated_channel_unavailable')
            claim_checks.append(dict(claim=claim,reasons=sorted(set(problems))))
            reasons.extend(problems)
        if any('conflict' in r or r=='curated_recording_excluded_by_independent_evidence' for r in reasons):
            status='conflicting'
        elif any(r.startswith('curated_') for r in reasons) and status=='complete_proposal':
            status='partial'
        summaries.append(dict(trial_id=identity,status=status,recording_edge_ids=[e['recording_edge_id'] for e in edges],
                              calibration_edge_ids=[c['calibration_edge_id'] for c in calibrations_for_trial],
                              expected_main_roles=expected or [],reasons=sorted(set(reasons)),curated_claim_checks=claim_checks,scientifically_accepted=False))
    result = dict(recording_candidates=record_edges,calibration_candidates=cal_edges,pairing_summary=summaries,exclusions=exclusions)
    _reconcile_existing_links(result,trials,preparations,provenance,recordings,associations)
    if protocol:
        _infer_chronology(result,trials,provenance,recordings,tolerance_seconds,overrides)
    for summary in summaries:
        selected = summary.get('selected_calibration_edge_ids',[]) if protocol else [
            c['calibration_edge_id'] for c in cal_edges if c['trial_id']==summary['trial_id'] and c['status']=='supported']
        summary['identity_review_required'] = not selected or any(c['identity_status']!='native_match' for c in cal_edges
                                                                  if c['calibration_edge_id'] in selected) or any(
            c['identity_status'] in ('native_conflict','evidence_conflict') and
            c['recording_edge_id'] in summary.get('selected_recording_edge_ids',summary['recording_edge_ids']) and
            (c['source_relationship']==summary['trial_id'] or c['reviewed_evidence']) for c in cal_edges)
        summary['identity_policy'] = 'Source links establish pairings; placeholder aliases do not establish physical identity.'
    result['calibration_device_checks'] = native_calibrations
    result['recording_segments'] = [dict(logical_recording_id=r['logical_recording_id'],
        source_logical_recording_id=r.get('source_logical_recording_id',r['logical_recording_id']),
        members=r['members'],sample_count=len(r['samples']),
        acquisition_start_local=r.get('acquisition_start_local',''),acquisition_end_local=r.get('acquisition_end_local','')) for r in recordings]
    return result


def _read_table(path, required):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not set(required).issubset(reader.fieldnames) or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f'Invalid table schema: {path}')
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f'Malformed CSV row: {path}')
    return rows


def _write_table(path, rows, fields):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k:_json(v) if isinstance(v,(dict,list,bool)) else v for k,v in row.items()})


def run_matching(records_dir, processed_dir, calibration_dir, output_dir, *, root=ROOT, overrides_path=None, protocol=True, gap_seconds=60.0, gap_factor=10.0, tolerance_seconds=120.0):
    """Publish a new reproducible proposal bundle after validating pinned inputs."""
    root = Path(root).resolve()
    if Path(output_dir).is_symlink():
        raise ValueError('Output must not traverse a symlink')
    records_dir, processed_dir, calibration_dir, output_dir = [Path(p).resolve() for p in (records_dir,processed_dir,calibration_dir,output_dir)]
    if Path(output_dir).is_symlink() or (output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir()))):
        raise FileExistsError(f'Refusing existing output: {output_dir}')
    if any(output_dir.is_relative_to(p) or p.is_relative_to(output_dir) for p in (records_dir,processed_dir,calibration_dir)):
        raise ValueError('Output must be separate from input directories')
    trials = _read_table(records_dir/'trials.csv', ['trial_id','field_date','site_alias','dump_timestamp_utc'])
    calibrations = _read_table(records_dir/'calibrations.csv', ['calibration_id','field_date','site_alias'])
    points = _read_table(records_dir/'calibration_points.csv', ['calibration_id','step_no','probe_alias'])
    associations = _read_table(records_dir/'trial_inputs.csv', ['trial_id','dataset_id','processed_path'])
    for rows, key in ((trials,'trial_id'),(calibrations,'calibration_id')):
        values = [row[key] for row in rows]
        if any(not v for v in values) or len(set(values)) != len(values):
            raise ValueError(f'Duplicate or blank authoritative {key}')
    if any(a['trial_id'] not in {t['trial_id'] for t in trials} for a in associations):
        raise ValueError('Association references unknown trial')
    point_keys=[(p['calibration_id'],p['step_no'],p['probe_alias']) for p in points]
    if len(set(point_keys)) != len(point_keys):
        raise ValueError('Duplicate calibration observation key')
    if any(p['calibration_id'] not in {c['calibration_id'] for c in calibrations} for p in points):
        raise ValueError('Calibration point references unknown preparation')
    provenance_path = records_dir/'provenance.json'
    provenance = json.loads(provenance_path.read_text())
    fit_path = calibration_dir/'calibration_fits.csv'
    fit_run_path = calibration_dir/'run_info.json'
    fit_run = json.loads(fit_run_path.read_text())
    inputs = {records_dir/name for name in ('trials.csv','calibrations.csv','calibration_points.csv','trial_inputs.csv','provenance.json')}
    inputs.update((fit_path,fit_run_path))
    required_pins={'calibrations.csv','calibration_points.csv','provenance.json','procedure_versions.json'}
    pins={}
    for item in fit_run.get('inputs', []):
        name=Path(item['path']).name
        path=records_dir/name if name in {'calibrations.csv','calibration_points.csv','provenance.json'} else _path(item['path'],root)
        if not path.is_relative_to(root) or not path.is_file() or _hash(path) != item.get('sha256'):
            raise ValueError(f'Stale calibration input hash: {item["path"]}')
        if name in pins:
            raise ValueError('Duplicate calibration input pin')
        pins[name]=item; inputs.add(path)
    if not required_pins.issubset(pins):
        raise ValueError('Calibration run lacks required input hashes')
    fit_outputs=[o for o in fit_run.get('outputs',[]) if o['path']=='calibration_fits.csv']
    if len(fit_outputs)!=1 or _hash(fit_path)!=fit_outputs[0].get('sha256'):
        raise ValueError('Calibration fit output hash mismatch')
    fits = _read_table(fit_path, ['calibration_id','probe_alias','conductivity_basis','calibration_basis','k',
                                 'concentration_unit','coefficient_unit','fit_method','status'])
    for fit in fits:
        fit['_fit_reference'] = dict(run_path=_ref(calibration_dir,root),run_info_sha256=_hash(fit_run_path),
                                     fit_table_sha256=_hash(fit_path),
                                     key=[fit['calibration_id'],fit['probe_alias'],fit['conductivity_basis']])
    overrides = None
    if overrides_path is not None:
        overrides_path=Path(overrides_path).resolve()
        overrides=json.loads(overrides_path.read_text());inputs.add(overrides_path)
    for evidence in provenance.get('calibrations',{}).values():
        for file in evidence.get('probe_identity_review',{}).get('files',[]):
            path=_path(file['path'],root)
            if path.is_file():
                inputs.add(path)
    code_paths = [Path(__file__), *sorted((ROOT/'salt_dilution/scripts/parsers').glob('*.py'))]
    inputs.update(code_paths)
    initial_hashes={_ref(path,root):_hash(path) for path in sorted(inputs)}
    for identity,evidence in provenance.get('calibrations',{}).items():
        evidence['_matching_sequence']=_sequence_evidence(identity,evidence,points,root)
    inventory=inventory_recordings(processed_dir,provenance,root)
    for rec in inventory:
        for file in rec['files'].values():
            initial_hashes[file['path']]=file['sha256']
    logical=reconcile_recordings(inventory)
    result=match_records(trials,calibrations,fits,provenance,logical,overrides,associations=associations,protocol=protocol,gap_seconds=gap_seconds,gap_factor=gap_factor,tolerance_seconds=tolerance_seconds)
    for name,digest in initial_hashes.items():
        if _hash(Path(name) if Path(name).is_absolute() else root/name) != digest:
            raise ValueError(f'Input changed during matching: {name}')
    try:
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except (OSError,subprocess.CalledProcessError):
        revision=None
    from collections import Counter
    info=dict(schema_version=2,created_at_utc=datetime.now(timezone.utc).isoformat(),git_commit=revision,
              code_sha256=_hash(Path(__file__)),python_version=__import__('platform').python_version(),
              numpy_version=np.__version__,pandas_version=pd.__version__,
              scope='Pairing proposals only; no background/window selection, concentration conversion or Q.',
              scientific_acceptance=False,release_count=len(trials),physical_file_count=len(inventory),
              logical_recording_count=len(logical),recording_segments=result['recording_segments'],status_counts=dict(Counter(r['status'] for r in result['pairing_summary'])),
              inputs=[dict(path=p,sha256=h) for p,h in sorted(initial_hashes.items())],
              parser_sha256={p.name:_hash(p) for p in sorted((ROOT/'salt_dilution/scripts/parsers').glob('*.py'))},
              overrides=overrides or {},sample_reference_policy='Member content_ref and zero-based normalized source row; original files retained. Equal overlaps coalesced only in memory.',
              excluded_nonrecording_tables=[_ref(p,root) for p in sorted(processed_dir.rglob('*.csv'))
                  if _ref(p,root) not in {r['path'] for r in inventory}],
              inventory=[{k:v for k,v in r.items() if k not in ('samples','metadata','evidence')} for r in inventory],
              logical_recordings=[dict(logical_recording_id=r['logical_recording_id'],members=r['members'],
                                       member_files=r['member_files'],issues=r['issues'],sample_count=len(r['samples'])) for r in logical],
              exclusions=result['exclusions'],
              electronic_sequence_checks={k:e['_matching_sequence'] for k,e in provenance.get('calibrations',{}).items()},
              calibration_device_checks=result['calibration_device_checks'],
              options=dict(protocol_inference=protocol,session_gap_seconds=gap_seconds,session_gap_factor=gap_factor,association_tolerance_seconds=tolerance_seconds,
                           probe_identity_policy='Record-table aliases are placeholders; source relationships establish K pairing, independently pinned native evidence establishes physical identity.',
                           mass_route_eligible='Compatible concentration units and a supported K link only; not discharge readiness or scientific acceptance.',
                           candidate_generation='all local date/site-compatible recordings; reviewed relationships required for support',
                           chronology='Reported field-local clocks under explicit protocol; association tolerance is operational, not a travel-time estimate or UTC correction',
                           gap_diagnostic='delta > 1.5 * median positive cadence; not an event boundary',
                           sequence='recheck pinned ordered observations with their recorded tolerance'),
              outputs=[])
    info['status']='complete_proposals' if all(r['status'] in ('complete_proposal','inferred_proposal') for r in result['pairing_summary']) else 'complete_with_unresolved'
    output_dir.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.matching-',dir=output_dir.parent))
    try:
        for name,fields in (('recording_candidates',['recording_edge_id','trial_id','logical_recording_id','status','reasons']),
                            ('calibration_candidates',['calibration_edge_id','recording_edge_id','trial_id','status','reasons']),
                            ('pairing_summary',['trial_id','status','reasons']),
                            ('trial_associations',['csv_row_number','trial_id','recording_link_status','calibration_link_status','applicability_status'])):
            path=stage/(name+'.csv');_write_table(path,result[name],fields)
            info['outputs'].append(dict(path=path.name,sha256=_hash(path)))
        (stage/'run_info.json').write_text(json.dumps(info,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
        if output_dir.exists():
            output_dir.rmdir()  # Only a still-empty directory may be replaced.
        stage.rename(output_dir)
    except BaseException:
        shutil.rmtree(stage)
        raise
    return info


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records',type=Path,default=ROOT/'salt_dilution/data/records')
    parser.add_argument('--processed',type=Path,default=ROOT/'salt_dilution/data/processed')
    parser.add_argument('--calibrations',type=Path,required=True,help='Saved calibration bundle with run_info.json')
    parser.add_argument('--output',type=Path,required=True,help='New output directory')
    parser.add_argument('--overrides',type=Path,help='Reviewed evidence JSON, schema_version 1; see docs/getting_started.md')
    parser.add_argument('--no-protocol-inference',action='store_true',help='Use only explicit reviewed pairing decisions')
    parser.add_argument('--session-gap-seconds',type=float,default=60,help='Minimum acquisition-break candidate gap; not an integration boundary')
    parser.add_argument('--session-gap-factor',type=float,default=10,help='Gap must also exceed this multiple of median sampling cadence')
    parser.add_argument('--association-tolerance-seconds',type=float,default=120,help='Working allowance outside acquisition coverage; not a measured travel time')
    args=parser.parse_args(argv)
    try:
        info=run_matching(args.records,args.processed,args.calibrations,args.output,overrides_path=args.overrides,protocol=not args.no_protocol_inference,gap_seconds=args.session_gap_seconds,gap_factor=args.session_gap_factor,tolerance_seconds=args.association_tolerance_seconds)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        parser.exit(2,f'Matching failed: {exc}\n')
    print(_json(dict(status=info['status'],releases=info['release_count'],status_counts=info['status_counts'],output=str(args.output))))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
