"""Integration checks against the raw HTML exports added in commit 5cd3f5e.

No raw observations are copied into fixtures. Set MORA_REQUIRE_RAW_TESTS=1 to
make a missing raw corpus a failure (used by CI). Otherwise source-only copies
can run the unit suite with these two integration checks explicitly skipped.
"""

import hashlib
from html import unescape
import math
import os
from pathlib import Path
import re
import tempfile
import unittest

import pandas as pd

from salt_dilution.scripts.parsers.parse_data import process_path, read_data

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'salt_dilution/data/raw'
CASES = [
    ('20260918', '2026-09-18_15-53-31', 373),
    ('20261002', '2026-10-02_14-42-48', 355),
    ('20261002', '2026-10-02_17-48-22', 369),
    ('20261004', '2026-10-04_07-21-30', 431),
    ('20261004', '2026-10-04_12-24-34', 470),
    ('20261004', '2026-10-04_15-29-37', 290),
    ('20261004', '2026-10-04_17-45-54', 388),
    ('20261005', '2026-10-05_11-49-30', 422),
    ('20261005', '2026-10-05_14-49-50', 402),
    ('20261005', '2026-10-05_17-33-57', 401),
]


class RecentVuSituIntegrationTests(unittest.TestCase):
    def setUp(self):
        missing = [stamp for date, stamp, _ in CASES
                   if not (RAW / date / f'VuSitu_LiveReadings_{stamp}_Device_Location.html').is_file()]
        if missing:
            if os.environ.get('MORA_REQUIRE_RAW_TESTS') == '1':
                self.fail(f'Required raw corpus is missing: {missing}')
            self.skipTest('Raw corpus absent in this source-only checkout')

    def test_all_ten_files_preserve_every_source_cell(self):
        for date, stamp, expected in CASES:
            with self.subTest(recording=stamp):
                path = RAW / date / f'VuSitu_LiveReadings_{stamp}_Device_Location.html'
                before = hashlib.sha256(path.read_bytes()).hexdigest()
                text = path.read_text(encoding='utf-8-sig')
                df, meta = read_data(path)
                self.assertEqual(len(df), expected)
                self.assertEqual(meta['embedded_metadata']['ReportProperties']['Readings'], str(expected))
                self.assertEqual(meta['embedded_metadata']['ReportProperties']['TimeOffset'], '-07:00:00')
                self.assertEqual(meta['utc_offset_seconds'], -25200)
                self.assertTrue(df.timestamp.is_monotonic_increasing)
                self.assertFalse(df.timestamp.duplicated().any())
                self.assertTrue((df.timestamp.diff().dropna().dt.total_seconds() == 1).all())
                pd.testing.assert_series_equal(
                    df.timestamp_utc.dt.tz_localize(None) - df.timestamp,
                    pd.Series(pd.Timedelta(hours=7), index=df.index), check_names=False,
                )
                self.assertNotIn('temperature_c', df)
                self.assertEqual(sum(str(c).startswith('Temperature') for c in df.columns), 2)
                self.assertTrue(any(c.get('unit_type') == '65' for c in meta['channels']))
                # Independent extraction of the fixed vendor row/cell markup;
                # do not call the implementation's HTML parser as our oracle.
                rows = re.findall(r'<tr\b[^>]*\bisi-data-row[^>]*>(.*?)</tr>', text, flags=re.S | re.I)
                self.assertEqual(len(rows), expected)
                columns = [c['column'] for c in meta['channels']]
                for i, row in enumerate(rows):
                    cells = [unescape(re.sub(r'<[^>]+>', '', c)).strip()
                             for c in re.findall(r'<td\b[^>]*>(.*?)</td>', row, flags=re.S | re.I)]
                    self.assertEqual(len(cells), len(columns))
                    for name, value in zip(columns, cells):
                        actual = df[name].iloc[i]
                        if name == 'timestamp':
                            self.assertEqual(actual, pd.Timestamp(value))
                        elif not value:
                            self.assertTrue(pd.isna(actual) or actual == '')
                        else:
                            try:
                                number = float(value)
                            except ValueError:
                                self.assertEqual(str(actual), value)
                            else:
                                self.assertTrue(math.isclose(float(actual), number, rel_tol=1e-12, abs_tol=1e-12))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)

    def test_batch_writes_ten_and_skips_four_supporting_reports(self):
        includes = [f'{date}/*.html' for date in sorted({c[0] for c in CASES})]
        with tempfile.TemporaryDirectory() as directory:
            report = process_path(RAW, Path(directory), recursive=True, include=includes)
            self.assertEqual(report['counts'], {'parsed': 0, 'written': 10, 'skipped': 4, 'failed': 0})
            self.assertEqual(sum(e.get('row_count', 0) for e in report['files']), 3901)
            for entry in report['files']:
                if entry['status'] == 'written':
                    data = Path(entry['processed_path'])
                    self.assertEqual(len(pd.read_csv(data)), entry['row_count'])
                    self.assertEqual(hashlib.sha256(data.read_bytes()).hexdigest(), entry['processed_sha256'])
                elif entry['status'] == 'skipped':
                    self.assertEqual(entry['reason'], 'supporting_report')


if __name__ == '__main__':
    unittest.main()
