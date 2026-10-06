import tempfile
from pathlib import Path
import unittest

import pandas as pd

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

    def test_winsitu_csv_skips_notes_table_and_finds_log_data(self):
        from salt_dilution.scripts.parsers.aquatroll import read_aquatroll

        path = self.dir / "NaCl_20260716.csv"
        path.write_text(
            "Report Date:,8/14/2026 6:02:16 PM\n"
            "Application:,WinSitu.exe\n"
            "\n"
            "Log Notes:\n"
            "Date and Time,Note\n"
            "7/16/2026 2:49:07 PM,field note\n"
            "\n"
            "Log Data:\n"
            "Time Zone: Pacific Daylight Time\n"
            "Date and Time,Seconds,Temperature (C),"
            "Actual Conductivity (µS/cm),Specific Conductivity (µS/cm)\n"
            "7/16/2026 4:07:15 PM,0,9.277,16.016,22.890\n",
            encoding="utf-8",
        )

        df, meta = read_aquatroll(path)

        self.assertEqual(len(df), 1)
        self.assertEqual(str(df.loc[0, "timestamp"]), "2026-07-16 16:07:15")
        self.assertEqual(df.loc[0, "actual_conductivity_us_cm"], 16.016)
        self.assertEqual(df.loc[0, "specific_conductivity_us_cm"], 22.89)
        self.assertEqual(
            meta["embedded_metadata"]["Log Data"]["Time Zone"],
            "Pacific Daylight Time",
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


class GeneralLoggerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_xlsx_reader_combines_date_time_and_preserves_channels(self):
        from salt_dilution.scripts.parsers.general_logger import read_general_logger

        path = self.dir / "20250731_General1_attenuation_riverLeft.xlsx"
        source = pd.DataFrame(
            {
                "Position": [1, 2],
                "Date": ["2025-07-31", "2025-07-31"],
                "Time": ["07:52:34", "07:52:35"],
                "Ch1 Value": [18.1, 18.2],
                "Ch1 Unit": ["uS/cm", "uS/cm"],
                "Ch2 Value": [7.2, 7.3],
                "Ch2 Unit": ["deg C", "deg C"],
            }
        )
        source.to_excel(path, index=False)

        df, meta = read_general_logger(path)

        self.assertIn("timestamp", df)
        self.assertEqual(str(df.loc[0, "timestamp"]), "2025-07-31 07:52:34")
        self.assertEqual(df.loc[0, "Ch1 Value"], 18.1)
        self.assertEqual(df.loc[0, "Ch1 Unit"], "uS/cm")
        self.assertEqual(df.loc[0, "Ch2 Value"], 7.2)
        self.assertEqual(df.loc[0, "Ch2 Unit"], "deg C")
        self.assertEqual(meta["source_format"], "xlsx")
        self.assertEqual(meta["source_type"], "general")
        self.assertEqual(meta["instrument_family"], "general_logger")
        self.assertEqual(meta["filename_metadata"]["instrument_id"], "1")
        self.assertEqual(meta["filename_metadata"]["site"], "attenuation")
        self.assertEqual(meta["filename_metadata"]["bank"], "river_left")


class CalibrationTableTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_solution_injection_schema(self):
        from salt_dilution.scripts.parsers.calibration_table import read_calibration_table

        path = self.dir / "solution.csv"
        path.write_text(
            "Calibration_volume_ml,Additions_of_secondary_ml,"
            "Cumulative_secondary_solution_ml,Conductivity\n"
            "15000,0.5,0.5,36.49\n",
            encoding="utf-8",
        )

        df, meta = read_calibration_table(path)

        self.assertEqual(meta["calibration_type"], "solution_injection")
        self.assertEqual(df.loc[0, "Conductivity"], 36.49)

    def test_solution_injection_schema_without_cumulative_column(self):
        from salt_dilution.scripts.parsers.calibration_table import read_calibration_table

        path = self.dir / "field_solution.csv"
        path.write_text(
            "Calibration_volume_ml,additions_of_calibration_ml,Conductivity,Tempature (C)\n"
            "2000,0,n/a,n/a\n"
            "2002,2,34.5,12.6\n",
            encoding="utf-8",
        )

        df, meta = read_calibration_table(path)

        self.assertEqual(meta["calibration_type"], "solution_injection")
        self.assertNotIn("Cumulative_calibration_solution_ml", df.columns)

    def test_mass_stock_schema(self):
        from salt_dilution.scripts.parsers.calibration_table import read_calibration_table

        path = self.dir / "mass.csv"
        path.write_text(
            "Calibration volume (ml),Calibration solution added (ml),"
            "Salt added (g),Concentration (g/mL),Conductivity,Temp\n"
            "2000,10,1,0.0005,50,8\n",
            encoding="utf-8",
        )

        df, meta = read_calibration_table(path)

        self.assertEqual(meta["calibration_type"], "mass_stock_titration")
        self.assertEqual(df.loc[0, "Salt added (g)"], 1)

    def test_unknown_calibration_schema_fails_clearly(self):
        from salt_dilution.scripts.parsers.calibration_table import read_calibration_table

        path = self.dir / "unknown.csv"
        path.write_text("foo,bar\n1,2\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "Unsupported calibration table schema"):
            read_calibration_table(path)


class ParseDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_dispatches_aquatroll_csv(self):
        from salt_dilution.scripts.parsers.parse_data import read_data

        path = self.dir / "slug.csv"
        path.write_text(
            '"Date Time","Actual Conductivity (µS/cm) (1)",'
            '"Specific Conductivity (µS/cm) (1)"\n'
            '"2026-09-01 16:21:24","1","2"\n',
            encoding="utf-8",
        )

        _, meta = read_data(path)
        self.assertEqual(meta["instrument_family"], "aquatroll")

    def test_dispatches_calibration_csv(self):
        from salt_dilution.scripts.parsers.parse_data import read_data

        path = self.dir / "calibration.csv"
        path.write_text(
            "Calibration_volume_ml,additions_of_calibration_ml,"
            "Cumulative_calibration_solution_ml,Conductivity\n"
            "2000,1,1,20\n",
            encoding="utf-8",
        )

        _, meta = read_data(path)
        self.assertEqual(meta["source_type"], "calibration")

    def test_dispatches_general_xlsx(self):
        from salt_dilution.scripts.parsers.parse_data import read_data

        path = self.dir / "20250731_General1_attenuation_riverLeft.xlsx"
        pd.DataFrame(
            {
                "Date": ["2025-07-31"],
                "Time": ["07:52:34"],
                "Ch1 Value": [18.1],
                "Ch1 Unit": ["uS/cm"],
            }
        ).to_excel(path, index=False)

        _, meta = read_data(path)
        self.assertEqual(meta["instrument_family"], "general_logger")

    def test_unsupported_extension_fails(self):
        from salt_dilution.scripts.parsers.parse_data import read_data

        path = self.dir / "data.txt"
        path.write_text("not data", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "Unsupported data file"):
            read_data(path)

    def test_cli_writes_only_when_output_is_given(self):
        from salt_dilution.scripts.parsers.parse_data import main

        path = self.dir / "slug.csv"
        path.write_text(
            '"Date Time","Actual Conductivity (µS/cm) (1)",'
            '"Specific Conductivity (µS/cm) (1)"\n'
            '"2026-09-01 16:21:24","1","2"\n',
            encoding="utf-8",
        )
        output = self.dir / "processed"

        main([str(path)])
        self.assertFalse(output.exists())

        main([str(path), "--output", str(output)])
        self.assertTrue((output / "slug.csv").is_file())
        self.assertTrue((output / "slug_metadata.json").is_file())


if __name__ == "__main__":
    unittest.main()
