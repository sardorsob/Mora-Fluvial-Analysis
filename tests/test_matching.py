"""Pairing must preserve uncertainty rather than fill links from date/order alone."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

try:
    from salt_dilution.scripts.processing import matching
except ImportError:
    matching = None


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


class FileFixtures:
    def setUp(self):
        self.assertIsNotNone(matching, 'The pairing module has not been implemented')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.processed = self.root / 'processed'
        self.provenance = {'datasets': {}, 'probe_registry': {'probe_01': '111', 'probe_02': '222'}}

    def recording(self, name='a', serial='111', times=('10:00:00', '10:00:01'), values=(20, 30), **meta):
        path = self.processed / f'{name}.csv'
        rows = [dict(timestamp=f'2026-10-05 {t}', timestamp_utc=f'2026-10-05T{t}+00:00',
                     actual_conductivity_us_cm=v) for t, v in zip(times, values)]
        write_csv(path, rows)
        metadata = dict(source_type='live_reading', instrument_family='aquatroll',
                        site_alias='NISQ', timestamp_basis='explicit_report_numeric_offset',
                        utc_offset_seconds=0, channels=[dict(column='actual_conductivity_us_cm',
                        unit='µS/cm', sensor_serial_number=serial),
                        dict(column='Temperature', unit='C', sensor_serial_number='999')])
        raw=self.root/'raw'/f'{name}.csv'
        raw.parent.mkdir(parents=True,exist_ok=True)
        raw.write_bytes(path.read_bytes())
        metadata['source_file']=str(raw)
        metadata.update(meta)
        path.with_name(f'{name}_metadata.json').write_text(json.dumps(metadata))
        return path

    def inventory(self):
        return matching.inventory_recordings(self.processed, self.provenance, self.root)


class InventoryTests(FileFixtures, unittest.TestCase):
    def test_only_conductivity_channel_identifies_probe(self):
        self.recording()
        rec = self.inventory()[0]
        self.assertEqual(rec['probe_alias'], 'probe_01')
        self.assertEqual(rec['conductivity_bases'], ['actual'])
        self.assertFalse(rec['issues'])

    def test_unknown_units_are_not_silently_stripped(self):
        self.recording(channels=[dict(column='actual_conductivity_us_cm', unit=None, sensor_serial_number='111')])
        self.assertIn('unknown_conductivity_units', self.inventory()[0]['issues'])

    def test_registered_hash_disagreement_is_preserved(self):
        path = self.recording()
        self.provenance['datasets']['D1'] = dict(processed_path='processed/a.csv', processed_sha256='bad', probe_alias='probe_02')
        rec = self.inventory()[0]
        self.assertIn('processed_hash_mismatch', rec['issues'])
        self.assertIn('recorded_probe_alias_disagrees_with_native_label', rec['alias_qualifications'])
        self.assertEqual(rec['probe_alias'], 'probe_01')

    def test_missing_raw_does_not_claim_recovered_metadata(self):
        self.recording(channels=[], source_file='raw/missing.html')
        rec = self.inventory()[0]
        self.assertIn('raw_source_missing', rec['issues'])
        self.assertEqual(rec['conductivity_bases'], [])

    def test_equal_overlaps_and_adjacent_pieces_share_one_logical_recording(self):
        self.recording()
        self.recording('b', times=('10:00:01', '10:00:02'), values=(30, 40))
        groups = matching.reconcile_recordings(self.inventory())
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]['members']), 2)
        self.assertEqual(len(groups[0]['samples']), 3)

    def test_conflicting_overlap_cannot_be_averaged_or_merged(self):
        self.recording()
        self.recording('b', times=('10:00:01', '10:00:02'), values=(99, 40))
        groups = matching.reconcile_recordings(self.inventory())
        self.assertEqual(len(groups), 2)
        self.assertTrue(all('conflicting_overlap' in g['issues'] for g in groups))

    def test_distinct_probes_are_not_deduplicated_by_curve(self):
        self.recording()
        self.recording('b', serial='222')
        self.assertEqual(len(matching.reconcile_recordings(self.inventory())), 2)

    def test_gaps_and_bad_timestamp_order_are_visible(self):
        self.recording(times=('10:00:02','10:00:01'), values=(20,30))
        self.assertIn('nonmonotonic_timestamps', self.inventory()[0]['issues'])
        self.recording('b', times=('12:00:00','12:00:01'))
        self.assertEqual(len(matching.reconcile_recordings(self.inventory())), 2)

    def test_identical_export_members_do_not_create_an_extra_recording(self):
        path = self.recording()
        self.recording('b')
        groups = matching.reconcile_recordings(self.inventory())
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]['samples']), 2)

    def test_native_equal_duplicates_merge_without_registry_aliases(self):
        self.provenance['probe_registry'] = {}
        self.recording()
        self.recording('b')
        groups = matching.reconcile_recordings(self.inventory())
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]['members']), 2)


class AssociationFixtures(FileFixtures):
    def setUp(self):
        super().setUp()
        self.recording()
        self.trials = [dict(trial_id='T01', field_date='2026-10-05', site_alias='NISQ', dump_timestamp_utc='2026-10-05T10:00:00Z')]
        self.preps = [dict(calibration_id='C01', field_date='2026-10-05', site_alias='NISQ')]
        self.fits = [dict(calibration_id='C01', probe_alias='probe_01', conductivity_basis='actual',
                          calibration_basis='mass_concentration', concentration_unit='mg/L',
                          coefficient_unit='(mg/L) / (uS/cm)', k='0.25', status='provisional',
                          fit_method='OLS concentration on conductivity; free intercept')]
        self.provenance['calibrations'] = {'C01': dict(source_trial_id='T01', probe_alias='probe_01')}
        rec = self.inventory()[0]
        self.record_ref = rec['content_ref']
        self.overrides = dict(schema_version=1,
            recordings=[dict(content_ref=self.record_ref,site_alias='NISQ',role='downstream_left',activity='river',evidence='field log',source_ref='notebook#1')],
            recording_links=[dict(trial_id='T01',content_ref=self.record_ref,evidence='explicit source relationship',source_ref='notebook#1')],
            expected_roles=[dict(trial_id='T01',roles=['downstream_left'],evidence='single device',source_ref='notebook#1')])

    def match(self, overrides=True):
        return matching.match_records(self.trials,self.preps,self.fits,self.provenance,
                                       matching.reconcile_recordings(self.inventory()),
                                       self.overrides if overrides else None)

    def native_calibration(self, serial):
        path=self.recording('calibration',serial=serial,times=('11:00:00','11:00:01'))
        rec=next(r for r in self.inventory() if Path(r['path']).name==path.name)
        evidence=self.provenance['calibrations']['C01']
        evidence['_matching_sequence']=dict(status='reproduced',counts={'actual_conductivity_us_cm':2})
        evidence['probe_identity_review']=dict(matches={'actual_conductivity_us_cm':[{}, {}]},
            files=list(rec['files'].values()),basis='electronic_calibration_sequence_and_measured_sensor_identity')



class AssociationTests(AssociationFixtures, unittest.TestCase):
    def test_supported_release_and_k_are_separate_edges(self):
        result = self.match()
        self.assertEqual(result['recording_candidates'][0]['status'], 'supported')
        self.assertEqual(result['calibration_candidates'][0]['status'], 'supported')
        self.assertTrue(result['calibration_candidates'][0]['mass_route_eligible'])
        self.assertEqual(result['pairing_summary'][0]['status'], 'complete_proposal')
        self.assertNotIn('window_start_utc', result['recording_candidates'][0])

    def test_date_and_unique_file_alone_never_complete_pairing(self):
        self.trials[0]['dump_timestamp_utc']=''
        result = self.match(False)
        self.assertEqual(result['recording_candidates'][0]['status'], 'ambiguous')
        self.assertNotEqual(result['pairing_summary'][0]['status'], 'complete_proposal')

    def test_wrong_day_and_wrong_site_are_excluded(self):
        self.trials.extend([dict(self.trials[0],trial_id='T02',field_date='2026-10-06',dump_timestamp_utc=''),
                            dict(self.trials[0],trial_id='T03',site_alias='PAR')])
        result=self.match()
        statuses={r['trial_id']:r['status'] for r in result['pairing_summary']}
        self.assertEqual(statuses['T02'],'unmatched');self.assertEqual(statuses['T03'],'unmatched')

    def test_unknown_clock_remains_ambiguous_despite_reviewed_link(self):
        self.trials[0]['dump_timestamp_utc']=''
        result=self.match()
        self.assertIn('release_clock_unresolved', result['recording_candidates'][0]['reasons'])
        self.assertEqual(result['pairing_summary'][0]['status'],'ambiguous')

    def test_wrong_probe_k_is_not_transferred(self):
        self.native_calibration('222')
        self.fits[0]['probe_alias']='probe_02'
        result=self.match()
        self.assertEqual(result['calibration_candidates'][0]['status'],'conflicting')
        self.assertNotEqual(result['pairing_summary'][0]['status'],'complete_proposal')

    def test_relative_k_is_preserved_without_mass_route_eligibility(self):
        self.fits[0].update(calibration_basis='relative_concentration',concentration_unit='mL/mL',
                            coefficient_unit='(mL/mL) / (uS/cm)')
        edge=self.match()['calibration_candidates'][0]
        self.assertEqual(edge['status'],'supported');self.assertFalse(edge['mass_route_eligible'])

    def test_specific_k_cannot_use_actual_only_recording(self):
        self.fits[0]['conductivity_basis']='specific'
        self.assertIn('conductivity_channel_unavailable', self.match()['calibration_candidates'][0]['reasons'])

    def test_competing_calibrations_are_not_ranked_by_r_squared(self):
        self.preps.append(dict(self.preps[0], calibration_id='C02'))
        self.fits.append(dict(self.fits[0],calibration_id='C02',r_squared='1.0'))
        self.provenance['calibrations']['C02']=dict(source_trial_id='T01',probe_alias='probe_01')
        result=self.match()
        self.assertTrue(all(e['status']=='ambiguous' for e in result['calibration_candidates']))
        self.assertEqual(result['pairing_summary'][0]['status'],'ambiguous')

    def test_missing_release_does_not_shift_later_associations(self):
        self.trials.insert(0,dict(self.trials[0],trial_id='T00',field_date='2026-10-04',dump_timestamp_utc=''))
        result=self.match()
        self.assertEqual([r['status'] for r in result['pairing_summary']],['unmatched','complete_proposal'])

    def test_unknown_bank_count_does_not_block_a_pairing_proposal(self):
        self.overrides.pop('expected_roles')
        self.assertEqual(self.match()['pairing_summary'][0]['status'],'inferred_proposal')

    def test_two_releases_can_share_one_recording_without_creating_events(self):
        self.trials.append(dict(self.trials[0],trial_id='T02',dump_timestamp_utc='2026-10-05T10:00:01Z'))
        self.preps.append(dict(self.preps[0],calibration_id='C02'))
        self.fits.append(dict(self.fits[0],calibration_id='C02'))
        self.provenance['calibrations']['C02']=dict(source_trial_id='T02',probe_alias='probe_01')
        self.overrides['recording_links'].append(dict(self.overrides['recording_links'][0],trial_id='T02'))
        self.overrides['expected_roles'].append(dict(self.overrides['expected_roles'][0],trial_id='T02'))
        result=self.match()
        self.assertEqual(len(result['recording_candidates']),2)
        self.assertEqual({r['logical_recording_id'] for r in result['recording_candidates']},
                         {result['recording_candidates'][0]['logical_recording_id']})
        self.assertEqual([r['status'] for r in result['pairing_summary']],['complete_proposal']*2)

    def test_overrides_reject_unknown_fields_and_need_evidence(self):
        self.overrides['recordings'][0]['magic_clock_fix']=1
        with self.assertRaisesRegex(ValueError,'unknown|Unknown'):
            self.match()


class RunnerTests(AssociationFixtures, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.records=self.root/'records';self.bundle=self.root/'calibration'
        self.bundle.mkdir()
        write_csv(self.records/'trials.csv',self.trials)
        write_csv(self.records/'calibrations.csv',self.preps)
        write_csv(self.records/'trial_inputs.csv',[dict(trial_id='T01',dataset_id='',processed_path='')])
        write_csv(self.records/'calibration_points.csv',[dict(calibration_id='C01',step_no='0',probe_alias='probe_01',actual_conductivity_us_cm='20')])
        (self.records/'provenance.json').write_text(json.dumps(self.provenance))
        config=self.root/'salt_dilution/config/procedure_versions.json';config.parent.mkdir(parents=True);config.write_text('{}')
        write_csv(self.bundle/'calibration_fits.csv',self.fits)
        inputs=[dict(path=str(p.relative_to(self.root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                for p in [self.records/'calibrations.csv',self.records/'calibration_points.csv',self.records/'provenance.json',config]]
        self.runinfo=dict(inputs=inputs,outputs=[dict(path='calibration_fits.csv',sha256=hashlib.sha256((self.bundle/'calibration_fits.csv').read_bytes()).hexdigest())])
        (self.bundle/'run_info.json').write_text(json.dumps(self.runinfo))
        self.override_file=self.root/'overrides.json';self.override_file.write_text(json.dumps(self.overrides))

    def run_matcher(self, name='output'):
        return matching.run_matching(self.records,self.processed,self.bundle,self.root/name,
                                     root=self.root,overrides_path=self.override_file)

    def test_run_is_deterministic_and_preserves_sources(self):
        paths=list(self.records.iterdir())+list(self.processed.iterdir())+list(self.bundle.iterdir())
        before={p:p.read_bytes() for p in paths}
        self.run_matcher('one');self.run_matcher('two')
        for name in ('recording_candidates.csv','calibration_candidates.csv','pairing_summary.csv'):
            self.assertEqual((self.root/'one'/name).read_bytes(),(self.root/'two'/name).read_bytes())
        self.assertEqual(before,{p:p.read_bytes() for p in paths})
        summary=list(csv.DictReader((self.root/'one/pairing_summary.csv').read_text().splitlines()))
        self.assertEqual(summary[0]['status'],'complete_proposal')
        run=json.loads((self.root/'one/run_info.json').read_text())
        self.assertEqual(run['release_count'],1)
        self.assertTrue(run['outputs']);self.assertTrue(run['inputs'])

    def test_changed_calibration_input_stops_without_publishing(self):
        with (self.records/'calibrations.csv').open('a') as stream:stream.write('\n')
        with self.assertRaisesRegex(ValueError,'[Ss]tale|hash'):
            self.run_matcher()
        self.assertFalse((self.root/'output').exists())

    def test_changed_fit_table_stops_without_publishing(self):
        with (self.bundle/'calibration_fits.csv').open('a') as stream:stream.write('\n')
        with self.assertRaisesRegex(ValueError,'hash'):
            self.run_matcher()

    def test_nonempty_output_is_not_overwritten(self):
        out=self.root/'output';out.mkdir();(out/'keep').write_text('keep me')
        with self.assertRaises(FileExistsError):self.run_matcher()
        self.assertEqual((out/'keep').read_text(),'keep me')

    def test_duplicate_authoritative_ids_are_rejected(self):
        write_csv(self.records/'trials.csv',self.trials*2)
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            self.run_matcher()

    def test_unknown_override_reference_is_rejected(self):
        self.overrides['recording_links'][0]['content_ref']='missing'
        self.override_file.write_text(json.dumps(self.overrides))
        with self.assertRaisesRegex(ValueError,'Unknown'):
            self.run_matcher()

    def test_output_symlink_is_rejected_without_touching_destination(self):
        target=self.root/'target';target.mkdir()
        (self.root/'output').symlink_to(target,target_is_directory=True)
        with self.assertRaises((ValueError,FileExistsError)):
            self.run_matcher()
        self.assertTrue((self.root/'output').is_symlink())
        self.assertEqual(list(target.iterdir()),[])

    def test_blank_trial_without_recording_still_has_summary(self):
        self.trials.append(dict(self.trials[0],trial_id='T02',field_date='2026-10-06',dump_timestamp_utc=''))
        write_csv(self.records/'trials.csv',self.trials)
        self.run_matcher()
        rows=list(csv.DictReader((self.root/'output/pairing_summary.csv').read_text().splitlines()))
        self.assertEqual([(r['trial_id'],r['status']) for r in rows],[('T01','complete_proposal'),('T02','unmatched')])

    def test_missing_current_curated_link_is_not_ignored(self):
        write_csv(self.records/'trial_inputs.csv',[dict(trial_id='T01',dataset_id='new-incorrect-link',processed_path='processed/missing.csv')])
        self.run_matcher()
        rows=list(csv.DictReader((self.root/'output/pairing_summary.csv').read_text().splitlines()))
        self.assertNotEqual(rows[0]['status'],'complete_proposal')
        self.assertIn('curated',rows[0]['reasons'])


    def test_current_specific_claim_cannot_be_satisfied_by_actual_fit(self):
        path=self.processed/'a.csv'
        frame=pd.read_csv(path);frame['specific_conductivity_us_cm']=frame['actual_conductivity_us_cm'];frame.to_csv(path,index=False)
        meta_path=self.processed/'a_metadata.json';meta=json.loads(meta_path.read_text())
        meta['channels'].append(dict(column='specific_conductivity_us_cm',unit='µS/cm',sensor_serial_number='111'))
        meta_path.write_text(json.dumps(meta))
        ref=self.inventory()[0]['content_ref']
        self.overrides['recordings'][0]['content_ref']=ref;self.overrides['recording_links'][0]['content_ref']=ref
        self.override_file.write_text(json.dumps(self.overrides))
        write_csv(self.records/'trial_inputs.csv',[dict(trial_id='T01',dataset_id=ref,processed_path='processed/a.csv',
            calibration_id='C01',conductivity_basis='specific',probe_alias='probe_01')])
        self.run_matcher()
        rows=list(csv.DictReader((self.root/'output/pairing_summary.csv').read_text().splitlines()))
        self.assertNotEqual(rows[0]['status'],'complete_proposal')
        self.assertIn('curated_calibration',rows[0]['reasons'])


class SafetyTests(AssociationFixtures, unittest.TestCase):
    def test_no_numpy_timedelta_warning_in_clock_comparison(self):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('error', DeprecationWarning)
            self.assertEqual(self.match()['pairing_summary'][0]['status'],'complete_proposal')

    def test_conflicting_samples_in_same_export_are_never_supported(self):
        self.recording(times=('10:00:00','10:00:00'),values=(20,99))
        ref=self.inventory()[0]['content_ref']
        self.overrides['recordings'][0]['content_ref']=ref
        self.overrides['recording_links'][0]['content_ref']=ref
        self.assertNotEqual(self.match()['recording_candidates'][0]['status'],'supported')

    def test_reviewed_links_do_not_override_a_hash_conflict(self):
        self.provenance['datasets'][self.record_ref]=dict(processed_path='processed/a.csv',processed_sha256='bad',probe_alias='probe_01')
        self.assertEqual(self.match()['recording_candidates'][0]['status'],'conflicting')

    def test_paired_devices_do_not_borrow_a_single_probes_fit(self):
        self.native_calibration('111')
        self.recording('b',serial='222')
        rec=next(r for r in self.inventory() if r['probe_alias']=='probe_02')
        self.overrides['recordings'].append(dict(self.overrides['recordings'][0],content_ref=rec['content_ref'],role='downstream_right'))
        self.overrides['recording_links'].append(dict(self.overrides['recording_links'][0],content_ref=rec['content_ref']))
        self.overrides['expected_roles'][0]['roles'].append('downstream_right')
        result=self.match()
        self.assertNotEqual(result['pairing_summary'][0]['status'],'complete_proposal')
        self.assertTrue(any(c['status']=='conflicting' for c in result['calibration_candidates']))
        self.assertTrue(result['pairing_summary'][0]['identity_review_required'])


class MetadataRegressionTests(FileFixtures, unittest.TestCase):
    def test_csv_conductivity_header_serial_is_not_lost(self):
        self.recording(channels=[dict(column='actual_conductivity_us_cm',unit='µS/cm',
                                     source_column='Actual Conductivity (µS/cm) (111)')])
        self.assertEqual(self.inventory()[0]['probe_alias'],'probe_01')

    def test_winsitu_device_properties_identify_sensor_not_comms_adapter(self):
        self.recording(channels=[dict(column='actual_conductivity_us_cm',unit='µS/cm')],
                       embedded_metadata={'Device Properties':{'Device':'Aqua TROLL 200','Serial Number':'111'}})
        self.assertEqual(self.inventory()[0]['probe_alias'],'probe_01')

    def test_unobserved_identity_is_missing_not_a_conflict(self):
        self.recording(channels=[dict(column='actual_conductivity_us_cm',unit='µS/cm')])
        self.provenance['datasets']['D1']=dict(processed_path='processed/a.csv',probe_alias='probe_01')
        rec=self.inventory()[0]
        self.assertIn('unknown_probe_identity',rec['issues'])
        self.assertNotIn('probe_identity_conflict',rec['issues'])

    def test_field_note_tables_are_not_instrument_recordings(self):
        self.recording()
        write_csv(self.processed/'field_notes/trials.csv',[dict(trial_id='T01',timestamp_utc='',notes='not a stream')])
        self.assertEqual(len(self.inventory()),1)


class ReviewRegressionTests(AssociationFixtures, unittest.TestCase):
    def test_site_override_does_not_erase_an_observed_contradiction(self):
        path=self.processed/'a_metadata.json'
        meta=json.loads(path.read_text());meta['site_alias']='PAR';path.write_text(json.dumps(meta))
        result=self.match()
        self.assertEqual(result['recording_candidates'][0]['status'],'conflicting')
        self.assertNotEqual(result['pairing_summary'][0]['status'],'complete_proposal')

    def test_channel_and_device_properties_contradiction_is_visible(self):
        path=self.processed/'a_metadata.json'
        meta=json.loads(path.read_text());meta['embedded_metadata']={'Device Properties':{'Device':'Aqua TROLL 200','Serial Number':'222'}}
        path.write_text(json.dumps(meta))
        self.assertIn('multiple_conductivity_devices',self.inventory()[0]['issues'])
        self.assertNotEqual(self.match()['pairing_summary'][0]['status'],'complete_proposal')

    def test_missing_raw_pointer_is_not_a_complete_pairing(self):
        path=self.processed/'a_metadata.json'
        meta=json.loads(path.read_text());meta.pop('source_file');path.write_text(json.dumps(meta))
        self.assertIn('raw_source_unavailable',self.inventory()[0]['issues'])
        self.assertNotEqual(self.match()['pairing_summary'][0]['status'],'complete_proposal')

    def test_new_middle_piece_bridges_two_preexisting_groups(self):
        self.recording('b',times=('10:00:04','10:00:05'),values=(50,60))
        self.recording('c',times=('10:00:02','10:00:03'),values=(35,40))
        groups=matching.reconcile_recordings(self.inventory())
        self.assertEqual(len(groups),1)
        self.assertEqual(len(groups[0]['members']),3)
        self.assertEqual(len(groups[0]['samples']),6)


class ClockRegressionTests(AssociationFixtures, unittest.TestCase):
    def test_metadata_utc_must_agree_with_explicit_numeric_offset(self):
        path=self.processed/'a_metadata.json';meta=json.loads(path.read_text())
        meta['utc_offset_seconds']=-25200;path.write_text(json.dumps(meta))
        self.assertIn('utc_clock_conflict',self.inventory()[0]['issues'])
        self.assertNotEqual(self.match()['pairing_summary'][0]['status'],'complete_proposal')

    def test_clock_corrections_cannot_be_tuned_independently_per_event_file(self):
        self.recording('b',times=('12:00:00','12:00:01'))
        rec=next(r for r in self.inventory() if Path(r['path']).name=='b.csv')
        self.overrides['recordings'][0].update(clock_correction_seconds=60,clock_basis='reviewed_clock')
        self.overrides['recordings'].append(dict(self.overrides['recordings'][0],content_ref=rec['content_ref'],clock_correction_seconds=120))
        with self.assertRaisesRegex(ValueError,'[Cc]lock'):
            self.match()


class NonRiverTests(FileFixtures, unittest.TestCase):
    def test_known_calibration_table_does_not_require_stream_metadata_recovery(self):
        self.recording(source_type='calibration',channels=[])
        rec=self.inventory()[0]
        self.assertEqual(rec['activity'],'calibration')
        self.assertNotIn('raw_recovery_failed',rec['issues'])


class ChronologyFixtures(AssociationFixtures):
    def setUp(self):
        super().setUp()
        self.trials[0]['dump_timestamp_utc']=''
        self.provenance['trials']={'T01':{'source_record':{'injection_time_local':'10:00:00','injection_time_raw':'10:00:00','timezone_label_raw':'PST'}}}


class ChronologyTests(ChronologyFixtures, unittest.TestCase):
    def test_local_protocol_match_does_not_require_utc_or_bank_review(self):
        result=self.match(False)
        edge=result['recording_candidates'][0]
        self.assertEqual(edge['status'],'inferred')
        self.assertTrue(edge['selected_for_pairing'])
        self.assertEqual(edge['time_evidence']['release_utc'],'')
        self.assertEqual(result['pairing_summary'][0]['status'],'inferred_proposal')
        self.assertFalse(result['pairing_summary'][0]['scientifically_accepted'])

    def test_multiple_releases_in_continuous_log_keep_distinct_anchors(self):
        self.trials.append(dict(self.trials[0],trial_id='T02'))
        self.provenance['trials']['T02']={'source_record':{'injection_time_local':'10:00:01'}}
        result=self.match(False)
        selected=[e for e in result['recording_candidates'] if e.get('selected_for_pairing')]
        self.assertEqual(len(selected),2)
        self.assertEqual(len({e['logical_recording_id'] for e in selected}),1)
        self.assertEqual({e['chronology_evidence']['release_clock'] for e in selected},{'2026-10-05 10:00:00','2026-10-05 10:00:01'})

    def test_missing_recording_does_not_shift_later_trial(self):
        self.recording('b',times=('12:00:00','12:00:01'))
        self.trials += [dict(self.trials[0],trial_id='T02'),dict(self.trials[0],trial_id='T03')]
        self.provenance['trials'].update(T02={'source_record':{'injection_time_local':'11:00:00'}},T03={'source_record':{'injection_time_local':'12:00:00'}})
        result=self.match(False)
        selected=[e for e in result['recording_candidates'] if e.get('selected_for_pairing')]
        self.assertEqual({e['trial_id'] for e in selected},{'T01','T03'})

    def test_ids_are_not_used_as_clock_order(self):
        self.recording('b',times=('12:00:00','12:00:01'))
        self.trials.append(dict(self.trials[0],trial_id='T00'))
        self.provenance['trials']['T00']={'source_record':{'injection_time_local':'12:00:00'}}
        selected=[e for e in self.match(False)['recording_candidates'] if e.get('selected_for_pairing')]
        first=next(e for e in selected if e['trial_id']=='T01');last=next(e for e in selected if e['trial_id']=='T00')
        self.assertEqual(first['chronology_evidence']['acquisition_start_local'],'2026-10-05 10:00:00')
        self.assertEqual(last['chronology_evidence']['acquisition_start_local'],'2026-10-05 12:00:00')

    def test_large_break_creates_acquisition_segments_not_analysis_windows(self):
        self.recording(times=('10:00:00','10:00:01','12:00:00','12:00:01'),values=(20,30,20,30))
        self.trials.append(dict(self.trials[0],trial_id='T02'))
        self.provenance['trials']['T02']={'source_record':{'injection_time_local':'12:00:00'}}
        selected=[e for e in self.match(False)['recording_candidates'] if e.get('selected_for_pairing')]
        self.assertEqual(len(selected),2)
        self.assertEqual(len({e['logical_recording_id'] for e in selected}),2)
        self.assertTrue(all('window_start_utc' not in e for e in selected))

    def test_overlapping_alternatives_for_same_probe_remain_ambiguous(self):
        self.recording('b',times=('09:59:59','10:00:02'),values=(21,29))
        result=self.match(False)
        self.assertFalse(any(e.get('selected_for_pairing') for e in result['recording_candidates']))
        self.assertEqual(result['pairing_summary'][0]['status'],'ambiguous')

    def test_missing_probe_fit_does_not_hide_recording_inference(self):
        self.fits[0]['probe_alias']='probe_02'
        result=self.match(False)
        self.assertEqual(result['recording_candidates'][0]['status'],'inferred')
        self.assertEqual(result['pairing_summary'][0]['status'],'inferred_proposal')

    def test_uncertain_written_clock_is_not_made_exact(self):
        self.provenance['trials']['T01']['source_record']['injection_time_local']=''
        self.provenance['trials']['T01']['source_record']['injection_time_raw']='10:00?'
        self.assertFalse(any(e.get('selected_for_pairing') for e in self.match(False)['recording_candidates']))


class ChronologyReviewTests(ChronologyFixtures, unittest.TestCase):
    def test_reviewed_clock_correction_is_applied_before_inference(self):
        self.trials[0]['dump_timestamp_utc']='2026-10-05T10:00:00Z'
        self.overrides['recordings'][0].update(clock_correction_seconds=3600,clock_basis='clock_audit')
        result=self.match(True)
        self.assertFalse(any(e.get('selected_for_pairing') for e in result['recording_candidates']))
        self.assertNotEqual(result['pairing_summary'][0]['status'],'inferred_proposal')

    def test_reviewed_notebook_offset_is_not_ignored(self):
        self.overrides['trial_clocks']=[dict(trial_id='T01',utc_offset_seconds=-3600,evidence='clock audit',source_ref='field#1')]
        result=self.match(True)
        self.assertFalse(any(e.get('selected_for_pairing') for e in result['recording_candidates']))

    def test_curated_claim_is_compared_with_selected_session(self):
        self.recording('b',times=('12:00:00','12:00:01'))
        late=next(r for r in self.inventory() if Path(r['path']).name=='b.csv')
        claims=[dict(trial_id='T01',dataset_id=late['content_ref'],processed_path=late['path'])]
        result=matching.match_records(self.trials,self.preps,self.fits,self.provenance,matching.reconcile_recordings(self.inventory()),associations=claims)
        self.assertNotEqual(result['pairing_summary'][0]['status'],'inferred_proposal')
        self.assertIn('curated_recording_differs_from_protocol_pairing',result['pairing_summary'][0]['reasons'])

    def test_known_expected_second_role_still_has_to_be_accounted_for(self):
        self.overrides['expected_roles'][0]['roles']=['downstream_left','downstream_right']
        self.overrides['recording_links']=[]
        result=self.match(True)
        self.assertEqual(result['pairing_summary'][0]['status'],'partial')
        self.assertIn('missing_role:downstream_right',result['pairing_summary'][0]['reasons'])

    def test_selected_supported_pair_keeps_exact_k_references(self):
        self.trials[0]['dump_timestamp_utc']='2026-10-05T10:00:00Z'
        result=self.match(True)
        self.assertTrue(result['pairing_summary'][0]['selected_calibration_edge_ids'])


class ChronologyParameterTests(ChronologyFixtures, unittest.TestCase):
    def test_clear_break_assignments_are_stable_across_gap_parameters(self):
        self.recording(times=('10:00:00','10:00:01','12:00:00','12:00:01'),values=(20,30,20,30))
        self.trials.append(dict(self.trials[0],trial_id='T02'))
        self.provenance['trials']['T02']={'source_record':{'injection_time_local':'12:00:00'}}
        for gap,factor in ((30,5),(60,10),(120,20)):
            result=matching.match_records(self.trials,self.preps,self.fits,self.provenance,matching.reconcile_recordings(self.inventory()),gap_seconds=gap,gap_factor=factor)
            selected=[e for e in result['recording_candidates'] if e['selected_for_pairing']]
            self.assertEqual([(e['trial_id'],e['chronology_evidence']['acquisition_start_local']) for e in selected],
                             [('T01','2026-10-05 10:00:00'),('T02','2026-10-05 12:00:00')])

    def test_invalid_tolerances_are_not_silently_accepted(self):
        with self.assertRaisesRegex(ValueError,'finite and positive'):
            matching.match_records(self.trials,self.preps,self.fits,self.provenance,matching.reconcile_recordings(self.inventory()),tolerance_seconds=float('nan'))


class ExistingSourceLinkTests(AssociationFixtures, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.trials[0]['dump_timestamp_utc']=''
        self.provenance['trials']={'T01':{'source_record':{'injection_time_raw':'10:00?'}}}
        rec=self.inventory()[0]
        self.provenance['datasets']['D1']=dict(processed_path='processed/a.csv',probe_alias='probe_01',
            processed_sha256=rec['files']['processed']['sha256'],metadata_sha256=rec['files']['metadata']['sha256'],
            source_sha256=rec['files']['raw']['sha256'])
        self.claim=dict(trial_id='T01',dataset_id='D1',processed_path='processed/a.csv',
            calibration_id='C01',probe_alias='probe_01',conductivity_basis='actual')
        self.provenance['trial_inputs']=[dict(csv_row_number=2,trial_id='T01',dataset_id='D1',
            evidence=['notebook#page=1; recorded device and event'],
            field_status={'recording_identity':'confirmed_file_and_probe; scientific_use_pending'})]

    def reconcile(self, claims=None):
        return matching.match_records(self.trials,self.preps,self.fits,self.provenance,
            matching.reconcile_recordings(self.inventory()),associations=[self.claim] if claims is None else claims)

    def test_source_link_pairs_uncertain_clock_without_inventing_timestamp(self):
        result=self.reconcile()
        row=result['trial_associations'][0]
        self.assertEqual(row['recording_link_status'],'source_confirmed')
        self.assertEqual(row['calibration_link_status'],'source_linked')
        self.assertEqual(row['applicability_status'],'source_linked_identity_unverified')
        self.assertEqual(result['pairing_summary'][0]['status'],'inferred_proposal')
        selected=[e for e in result['recording_candidates'] if e['selected_for_pairing']]
        self.assertEqual(len(selected),1)
        self.assertEqual(selected[0]['time_evidence']['release_utc'],'')
        self.assertEqual(self.provenance['trials']['T01']['source_record']['injection_time_raw'],'10:00?')

    def test_wrong_current_path_does_not_inherit_old_confirmation(self):
        self.claim['processed_path']='processed/missing.csv'
        row=self.reconcile()['trial_associations'][0]
        self.assertEqual(row['recording_link_status'],'conflicting')
        self.assertIn('current_dataset_path_conflict',row['reasons'])

    def test_hash_mismatch_blocks_source_promotion(self):
        self.provenance['datasets']['D1']['source_sha256']='bad'
        result=self.reconcile()
        self.assertEqual(result['trial_associations'][0]['recording_link_status'],'conflicting')
        self.assertFalse(any(e['selected_for_pairing'] for e in result['recording_candidates']))

    def test_cross_probe_is_known_link_with_unverified_applicability(self):
        self.fits[0]['probe_alias']='probe_02'
        self.provenance['calibrations']['C01']['probe_alias']='probe_02'
        row=self.reconcile()['trial_associations'][0]
        self.assertEqual(row['calibration_link_status'],'source_linked')
        self.assertEqual(row['calibration_probe_alias'],'probe_02')
        self.assertEqual(row['recording_probe_alias'],'probe_01')
        self.assertEqual(row['k'],'0.25')
        self.assertEqual(row['applicability_status'],'source_linked_identity_unverified')

    def test_no_source_relationship_cannot_be_created_from_same_day(self):
        self.provenance['calibrations']['C01']['source_trial_id']='other'
        row=self.reconcile()['trial_associations'][0]
        self.assertEqual(row['calibration_link_status'],'conflicting')
        self.assertNotEqual(row['applicability_status'],'same_probe_and_channel')

    def test_ambiguous_preparations_are_retained_without_best_fit_selection(self):
        self.preps.append(dict(self.preps[0],calibration_id='C02'))
        self.fits.append(dict(self.fits[0],calibration_id='C02',k='0.30'))
        self.provenance['calibrations']['C02']=dict(self.provenance['calibrations']['C01'])
        result=self.reconcile([self.claim,dict(self.claim,calibration_id='C02')])
        self.assertEqual({r['calibration_id'] for r in result['trial_associations']},{'C01','C02'})
        self.assertTrue(all(r['applicability_status']=='competing_calibrations' for r in result['trial_associations']))
        self.assertNotEqual(result['pairing_summary'][0]['status'],'inferred_proposal')

    def test_source_relationship_does_not_choose_between_acquisition_segments(self):
        self.recording(times=('10:00:00','10:00:01','12:00:00','12:00:01'),values=(20,30,20,30))
        rec=self.inventory()[0]
        for kind,key in [('processed','processed_sha256'),('metadata','metadata_sha256'),('raw','source_sha256')]:
            self.provenance['datasets']['D1'][key]=rec['files'][kind]['sha256']
        result=self.reconcile()
        self.assertFalse(any(e['selected_for_pairing'] for e in result['recording_candidates']))
        self.assertIn('acquisition_segment_unresolved',result['trial_associations'][0]['reasons'])

    def test_explicit_clock_contradiction_is_not_overridden_by_source_link(self):
        self.trials[0]['dump_timestamp_utc']='2026-10-05T15:00:00Z'
        result=self.reconcile()
        self.assertFalse(any(e['selected_for_pairing'] for e in result['recording_candidates']))

    def test_missing_native_probe_does_not_inherit_registered_identity(self):
        path=self.processed/'a_metadata.json'
        meta=json.loads(path.read_text())
        meta['channels'][0].pop('sensor_serial_number')
        path.write_text(json.dumps(meta))
        self.provenance['datasets']['D1']['metadata_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        self.claim['probe_alias']=''
        result=self.reconcile()
        self.assertEqual(result['trial_associations'][0]['recording_link_status'],'unresolved')
        self.assertFalse(any(e['selected_for_pairing'] for e in result['recording_candidates']))

    def test_offset_override_cannot_make_question_marked_time_exact(self):
        for local in ('','10:00:00'):
            with self.subTest(local=local):
                self.provenance['trials']['T01']['source_record']['injection_time_local']=local
                overrides=matching._validate_overrides(dict(schema_version=1,trial_clocks=[dict(
                    trial_id='T01',utc_offset_seconds=0,evidence='timezone only',source_ref='notebook#1')]),
                    self.trials,self.preps,matching.reconcile_recordings(self.inventory()))
                value,_=matching._release_time(self.trials[0],self.provenance,overrides)
                self.assertIsNone(value)

    def test_missing_measurements_do_not_erase_known_file_identity(self):
        self.recording(values=(20,float('nan')))
        rec=self.inventory()[0]
        for kind,key in [('processed','processed_sha256'),('metadata','metadata_sha256'),('raw','source_sha256')]:
            self.provenance['datasets']['D1'][key]=rec['files'][kind]['sha256']
        result=self.reconcile()
        row=result['trial_associations'][0]
        self.assertEqual(row['recording_link_status'],'source_confirmed')
        self.assertEqual(row['applicability_status'],'evidence_requires_review')
        self.assertIn('nonfinite_conductivity',row['reasons'])
        self.assertFalse(any(e['selected_for_pairing'] for e in result['recording_candidates']))


    def test_guessed_current_recording_alias_does_not_break_confirmed_file_link(self):
        self.claim['probe_alias']='probe_02'
        result=self.reconcile()
        self.assertEqual(result['trial_associations'][0]['recording_link_status'],'source_confirmed')
        self.assertEqual(result['pairing_summary'][0]['status'],'inferred_proposal')

    def test_native_serial_does_not_require_a_registry_alias(self):
        self.provenance['probe_registry']={}
        result=self.reconcile()
        self.assertEqual(result['trial_associations'][0]['recording_device_serial'],'111')
        self.assertEqual(result['pairing_summary'][0]['status'],'inferred_proposal')


class PlaceholderAliasTests(AssociationFixtures, unittest.TestCase):
    def river_k(self):
        result=self.match()
        return result,next(c for c in result['calibration_candidates'] if c['recording_edge_id'].endswith(result['recording_candidates'][0]['logical_recording_id']))

    def test_placeholder_difference_does_not_block_source_linked_k(self):
        self.fits[0]['probe_alias']='probe_02'
        self.provenance['calibrations']['C01']['probe_alias']='probe_02'
        result,edge=self.river_k()
        self.assertEqual(edge['status'],'supported')
        self.assertEqual(edge['identity_status'],'unverified')
        self.assertEqual(result['pairing_summary'][0]['status'],'complete_proposal')
        self.assertTrue(result['pairing_summary'][0]['identity_review_required'])
        self.assertFalse(result['pairing_summary'][0]['scientifically_accepted'])

    def test_blank_fit_alias_still_pairs_by_preparation_and_channel(self):
        self.fits[0]['probe_alias']=''
        self.provenance['calibrations']['C01']['probe_alias']=''
        _,edge=self.river_k()
        self.assertEqual(edge['status'],'supported')
        self.assertEqual(edge['identity_status'],'unverified')

    def test_equal_placeholder_aliases_do_not_establish_physical_identity(self):
        _,edge=self.river_k()
        self.assertEqual(edge.get('identity_status'),'unverified')
        self.assertEqual(edge.get('calibration_device_serial'),'')

    def test_empty_sequence_does_not_establish_native_identity(self):
        self.native_calibration('111')
        evidence = self.provenance['calibrations']['C01']
        evidence['probe_identity_review']['matches'] = {'actual_conductivity_us_cm': []}
        evidence['_matching_sequence']['counts'] = {'actual_conductivity_us_cm': 0}
        result, edge = self.river_k()
        self.assertEqual(edge['identity_status'], 'unverified')
        self.assertTrue(result['pairing_summary'][0]['identity_review_required'])
        evidence['probe_identity_review']['tolerance_us_cm'] = 0
        checked = matching._sequence_evidence('C01', evidence, [], self.root)
        self.assertEqual(checked['status'], 'unavailable')

    def test_native_calibration_conflict_is_preserved_even_when_aliases_agree(self):
        self.native_calibration('222')
        result,edge=self.river_k()
        self.assertEqual(edge['status'],'conflicting')
        self.assertEqual(edge['identity_status'],'native_conflict')
        self.assertEqual(edge['calibration_device_serial'],'222')
        self.assertEqual(edge['recording_device_serial'],'111')
        self.assertNotEqual(result['pairing_summary'][0]['status'],'complete_proposal')

    def test_native_calibration_agreement_survives_disagreeing_placeholders(self):
        self.native_calibration('111')
        self.fits[0]['probe_alias']='probe_02'
        self.provenance['calibrations']['C01']['probe_alias']='probe_02'
        _,edge=self.river_k()
        self.assertEqual(edge['status'],'supported')
        self.assertEqual(edge['identity_status'],'native_match')
        self.assertEqual(edge['calibration_device_serial'],'111')

    def test_stale_native_identity_pin_is_not_downgraded_to_placeholder(self):
        self.native_calibration('111')
        self.provenance['calibrations']['C01']['probe_identity_review']['files'][0]['sha256']='bad'
        _,edge=self.river_k()
        self.assertEqual(edge['status'],'conflicting')
        self.assertIn('native_identity_evidence_conflict',edge['reasons'])

    def test_same_preparation_multiple_alias_series_is_ambiguous(self):
        self.fits.append(dict(self.fits[0],probe_alias='probe_02',k='0.3'))
        result=self.match()
        self.assertTrue(all(c['status']=='ambiguous' for c in result['calibration_candidates']))
        self.assertTrue(all('competing_calibration_series' in c['reasons'] for c in result['calibration_candidates']))
