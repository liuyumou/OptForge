"""Frozen matched-study schema, pairing, replay and artifact preservation contracts."""
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from benchmark_lp_matched import protocol, CONFIG
from benchmark_lp import schedule
from lp_protocol import NS, Ledger, file_hash, read_json, validate, write_json
from report_lp_matched import analyze

class MatchedStudyTests(unittest.TestCase):
    def test_frozen_grid_profiles_and_prior_consumption(self):
        value,base,manifests=protocol(materialized=False)
        jobs=list(schedule(value,manifests))
        self.assertEqual(len(jobs),160)
        self.assertEqual(sum(job[2]['backend']!='host-lp' for job in jobs),120)
        self.assertEqual(sum(job[-1]=='profile' for job in jobs),16)
        self.assertEqual(len({job[0] for job in jobs}),160)
        self.assertEqual(value['prior_gpu_ns'],194142866023)
        self.assertEqual(value['additional_gpu_seconds'],600)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'campaign.json'
            for change in ['schema','grid','seed','profile','budget','binary','escape']:
                wrong=copy.deepcopy(value)
                if change=='schema':wrong['extra']=1
                if change=='grid':wrong['configurations'][0]=wrong['configurations'][1]
                if change=='seed':wrong['order_seed']+=1
                if change=='profile':wrong['profile_instances'].append('gpup-held_out-small-4')
                if change=='budget':wrong['prior_gpu_ns']=0
                if change=='binary':wrong['reference_binary']['sha256']='0'*64
                if change=='escape':wrong['reference_binary']['path']='../escape'
                write_json(path,wrong)
                with self.assertRaises(Exception):protocol(path,False)
        self.assertEqual(jobs,list(schedule(value,manifests)))

    def test_archived_v1_schemas_and_campaign_are_byte_preserved(self):
        paths=list((ROOT/'schemas').glob('lp-*-v1.schema.json'))+[ROOT/'benchmarks/configs/lp-campaign-v1.json']
        for path in paths:
            original=subprocess.check_output(['git','show','e415918:'+str(path.relative_to(ROOT))],cwd=ROOT)
            self.assertEqual(path.read_bytes(),original,path.name)

    def test_hand_checked_pairing_timeouts_and_incomplete_repetitions(self):
        value,_,_=protocol(materialized=False)
        def trial(config,repetition,time,success=True):
            return dict(instance_id='fixture',config_id=config,repetition=repetition,mode='timing',
                status='completed' if success else 'timeout',endpoint_class='certified_success' if success else 'timeout',
                requested_backend=config,executed_backend=config,elapsed_ns=time)
        trials=[trial('cuda-lp',0,100),trial('cuda-lp-matched',0,50),
            trial('cuda-lp',1,200),trial('cuda-lp-matched',1,100),
            trial('cuda-lp',2,300,False),trial('cuda-lp-matched',2,10,False)]
        rows,ratios=analyze(trials,value,[{'id':'fixture'}])
        ratio=next(r['statistics'] for r in ratios if r['comparison']=='cuda-lp/cuda-lp-matched')
        self.assertEqual(ratio,{'paired_repetitions':2,'ratio':2,'ci95':[2,2]})
        row=next(r for r in rows if r['configuration']=='cuda-lp')
        self.assertEqual((row['certified'],row['attempted'],row['censored_timeouts']),(2,3,1))
        self.assertEqual(row['observed_median_ns'],200)
        self.assertEqual(row['certified_median_ns'],150)
        missing=next(r for r in rows if r['configuration']=='host-lp')
        self.assertEqual(missing['attempted'],0);self.assertIsNone(missing['observed_median_ns'])
        with self.assertRaises(ValueError):analyze(trials+[trials[0]],value,[{'id':'fixture'}])

    def test_matched_profile_phase_is_versioned_and_incomplete_evidence_stays_interim(self):
        from report_lp_matched import complete_evidence
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);settings=read_json(ROOT/'examples/lp-settings-v1.json')
            settings.update(iteration_limit=3,check_interval=2);write_json(tmp/'settings.json',settings)
            run=subprocess.run([str(ROOT/'target/debug/optimizer'),'solve','--model',str(ROOT/'examples/lp-model-v1.json'),
                '--config',str(ROOT/'examples/solve-config-v1.json'),'--backend','host-lp',
                '--lp-settings',str(tmp/'settings.json'),'--lp-evidence',str(tmp/'endpoint.json')],capture_output=True,timeout=15)
            self.assertIn(run.returncode,(0,1),run.stderr)
            endpoint=read_json(tmp/'endpoint.json')
        endpoint['diagnostics']['phases_ns']['controller']=7
        with self.assertRaises(Exception):validate('endpoint',endpoint)
        endpoint['schema_version']=2;endpoint['requested_backend']='cuda-lp-matched'
        validate('endpoint',endpoint)
        endpoint['diagnostics']['phases_ns']['invented']=0
        with self.assertRaises(Exception):validate('endpoint',endpoint)
        self.assertTrue(complete_evidence([{'status':'completed'},{'status':'timeout'}],2))
        for status in ['invalid_evidence','missing_evidence','process_failure','activity_blocked']:
            self.assertFalse(complete_evidence([{'status':status}],1))
        self.assertFalse(complete_evidence([],1))

    def test_v2_cpu_trial_uses_supervisor_and_independent_rust_verifier(self):
        from benchmark_lp import run_trial, provenance
        binary=ROOT/'target/debug/optimizer'
        if not binary.is_file():self.skipTest('CLI build required')
        value,base,manifests=protocol(materialized=False)
        job=next(job for job in schedule(value,manifests) if job[1]['id']=='gpup-development-small-4' and job[2]['backend']=='host-lp')
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);write_json(directory/'solve.json',value['solve']);write_json(directory/'lp-settings.json',value['lp_settings'])
            with Ledger(directory/'budget',value['budget_authority']['sha256']) as ledger:
                trial=run_trial(value,*job,binary,directory,ledger,provenance(binary,value['device']),file_hash(CONFIG))
                self.assertEqual(trial['status'],'completed')
                self.assertEqual(trial['endpoint_class'],'certified_success')
                self.assertEqual(trial['schema_version'],2)
                self.assertEqual(ledger.totals(),0)
                self.assertGreater(ledger.totals('cpu'),0)
                validate('trial',trial)
                wrong=copy.deepcopy(trial);wrong['provenance']['surprise']=True
                with self.assertRaises(Exception):validate('trial',wrong)
                evidence=directory/trial['endpoint']['path'];before=evidence.read_bytes()
                output=directory/'replayed.json'
                replay=[str(binary),'lp-study','replay','--model',str(ROOT/job[1]['model']['path']),
                    '--evidence',str(evidence),'--output',str(output)]
                run=subprocess.run(replay,capture_output=True,timeout=15)
                self.assertEqual(run.returncode,0,run.stderr)
                verify=subprocess.run([str(binary),'lp-study','verify','--model',str(ROOT/job[1]['model']['path']),
                    '--evidence',str(output)],capture_output=True,timeout=15)
                self.assertEqual(verify.returncode,0,verify.stderr)
                saved=output.read_bytes();again=subprocess.run(replay,capture_output=True,timeout=15)
                self.assertNotEqual(again.returncode,0)
                self.assertEqual(saved,output.read_bytes());self.assertEqual(before,evidence.read_bytes())

if __name__=='__main__':unittest.main()
