"""SPEC-0018 frozen setup identity and inherited resource authority, without GPU data."""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests/integration'))
from lp_setup_budget import protocol, ledger_for
from benchmark_lp_setup import jobs, command, check_setup
from lp_protocol import file_hash, read_json, write_json, NS
from validate_artifacts import validator
from test_lp_adaptive_cost import AdaptiveCostStudyTests

class SetupTests(unittest.TestCase):
    def test_frozen_grid(self):
        value = protocol(); schedule = list(jobs(value))
        self.assertEqual(len(schedule), 32)
        self.assertEqual(len({j['id'] for j in schedule}), 32)
        self.assertEqual(sum(j['mode'] == 'timing' for j in schedule), 24)
        self.assertEqual(sum(j['mode'] == 'profile' and j['configuration']['variant'] == 'baseline' for j in schedule), 4)
        self.assertEqual(schedule, list(jobs(value)))
        for field, replacement in [('timing_repetitions', 4), ('additional_gpu_seconds', 1), ('order_seed', 42)]:
            wrong = copy.deepcopy(value); wrong[field] = replacement
            with self.assertRaises(Exception): validator('lp-setup-study-v1.schema.json').validate(wrong)
        # Command uses a committed fixture; no generated model prerequisite.
        job = copy.deepcopy(schedule[0]);job['instance']['model'] = dict(path='examples/lp-model-v1.json', sha256=file_hash(ROOT/'examples/lp-model-v1.json'))
        args = command(value, job, Path('/binary'), Path('/output'))
        self.assertIn('--cuda-context', args); self.assertIn('--setup-receipt', args)
        self.assertEqual('--lp-adaptive' in args, job['configuration']['adaptive'] is not None)

    def test_clean_source_authority_and_caps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); parent, directory = AdaptiveCostStudyTests().fixture(root)
            value = protocol(); parent_path = root / value['previous_protocol']['path']; write_json(parent_path, parent)
            value['previous_protocol']['sha256'] = file_hash(parent_path)
            decision = root/value['decision']['path']; decision.parent.mkdir(parents=True, exist_ok=True); decision.write_bytes((ROOT/value['decision']['path']).read_bytes())
            value.update(prior_events=parent['prior_events'], prior_gpu_ns=0, prior_ledger_sha256=parent['prior_ledger_sha256'])
            with ledger_for(value, root) as ledger: self.assertEqual(ledger.totals(), 0)
            for field, replacement in [('additional_gpu_seconds', 1), ('cumulative_gpu_ns', value['cumulative_gpu_ns']+1), ('prior_gpu_ns', 1), ('prior_ledger_sha256', '0'*64)]:
                wrong = copy.deepcopy(value); wrong[field]=replacement
                with self.assertRaises(ValueError): ledger_for(wrong, root)
            for category in value['categories']:
                wrong = copy.deepcopy(value); wrong['categories'][category]['seconds'] += 1
                with self.assertRaises(ValueError): ledger_for(wrong, root)
            for rule in value['categories'].values(): rule['seconds']=2
            value['combined_cap_seconds']=3
            with ledger_for(value, root) as ledger:
                with self.assertRaises(ValueError): ledger.reserve(value['id']+'-profile-bad',1,phase='ablations')
                r=ledger.reserve(value['id']+'-timing-one',2,phase='ablations');ledger.settle(r,2*NS)
                ledger.reserve(value['id']+'-profile-crash',1,phase='repeatability')
            with ledger_for(value, root) as ledger:
                self.assertEqual(ledger.usage('profile'),NS)
                with self.assertRaises(ValueError): ledger.reserve(value['id']+'-accept-over',1,phase='repeatability')
                with self.assertRaises(ValueError): ledger.reserve(value['id']+'-timing-one',1,phase='ablations')

    def test_strict_report_request_identity(self):
        from report_lp_setup import check_identity
        from benchmark_lp_setup import configuration_hash
        value=protocol(); job=copy.deepcopy(next(jobs(value)))
        job['instance']['model']=dict(path='examples/lp-model-v1.json',sha256=file_hash(ROOT/'examples/lp-model-v1.json'))
        config=job['configuration']; directory=Path('/output'); binary=Path('/binary')
        trial=dict(id=job['id'],campaign_sha256='a'*64,model_sha256=job['instance']['model']['sha256'],instance_id=job['instance']['id'],config_id=config['id'],variant=config['variant'],policy_id=config['policy_id'],adaptive=config['adaptive'],cuda_context=config['cuda_context'],evidence_format=config['evidence_format'],config_sha256=configuration_hash(value,config),requested_backend=config['backend'],repetition=job['repetition'],order=job['order'],block=f'{job["instance"]["id"]}:{config["policy_id"]}:{job["repetition"]}',mode=job['mode'],category=job['mode'],limits=value['limits'],solve=value['solve'],lp_settings=value['lp_settings'],budget_authority_sha256=value['budget_authority']['sha256'])
        request={k:value['limits'][k] for k in ['solve_seconds','cleanup_seconds','host_rss_bytes','poll_ms','output_bytes']}
        request.update(schema_version=2,gpu_admission_seconds=3,command=command(value,job,binary,directory),directory=str(directory),prefix=job['id'])
        check_identity(value,job,trial,request,directory,binary,'a'*64)
        for field in ['cuda_context','mode','variant','policy_id']:
            wrong=copy.deepcopy(trial);wrong[field]='wrong'
            with self.assertRaises(ValueError):check_identity(value,job,wrong,request,directory,binary,'a'*64)
        with self.assertRaises(ValueError):check_identity(value,job,trial,request,directory,Path('/wrong'),'a'*64)

    def test_trial_artifacts_cannot_be_substituted_between_attempts(self):
        from report_lp_setup import check_trial_artifacts
        from benchmark_lp import reference
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            suffixes = dict(worker='.worker.json', stdout='.stdout', stderr='.stderr',
                            endpoint='.endpoint.json', activity='.activity.json',
                            cost='.cost.json', setup='.setup.json')
            trial = dict(id='attempt-a')
            for role, suffix in suffixes.items():
                path = directory / ('attempt-a' + suffix)
                path.write_text('{}')
                trial[role] = reference(directory, path)
            check_trial_artifacts(directory, trial)
            for role, suffix in suffixes.items():
                substitute = directory / ('attempt-b' + suffix)
                substitute.write_text('{}')  # Even identical bytes belong to another attempt.
                wrong = copy.deepcopy(trial)
                wrong[role] = reference(directory, substitute)
                with self.assertRaisesRegex(ValueError, 'artifact path'):
                    check_trial_artifacts(directory, wrong)
            wrong = copy.deepcopy(trial)
            wrong['setup']['sha256'] = '0' * 64
            with self.assertRaises(ValueError):
                check_trial_artifacts(directory, wrong)

    def test_receipt_requires_policy_endpoint_and_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp); endpoint=directory/'endpoint';endpoint.write_text('{}')
            path=directory/'receipt'
            value=dict(schema_version=1,requested='user',observed='user',device='GPU-a',status='passed',endpoint_sha256=file_hash(endpoint),error=None,
                events=[dict(operation='context_create_user',ok=True,detail='GPU-a'),dict(operation='context_destroy_user',ok=True,detail='0')])
            write_json(path,value); check_setup(path,endpoint,'user','GPU-a')
            for field, replacement in [('requested','primary-experimental'),('observed',None),('device','GPU-b'),('endpoint_sha256','0'*64),('status','failed'),('events',value['events'][:1])]:
                wrong=copy.deepcopy(value);wrong[field]=replacement;write_json(path,wrong)
                with self.assertRaises(ValueError):check_setup(path,endpoint,'user','GPU-a')
            wrong=copy.deepcopy(value);wrong['events'][-1]['ok']=False;write_json(path,wrong)
            with self.assertRaises(ValueError):check_setup(path,endpoint,'user','GPU-a')

if __name__ == '__main__': unittest.main()
