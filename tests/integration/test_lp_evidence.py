"""SPEC-0015 compact evidence and study CLI contracts; no GPU required."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from lp_protocol import read_json, write_json
from validate_artifacts import validator

BINARY = ROOT / 'target/debug/optimizer'


class CompactCliTests(unittest.TestCase):
    def call(self, args):
        return subprocess.run([str(BINARY), *map(str, args)], capture_output=True, text=True, timeout=30)

    def solve(self, directory, name='source', format=None, model=None):
        base = read_json(ROOT / 'benchmarks/configs/lp-copt-comparison-v1.json')
        write_json(directory / 'solve.json', dict(base['solve'], iteration_limit=3))
        write_json(directory / 'method.json', dict(base['lp_settings'], iteration_limit=3, check_interval=2))
        endpoint = directory / (name + '.json')
        args = ['lp-study', 'solve', '--model', model or ROOT / 'examples/lp-model-v1.json',
                '--config', directory / 'solve.json', '--backend', 'host-lp',
                '--lp-settings', directory / 'method.json', '--lp-evidence', endpoint]
        if format is not None:
            args += ['--evidence-format', format]
        result = self.call(args)
        self.assertEqual(result.returncode, 1, result.stderr)
        return endpoint, result

    def test_default_legacy_compact_stdout_and_verified_roundtrip(self):
        model = ROOT / 'examples/lp-model-v1.json'
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            legacy, result = self.solve(d)
            original = read_json(legacy)
            validator('lp-endpoint-v1.schema.json').validate(original)
            self.assertEqual(json.loads(result.stdout), original['record'])
            compact, result = self.solve(d, 'direct', 'compact-v1')
            value = read_json(compact)
            validator('lp-compact-endpoint-v1.schema.json').validate(value)
            self.assertEqual(json.loads(result.stdout), value['endpoint']['assessment'])
            self.assertNotIn('validation', value['endpoint']['record'])
            self.assertNotIn('\n', compact.read_text())
            converted = d / 'converted.json'
            result = self.call(['lp-study', 'transcode', '--model', model, '--evidence', legacy,
                                '--output', converted, '--evidence-format', 'compact-v1'])
            self.assertEqual(result.returncode, 0, result.stderr)
            validator('lp-compact-endpoint-v1.schema.json').validate(read_json(converted))
            restored = d / 'restored.json'
            result = self.call(['lp-study', 'transcode', '--model', model, '--evidence', converted,
                                '--output', restored, '--evidence-format', 'legacy'])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(restored.read_bytes(), legacy.read_bytes())
            for path in [legacy, compact, converted, restored]:
                result = self.call(['lp-study', 'verify', '--model', model, '--evidence', path])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['classification'], 'work_limit')
            for source, target_format in [(compact, None), (compact, 'legacy'), (legacy, 'compact-v1')]:
                output = d / ('replay-' + source.stem + '-' + str(target_format) + '.json')
                args = ['lp-study', 'replay', '--model', model, '--evidence', source, '--output', output]
                if target_format:
                    args += ['--evidence-format', target_format]
                result = self.call(args)
                self.assertEqual(result.returncode, 1, result.stderr)
                replay = read_json(output)
                expected_compact = target_format == 'compact-v1' or (target_format is None and source == compact)
                self.assertEqual('format' in replay, expected_compact)
                endpoint = replay['endpoint'] if expected_compact else replay
                self.assertEqual(endpoint['record']['candidate'], original['record']['candidate'])
                self.assertEqual(endpoint['diagnostics']['dual'], original['diagnostics']['dual'])
                self.assertEqual(endpoint['assessment'], original['assessment'])

    def test_flag_scope_preflight_and_preserved_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            source, _ = self.solve(d, format='compact-v1')
            existing = d / 'existing.json'
            existing.write_text('preserve')
            missing = d / 'missing.json'
            base = ['lp-study', 'solve', '--model', missing, '--config', missing,
                    '--backend', 'cuda-lp-tuned', '--lp-evidence', existing,
                    '--evidence-format', 'compact-v1']
            result = self.call(base)
            self.assertIn('already exists', result.stderr)
            self.assertEqual(existing.read_text(), 'preserve')
            existing.unlink()
            existing.with_suffix('.partial').write_text('partial evidence')
            result = self.call(base)
            self.assertIn('already exists', result.stderr)
            self.assertEqual(existing.with_suffix('.partial').read_text(), 'partial evidence')
            cases = [
                ['solve', '--evidence-format', 'compact-v1'],
                ['lp-study', 'verify', '--evidence-format', 'legacy'],
                ['lp-study', 'transcode', '--model', missing],
                ['lp-study', 'solve', '--evidence-format', 'gzip'],
                ['lp-study', 'solve', '--evidence-format', 'legacy', '--evidence-format', 'compact-v1'],
                ['lp-study', 'replay', '--cost-profile', missing],
                ['lp-study', 'transcode', '--model-byte-limit', 134217729, '--evidence-format', 'legacy'],
                ['lp-study', 'transcode', '--model-byte-limit', 0, '--evidence-format', 'legacy'],
                ['lp-study', 'transcode', '--model', ROOT / 'examples/lp-model-v1.json', '--evidence', source,
                 '--output', source, '--evidence-format', 'legacy'],
            ]
            original = source.read_bytes()
            for args in cases:
                result = self.call(args)
                self.assertEqual(result.returncode, 2, (args, result.stderr))
            self.assertEqual(source.read_bytes(), original)

    def test_extended_evidence_limit_on_verify_replay_and_transcode(self):
        model = ROOT / 'examples/lp-model-v1.json'
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            source, _ = self.solve(d, format='compact-v1')
            padded = d / 'padded.json'
            padded.write_bytes(source.read_bytes() + b' ' * (17 * 1024 * 1024))
            for command in ['verify', 'replay', 'transcode']:
                args = ['lp-study', command, '--model', model, '--evidence', padded]
                if command != 'verify':
                    args += ['--output', d / (command + '.json')]
                if command == 'transcode':
                    args += ['--evidence-format', 'legacy']
                result = self.call(args)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('input exceeds', result.stderr)
                result = self.call([*args, '--model-byte-limit', 128 * 1024 * 1024])
                self.assertEqual(result.returncode, 1 if command == 'replay' else 0, result.stderr)

    def test_schema_and_runtime_refuse_compact_presence_and_identity_mutations(self):
        model = ROOT / 'examples/lp-model-v1.json'
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            source, _ = self.solve(d, format='compact-v1')
            original = read_json(source)
            malformed = []
            v = copy.deepcopy(original); del v['validation_sha256']; malformed.append(v)
            v = copy.deepcopy(original); v['endpoint']['record']['validation'] = None; malformed.append(v)
            v = copy.deepcopy(original); v['validation_sha256'] = 'A' * 64; malformed.append(v)
            v = copy.deepcopy(original); v['extra'] = 1; malformed.append(v)
            v = copy.deepcopy(original); del v['endpoint']['record']['candidate']; malformed.append(v)
            v = copy.deepcopy(original); v['endpoint']['diagnostics'] = []; malformed.append(v)
            for n, v in enumerate(malformed):
                with self.assertRaises(Exception):
                    validator('lp-compact-endpoint-v1.schema.json').validate(v)
                path = d / f'bad-{n}.json'; write_json(path, v)
                result = self.call(['lp-study', 'verify', '--model', model, '--evidence', path])
                self.assertEqual(result.returncode, 2, result.stderr)
            v = copy.deepcopy(original); v['validation_sha256'] = '0' * 64
            path = d / 'false-digest.json'; write_json(path, v)
            validator('lp-compact-endpoint-v1.schema.json').validate(v)
            result = self.call(['lp-study', 'verify', '--model', model, '--evidence', path])
            self.assertIn('validation digest differs', result.stderr)
            self.assertEqual(result.returncode, 2)


class EvidenceStudyTests(unittest.TestCase):
    def fixture(self, root):
        import hashlib
        import shutil
        from lp_evidence_budget import protocol
        from lp_protocol import Ledger
        value = protocol()
        pending = [value[k] for k in ['budget_authority', 'previous_protocol', 'decision']]
        seen = set()
        while pending:
            ref = pending.pop(); name = ref['path']
            if name in seen:
                continue
            seen.add(name)
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
            if target.suffix == '.json':
                doc = read_json(target)
                pending += [doc[k] for k in ['budget_authority', 'previous_protocol', 'decision', 'source_campaign'] if k in doc]
        directory = root / 'artifacts/lp-campaign-ledgers/gpup-baseline-v1'
        with Ledger(directory, value['budget_authority']['sha256'], value['phase_gpu_seconds'], cumulative_ns=value['cumulative_gpu_ns']) as ledger:
            ledger.bind_output(root / 'artifacts/gpup-baseline-v1')
            r = ledger.reserve('synthetic-prefix', 1, resource='cpu'); ledger.settle(r, 1)
        data = (directory / 'ledger.jsonl').read_bytes()
        value.update(prior_events=2, prior_gpu_ns=0, prior_ledger_sha256=hashlib.sha256(data).hexdigest())
        return value, directory

    def test_frozen_grid_format_identity_and_no_added_allowance(self):
        from lp_evidence_budget import protocol
        from benchmark_lp_evidence import jobs, configuration_hash
        value = protocol(); schedule = list(jobs(value))
        self.assertEqual(len(schedule), 24)
        self.assertEqual(len({j['id'] for j in schedule}), 24)
        self.assertEqual(schedule, list(jobs(value)))
        self.assertEqual({j['instance']['id'] for j in schedule}, set(value['instances']))
        self.assertEqual(sum(36 for _ in schedule), 864)
        self.assertEqual(value['additional_gpu_seconds'], 0)
        self.assertNotEqual(configuration_hash(value, value['configurations'][0]), configuration_hash(value, value['configurations'][1]))
        for field, replacement in [('timing_repetitions', 4), ('additional_gpu_seconds', 1), ('order_seed', 42)]:
            wrong = copy.deepcopy(value); wrong[field] = replacement
            with self.assertRaises(Exception):
                validator('lp-evidence-study-v1.schema.json').validate(wrong)

    def test_synthetic_authority_chain_prefix_output_and_cap_checks(self):
        from lp_evidence_budget import ledger_for
        from lp_protocol import NS
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); value, directory = self.fixture(root)
            with ledger_for(value, root) as ledger:
                self.assertEqual(ledger.totals(), 0)
            for field, replacement in [('cumulative_gpu_ns', value['cumulative_gpu_ns'] + 1), ('additional_gpu_seconds', 1),
                                       ('prior_gpu_ns', 1), ('prior_ledger_sha256', '0' * 64), ('combined_cap_seconds', 1201)]:
                wrong = copy.deepcopy(value); wrong[field] = replacement
                with self.assertRaises(ValueError):
                    ledger_for(wrong, root)
            for field in ['decision', 'previous_protocol', 'budget_authority']:
                wrong = copy.deepcopy(value); wrong[field]['sha256'] = '0' * 64
                with self.assertRaises(ValueError):
                    ledger_for(wrong, root)
            wrong = copy.deepcopy(value); wrong['categories']['timing']['phase'] = 'screening'
            with self.assertRaises(ValueError):
                ledger_for(wrong, root)
            wrong = copy.deepcopy(value); wrong['categories']['timing']['seconds'] = 901
            with self.assertRaises(ValueError):
                ledger_for(wrong, root)
            binding = directory / 'output.json'; saved = read_json(binding)
            write_json(binding, dict(saved, output_path=str(root / 'other')))
            with self.assertRaises(ValueError):
                ledger_for(value, root)
            write_json(binding, saved)
            value['categories']['timing']['seconds'] = 2
            value['categories']['accept']['seconds'] = 2
            value['combined_cap_seconds'] = 3
            with ledger_for(value, root) as ledger:
                with self.assertRaises(ValueError):
                    ledger.reserve(value['id'] + '-timing-wrong', 1, phase='repeatability')
                r = ledger.reserve(value['id'] + '-timing-one', 2, phase='ablations'); ledger.settle(r, 2 * NS)
                with self.assertRaises(ValueError):
                    ledger.reserve(value['id'] + '-timing-over', 1, phase='ablations')
                ledger.reserve(value['id'] + '-accept-crash', 1, phase='repeatability')
            with ledger_for(value, root) as ledger:
                self.assertEqual(ledger.usage('accept'), NS)
                with self.assertRaises(ValueError):
                    ledger.reserve(value['id'] + '-accept-new', 1, phase='repeatability')
                with self.assertRaises(ValueError):
                    ledger.reserve(value['id'] + '-timing-one', 1, phase='ablations')

    def test_pairing_uses_median_paired_ratios_and_numerical_digest_keeps_bits(self):
        from report_lp_evidence import paired_ratios
        from report_lp_copt import numerical_digest
        self.assertEqual(paired_ratios([(10, 10), (100, 20), (100, 100)], resamples=100)['ratio'], 1.0)
        self.assertIsNone(paired_ratios([]))
        with self.assertRaises(ValueError):
            paired_ratios([(0, 1)])
        e = dict(record=dict(elapsed_ms=1, candidate=[0.0], validation={}), model_sha256='a' * 64,
                 diagnostics=dict(dual=[-0.0], iterations=1, assessment_iteration=1, restarts=0), assessment={})
        other = copy.deepcopy(e); other['record'].pop('validation'); other['record']['elapsed_ms'] = 9
        self.assertEqual(numerical_digest(e), numerical_digest(other))
        other['diagnostics']['dual'] = [0.0]
        self.assertNotEqual(numerical_digest(e), numerical_digest(other))


    def test_report_refuses_format_command_limits_and_failed_worker_promotion(self):
        from lp_evidence_budget import protocol, CONFIG
        from benchmark_lp_evidence import jobs, command, configuration_hash
        from lp_protocol import file_hash
        from report_lp_evidence import check_identity, timing_eligible
        value = protocol(); job = next(jobs(value)); config = job['configuration']
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); binary = directory / 'optimizer'
            trial = dict(id=job['id'], campaign_sha256=file_hash(CONFIG), instance_id=job['instance']['id'],
                         model_sha256=job['instance']['model']['sha256'], config_id=config['id'],
                         evidence_format=config['evidence_format'], config_sha256=configuration_hash(value, config),
                         requested_backend=config['backend'], repetition=job['repetition'], order=job['order'],
                         block=f'{job["instance"]["id"]}:{job["repetition"]}', mode='timing', category='timing',
                         limits=value['limits'], solve=value['solve'], lp_settings=value['lp_settings'],
                         budget_authority_sha256=value['budget_authority']['sha256'])
            request = {k: value['limits'][k] for k in ['solve_seconds', 'cleanup_seconds', 'host_rss_bytes', 'poll_ms', 'output_bytes']}
            request.update(schema_version=2, gpu_admission_seconds=3, command=command(value, job, binary, directory), directory=str(directory), prefix=job['id'])
            check_identity(value, job, trial, request, directory, binary, file_hash(CONFIG))
            wrong = copy.deepcopy(trial); wrong['evidence_format'] = 'other'
            with self.assertRaises(ValueError):
                check_identity(value, job, wrong, request, directory, binary, file_hash(CONFIG))
            for mutation in ['command', 'output_bytes', 'prefix']:
                wrong = copy.deepcopy(request)
                if mutation == 'command':
                    wrong['command'][-1] = 'other'
                elif mutation == 'output_bytes':
                    wrong['output_bytes'] *= 2
                else:
                    wrong['prefix'] = 'another-attempt'
                with self.assertRaises(ValueError):
                    check_identity(value, job, trial, wrong, directory, binary, file_hash(CONFIG))
        trial = dict(status='completed', endpoint_class='certified_success', requested_backend='cuda-lp-tuned', executed_backend='cuda-lp-tuned')
        worker = dict(reason='completed', returncode=0)
        endpoint = dict(record=dict(termination='optimal'))
        self.assertTrue(timing_eligible(trial, worker, endpoint))
        for failed in [dict(reason='timeout', returncode=0), dict(reason='completed', returncode=-25), None]:
            self.assertFalse(timing_eligible(trial, failed, endpoint))
        self.assertFalse(timing_eligible(dict(trial, status='invalid_evidence'), worker, endpoint))
        self.assertFalse(timing_eligible(trial, worker, dict(record=dict(termination='iteration_limit'))))


    def test_report_ledger_validation_is_read_only_and_refuses_corruption(self):
        from lp_protocol import Ledger
        from report_lp_evidence import checked_ledger
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); value, directory = self.fixture(root)
            path = directory / 'ledger.jsonl'; original = path.read_bytes()
            self.assertEqual(len(checked_ledger(path, value)), 2)
            self.assertEqual(path.read_bytes(), original)
            for bad in [original[:-1], original.replace(b'"sequence":0', b'"sequence":9')]:
                self.assertNotEqual(bad, original)
                path.write_bytes(bad)
                with self.assertRaises(ValueError):
                    checked_ledger(path, value)
                self.assertEqual(path.read_bytes(), bad)
            path.write_bytes(original)
            with Ledger(directory, value['budget_authority']['sha256']) as ledger:
                ledger.reserve('unfinished', 1, resource='cpu')
            pending = path.read_bytes()
            with self.assertRaises(ValueError):
                checked_ledger(path, value)
            self.assertEqual(path.read_bytes(), pending)
            self.assertFalse(list(directory.glob('torn-*')))
