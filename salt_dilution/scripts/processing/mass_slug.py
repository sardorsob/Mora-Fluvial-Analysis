"""Proposed mass-slug discharge with explicit windows, gaps, units and source evidence."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from . import calibration, calibration_quality, calibration_reuse as reuse, matching

ROOT=matching.ROOT


def prepare_series(samples, channel, *, gap_seconds=5., gap_factor=3.):
    if channel not in matching.CHANNELS or matching.CHANNELS[channel] not in samples:
        raise ValueError('conductivity_channel_unavailable')
    if gap_seconds<=0 or gap_factor<=0:
        raise ValueError('invalid_gap_threshold')
    frame=pd.DataFrame(dict(timestamp=matching._times(samples['timestamp']),
                            ec=pd.to_numeric(samples[matching.CHANNELS[channel]],errors='coerce')))
    if 'sample_source' in samples:frame['sample_source']=samples.sample_source
    if frame.timestamp.isna().any():raise ValueError('invalid_sample_timestamp')
    frame=frame.sort_values('timestamp',kind='stable').reset_index(drop=True)
    if frame.empty:raise ValueError('empty_recording')
    repeated=frame[frame.duplicated('timestamp',keep=False)]
    if not repeated.empty and any(group.ec.nunique(dropna=False)>1 for _,group in repeated.groupby('timestamp')):
        raise ValueError('duplicate_timestamps_conflicting')
    count=int(frame.duplicated('timestamp').sum());issues=[]
    if count:issues.append(f'identical_duplicates_collapsed:{count}')
    frame=frame.drop_duplicates('timestamp').reset_index(drop=True)
    frame['t_s']=(frame.timestamp-frame.timestamp.iloc[0]).dt.total_seconds()
    delta=frame.t_s.diff();cadence=float(delta[delta>0].median()) if (delta>0).any() else 0
    frame['segment']=(delta>max(gap_seconds,gap_factor*cadence)).cumsum().astype(int)
    if frame.segment.nunique()>1:issues.append('sampling_gaps_present')
    if not np.isfinite(frame.ec).all():issues.append('nonfinite_conductivity_preserved')
    return frame,issues


def propose_windows(frame, *, release_offset_s=None, min_background_s=30., min_background_n=10,
                    max_background_s=120., threshold_floor=.5, k_sigma=3., settle_s=30.):
    candidates=[];problems=[];incomplete_peaks=[]
    for _,part in frame.groupby('segment',sort=True):
        part=part.reset_index(drop=True);t=part.t_s.to_numpy();ec=part.ec.to_numpy()
        pre=part.loc[part.t_s<=t[0]+min_background_s]
        finite=pre[np.isfinite(pre.ec)]
        if len(finite)<min_background_n or finite.t_s.iloc[-1]-finite.t_s.iloc[0]<min_background_s:
            problems.append('no_pre_pulse_background');continue
        coef=np.polyfit(finite.t_s,finite.ec,1)
        residual=ec-np.polyval(coef,t)
        noise=finite.ec-np.polyval(coef,finite.t_s)
        threshold=max(threshold_floor,k_sigma*float(np.std(noise,ddof=1)))
        if np.median(finite.ec.iloc[:5])-np.median(finite.ec.iloc[-5:])>threshold:
            problems.append('no_pre_pulse_background');continue
        if not np.isfinite(residual).any():continue
        peak=int(np.nanargmax(residual))
        if peak<len(pre) or ec[0]-np.nanmin(ec)>max(threshold,.2*(np.nanmax(ec)-np.nanmin(ec))):
            problems.append('no_pre_pulse_background');continue
        above=np.flatnonzero(np.isfinite(residual)&(residual>threshold)&(t>=pre.t_s.iloc[-1]))
        if not len(above):problems.append('no_detectable_pulse');continue
        groups=[]
        for i in above:
            if groups and t[i]-t[groups[-1][-1]]<=settle_s:groups[-1].append(int(i))
            else:groups.append([int(i)])
        maximum=max(float(np.max(residual[g])) for g in groups)
        groups=[g for g in groups if np.max(residual[g])>=.5*maximum]
        for g in groups:
            peak=g[int(np.argmax(residual[g]))]
            if release_offset_s is not None and t[peak]<release_offset_s:continue
            # Threshold crossings detect the event but omit low-amplitude tails.
            # Pad the integration proposal, then require a separate settled tail.
            start=max(int(np.searchsorted(t,t[g[0]]-10))-1,len(pre))
            end=int(np.searchsorted(t,t[g[-1]]+30))
            if end>=len(part) or t[-1]-t[end]<settle_s:
                problems.append('tail_incomplete');incomplete_peaks.append(float(t[peak]));continue
            post=part.loc[part.t_s.between(t[end],t[end]+settle_s)]
            tail=residual[end:end+len(post)]
            if len(post)<min_background_n or not np.isfinite(tail).all() or np.any(np.abs(tail)>threshold):
                problems.append('tail_incomplete');incomplete_peaks.append(float(t[peak]));continue
            if t[start]<=finite.t_s.iloc[-1]:
                problems.append('no_pre_pulse_background');continue
            candidates.append(dict(pre=[float(t[0]),float(finite.t_s.iloc[-1])],pulse=[float(t[start]),float(t[end])],
                post=[float(post.t_s.iloc[0]),float(post.t_s.iloc[-1])],peak_t_s=float(t[peak]),threshold_us_cm=threshold,
                segment=int(part.segment.iloc[0]),issues=[]))
    if release_offset_s is not None and candidates:
        chosen=min(candidates,key=lambda c:c['peak_t_s'])
        if any(peak<chosen['peak_t_s'] for peak in incomplete_peaks):
            return dict(issues=['earlier_pulse_incomplete'])
        return chosen
    if len(candidates)==1:return candidates[0]
    if len(candidates)>1:return dict(issues=['multiple_pulses_ambiguous'])
    return dict(issues=sorted(set(problems or ['no_detectable_pulse'])))


def _window_parts(frame, windows):
    parts=[]
    for key in ('pre','pulse','post'):
        pair=windows.get(key,[])
        if len(pair)!=2 or not all(math.isfinite(float(v)) for v in pair) or pair[0]>=pair[1]:
            raise ValueError('invalid_window_order')
        if pair[0]<frame.t_s.min() or pair[1]>frame.t_s.max():raise ValueError('window_outside_recording')
        part=frame.loc[frame.t_s.between(*pair)]
        if len(part)<2:raise ValueError('too_few_window_samples')
        parts.append(part)
    if windows['pre'][1]>windows['pulse'][0] or windows['pulse'][1]>windows['post'][0]:raise ValueError('overlapping_background_windows')
    whole=frame.loc[frame.t_s.between(windows['pre'][0],windows['post'][1])]
    if whole.segment.nunique()!=1:
        pause=windows.get('pre_injection_pause',{})
        release=pause.get('release_offset_s')
        pulse_start=parts[1].segment.iloc[0]
        resumed=float(frame.loc[frame.segment==pulse_start,'t_s'].min())
        # Only a documented pause before release can separate baseline from pulse.
        valid_pause=(all(p.segment.nunique()==1 for p in parts)
            and frame.loc[frame.t_s.between(windows['pulse'][0],windows['post'][1]),'segment'].nunique()==1
            and parts[0].segment.iloc[-1]<pulse_start
            and pause.get('background_applicable') is True and bool(pause.get('evidence'))
            and isinstance(release,(int,float)) and math.isfinite(release)
            and resumed<=release<=windows['pulse'][0])
        if not valid_pause:raise ValueError('pulse_or_background_crosses_segment_gap')
    if any(not np.isfinite(p.ec).all() for p in parts):raise ValueError('missing_cells_in_windows')
    return parts


def _background(t, pre, post, mode):
    a,b=float(pre.ec.mean()),float(post.ec.mean())
    if mode=='pre':return np.full_like(t,a,dtype=float)
    if mode=='post':return np.full_like(t,b,dtype=float)
    if mode!='linear':raise ValueError('unknown_background_mode')
    x,y=float(pre.t_s.mean()),float(post.t_s.mean())
    return a+(b-a)*(t-x)/(y-x)


def integrate_excess(frame, windows, *, background='linear'):
    pre,pulse,post=_window_parts(frame,windows)
    t=pulse.t_s.to_numpy();excess=pulse.ec.to_numpy()-_background(t,pre,post,background)
    return dict(integral_us_cm_s=float(np.trapezoid(excess,t)),negative_area_us_cm_s=float(np.trapezoid(np.minimum(excess,0),t)),
                bridged_cells=0,gap_bound_us_cm_s=None,baseline_shift_us_cm=float(post.ec.mean()-pre.ec.mean()),
                pulse_start_t_s=float(t[0]),pulse_end_t_s=float(t[-1]),pulse_samples=len(pulse))


def discharge(mass_g,k,integral):
    if not all(math.isfinite(float(v)) and float(v)>0 for v in (mass_g,k,integral)):
        raise ValueError('nonpositive_or_nonfinite_mass_k_or_integral')
    q=float(mass_g)*1000/(float(k)*float(integral))
    return dict(q_l_s=q,q_m3_s=q/1000)


def solution_discharge(volume_ml,k_relative,integral):
    """Conserve the original injectate volume using a relative-concentration K."""
    if not all(math.isfinite(float(v)) and float(v)>0 for v in (volume_ml,k_relative,integral)):
        raise ValueError('nonpositive_or_nonfinite_volume_k_or_integral')
    q=float(volume_ml)/1000/(float(k_relative)*float(integral))
    return dict(q_l_s=q,q_m3_s=q/1000)


def solution_quantity(trial,provenance,*,allow_reported=False):
    source=provenance.get('source_record',{})
    delivered=source.get('delivered_solution_ml')
    if delivered:
        volume=float(delivered);basis='recorded_delivered'
    elif allow_reported:
        reported=source.get('reported_injected_solution_ml')
        compact=trial.get('injection_solution_volume_ml')
        if not reported or not compact or not math.isclose(float(reported),float(compact)):
            raise ValueError('solution_volume_source_unresolved')
        volume=float(reported);basis='reported_delivery_assumed'
    else:
        raise ValueError('delivered_solution_volume_unavailable')
    if not math.isfinite(volume) or volume<=0:raise ValueError('invalid_solution_volume')
    return volume,basis


def uncertainty(frame,windows,mass_g,k,k_se,*,method='mass_slug'):
    pre,pulse,post=_window_parts(frame,windows)
    calculate=discharge if method=='mass_slug' else solution_discharge
    primary=calculate(mass_g,k,integrate_excess(frame,windows)['integral_us_cm_s'])['q_l_s']
    bg=[];edges=[]
    for mode in ('pre','post'):
        area=integrate_excess(frame,windows,background=mode)['integral_us_cm_s']
        if area>0:bg.append(abs(calculate(mass_g,k,area)['q_l_s']/primary-1))
    for a,b in ((windows['pulse'][0]-10,windows['pulse'][1]),(windows['pulse'][0]+10,windows['pulse'][1]),
                (windows['pulse'][0],windows['pulse'][1]-30),(windows['pulse'][0],windows['pulse'][1]+30)):
        if a<frame.t_s.min() or b>frame.t_s.max() or a>=b:continue
        p=frame.loc[frame.t_s.between(a,b)]
        if p.segment.nunique()!=1 or not np.isfinite(p.ec).all():continue
        area=float(np.trapezoid(p.ec.to_numpy()-_background(p.t_s.to_numpy(),pre,post,'linear'),p.t_s.to_numpy()))
        if area>0:edges.append(abs(calculate(mass_g,k,area)['q_l_s']/primary-1))
    uk=float(k_se)/float(k) if k_se not in ('',None) and math.isfinite(float(k_se)) else None
    ub=max(bg) if len(bg)==2 else None;uw=max(edges) if len(edges)==4 else None
    rss=float(np.sqrt(uk**2+sum(v**2 for v in (ub,uw) if v is not None))) if uk is not None else None
    return dict(u_k_fit_relative=uk,u_background_sensitivity=ub,u_window_sensitivity=uw,u_mass='not_quantified',u_gap='no_bridge_allowed',
                indicative_sensitivity_relative=rss,indicative_q_lower_l_s=max(0,primary*(1-rss)) if rss is not None else None,
                indicative_q_upper_l_s=primary*(1+rss) if rss is not None else None,
                uncertainty_scope='Indicative fit-SE plus deterministic sensitivity RSS; not a confidence interval or total Q uncertainty. Mass, recipe, mixing and clock errors unquantified.')


def _table(path, rows, empty_fields):
    fields = list(dict.fromkeys(key for row in rows for key in row)) or empty_fields
    matching._write_table(path, [{key: row.get(key, '') for key in fields} for row in rows], fields)


def _decoded(row, key, default):
    return json.loads(row[key]) if row.get(key) else default


def calibration_reference_fields(fit):
    """Attach a conditional reference to this coefficient without changing its value."""
    diagnostic = calibration_quality.reference_diagnostic(fit)
    return dict(calibration_reference_flags=diagnostic['flags'],
                calibration_reference_status=diagnostic['diagnostic_status'],
                calibration_reference_assumptions=diagnostic['reference_assumptions'])


def _selected_fit(edge, fits, calibration_dir):
    """A pairing edge is a reference to a fit, never a replacement coefficient."""
    reference = _decoded(edge, 'fit_reference', {})
    if (reference.get('fit_table_sha256') != matching._hash(calibration_dir/'calibration_fits.csv')
            or reference.get('run_info_sha256') != matching._hash(calibration_dir/'run_info.json')):
        raise ValueError('Selected fit reference does not identify this calibration bundle')
    key = tuple(reference.get('key', []))
    if key not in fits:
        raise ValueError('Selected fit reference key is absent')
    fit = fits[key]
    for field in ('calibration_id', 'probe_alias', 'conductivity_basis', 'k',
                  'calibration_basis', 'concentration_unit', 'coefficient_unit'):
        if edge.get(field, '') != fit.get(field, ''):
            raise ValueError(f'Selected fit differs from saved fit: {field}')
    return fit


def _recording_samples(edge, info, processed_dir, root):
    members = _decoded(edge, 'member_refs', [])
    segment = next((s for s in info.get('recording_segments', [])
                    if s['logical_recording_id'] == edge['logical_recording_id']), {})
    logical_id = segment.get('source_logical_recording_id', edge['logical_recording_id'])
    logical = next((r for r in info['logical_recordings'] if r['logical_recording_id'] == logical_id), None)
    if not logical or not members or set(members) != set(logical['members']):
        raise ValueError('recording_members_differ_from_logical_inventory')
    inventory = {item['content_ref']: item for item in info['inventory']}
    frames = []
    for member in members:
        item = inventory[member]
        pin = item['files']['processed']
        path = matching._path(pin['path'], root).resolve()
        if not path.is_relative_to(processed_dir.resolve()):
            raise ValueError('recording_path_outside_processed_directory')
        if matching._hash(path) != pin['sha256']:
            raise ValueError('processed inventory hash mismatch')
        frame = pd.read_csv(path)
        frame['sample_source'] = [f'{member}:row={i+2}' for i in range(len(frame))]
        frames.append(frame)
    frame = pd.concat(frames, ignore_index=True)
    if segment.get('acquisition_start_local'):
        time = matching._times(frame.timestamp)
        frame = frame.loc[time.between(pd.Timestamp(segment['acquisition_start_local']),
                                      pd.Timestamp(segment['acquisition_end_local']))]
    return frame.reset_index(drop=True)


def _read_windows(path):
    if path is None:
        return {}
    config = json.loads(Path(path).read_text())
    if config.get('schema_version') != 1:
        raise ValueError('Unsupported pulse windows schema')
    result = {}
    for row in config['windows']:
        key = tuple(row[k] for k in ('trial_id', 'logical_recording_id', 'channel'))
        if key in result or key[2] not in matching.CHANNELS:
            raise ValueError('Duplicate or invalid pulse windows key')
        if row.get('review_status') not in ('checker_proposed', 'reviewed', 'blocked'):
            raise ValueError('Window decision requires an explicit review status')
        if not all(row.get(k) for k in ('evidence', 'reviewer', 'reviewed_on')):
            raise ValueError('Window decision requires evidence, reviewer and date')
        if row['review_status'] == 'reviewed' and row.get('user_signoff') is not True:
            raise ValueError('Reviewed windows require explicit user signoff')
        result[key] = row
    return result


def _choose_windows(frame, edge, channel, decisions):
    key = (edge['trial_id'], edge['logical_recording_id'], channel)
    decision = decisions.get(key)
    origin = frame.timestamp.iloc[0]
    if decision:
        if decision['review_status'] == 'blocked':
            return dict(issues=[decision.get('reason_code', 'reviewer_blocked')],
                        detail=decision.get('reason', 'Reviewer rejected this window')), 'blocked'
        windows = {k: [(pd.Timestamp(t)-origin).total_seconds() for t in decision[k]]
                   for k in ('pre', 'pulse', 'post')}
        if decision.get('pre_injection_pause'):
            windows['pre_injection_pause']=decision['pre_injection_pause']
        windows['issues'] = []
        _window_parts(frame, windows)
        return windows, decision['review_status']
    chronology = _decoded(edge, 'chronology_evidence', {})
    clock = chronology.get('release_clock')
    offset = chronology.get('release_offset_seconds')
    if offset is None and clock:
        release=pd.Timestamp(clock)
        if release.tzinfo is None and origin.tzinfo is None:
            offset=(release-origin).total_seconds()
        elif release.tzinfo is not None and origin.tzinfo is not None:
            offset=(release-origin).total_seconds()
        else:
            raise ValueError('release_recording_clock_basis_mismatch')
    # The notebook clock can be unresolved. It may select a pulse only when it
    # falls in this recording's local acquisition range; it is not a UTC fix.
    if offset is not None and not 0 <= offset <= frame.t_s.iloc[-1]:
        offset = None
    return propose_windows(frame, release_offset_s=offset), 'automatic'


def assign_roles(estimates):
    """Choose the primary channel from successful estimates, not candidates."""
    keys = {(r['trial_id'], r['logical_recording_id']) for r in estimates}
    for key in keys:
        rows = [r for r in estimates if (r['trial_id'], r['logical_recording_id']) == key
                and r['coefficient_source'] == 'trial_specific']
        primary = next((r for r in rows if r['conductivity_basis'] == 'specific'), rows[0] if rows else None)
        for row in rows:
            row['estimate_role'] = 'primary' if row is primary else 'comparison_channel'


def read_release_confirmations(path, trials):
    """Apply explicit field evidence to named releases without rewriting records."""
    if path is None:
        return {}
    data = json.loads(Path(path).read_text())
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported release confirmations schema')
    confirmations = {}
    for entry in data['releases']:
        tid = entry.get('trial_id')
        if tid not in trials or tid in confirmations:
            raise ValueError('Unknown or duplicate release confirmation')
        trial = trials[tid]
        if (entry.get('field_date') != matching._date(trial['field_date'])
                or entry.get('site_alias') != trial['site_alias']):
            raise ValueError('Release confirmation date/site differs from source trial')
        quantity = entry.get('delivered_salt_mass_g')
        if isinstance(quantity, bool) or quantity is None or not math.isfinite(float(quantity)) or float(quantity) <= 0:
            raise ValueError('Confirmed delivered mass must be finite and positive')
        if (entry.get('status') != 'confirmed_delivered'
                or not all(entry.get(k) for k in ('evidence', 'confirmed_by', 'confirmed_on'))
                or not matching._date(entry['confirmed_on'])):
            raise ValueError('Delivery confirmation requires explicit status, date and evidence')
        confirmations[tid] = entry
    return confirmations


def plot_pulse(path, frame, windows, *, trial_id, channel, device, status, mass_confirmed=False,
               clock_label='Recorded field time',q_m3_s=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    with plt.rc_context({'font.size': 12}):
        fig, ax = plt.subplots(figsize=(12, 5), layout='constrained')
        for index, part in frame.groupby('segment'):
            ax.plot(part.timestamp, part.ec, color='#0072B2', lw=1.5,
                    label='Recorded conductivity' if index == 0 else None)
        if not windows.get('issues'):
            pre, pulse, post = _window_parts(frame, windows)
            background = _background(pulse.t_s.to_numpy(), pre, post, 'linear')
            ax.plot(pulse.timestamp, background, color='#333333', ls='--', label='Interpolated background')
            ax.fill_between(pulse.timestamp, background, pulse.ec.to_numpy(), color='#0072B2', alpha=.18, label='Signed pulse area')
            for part in (pre, post):
                ax.axvspan(part.timestamp.iloc[0], part.timestamp.iloc[-1], color='#999999', alpha=.2)
            ax.axvline(pulse.timestamp.iloc[int(np.argmax(pulse.ec.to_numpy()-background))], color='#777777', ls=':', label='Pulse peak')
        value=f'Q = {q_m3_s:.3f} m³/s · ' if q_m3_s is not None else 'Q unavailable · '
        ax.set(title=f'{trial_id} · {channel} conductivity\n{value}{status}',
               ylabel='Conductivity (µS/cm)', xlabel=clock_label)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.grid(axis='y', alpha=.2); ax.legend(fontsize=10, frameon=False)
        mass_note = 'Delivery confirmed by field participant.' if mass_confirmed else 'Delivered mass unverified.'
        fig.supxlabel('Source: native Aqua TROLL recording through the saved pairing bundle. Gray: background windows. '+mass_note, fontsize=10)
        fig.savefig(path, dpi=150); plt.close(fig)


def plot_discharge(path, estimates):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    primaries = [r for r in estimates if r['estimate_role'] == 'primary']
    with plt.rc_context({'font.size': 12}):
        fig, ax = plt.subplots(figsize=(12, 5.5), layout='constrained')
        labels = []; seen = set()
        for i, row in enumerate(primaries):
            labels.append(row['trial_id'].replace('NISQ-', ''))
            label = f"{row['conductivity_basis'].title()} · trial-specific K (primary)"
            spread=row.get('indicative_sensitivity_relative')
            ax.errorbar(i, row['q_l_s'], yerr=row['q_l_s']*spread if spread is not None else None,
                        fmt='o', color='#0072B2', mfc='white', mec='#0072B2', ecolor='#777777', capsize=3,
                        label=label if label not in seen else None)
            seen.add(label)
            companions = [r for r in estimates if r['trial_id'] == row['trial_id']
                          and r['logical_recording_id'] == row['logical_recording_id'] and r['estimate_role'] != 'primary']
            for j, other in enumerate(companions):
                reference = other['coefficient_source'] != 'trial_specific'
                label = f"{other['conductivity_basis'].title()} · {'reference K' if reference else 'trial-specific K'} (comparison)"
                ax.scatter(i+.17+.08*j, other['q_l_s'], marker='D' if reference else 'x', color='#555555',
                           label=label if label not in seen else None)
                seen.add(label)
        ax.set_xticks(range(len(labels)), labels, rotation=40, ha='right')
        mass_note = ('Delivery confirmed by field participant' if primaries and all(r.get('mass_basis')=='user_confirmed_delivered' for r in primaries)
                     else 'Some delivered masses unverified')
        ax.set(ylabel='Proposed discharge Q (L/s)', xlabel='Release (YYYYMMDD–trial)',
               title=f'{len(primaries)} recording estimates use trial-specific calibration\n{mass_note}; window review pending')
        ax.grid(axis='y', alpha=.2)
        if primaries: ax.legend(fontsize=10, frameon=False)
        fig.supxlabel('Source: curated release records and saved Aqua TROLL/calibration pairings. Bars are sensitivity RSS, not confidence intervals; mass error excluded.', fontsize=10)
        fig.savefig(path, dpi=150); plt.close(fig)


def run_mass_slug(records_dir, processed_dir, pairing_dir, calibration_dir, output_dir, *,
                  reuse_dir=None, windows_path=None, confirmations_path=None, site='NISQ', root=ROOT,
                  include_relative=False, allow_reported_volume=False):
    """Calculate proposals without changing a source, pairing or previous run."""
    records_dir, processed_dir, pairing_dir, calibration_dir, root = [Path(p).resolve()
        for p in (records_dir, processed_dir, pairing_dir, calibration_dir, root)]
    output = Path(output_dir).resolve()
    for source in (records_dir, processed_dir, pairing_dir, calibration_dir):
        if output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError('Output must be separate from input directories')
    pair, pins = reuse.verify_bundle(pairing_dir, root)
    cal_info, calpins = reuse.verify_bundle(calibration_dir, root); pins.update(calpins)
    reference_domains = []
    if reuse_dir:
        _, reusepins = reuse.verify_bundle(reuse_dir, root); pins.update(reusepins)
        reference_domains = matching._read_table(Path(reuse_dir)/'reuse_evaluation.csv', ['outcome'])
    if windows_path:
        pins[str(Path(windows_path).resolve())] = matching._hash(windows_path)
    reuse.pin_record_tables(records_dir, cal_info, pins, root)
    trials = {r['trial_id']: r for r in calibration._read_csv(records_dir/'trials.csv')}
    if confirmations_path is None:
        default = root/'salt_dilution/config/release_confirmations.json'
        confirmations_path = default if default.is_file() else None
    if confirmations_path:
        pins[str(Path(confirmations_path).resolve())] = matching._hash(confirmations_path)
    confirmations = read_release_confirmations(confirmations_path, trials)
    summaries = matching._read_table(pairing_dir/'pairing_summary.csv', ['trial_id', 'status'])
    if len(summaries) != len(trials) or {r['trial_id'] for r in summaries} != set(trials):
        raise ValueError('Pairing summary must account for each release exactly once')
    recordings = {r['recording_edge_id']: r for r in matching._read_table(pairing_dir/'recording_candidates.csv', ['recording_edge_id'])}
    edges = {r['calibration_edge_id']: r for r in matching._read_table(pairing_dir/'calibration_candidates.csv', ['calibration_edge_id'])}
    fits = {(r['calibration_id'], r.get('probe_alias', ''), r['conductivity_basis']): r
            for r in calibration._read_csv(calibration_dir/'calibration_fits.csv')}
    audit=[]
    for selected_site in sorted({t['site_alias'] for t in trials.values()} if site is None else {site}):
        rows, _ = reuse.audit_calibrations(records_dir, calibration_dir, pairing_dir, site=selected_site)
        audit.extend(r for r in rows if r['site_alias']==selected_site)
    audited = {(r['calibration_id'], r['alias_label'], r['conductivity_basis']): r for r in audit}
    provenance = json.loads((records_dir/'provenance.json').read_text())
    decisions = _read_windows(windows_path)
    valid_keys = {(e['trial_id'], recordings[e['recording_edge_id']]['logical_recording_id'], e['conductivity_basis'])
                  for s in summaries for eid in _decoded(s, 'selected_calibration_edge_ids', []) for e in [edges[eid]]}
    for key, decision in decisions.items():
        if key not in valid_keys:
            raise ValueError('Window decision does not refer to a selected recording/channel')
        reference = decision.get('pairing_reference')
        if reference:
            if reference.get('run_info_sha256') != matching._hash(pairing_dir/'run_info.json'):
                raise ValueError('Window decision refers to a different pairing run')
            candidate = edges[reference['calibration_edge_id']]
            if (candidate['recording_edge_id'] != reference['recording_edge_id']
                or (candidate['trial_id'], recordings[candidate['recording_edge_id']]['logical_recording_id'], candidate['conductivity_basis']) != key):
                raise ValueError('Window decision pairing reference differs from selected edge')
            for item in reference.get('processed_sources', []):
                path = matching._path(item['path'], root).resolve()
                if pins.get(str(path)) != item['sha256']:
                    raise ValueError('Window source hash is not pinned by the pairing run')
    estimates, outcomes, proposals, attempts = [], [], [], []
    with reuse.staged_run(output_dir, pins, [__file__, reuse.__file__, calibration.__file__, calibration_quality.__file__, matching.__file__]) as (stage, pins):
        pulse_dir = stage/'figures/pulses'; pulse_dir.mkdir(parents=True)
        for summary in summaries:
            tid = summary['trial_id']; trial = trials[tid]; reasons = []; start_count = len(estimates)
            category = ''
            if site is not None and trial['site_alias'] != site: category = 'out_of_scope_site'
            elif summary['status'] == 'excluded_practice': category = 'excluded_practice'
            elif summary['status'] == 'partial': category = 'partial_missing_calibration'
            elif summary['status'] == 'conflicting': category = 'conflicting_identity'
            elif summary['status'] != 'inferred_proposal': category = 'blocked_pairing_unresolved'
            selected_edges = [edges[e] for e in _decoded(summary, 'selected_calibration_edge_ids', [])]
            selected_recordings = _decoded(summary, 'selected_recording_edge_ids', [])
            for edge in selected_edges:
                if edge['trial_id'] != tid or edge['recording_edge_id'] not in selected_recordings:
                    raise ValueError('Selected calibration edge has a different release or recording')
                _selected_fit(edge, fits, calibration_dir)
            if any(recordings[rid]['trial_id'] != tid for rid in selected_recordings):
                raise ValueError('Selected recording edge has a different release')
            if include_relative and category=='conflicting_identity' and any(e.get('status')=='supported' for e in selected_edges):
                category=''
            if not category:
                if any(audited[tuple(_decoded(e, 'fit_reference', {})['key'])]['compat_class'] == 'method_conflict_isolated' for e in selected_edges):
                    category = 'method_conflict_isolated'
                elif not include_relative and not any(e.get('mass_route_eligible', '').lower() == 'true' for e in selected_edges):
                    category = 'relative_basis_not_mass_route'
            if not category:
                for rid in _decoded(summary, 'selected_recording_edge_ids', []):
                    edge_recording = recordings[rid]
                    candidates = [e for e in selected_edges if e['recording_edge_id'] == rid
                                  and (include_relative or e.get('mass_route_eligible', '').lower() == 'true')]
                    for edge in candidates:
                        basis = edge['conductivity_basis']; logical_id = edge_recording['logical_recording_id']
                        fit = fits[tuple(_decoded(edge, 'fit_reference', {})['key'])]
                        compatible = audited[(fit['calibration_id'], fit.get('probe_alias', ''), basis)]
                        attempt = dict(trial_id=tid, logical_recording_id=logical_id, channel=basis,
                                       recording_edge_id=rid, calibration_edge_id=edge['calibration_edge_id'], outcome='')
                        attempts.append(attempt)
                        frame = None; windows = dict(issues=[])
                        try:
                            relative=include_relative and fit.get('calibration_basis')=='relative_concentration'
                            method='solution_slug' if relative else 'mass_slug'
                            allowed=('relative_only',) if relative else ('mass_library_eligible','mass_trial_only')
                            if compatible['compat_class'] not in allowed:
                                raise ValueError('calibration_not_mass_compatible')
                            required_unit='(mL/mL) / (uS/cm)' if relative else '(mg/L) / (uS/cm)'
                            if fit['coefficient_unit']!=required_unit:raise ValueError('coefficient_unit_method_mismatch')
                            serial = edge_recording.get('device_serial', '')
                            cal_serial = edge.get('calibration_device_serial', '') or compatible['sensor_serial']
                            if compatible['sensor_serial'] and cal_serial != compatible['sensor_serial']:
                                raise ValueError('edge_calibration_identity_disagrees_with_native_audit')
                            if serial and cal_serial and serial != cal_serial:
                                raise ValueError('no_compatible_coefficient_for_sensor')
                            samples = _recording_samples(edge_recording, pair, processed_dir, root)
                            frame, flags = prepare_series(samples, basis)
                            windows, window_status = _choose_windows(frame, edge_recording, basis, decisions)
                            if windows.get('issues'): raise ValueError(';'.join(windows['issues']))
                            area = integrate_excess(frame, windows)
                            confirmation = confirmations.get(tid, {})
                            mass = '' if relative else float(confirmation.get('delivered_salt_mass_g', trial.get('salt_mass_g') or 'nan'))
                            volume,volume_basis=solution_quantity(trial,provenance['trials'].get(tid,{}),
                                allow_reported=allow_reported_volume) if relative else ('','')
                            quantity=volume if relative else mass
                            q = (solution_discharge if relative else discharge)(quantity, fit['k'], area['integral_us_cm_s'])
                            basis_source = provenance['trials'].get(tid, {}).get('quantity_basis', {}).get('salt_mass_g', 'unknown')
                            mass_basis = '' if relative else ('user_confirmed_delivered' if confirmation else ('operational_unverified' if basis_source == 'unknown' else basis_source))
                            if relative and volume_basis=='reported_delivery_assumed':flags.append('reported_equals_delivered_solution_assumed')
                            if not relative and not confirmation: flags.append('nominal_equals_delivered_mass_assumed')
                            flags += ['mixing_not_independently_validated',
                                      'compensation_settings_unrecovered', 'window_user_signoff_pending']
                            if edge.get('identity_status') not in ('native_match', 'source_protocol_match'): flags.append('identity_unverified')
                            if summary.get('event_alignment_review_required', '').lower() == 'true': flags.append('event_alignment_unverified')
                            if basis == 'actual': flags.append('temperature_comparability_unverified')
                            variant_conflict=str(fit.get('incompatible_notebook_version','')).lower()=='true'
                            if variant_conflict:flags.append('calibration_source_variant_unreconciled')
                            pulse_ec = frame.loc[frame.t_s.between(*windows['pulse']), 'ec']
                            if float(pulse_ec.min()) < float(fit['ec_min']) or float(pulse_ec.max()) > float(fit['ec_max']):
                                flags.append('conductivity_extrapolates_calibration_range')
                            reference_fields=calibration_reference_fields(fit)
                            flags += reference_fields['calibration_reference_flags']
                            row = dict(trial_id=tid, field_date=matching._date(trial['field_date']), logical_recording_id=logical_id,
                                recording_edge_id=rid, member_refs=_decoded(edge_recording, 'member_refs', []), sensor_serial=serial,
                                identity_status=edge.get('identity_status', ''), conductivity_basis=basis,
                                coefficient_source='trial_specific', calibration_id=fit['calibration_id'], fit_reference=_decoded(edge, 'fit_reference', {}),
                                k=fit['k'], k_se=compatible['k_se'], coefficient_unit=fit['coefficient_unit'],
                                discharge_method=method,injection_solution_volume_ml=volume,solution_volume_basis=volume_basis,
                                mass_g=mass, mass_basis=mass_basis, mass_source_basis=basis_source,
                                mass_confirmation=confirmation, nominal_equals_delivered_mass_assumed=not relative and not bool(confirmation),
                                windows={key: windows[key] for key in ('pre', 'pulse', 'post','pre_injection_pause') if key in windows}, recording_origin_local=str(frame.timestamp.iloc[0]),
                                window_status=window_status, background_mode='linear', **area,
                                integral_mg_s_l='' if relative else float(fit['k'])*area['integral_us_cm_s'],
                                integral_relative_s=float(fit['k'])*area['integral_us_cm_s'] if relative else '', **q,
                                **uncertainty(frame, windows, quantity, fit['k'], compatible['k_se'],method=method), flags=sorted(set(flags)),
                                calibration_source_variant=fit.get('source_variant','curated_notebook'), **reference_fields,
                                estimate_support='conditional_calibration_variant' if variant_conflict else ('conditional_reported_volume' if volume_basis=='reported_delivery_assumed' else 'proposed_observed_pulse'),
                                q_status='proposed', estimate_role='primary' if basis == 'specific' or not any(c['conductivity_basis']=='specific' for c in candidates) else 'comparison_channel',
                                scientifically_accepted=False)
                            estimates.append(row); attempt['outcome'] = 'computed'
                            # Reference coefficients remain comparisons, and only within
                            # a passed, identical sensor/channel/procedure/date domain.
                            for domain in reference_domains:
                                if (domain['outcome'] == 'pass' and domain['sensor_serial'] == serial
                                    and domain['conductivity_basis'] == basis and domain['site_alias'] == site
                                    and domain['procedure_id'] == compatible['procedure_id']
                                    and domain['water_source'] == compatible['stock_water_source']
                                    and domain['date_start'] <= row['field_date'] <= domain['date_end']
                                    and fit['calibration_id'] in json.loads(domain['session_ids'])):
                                    other = dict(row, coefficient_source='reference_comparison', k=domain['k_reference'], k_se='',
                                        estimate_role='comparison_reference', **discharge(mass, domain['k_reference'], area['integral_us_cm_s']))
                                    other.update(calibration_reference_fields(dict(fit,k=domain['k_reference'])))
                                    other['flags']=sorted((set(row['flags'])-set(row['calibration_reference_flags']))
                                                          |set(other['calibration_reference_flags']))
                                    other['integral_mg_s_l'] = float(domain['k_reference'])*area['integral_us_cm_s']
                                    other['u_k_fit_relative'] = ''; other['indicative_sensitivity_relative'] = ''
                                    other['indicative_q_lower_l_s'] = ''; other['indicative_q_upper_l_s'] = ''
                                    other['uncertainty_scope'] = 'Reference application log SD reported separately; no total Q interval.'
                                    other['reference_application_log_sd'] = domain['application_log_sd']
                                    estimates.append(other)
                        except (ValueError, KeyError) as error:
                            attempt['outcome'] = 'blocked'; attempt['reason'] = str(error); reasons.append(str(error))
                            if windows.get('detail'): attempt['detail'] = windows['detail']
                            windows = dict(issues=[str(error)])
                        proposal = dict(trial_id=tid, logical_recording_id=logical_id, channel=basis,
                                        issues=windows.get('issues', []), decision='computed_proposal' if attempt['outcome']=='computed' else 'blocked')
                        if frame is not None:
                            if windows.get('pre_injection_pause'):
                                proposal['pre_injection_pause']=windows['pre_injection_pause']
                            proposal.update({key: [(frame.timestamp.iloc[0]+pd.to_timedelta(v, unit='s')).isoformat(' ') for v in windows[key]]
                                             for key in ('pre', 'pulse', 'post') if key in windows})
                            plot_pulse(pulse_dir/f'{tid}_{logical_id.replace(":", "-")}_{basis}.png', frame, windows,
                                       trial_id=tid, channel=basis, device=edge_recording.get('device_serial', ''),
                                       status='Proposed windows · delivery confirmed' if attempt['outcome']=='computed' and tid in confirmations else
                                              ('Proposed windows · nominal mass' if attempt['outcome']=='computed' else 'Blocked: '+attempt.get('reason', '')),
                                       mass_confirmed=tid in confirmations,
                                       clock_label='Field time (PST, UTC−08:00)' if _decoded(edge_recording,'time_evidence',{}).get('effective_offset_seconds')==-28800 else 'Recorded field time',
                                       q_m3_s=q['q_m3_s'] if attempt['outcome']=='computed' else None)
                        proposals.append(proposal)
                category = 'computed' if len(estimates)>start_count else 'blocked_'+(reasons[0].split(';')[0] if reasons else 'no_compatible_coefficient_for_sensor')
            outcomes.append(dict(trial_id=tid, pairing_status=summary['status'], category=category,
                                 estimate_count=len(estimates)-start_count, reasons=sorted(set(reasons or ([category] if category!='computed' else []))),
                                 mass_confirmation_status='confirmed_delivered' if tid in confirmations else 'unconfirmed',
                                 confirmed_delivered_mass_g=confirmations[tid]['delivered_salt_mass_g'] if tid in confirmations else '',
                                 scientifically_accepted=False))
        assign_roles(estimates)
        _table(stage/'discharge_estimates.csv', estimates, ['trial_id', 'q_l_s'])
        _table(stage/'release_summary.csv', outcomes, ['trial_id', 'category'])
        _table(stage/'recording_outcomes.csv', attempts, ['trial_id', 'outcome'])
        (stage/'pulse_windows_proposed.json').write_text(matching._json(dict(schema_version=1, windows=proposals))+'\n')
        if windows_path: (stage/'pulse_windows_used.json').write_bytes(Path(windows_path).read_bytes())
        if confirmations_path: (stage/'release_confirmations_used.json').write_bytes(Path(confirmations_path).read_bytes())
        plot_discharge(stage/'figures/discharge_comparison.png', estimates)
        info = reuse.write_run_info(stage, pins, scope=f'{site} mass-slug proposals only; no staff acceptance.',
            release_count=len(outcomes), category_counts=dict(Counter(r['category'] for r in outcomes)),
            estimate_count=len(estimates), q_status_counts=dict(Counter(r['q_status'] for r in estimates)),
            reference_comparison_count=sum(r['coefficient_source']!='trial_specific' for r in estimates),
            confirmed_delivery_release_ids=sorted(confirmations), confirmed_delivery_release_count=len(confirmations),
            reference_policy='Only passed observed domains; trial-specific K remains primary.',
            gap_policy='No bridging or filling; missing cells in used windows block integration.',
            formula='Q_L_s = mass_g * 1000 / (K_mass * integral); solution Q_L_s = volume_ml / 1000 / (K_relative * integral)',
            include_relative=include_relative,allow_reported_volume=allow_reported_volume,
            limitations=['unconfirmed_masses_remain_unverified','calibration_and_clock_assumptions','mixing_unvalidated','indicative_sensitivity_not_total_uncertainty'])
    return info


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, default=ROOT/'salt_dilution/data/records')
    parser.add_argument('--processed', type=Path, default=ROOT/'salt_dilution/data/processed')
    parser.add_argument('--pairing', type=Path, default=reuse.DEFAULT_PAIRING)
    parser.add_argument('--calibrations', type=Path, default=reuse.DEFAULT_CALIBRATIONS)
    parser.add_argument('--reuse', type=Path)
    parser.add_argument('--windows', type=Path)
    parser.add_argument('--confirmations', type=Path, help='Explicit per-release delivered-mass confirmations; defaults to config/release_confirmations.json when present.')
    parser.add_argument('--include-relative',action='store_true',help='Also calculate the historical original-solution-volume route.')
    parser.add_argument('--allow-reported-volume',action='store_true',help='Permit matching source-reported solution volumes, with conditional-delivery flags.')
    parser.add_argument('--all-sites',action='store_true',help='Assess every recorded site separately.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        info = run_mass_slug(args.records, args.processed, args.pairing, args.calibrations, args.output,
                             reuse_dir=args.reuse, windows_path=args.windows, confirmations_path=args.confirmations,
                             include_relative=args.include_relative,allow_reported_volume=args.allow_reported_volume,
                             site=None if args.all_sites else 'NISQ')
    except (ValueError, OSError) as error:
        parser.exit(2, str(error)+'\n')
    print(matching._json(dict(categories=info['category_counts'], estimates=info['estimate_count'], output=str(args.output))))
    return 0


if __name__ == '__main__': raise SystemExit(main())
