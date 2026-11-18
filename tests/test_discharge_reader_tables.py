"""Verify compact discharge results against their published sources."""

import csv
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from salt_dilution.scripts.processing.export_discharge_reader_tables import (  # noqa: E402
    BASELINE_COLUMNS,
    RESULTS_DIR,
    SCENARIO_TABLE_COLUMNS,
    project_csv,
)


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read header and values as CSV strings."""
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return reader.fieldnames or [], list(reader)


class DischargeReaderTableTests(unittest.TestCase):
    def test_saved_projections_preserve_exact_values_and_order(self) -> None:
        for source_dir, group, table_columns in (
            (Path("discharge_analysis") / "tables", "baseline", BASELINE_COLUMNS),
            (Path("discharge_scenarios"), "scenarios", SCENARIO_TABLE_COLUMNS),
        ):
            for table, selection in table_columns.items():
                with self.subTest(table=table):
                    source = RESULTS_DIR / source_dir / f"{table}.csv"
                    saved = RESULTS_DIR / "reader_tables" / group / f"{table}_compact.csv"
                    source_fields, source_rows = read_rows(source)
                    fields, rows = read_rows(saved)

                    self.assertEqual(fields, selection.split())
                    self.assertLess(len(fields), len(source_fields))
                    self.assertEqual(len(fields), len(set(fields)))
                    self.assertEqual(rows, [{field: row[field] for field in fields} for row in source_rows])

    def test_working_summary_and_spill_response(self) -> None:
        source_dir = RESULTS_DIR / "discharge_scenarios"
        full_fields, full_rows = read_rows(source_dir / "working_estimates.csv")
        summary_fields, summary_rows = read_rows(source_dir / "working_estimates_summary.csv")
        self.assertLess(len(summary_fields), len(full_fields))
        self.assertEqual(
            summary_rows, [{field: row[field] for field in summary_fields} for row in full_rows]
        )

        for table in ("working_estimates", "scenario_estimates"):
            with self.subTest(table=table):
                _, rows = read_rows(
                    RESULTS_DIR / "reader_tables" / "scenarios" / f"{table}_compact.csv"
                )
                key_fields = (
                    "trial_id", "recipe_id", "window_id", "recording_edge_id",
                    "conductivity_basis", "calibration_id", "calibration_series_alias",
                    "background_mode", "gap_mode",
                )
                self.assertEqual(len(rows), len({tuple(row[field] for field in key_fields) for row in rows}))
                spill = [row for row in rows if row["result_class"] == "unit_response"]
                self.assertEqual(len(spill), 2 if table == "working_estimates" else 6)
                self.assertTrue(all(not row["q_m3_s"] and row["q_m3_s_per_delivered_litre"] for row in spill))

    def test_missing_field_fails_instead_of_publishing_empty_values(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.csv"
            source.write_text("trial_id,q_m3_s\nT01,1.0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing columns: conductivity_basis"):
                project_csv(source, ["trial_id", "conductivity_basis"])
