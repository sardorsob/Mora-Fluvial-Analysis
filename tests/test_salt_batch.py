"""Regression tests for metadata, timestamps and safe batch ingestion."""

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from salt_dilution.scripts.parsers.aquatroll import read_aquatroll
from salt_dilution.scripts.parsers.parse_data import main


def live_html(offset="-07:00:00", times=None, inline=True):
    times = times or ["2026-10-02 14:42:48", "2026-10-02 14:42:49"]
    def prop(group, key, label, value):
        if inline:
            return (f'<tr><td isi-group-member="{group}" isi-property="{key}">'
                    f'<span isi-label="">{label}</span> = '
                    f'<span isi-value=""><b>{value}</b></span></td></tr>')
        return (f'<tr><td isi-group-member="{group}" isi-property="{key}"></td>'
                f'<td>{label}</td><td>{value}</td></tr>')
    properties = prop("InstrumentProperties-101", "Model", "Device Model", "Aqua TROLL 200")
    properties += prop("ReportProperties", "Readings", "Readings", str(len(times)))
    if offset is not None:
        properties += prop("ReportProperties", "TimeOffset", "Time Offset", offset)
    labels = ["Date Time", "Actual Conductivity (µS/cm) (101)",
              "Specific Conductivity (µS/cm) (101)",
              "Temperature (°C) (101)", "Temperature (°C) (202)"]
    headers = ''.join(f'<td isi-data-column-header="Parameter" '
                      f'isi-device-serial-number="{202 if i == 4 else 101}" '
                      f'isi-unit-type="{65 if i in (1, 2) else 1}">{label}</td>'
                      for i, label in enumerate(labels))
    rows = ''.join(f'<tr isi-data-row=""><td>{stamp}</td><td>25.5</td>'
                   '<td>35.5</td><td>10.5</td><td>25.0</td></tr>' for stamp in times)
    return ('<html><head><meta name="isi-report-type" content="LiveReadings"></head>'
            f'<body><table>{properties}<tr>{headers}</tr>{rows}</table></body></html>')


class TempTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = self.root / 'raw'
        self.raw.mkdir()
        self.out = self.root / 'processed'

    def source(self, name='sample.html', content=None):
        path = self.raw / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(live_html() if content is None else content, encoding='utf-8')
        return path

    def run_cli(self, *args):
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        with contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr):
            return main([str(a) for a in args])

    def manifest(self):
        return json.loads((self.out / 'ingestion_manifest.json').read_text())


class MetadataTests(TempTests):
    def test_inline_metadata_and_channel_identity(self):
        df, meta = read_aquatroll(self.source())
        self.assertEqual(meta['embedded_metadata'].get('ReportProperties', {}).get('TimeOffset'), '-07:00:00')
        self.assertEqual(meta['embedded_metadata']['InstrumentProperties-101']['Model'], 'Aqua TROLL 200')
        channel = next(c for c in meta['channels'] if c['column'] == 'actual_conductivity_us_cm')
        self.assertEqual(channel['device_serial_number'], '101')
        self.assertEqual(channel['unit'], 'µS/cm')
        self.assertEqual(channel['unit_type'], '65')
        self.assertEqual(df['actual_conductivity_us_cm'].tolist(), [25.5, 25.5])
        self.assertNotIn('temperature_c', df)
        self.assertIn('Temperature (°C) (101)', df)
        self.assertIn('Temperature (°C) (202)', df)

    def test_separate_cell_layout_still_works(self):
        df, meta = read_aquatroll(self.source(content=live_html(inline=False)))
        self.assertEqual(meta['embedded_metadata']['ReportProperties']['TimeOffset'], '-07:00:00')
        self.assertEqual(len(df), 2)

    def test_numeric_offset_adds_utc_without_replacing_source_clock(self):
        df, meta = read_aquatroll(self.source())
        self.assertIn('timestamp_utc', df)
        self.assertEqual(str(df['timestamp'].iloc[0]), '2026-10-02 14:42:48')
        self.assertEqual(str(df['timestamp_utc'].iloc[0]), '2026-10-02 21:42:48+00:00')
        self.assertEqual(meta['utc_offset_seconds'], -25200)

    def test_missing_offset_is_not_invented(self):
        df, meta = read_aquatroll(self.source(content=live_html(offset=None)))
        self.assertNotIn('timestamp_utc', df)
        self.assertTrue(any('offset' in w.lower() for w in meta.get('warnings', [])))

    def test_invalid_offset_is_not_guessed(self):
        df, meta = read_aquatroll(self.source(content=live_html(offset='PST')))
        self.assertNotIn('timestamp_utc', df)
        self.assertTrue(any('offset' in w.lower() for w in meta.get('warnings', [])))

    def test_clock_only_values_are_rejected(self):
        with self.assertRaisesRegex(ValueError, '[Cc]lock-only'):
            read_aquatroll(self.source(content=live_html(times=['14:42:48', '14:42:49'])))

    def test_clock_only_csv_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '[Cc]lock-only'):
            read_aquatroll(self.source('clock.csv', 'Time,Actual Conductivity (µS/cm)\n12:34:56,1\n'))

    def test_csv_offset_also_preserved_and_used(self):
        df, meta = read_aquatroll(self.source('random.csv', 'Report Properties\nTime Offset = +05:30:00\n'
            'Date Time,Actual Conductivity (µS/cm)\n2026-10-02 14:42:48,10\n'))
        self.assertIn('timestamp_utc', df)
        self.assertEqual(str(df['timestamp_utc'].iloc[0]), '2026-10-02 09:12:48+00:00')

    def test_units_are_not_silently_relabelled(self):
        text = live_html().replace('µS/cm', 'mS/cm').replace('°C', '°F')
        df, meta = read_aquatroll(self.source(content=text))
        self.assertNotIn('actual_conductivity_us_cm', df)
        self.assertIn('Actual Conductivity (mS/cm) (101)', df)
        self.assertTrue(meta.get('warnings'))

    def test_empty_recording_is_failure(self):
        text = '<meta name="isi-report-type" content="LiveReadings"><table><tr>'
        text += '<td isi-data-column-header="DateTime">Date Time</td></tr></table>'
        with self.assertRaisesRegex(ValueError, '[Ee]mpty|[Nn]o.*rows'):
            read_aquatroll(self.source(content=text))


class BatchTests(TempTests):
    def test_recursive_extraction_and_manifest(self):
        source = self.source('20261002/unusual_name.html')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        self.assertEqual(self.run_cli(self.raw, '--recursive', '--output', self.out), 0)
        self.assertTrue((self.out / '20261002/unusual_name.csv').exists())
        meta = json.loads((self.out / '20261002/unusual_name_metadata.json').read_text())
        self.assertEqual(meta['source_sha256'], digest)
        entry = self.manifest()['files'][0]
        self.assertEqual(entry['status'], 'written')
        self.assertEqual(entry['row_count'], 2)
        self.assertEqual(entry['source_sha256'], digest)
        self.assertEqual(entry['time_start_utc'], '2026-10-02T21:42:48+00:00')
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)

    def test_dry_run_does_not_write(self):
        self.source()
        self.assertEqual(self.run_cli(self.raw, '--recursive'), 0)
        self.assertFalse(self.out.exists())
        self.assertEqual(list(self.raw.glob('*.csv')), [])

    def test_nonrecursive_only_reads_top_level(self):
        self.source('top.html')
        self.source('nested/child.html')
        self.assertEqual(self.run_cli(self.raw, '--output', self.out), 0)
        self.assertEqual(self.manifest()['counts']['written'], 1)

    def test_content_based_supporting_reports_are_skipped(self):
        self.source('one.html', '<meta name="isi-report-type" content="DeploymentReport"><h1>Deployment</h1>')
        self.source('two.html', '<html><h2>Calibration Report</h2><table><tr><td>Instrument</td><td>Aqua TROLL 200</td></tr></table></html>')
        self.source('data.html')
        self.assertEqual(self.run_cli(self.raw, '--output', self.out), 0)
        self.assertEqual(self.manifest()['counts']['skipped'], 2)
        self.assertEqual(self.manifest()['counts']['written'], 1)
        self.assertEqual(self.manifest()['counts']['failed'], 0)

    def test_bad_measurement_is_failure_not_supporting_skip(self):
        self.source('broken.html', '<meta name="isi-report-type" content="LiveReadings"><p>Missing table</p>')
        self.source('good.html')
        self.assertEqual(self.run_cli(self.raw, '--output', self.out), 1)
        self.assertEqual(self.manifest()['counts']['failed'], 1)
        self.assertTrue((self.out / 'good.csv').exists())

    def test_existing_output_refused_without_modification(self):
        self.source()
        self.out.mkdir()
        existing = self.out / 'sample.csv'
        existing.write_text('keep me')
        self.assertEqual(self.run_cli(self.raw, '--output', self.out), 1)
        self.assertEqual(existing.read_text(), 'keep me')
        self.assertFalse((self.out / 'sample_metadata.json').exists())

    def test_explicit_overwrite(self):
        self.source()
        self.assertEqual(self.run_cli(self.raw, '--output', self.out), 0)
        self.assertEqual(self.run_cli(self.raw, '--output', self.out, '--overwrite'), 0)

    def test_same_stem_collision_is_not_overwritten(self):
        self.source('same.html')
        self.source('same.csv', 'Date Time,Actual Conductivity (µS/cm)\n2026-10-02 14:42:48,9\n')
        self.assertEqual(self.run_cli(self.raw, '--output', self.out, '--overwrite'), 1)
        self.assertFalse((self.out / 'same.csv').exists())

    def test_output_may_not_be_inside_raw(self):
        source = self.source()
        before = source.read_bytes()
        self.assertEqual(self.run_cli(self.raw, '--recursive', '--output', self.raw / 'processed'), 1)
        self.assertFalse((self.raw / 'processed').exists())
        self.assertEqual(source.read_bytes(), before)

    def test_single_source_cannot_be_overwritten(self):
        source = self.source('sample.csv', 'Date Time,Actual Conductivity (µS/cm)\n2026-10-02 14:42:48,9\n')
        before = source.read_bytes()
        self.assertEqual(self.run_cli(source, '--output', self.raw, '--overwrite'), 1)
        self.assertEqual(source.read_bytes(), before)

    def test_unexpected_csv_failure_is_recorded(self):
        self.source('unknown.csv', 'a,b\n1,2\n')
        self.assertEqual(self.run_cli(self.raw, '--output', self.out), 1)
        self.assertEqual(self.manifest()['counts']['failed'], 1)

    def test_csv_failure_keeps_the_underlying_reason(self):
        self.source('clock.csv', 'Time,Actual Conductivity (µS/cm)\n12:34:56,1\n')
        self.assertEqual(self.run_cli(self.raw, '--output', self.out), 1)
        self.assertIn('Clock-only', self.manifest()['files'][0]['error'])

    def test_include_filter(self):
        self.source('20261002/yes.html')
        self.source('20250709/no.html')
        self.assertEqual(self.run_cli(self.raw, '--recursive', '--include', '20261002/*', '--output', self.out), 0)
        self.assertEqual(self.manifest()['counts']['written'], 1)
        self.assertFalse((self.out / '20250709').exists())

    def test_empty_selection_fails(self):
        self.assertEqual(self.run_cli(self.raw, '--recursive'), 1)

    def test_single_file_command_remains_available(self):
        source = self.source()
        self.assertEqual(self.run_cli(source, '--output', self.out), 0)
        self.assertTrue((self.out / 'sample.csv').exists())
        self.assertTrue((self.out / 'sample_metadata.json').exists())


if __name__ == '__main__':
    unittest.main()
