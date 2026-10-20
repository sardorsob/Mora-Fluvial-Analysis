"""Keep the uploaded stock-mass corrections and reconciled record identities together."""

from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import unittest


RECORDS = Path(__file__).resolve().parents[1] / "salt_dilution/data/records"


def read_table(name):
    with (RECORDS / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


class LocalRecordReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((RECORDS / "manifest.json").read_text(encoding="utf-8"))
        cls.review = cls.manifest["reviewed_setting_overrides"]
        cls.preparations = read_table("calibrations.csv")

    def test_uploaded_table_preserved_except_source_block_id_repairs(self):
        aliases = self.review["local_to_current_id_by_source_block"]
        restored = []
        seen = set()
        for row in self.preparations:
            row = dict(row)
            block = row["sourcebook_reference"].split(";block=")[-1]
            if block in aliases:
                self.assertEqual(row["calibration_id"], aliases[block]["current"])
                row["calibration_id"] = aliases[block]["local"]
                seen.add(block)
            restored.append(row)
        self.assertEqual(seen, set(aliases))
        text = io.StringIO(newline="")
        writer = csv.DictWriter(text, fieldnames=list(restored[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(restored)
        data = text.getvalue().encode("utf-8")
        digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        self.assertEqual(digest, self.review["source_calibrations_git_blob"])

    def test_finite_review_overlay_matches_every_current_preparation(self):
        provenance = json.loads((RECORDS / "provenance.json").read_text(encoding="utf-8"))
        values = self.review["values"]
        field = self.review["field"]
        self.assertEqual(field, "stock_salt_mass_g")
        self.assertEqual(len(values), self.review["changed_cells"])
        self.assertTrue(set(values).issubset(provenance["calibrations"]))
        for row in self.preparations:
            identity = row["calibration_id"]
            expected = dict(provenance["calibrations"][identity]["current_csv_values"])
            if identity in values:
                self.assertEqual(expected[field], self.review["previous_value"])
                expected[field] = values[identity]
            self.assertEqual(row, expected, identity)

    def test_validation_summary_matches_tables_and_manifest(self):
        report = json.loads((RECORDS / "validation_report.json").read_text(encoding="utf-8"))
        for name, entry in self.manifest["tables"].items():
            self.assertEqual(report["current_table_sha256"][name], entry["sha256"])
            self.assertEqual(report["row_counts"][name.removesuffix(".csv")], len(read_table(name)))
        self.assertEqual(report["procedure_counts"], dict(Counter(row["procedure_id"] for row in self.preparations)))
        details = report["local_reconciliation"]
        self.assertEqual(details["stock_mass_cells_imported"], self.review["changed_cells"])
        self.assertEqual(details["stock_mass_values_populated"], sum(bool(row["stock_salt_mass_g"]) for row in self.preparations))
        self.assertEqual(details["unique_calibration_ids"], len({row["calibration_id"] for row in self.preparations}))
        links = read_table("trial_inputs.csv")
        linked = [row for row in links if row["dataset_id"]]
        self.assertEqual(report["recording_candidate_rows"], len(linked))
        self.assertEqual(report["unresolved_recording_rows"], len(links) - len(linked))
        self.assertEqual(report["distinct_electronic_datasets"], len({row["dataset_id"] for row in linked}))
        self.assertEqual(report["linked_releases"], len({row["trial_id"] for row in linked}))
        self.assertEqual(report["missing_trial_input_fields"], {field: sum(not row[field] for row in links) for field in links[0]})


if __name__ == "__main__":
    unittest.main()
