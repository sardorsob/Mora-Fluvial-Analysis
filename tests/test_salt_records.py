"""Integrity checks for curated records; opt in to checks of local parser outputs.

Run local file checks with MORA_CHECK_LOCAL_RECORDINGS=1. A fresh clone can run
the table checks without downloading or regenerating ignored stream readings.
"""

from collections import Counter
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / 'salt_dilution/data/records'


def read_table(name):
    with (RECORDS / f'{name}.csv').open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


class SaltRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = {name: read_table(name) for name in
                      ('trials', 'calibrations', 'calibration_points', 'trial_inputs')}
        cls.provenance = json.loads((RECORDS / 'provenance.json').read_text())

    def test_unique_parents_and_lossless_point_join(self):
        parents = Counter(row['calibration_id'] for row in self.tables['calibrations'])
        self.assertTrue(all(count == 1 for count in parents.values()), parents)
        points = self.tables['calibration_points']
        self.assertFalse({row['calibration_id'] for row in points} - parents.keys())
        self.assertEqual(sum(parents[row['calibration_id']] for row in points), len(points))
        keys = [(row['calibration_id'], row['probe_alias'], row['step_no']) for row in points]
        self.assertEqual(len(keys), len(set(keys)))

    def test_supporting_preparations_keep_distinct_source_identities(self):
        by_block = {row['sourcebook_reference'].split(';block=')[-1]: row['calibration_id']
                    for row in self.tables['calibrations']}
        expected = {'c_06_test_left': 'PAR-20260903-C06',
                    'c_06_test_right': 'PAR-20260903-C07',
                    'c_07_pr02': 'PAR-20260903-C08',
                    'c_08_p_unknown': 'PAR-20260903-C09',
                    'c_07_pr03': 'PAR-20260903-C01',
                    'c_07_pr04': 'PAR-20260903-C02',
                    'c_07_pr05': 'PAR-20260903-C03',
                    'c_07_pr06': 'PAR-20260903-C04',
                    'c_08_pr35': 'PAR-20260903-C05'}
        for block, identity in expected.items():
            self.assertEqual(by_block[block], identity)
            self.assertEqual(self.provenance['id_mapping']['calibrations'][block], identity)

    def test_foreign_keys_and_provenance_cover_current_rows(self):
        trials = {row['trial_id'] for row in self.tables['trials']}
        calibrations = {row['calibration_id'] for row in self.tables['calibrations']}
        self.assertEqual(len(trials), len(self.tables['trials']))
        self.assertEqual(trials, {row['trial_id'] for row in self.tables['trial_inputs']})
        self.assertEqual(calibrations, self.provenance['calibrations'].keys())
        point_keys = {f"{r['calibration_id']}|{r['probe_alias']}|{r['step_no']}"
                      for r in self.tables['calibration_points']}
        self.assertEqual(point_keys, self.provenance['calibration_points'].keys())
        self.assertEqual(len(self.tables['trial_inputs']), len(self.provenance['trial_inputs']))
        for number, (row, evidence) in enumerate(zip(self.tables['trial_inputs'],
                                                    self.provenance['trial_inputs']), 2):
            self.assertEqual(evidence['csv_row_number'], number)
            self.assertEqual((evidence['trial_id'], evidence['dataset_id']),
                             (row['trial_id'], row['dataset_id']))
            self.assertIn(row['trial_id'], trials)
            if row['calibration_id']:
                self.assertIn(row['calibration_id'], calibrations)

    def test_dataset_identity_probe_channel_and_pending_states(self):
        datasets = self.provenance['datasets']
        paths = {}
        for row in self.tables['trial_inputs']:
            self.assertEqual(bool(row['dataset_id']), bool(row['processed_path']))
            self.assertIn(row['conductivity_basis'], ('', 'actual', 'specific'))
            self.assertIn(row['review_status'], ('unreviewed', 'needs_review', 'verified'))
            self.assertEqual(bool(row['window_start_utc']), bool(row['window_end_utc']))
            if row['window_start_utc']:
                start, end = (datetime.fromisoformat(row[key].replace('Z', '+00:00'))
                              for key in ('window_start_utc', 'window_end_utc'))
                self.assertEqual(start.utcoffset().total_seconds(), 0)
                self.assertEqual(end.utcoffset().total_seconds(), 0)
                self.assertLess(start, end)
            if not all(row[key] for key in ('dataset_id', 'calibration_id', 'probe_alias',
                                           'conductivity_basis', 'window_start_utc', 'window_end_utc')):
                self.assertNotEqual(row['review_status'], 'verified')
            if not row['dataset_id']:
                continue
            dataset = datasets[row['dataset_id']]
            self.assertEqual(row['processed_path'], dataset['processed_path'])
            self.assertEqual(row['probe_alias'], dataset['probe_alias'])
            self.assertIn(row['probe_alias'], self.provenance['probe_registry'])
            if row['conductivity_basis']:
                self.assertIn(row['conductivity_basis'], dataset['available_conductivity_bases'])
            self.assertFalse(Path(row['processed_path']).is_absolute())
            self.assertNotIn('..', Path(row['processed_path']).parts)
            self.assertEqual(paths.setdefault(row['processed_path'], row['dataset_id']), row['dataset_id'])
            if row['calibration_id']:
                cal_probe = self.provenance['calibrations'][row['calibration_id']]['probe_alias']
                if cal_probe:
                    self.assertEqual(cal_probe, row['probe_alias'])

    def test_confirmed_october_links_follow_source_blocks_not_id_order(self):
        expected = {'NISQ-20261002-T01': '2026-10-02_17-48-22',
                    'NISQ-20261002-T02': '2026-10-02_14-42-48',
                    'NISQ-20261004-T01': '2026-10-04_07-21-30',
                    'NISQ-20261004-T02': '2026-10-04_12-24-34',
                    'NISQ-20261004-T03': '2026-10-04_17-45-54',
                    'NISQ-20261004-T04': '2026-10-04_15-29-37',
                    'NISQ-20261005-T01': '2026-10-05_11-49-30',
                    'NISQ-20261005-T02': '2026-10-05_14-49-50',
                    'NISQ-20261005-T03': '2026-10-05_17-33-57'}
        for trial, start in expected.items():
            rows = [r for r in self.tables['trial_inputs'] if r['trial_id'] == trial]
            self.assertEqual(len(rows), 1)
            self.assertIn(start, rows[0]['processed_path'])
            self.assertEqual(rows[0]['probe_alias'], 'probe_03')
            self.assertEqual(rows[0]['conductivity_basis'], 'specific')
            dataset = self.provenance['datasets'][rows[0]['dataset_id']]
            self.assertFalse(dataset['measurement_timezone'])
            self.assertTrue(dataset['export_created'])
            self.assertFalse(rows[0]['window_start_utc'])
            self.assertFalse(rows[0]['window_end_utc'])

    def test_paired_probes_split_logs_and_shared_recordings_are_retained(self):
        rows = self.tables['trial_inputs']
        july = [r for r in rows if r['trial_id'] == 'NISQ-20260721-T01']
        self.assertEqual({r['probe_alias'] for r in july}, {'probe_01', 'probe_03'})
        self.assertEqual(len({r['dataset_id'] for r in july}), 2)
        for row in july:
            dataset = self.provenance['datasets'][row['dataset_id']]
            self.assertTrue(dataset['first_source_timestamp'].startswith('2026-07-21'))
            self.assertEqual(dataset['measurement_timezone'], 'Pacific Daylight Time')
            self.assertIn('2026-08-', row['processed_path'])  # Export date is not the field date.
        first = [r['dataset_id'] for r in rows if r['trial_id'] == 'NISQ-20250731-T01'
                 and r['probe_alias'] == 'probe_04']
        second = [r['dataset_id'] for r in rows if r['trial_id'] == 'NISQ-20250731-T02'
                  and r['probe_alias'] == 'probe_04']
        self.assertEqual(len(set(first)), 2)
        self.assertTrue(set(first) & set(second))

    def test_original_timestamps_and_cross_probe_calibration_cautions(self):
        rows = self.tables['trial_inputs']
        august = [r for r in rows if r['trial_id'] == 'NISQ-20250808-T01'
                  and r['probe_alias'] == 'probe_04']
        self.assertEqual(len(august), 1)
        self.assertIn('/LiveReadings/', august[0]['processed_path'])
        self.assertIn('09-45-13', august[0]['processed_path'])
        for row, evidence in zip(rows, self.provenance['trial_inputs']):
            if row['trial_id'].startswith('NISQ-20250805-') or row['trial_id'].startswith('NISQ-20250903-'):
                self.assertFalse(row['calibration_id'])
                self.assertTrue(evidence['notebook_calibration_candidates'])
                self.assertEqual(evidence['field_status']['calibration_applicability'],
                                 'known_cross_probe_candidate_withheld')

    def test_uncertain_september_event_stays_unlinked(self):
        rows = [r for r in self.tables['trial_inputs'] if r['trial_id'] == 'NISQ-20260918-T01']
        self.assertTrue(rows)
        self.assertTrue(all(not r['dataset_id'] and r['review_status'] == 'needs_review' for r in rows))

    def test_manifest_matches_current_bytes_and_headers(self):
        manifest = json.loads((RECORDS / 'manifest.json').read_text())
        for name, rows in self.tables.items():
            entry = manifest['tables'][f'{name}.csv']
            self.assertEqual(entry['sha256'], hashlib.sha256((RECORDS / f'{name}.csv').read_bytes()).hexdigest())
            self.assertEqual(entry['rows'], len(rows))
            self.assertEqual(list(rows[0]), manifest['schema_columns'][name])
        self.assertEqual(manifest['provenance_sha256'],
                         hashlib.sha256((RECORDS / 'provenance.json').read_bytes()).hexdigest())


@unittest.skipUnless(os.environ.get('MORA_CHECK_LOCAL_RECORDINGS') == '1',
                     'Set MORA_CHECK_LOCAL_RECORDINGS=1 to check ignored parser outputs')
class LocalRecordingTests(unittest.TestCase):
    def test_registered_files_hashes_measurement_probes_and_channels(self):
        provenance = json.loads((RECORDS / 'provenance.json').read_text())
        rows = read_table('trial_inputs')
        for identity, dataset in provenance['datasets'].items():
            with self.subTest(dataset=identity):
                for path_key, hash_key in [('processed_path', 'processed_sha256'),
                                           ('metadata_path', 'metadata_sha256'),
                                           ('source_path', 'source_sha256')]:
                    path = ROOT / dataset[path_key]
                    self.assertTrue(path.is_file(), path)
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), dataset[hash_key])
                meta = json.loads((ROOT / dataset['metadata_path']).read_text())
                serials = {serial for original, canonical in meta.get('column_map', {}).items()
                           if canonical in ('actual_conductivity_us_cm', 'specific_conductivity_us_cm')
                           for serial in re.findall(r'\((\d{6,7})\)', original)}
                serial = meta.get('embedded_metadata', {}).get('Device Properties', {}).get('Serial Number')
                if serial:
                    serials.add(serial)
                self.assertEqual(serials, {provenance['probe_registry'][dataset['probe_alias']]})
                with (ROOT / dataset['processed_path']).open(newline='') as stream:
                    reader = csv.DictReader(stream)
                    channels = set(reader.fieldnames)
                    self.assertEqual(sum(1 for _ in reader), dataset['row_count'])
                for row in rows:
                    if row['dataset_id'] == identity and row['conductivity_basis']:
                        self.assertIn(f"{row['conductivity_basis']}_conductivity_us_cm", channels)


if __name__ == '__main__':
    unittest.main()
