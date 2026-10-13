"""CPU-only adversarial review regressions for GPUP-EXEC evidence tooling."""
import copy
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import lp_exec_accept as acceptance
import lp_exec_budget as budget
import benchmark_lp_exec as study
import report_lp_exec as report
from lp_protocol import file_hash, read_json, write_json


@contextmanager
def acceptance_fixture():
    """Seven tiny receipts exercise validation without any CUDA executable."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        value = budget.protocol()
        value.update(acceptance_output='acceptance', acceptance_instances=[])
        directory = root / value['acceptance_output']
        source = directory / 'sources' / ('a' * 64)
        images = source / 'images'
        images.mkdir(parents=True)
        def ref(path):
            return dict(path=str(path.relative_to(root)), sha256=file_hash(path))
        image_refs = {}
        for name in ['schedule_eval.cubin', 'lp_pdhg.cubin', 'lp_pdhg_tuned.cubin', 'lp_pdhg_precision.cubin', 'lp_pdhg_exec.cubin']:
            path = images / name
            path.write_bytes(name.encode())
            image_refs[name] = ref(path)
        binaries = {}
        for name in ['device-cuda', 'device-schedule', 'device-lp', 'exec_device-fixture', 'lp_precision_exec-fixture']:
            path = source / name
            path.write_bytes(b'\x7fELF' + name.encode())
            binaries[name] = path
        identity = dict(source_tree_sha256='a' * 64,
                        exec_binary_sha256=file_hash(binaries['lp_precision_exec-fixture']),
                        code_object_sha256=image_refs['lp_pdhg_exec.cubin']['sha256'])
        events = []
        gates = {}
        for role in ['regular', 'oracle', 'memcheck', 'racecheck', 'initcheck', 'synccheck', 'project']:
            key = value['id'] + '-accept-review-' + role
            if role == 'regular':
                paths = [binaries[name] for name in ['device-cuda', 'device-schedule', 'device-lp']]
                args = ['bash', str(ROOT / 'tools/lp_exec_regular_check.sh'), *map(str, paths)]
                stdout = '\n'.join(f'test result: ok. {n} passed; 0 failed; 0 ignored;' for n in [14, 6, 46])
            elif role == 'project':
                paths = [binaries['lp_precision_exec-fixture']]
                args = ['python3', str(ROOT / 'tools/lp_exec_accept.py'), 'project', '--binary', str(paths[0])]
                stdout = 'three cached/uncached fixed-work pairs and six same-device replays pass'
            else:
                paths = [binaries['exec_device-fixture']]
                args = ['bash', str(ROOT / 'tools/lp_exec_gpu_check.sh'), str(paths[0]), 'regular' if role == 'oracle' else role]
                stdout = 'test result: ok. 3 passed; 0 failed; 0 ignored;'
            command = ['/usr/bin/env', 'AI_OPTIMIZER_CUDA_DIR=' + str(images), 'AI_OPTIMIZER_EXEC_ACCEPT_KEY=' + key, *args]
            request = dict(schema_version=2, gpu_admission_seconds=3, command=command,
                           directory=str(directory), prefix=key, solve_seconds=10,
                           cleanup_seconds=2, host_rss_bytes=value['limits']['host_rss_bytes'],
                           poll_ms=10, output_bytes=value['limits']['output_bytes'])
            worker = dict(reason='completed', returncode=0, leased_ns=20, elapsed_ns=10,
                          activity=dict(device=value['device'], reason='quiet'))
            gate = dict(gate=role, status='passed', source_tree_sha256=identity['source_tree_sha256'],
                        image_sha256=identity['code_object_sha256'], command=command,
                        images=copy.deepcopy(image_refs), binaries=[ref(p) for p in paths], project=None)
            for suffix, data in [('request', request), ('worker', worker)]:
                path = directory / (key + '.' + suffix + '.json')
                write_json(path, data)
                gate[suffix] = ref(path)
            for suffix, data in [('stdout', stdout), ('stderr', '')]:
                path = directory / (key + '.' + suffix)
                path.write_text(data)
                gate[suffix] = ref(path)
            if role == 'project':
                path = directory / (key + '.project.json')
                write_json(path, dict(status='passed', source_tree_sha256=identity['source_tree_sha256'],
                                      executable_sha256=identity['exec_binary_sha256'],
                                      image_sha256=identity['code_object_sha256'], pairs=[]))
                gate['project'] = ref(path)
            path = directory / (key + '.gate.json')
            write_json(path, gate)
            gates[role] = path
            for kind in ['reserve', 'settle']:
                events.append(dict(trial_id=key, kind=kind, resource='gpu', phase='repeatability',
                                   reserved_ns=16 * 10**9, charged_ns=0 if kind == 'reserve' else 20))
        ledger = root / 'ledger.jsonl'
        import json
        ledger.write_text(''.join(json.dumps(e) + '\n' for e in events))
        with patch.object(acceptance, 'ROOT', root), patch.object(acceptance, 'ledger_for', return_value=SimpleNamespace(path=ledger)):
            yield root, value, identity, gates, ref


class ExecReviewContracts(unittest.TestCase):
    def test_acceptance_binds_worker_device(self):
        with acceptance_fixture() as (root, value, identity, gates, ref):
            acceptance.check_acceptance(value, identity)
            gate = read_json(gates['oracle'])
            path = root / gate['worker']['path']
            worker = read_json(path)
            worker['activity']['device'] = 'GPU-other'
            write_json(path, worker)
            gate['worker'] = ref(path)
            write_json(gates['oracle'], gate)
            with self.assertRaisesRegex(ValueError, 'device'):
                acceptance.check_acceptance(value, identity)

    def test_acceptance_binds_archived_environment_and_executable(self):
        for mutation in ['image_directory', 'attempt_key', 'executable']:
            with self.subTest(mutation=mutation), acceptance_fixture() as (root, value, identity, gates, ref):
                gate = read_json(gates['oracle'])
                request_path = root / gate['request']['path']
                request = read_json(request_path)
                command = gate['command']
                if mutation == 'image_directory':
                    command[1] = 'AI_OPTIMIZER_CUDA_DIR=/tmp/unarchived-images'
                elif mutation == 'attempt_key':
                    command[2] = 'AI_OPTIMIZER_EXEC_ACCEPT_KEY=another-attempt'
                else:
                    path = root / 'exec_device-unarchived'
                    path.write_bytes(b'\x7fELFother')
                    command[5] = str(path)
                request['command'] = command
                write_json(request_path, request)
                gate['request'] = ref(request_path)
                write_json(gates['oracle'], gate)
                with self.assertRaisesRegex(ValueError, 'command|archive|environment'):
                    acceptance.check_acceptance(value, identity)


    def test_recovered_endpoint_assessment_stays_independent(self):
        assessed = dict(classification='certified_success', gap_closed=True)
        recovered = dict(status='interrupted', assessment=None)
        report.check_assessment(recovered, assessed)
        report.check_assessment(recovered, None)
        self.assertIsNone(recovered['assessment'])
        for status in ['completed', 'invalid_evidence', 'missing_evidence']:
            with self.subTest(status=status), self.assertRaises(ValueError):
                report.check_assessment(dict(status=status, assessment=None), assessed)
        with self.assertRaises(ValueError):
            report.check_assessment(dict(status='interrupted', assessment=assessed), None)

    def test_recovered_reservation_cannot_be_promoted_or_undercharged(self):
        value = budget.protocol()
        job = next(j for j in study.jobs(value) if j['configuration']['backend'] == 'lp-exec-v1')
        identity = dict(source_tree_sha256='a' * 64, exec_binary_sha256='b' * 64, code_object_sha256='c' * 64)
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            key = job['id']
            request = study.write_inputs(value, job, directory, identity)
            request_path = directory / (key + '.request.json')
            write_json(request_path, request)
            worker = dict(leased_ns=20, activity=dict(device=value['device']))
            write_json(directory / (key + '.worker.json'), worker)
            reserved = (study.effective(value, job)[2] + 6) * 10**9
            events = [dict(trial_id=key, kind=kind, resource='gpu', phase='screening',
                           reserved_ns=reserved, charged_ns=0 if kind == 'reserve' else reserved)
                      for kind in ['reserve', 'recover']]
            trial = dict(id=key, job=job, campaign_sha256=file_hash(budget.CONFIG),
                         source_tree_sha256=identity['source_tree_sha256'],
                         request_sha256=file_hash(request_path), status='interrupted',
                         artifacts=study.refs(directory, key), assessment=None)
            self.assertEqual(report.check_trial(value, job, trial, directory, identity, events), worker)
            trial['status'] = 'completed'
            with self.assertRaisesRegex(ValueError, 'recovered'):
                report.check_trial(value, job, trial, directory, identity, events)
            trial['status'] = 'interrupted'
            events[1]['charged_ns'] = worker['leased_ns']
            with self.assertRaisesRegex(ValueError, 'full charge'):
                report.check_trial(value, job, trial, directory, identity, events)


    def test_review_source_binding_cannot_widen_to_runtime(self):
        import hashlib
        import io
        import tarfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / 'study'
            directory.mkdir()
            contents = {'crates/solver.rs': b'measured runtime',
                        'tools/report_lp_exec.py': b'measured verifier'}
            for name, data in contents.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            with tarfile.open(directory / 'source.tar', 'w') as archive:
                digest = hashlib.sha256()
                for name, data in sorted(contents.items()):
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
                    digest.update(name.encode() + b'\0' + data + b'\0')
            for name in ['optimizer', 'lp_precision_exec', 'lp_pdhg_exec.cubin']:
                (directory / name).write_bytes(name.encode())
            source_hash = digest.hexdigest()
            identity = dict(source_tree_sha256=source_hash,
                            source_archive_sha256=file_hash(directory / 'source.tar'),
                            binary_sha256=file_hash(directory / 'optimizer'),
                            exec_binary_sha256=file_hash(directory / 'lp_precision_exec'),
                            code_object_sha256=file_hash(directory / 'lp_pdhg_exec.cubin'))
            write_json(directory / 'execution.json', identity)
            write_json(directory / 'campaign.json', {})
            write_json(directory / 'native-gate.json', dict(native=True, source_tree_sha256=source_hash))
            write_json(directory / 'code-objects.json', {'lp_pdhg_exec.cubin': identity['code_object_sha256']})
            (root / 'tools/report_lp_exec.py').write_bytes(b'reviewed verifier')
            correction = dict(path='tools/report_lp_exec.py',
                              measured_sha256=hashlib.sha256(contents['tools/report_lp_exec.py']).hexdigest(),
                              reviewed_sha256=file_hash(root / 'tools/report_lp_exec.py'))
            review = dict(identity='gpup-exec-review-corrections-v1', source_tree_sha256=source_hash, files=[correction])
            review_path = root / 'docs/benchmarks/data/exec/review-corrections.json'
            review_path.parent.mkdir(parents=True)
            write_json(review_path, review)
            with patch.object(report, 'ROOT', root):
                self.assertEqual(report.check_archive(directory, {}), identity)
                (root / 'crates/solver.rs').write_bytes(b'changed numerical worker')
                with self.assertRaisesRegex(ValueError, 'undeclared measured source'):
                    report.check_archive(directory, {})
                review['files'].append(dict(path='crates/solver.rs',
                                           measured_sha256=hashlib.sha256(contents['crates/solver.rs']).hexdigest(),
                                           reviewed_sha256=file_hash(root / 'crates/solver.rs')))
                write_json(review_path, review)
                with self.assertRaisesRegex(ValueError, 'scope'):
                    report.check_archive(directory, {})

    def test_regular_acceptance_requires_the_test_counts(self):
        with acceptance_fixture() as (root, value, identity, gates, ref):
            gate = read_json(gates['regular'])
            path = root / gate['stdout']['path']
            path.write_text('\n'.join(['test result: ok. 0 passed; 0 failed; 0 ignored;'] * 3))
            gate['stdout'] = ref(path)
            write_json(gates['regular'], gate)
            with self.assertRaisesRegex(ValueError, 'regular'):
                acceptance.check_acceptance(value, identity)


if __name__ == '__main__':
    unittest.main()
