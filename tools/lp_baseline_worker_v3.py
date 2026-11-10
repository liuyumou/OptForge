"""Fresh bounded baseline worker: native export, independent checker, evidence."""
import argparse
import os
from pathlib import Path
import resource
import subprocess
import threading
import time

from lp_baseline_common_v3 import (DEVICE, NS, ROOT, canonical_file, checked, load,
    put, ref, require, tiny_model, verify_certificate)
from lp_baseline_contract import validate_endpoint
import lp_baseline_adapters_v3 as adapters


class Activity:
    """Read-only process-attributed NVML observations; never a hard memory claim."""
    def __init__(self, enabled):
        self.enabled = enabled
        self.samples = []
        self.error = None
        self.stop = threading.Event()
        self.process = None
        self.thread = None

    def __enter__(self):
        if self.enabled:
            index = subprocess.check_output(['nvidia-smi', '--id=' + DEVICE,
                '--query-gpu=index', '--format=csv,noheader,nounits'], text=True, timeout=2).strip()
            self.process = subprocess.Popen(['nvidia-smi', 'pmon', '-i', index, '-s', 'um', '-d', '1'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            def collect():
                for line in self.process.stdout:
                    fields = line.split()
                    if len(fields) >= 12 and fields[1].isdigit():
                        pid = int(fields[1])
                        current, owned = pid, pid == os.getpid()
                        for _ in range(32):
                            if owned or current <= 1: break
                            try:
                                status = Path(f'/proc/{current}/status').read_text()
                                current = int(next(s.split()[1] for s in status.splitlines() if s.startswith('PPid:')))
                                owned = current == os.getpid()
                            except (OSError, StopIteration): break
                        sample = dict(monotonic_ns=time.monotonic_ns(), pid=int(fields[1]),
                            owned_process=owned,
                            sm_percent=int(fields[3]) if fields[3].isdigit() else None,
                            memory_mib=int(fields[9]) if fields[9].isdigit() else None)
                        self.samples.append(sample)
                        if owned and (sample['memory_mib'] or 0) > 12 * 1024:
                            self.error = 'sampled GPU memory limit exceeded'
                            # Interrupt native work promptly; guardian owns final cleanup.
                            os.kill(os.getpid(), 2)
            self.thread = threading.Thread(target=collect, daemon=True)
            self.thread.start()
        return self

    def __exit__(self, *_):
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=2)
            self.thread.join(timeout=2)


def solve_one(manifest, config, original, directory, seconds, readback, activity):
    directory.mkdir(parents=True, exist_ok=False)
    canonical_ref = canonical_file(original, directory / 'canonical.json')
    model = load(checked(canonical_ref))
    started = time.monotonic_ns()
    raw = adapters.result()
    transport = 'completed'
    error = None
    try:
        if config['solver'] in ('copt', 'cuopt'):
            raw = getattr(adapters, config['solver'])(model, config, seconds, directory, readback)
        else:
            raw = adapters.retained(model, config, seconds, directory, readback, manifest, original)
    except Exception as exc:
        transport = 'error'
        error = type(exc).__name__ + ': ' + str(exc)
        raw['limitations'].append(error)
    ended = time.monotonic_ns()
    if activity.error:
        raise ValueError(activity.error)
    observations = [s for s in activity.samples if s['pid'] == os.getpid() and started <= s['monotonic_ns'] <= ended]
    active = any((s['sm_percent'] or 0) > 0 for s in observations)
    if config['gpu'] and raw['executed_device'] == 'unknown' and active:
        raw['executed_device'] = 'gpu'
    execution = put(directory / 'execution.json', dict(schema_version=1,
        kind='lp-baseline-execution-observation', model=ref(original), canonical=canonical_ref,
        configuration=config, manifest=manifest['self_reference'], native=raw,
        process_id=os.getpid(), cpu_affinity=sorted(os.sched_getaffinity(0)),
        gpu_uuid=DEVICE if config['gpu'] else None, gpu_activity=observations,
        device_memory_policy='sampled process framebuffer memory; not hard containment',
        native_log=ref(directory/'native.log') if (directory/'native.log').exists() else None,
        retained_output=ref(directory/'native.json') if (directory/'native.json').exists() else None,
        error=error, adapter_elapsed_ns=ended-started))
    candidate = dict(schema_version=1, kind='lp-baseline-candidate', model_sha256=ref(original)['sha256'],
        row_ids=model['row_ids'], variable_ids=model['variable_ids'], primal=raw['primal'], dual=raw['dual'],
        transport=transport, native_status=raw['native_status'])
    candidate_ref = put(directory / 'candidate.json', candidate)
    certificate_start = time.monotonic_ns()
    certificate_path = directory / 'certificate.json'
    subprocess.run([str(checked(manifest['checker'])), 'check', str(original),
        str(checked(candidate_ref)), str(certificate_path)], check=True)
    certificate_ref = ref(certificate_path)
    c = verify_certificate(certificate_ref, candidate_ref, ref(original), manifest['checker'])
    certificate_ns = time.monotonic_ns() - certificate_start
    endpoint = dict(schema_version=1, kind='lp-baseline-endpoint', evidence_kind='measurement',
        model_sha256=canonical_ref['sha256'], original_sha256=model['original_sha256'],
        proposal_sha256=manifest['proposal']['sha256'], configuration_id=config['id'],
        solver=config['solver'], solver_version=config['version'], adapter=manifest['adapter'],
        environment=manifest['environment'], requested_device='gpu' if config['gpu'] else 'cpu',
        executed_device=raw['executed_device'], device_uuid=DEVICE if raw['executed_device'] == 'gpu' else None,
        gpu_evidence=execution if raw['executed_device'] == 'gpu' else None,
        algorithm_requested=config['algorithm'], algorithm_executed=raw['algorithm_executed'],
        transport=transport, native_status=raw['native_status'], row_ids=model['row_ids'], variable_ids=model['variable_ids'],
        primal=raw['primal'], dual=raw['dual'], native_reduced_costs=raw['reduced_costs'],
        dual_convention='original_units_min_lower_positive', checker=dict(state='accepted' if c['accepted'] else 'rejected', receipt=certificate_ref),
        elapsed_ns=None, native_solve_ns=raw['native_solve_ns'], certificate_ns=certificate_ns,
        limitations=raw['limitations'] + ['Primary elapsed_ns is in the controller trial after fresh worker exit; this envelope records the endpoint only.'])
    # The v1 envelope requires elapsed_ns when accepted. This is the endpoint
    # interval, explicitly not the primary cold-process trial measurement.
    endpoint['elapsed_ns'] = time.monotonic_ns() - started
    validate_endpoint(endpoint, model, canonical_ref['sha256'])
    endpoint_ref = put(directory / 'endpoint.json', endpoint)
    return dict(original=ref(original), canonical=canonical_ref, candidate=candidate_ref,
        certificate=certificate_ref, endpoint=endpoint_ref, execution=execution,
        accepted=c['accepted'], gpu_confirmed=raw['executed_device']=='gpu',
        iterations=raw['iterations'], readback=raw['readback'], error=error)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest')
    p.add_argument('job')
    a = p.parse_args()
    manifest = load(a.manifest)
    manifest['self_reference'] = ref(a.manifest)
    job = next(j for j in manifest['jobs'] if j['id'] == a.job)
    config = next(c for c in manifest['configurations'] if c['id'] == job['configuration'])
    directory = ROOT / job['directory']
    directory.mkdir(parents=True, exist_ok=False)
    require(sorted(os.sched_getaffinity(0)) == manifest['cpu_affinity'], 'worker affinity differs')
    require('LP_CPU_PHASE_SHA256' in os.environ, 'worker requires the CPU supervisor')
    if config['gpu']:
        require(os.environ.get('AI_OPTIMIZER_GPU_LEASE') == 'inherited' and os.environ.get('CUDA_VISIBLE_DEVICES') == DEVICE, 'missing pinned GPU lease')
    else:
        require(os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'CPU worker exposes GPUs')
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 << 20, 128 << 20))
    results = []
    with Activity(config['gpu']) as activity:
        if job['phase'] == 'admission':
            deadline = time.monotonic() + 20
            cases = []
            for sense in ('minimize','maximize'):
                for shape in ('ranged','equality'):
                    path = directory / (sense + '-' + shape + '.model.json')
                    put(path, tiny_model(sense, shape))
                    cases.append((path, sense + '-' + shape, True))
            cases.append((checked(job['model']), 'nontrivial', False))
            for original, name, tiny in cases:
                remaining = deadline - time.monotonic()
                require(remaining > 0, 'admission native-call deadline exhausted')
                r = solve_one(manifest, config, original, directory/name, remaining, True, activity)
                results.append(r)
                if not r['accepted'] or not r['readback']:
                    break
                if tiny:
                    candidate = load(checked(r['candidate']))
                    sign = 1 if 'minimize' in name else -1
                    require(abs(candidate['dual'][0] - sign) <= 1e-7, 'original-sense dual mapping not established')
            final = results[-1]
            passed = (len(results) == 5 and all(r['accepted'] and r['readback'] for r in results)
                and (not config['gpu'] or final['gpu_confirmed'])
                and (config['algorithm'] not in ('pdlp','tuned-pdhg') or (final['iterations'] or 0) > 0))
        else:
            results.append(solve_one(manifest, config, checked(job['model']), directory/'solve', 40, False, activity))
            passed = True  # Uncertified numerical endpoints are screening results.
    put(directory/'worker-result.json', dict(status='passed' if passed else 'refused',
        job=a.job, results=results, gpu_activity=activity.samples))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
