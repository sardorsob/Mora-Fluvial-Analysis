"""Audit saved calibration series and test conditional reuse within observed domains."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
from importlib.metadata import version
import numpy as np
from scipy import stats
from . import calibration, matching

ROOT = matching.ROOT
DEFAULT_CALIBRATIONS = ROOT/'salt_dilution/results/calibrations/2026-10-26_probe_review'
DEFAULT_PAIRING = ROOT/'salt_dilution/results/matching/2026-11-01_reviewed_pairings'


def verify_bundle(directory, root=ROOT):
    """Verify historical bytes without requiring the old code to be current."""
    directory, root = Path(directory).resolve(), Path(root).resolve()
    info = json.loads((directory/'run_info.json').read_text())
    pins = {str(directory/'run_info.json'): matching._hash(directory/'run_info.json')}
    for group, base in (('inputs', root), ('outputs', directory)):
        for item in info[group]:
            path = matching._path(item['path'], base).resolve()
            if not path.is_file() or matching._hash(path) != item['sha256']:
                raise ValueError(f'Stale or missing {group} hash: {path}')
            pins[str(path)] = item['sha256']
    return info, pins


def pin_record_tables(records_dir, calibration_info, pins, root=ROOT):
    """Alternate locations are allowed only for the same saved source bytes."""
    preparations = [matching._path(item['path'], root).resolve() for item in calibration_info['inputs']
                    if Path(item['path']).name == 'calibrations.csv']
    if len(preparations) != 1:
        raise ValueError('Calibration bundle must identify one source preparation table')
    anchor = preparations[0].parent
    for name in ('trials.csv', 'calibrations.csv', 'calibration_points.csv', 'trial_inputs.csv', 'provenance.json'):
        path = (Path(records_dir)/name).resolve()
        expected = pins.get(str(anchor/name))
        if expected is None or matching._hash(path) != expected:
            raise ValueError(f'Records differ from bundle-pinned source: {name}')
        pins[str(path)] = expected


@contextmanager
def staged_run(output, pins, code_paths):
    """Publish a complete new bundle only after its source hashes still match."""
    output = Path(output)
    if output.is_symlink() or output.exists():
        raise FileExistsError(f'Refusing existing output: {output}')
    output = output.resolve()
    for name in pins:
        source=Path(name).resolve()
        if source==output or source.is_relative_to(output):
            raise ValueError('Output overlaps an input')
    pins = dict(pins)
    pins.update({str(Path(p).resolve()): matching._hash(p) for p in code_paths})
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.analysis-', dir=output.parent))
    try:
        yield stage, pins
        for name,digest in pins.items():
            if not Path(name).is_file() or matching._hash(name)!=digest:
                raise ValueError(f'Input changed during analysis: {name}')
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def write_run_info(stage, pins, **details):
    git = subprocess.run(['git','rev-parse','HEAD'], cwd=ROOT, capture_output=True, text=True)
    dirty = subprocess.run(['git','status','--porcelain'], cwd=ROOT, capture_output=True, text=True)
    info = dict(schema_version=1, created_at_utc=datetime.now(timezone.utc).isoformat(),
                git_commit=git.stdout.strip(), working_tree_dirty=bool(dirty.stdout.strip()),
                scientific_acceptance=False, numpy_version=np.__version__, python_version=sys.version,
                scipy_version=version('scipy'), pandas_version=version('pandas'), matplotlib_version=version('matplotlib'),
                inputs=[dict(path=matching._ref(p,ROOT),sha256=h) for p,h in sorted(pins.items())],
                outputs=[dict(path=p.relative_to(stage).as_posix(),sha256=matching._hash(p))
                         for p in sorted(stage.rglob('*')) if p.is_file()], **details)
    (stage/'run_info.json').write_text(matching._json(info)+'\n')
    return info


def classify_fit(fit, prep, evidence, device, *, site='NISQ'):
    if site is not None and prep['site_alias']!=site:
        return 'out_of_scope_site', ['site_excluded']
    status=evidence.get('source_table_status',evidence.get('source_record',{}).get('source_table_status',''))
    if status in ('abandoned','crossed_out'):
        return 'abandoned_or_supporting', [status]
    if not fit.get('k'):
        return 'not_fitted', [fit.get('reason','no_saved_fit')]
    source_method=evidence.get('source_record',{}).get('method_family','')
    if fit.get('calibration_basis')=='relative_concentration':
        if (fit.get('concentration_unit') != 'mL/mL' or fit.get('coefficient_unit') != '(mL/mL) / (uS/cm)'
                or not math.isfinite(float(fit['k'])) or float(fit['k']) <= 0):
            return 'not_fitted', ['invalid_relative_coefficient_or_units']
        if source_method == 'mass_stock':
            return 'method_conflict_isolated', ['source_mass_stock_but_saved_relative_fit']
        return 'relative_only', ['relative_injectate_not_mass_concentration']
    if (fit.get('calibration_basis')!='mass_concentration' or fit.get('concentration_unit')!='mg/L'
            or fit.get('coefficient_unit')!='(mg/L) / (uS/cm)' or not math.isfinite(float(fit['k'])) or float(fit['k'])<=0):
        return 'not_fitted', ['invalid_mass_coefficient_or_units']
    required=('stock_salt_mass_g','calibration_water_initial_ml')
    volume=prep.get('stock_solution_final_ml') or prep.get('stock_water_initial_ml')
    if not (volume or prep.get('stock_solution_concentration_mg_ml')) or any(not prep.get(k) for k in required):
        return 'not_fitted', ['recipe_incomplete']
    if prep.get('incompatible_notebook_version'):
        return 'mass_trial_only', ['alternate_worksheet_calibration_source_version']
    if device.get('status')=='verified' and device.get('device_serial') and status=='recorded':
        return 'mass_library_eligible', []
    return 'mass_trial_only', ['calibration_identity_or_disposition_unverified']


def slope_se(x, residuals):
    x, residuals = np.asarray(x,dtype=float), np.asarray(residuals,dtype=float)
    if len(x)<3 or len(x)!=len(residuals) or not np.isfinite(x).all() or not np.isfinite(residuals).all():
        raise ValueError('At least three finite fitted pairs are required')
    sxx=float(np.sum((x-x.mean())**2))
    if sxx<=0:
        raise ValueError('Conductivity has no variation')
    return float(np.sqrt(np.sum(residuals**2)/(len(x)-2)/sxx))


def point_selection_diagnostics(points, k):
    """Describe sensitivity to complete dose steps without selecting a new fit."""
    used = [p for p in points if str(p['used_in_fit']).lower() == 'true']
    x = np.array([float(p['conductivity_us_cm']) for p in used])
    y = np.array([float(p['concentration']) for p in used])
    residuals = np.array([float(p['residual']) for p in used])
    slopes = {}
    if len(x) >= 4:
        for i, point in enumerate(used):
            keep = np.arange(len(x)) != i
            if np.ptp(x[keep]) > 0:
                slopes[point['step_no']] = float(stats.linregress(x[keep], y[keep]).slope)
    quadratic_reduction = None
    sse = float(np.dot(residuals, residuals))
    if len(x) >= 5 and len(set(x)) >= 3 and sse > np.finfo(float).eps * np.dot(y, y):
        scaled = (x - x.mean()) / np.ptp(x)
        quadratic = np.polynomial.Polynomial.fit(scaled, y, 2)(scaled)
        quadratic_reduction = float(np.clip(1 - np.sum((y - quadratic) ** 2) / sse, 0, 1))
    return dict(point_selection_rule='all_usable_dose_steps' if used else '',
                used_dose_steps=[p['step_no'] for p in used],
                excluded_dose_steps={p['step_no']: p['exclusion_reason'] for p in points
                                     if str(p['used_in_fit']).lower() != 'true'},
                calibration_ec_span_us_cm=float(np.ptp(x)) if used else None,
                dose_residuals={p['step_no']: float(p['residual']) for p in used},
                leave_one_dose_k=slopes,
                max_abs_leave_one_dose_k_relative_effect=max((abs(v / k - 1) for v in slopes.values()), default=None),
                quadratic_sse_reduction_fraction=quadratic_reduction)


def method_candidate(prep, points, saved):
    direct=dict(prep,procedure_id='mass_stock_river')
    fitted,_=calibration.fit_calibration(direct,points,conductivity_basis=saved['conductivity_basis'])
    old,_=calibration.fit_calibration(prep,points,conductivity_basis=saved['conductivity_basis'])
    expected=float(saved['k'])*fitted['stock_concentration']/old['stock_concentration']
    if not np.isclose(fitted['k'],expected,rtol=1e-12,atol=0):
        raise ValueError('Candidate refit does not equal the independently specified stock-ratio conversion')
    return dict(calibration_id=prep['calibration_id'],conductivity_basis=saved['conductivity_basis'],
                k_saved_relative=saved['k'],k_candidate_direct_mass=fitted['k'],
                candidate_label='unresolved_method_candidate_not_for_use',coefficient_unit='(mg/L) / (uS/cm)')


def audit_calibrations(records_dir, calibration_dir, pairing_dir, *, site='NISQ'):
    read=calibration._read_csv
    preparations=read(Path(records_dir)/'calibrations.csv')
    calibration_run = Path(calibration_dir) / 'run_info.json'
    inputs = json.loads(calibration_run.read_text()).get('inputs', []) if calibration_run.is_file() else []
    recovery_paths = {}
    for pin in inputs:
        name = Path(pin['path']).name
        if name in (calibration.RECOVERY.name, calibration.RECIPE_RECOVERY.name):
            path = matching._path(pin['path'], ROOT)
            if matching._hash(path) != pin['sha256']:
                raise ValueError(f'Stale calibration recovery pin: {path}')
            recovery_paths[name] = path
    source, _ = calibration.read_calibration_points(records_dir, recovery_path=recovery_paths.get(calibration.RECOVERY.name))
    provenance=json.loads((Path(records_dir)/'provenance.json').read_text())
    preparations, source, _, _ = calibration.apply_recipe_recovery(
        preparations, source, provenance, recovery_paths.get(calibration.RECIPE_RECOVERY.name))
    preps = {p['calibration_id']: p for p in preparations}
    bundle=json.loads((Path(pairing_dir)/'run_info.json').read_text())
    derived=read(Path(calibration_dir)/'calibration_points.csv')
    series=read(Path(calibration_dir)/'calibration_fits.csv')+read(Path(calibration_dir)/'calibration_skips.csv')
    rows,candidates=[],[]
    for fit in series:
        cid,basis=fit['calibration_id'],fit['conductivity_basis']
        prep,evidence=preps[cid],provenance['calibrations'].get(cid,{})
        device=bundle.get('calibration_device_checks',{}).get(cid,{})
        kind,reasons=classify_fit(fit,prep,evidence,device,site=site)
        dose_points=[p for p in derived if p['calibration_id']==cid and p['conductivity_basis']==basis
                     and p['probe_alias']==fit.get('probe_alias','')]
        used=[p for p in dose_points if p['used_in_fit'].lower()=='true']
        measured=[p for p in source if p['calibration_id']==cid and p.get('probe_alias','')==fit.get('probe_alias','')]
        temperature_by_step = {p['step_no']: p.get('temperature_c') for p in measured if p.get('step_no')}
        diagnostic_points = dose_points if all(
            p.get('step_no') and (str(p['used_in_fit']).lower() != 'true' or p.get('concentration') not in (None, ''))
            for p in dose_points) else []
        identity = 'unverified'
        if device.get('status') == 'verified':
            identity = ('native_match' if device.get('basis') in ('electronic_sequence', 'recovered_native_calibration_sequence')
                        else 'source_protocol_match')
        rows.append(dict(calibration_id=cid,site_alias=prep['site_alias'],field_date=matching._date(prep['field_date']),
            conductivity_basis=basis,calibration_basis=fit.get('calibration_basis',''),coefficient_unit=fit.get('coefficient_unit',''),
            k=fit.get('k',''),k_se=slope_se([p['conductivity_us_cm'] for p in used],[p['residual'] for p in used]) if used else '',
            n_points=len(used),ec_min=fit.get('ec_min',''),ec_max=fit.get('ec_max',''),procedure_id=prep['procedure_id'],
            source_method_family=evidence.get('source_record',{}).get('method_family',''),
            recipe={k:prep.get(k,'') for k in ('stock_salt_mass_g','stock_water_initial_ml','stock_solution_final_ml',
                                             'stock_solution_concentration_mg_ml','calibration_water_initial_ml','stock_water_source')},
            recipe_source_reference=prep.get('recipe_source_reference',''),
            source_variant=prep.get('source_variant','curated_notebook'),
            incompatible_notebook_version=prep.get('incompatible_notebook_version',False),
            recipe_qualification=prep.get('recipe_qualification',''),
            stock_water_source=prep.get('stock_water_source',''),stock_lineage=evidence.get('stock_stages',[]) or 'unknown',
            sensor_serial=device.get('device_serial',''),identity_status=identity,alias_label=fit.get('probe_alias',''),
            temperature_available=bool(used) and all(
                p.get('temperature_c') or temperature_by_step.get(p.get('step_no')) for p in used),
            reuse_conditions_confirmed=False,
            receiver_background_ec=float(used[0]['conductivity_us_cm']) if used else '',
            disposition=evidence.get('source_table_status',''),compat_class=kind,reasons=reasons,
            **point_selection_diagnostics(diagnostic_points, float(fit['k']) if fit.get('k') else None)))
        if kind=='method_conflict_isolated':
            try:candidates.append(method_candidate(prep,measured,fit))
            except ValueError as error:candidates.append(dict(calibration_id=cid,conductivity_basis=basis,candidate_label='unresolved_method_candidate_not_for_use',reason=str(error)))
    return rows,candidates


def evaluate_reuse(rows, *, tolerance=.05):
    if not 0<tolerance<1:
        raise ValueError('Tolerance must be between zero and one')
    groups=defaultdict(list)
    for row in rows:
        if row['compat_class']=='mass_library_eligible':
            groups[(row['sensor_serial'],row['conductivity_basis'],row['site_alias'],row['procedure_id'],row['stock_water_source'])].append(row)
    results=[]
    for key,group in sorted(groups.items()):
        group=sorted(group,key=lambda r:(r['field_date'],r['calibration_id']))
        y=np.log([float(r['k']) for r in group]);days=sorted({r['field_date'] for r in group})
        daily=np.array([np.mean([v for v,r in zip(y,group) if r['field_date']==day]) for day in days])
        n,d=len(y),len(days);m=float(daily.mean());sd=float(y.std(ddof=1)) if n>1 else 0
        ds=float(daily.std(ddof=1)) if d>1 else 0
        t_day=float(stats.t.ppf(.975,d-1)) if d>1 else 0
        t_session=float(stats.t.ppf(.975,n-1)) if n>1 else 0
        mean_margin=t_day*ds/np.sqrt(d) if d>1 else 0
        session_margin=t_session*sd*np.sqrt(1+1/n) if n>1 else 0
        day_margin=t_day*ds*np.sqrt(1+1/d) if d>1 else 0
        lodo=[];daily_effect=[]
        for day in days:
            others=[v for v,other in zip(daily,days) if other!=day]
            if not others:continue
            ref=float(np.mean(others));daily_effect.append(float(np.expm1(daily[days.index(day)]-ref)))
            lodo.extend(dict(calibration_id=r['calibration_id'],day=day,q_relative_effect=float(np.expm1(v-ref))) for v,r in zip(y,group) if r['field_date']==day)
        x=np.array([(np.datetime64(day)-np.datetime64(days[0]))/np.timedelta64(1,'D') for day in days],dtype=float)
        drift=drift_se=0.0
        if d>=3 and np.ptp(x)>0:
            coef=np.polyfit(x,daily,1);residual=daily-np.polyval(coef,x)
            drift=float(coef[0]*np.ptp(x));drift_se=float(np.sqrt(np.sum(residual**2)/(d-2)/np.sum((x-x.mean())**2))*np.ptp(x))
        drift_margin=float(stats.t.ppf(.975,d-2))*drift_se if d>=3 else 0
        drift_upper=math.expm1(abs(drift)+drift_margin)
        drift_lower=math.expm1(max(0,abs(drift)-drift_margin))
        background=np.array([np.mean([float(r['receiver_background_ec']) for r in group if r['field_date']==day]) for day in days])
        background_slope=None; background_r2=None
        if d>=3 and np.isfinite(background).all() and np.ptp(background)>0:
            background_slope=float(np.polyfit(background,daily,1)[0])
            if np.ptp(daily)>0:background_r2=float(np.corrcoef(background,daily)[0,1]**2)
        ec_low=[float(r['ec_min']) for r in group if r.get('ec_min') not in ('',None)]
        ec_high=[float(r['ec_max']) for r in group if r.get('ec_max') not in ('',None)]
        reasons=[];outcome='insufficient_evidence'
        coverage=n>=6 and d>=3
        if not coverage:reasons.append('too_few_independent_days_or_sessions')
        if key[1]=='actual':
            reasons.append('temperature_unavailable' if not all(r['temperature_available'] for r in group)
                           else 'temperature_model_not_implemented')
        if coverage and not reasons:
            # The session interval is diagnostic; only observed held-out day
            # changes or a day-level drift interval establish a failure here.
            if max(map(abs,daily_effect),default=0)>tolerance or drift_lower>tolerance:
                outcome='fail';reasons.append('observed_day_effect_or_drift_exceeds_tolerance')
            elif (max((abs(e['q_relative_effect']) for e in lodo),default=0)<=tolerance
                  and math.expm1(day_margin)<=tolerance and math.expm1(session_margin)<=tolerance
                  and drift_upper<=tolerance/2):
                if all(r.get('reuse_conditions_confirmed') is True for r in group):outcome='pass'
                else:reasons.append('stock_settings_or_independence_unverified')
            else:reasons.append('application_uncertainty_or_drift_not_bounded_within_tolerance')
        results.append(dict(sensor_serial=key[0],conductivity_basis=key[1],site_alias=key[2],procedure_id=key[3],water_source=key[4],
            date_start=days[0],date_end=days[-1],session_count=n,day_count=d,session_ids=[r['calibration_id'] for r in group],
            calibration_ec_min=min(ec_low) if ec_low else None,calibration_ec_max=max(ec_high) if ec_high else None,
            receiver_background_min=float(background.min()),receiver_background_max=float(background.max()),
            temperature_session_count=sum(bool(r['temperature_available']) for r in group),
            background_association_log_slope_per_us_cm=background_slope,background_association_r_squared=background_r2,
            background_association_day_count=d,background_association_scope='Exploratory day-mean association; not causal, not a reuse gate.',
            k_reference=float(np.exp(m)),mean_ci_lower=float(np.exp(m-mean_margin)),mean_ci_upper=float(np.exp(m+mean_margin)),
            session_prediction_lower_ratio=float(np.exp(-session_margin)),session_prediction_upper_ratio=float(np.exp(session_margin)),
            day_prediction_lower_ratio=float(np.exp(-day_margin)),day_prediction_upper_ratio=float(np.exp(day_margin)),
            application_log_sd=max(sd,ds),within_day_log_sd=float(np.sqrt(sum(np.sum((y[[i for i,r in enumerate(group) if r['field_date']==day]]-daily[j])**2) for j,day in enumerate(days))/max(n-d,1))),
            between_day_log_sd=ds,drift_effect_log=drift,drift_ci_lower_log=drift-drift_margin,drift_ci_upper_log=drift+drift_margin,
            lodo_effects=lodo,max_abs_lodo=max((abs(e['q_relative_effect']) for e in lodo),default=0),tolerance_q=tolerance,
            outcome=outcome,reasons=reasons,cross_sensor_pooling='not_assessed',
            interpretation='Conditional on independent day groups, comparable water/settings and stable stock preparation; not universal device validation.',
            limitations=['only_observed_date_domain','unknown_shared_stock_lineage','specific_compensation_settings_not_recovered']))
    return results


def plot_consistency(path, rows, evaluations):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    eligible=[r for r in rows if r['compat_class']=='mass_library_eligible']
    with plt.rc_context({'font.size':12}):
        fig,axes=plt.subplots(1,2,figsize=(12.8,5.3),layout='constrained')
        for ax,basis in zip(axes,('specific','actual')):
            points=[r for r in eligible if r['conductivity_basis']==basis]
            if points:
                x=[np.datetime64(r['field_date']) for r in points];y=[float(r['k']) for r in points]
                ax.scatter(x,y,s=48,color='#0072B2')
                ref=next(e for e in evaluations if e['conductivity_basis']==basis)
                ax.axhline(ref['k_reference'],color='#333333',label='Reference geometric mean')
                ax.axhspan(ref['mean_ci_lower'],ref['mean_ci_upper'],color='#0072B2',alpha=.15,label='Mean interval (day groups)')
                lo=ref['k_reference']*ref['session_prediction_lower_ratio'];hi=ref['k_reference']*ref['session_prediction_upper_ratio']
                ax.axhspan(lo,hi,facecolor='none',edgecolor='#777777',hatch='//',label='Session interval (conditional)')
                ax.axhline(ref['k_reference']*.95,color='#777777',ls=':',label='±5% Q-effect limits')
                ax.axhline(ref['k_reference']*1.05,color='#777777',ls=':')
                ax.set_title(f"{basis.title()}: {ref['outcome'].replace('_',' ')}\nn={len(points)} sessions, {ref['day_count']} days",fontsize=13)
                ax.tick_params(axis='x',rotation=25)
            ax.set_ylabel('K [(mg/L)/(µS/cm)]');ax.set_xlabel('Calibration date');ax.grid(axis='y',alpha=.2)
        axes[0].legend(fontsize=9,frameon=False)
        fig.suptitle('One calibration coefficient is not yet validated for general reuse',fontsize=16)
        fig.supxlabel('Source: reviewed calibration bundle; October 2–5, 2026. Method-conflict candidates excluded. Intervals are conditional.',fontsize=10)
        fig.savefig(path,dpi=150);plt.close(fig)


def run_reuse(records_dir, calibration_dir, pairing_dir, output_dir, *, site='NISQ', tolerance=.05, root=ROOT):
    cal_info,pins=verify_bundle(calibration_dir,root);pair,pairpins=verify_bundle(pairing_dir,root);pins.update(pairpins)
    pin_record_tables(records_dir,cal_info,pins,root)
    with staged_run(output_dir,pins,[__file__,calibration.__file__,matching.__file__]) as (stage,pins):
        rows,candidates=audit_calibrations(records_dir,calibration_dir,pairing_dir,site=site)
        frozen=[{k:r[k] for k in ('calibration_id','conductivity_basis','sensor_serial','field_date')} for r in rows if r['compat_class']=='mass_library_eligible']
        prereg=dict(created_at_utc=datetime.now(timezone.utc).isoformat(),tolerance_q=tolerance,frozen_sessions=frozen,
            rules='n>=6,d>=3; specific pass requires LODO, both application intervals <=T, drift upper<=T/2 and verified stock/settings/independence; fail requires observed held-out day effect or drift lower>T. Actual reuse requires a temperature model (not implemented); otherwise insufficient.',
            inference='Day-balanced geometric reference and day-level t drift; session interval diagnostic, grouped-day IID assumption conditional.')
        (stage/'frozen_sessions.json').write_text(matching._json(prereg)+'\n')
        evaluations=evaluate_reuse(rows,tolerance=tolerance)
        for name,data in [('compatibility',rows),('method_candidates',candidates),('reuse_evaluation',evaluations)]:
            matching._write_table(stage/(name+'.csv'),data,['calibration_id'] if name!='reuse_evaluation' else ['sensor_serial'])
        (stage/'figures').mkdir();plot_consistency(stage/'figures/calibration_consistency.png',rows,evaluations)
        info=write_run_info(stage,pins,scope=f'{site or "All recorded sites"}: calibration compatibility and conditional coefficient-reuse test only.',
            preregistration=prereg,compatibility_counts=dict(Counter(r['compat_class'] for r in rows)),
            outcome_counts=dict(Counter(e['outcome'] for e in evaluations)),frozen_session_count=len(frozen),
            no_library_domains_reason='No identity-supported mass sessions exist for other sensors/periods.',
            methodology_adjustments=['Day-group inference, not session pseudoreplication','Both session and day application bounds required','No chi-square IID-session failure claim with shared stock/day effects'])
    return info


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--records',type=Path,default=ROOT/'salt_dilution/data/records');p.add_argument('--calibrations',type=Path,default=DEFAULT_CALIBRATIONS)
    p.add_argument('--pairing',type=Path,default=DEFAULT_PAIRING);p.add_argument('--output',type=Path,required=True);p.add_argument('--tolerance',type=float,default=.05)
    p.add_argument('--all-sites',action='store_true',help='Audit each site without changing the site-separated reuse domains.')
    a=p.parse_args(argv)
    try:info=run_reuse(a.records,a.calibrations,a.pairing,a.output,tolerance=a.tolerance,site=None if a.all_sites else 'NISQ')
    except (ValueError,OSError) as error:p.exit(2,str(error)+'\n')
    print(matching._json(dict(compatibility=info['compatibility_counts'],reuse=info['outcome_counts'],output=str(a.output))))
    return 0

if __name__=='__main__':raise SystemExit(main())
