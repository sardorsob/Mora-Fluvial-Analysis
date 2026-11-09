"""Assemble a reviewed analysis bundle without granting field acceptance."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import shutil

from . import calibration_reuse as reuse, mass_slug, matching

ROOT = matching.ROOT
DEFAULT_MASS = ROOT/'salt_dilution/results/discharge/2026-11-08_confirmed_mass'
DEFAULT_AUDIT = ROOT/'salt_dilution/results/discharge/2026-11-08_confirmed_mass_evidence'
DEFAULT_REVIEW = ROOT/'salt_dilution/results/discharge/2026-11-08_window_applicability_review'
DEFAULT_REUSE = ROOT/'salt_dilution/results/calibration_reuse/2026-11-08_reuse_test'

# Retain scientific evidence and settings alongside the combined analysis table.
COPY_FILES = {
    'mass': [('discharge_estimates.csv','discharge_estimates.csv'),
             ('recording_outcomes.csv','recording_outcomes.csv'),
             ('pulse_windows_used.json','pulse_windows.json'),
             ('release_confirmations_used.json','release_confirmations.json')],
    'audit': [('native_export_comparison.csv','native_export_comparison.csv'),
              ('capture_coverage.csv','capture_coverage.csv')],
    'review': [('review_by_release.csv','quality_review_by_release.csv'),
               ('review_by_channel.csv','quality_review_by_channel.csv'),
               ('window_sensitivity_scenarios.csv','window_sensitivity_scenarios.csv'),
               ('notebook_native_comparison.csv','field_note_comparison.csv'),
               ('blocked_release_review.csv','blocked_capture_review.csv'),
               ('review_design.json','window_review_design.json'),
               ('references.json','references.json')],
    'reuse': [('compatibility.csv','calibration_compatibility.csv'),
              ('method_candidates.csv','isolated_method_candidates.csv'),
              ('reuse_evaluation.csv','coefficient_reuse.csv'),
              ('frozen_sessions.json','reuse_test_design.json')],
}

DISPOSITIONS = {
    'computed': 'estimated_proposed',
    'blocked_tail_not_settled': 'not_estimable_capture',
    'blocked_pulse_start_missing': 'not_estimable_capture',
    'partial_missing_calibration': 'not_estimable_missing_calibration',
    'conflicting_identity': 'not_estimable_identity_conflict',
    'method_conflict_isolated': 'not_estimable_recipe_conflict',
    'relative_basis_not_mass_route': 'relative_route_out_of_scope',
    'out_of_scope_site': 'out_of_scope_site',
    'excluded_practice': 'excluded_practice',
}


def _indexed(rows, label):
    result = {}
    for row in rows:
        key = row.get('trial_id')
        if not key or key in result:
            raise ValueError(f'Duplicate or missing release key in {label}')
        result[key] = row
    return result


def assemble_release_table(master, estimates, reviews):
    """Close data-processing cases while retaining proposed values and limits."""
    source = _indexed(master, 'master')
    primary = _indexed([r for r in estimates if r['estimate_role']=='primary'], 'primary estimates')
    reviewed = _indexed(reviews, 'review')
    if not ({r['trial_id'] for r in estimates} | set(reviewed)).issubset(source):
        raise ValueError('Estimate/review refers to an unknown release')
    if {key for key,row in source.items() if row['category']=='computed'} != set(primary):
        raise ValueError('Computed releases must each have one primary estimate')
    if not set(primary).issubset(reviewed):
        raise ValueError('Each primary estimate requires a completed numerical review')
    result = []
    for key, original in source.items():
        row = dict(original)
        category = row['category']
        if category not in DISPOSITIONS:
            raise ValueError(f'Unknown release disposition: {category}')
        if key in primary:
            estimate = primary[key]
            for field, saved in [('q_primary_m3_s','q_m3_s'), ('q_primary_l_s','q_l_s')]:
                value = float(row[field])
                if not math.isfinite(value) or value<=0 or not math.isclose(value,float(estimate[saved]),rel_tol=1e-12):
                    raise ValueError(f'Master Q differs from selected primary: {key}')
            if str(estimate.get('scientifically_accepted','false')).lower() != 'false':
                raise ValueError('This export expects scientifically unaccepted source estimates')
        elif row.get('q_primary_m3_s') or row.get('q_primary_l_s'):
            raise ValueError('A release without a primary estimate must retain blank Q')
        review = reviewed.get(key, {})
        discrepancy = review.get('recommendation')=='source_background_reconciliation_required'
        limits = json.loads(row.pop('missing_requirements', '[]'))
        limits += json.loads(review.get('remaining_evidence_gaps') or '[]')
        flags = json.loads(primary.get(key,{}).get('flags') or '[]')
        if discrepancy: flags.append('unresolved_notebook_background')
        row.update(case_disposition=DISPOSITIONS[category], case_closed_for_current_data=True,
                   analysis_status=('proposed_with_source_discrepancy' if discrepancy else 'proposed_with_limits') if key in primary else 'not_estimated',
                   source_background_discrepancy=discrepancy,
                   window_numerical_review=review.get('window_numerical_review','disposition_review_completed'),
                   local_sensitivity_min_relative=review.get('local_sensitivity_min_relative',''),
                   local_sensitivity_max_relative=review.get('local_sensitivity_max_relative',''),
                   quality_flags=sorted(set(flags)), data_limits=sorted(set(limits)),
                   user_window_signoff=False, scientifically_accepted=False)
        result.append(row)
    return result


def run_export(mass_dir, audit_dir, review_dir, reuse_dir, output_dir, *, root=ROOT):
    root = Path(root).resolve()
    sources = {key: Path(value).resolve() for key,value in
               [('mass',mass_dir),('audit',audit_dir),('review',review_dir),('reuse',reuse_dir)]}
    output = Path(output_dir).resolve()
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in sources.values()):
        raise ValueError('Output must be separate from source bundles')
    pins, source_info, index = {}, {}, {}
    for key, path in sources.items():
        source_info[key], current = reuse.verify_bundle(path, root)
        pins.update(current)
        index[key] = dict(path=matching._ref(path,root),run_info_sha256=matching._hash(path/'run_info.json'))
    mass_info = str(sources['mass']/'run_info.json')
    for key in ('audit','review'):
        recorded = {str(matching._path(p['path'],root).resolve()):p['sha256'] for p in source_info[key]['inputs']}
        if recorded.get(mass_info) != index['mass']['run_info_sha256']:
            raise ValueError(f'{key} does not reference the selected mass-run bundle')
    mass_inputs = {str(matching._path(p['path'],root).resolve()):p['sha256'] for p in source_info['mass']['inputs']}
    if mass_inputs.get(str(sources['reuse']/'run_info.json')) != index['reuse']['run_info_sha256']:
        raise ValueError('The selected reuse evaluation is not the mass-run dependency')
    read = lambda p: matching._read_table(p,['trial_id'])
    master = read(sources['audit']/'discharge_by_release.csv')
    estimates = read(sources['mass']/'discharge_estimates.csv')
    reviews = read(sources['review']/'review_by_release.csv')
    combined = assemble_release_table(master, estimates, reviews)
    primaries = [r for r in combined if r['case_disposition']=='estimated_proposed']
    copies = [(sources[key]/source,Path(destination)) for key,files in COPY_FILES.items() for source,destination in files]
    for key in ('mass','review','reuse'):
        directory = sources[key]/'figures'
        copies += [(p,Path('figures')/key/p.relative_to(directory)) for p in sorted(directory.rglob('*.png')) if p.is_file()]
    for source,_ in copies:
        if pins.get(str(source.resolve())) != matching._hash(source):
            raise ValueError(f'Export source is not pinned by its bundle: {source}')
    with reuse.staged_run(output_dir,pins,[__file__,reuse.__file__,mass_slug.__file__,matching.__file__]) as (stage,pins):
        mass_slug._table(stage/'discharge_by_release.csv',combined,['trial_id'])
        mass_slug._table(stage/'discharge_primary.csv',primaries,['trial_id','q_primary_m3_s'])
        for source,destination in copies:
            target = stage/destination
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
        (stage/'source_bundles.json').write_text(matching._json(index)+'\n')
        limits = dict(scientifically_accepted=False,window_signoff_inferred=False,
            meaning_of_closure='All processing cases have a recorded result or no-estimate disposition for the current dataset; new source evidence can reopen a case.',
            capture_policy='No tail extrapolation, interpolation across missing samples or substitution of another release.',
            calibration_policy='Trial-specific coefficients only; failed/inconclusive reuse tests do not authorize a shared coefficient.',
            uncertainty='Window/background ranges and fit standard errors do not quantify total Q uncertainty. Mixing, recovery, settings and recipe uncertainty remain documented limits.',
            unresolved_source_policy='Preserve flagged October 4 T03 Q without guessing a background correction.')
        (stage/'analysis_limits.json').write_text(matching._json(limits)+'\n')
        commands = ['python','-m','salt_dilution.scripts.processing.export_discharge']
        for key,option in [('mass','--mass-run'),('audit','--audit-run'),('review','--review-run'),('reuse','--reuse-run')]:
            commands += [option,matching._ref(sources[key],root)]
        commands += ['--output','<fresh_output_directory>']
        guide = dict(entry_point='discharge_by_release.csv',primary_subset='discharge_primary.csv',
            channel_estimates='discharge_estimates.csv',units=dict(q_primary_m3_s='m3/s',q_primary_l_s='L/s',mass_g='g',k='(mg/L)/(uS/cm)'),
            missing_values='Blank Q means not estimated; never zero discharge.',
            figures='figures/mass: discharge and pulse plots; figures/review: window sensitivity; figures/reuse: calibration consistency.',
            quality='quality_review_by_release.csv, quality_review_by_channel.csv, field_note_comparison.csv and analysis_limits.json',
            reproduce_command=commands)
        (stage/'bundle_index.json').write_text(matching._json(guide)+'\n')
        (stage/'code').mkdir();shutil.copy2(__file__,stage/'code/export_discharge.py')
        info = reuse.write_run_info(stage,pins,scope='Complete analysis handoff for the current dataset; proposed estimates and explicit no-estimate outcomes.',
            completion_status='complete_for_current_dataset',release_count=len(combined),primary_release_count=len(primaries),
            channel_estimate_count=len(estimates),disposition_counts=dict(Counter(r['case_disposition'] for r in combined)),
            retained_source_discrepancy_ids=[r['trial_id'] for r in combined if r['source_background_discrepancy']],
            case_closure_is_scientific_acceptance=False,source_bundles=index,
            field_acceptance='Not claimed. Remaining physical evidence limits are retained, not uncompleted software tasks.')
    return info


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mass-run',type=Path,default=DEFAULT_MASS)
    parser.add_argument('--audit-run',type=Path,default=DEFAULT_AUDIT)
    parser.add_argument('--review-run',type=Path,default=DEFAULT_REVIEW)
    parser.add_argument('--reuse-run',type=Path,default=DEFAULT_REUSE)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    try: info = run_export(args.mass_run,args.audit_run,args.review_run,args.reuse_run,args.output)
    except (ValueError,OSError) as error: parser.exit(2,str(error)+'\n')
    print(matching._json({k:info[k] for k in ('completion_status','release_count','primary_release_count','disposition_counts')}))
    return 0


if __name__=='__main__': raise SystemExit(main())
