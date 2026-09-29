"""SPEC-0017 adaptive host costs, strict before/after identity and bounded authority."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lp_protocol import Ledger, NS, file_hash, read_json, write_json
from lp_adaptive_cost_budget import protocol, ledger_for, CONFIG
from benchmark_lp_adaptive_cost import jobs, command, configuration_hash
from report_lp_adaptive_cost import check_identity, timing_eligible
from validate_artifacts import validator


class AdaptiveCostStudyTests(unittest.TestCase):
    def fixture(self, root):
        value = protocol(); pending = [value[k] for k in ['budget_authority', 'previous_protocol', 'decision']]; seen = set()
        while pending:
            ref = pending.pop(); name = ref['path']
            if name in seen:
                continue
            seen.add(name); target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
            if target.suffix == '.json':
                doc = read_json(target)
                pending += [doc[k] for k in ['budget_authority', 'previous_protocol', 'decision', 'source_campaign'] if k in doc]
        directory = root / 'artifacts/lp-campaign-ledgers/gpup-baseline-v1'
        with Ledger(directory, value['budget_authority']['sha256'], value['phase_gpu_seconds'], cumulative_ns=value['cumulative_gpu_ns']) as ledger:
            ledger.bind_output(root / 'artifacts/gpup-baseline-v1')
            r = ledger.reserve('synthetic-host-prefix', 1, resource='cpu'); ledger.settle(r, 1)
        data = (directory / 'ledger.jsonl').read_bytes()
        value.update(prior_events=2, prior_gpu_ns=0, prior_ledger_sha256=hashlib.sha256(data).hexdigest())
        return value, directory

    def test_frozen_grid_and_no_new_allowance(self):
        value = protocol(); schedule = list(jobs(value))
        self.assertEqual(len(schedule), 32)
        self.assertEqual(len({j['id'] for j in schedule}), 32)
        self.assertEqual(schedule, list(jobs(value)))
        self.assertEqual(sum(j['mode'] == 'timing' for j in schedule), 24)
        self.assertEqual(sum(j['mode'] == 'profile' for j in schedule), 8)
        self.assertEqual(value['additional_gpu_seconds'], 0)
        self.assertNotEqual(configuration_hash(value, value['configurations'][0]), configuration_hash(value, value['configurations'][1]))
        for field, replacement in [('timing_repetitions', 4), ('additional_gpu_seconds', 1), ('order_seed', 42), ('combined_cap_seconds', 1801)]:
            wrong = copy.deepcopy(value); wrong[field] = replacement
            with self.assertRaises(Exception):
                validator('lp-adaptive-cost-study-v1.schema.json').validate(wrong)

    def test_synthetic_authority_prefix_binding_and_all_caps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); value, directory = self.fixture(root)
            with ledger_for(value, root) as ledger:
                self.assertEqual(ledger.totals(), 0)
            for field, replacement in [('cumulative_gpu_ns', value['cumulative_gpu_ns'] + 1), ('additional_gpu_seconds', 1),
                                       ('prior_gpu_ns', 1), ('prior_ledger_sha256', '0' * 64), ('combined_cap_seconds', 1801)]:
                wrong = copy.deepcopy(value); wrong[field] = replacement
                with self.assertRaises(ValueError):
                    ledger_for(wrong, root)
            for field in ['decision', 'previous_protocol', 'budget_authority']:
                wrong = copy.deepcopy(value); wrong[field]['sha256'] = '0' * 64
                with self.assertRaises(ValueError):
                    ledger_for(wrong, root)
            for category in value['categories']:
                wrong = copy.deepcopy(value); wrong['categories'][category]['seconds'] += 1
                with self.assertRaises(ValueError):
                    ledger_for(wrong, root)
            binding = directory / 'output.json'; saved = read_json(binding)
            write_json(binding, dict(saved, output_path=str(root / 'other')))
            with self.assertRaises(ValueError):
                ledger_for(value, root)
            write_json(binding, saved)
            for rule in value['categories'].values():
                rule['seconds'] = 2
            value['combined_cap_seconds'] = 3
            with ledger_for(value, root) as ledger:
                with self.assertRaises(ValueError):
                    ledger.reserve(value['id'] + '-profile-wrong', 1, phase='ablations')
                r = ledger.reserve(value['id'] + '-timing-one', 2, phase='ablations'); ledger.settle(r, 2 * NS)
                with self.assertRaises(ValueError):
                    ledger.reserve(value['id'] + '-timing-over', 1, phase='ablations')
                ledger.reserve(value['id'] + '-profile-crash', 1, phase='repeatability')
            with ledger_for(value, root) as ledger:
                self.assertEqual(ledger.usage('profile'), NS)
                with self.assertRaises(ValueError):
                    ledger.reserve(value['id'] + '-accept-over', 1, phase='repeatability')
                with self.assertRaises(ValueError):
                    ledger.reserve(value['id'] + '-timing-one', 1, phase='ablations')

    def test_report_rejects_wrong_executable_mode_limits_and_success_promotion(self):
        value = protocol()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for job in [list(jobs(value))[0], list(jobs(value))[-1]]:
                # A committed input keeps identity tests independent of generated/ignored data.
                job['instance'] = dict(job['instance'], model=dict(path='examples/lp-model-v1.json',
                    sha256=file_hash(ROOT / 'examples/lp-model-v1.json')))
                config = job['configuration']; binary = directory / config['id']
                trial = dict(id=job['id'], campaign_sha256=file_hash(CONFIG), instance_id=job['instance']['id'],
                             model_sha256=job['instance']['model']['sha256'], config_id=config['id'],
                             variant=config['variant'], policy_id=config['policy_id'], adaptive=config['adaptive'],
                             evidence_format=config['evidence_format'], config_sha256=configuration_hash(value, config),
                             requested_backend=config['backend'], repetition=job['repetition'], order=job['order'],
                             block=f'{job["instance"]["id"]}:{config["policy_id"]}:{job["repetition"]}', mode=job['mode'], category=job['mode'],
                             limits=value['limits'], solve=value['solve'], lp_settings=value['lp_settings'],
                             budget_authority_sha256=value['budget_authority']['sha256'])
                request = {k: value['limits'][k] for k in ['solve_seconds', 'cleanup_seconds', 'host_rss_bytes', 'poll_ms', 'output_bytes']}
                request.update(schema_version=2, gpu_admission_seconds=3, command=command(value, job, binary, directory), directory=str(directory), prefix=job['id'])
                check_identity(value, job, trial, request, directory, binary, file_hash(CONFIG))
                with self.assertRaises(ValueError):
                    check_identity(value, job, trial, request, directory, directory / 'other', file_hash(CONFIG))
                for field in ['mode', 'category', 'config_id', 'policy_id', 'variant', 'adaptive']:
                    wrong = copy.deepcopy(trial); wrong[field] = 'wrong'
                    with self.assertRaises(ValueError):
                        check_identity(value, job, wrong, request, directory, binary, file_hash(CONFIG))
                wrong = copy.deepcopy(request); wrong['output_bytes'] *= 2
                with self.assertRaises(ValueError):
                    check_identity(value, job, trial, wrong, directory, binary, file_hash(CONFIG))
            trial = dict(status='completed', endpoint_class='certified_success', requested_backend='cuda-lp-tuned', executed_backend='cuda-lp-tuned')
            endpoint = dict(record=dict(termination='optimal')); worker = dict(reason='completed', returncode=0)
            self.assertTrue(timing_eligible(trial, worker, endpoint))
            self.assertFalse(timing_eligible(trial, dict(worker, returncode=1), endpoint))
            self.assertFalse(timing_eligible(trial, worker, dict(record=dict(termination='time_limit'))))

    def test_adaptive_policy_and_precision_image_are_verified_before_acceptance(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        import benchmark_lp_adaptive_cost as study
        value = protocol(); job = next(jobs(value)); config = job['configuration']
        endpoint = dict(model_sha256=job['instance']['model']['sha256'], requested_backend=config['backend'],
            record=dict(schema_version=5, backend=config['backend'], options=value['solve'],
                        lp_settings=value['lp_settings'], lp_adaptive=config['adaptive']),
            execution=dict(settings=config['execution'], code_object_sha256='a' * 64),
            adaptive=dict(settings=config['adaptive']), assessment={'classification': 'work_limit'})
        with patch.object(study, 'endpoint_shape', return_value=endpoint), \
             patch.object(study, 'checked_reference', return_value=Path('/synthetic/model.json')), \
             patch.object(study.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(endpoint['assessment']))):
            args = (value, job, Path('/synthetic'), Path('/synthetic/optimizer'), {'code_object_sha256': 'a' * 64})
            self.assertEqual(study.verify_endpoint(*args), endpoint)
            for section, field, replacement in [('record', 'lp_adaptive', {}), ('adaptive', 'settings', {}),
                ('execution', 'code_object_sha256', 'b' * 64), ('record', 'schema_version', 4)]:
                saved = endpoint[section][field]; endpoint[section][field] = replacement
                with self.assertRaises(ValueError): study.verify_endpoint(*args)
                endpoint[section][field] = saved
        for policy in value['policies']:
            configurations = [c for c in value['configurations'] if c['policy_id'] == policy['id']]
            self.assertEqual({c['variant'] for c in configurations}, {'baseline', 'repaired'})
            self.assertTrue(all(c['adaptive'] == policy['adaptive'] for c in configurations))
        self.assertEqual(len(value['acceptance_cases']), 12)


if __name__ == '__main__':
    unittest.main()
