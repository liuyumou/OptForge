"""ADR-0035 frozen arithmetic, budgets and interruption contracts (CPU only)."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import lp_exec_oracle as oracle
import lp_exec_budget as budget
import lp_exec_accept as acceptance
import benchmark_lp_exec as study
from lp_copt_budget import ComparisonLedger
from lp_protocol import write_json,read_json
class ExecContracts(unittest.TestCase):
    def test_oracle_reproduces(self):
        self.assertEqual(json.loads(oracle.FIXTURE.read_text()),oracle.generate())
    def test_frozen_roster_and_worst_case(self):
        value=budget.protocol();jobs=list(study.jobs(value));self.assertEqual(len(jobs),108)
        self.assertEqual(len({j['id'] for j in jobs}),108)
        self.assertEqual(sum(study.effective(value,j)[2]+6 for j in jobs if j['kind']=='timing'),2256)
        self.assertEqual(sum(study.effective(value,j)[2]+6 for j in jobs if j['kind']=='profile'),432)
        for j in jobs:
            solve,method,_=study.effective(value,j)
            self.assertEqual(solve['tolerances'],value['solve']['tolerances'])
            self.assertEqual(method['iteration_limit'],200 if j['kind']=='profile' else 50000)
    def test_authority_cannot_widen_or_reset(self):
        value=budget.protocol()
        # A source-only checkout has no campaign ledger. Malformed authority must
        # be refused before trying to load that private evidence chain.
        with patch('lp_convergence_budget.ledger_for',side_effect=FileNotFoundError('campaign artifacts absent')) as parent:
            for key,changed in [('cumulative_gpu_ns',21602574545062),('combined_cap_seconds',3601),('prior_events',0)]:
                altered=copy.deepcopy(value);altered[key]=changed
                with self.assertRaises(ValueError):budget.ledger_for(altered)
            altered=copy.deepcopy(value);altered['phase_gpu_seconds']['screening']+=1
            with self.assertRaises(ValueError):budget.ledger_for(altered)
            parent.assert_not_called()
            with self.assertRaises(FileNotFoundError):budget.ledger_for(value)
            parent.assert_called_once()
    def test_category_and_crash_accounting(self):
        value=budget.protocol()
        with tempfile.TemporaryDirectory() as directory:
            with ComparisonLedger(Path(directory),'a'*64,value) as ledger:
                pending=ledger.reserve('gpup-exec-v1-accept-simulated',20,phase='repeatability')
                with self.assertRaises(ValueError):ledger.reserve('gpup-exec-v1-accept-too-large',851,phase='repeatability')
                with self.assertRaises(ValueError):ledger.reserve('gpup-exec-v1-profile-wrong-phase',1,phase='repeatability')
            with ComparisonLedger(Path(directory),'a'*64,value) as ledger:
                self.assertEqual(ledger.usage('accept'),20*10**9)
                self.assertFalse(ledger.pending())
                with self.assertRaises(ValueError):ledger.reserve(pending['trial_id'],1,phase='repeatability')
    def test_worker_and_input_bindings_include_profile_and_mode(self):
        value=budget.protocol();job=next(j for j in study.jobs(value) if j['kind']=='profile' and j['configuration']['backend']=='lp-exec-v1')
        identity=dict(source_tree_sha256='a'*64,exec_binary_sha256='b'*64,code_object_sha256='c'*64)
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);request=study.write_inputs(value,job,directory,identity)
            study.check_request(value,job,directory,identity,request)
            bad=copy.deepcopy(request);bad['command']=['true']
            with self.assertRaises(ValueError):study.check_request(value,job,directory,identity,bad)
            path=directory/(job['id']+'.exec-request.json');data=read_json(path);data['profile']=False;write_json(path,data)
            with self.assertRaises(ValueError):study.check_request(value,job,directory,identity,request)
    def test_gate_labels_bind_real_commands(self):
        for gate in ['regular','oracle','memcheck','racecheck','initcheck','synccheck','project']:
            with self.assertRaises(ValueError):budget.validate_gate_command(gate,['true'])
        self.assertTrue(budget.validate_gate_command('oracle',['bash','tools/lp_exec_gpu_check.sh','/tmp/exec_device-test','regular']))
        with self.assertRaises(ValueError):budget.validate_gate_command('memcheck',['bash','tools/lp_exec_gpu_check.sh','/tmp/exec_device-test','regular'])
    def test_project_acceptance_binds_complete_request(self):
        value=budget.protocol();name=value['acceptance_instances'][0]
        identity=dict(source_tree_sha256='a'*64,exec_binary_sha256='b'*64,code_object_sha256='c'*64)
        request=dict(schema_version=1,mode='cached',model_sha256=study.instances(value)[name]['model']['sha256'],source_tree_sha256=identity['source_tree_sha256'],executable_sha256=identity['exec_binary_sha256'],code_object_sha256=identity['code_object_sha256'],device=value['device'],options=dict(value['solve'],iteration_limit=value['acceptance_work'],time_limit_ms=30000),method=dict(value['lp_settings'],iteration_limit=value['acceptance_work']),profile=False,device_buffer_bytes=value['limits']['device_buffer_bytes'])
        acceptance.check_project_request(value,identity,name,'cached',request)
        for field in ['source_tree_sha256','executable_sha256','code_object_sha256','device','device_buffer_bytes']:
            altered=dict(request);altered[field]=1 if field=='device_buffer_bytes' else 'd'*64
            with self.assertRaises(ValueError):acceptance.check_project_request(value,identity,name,'cached',altered)
    def test_freeze_requires_legacy_discovery_dependency(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            for name in ['lp_pdhg.cubin','lp_pdhg_tuned.cubin','lp_pdhg_precision.cubin','lp_pdhg_exec.cubin']:
                (directory/name).write_bytes(b'fixture')
            with self.assertRaises(FileNotFoundError):study.image_inventory(directory)
            (directory/'schedule_eval.cubin').write_bytes(b'discovery fixture')
            inventory=study.image_inventory(directory)
            self.assertEqual(len(inventory),5)
            self.assertEqual(inventory['schedule_eval.cubin'],study.file_hash(directory/'schedule_eval.cubin'))
    def test_child_failure_is_not_successful_supervision(self):
        self.assertEqual(study.worker_status(dict(reason='completed',returncode=2),0),'process_failure')
        self.assertEqual(study.worker_status(dict(reason='completed',returncode=0),0),'completed')
        self.assertEqual(study.worker_status(dict(reason='timeout',returncode=-2),0),'timeout')
        self.assertEqual(study.worker_status(None,1),'missing_worker')
    def test_interrupted_attempt_preserves_partial_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);key='gpup-exec-v1-timing-simulated'
            write_json(directory/(key+'.intent.json'),dict(id=key,status='reserved'))
            partial=directory/(key+'.endpoint.json');partial.write_text('[incomplete')
            class Ledger:
                def attempted(self):return {key}
            study.recover(directory,Ledger())
            saved=read_json(directory/(key+'.trial.json'))
            self.assertEqual(saved['status'],'interrupted');self.assertIsNone(saved['assessment'])
            self.assertIsNotNone(saved['artifacts']['endpoint']);self.assertEqual(partial.read_text(),'[incomplete')
if __name__=='__main__':unittest.main()
