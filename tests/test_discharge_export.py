"""The analysis handoff must preserve estimates, blanks and scientific limits."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from salt_dilution.scripts.processing import export_discharge as export


def save_table(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


class TableTests(unittest.TestCase):
    def setUp(self):
        self.master = [dict(trial_id='T1',category='computed',q_primary_m3_s='2.043823838972579',q_primary_l_s='2043.8238389725793',missing_requirements='["field_acceptance"]'),
                       dict(trial_id='T2',category='blocked_tail_not_settled',q_primary_m3_s='',q_primary_l_s='',missing_requirements='["tail_capture"]'),
                       dict(trial_id='T3',category='relative_basis_not_mass_route',q_primary_m3_s='',q_primary_l_s='',missing_requirements='["relative_route"]')]
        self.estimates = [dict(trial_id='T1',estimate_role='primary',q_m3_s='2.043823838972579',q_l_s='2043.8238389725793',scientifically_accepted='false',flags='["mixing_not_independently_validated"]')]
        self.review = [dict(trial_id='T1',recommendation='source_background_reconciliation_required',window_numerical_review='completed',local_sensitivity_min_relative='-0.0283',local_sensitivity_max_relative='0.0283',remaining_evidence_gaps='["notebook_background_disagrees_with_recording"]'),
                       dict(trial_id='T2',recommendation='not_calculable_from_current_capture',window_numerical_review='blocked_capture_review_completed',local_sensitivity_min_relative='',local_sensitivity_max_relative='',remaining_evidence_gaps='["tail_not_settled"]')]

    def test_complete_join_keeps_exact_q_and_blanks(self):
        before=copy.deepcopy((self.master,self.estimates,self.review))
        result=export.assemble_release_table(self.master,self.estimates,self.review)
        self.assertEqual(len(result),3)
        self.assertEqual(result[0]['q_primary_m3_s'],'2.043823838972579')
        self.assertEqual(result[1]['q_primary_m3_s'],'')
        self.assertEqual(result[2]['q_primary_m3_s'],'')
        self.assertTrue(all(not r['case_closed_for_current_data'] for r in result))
        self.assertTrue(all(r['scientifically_accepted'] is False for r in result))
        self.assertEqual(result[1]['case_disposition'],'not_estimable_capture')
        self.assertEqual(result[2]['case_disposition'],'relative_route_out_of_scope')
        self.assertEqual((self.master,self.estimates,self.review),before)

    def test_source_flag_stays_with_proposed_q(self):
        row=export.assemble_release_table(self.master,self.estimates,self.review)[0]
        self.assertTrue(row['source_background_discrepancy'])
        self.assertEqual(row['analysis_status'],'proposed_with_source_discrepancy')
        self.assertEqual(row['window_numerical_review'],'completed')
        self.assertFalse(row['user_window_signoff'])

    def test_duplicate_keys_and_wrong_q_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            export.assemble_release_table(self.master+[self.master[0]],self.estimates,self.review)
        self.estimates[0]['q_m3_s']='9'
        with self.assertRaisesRegex(ValueError,'Q'):
            export.assemble_release_table(self.master,self.estimates,self.review)

    def test_unknown_review_key_and_missing_computed_primary_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'release'):
            export.assemble_release_table(self.master,self.estimates,self.review+[dict(self.review[0],trial_id='unknown')])
        with self.assertRaisesRegex(ValueError,'primary'):
            export.assemble_release_table(self.master,[],self.review)

    def test_comparison_rows_are_not_additional_primary_releases(self):
        self.estimates.append(dict(self.estimates[0],estimate_role='comparison_channel',q_m3_s='2.18'))
        result=export.assemble_release_table(self.master,self.estimates,self.review)
        self.assertEqual(sum(r['case_disposition']=='estimated_proposed' for r in result),1)

    def test_new_blocking_reason_remains_an_open_recovery_case(self):
        self.master[1]['category']='blocked_solution_volume_source_unresolved'
        row=export.assemble_release_table(self.master,self.estimates,self.review)[1]
        self.assertEqual(row['case_disposition'],'not_estimated')
        self.assertFalse(row['case_closed_for_current_data'])

    def test_unknown_comparison_release_cannot_escape_accounting(self):
        self.estimates.append(dict(self.estimates[0],trial_id='unknown',estimate_role='comparison_channel'))
        with self.assertRaisesRegex(ValueError,'release'):
            export.assemble_release_table(self.master,self.estimates,self.review)


class BundleTests(unittest.TestCase):
    def setUp(self):
        TableTests.setUp(self)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.sources={name:self.root/name for name in ('mass','audit','review','reuse')}
        for p in self.sources.values():p.mkdir()
        save_table(self.sources['mass']/'discharge_estimates.csv',self.estimates)
        save_table(self.sources['audit']/'discharge_by_release.csv',self.master)
        save_table(self.sources['review']/'review_by_release.csv',self.review)
        for group,files in export.COPY_FILES.items():
            for source,_ in files:
                p=self.sources[group]/source
                if not p.exists():p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}\n' if p.suffix=='.json' else 'trial_id\n')
        for group in ('mass','review','reuse'):
            p=self.sources[group]/'figures/example.png';p.parent.mkdir();p.write_bytes(b'fixture-image-bytes')
        self.seal()

    def seal(self):
        for group in ('reuse','mass','audit','review'):
            p=self.sources[group]
            outputs=[dict(path=str(f.relative_to(p)),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in p.rglob('*') if f.is_file() and f.name!='run_info.json']
            inputs=[]
            if group in ('mass','audit','review'):
                source=self.sources['reuse' if group=='mass' else 'mass']/'run_info.json'
                inputs=[dict(path=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest())]
            (p/'run_info.json').write_text(json.dumps(dict(inputs=inputs,outputs=outputs)))

    def run_export(self, output=None):
        return export.run_export(self.sources['mass'],self.sources['audit'],self.sources['review'],self.sources['reuse'],output or self.root/'out',root=self.root)

    def test_complete_bundle_has_master_primary_subset_and_source_figures(self):
        info=self.run_export()
        self.assertEqual(info['release_count'],3);self.assertEqual(info['primary_release_count'],1)
        self.assertFalse(info['scientific_acceptance'])
        self.assertEqual(info['completion_status'],'reviewed_with_open_evidence')
        self.assertEqual((self.root/'out/figures/mass/example.png').read_bytes(),b'fixture-image-bytes')
        with (self.root/'out/tables/discharge_primary.csv').open() as stream:self.assertEqual(len(list(csv.DictReader(stream))),1)
        self.assertTrue((self.root/'out/bundle_index.json').is_file())

    def test_changed_source_and_existing_output_are_refused(self):
        self.run_export()
        with self.assertRaises(FileExistsError):self.run_export()
        with (self.sources['audit']/'discharge_by_release.csv').open('a') as stream:stream.write('changed')
        with self.assertRaisesRegex(ValueError,'hash'):self.run_export(self.root/'other')
        self.assertFalse((self.root/'other').exists())

    def test_output_cannot_overlap_input_folder(self):
        with self.assertRaisesRegex(ValueError,'separate'):
            self.run_export(self.sources['mass']/'nested')

    def test_unpinned_figure_cannot_enter_the_analysis_bundle(self):
        (self.sources['mass']/'figures/unverified.png').write_bytes(b'unverified')
        with self.assertRaisesRegex(ValueError,'pinned'):self.run_export()
        self.assertFalse((self.root/'out').exists())

    def test_incomplete_refreshed_figures_do_not_publish_bundle(self):
        from salt_dilution.scripts.processing import plot_discharge_pulses, plot_discharge_summary

        output = self.root/'out'
        with patch.object(plot_discharge_summary, 'render_summary'), \
                patch.object(plot_discharge_pulses, 'render_pulses'), \
                self.assertRaisesRegex(ValueError, 'figure inventory'):
            export.run_export(self.sources['mass'], self.sources['audit'],
                              self.sources['review'], self.sources['reuse'], output,
                              root=self.root, refresh_figures=True)
        self.assertFalse(output.exists())

    def test_reuse_run_must_match_the_mass_bundle_dependency(self):
        other=self.root/'unrelated_reuse';shutil.copytree(self.sources['reuse'],other)
        with self.assertRaisesRegex(ValueError,'reuse'):
            export.run_export(self.sources['mass'],self.sources['audit'],self.sources['review'],other,self.root/'out',root=self.root)

    def test_stable_layout_keeps_code_out_of_results(self):
        self.run_export()
        output = self.root/'out'
        self.assertEqual(export.DEFAULT_OUTPUT, export.ROOT/'salt_dilution/results/discharge_analysis')
        self.assertFalse((output/'code').exists())
        self.assertFalse(list(output.rglob('*.py')))
        self.assertFalse(list(output.rglob('*.ipynb')))
        for directory in ('tables', 'figures', 'settings', 'provenance'):
            self.assertTrue((output/directory).is_dir())
        guide = json.loads((output/'bundle_index.json').read_text())
        for field in ('entry_point', 'primary_subset', 'channel_estimates', 'provenance'):
            self.assertTrue((output/guide[field]).is_file(), field)
        self.assertEqual((output/'tables/discharge_estimates.csv').read_bytes(),
                         (self.sources['mass']/'discharge_estimates.csv').read_bytes())
        manifest = json.loads((output/'run_info.json').read_text())
        self.assertFalse(any(item['path'].startswith('code/') for item in manifest['outputs']))
        for item in manifest['outputs']:
            self.assertEqual(hashlib.sha256((output/item['path']).read_bytes()).hexdigest(), item['sha256'])
