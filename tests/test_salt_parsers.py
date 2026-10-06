import unittest

from salt_dilution.scripts.parsers.filename_metadata import parse_filename


class FilenameMetadataTests(unittest.TestCase):
    def test_canonical_filename(self):
        meta = parse_filename(
            "20250709_144014_LiveReadings_790478_mixing_riverRight.html"
        )
        self.assertEqual(meta["date"], "20250709")
        self.assertEqual(meta["time"], "144014")
        self.assertEqual(meta["source_type"], "live_reading")
        self.assertEqual(meta["instrument_id"], "790478")
        self.assertEqual(meta["site"], "mixing")
        self.assertEqual(meta["bank"], "river_right")

    def test_legacy_filename_without_time(self):
        meta = parse_filename("20250709_LiveReading_790478_mixing_riverRight.html")
        self.assertEqual(meta["date"], "20250709")
        self.assertNotIn("time", meta)
        self.assertEqual(meta["source_type"], "live_reading")
        self.assertEqual(meta["bank"], "river_right")

    def test_vendor_filename(self):
        meta = parse_filename(
            "VuSitu_LiveReadings_2025-07-09_15-47-28_Device_Location.html"
        )
        self.assertEqual(meta["date"], "20250709")
        self.assertEqual(meta["time"], "154728")
        self.assertEqual(meta["source_type"], "live_reading")

    def test_unknown_filename_is_safe(self):
        self.assertEqual(parse_filename("PR04_03_600.csv"), {})


if __name__ == "__main__":
    unittest.main()
