"""SPEC-0016 host input reuse, strict before/after identity and bounded authority."""
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
from lp_host_budget import protocol, ledger_for, CONFIG
from benchmark_lp_host import jobs, command, configuration_hash
from report_lp_host import check_identity, timing_eligible
from validate_artifacts import validator


class HostInputCliTests(unittest.TestCase):
    def call(self, args):
        return subprocess.run([str(ROOT / 'target/debug/optimizer'), *map(str, args)], capture_output=True, text=True, timeout=30)

    def test_one_model_reconstruction_two_sparse_programs_and_fresh_verification(self):
        from lp_cost import validate_profile
        from report_lp_copt import numerical_digest
        value = protocol()
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_json(directory / 'solve.json', dict(value['solve'], iteration_limit=3))
            write_json(directory / 'method.json', dict(value['lp_settings'], iteration_limit=3, check_interval=2))
            model = ROOT / 'examples/lp-model-v1.json'; outputs = []; counts = []
            for fmt in ['legacy', 'compact-v1']:
                path = directory / (fmt + '.json'); cost = directory / (fmt + '.cost.json')
                result = self.call(['lp-study', 'solve', '--model', model, '--config', directory / 'solve.json',
                                    '--backend', 'host-lp', '--lp-settings', directory / 'method.json',
                                    '--lp-evidence', path, '--evidence-format', fmt, '--cost-profile', cost])
                self.assertEqual(result.returncode, 1, result.stderr)
                raw = read_json(cost); validate_profile(raw)
                calls = {name: sum(s['calls'] for s in raw['scopes'] if s['path'][-1] == name) for name in
                         ['json_parse', 'model_validation_canonicalization', 'sparse_operator_construction',
                          'original_program_assessment', 'candidate_feasibility_objective', 'dual_certification', 'gap_assessment']}
                self.assertEqual([calls[k] for k in ['json_parse', 'model_validation_canonicalization', 'sparse_operator_construction', 'original_program_assessment']], [1, 1, 2, 1])
                self.assertGreaterEqual(calls['candidate_feasibility_objective'], 2)
                self.assertGreaterEqual(calls['dual_certification'], 2)
                counts.append(calls)
                endpoint = read_json(path); endpoint = endpoint.get('endpoint', endpoint); outputs.append(endpoint)
                self.assertEqual(endpoint['assessment']['classification'], 'work_limit')
                verification = directory / (fmt + '.verify.cost.json')
                result = self.call(['lp-study', 'verify', '--model', model, '--evidence', path, '--cost-profile', verification])
                self.assertEqual(result.returncode, 0, result.stderr)
                scopes = read_json(verification)['scopes']
                for name in ['json_parse', 'model_validation_canonicalization', 'candidate_feasibility_objective', 'dual_certification']:
                    self.assertTrue(any(s['path'][-1] == name and s['calls'] >= 1 for s in scopes), name)
                changed = read_json(model); changed['objective']['offset'] += 1.0
                write_json(directory / 'changed.json', changed)
                result = self.call(['lp-study', 'verify', '--model', directory / 'changed.json', '--evidence', path])
                self.assertEqual(result.returncode, 2, result.stderr)
                replay = directory / (fmt + '.replay.json')
                result = self.call(['lp-study', 'replay', '--model', model, '--evidence', path, '--output', replay])
                self.assertEqual(result.returncode, 1, result.stderr)
                repeated = read_json(replay); repeated = repeated.get('endpoint', repeated)
                self.assertEqual(numerical_digest(endpoint), numerical_digest(repeated))
            self.assertEqual(counts[0], counts[1])
            self.assertEqual(numerical_digest(outputs[0]), numerical_digest(outputs[1]))


class HostStudyTests(unittest.TestCase):
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
        self.assertEqual(len(schedule), 28)
        self.assertEqual(len({j['id'] for j in schedule}), 28)
        self.assertEqual(schedule, list(jobs(value)))
        self.assertEqual(sum(j['mode'] == 'timing' for j in schedule), 24)
        self.assertEqual(sum(j['mode'] == 'profile' for j in schedule), 4)
        self.assertEqual(value['additional_gpu_seconds'], 0)
        self.assertNotEqual(configuration_hash(value, value['configurations'][0]), configuration_hash(value, value['configurations'][1]))
        for field, replacement in [('timing_repetitions', 4), ('additional_gpu_seconds', 1), ('order_seed', 42), ('combined_cap_seconds', 1401)]:
            wrong = copy.deepcopy(value); wrong[field] = replacement
            with self.assertRaises(Exception):
                validator('lp-host-study-v1.schema.json').validate(wrong)

    def test_synthetic_authority_prefix_binding_and_all_caps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); value, directory = self.fixture(root)
            with ledger_for(value, root) as ledger:
                self.assertEqual(ledger.totals(), 0)
            for field, replacement in [('cumulative_gpu_ns', value['cumulative_gpu_ns'] + 1), ('additional_gpu_seconds', 1),
                                       ('prior_gpu_ns', 1), ('prior_ledger_sha256', '0' * 64), ('combined_cap_seconds', 1401)]:
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
                config = job['configuration']; binary = directory / config['id']
                trial = dict(id=job['id'], campaign_sha256=file_hash(CONFIG), instance_id=job['instance']['id'],
                             model_sha256=job['instance']['model']['sha256'], config_id=config['id'],
                             evidence_format=config['evidence_format'], config_sha256=configuration_hash(value, config),
                             requested_backend=config['backend'], repetition=job['repetition'], order=job['order'],
                             block=f'{job["instance"]["id"]}:{job["repetition"]}', mode=job['mode'], category=job['mode'],
                             limits=value['limits'], solve=value['solve'], lp_settings=value['lp_settings'],
                             budget_authority_sha256=value['budget_authority']['sha256'])
                request = {k: value['limits'][k] for k in ['solve_seconds', 'cleanup_seconds', 'host_rss_bytes', 'poll_ms', 'output_bytes']}
                request.update(schema_version=2, gpu_admission_seconds=3, command=command(value, job, binary, directory), directory=str(directory), prefix=job['id'])
                check_identity(value, job, trial, request, directory, binary, file_hash(CONFIG))
                with self.assertRaises(ValueError):
                    check_identity(value, job, trial, request, directory, directory / 'other', file_hash(CONFIG))
                for field in ['mode', 'category', 'config_id']:
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


if __name__ == '__main__':
    unittest.main()
