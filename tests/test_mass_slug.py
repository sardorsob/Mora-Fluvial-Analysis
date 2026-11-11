"""Mass conservation, actual clock integration and explicit pulse exclusions."""
import unittest
import numpy as np
import pandas as pd
from salt_dilution.scripts.processing import mass_slug as slug


def samples(t, ec):
    return pd.DataFrame(dict(timestamp=pd.Timestamp('2026-10-04 09:00:00')+pd.to_timedelta(t,unit='s'),specific_conductivity_us_cm=ec))


class NumericalTests(unittest.TestCase):
    def frame(self,t=None,drift=0):
        t=np.arange(0.,601.) if t is None else np.asarray(t)
        pulse=np.where((t>=100)&(t<=300),10*np.sin(np.pi*(t-100)/200)**2,0)
        frame,issues=slug.prepare_series(samples(t,30+drift*t+pulse),'specific')
        return frame

    def windows(self):return dict(pre=[0,60],pulse=[80,350],post=[400,500],issues=[])

    def test_units_and_scaling(self):
        result=slug.discharge(4,.5,2000)
        self.assertEqual(result['q_l_s'],4)
        self.assertEqual(result['q_m3_s'],.004)
        self.assertEqual(slug.discharge(8,.5,2000)['q_l_s'],8)
        self.assertEqual(slug.discharge(4,1,2000)['q_l_s'],2)
        for mass,k,area in [(0,.5,2),(1,0,2),(1,1,0),(float('nan'),1,2)]:
            with self.assertRaises(ValueError):slug.discharge(mass,k,area)

    def test_regular_integral_recovers_known_q(self):
        area=slug.integrate_excess(self.frame(),self.windows())
        self.assertAlmostEqual(area['integral_us_cm_s'],1000,places=8)
        self.assertAlmostEqual(slug.discharge(4,.5,area['integral_us_cm_s'])['q_l_s'],8,places=8)

    def test_irregular_uses_elapsed_seconds(self):
        t=np.r_[0,np.cumsum(np.random.default_rng(42).uniform(.5,2,490))]
        area=slug.integrate_excess(self.frame(t),self.windows())['integral_us_cm_s']
        self.assertLess(abs(area/1000-1),.001)
        self.assertGreater(abs(np.trapezoid(self.frame(t).ec.to_numpy()-30)/1000-1),.05)

    def test_linear_background_removes_drift(self):
        frame=self.frame(drift=.02)
        result=slug.integrate_excess(frame,self.windows())
        self.assertAlmostEqual(result['integral_us_cm_s'],1000,places=6)
        pre=slug.integrate_excess(frame,self.windows(),background='pre')
        self.assertGreater(pre['integral_us_cm_s'],1000)

    def test_constant_offset_cancels(self):
        frame=self.frame();frame['ec']+=100
        self.assertAlmostEqual(slug.integrate_excess(frame,self.windows())['integral_us_cm_s'],1000,places=8)

    def test_negative_excess_not_clamped(self):
        frame=self.frame();frame.loc[(frame.t_s>=310)&(frame.t_s<=330),'ec']-=2
        result=slug.integrate_excess(frame,self.windows())
        self.assertLess(result['integral_us_cm_s'],1000)
        self.assertLess(result['negative_area_us_cm_s'],0)

    def test_identical_duplicates_collapse_but_conflicts_block(self):
        data=samples([0,1,1,2],[30,31,31,32])
        frame,issues=slug.prepare_series(data,'specific')
        self.assertEqual(len(frame),3);self.assertIn('identical_duplicates_collapsed:1',issues)
        data.loc[2,'specific_conductivity_us_cm']=99
        with self.assertRaisesRegex(ValueError,'duplicate'):slug.prepare_series(data,'specific')

    def test_gap_in_pulse_blocks(self):
        frame=self.frame();frame=frame.loc[~frame.t_s.between(150,180)]
        prepared,_=slug.prepare_series(samples(frame.t_s,frame.ec),'specific')
        with self.assertRaisesRegex(ValueError,'gap'):slug.integrate_excess(prepared,self.windows())

    def test_any_missing_pulse_cell_blocks_without_invented_bound(self):
        for indices in ([150],[150,151]):
            frame=self.frame();frame.loc[indices,'ec']=np.nan
            with self.assertRaisesRegex(ValueError,'missing'):slug.integrate_excess(frame,self.windows())

    def test_gaps_outside_selected_windows_do_not_block(self):
        frame=self.frame();frame=frame.loc[~frame.t_s.between(20,30)]
        prepared,_=slug.prepare_series(samples(frame.t_s,frame.ec),'specific')
        windows=dict(pre=[40,80],pulse=[90,350],post=[400,500])
        self.assertAlmostEqual(slug.integrate_excess(prepared,windows)['integral_us_cm_s'],1000,places=8)

    def test_confirmed_pre_injection_pause_does_not_fill_or_drop_the_pulse(self):
        frame=self.frame(); frame=frame.loc[~frame.t_s.between(65,75)]
        prepared,_=slug.prepare_series(samples(frame.t_s,frame.ec),'specific')
        windows=self.windows()
        windows['pre_injection_pause']=dict(release_offset_s=78,background_applicable=True,
                                            evidence='Field record places release after recording resumed.')
        area=slug.integrate_excess(prepared,windows)
        self.assertAlmostEqual(area['integral_us_cm_s'],1000,places=8)
        self.assertEqual(area['bridged_cells'],0)

    def test_pause_confirmation_cannot_justify_an_in_pulse_gap(self):
        frame=self.frame(); frame=frame.loc[~frame.t_s.between(150,180)]
        prepared,_=slug.prepare_series(samples(frame.t_s,frame.ec),'specific')
        windows=self.windows()
        windows['pre_injection_pause']=dict(release_offset_s=78,background_applicable=True,evidence='Before release')
        with self.assertRaisesRegex(ValueError,'gap'):slug.integrate_excess(prepared,windows)

    def test_unconfirmed_pause_between_background_and_pulse_remains_visible(self):
        frame=self.frame();frame=frame.loc[~frame.t_s.between(65,75)]
        prepared,_=slug.prepare_series(samples(frame.t_s,frame.ec),'specific')
        with self.assertRaisesRegex(ValueError,'gap'):slug.integrate_excess(prepared,self.windows())

    def test_missing_fit_se_does_not_prevent_sensitivity_calculation(self):
        result=slug.uncertainty(self.frame(),self.windows(),4,.5,'')
        self.assertIsNone(result['u_k_fit_relative'])
        self.assertIsNone(result['indicative_sensitivity_relative'])
        self.assertIsNotNone(result['u_background_sensitivity'])

    def test_solution_volume_and_equivalent_mass_give_same_discharge(self):
        result=slug.solution_discharge(1000,2e-6,1000)
        self.assertAlmostEqual(result['q_m3_s'],.5)
        self.assertEqual(result,slug.discharge(250,.5,1000))
        with self.assertRaises(ValueError):slug.solution_discharge(-1,2e-6,1000)

    def test_reported_solution_volume_requires_matching_source_and_opt_in(self):
        trial=dict(injection_solution_volume_ml='12900')
        evidence=dict(source_record=dict(reported_injected_solution_ml='12900',delivered_solution_ml=''))
        with self.assertRaisesRegex(ValueError,'delivered_solution'):slug.solution_quantity(trial,evidence)
        volume,basis=slug.solution_quantity(trial,evidence,allow_reported=True)
        self.assertEqual(volume,12900)
        self.assertEqual(basis,'reported_delivery_assumed')
        with self.assertRaisesRegex(ValueError,'source'):
            slug.solution_quantity(dict(injection_solution_volume_ml='13000'),evidence,allow_reported=True)

    def test_reversed_or_outside_windows_rejected(self):
        for windows in [dict(pre=[0,60],pulse=[300,100],post=[400,500]),dict(pre=[0,60],pulse=[80,350],post=[600,700])]:
            with self.assertRaises(ValueError):slug.integrate_excess(self.frame(),windows)

    def test_actual_is_primary_if_specific_did_not_compute(self):
        rows=[dict(trial_id='T',logical_recording_id='R',conductivity_basis='actual',coefficient_source='trial_specific',estimate_role='comparison_channel')]
        slug.assign_roles(rows)
        self.assertEqual(rows[0]['estimate_role'],'primary')
        rows.append(dict(rows[0],conductivity_basis='specific'))
        slug.assign_roles(rows)
        self.assertEqual([r['estimate_role'] for r in rows],['comparison_channel','primary'])


class WindowTests(unittest.TestCase):
    frame = NumericalTests.frame

    def test_coarse_sampling_uses_elapsed_background_duration(self):
        for cadence in (5., 10.):
            with self.subTest(cadence=cadence):
                frame = self.frame(t=np.arange(0., 601., cadence))
                windows = slug.propose_windows(frame)
                self.assertFalse(windows['issues'], windows)
                pre, _, post = slug._window_parts(frame, windows)
                self.assertEqual(len(pre), int(30 / cadence) + 1)
                self.assertEqual(len(post), int(30 / cadence) + 1)
                self.assertAlmostEqual(slug.integrate_excess(frame, windows)['integral_us_cm_s'], 1000, places=6)

    def test_two_background_samples_use_detection_floor_with_support_flags(self):
        frame, _ = slug.prepare_series(samples(np.arange(0., 361., 60.),
                                               [30, 30, 35, 40, 34, 30, 30]), 'specific')
        windows = slug.propose_windows(frame)
        self.assertFalse(windows['issues'], windows)
        support = windows['background_support']
        self.assertEqual((support['pre_samples'], support['post_samples']), (2, 2))
        self.assertEqual((support['pre_duration_s'], support['post_duration_s']), (60., 60.))
        self.assertIsNone(support['pre_noise_std_us_cm'])
        self.assertEqual(windows['threshold_us_cm'], .5)
        self.assertEqual(set(support['flags']), {'low_background_support', 'insufficient_noise_df'})
        self.assertEqual(windows['pulse'], [60., 300.])
        self.assertAlmostEqual(slug.integrate_excess(frame, windows)['integral_us_cm_s'], 1140.)

    def test_explicit_sample_count_still_respects_maximum_duration(self):
        frame = self.frame(t=np.arange(0., 601., 20.))
        self.assertIn('no_pre_pulse_background', slug.propose_windows(frame, min_background_n=10)['issues'])

    def test_two_point_decline_is_not_hidden_by_overlapping_pre_window_slices(self):
        frame, _ = slug.prepare_series(samples(np.arange(0., 421., 60.),
                                               [31, 30, 29, 50, 65, 40, 25, 24]), 'specific')
        self.assertIn('no_pre_pulse_background', slug.propose_windows(frame, min_background_n=2)['issues'])

    def test_explicit_shorter_settling_window_remains_observed(self):
        frame = self.frame().iloc[:331]
        edge = dict(trial_id='T', logical_recording_id='R')
        windows, _ = slug._choose_windows(frame, edge, 'specific', {})
        self.assertIn('tail_incomplete', windows['issues'])
        windows, _ = slug._choose_windows(frame, edge, 'specific', {},
                                          automatic_window_policy={'settle_s': 15.})
        self.assertFalse(windows['issues'], windows)
        self.assertEqual(windows['background_support']['post_duration_s'], 15.)

    def test_noninteger_cadence_spans_the_requested_background_duration(self):
        frame = self.frame(t=np.arange(0., 601., 2.3))
        windows = slug.propose_windows(frame)
        self.assertFalse(windows['issues'], windows)
        pre, _, post = slug._window_parts(frame, windows)
        self.assertGreaterEqual(pre.t_s.iloc[-1]-pre.t_s.iloc[0], 30.)
        self.assertGreaterEqual(post.t_s.iloc[-1]-post.t_s.iloc[0], 30.)
        self.assertLess(abs(slug.integrate_excess(frame, windows)['integral_us_cm_s']/1000-1), .001)

    def test_full_pulse_proposed(self):
        windows=slug.propose_windows(self.frame())
        self.assertFalse(windows['issues'],windows)
        self.assertLessEqual(windows['pulse'][0],120)
        self.assertGreater(windows['pulse'][1],270)

    def test_detection_threshold_does_not_cut_off_smooth_pulse_tails(self):
        frame=self.frame();windows=slug.propose_windows(frame)
        area=slug.integrate_excess(frame,windows)['integral_us_cm_s']
        self.assertLess(abs(area/1000-1),.005)

    def test_truncated_tail_rejected(self):
        frame=self.frame().iloc[:210]
        self.assertIn('tail_incomplete',slug.propose_windows(frame)['issues'])

    def test_pulse_at_recording_start_rejected(self):
        frame=self.frame();frame=frame.loc[frame.t_s>=170].copy();frame.t_s-=170
        self.assertIn('no_pre_pulse_background',slug.propose_windows(frame)['issues'])

    def test_two_pulses_require_event_selection(self):
        frame=self.frame();t=frame.t_s.to_numpy()
        frame['ec']+=np.where((t>=400)&(t<=500),10*np.sin(np.pi*(t-400)/100)**2,0)
        self.assertIn('multiple_pulses_ambiguous',slug.propose_windows(frame)['issues'])
        chosen=slug.propose_windows(frame,release_offset_s=380)
        self.assertFalse(chosen['issues'],chosen)
        self.assertGreater(chosen['pulse'][0],350)

    def test_corrected_elapsed_release_offset_selects_the_intended_pulse(self):
        frame=self.frame();t=frame.t_s.to_numpy()
        frame['ec']+=np.where((t>=400)&(t<=500),10*np.sin(np.pi*(t-400)/100)**2,0)
        edge=dict(trial_id='T',logical_recording_id='R',chronology_evidence=json.dumps(
            dict(release_offset_seconds=380,release_clock='2026-10-04 17:06:20+00:00',clock_basis='explicit_utc')))
        windows,_=slug._choose_windows(frame,edge,'specific',{})
        self.assertFalse(windows['issues'])
        self.assertGreater(windows['pulse'][0],350)

    def test_incomplete_first_wave_is_not_replaced_by_a_later_complete_wave(self):
        t=np.arange(801,dtype=float)
        frame=self.frame(t);frame['ec']+=np.where((t>=450)&(t<=550),10*np.sin(np.pi*(t-450)/100)**2,0)
        frame=frame.loc[~frame.t_s.between(150,180)&~frame.t_s.between(350,380)]
        frame,_=slug.prepare_series(samples(frame.t_s,frame.ec),'specific')
        first=slug.propose_windows(frame,release_offset_s=90)
        self.assertIn('earlier_pulse_incomplete',first['issues'])
        second=slug.propose_windows(frame,release_offset_s=430)
        self.assertFalse(second['issues'])
        self.assertGreater(second['pulse'][0],400)


import csv
import hashlib
import json
from pathlib import Path
import tempfile
import shutil


def csvfile(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(dict.fromkeys(k for row in rows for k in row)));writer.writeheader();writer.writerows(rows)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.records=self.root/'records';self.proc=self.root/'processed';self.cal=self.root/'cal';self.pair=self.root/'pair'
        for d in (self.records,self.proc,self.cal,self.pair):d.mkdir()
        self.trials=[dict(trial_id='T'+str(i),field_date='10/4/2026',site_alias='NISQ',salt_mass_g='4') for i in (1,2,3)]
        prep=dict(calibration_id='C1',site_alias='NISQ',field_date='10/4/2026',procedure_id='mass_stock_river',stock_water_source='river',stock_salt_mass_g='2',stock_water_initial_ml='1000',stock_solution_final_ml='',calibration_water_initial_ml='2000')
        self.preps=[prep,dict(prep,calibration_id='C2',procedure_id='solution_secondary',injectate_aliquot_ml='10',secondary_water_initial_ml='1000')]
        csvfile(self.records/'trials.csv',self.trials);csvfile(self.records/'calibrations.csv',self.preps)
        csvfile(self.records/'trial_inputs.csv',[dict(trial_id='T1',dataset_id='F1',processed_path='processed/a.csv')])
        points=[dict(calibration_id=cid,step_no=str(i),probe_alias='',temperature_c='',specific_conductivity_us_cm=str(30+i*10)) for cid in ('C1','C2') for i in range(3)]
        csvfile(self.records/'calibration_points.csv',points)
        provenance=dict(calibrations={cid:dict(source_table_status='recorded',source_record={'method_family':'mass_stock' if cid=='C1' else 'unspecified'}) for cid in ('C1','C2')},trials={t['trial_id']:dict(quantity_basis={'salt_mass_g':'unknown'}) for t in self.trials})
        (self.records/'provenance.json').write_text(json.dumps(provenance))
        fit=dict(calibration_id='C1',probe_alias='',conductivity_basis='specific',calibration_basis='mass_concentration',concentration_unit='mg/L',coefficient_unit='(mg/L) / (uS/cm)',k='0.5',ec_min='30',ec_max='50')
        self.fits=[fit,dict(fit,calibration_id='C2',calibration_basis='relative_concentration',concentration_unit='mL/mL',coefficient_unit='(mL/mL) / (uS/cm)')]
        csvfile(self.cal/'calibration_fits.csv',self.fits)
        csvfile(self.cal/'calibration_points.csv',[dict(calibration_id=cid,probe_alias='',conductivity_basis='specific',used_in_fit='True',conductivity_us_cm=str(30+i*10),residual='0') for cid in ('C1','C2') for i in range(3)])
        (self.cal/'calibration_skips.csv').write_text('calibration_id,probe_alias,conductivity_basis,reason\n')
        self.calinfo=dict(inputs=self.pins(list(self.records.iterdir())),outputs=self.outputs(self.cal))
        (self.cal/'run_info.json').write_text(json.dumps(self.calinfo))
        inventory=[]
        for name,n in [('a',601),('b',210)]:
            t=np.arange(n,dtype=float);v=30+np.where((t>=100)&(t<=300),10*np.sin(np.pi*(t-100)/200)**2,0)
            df=samples(t,v);path=self.proc/(name+'.csv');df.to_csv(path,index=False)
            ref='F1' if name=='a' else 'F3'
            inventory.append(dict(content_ref=ref,members=[ref],path=f'processed/{name}.csv',device_serial='111',files={'processed':dict(path=f'processed/{name}.csv',sha256=hashlib.sha256(path.read_bytes()).hexdigest())}))
        self.recordings=[dict(trial_id='T'+str(i),recording_edge_id='E'+str(i),logical_recording_id='R1' if i!=3 else 'R3',member_refs=json.dumps(['F1' if i!=3 else 'F3']),device_serial='111',time_evidence='{}',chronology_evidence='{}',selected_for_pairing='true') for i in (1,2,3)]
        self.edges=[]
        for i in (1,2,3):
            cid='C2' if i==2 else 'C1';f=self.fits[1 if i==2 else 0]
            ref=dict(key=[cid,'','specific'],fit_table_sha256=hashlib.sha256((self.cal/'calibration_fits.csv').read_bytes()).hexdigest(),run_info_sha256=hashlib.sha256((self.cal/'run_info.json').read_bytes()).hexdigest())
            self.edges.append(dict(f,trial_id='T'+str(i),calibration_edge_id='K'+str(i),recording_edge_id='E'+str(i),status='supported',mass_route_eligible='false' if i==2 else 'true',identity_status='native_match',recording_device_serial='111',calibration_device_serial='111',fit_reference=json.dumps(ref)))
        self.summaries=[dict(trial_id='T'+str(i),status='inferred_proposal',selected_recording_edge_ids=json.dumps(['E'+str(i)]),selected_calibration_edge_ids=json.dumps(['K'+str(i)]),event_alignment_review_required='false') for i in (1,2,3)]
        self.info=dict(inputs=self.pins([*self.records.iterdir(),*self.proc.iterdir(),self.cal/'run_info.json',self.cal/'calibration_fits.csv']),inventory=inventory,
                       calibration_device_checks={'C1':dict(status='verified',device_serial='111',basis='within_trial_continuity')},
                       logical_recordings=[dict(logical_recording_id='R1',members=['F1']),dict(logical_recording_id='R3',members=['F3'])],recording_segments=[])
        self.seal()

    def pins(self,paths):return [dict(path=p.relative_to(self.root).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths if p.is_file()]
    def outputs(self,folder):return [dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in folder.iterdir() if p.is_file() and p.name!='run_info.json']
    def seal(self):
        for name,data in [('recording_candidates',self.recordings),('calibration_candidates',self.edges),('pairing_summary',self.summaries)]:csvfile(self.pair/(name+'.csv'),data)
        self.info['outputs']=self.outputs(self.pair);(self.pair/'run_info.json').write_text(json.dumps(self.info))
    def run_batch(self,**kwargs):return slug.run_mass_slug(self.records,self.proc,self.pair,self.cal,self.root/'out',root=self.root,**kwargs)
    def read(self,name):
        with (self.root/'out'/name).open() as stream:return list(csv.DictReader(stream))

    def test_end_to_end_and_accounting(self):
        self.run_batch()
        rows=self.read('release_summary.csv');self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]['category'],'computed')
        self.assertEqual(rows[1]['category'],'relative_basis_not_mass_route')
        self.assertTrue(rows[2]['category'].startswith('blocked_'))
        estimate=self.read('discharge_estimates.csv')[0]
        self.assertAlmostEqual(float(estimate['q_l_s']),8,delta=.08)
        self.assertEqual(estimate['q_status'],'proposed');self.assertEqual(estimate['mass_basis'],'operational_unverified')
        self.assertEqual(estimate['k'],'0.5');self.assertEqual(estimate['scientifically_accepted'],'false')

    def test_relative_runner_uses_original_injectate_volume(self):
        self.trials[1]['injection_solution_volume_ml']='1000'
        csvfile(self.records/'trials.csv',self.trials)
        p=json.loads((self.records/'provenance.json').read_text())
        p['trials']['T2']['source_record']=dict(delivered_solution_ml='1000')
        (self.records/'provenance.json').write_text(json.dumps(p))
        self.calinfo['inputs']=self.pins(list(self.records.iterdir()))
        (self.cal/'run_info.json').write_text(json.dumps(self.calinfo))
        for edge in self.edges:
            ref=json.loads(edge['fit_reference'])
            ref['run_info_sha256']=hashlib.sha256((self.cal/'run_info.json').read_bytes()).hexdigest()
            edge['fit_reference']=json.dumps(ref)
        self.info['inputs']=self.pins([*self.records.iterdir(),*self.proc.iterdir(),self.cal/'run_info.json',self.cal/'calibration_fits.csv'])
        self.seal();self.run_batch(include_relative=True)
        row=next(r for r in self.read('discharge_estimates.csv') if r['trial_id']=='T2')
        self.assertAlmostEqual(float(row['q_l_s']),.002,delta=.00002)
        self.assertEqual(row['discharge_method'],'solution_slug')
        self.assertEqual(row['mass_g'],'')
        self.assertEqual(row['injection_solution_volume_ml'],'1000.0')

    def test_low_k_reference_warning_survives_q_and_release_without_correcting_k(self):
        from salt_dilution.scripts.processing import discharge_review
        self.fits[0]['k']='0.4'
        csvfile(self.cal/'calibration_fits.csv',self.fits)
        self.calinfo['outputs']=self.outputs(self.cal)
        (self.cal/'run_info.json').write_text(json.dumps(self.calinfo))
        for edge in self.edges:
            if edge['calibration_id']=='C1':edge['k']='0.4'
            ref=json.loads(edge['fit_reference'])
            ref['fit_table_sha256']=hashlib.sha256((self.cal/'calibration_fits.csv').read_bytes()).hexdigest()
            ref['run_info_sha256']=hashlib.sha256((self.cal/'run_info.json').read_bytes()).hexdigest()
            edge['fit_reference']=json.dumps(ref)
        self.info['inputs']=self.pins([*self.records.iterdir(),*self.proc.iterdir(),self.cal/'run_info.json',self.cal/'calibration_fits.csv'])
        self.seal();self.run_batch()
        row=next(r for r in self.read('discharge_estimates.csv') if r['trial_id']=='T1')
        self.assertEqual(row['k'],'0.4')
        self.assertAlmostEqual(float(row['q_l_s']),10,delta=.1)
        self.assertIn('below_ideal_nacl_reference',json.loads(row['flags']))
        self.assertIn('below_ideal_nacl_reference',json.loads(row['calibration_reference_flags']))
        self.assertIn('not a correction',row['calibration_reference_assumptions'])
        summary=next(r for r in self.read('release_summary.csv') if r['trial_id']=='T1')
        master,_=discharge_review._release_rows(self.trials[0],summary,{},[row],
            [dict(estimate_role='primary',added_ec_span_exceeded=False)],[],[],'test')
        self.assertIn('below_ideal_nacl_reference',master['flags'])
        self.assertEqual(master['calibration_reference_assumptions'],row['calibration_reference_assumptions'])

    def test_supported_edge_can_survive_a_conflicting_companion(self):
        self.summaries[0]['status']='conflicting'
        self.seal();self.run_batch(include_relative=True)
        self.assertTrue(any(r['trial_id']=='T1' for r in self.read('discharge_estimates.csv')))

    def test_saved_pause_windows_replay_with_their_evidence(self):
        path=self.proc/'a.csv';df=pd.read_csv(path)
        df=df.drop(index=range(65,76));df.to_csv(path,index=False)
        self.info['inventory'][0]['files']['processed']['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        self.info['inputs']=self.pins([*self.records.iterdir(),*self.proc.iterdir(),self.cal/'run_info.json',self.cal/'calibration_fits.csv'])
        self.seal()
        origin=pd.Timestamp('2026-10-04 09:00:00')
        window=dict(trial_id='T1',logical_recording_id='R1',channel='specific',review_status='checker_proposed',
            evidence='Documented stop before release.',reviewer='test reviewer',reviewed_on='2026-11-10',
            pre_injection_pause=dict(release_offset_s=78,background_applicable=True,evidence='Release after resume.'))
        for key,values in dict(pre=[0,60],pulse=[80,350],post=[400,500]).items():
            window[key]=[(origin+pd.Timedelta(seconds=v)).isoformat() for v in values]
        windows=self.root/'windows.json';windows.write_text(json.dumps(dict(schema_version=1,windows=[window])))
        self.run_batch(windows_path=windows)
        row=next(r for r in self.read('discharge_estimates.csv') if r['trial_id']=='T1')
        frame,_=slug.prepare_series(df,'specific')
        replay=slug.integrate_excess(frame,json.loads(row['windows']))
        self.assertAlmostEqual(replay['integral_us_cm_s'],float(row['integral_us_cm_s']))
        proposal=json.loads((self.root/'out/pulse_windows_proposed.json').read_text())['windows'][0]
        self.assertEqual(proposal['pre_injection_pause'],window['pre_injection_pause'])

    def test_stale_processed_hash_stops_before_output(self):
        with (self.proc/'a.csv').open('a') as f:f.write('changed')
        with self.assertRaisesRegex(ValueError,'hash'):self.run_batch()
        self.assertFalse((self.root/'out').exists())

    def test_no_cross_sensor_k(self):
        self.recordings[0]['device_serial']='222';self.seal();self.run_batch()
        self.assertFalse(any(r['trial_id']=='T1' for r in self.read('discharge_estimates.csv')))

    def test_edge_identity_cannot_override_audited_native_identity(self):
        self.recordings[0]['device_serial']='222'
        self.edges[0]['calibration_device_serial']='222'
        self.seal();self.run_batch()
        self.assertFalse(any(r['trial_id']=='T1' for r in self.read('discharge_estimates.csv')))

    def test_selected_edge_cannot_point_to_a_different_release(self):
        self.edges[0]['trial_id']='T2';self.seal()
        with self.assertRaisesRegex(ValueError,'release'):self.run_batch()

    def test_user_signoff_is_required_for_reviewed_status(self):
        p=self.root/'windows.json';p.write_text(json.dumps(dict(schema_version=1,windows=[dict(trial_id='T1',logical_recording_id='R1',channel='specific',review_status='reviewed',evidence='visible',reviewer='Checker',reviewed_on='2026-11-08')])))
        with self.assertRaisesRegex(ValueError,'signoff'):self.run_batch(windows_path=p)

    def test_alternate_records_must_match_bundles_not_just_exist(self):
        other=self.root/'other_records';shutil.copytree(self.records,other)
        trials=[dict(row,salt_mass_g='8') for row in self.trials];csvfile(other/'trials.csv',trials)
        with self.assertRaisesRegex(ValueError,'source'):
            slug.run_mass_slug(other,self.proc,self.pair,self.cal,self.root/'out',root=self.root)
        with self.assertRaisesRegex(ValueError,'source'):
            slug.reuse.run_reuse(other,self.cal,self.pair,self.root/'reuse',root=self.root)

    def test_fit_reference_k_cannot_be_changed(self):
        self.edges[0]['k']='0.6';self.seal()
        with self.assertRaisesRegex(ValueError,'fit'):self.run_batch()

    def test_paradise_is_reported_not_omitted(self):
        self.trials[0]['site_alias']='PAR';csvfile(self.records/'trials.csv',self.trials)
        # Refresh the explicitly generated fixture provenance pins, not a production source.
        for info in (self.calinfo,self.info):
            for pin in info['inputs']:
                if pin['path']=='records/trials.csv':pin['sha256']=hashlib.sha256((self.records/'trials.csv').read_bytes()).hexdigest()
        (self.cal/'run_info.json').write_text(json.dumps(self.calinfo))
        for e in self.edges:
            f=json.loads(e['fit_reference']);f['run_info_sha256']=hashlib.sha256((self.cal/'run_info.json').read_bytes()).hexdigest();e['fit_reference']=json.dumps(f)
        for pin in self.info['inputs']:
            if pin['path']=='cal/run_info.json':pin['sha256']=hashlib.sha256((self.cal/'run_info.json').read_bytes()).hexdigest()
        self.seal();self.run_batch();self.assertEqual(self.read('release_summary.csv')[0]['category'],'out_of_scope_site')

    def test_existing_output_refused(self):
        self.run_batch()
        with self.assertRaises(FileExistsError):self.run_batch()

    def test_reviewed_windows_need_evidence_and_user_signoff(self):
        p=self.root/'windows.json';p.write_text(json.dumps(dict(schema_version=1,windows=[dict(trial_id='T1',logical_recording_id='R1',channel='specific',pre=['2026-10-04 09:00:00','2026-10-04 09:01:00'],pulse=['2026-10-04 09:01:20','2026-10-04 09:05:50'],post=['2026-10-04 09:06:40','2026-10-04 09:08:20'],review_status='checker_proposed',evidence='visible return',reviewer='Checker',reviewed_on='2026-11-08')])))
        self.run_batch(windows_path=p)
        row=self.read('discharge_estimates.csv')[0]
        self.assertEqual(row['window_status'],'checker_proposed');self.assertEqual(row['q_status'],'proposed')

    def confirmations(self, **changes):
        entry=dict(trial_id='T1',field_date='2026-10-04',site_alias='NISQ',delivered_salt_mass_g=4,
                   status='confirmed_delivered',confirmed_on='2026-11-08',confirmed_by='field_participant',
                   evidence='The participant confirms the mass entered the stream, including bucket residue.')
        entry.update(changes)
        path=self.root/'confirmations.json'
        path.write_text(json.dumps(dict(schema_version=1,releases=[entry])))
        return path

    def test_delivery_confirmation_changes_provenance_not_q_or_acceptance(self):
        self.run_batch();before=self.read('discharge_estimates.csv')[0]
        path=self.confirmations()
        slug.run_mass_slug(self.records,self.proc,self.pair,self.cal,self.root/'confirmed',
                           confirmations_path=path,root=self.root)
        with (self.root/'confirmed/discharge_estimates.csv').open() as stream:after=list(csv.DictReader(stream))[0]
        for key in ('q_l_s','q_m3_s','k','integral_us_cm_s'):self.assertEqual(before[key],after[key])
        self.assertEqual(after['mass_basis'],'user_confirmed_delivered')
        self.assertEqual(after['nominal_equals_delivered_mass_assumed'],'false')
        self.assertNotIn('nominal_equals_delivered_mass_assumed',json.loads(after['flags']))
        self.assertEqual(after['q_status'],'proposed');self.assertEqual(after['scientifically_accepted'],'false')
        self.assertEqual(after['u_mass'],'not_quantified')
        self.assertEqual((self.root/'confirmed/release_confirmations_used.json').read_bytes(),path.read_bytes())
        info=json.loads((self.root/'confirmed/run_info.json').read_text())
        self.assertTrue(any(p['sha256']==hashlib.sha256(path.read_bytes()).hexdigest() for p in info['inputs']))

    def test_confirmation_scope_does_not_spread_to_other_releases(self):
        path=self.confirmations();self.run_batch(confirmations_path=path)
        rows=self.read('release_summary.csv')
        self.assertEqual([r['mass_confirmation_status'] for r in rows],['confirmed_delivered','unconfirmed','unconfirmed'])

    def test_confirmation_cannot_change_trial_date_or_infer_missing_evidence(self):
        for changes in [dict(field_date='2026-10-05'),dict(site_alias='PAR'),dict(trial_id='unknown'),
                        dict(evidence=''),dict(delivered_salt_mass_g=-1),dict(delivered_salt_mass_g=True)]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):self.run_batch(confirmations_path=self.confirmations(**changes))
