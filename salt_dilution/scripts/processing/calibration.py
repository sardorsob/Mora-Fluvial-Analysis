"""Fit conductivity-to-concentration curves from the curated calibration tables.

The fit is independent of stream-event windows. Results remain provisional;
this module does not select a discharge background or calculate Q.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import tempfile

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
PROFILES = ROOT / 'salt_dilution/config/procedure_versions.json'


def _number(value, field, *, positive=False):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field} is missing or not numeric') from None
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError(f'{field} must be finite' + (' and positive' if positive else ''))
    return number


def fit_calibration(preparation, points, *, conductivity_basis='specific'):
    """Return fit metadata and derived point rows without changing observations.

    Regress concentration on the selected EC channel with a free intercept.
    K is that slope, not the inverse of an EC-on-concentration regression.
    """
    if conductivity_basis not in ('actual', 'specific'):
        raise ValueError('conductivity_basis must be actual or specific')
    profiles = json.loads(PROFILES.read_text())
    procedure = preparation['procedure_id']
    if procedure not in profiles:
        raise ValueError(f'Unsupported procedure: {procedure}')
    profile = profiles[procedure]
    receiver = _number(preparation.get('calibration_water_initial_ml'),
                       'calibration_water_initial_ml', positive=True)
    stock_volume, stock_basis = '', ''
    if profile['calibration_basis'] == 'mass_concentration':
        mass = _number(preparation.get('stock_salt_mass_g'), 'stock_salt_mass_g', positive=True)
        stock_basis = ('stock_solution_final_ml' if preparation.get('stock_solution_final_ml')
                       else 'stock_water_initial_ml')
        stock_volume = _number(preparation.get(stock_basis), stock_basis, positive=True)
        stock_concentration = mass * 1_000_000 / stock_volume  # g and mL -> mg/L
        unit = 'mg/L'
    else:
        aliquot = _number(preparation.get('injectate_aliquot_ml'), 'injectate_aliquot_ml', positive=True)
        water = _number(preparation.get('secondary_water_initial_ml'), 'secondary_water_initial_ml', positive=True)
        stock_concentration = aliquot / (water + aliquot)
        unit = 'mL/mL'

    ordered = sorted(points, key=lambda row: int(row['step_no']))
    if len({row['step_no'] for row in ordered}) != len(ordered):
        raise ValueError('Duplicate step numbers within a calibration/probe series')
    probes = {row.get('probe_alias', '') for row in ordered} - {''}
    if len(probes) > 1:
        raise ValueError('Fit each calibration probe series separately')
    derived, total, previous = [], 0.0, 0.0
    column = conductivity_basis + '_conductivity_us_cm'
    for row in ordered:
        if row['calibration_id'] != preparation['calibration_id']:
            raise ValueError('Calibration point refers to a different preparation')
        kind = row['addition_kind']
        if kind not in ('incremental', 'cumulative'):
            raise ValueError('Addition interpretation is unconfirmed')
        issue = ''
        try:
            added = _number(row.get('recorded_added_volume_ml'), 'recorded_added_volume_ml')
        except ValueError:
            added, issue = None, 'missing_or_invalid_added_volume'
        if added is not None and added < 0:
            raise ValueError('Added volumes must be nonnegative')
        if kind == 'incremental':
            total = total + added if total is not None and added is not None else None
        else:
            if added is not None and added < previous:
                raise ValueError('Cumulative volume decreases; split restarted preparations')
            total = added
            if added is not None:
                previous = added
        if total is None:
            issue = issue or 'cumulative_volume_unknown_after_missing_increment'
        concentration = stock_concentration * total / (receiver + total) if total is not None else None
        try:
            ec = _number(row.get(column), column)
        except ValueError:
            ec = None
            issue = issue or f'missing_or_invalid_{conductivity_basis}_conductivity'
        written_volume = row.get('recorded_vessel_volume_ml', '')
        discrepancy = ''
        if written_volume and total is not None:
            discrepancy = _number(written_volume, 'recorded_vessel_volume_ml', positive=True) - (receiver + total)
        derived.append(dict(calibration_id=preparation['calibration_id'],
                            probe_alias=next(iter(probes), ''), conductivity_basis=conductivity_basis,
                            step_no=row['step_no'], recorded_added_volume_ml=row.get('recorded_added_volume_ml', ''),
                            addition_kind=kind, cumulative_added_volume_ml=total,
                            calculated_vessel_volume_ml=receiver + total if total is not None else None,
                            recorded_vessel_volume_ml=written_volume, vessel_volume_difference_ml=discrepancy,
                            conductivity_us_cm=ec, concentration=concentration, concentration_unit=unit,
                            used_in_fit=not issue, exclusion_reason=issue,
                            sourcebook_reference=row.get('sourcebook_reference', '')))
    selected = [row for row in derived if row['used_in_fit']]
    if len(selected) < 3:
        raise ValueError(f'Fewer than three usable {conductivity_basis} conductivity/addition pairs')
    x = np.array([row['conductivity_us_cm'] for row in selected])
    y = np.array([row['concentration'] for row in selected])
    dx, dy = x - x.mean(), y - y.mean()
    if np.dot(dx, dx) == 0 or np.dot(dy, dy) == 0:
        raise ValueError('Conductivity and concentration must both vary')
    k = float(np.dot(dx, dy) / np.dot(dx, dx))
    if k <= 0:
        raise ValueError('Calibration slope must be positive')
    intercept = float(y.mean() - k * x.mean())
    residual = y - (k * x + intercept)
    for row in derived:
        row['fitted_concentration'] = k * row['conductivity_us_cm'] + intercept if row['used_in_fit'] else None
        row['residual'] = row['concentration'] - row['fitted_concentration'] if row['used_in_fit'] else None
    fit = dict(calibration_id=preparation['calibration_id'], procedure_id=procedure,
               calibration_basis=profile['calibration_basis'], conductivity_basis=conductivity_basis,
               probe_alias=next(iter(probes), ''), concentration_unit=unit,
               coefficient_unit=f'({unit}) / (uS/cm)', fit_method='OLS concentration on conductivity; free intercept',
               k=k, intercept=intercept, r_squared=float(1 - np.dot(residual, residual) / np.dot(dy, dy)),
               rmse=float(np.sqrt(np.mean(residual ** 2))), n_points=len(selected), n_source_points=len(ordered),
               ec_min=float(x.min()), ec_max=float(x.max()),
               concentration_min=float(y.min()), concentration_max=float(y.max()),
               stock_volume_ml=stock_volume, stock_volume_basis=stock_basis,
               stock_concentration=stock_concentration, stock_concentration_unit=unit,
               stock_salt_mass_g=preparation.get('stock_salt_mass_g', ''),
               calibration_water_initial_ml=receiver,
               vessel_disagreement_points=sum(abs(row['vessel_volume_difference_ml'] or 0) > .01 for row in derived),
               status='provisional')
    return fit, derived


def _read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def _write_csv(path, rows):
    fields = list(rows[0]) if rows else ['calibration_id', 'conductivity_basis', 'probe_alias', 'reason']
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)


def _plot_calibration(path, fits, points):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    with plt.rc_context({'font.size': 12}):
        figure, axes = plt.subplots(1, 2, figsize=(12, 5.2), layout='constrained')
        for fit in fits:
            basis = fit['conductivity_basis']
            selected = [p for p in points if p['conductivity_basis'] == basis and p['used_in_fit']]
            x = np.array([p['conductivity_us_cm'] for p in selected])
            y = np.array([p['concentration'] for p in selected])
            color, marker = ('#0072B2', 'o') if basis == 'specific' else ('#D55E00', '^')
            axes[0].scatter(x, y, color=color, marker=marker, label=f"{basis}: n={fit['n_points']}, R²={fit['r_squared']:.4f}")
            limits = np.array([x.min(), x.max()])
            axes[0].plot(limits, fit['k'] * limits + fit['intercept'], color=color)
            axes[1].scatter(x, [p['residual'] for p in selected], color=color, marker=marker)
        axes[0].set_ylabel('Added salt (mg/L)' if fits[0]['concentration_unit'] == 'mg/L'
                           else 'Relative injectate concentration (mL/mL)')
        axes[1].set_ylabel(f"Residual ({fits[0]['concentration_unit']})")
        axes[1].axhline(0, color='#777777', linewidth=1)
        axes[0].legend(frameon=False, fontsize=11)
        for ax in axes:
            ax.set_xlabel('Conductivity (µS/cm)')
            ax.grid(axis='y', color='#dddddd', linewidth=.6)
            ax.set_axisbelow(True)
        figure.suptitle(f"{fits[0]['calibration_id']} — provisional calibration", fontsize=15)
        figure.supxlabel('Source: curated calibration tables • fit and preparation details saved with results', fontsize=10)
        figure.savefig(path, dpi=150)
        plt.close(figure)


def run_calibrations(records_dir, output_dir, *, conductivity_basis='specific'):
    """Fit available series and save small results, including explicit skip reasons."""
    records_dir, output_dir = Path(records_dir), Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f'Refusing to replace an existing run: {output_dir}')
    bases = ['specific', 'actual'] if conductivity_basis == 'both' else [conductivity_basis]
    if any(basis not in ('specific', 'actual') for basis in bases):
        raise ValueError('Choose actual, specific or both conductivity bases')
    preparations = _read_csv(records_dir / 'calibrations.csv')
    observations = _read_csv(records_dir / 'calibration_points.csv')
    identities = [row['calibration_id'] for row in preparations]
    if len(identities) != len(set(identities)):
        raise ValueError('Duplicate preparation IDs')
    if any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', identity) for identity in identities):
        raise ValueError('Use file-safe calibration IDs without slashes or traversal components')
    keys = [(r['calibration_id'], r.get('probe_alias', ''), r['step_no']) for r in observations]
    if len(keys) != len(set(keys)) or any(r['calibration_id'] not in identities for r in observations):
        raise ValueError('Duplicate or orphan calibration points')
    if any(probe and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', probe) for _, probe, _ in keys):
        raise ValueError('Use file-safe probe aliases')
    provenance_path = records_dir / 'provenance.json'
    provenance = json.loads(provenance_path.read_text()) if provenance_path.is_file() else {}
    fits, derived, skips = [], [], []
    grouped = defaultdict(list)
    for row in observations:
        grouped[row['calibration_id'], row.get('probe_alias', '')].append(row)
    for prep in preparations:
        identity = prep['calibration_id']
        evidence = provenance.get('calibrations', {}).get(identity, {})
        groups = [(probe, rows) for (cal_id, probe), rows in grouped.items() if cal_id == identity]
        for probe, points in groups or [('', [])]:
            for basis in bases:
                try:
                    if evidence.get('source_table_status') == 'abandoned':
                        raise ValueError('Abandoned preparation; original staged attempt retained as evidence')
                    fit, computed = fit_calibration(prep, points, conductivity_basis=basis)
                except ValueError as error:
                    skips.append(dict(calibration_id=identity, conductivity_basis=basis,
                                      probe_alias=probe, reason=str(error)))
                    continue
                fit['probe_alias'] = probe or evidence.get('probe_alias', '')
                for point in computed:
                    point['probe_alias'] = fit['probe_alias']
                fit['source_note'] = evidence.get('source_record', {}).get('notes', '')
                fit['figure'] = f'figures/{identity}' + (f'_{probe}' if probe else '') + '.png'
                fits.append(fit); derived.extend(computed)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.calibration-', dir=output_dir.parent) as temporary:
        stage = Path(temporary); (stage / 'figures').mkdir()
        for figure_path in dict.fromkeys(fit['figure'] for fit in fits):
            group = [fit for fit in fits if fit['figure'] == figure_path]
            points = [p for p in derived if p['calibration_id'] == group[0]['calibration_id']
                      and p['probe_alias'] == group[0]['probe_alias']]
            _plot_calibration(stage / figure_path, group, points)
        _write_csv(stage / 'calibration_fits.csv', fits)
        _write_csv(stage / 'calibration_points.csv', derived)
        _write_csv(stage / 'calibration_skips.csv', skips)
        inputs = [records_dir / 'calibrations.csv', records_dir / 'calibration_points.csv', PROFILES]
        if provenance_path.is_file():
            inputs.append(provenance_path)
        git = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
        info = dict(status='complete_with_skips' if skips else 'complete',
                    created_at_utc=datetime.now(timezone.utc).isoformat(), git_commit=git.stdout.strip(),
                    code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    python_version=platform.python_version(), numpy_version=np.__version__,
                    conductivity_basis=conductivity_basis, fits=len(fits), skipped_series=len(skips),
                    inputs=[dict(path=str(path.resolve().relative_to(ROOT)) if path.resolve().is_relative_to(ROOT) else path.name,
                                 sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in inputs],
                    scope='Provisional calibration fits only. No stream-window selection, discharge, or staff acceptance.',
                    stock_volume_policy='Measured final volume when supplied; otherwise recorded preparation-water volume under the user-confirmed working protocol. No CSV values inferred.',
                    fit_definition='Concentration = k * conductivity + intercept. K is the free-intercept OLS slope; units and channel are saved per fit.')
        info['outputs'] = [dict(path=str(path.relative_to(stage)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                           for path in sorted(stage.rglob('*')) if path.is_file()]
        (stage / 'run_info.json').write_text(json.dumps(info, indent=2) + '\n')
        stage.rename(output_dir)
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, default=ROOT / 'salt_dilution/data/records')
    parser.add_argument('--output', type=Path, required=True, help='New result directory; existing runs are never overwritten')
    parser.add_argument('--basis', choices=['specific', 'actual', 'both'], default='specific')
    args = parser.parse_args()
    try:
        result = run_calibrations(args.records, args.output, conductivity_basis=args.basis)
    except (ValueError, FileExistsError) as error:
        parser.exit(2, f'{error}\n')
    print(f"Saved {result['fits']} provisional fits; {result['skipped_series']} series skipped: {args.output}")
    return 0 if result['fits'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
