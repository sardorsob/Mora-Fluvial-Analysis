import tempfile
from pathlib import Path
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


class AquaTrollTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_html_reader_preserves_measurements_and_metadata(self):
        from salt_dilution.scripts.parsers.aquatroll import read_aquatroll

        path = self.dir / "VuSitu_LiveReadings_2025-07-09_15-47-28_Device_Location.html"
        html = (
            '<html><head>'
            '<meta name="isi-report-type" content="LiveReadings"/>'
            '<meta name="isi-csv-file-name" content="VuSitu_LiveReadings_2025-07-09_15-47-28_Device_Location.csv"/>'
            '</head><body><table>'
            '<tr><td isi-group="InstrumentProperties">Instrument Properties</td></tr>'
            '<tr><td></td><td isi-group-member="InstrumentProperties" isi-property="DeviceModel"></td>'
            '<td>Device Model</td><td>Aqua TROLL 200</td></tr>'
            '<tr class="dataHeader" isi-data-table="">'
            '<td isi-data-column-header="DateTime">Date Time</td>'
            '<td isi-data-column-header="Parameter">Actual Conductivity (µS/cm) (790478)</td>'
            '<td isi-data-column-header="Parameter">Specific Conductivity (µS/cm) (790478)</td>'
            '<td isi-data-column-header="Parameter">Temperature (°C) (790478)</td>'
            '<td isi-data-column-header="Parameter">Depth (ft) (790478)</td>'
            '</tr>'
            '<tr class="data" isi-data-row="">'
            '<td>2025-07-09 15:47:28.125</td><td>10.5</td><td>12.5</td><td>8.1</td><td>1.2</td>'
            '</tr></table></body></html>'
        )
        path.write_text(html, encoding="utf-8")

        df, meta = read_aquatroll(path)

        self.assertEqual(
            list(df.columns),
            [
                "timestamp",
                "actual_conductivity_us_cm",
                "specific_conductivity_us_cm",
                "temperature_c",
                "Depth (ft) (790478)",
            ],
        )
        self.assertEqual(str(df.loc[0, "timestamp"]), "2025-07-09 15:47:28.125000")
        self.assertEqual(df.loc[0, "actual_conductivity_us_cm"], 10.5)
        self.assertEqual(df.loc[0, "specific_conductivity_us_cm"], 12.5)
        self.assertEqual(df.loc[0, "Depth (ft) (790478)"], 1.2)
        self.assertEqual(meta["source_format"], "html")
        self.assertEqual(meta["source_type"], "live_reading")
        self.assertEqual(meta["instrument_family"], "aquatroll")
        self.assertEqual(
            meta["embedded_metadata"]["InstrumentProperties"]["DeviceModel"],
            "Aqua TROLL 200",
        )

    def test_csv_reader_finds_variable_header_and_keeps_extra_columns(self):
        from salt_dilution.scripts.parsers.aquatroll import read_aquatroll

        path = self.dir / "EC02_01_200.csv"
        csv_text = (
            '"Location Properties"\n'
            '"Location Name = EC-02"\n'
            '""\n'
            '"Report Properties"\n'
            '"Time Offset = -07:00:00"\n'
            '"Extra metadata row = yes"\n'
            '""\n'
            '"Date Time","Actual Conductivity (µS/cm) (914228)",'
            '"Specific Conductivity (µS/cm) (914228)",'
            '"Salinity (PSU) (914228)","Temperature (°C) (558407)"\n'
            '"2026-09-01 16:21:24","104.5","124.6","0.05","16.5"\n'
        )
        path.write_text(csv_text, encoding="utf-8")

        df, meta = read_aquatroll(path)

        self.assertEqual(len(df), 1)
        self.assertIn("actual_conductivity_us_cm", df)
        self.assertIn("specific_conductivity_us_cm", df)
        self.assertIn("Salinity (PSU) (914228)", df)
        self.assertEqual(meta["source_format"], "csv")
        self.assertEqual(
            meta["embedded_metadata"]["Report Properties"]["Time Offset"],
            "-07:00:00",
        )

    def test_multiple_temperature_columns_are_not_collapsed(self):
        from salt_dilution.scripts.parsers.aquatroll import read_aquatroll

        path = self.dir / "sample.csv"
        csv_text = (
            '"Date Time","Actual Conductivity (µS/cm) (1)",'
            '"Specific Conductivity (µS/cm) (1)",'
            '"Temperature (°C) (1)","Temperature (°C) (2)"\n'
            '"2026-09-01 16:21:24","1","2","3","4"\n'
        )
        path.write_text(csv_text, encoding="utf-8")

        df, _ = read_aquatroll(path)

        self.assertNotIn("temperature_c", df)
        self.assertIn("Temperature (°C) (1)", df)
        self.assertIn("Temperature (°C) (2)", df)


if __name__ == "__main__":
    unittest.main()
