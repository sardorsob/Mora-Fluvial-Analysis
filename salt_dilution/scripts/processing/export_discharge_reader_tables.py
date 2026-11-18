"""Export compact reader tables from the saved discharge CSVs."""

import argparse
import csv
from io import StringIO
from pathlib import Path


RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"

RELEASE_COLUMNS = """
    trial_id field_date site_alias category q_primary_m3_s q_actual_comparison_m3_s
    q_status scientifically_accepted conductivity_basis logical_recording_id
    sensor_serial calibration_id discharge_method mass_g mass_basis
    mass_confirmation_status injection_solution_volume_ml solution_volume_basis
    k coefficient_unit integral_us_cm_s window_status estimate_support pairing_status
    case_disposition window_numerical_review local_sensitivity_min_relative
    local_sensitivity_max_relative quality_flags calibration_reference_flags data_limits
    user_window_signoff
"""

CALIBRATION_COLUMNS = """
    calibration_id field_date site_alias conductivity_basis calibration_basis alias_label
    sensor_serial identity_status source_variant procedure_id stock_water_source
    incompatible_notebook_version recipe_qualification k k_se coefficient_unit n_points
    ec_min ec_max receiver_background_ec max_abs_leave_one_dose_k_relative_effect
    quadratic_sse_reduction_fraction disposition compat_class reasons
"""

SCENARIO_COLUMNS = """
    trial_id recipe_id window_id recording_edge_id conductivity_basis calibration_id
    calibration_series_alias sensor_serial background_mode gap_mode q_m3_s
    q_m3_s_per_delivered_litre result_class scientifically_accepted quantity_kind mass_g
    injection_solution_volume_ml k k_se coefficient_unit dose_fraction_slope
    concentration_scale n_points r_squared ec_min ec_max integral_us_cm_s
    observed_interval_integral_us_cm_s modelled_gap_integral_us_cm_s modelled_gap_seconds
    background_pre_us_cm background_post_us_cm pulse_samples gap_interpretation capture_status
    recipe_evidence unresolved_requirements calibration_limitations capture_limitations
    quantity_limitations
    event_link_status sensor_applicability series_issues
"""

BASELINE_COLUMNS = {
    "calibration_compatibility": CALIBRATION_COLUMNS + """
        reuse_conditions_confirmed
    """,
    "calibration_quality": CALIBRATION_COLUMNS + """
        fit_status skip_reason fit_se_status recipe_uncertainty temperature_min_c
        temperature_max_c diagnostic_status flags nacl_reference_k nacl_reference_unit
        q_ratio_if_reference_k_and_fixed_integral implied_original_injectate_mg_l
        nacl_saturation_reference_mg_l reference_assumptions
    """,
    "capture_coverage": """
        trial_id logical_recording_id channel device_serial outcome reason_code detail
        first_local last_local sample_count duration_s pre_30s_samples post_30s_samples
        pre_30s_mean_us_cm post_30s_mean_us_cm post_minus_pre_us_cm peak_us_cm
        post_30s_slope_us_cm_per_s sample_gaps diagnostic_scope series_issues
    """,
    "coefficient_reuse": """
        sensor_serial conductivity_basis site_alias procedure_id water_source date_start
        date_end session_count day_count session_ids calibration_ec_min calibration_ec_max
        receiver_background_min receiver_background_max temperature_session_count k_reference
        mean_ci_lower mean_ci_upper session_prediction_lower_ratio session_prediction_upper_ratio
        day_prediction_lower_ratio day_prediction_upper_ratio drift_effect_log drift_ci_lower_log
        drift_ci_upper_log max_abs_lodo tolerance_q outcome reasons cross_sensor_pooling
        interpretation limitations
    """,
    "conditional_discharge": """
        trial_id field_date logical_recording_id conductivity_basis calibration_id
        q_m3_s mass_g k coefficient_unit integral_us_cm_s pre_mean interval_start_local
        interval_end_local scenario qualification evidence scientifically_accepted
        calibration_reference_flags calibration_reference_status calibration_reference_assumptions
    """,
    "discharge_by_release": RELEASE_COLUMNS,
    "discharge_estimates": """
        trial_id field_date logical_recording_id recording_edge_id sensor_serial identity_status
        conductivity_basis calibration_id fit_reference q_m3_s q_status estimate_role
        scientifically_accepted estimate_support discharge_method mass_g mass_basis
        mass_confirmation nominal_equals_delivered_mass_assumed injection_solution_volume_ml
        solution_volume_basis k k_se coefficient_unit integral_us_cm_s
        background_mode window_status pulse_start_t_s pulse_end_t_s pulse_samples bridged_cells
        gap_bound_us_cm_s indicative_sensitivity_relative indicative_q_lower_l_s
        indicative_q_upper_l_s uncertainty_scope flags calibration_source_variant
        calibration_reference_flags calibration_reference_status
    """,
    "discharge_primary": RELEASE_COLUMNS,
    "observed_pulse_areas": """
        trial_id logical_recording_id conductivity_basis sensor_serial integral_us_cm_s
        area_unit background_pre_integral_us_cm_s background_post_integral_us_cm_s
        pre_mean post_mean pre_samples pulse_samples post_samples event_link_status
        clock_face_windows scientifically_accepted interpretation
    """,
    "quality_review_by_channel": """
        trial_id logical_recording_id conductivity_basis calibration_id identity_status
        estimate_role q_primary_m3_s q_status scientifically_accepted discharge_method
        estimate_support independently_recomputed_integral_us_cm_s tested_scenarios
        rejected_scenarios q_sensitivity_min_m3_s q_sensitivity_max_m3_s
        window_numerical_review window_user_signoff
        k k_fit_se_relative calibration_r_squared calibration_ec_min calibration_ec_max
        river_pulse_ec_min river_pulse_ec_max added_ec_span_exceeded peak_added_ec_to_calibration_span_ratio
        area_above_added_ec_span_fraction peak_to_pre_noise pulse_end_excess_to_peak_ratio
        calibration_applicability mixing_check tracer_recovery mass_basis solution_volume_basis
        total_uncertainty calibration_reference_flags calibration_reference_status
    """,
    "stage_diagnostics": """
        trial_id logical_recording_id channel field_date parameter unit source_column
        pre_mean post_mean change pre_sample_count post_sample_count comparison_window
        interpretation
    """,
}

SCENARIO_TABLE_COLUMNS = {
    "scenario_calibrations": """
        trial_id recipe_id calibration_id probe_alias conductivity_basis k k_se coefficient_unit
        n_points r_squared ec_min ec_max fit_note
    """,
    "scenario_estimates": SCENARIO_COLUMNS,
    "working_estimates": SCENARIO_COLUMNS + """
        working_recipe_status protocol_exceptions working_choice_is_measurement
    """,
}


def project_csv(source: Path, columns: list[str]) -> str:
    """Copy the selected fields in source row order without parsing numeric values."""
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    with source.open(encoding="utf-8", newline="") as file:
        reader = csv.reader(file, strict=True)
        header = next(reader, [])
        if len(header) != len(set(header)):
            raise ValueError(f"{source}: duplicate source headers")
        missing = set(columns) - set(header)
        if missing:
            raise ValueError(f"{source}: missing columns: {', '.join(sorted(missing))}")
        positions = [header.index(column) for column in columns]
        writer.writerow(columns)
        for row in reader:
            if len(row) != len(header):
                raise ValueError(f"{source}:{reader.line_num}: unexpected row width")
            writer.writerow([row[position] for position in positions])
    return output.getvalue()


def main() -> None:
    """Generate reader tables or check that the saved copies are current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--check", action="store_true", help="Check the saved CSVs without writing.")
    args = parser.parse_args()

    projections = {}
    for source_dir, group, table_columns in (
        (Path("discharge_analysis") / "tables", "baseline", BASELINE_COLUMNS),
        (Path("discharge_scenarios"), "scenarios", SCENARIO_TABLE_COLUMNS),
    ):
        for table, fields in table_columns.items():
            source = args.results_dir / source_dir / f"{table}.csv"
            destination = args.results_dir / "reader_tables" / group / f"{table}_compact.csv"
            projections[destination] = project_csv(source, fields.split())

    if args.check:
        stale = [
            path for path, projected in projections.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != projected
        ]
        if stale:
            parser.exit(1, "Missing or stale reader tables:\n" + "\n".join(map(str, stale)) + "\n")
        print(f"Checked {len(projections)} reader tables.")
        return

    for path, projected in projections.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(projected, encoding="utf-8", newline="\n")
    print(f"Exported {len(projections)} reader tables.")


if __name__ == "__main__":
    main()
