"""Frozen GPUP-6 protocol and budget refusal tests, independent of local campaigns."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from lp_adaptive_budget import protocol, ledger_for
from benchmark_lp_adaptive import jobs
from lp_protocol import Ledger, NS, read_json, write_json, file_hash
from validate_artifacts import validator

class AdaptiveContracts(unittest.TestCase):
    def test_frozen_grid_and_existing_protocol_pins(self):
        v=protocol();schedule=list(jobs(v))
        self.assertEqual(len(schedule),2376);self.assertEqual(len({j[0] for j in schedule}),2376)
        self.assertEqual([len(b['instances'])*len(b['configurations'])*b['repetitions'] for b in v['blocks']],[936,1416,24])
        self.assertEqual(v['solve']['tolerances'],dict(absolute=1e-9,relative=1e-9,integrality=1e-9))
        self.assertEqual((v['study_phase'],v['acceptance_phase']),('ablations','repeatability'))
        self.assertEqual(v['cumulative_gpu_ns'],14402574545061)
        for c in v['configurations']:
            if 'adaptive' in c:validator('lp-adaptive-v1.schema.json').validate(c['adaptive'])
        self.assertEqual(file_hash(ROOT/v['previous_protocol']['path']),v['previous_protocol']['sha256'])
        self.assertEqual(file_hash(ROOT/'benchmarks/configs/lp-precision-v4.json'),'b40217f3e5ce7260f903b8f16882a14c1fc0521c2c397871240e51d90da7ec48')

    def fixture(self,root):
        v=protocol();previous=read_json(ROOT/v['previous_protocol']['path'])
        paths={v['budget_authority']['path'],v['previous_protocol']['path'],v['decision']['path'],previous['source_campaign']['path'],previous['decision']['path']}
        for name in paths:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
        directory=root/'artifacts/lp-campaign-ledgers/gpup-baseline-v1'
        with Ledger(directory,v['budget_authority']['sha256'],v['phase_gpu_seconds'],cumulative_ns=v['cumulative_gpu_ns']) as ledger:
            ledger.bind_output(root/'artifacts/gpup-baseline-v1')
            reservation=ledger.reserve('fixture-cpu',1,resource='cpu');ledger.settle(reservation,1)
        data=(directory/'ledger.jsonl').read_bytes()
        v.update(prior_events=2,prior_gpu_ns=0,prior_ledger_sha256=hashlib.sha256(data).hexdigest())
        return v,directory

    def test_authority_prefix_output_and_phase_refusals_without_live_ledger(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);v,directory=self.fixture(root)
            with ledger_for(v,root) as ledger:self.assertEqual(ledger.totals(),0)
            for name,value in [('cumulative_gpu_ns',v['cumulative_gpu_ns']+1),('prior_gpu_ns',1),('prior_ledger_sha256','0'*64),('study_phase','screening'),('acceptance_phase','ablations')]:
                wrong=copy.deepcopy(v);wrong[name]=value
                with self.assertRaises(ValueError,msg=name):ledger_for(wrong,root)
            wrong=copy.deepcopy(v);wrong['phase_gpu_seconds']['ablations']+=1
            with self.assertRaises(ValueError):ledger_for(wrong,root)
            wrong=copy.deepcopy(v);wrong['decision']['sha256']='0'*64
            with self.assertRaises(ValueError):ledger_for(wrong,root)
            binding=directory/'output.json';saved=read_json(binding);write_json(binding,dict(saved,output_path=str(root/'different')))
            with self.assertRaises(ValueError):ledger_for(v,root)
            write_json(binding,saved)
            self.assertEqual(len((directory/'ledger.jsonl').read_bytes().splitlines()),2)

    def test_category_caps_crash_recovery_and_no_cross_phase_borrowing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);v,directory=self.fixture(root)
            v.update(study_cap_seconds=2,acceptance_cap_seconds=2,combined_cap_seconds=3)
            key=v['id']
            with ledger_for(v,root) as ledger:
                with self.assertRaises(ValueError):ledger.reserve(key+'-study-wrong',1,phase='screening')
                with self.assertRaises(ValueError):ledger.reserve('another-job',1,phase='ablations')
                r=ledger.reserve(key+'-study-first',2,phase='ablations');ledger.settle(r,2*NS)
                with self.assertRaises(ValueError):ledger.reserve(key+'-study-over',1,phase='ablations')
                # An unsettled reservation is conservatively charged on reopen.
                ledger.reserve(key+'-accept-crash',1,phase='repeatability')
            with ledger_for(v,root) as ledger:
                self.assertEqual((ledger.usage('study'),ledger.usage('accept')),(2*NS,NS))
                self.assertFalse(ledger.pending())
                with self.assertRaises(ValueError):ledger.reserve(key+'-accept-combined-over',1,phase='repeatability')

class AdaptiveAdmissionShapes(unittest.TestCase):
    def test_every_frozen_configuration_reaches_admission_with_a_valid_v5_intent(self):
        from unittest.mock import patch
        from benchmark_lp import run_trial
        class AdmissionReached(Exception):pass
        value=protocol()
        class Boundary:
            campaign_hash=value['budget_authority']['sha256']
            def reserve(self,identity,seconds,resource,phase):
                if phase!='ablations':raise AssertionError('wrong phase')
                raise AdmissionReached()
        provenance=dict(revision='a'*40,dirty=False,source_tree_sha256='a'*64,binary_sha256='b'*64,code_object_sha256='c'*64,highs_library_sha256='d'*64,rustc='test',cargo='test',os='test',cpu='test',cpu_affinity=[0],build_profile='release',device=value['device'],telemetry_before='unavailable',telemetry_after='unavailable',copt_library_sha256=None,copt_binding_sha256=None)
        first={}
        for job in jobs(value):first.setdefault(job[2]['id'],job)
        self.assertEqual(set(first),{c['id'] for c in value['configurations']})
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary);model=directory/'model.json';model.write_text('{}')
            with patch('benchmark_lp.quiet_device',return_value={'elapsed_ns':0}),patch('benchmark_lp.telemetry',return_value='unavailable'),patch('benchmark_lp.checked_reference',return_value=model):
                for identity,job in first.items():
                    with self.assertRaises(AdmissionReached,msg=identity):
                        run_trial(value,*job,ROOT/'target/release/optimizer',directory,Boundary(),provenance,'e'*64)
                    trial=read_json(directory/(job[0]+'.intent.json'))
                    self.assertTrue(trial['block'].startswith(('coverage:','policy:','profiles:')))
                    command=read_json(directory/(job[0]+'.request.json'))['command']
                    self.assertEqual('--lp-adaptive' in command,'adaptive' in job[2])

    def test_archive_checks_discovery_image_before_any_admission(self):
        from benchmark_lp_adaptive import code_images
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            for name in ('lp_pdhg.cubin','lp_pdhg_tuned.cubin','lp_pdhg_precision.cubin'):
                (directory/name).write_bytes(name.encode())
            with self.assertRaises(FileNotFoundError):code_images(directory)
            (directory/'schedule_eval.cubin').write_bytes(b'discovery prerequisite')
            images=code_images(directory)
            self.assertEqual(len(images),4)
            self.assertEqual(images['schedule_eval.cubin'],file_hash(directory/'schedule_eval.cubin'))

if __name__=='__main__':unittest.main()
