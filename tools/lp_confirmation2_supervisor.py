"""SPEC-0041 supervision: finite prospective limit and explicit 100 ms observations.

One command family at a time. CPU charges are four times supervised wall time,
not sampled CPU counters. RSS is sampled and is not a hard memory enclosure.
"""
import argparse
import ctypes
import fcntl
import hashlib
import json
import math
import os
import platform
from pathlib import Path
import resource
import select
import signal
import socket
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
NS = 1_000_000_000
ADVISORY_GAP_NS = 100_000_000
PRIOR_CPU_NS = 19899822845162
CAP_CPU_NS = 35900 * NS
STAGES = dict(implementation=1600, proofs=1600, native=3800, workers=7800,
              reporting=800, margin=400)
THREAD_ENV = dict(CARGO_BUILD_JOBS='4', CMAKE_BUILD_PARALLEL_LEVEL='1',
                  RUST_TEST_THREADS='1', RAYON_NUM_THREADS='1',
                  OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
                  NVCC_THREADS='1')


class AdmissionError(RuntimeError):
    pass


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.pending')
    with temporary.open('w') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def prctl(option, value):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(option, value, 0, 0, 0):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def pidfd_open(pid):
    """Use the ordinary Linux syscall when Python lacks its optional wrapper."""
    native = getattr(os, 'pidfd_open', None)
    if native is not None:
        return native(pid)
    # Linux's generic syscall number, shared by the two supported host ABIs.
    # The container's seccomp policy still applies to this call.
    if platform.machine() not in ('x86_64', 'aarch64'):
        raise AdmissionError('pidfd_binding_unavailable_for_architecture')
    libc = ctypes.CDLL(None, use_errno=True)
    descriptor = libc.syscall(ctypes.c_long(434), ctypes.c_int(pid), ctypes.c_uint(0))
    if descriptor < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    os.set_inheritable(descriptor, False)
    return descriptor


def identity(pid):
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
    return dict(pid=pid, start_ticks=int(fields[19]), state=fields[0],
                ppid=int(fields[1]), pgid=int(fields[2]), sid=int(fields[3]))


def same_process(item):
    try:
        return identity(item['pid'])['start_ticks'] == item['start_ticks']
    except (FileNotFoundError, ProcessLookupError):
        return False


def snapshot(root, cpus, additional=()):
    """Visit every thread child list, including reparented/nested-session work."""
    pending = [root, *additional]
    found = {}
    rss = swap = hwm = threads = 0
    while pending:
        pid = pending.pop()
        if pid in found:
            continue
        try:
            item = identity(pid)
            found[pid] = item
            status = Path(f'/proc/{pid}/status').read_text()
            metrics = {line.split(':', 1)[0]: line.split()[1:]
                       for line in status.splitlines() if ':' in line}
            rss += int(metrics.get('VmRSS', ['0'])[0]) * 1024
            swap += int(metrics.get('VmSwap', ['0'])[0]) * 1024
            hwm += int(metrics.get('VmHWM', ['0'])[0]) * 1024
            for task in Path(f'/proc/{pid}/task').iterdir():
                try:
                    mask = os.sched_getaffinity(int(task.name))
                    if not mask or not mask <= cpus:
                        raise AdmissionError('affinity_changed')
                    threads += 1
                    pending.extend(map(int, (task / 'children').read_text().split()))
                except (FileNotFoundError, ProcessLookupError):
                    continue
        except (FileNotFoundError, ProcessLookupError):
            # A process may exit between discovery and reading /proc.
            continue
    return dict(processes=list(found.values()), rss_bytes=rss, swap_bytes=swap,
                sum_process_hwm_bytes=hwm, threads=threads)


def reap():
    statuses = {}
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if not pid:
            break
        statuses[pid] = os.waitstatus_to_exitcode(status)
    return statuses


def terminate_descendants(root, cpus, exclude=(), observer=None):
    """Stop tracked processes individually: descendants can create new sessions."""
    until = time.monotonic() + 1
    excluded = {root, *exclude}
    seen = {}
    while True:
        if observer is not None:
            # A failed actual resource sample must propagate, never be replaced
            # with a heartbeat or identity-only observation.
            current = observer()
            live = [p for p in current['processes'] if p['pid'] not in excluded]
        else:
            try:
                current = snapshot(root, cpus)
                live = [p for p in current['processes'] if p['pid'] not in excluded]
            except Exception:
                # Identity discovery remains possible even after an affinity failure.
                live = descendants_unchecked(root, excluded)
        for item in live:
            seen[item['pid']] = item
            if same_process(item):
                try:
                    os.kill(item['pid'], signal.SIGKILL)
                except ProcessLookupError:
                    pass
        reap()
        remaining = [p for p in descendants_unchecked(root, excluded)
                     if p['state'] != 'Z']
        if not remaining:
            reap()
            return dict(empty=True, killed=list(seen.values()))
        if time.monotonic() >= until:
            return dict(empty=False, remaining=remaining, killed=list(seen.values()))
        time.sleep(.005)


def descendants_unchecked(root, exclude=()):
    pending, found = [root], {}
    while pending:
        pid = pending.pop()
        if pid in found:
            continue
        try:
            found[pid] = identity(pid)
            for task in Path(f'/proc/{pid}/task').iterdir():
                try:
                    pending.extend(map(int, (task / 'children').read_text().split()))
                except (FileNotFoundError, ProcessLookupError):
                    pass
        except (FileNotFoundError, ProcessLookupError):
            pass
    return [item for pid, item in found.items() if pid not in {root, *exclude}]


def send(channel, value):
    raw = json.dumps(value).encode()
    if len(raw) > 65536:
        raise AdmissionError('ipc_control_frame_too_large')
    if channel.send(raw) != len(raw):
        raise AdmissionError('ipc_control_frame_short_write')


def receive(channel):
    raw, _, flags, _ = channel.recvmsg(65536)
    if flags & socket.MSG_TRUNC:
        raise AdmissionError('ipc_control_frame_truncated')
    return json.loads(raw) if raw else None


def prepare_result(request, result):
    """Persist the bounded result before returning its small control binding."""
    path = Path(request['output'] + '.coordinator-result.json')
    if path.exists():
        raise AdmissionError('immutable_coordinator_result_exists')
    atomic_json(path, result)
    raw = path.read_bytes()
    if len(raw) > 8 << 20:
        raise AdmissionError('coordinator_result_too_large')
    return dict(event='done', result_bytes=len(raw), result_sha256=hashlib.sha256(raw).hexdigest())


def publish_result(channel, request, result):
    """Keep control packets small; bind the separately durable bounded result."""
    send(channel, prepare_result(request, result))


class FinalizationSampler:
    """Continue real resource observations while cleanup/publication completes."""
    def __init__(self, channel, request, cpus, last_sample):
        self.channel, self.request, self.cpus = channel, request, cpus
        self.last = last_sample
        self.record = dict(samples=0, max_sample_gap_ns=0, max_sample_work_ns=0, peak_rss_bytes=0,
                           advisory_gap_ns=ADVISORY_GAP_NS, timing_exceedances=[])

    def sample(self):
        now = time.monotonic_ns(); request = self.request
        gap = now - self.last
        if gap > request['max_gap_ns']: raise AdmissionError('finalization_sample_gap')
        if now >= request['work_deadline_ns']: raise AdmissionError('finalization_work_deadline')
        send(self.channel, dict(event='heartbeat', timestamp_ns=now))
        observation = snapshot(os.getpid(), self.cpus, [request['guardian_pid']])
        if observation['rss_bytes'] >= request['rss_stop_bytes']: raise AdmissionError('finalization_rss_limit')
        if observation['swap_bytes']: raise AdmissionError('finalization_observed_swap')
        work = time.monotonic_ns() - now
        if work > request['max_gap_ns']: raise AdmissionError('finalization_sample_duration')
        self.record['samples'] += 1
        self.record['max_sample_gap_ns'] = max(self.record['max_sample_gap_ns'], gap)
        self.record['max_sample_work_ns'] = max(self.record['max_sample_work_ns'], work)
        self.record['peak_rss_bytes'] = max(self.record['peak_rss_bytes'], observation['rss_bytes'])
        if gap > ADVISORY_GAP_NS: self.record['timing_exceedances'].append(['sample_start_gap', self.last, gap])
        if work > ADVISORY_GAP_NS: self.record['timing_exceedances'].append(['sample_work', now, work])
        self.last = now
        return observation


def publish_result_observed(channel, request, result, sampler):
    """I/O may wait; the supervising thread must still complete real samples."""
    finished = threading.Event(); outcome = {}
    def write():
        try: outcome['message'] = prepare_result(request, result)
        except BaseException as error: outcome['error'] = error
        finally: finished.set()
    writer = threading.Thread(target=write, daemon=True)
    deadline = min(request['work_deadline_ns'], time.monotonic_ns() + request['publication_wall_seconds'] * NS)
    writer.start()
    while not finished.is_set():
        if time.monotonic_ns() >= deadline: raise AdmissionError('result_publication_deadline')
        sampler.sample()
        finished.wait(.005)
    writer.join()
    if 'error' in outcome: raise outcome['error']
    if time.monotonic_ns() >= deadline: raise AdmissionError('result_publication_deadline')
    sampler.sample()
    message = outcome['message']; message['finalization_observation'] = sampler.record
    send(channel, message)


def load_result(request, message):
    size = message.get('result_bytes')
    if type(size) is not int or not 0 < size <= 8 << 20:
        raise AdmissionError('coordinator_result_size_invalid')
    path = Path(request['output'] + '.coordinator-result.json')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        raw = stream.read(size + 1)
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != message.get('result_sha256'):
        raise AdmissionError('coordinator_result_binding_invalid')
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise AdmissionError('coordinator_result_type_invalid')
    if request.get('observed_finalization'):
        record = message.get('finalization_observation')
        scalars = {'samples', 'max_sample_gap_ns', 'max_sample_work_ns', 'peak_rss_bytes', 'advisory_gap_ns'}
        if (not isinstance(record, dict) or set(record) != scalars | {'timing_exceedances'} or
                any(type(record[k]) is not int or record[k] < 0 for k in scalars) or record['samples'] == 0 or
                record['advisory_gap_ns'] != ADVISORY_GAP_NS or not isinstance(record['timing_exceedances'], list) or
                len(record['timing_exceedances']) > 1024 or
                record['max_sample_gap_ns'] > request['max_gap_ns'] or record['max_sample_work_ns'] > request['max_gap_ns'] or
                record['peak_rss_bytes'] >= request['rss_stop_bytes']):
            raise AdmissionError('finalization_observation_invalid')
        for event in record['timing_exceedances']:
            if (not isinstance(event, list) or len(event) != 3 or event[0] not in ['sample_start_gap', 'sample_work'] or
                    type(event[1]) is not int or type(event[2]) is not int or event[1] < request['started_ns'] or
                    not ADVISORY_GAP_NS < event[2] <= request['max_gap_ns']):
                raise AdmissionError('finalization_advisory_invalid')
        result['finalization_observation'] = record
    return result


def launch(request, lock_fd, channel, cpus):
    ready_r, ready_w = os.pipe()
    release_r, release_w = os.pipe()
    pid = os.fork()
    if pid == 0:
        try:
            os.close(ready_r)
            os.close(release_w)
            os.close(lock_fd)
            channel.close()
            os.setsid()
            parent = os.getppid()
            prctl(1, signal.SIGKILL)
            if os.getppid() != parent:
                os._exit(125)
            os.sched_setaffinity(0, cpus)
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_FSIZE, (512 << 20, 512 << 20))
            limit = math.ceil(request['reserve_cpu_seconds'])
            resource.setrlimit(resource.RLIMIT_CPU, (limit, limit))
            if request['address_space_bytes']:
                amount = request['address_space_bytes']
                resource.setrlimit(resource.RLIMIT_AS, (amount, amount))
            os.write(ready_w, json.dumps(identity(os.getpid())).encode())
            os.close(ready_w)
            if os.read(release_r, 1) != b'G':
                os._exit(125)
            os.close(release_r)
            log_fd = os.open(request['log'], os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.dup2(log_fd, 1)
            os.dup2(log_fd, 2)
            os.close(log_fd)
            env = {**os.environ, **THREAD_ENV,
                   'LP_CPU_GUARDIAN_PID': str(request['guardian_pid']),
                   'LP_CPU_COORDINATOR_PID': str(os.getppid()),
                   'LP_CPU_DECLARED_MEMORY_BYTES': str(request['declared_memory_bytes']),
                   'LP_CPU_ALLOWED_CPUS': json.dumps(sorted(cpus)),
                   'LP_CPU_PHASE_SHA256': request['request_sha256'],
                   'LP_CPU_ALLOCATION_DIR': request['output']+'.allocations'}
            os.execvpe(request['command'][0], request['command'], env)
        except BaseException:
            os._exit(126)
    os.close(ready_w)
    os.close(release_r)
    descriptor = pidfd_open(pid)
    if not select.select([ready_r], [], [], 1)[0]:
        raise AdmissionError('entry_timeout')
    item = json.loads(os.read(ready_r, 8192))
    os.close(ready_r)
    current = identity(pid)
    if any(item[key] != current[key] for key in ('pid', 'start_ticks', 'pgid', 'sid')) or not os.sched_getaffinity(pid) <= cpus:
        raise AdmissionError('entry_identity_or_affinity')
    os.write(release_w, b'G')
    os.close(release_w)
    return pid, descriptor, item


def coordinator(request, lock_fd, channel, cpus):
    prctl(36, 1)
    parent_fd = pidfd_open(request['guardian_pid'])
    stopped = []
    signal.signal(signal.SIGTERM, lambda *_: stopped.append('cancelled'))
    signal.signal(signal.SIGINT, lambda *_: stopped.append('cancelled'))
    result = dict(reason='completed', returncode=None, samples=0, peak_rss_bytes=0,
                  peak_threads=0, peak_sum_process_hwm_bytes=0, max_sample_gap_ns=0, max_sample_work_ns=0, observed_swap=False,
                  observed_processes=[], entry=None, allocation_acknowledgements=[],
                  timing_exceedances=[], advisory_gap_ns=ADVISORY_GAP_NS, hard_gap_ns=request['max_gap_ns'],
                  peak_active_numerical_allocations=0)
    seen = {}
    last = time.monotonic_ns()
    last_sample = last
    try:
        pid, child_fd, item = launch(request, lock_fd, channel, cpus)
        result['entry'] = item
        send(channel, dict(event='entry', identity=item, coordinator=identity(os.getpid())))
        while True:
            now = time.monotonic_ns()
            gap = now - last
            result['max_sample_gap_ns'] = max(result['max_sample_gap_ns'], gap)
            if gap > ADVISORY_GAP_NS:
                result['timing_exceedances'].append(['sample_start_gap',last,gap])
            if gap > request['max_gap_ns']:
                raise AdmissionError('sample_gap')
            if stopped:
                raise AdmissionError(stopped[0])
            if select.select([parent_fd], [], [], 0)[0]:
                raise AdmissionError('guardian_lost')
            if now >= request['work_deadline_ns']:
                raise AdmissionError('cpu_wall_deadline')
            # Publish the actual sample start at its start. Sending this timestamp
            # only after scanning can make two individually valid scans look like
            # a stale sampler. Completion still requires every resource check and
            # the duration bound below; a progress message never grants a pass.
            send(channel, dict(event='heartbeat', timestamp_ns=now))
            last_sample = now
            observation = snapshot(os.getpid(), cpus, [request['guardian_pid']])
            allocation_path=Path(request['output']+'.allocations')
            if allocation_path.exists():
                acknowledgements=[json.loads(path.read_text()) for path in sorted(allocation_path.glob('*.json'))]
                active=[]
                for record in acknowledgements:
                    if record['phase_sha256']!=request['request_sha256'] or not 0<record['host_bytes']<=request['declared_memory_bytes']:
                        raise AdmissionError('allocation_acknowledgement_invalid')
                    if same_process(record['identity']):
                        active.append(record)
                if len(active)>request['slots'] or sum(r['host_bytes'] for r in active)>request['declared_memory_bytes']:
                    raise AdmissionError('numerical_allocation_reservations_exhausted')
                result['allocation_acknowledgements']=acknowledgements
                result['peak_active_numerical_allocations']=max(result['peak_active_numerical_allocations'],len(active))
            seen.update({(p['pid'], p['start_ticks']): p for p in observation['processes']})
            result['samples'] += 1
            result['peak_rss_bytes'] = max(result['peak_rss_bytes'], observation['rss_bytes'])
            result['peak_sum_process_hwm_bytes'] = max(result['peak_sum_process_hwm_bytes'],observation['sum_process_hwm_bytes'])
            result['peak_threads'] = max(result['peak_threads'], observation['threads'])
            result['observed_swap'] |= observation['swap_bytes'] > 0
            if observation['rss_bytes'] >= request['rss_stop_bytes']:
                raise AdmissionError('sampled_rss_limit')
            if result['observed_swap']:
                raise AdmissionError('observed_swap')
            sample_work = time.monotonic_ns() - now
            result['max_sample_work_ns'] = max(result['max_sample_work_ns'], sample_work)
            if sample_work > ADVISORY_GAP_NS:
                result['timing_exceedances'].append(['sample_work',now,sample_work])
            if sample_work > request['max_gap_ns']:
                raise AdmissionError('sample_duration')
            if select.select([child_fd], [], [], .005)[0]:
                _, status = os.waitpid(pid, 0)
                result['returncode'] = os.waitstatus_to_exitcode(status)
                if result['returncode']:
                    result['reason'] = 'command_failed'
                break
            # A 5ms pidfd wait plus work gives a target below the 10ms sample period.
            last = now
        os.close(child_fd)
    except BaseException as error:
        # Peer death may become visible through either its pidfd or its socket.
        # Both observations require the same cleanup and diagnostic identity.
        result['reason'] = ('guardian_lost' if isinstance(error,(BrokenPipeError,ConnectionResetError))
                            else str(error) or type(error).__name__)
    finally:
        sampler = FinalizationSampler(channel, request, cpus, last_sample) if request.get('observed_finalization') else None
        result['cleanup'] = terminate_descendants(os.getpid(), cpus, exclude=[request['guardian_pid']],
                                                  observer=sampler.sample if sampler else None)
        result['observed_processes'] = list(seen.values())
        try:
            if sampler: publish_result_observed(channel, request, result, sampler)
            else: publish_result(channel, request, result)
            # Keep the coordinator alive until the guardian consumes the result.
            # Otherwise an already-ready pidfd could race a queued final packet.
            select.select([channel], [], [], .5)
        except (BrokenPipeError, ConnectionResetError):
            # A lost guardian leaves a durable unsettled reservation, never a pass.
            atomic_json(Path(request['output'] + '.coordinator-failure.json'), result)
        os.close(parent_fd)


class Heartbeats:
    """Validate sensor cadence independently of when the guardian is scheduled."""
    def __init__(self, limit, started, earliest=None):
        self.limit = limit
        self.started = started
        self.earliest = started if earliest is None else earliest
        self.entered = False
        self.last = None
        self.count = 0
        self.max_sample_gap = 0
        self.max_delivery_lag = 0
        self.recent = []
        self.advisory_exceedances = []

    def entry(self):
        if self.entered:
            raise AdmissionError('duplicate_control_entry')
        self.entered = True

    def sample(self, sent, received):
        if not self.entered or type(sent) is not int or sent < self.earliest or sent > received:
            raise AdmissionError('invalid_heartbeat_timestamp')
        if self.last is not None:
            gap = sent - self.last
            if gap <= 0 or gap > self.limit:
                raise AdmissionError('heartbeat_sample_gap')
            self.max_sample_gap = max(self.max_sample_gap, gap)
            if gap > ADVISORY_GAP_NS:self.advisory_exceedances.append([self.last,sent,gap])
        self.last = sent
        self.count += 1
        self.max_delivery_lag = max(self.max_delivery_lag, received - sent)
        self.recent.append([sent, received])
        self.recent = self.recent[-16:]

    def fresh(self, now):
        return now - (self.last if self.last is not None else self.started) <= self.limit

    def record(self):
        return dict(heartbeats=self.count, max_sample_gap_ns=self.max_sample_gap,
                    max_delivery_lag_ns=self.max_delivery_lag, recent_samples=self.recent,
                    advisory_gap_ns=ADVISORY_GAP_NS,advisory_exceedances=self.advisory_exceedances)


def initial_journal():
    return dict(identity='gpup-tensor-cost-cpu-journal-v1', prior_cpu_ns=PRIOR_CPU_NS,
                ceiling_cpu_ns=CAP_CPU_NS,
                stages={name: dict(cap_cpu_ns=cap * NS, charged_cpu_ns=0)
                        for name, cap in STAGES.items()}, runs=[], active=None,
                failed=False)


def run(request):
    if request.get('max_gap_ns') not in (100_000_000,1_000_000_000):
        raise AdmissionError('unsupported_sampling_policy')
    receipt_seconds = request.get('receipt_finalization_seconds', 1)
    if type(receipt_seconds) is not int or not 1 <= receipt_seconds <= 10:
        raise AdmissionError('invalid_receipt_finalization_reserve')
    if request.get('observed_finalization'):
        publication = request.get('publication_wall_seconds')
        if type(publication) is not int or not 1 <= publication <= 30:
            raise AdmissionError('invalid_publication_reserve')
    receipt_ns = receipt_seconds * NS
    entered = time.monotonic_ns()
    available = sorted(os.sched_getaffinity(0))
    if len(available) < 4:
        raise AdmissionError('four_cpus_unavailable')
    cpus = set(available[:4])
    os.sched_setaffinity(0, cpus)
    prctl(36, 1)
    # Discover API/kernel/container incompatibility before creating any child.
    capability = pidfd_open(os.getpid())
    os.close(capability)
    output = Path(request['output'])
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or Path(request['log']).exists():
        raise AdmissionError('immutable_output_exists')
    lock_path = Path(request['lock'])
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        journal_path = Path(request['journal'])
        journal = json.loads(journal_path.read_text()) if journal_path.exists() else initial_journal()
        if journal['active'] or journal['failed']:
            raise AdmissionError('stale_or_failed_reservation')
        reserved = math.ceil(request['reserve_cpu_seconds'] * NS)
        stage = journal['stages'][request['stage']]
        if reserved < 12 * NS or reserved > stage['cap_cpu_ns'] - stage['charged_cpu_ns']:
            raise AdmissionError('stage_reservation_exhausted')
        if reserved // 4 <= receipt_ns + NS:
            raise AdmissionError('finalization_margin_exhausts_reservation')
        if journal['prior_cpu_ns'] + sum(s['cap_cpu_ns'] for s in journal['stages'].values()) > journal['ceiling_cpu_ns']:
            raise AdmissionError('mandatory_future_reserves_do_not_fit')
        if request['slots'] not in range(1, 5):
            raise AdmissionError('invalid_work_slots')
        if request['declared_memory_bytes'] + (128 << 20) > request['rss_stop_bytes']:
            raise AdmissionError('memory_envelope_refused')
        request.update(guardian_pid=os.getpid(), affinity=sorted(cpus),
                       started_ns=entered,
                       work_deadline_ns=entered + reserved // 4 - receipt_ns - NS)
        request['thread_environment'] = THREAD_ENV
        request['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        request['command_sources'] = [dict(path=p, sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
                                      for p in request['sources']]
        request['request_sha256'] = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        journal['active'] = dict(output=str(output), stage=request['stage'],
                                 reserved_cpu_ns=reserved, guardian=identity(os.getpid()),
                                 started_ns=entered, request_sha256=request['request_sha256'])
        atomic_json(journal_path, journal)
        left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        pid = os.fork()
        if pid == 0:
            left.close()
            try:
                coordinator(request, lock.fileno(), right, cpus)
            finally:
                os._exit(0)
        right.close()
        try:
            child_fd = pidfd_open(pid)
        except BaseException:
            terminate_descendants(os.getpid(), cpus)
            # Preserve the active reservation for explicit failure settlement.
            raise
        result = None
        reason = None
        watch = Heartbeats(request['max_gap_ns'], time.monotonic_ns(), request['started_ns'])
        cancelled = []
        signal.signal(signal.SIGTERM, lambda *_: cancelled.append('cancelled'))
        signal.signal(signal.SIGINT, lambda *_: cancelled.append('cancelled'))
        previous_observation = time.monotonic_ns()
        max_observation_gap = 0
        while True:
            now = time.monotonic_ns()
            max_observation_gap = max(max_observation_gap, now - previous_observation)
            previous_observation = now
            if cancelled:
                reason = cancelled[0]
                break
            if now >= request['work_deadline_ns']:
                reason = 'guardian_cpu_wall_deadline'
                break
            # A guardian scheduling pause is not a sampling pause. Drain already
            # queued samples BEFORE judging freshness, using their actual sample
            # timestamps rather than granting a new lease at each receipt.
            readable = select.select([left, child_fd], [], [], .005)[0]
            try:
                for _ in range(4096):
                    if left not in readable:
                        break
                    message = receive(left)
                    if message is None:
                        raise AdmissionError('coordinator_lost')
                    event = message.get('event')
                    if event == 'done':
                        result = load_result(request, message)
                        break
                    if event == 'entry':
                        watch.entry()
                        journal['active']['entry'] = message['identity']
                        journal['active']['coordinator'] = message['coordinator']
                        atomic_json(journal_path, journal)
                    elif event == 'heartbeat':
                        watch.sample(message.get('timestamp_ns'), time.monotonic_ns())
                    else:
                        raise AdmissionError('unknown_control_event')
                    readable = select.select([left, child_fd], [], [], 0)[0]
                else:
                    raise AdmissionError('control_queue_bound')
            except (OSError, ValueError, KeyError, TypeError, AdmissionError) as error:
                reason = ('coordinator_lost' if str(error) == 'coordinator_lost'
                          else 'coordinator_result_transport: ' + str(error))
                break
            now = time.monotonic_ns()
            if cancelled:
                reason = cancelled[0]
                result = None
                break
            if now >= request['work_deadline_ns']:
                reason = 'guardian_cpu_wall_deadline'
                result = None
                break
            if result is not None:
                break
            if not watch.fresh(now):
                reason = 'lost_coordinator_heartbeat'
                break
            if child_fd in readable:
                reason = 'coordinator_lost'
                break
        cleanup = terminate_descendants(os.getpid(), cpus)
        os.close(child_fd)
        left.close()
        if result is None:
            result = dict(reason=reason, returncode=None, cleanup=cleanup)
        if not cleanup['empty'] or not result.get('cleanup', {}).get('empty'):
            result['reason'] = 'cleanup_incomplete'
        success = (result['reason'] == 'completed' and result['returncode'] == 0
                   and cleanup['empty'])
        end = time.monotonic_ns()
        # Numerical work/cleanup must leave the prospectively charged durable
        # receipt allowance; it never extends the outer reservation.
        measured_upper = 4 * (end - entered + receipt_ns)
        charged = reserved if request['bootstrap'] or not success else measured_upper
        charged = max(charged, measured_upper)
        if charged > reserved:
            result['reason'] = 'cpu_reservation_overrun'
            success = False
        report = dict(identity='cooperative_process_supervision_v4', request=request,
                      status='passed' if success else 'refused', result=result,
                      guardian_cleanup=cleanup, charged_cpu_ns=charged,
                      guardian_observation=dict(max_loop_gap_ns=max_observation_gap, **watch.record()),
                      active_elapsed_ns=end-entered, finalization_wall_reserve_ns=receipt_ns,
                      cpu_method='4 * active wall including reserved finalization; full reservation on failure/bootstrap',
                      memory_method='sampled aggregate VmRSS; not hard cgroup containment',
                      hard_memory_enclosure=False, exact_aggregate_peak=False)
        stage['charged_cpu_ns'] += charged
        journal['runs'].append(dict(output=str(output), stage=request['stage'],
                                   charged_cpu_ns=charged, status=report['status']))
        journal['active'] = None if cleanup['empty'] else journal['active']
        journal['failed'] = not success
        def finalization_timeout(*_):
            raise AdmissionError('receipt_finalization_timeout')
        signal.signal(signal.SIGALRM, finalization_timeout)
        signal.setitimer(signal.ITIMER_REAL, receipt_seconds)
        try:
            if request.get('show_log'):
                with Path(request['log']).open('rb') as stream:
                    shown = stream.read(256 << 10)
                print(shown.decode(errors='replace'), end='', flush=True)
            # A failed final write leaves the prior durable active reservation.
            atomic_json(output, report)
            atomic_json(journal_path, journal)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-gap-ms',type=int,choices=[100,1000],default=100)
    parser.add_argument('--stage', choices=STAGES, required=True)
    parser.add_argument('--reserve-cpu-seconds', type=float, required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--journal', default=str(ROOT/'artifacts/gpup-tensor-cost-v1/cpu-journal.json'))
    parser.add_argument('--lock', default=str(ROOT/'artifacts/lp-cpu-admission.lock'))
    parser.add_argument('--slots', type=int, default=4)
    parser.add_argument('--declared-memory-bytes', type=int, default=4 << 30)
    parser.add_argument('--rss-stop-bytes', type=int, default=6 << 30)
    parser.add_argument('--address-space-bytes', type=int, default=0)
    parser.add_argument('--source', action='append', default=[])
    parser.add_argument('--bootstrap', action='store_true')
    parser.add_argument('--show-log', action='store_true')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = vars(parser.parse_args())
    args['command'] = args['command'][1:] if args['command'][:1] == ['--'] else args['command']
    args['reserve_cpu_seconds'] = args.pop('reserve_cpu_seconds')
    args['sources'] = args.pop('source')
    args['log'] = args['output'] + '.log'
    args['max_gap_ns'] = args.pop('max_gap_ms') * 1_000_000
    if not args['command'] or not math.isfinite(args['reserve_cpu_seconds']):
        parser.error('finite reservation and a command are required')
    try:
        report = run(args)
    except (OSError, AdmissionError, ValueError) as error:
        print(json.dumps(dict(status='refused_before_launch', reason=str(error))), flush=True)
        return 2
    print(json.dumps(dict(status=report['status'], reason=report['result']['reason'],
                          charged_cpu_ns=report['charged_cpu_ns'])), flush=True)
    return 0 if report['status'] == 'passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
