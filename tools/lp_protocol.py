"""Strict LP-only study contracts, ledger and frozen ordering (SPEC-0013)."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
from validate_artifacts import read_json, validator

ROOT = Path(__file__).resolve().parents[1]
NS = 1_000_000_000
PHASES = {'baseline': 1800, 'screening': 7200, 'ablations': 7200,
          'finalists': 9000, 'repeatability': 3600}

def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.partial')
    with temporary.open('wb') as stream:
        stream.write(encoded(value)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)

def local(root, path):
    if Path(path).is_absolute(): raise ValueError('absolute artifact path')
    target = (Path(root) / path).resolve()
    if not target.is_relative_to(Path(root).resolve()): raise ValueError('artifact path escapes root')
    return target

def validate(kind, value):
    version=value.get('schema_version',1)
    if version not in (1,2) or (version==2 and kind not in ('campaign','trial','endpoint')):
        raise ValueError('unsupported LP artifact version')
    validator(f'lp-{kind}-v{version}.schema.json').validate(value)
    return value

def checked_reference(root, reference):
    path = local(root, reference['path'])
    if not path.is_file() or file_hash(path) != reference['sha256']:
        raise ValueError('artifact checksum mismatch: ' + str(path))
    return path

def campaign(path, materialized=True):
    path = Path(path)
    value = validate('campaign', read_json(path))
    if value['phase_gpu_seconds'] != PHASES or value['total_gpu_seconds'] != 28800:
        raise ValueError('campaign allocation differs from frozen protocol')
    if value['slice_gpu_seconds'] != 900 or value['partition'] != 'development':
        raise ValueError('Slice 2 allocation/partition differs')
    if value['solve']['seed'] != 17 or value['solve']['threads'] != 1:
        raise ValueError('solver seed/threads differ from ADR-0014')
    if value['solve']['tolerances'] != dict(absolute=1e-9, relative=1e-9, integrality=1e-9):
        raise ValueError('numerical targets differ from ADR-0014')
    if value['order_seed'] != 17001 or value['analysis'] != {'seed':17002,'resamples':10000,'confidence':0.95}:
        raise ValueError('analysis/order protocol differs')
    if value['repetitions'] != 3 or value['profile_repetitions'] != 1:
        raise ValueError('repetition protocol differs')
    expected_solve = {'schema_version':1,'seed':17,'time_limit_ms':10000,
        'iteration_limit':50000,'node_limit':None,'threads':1,
        'tolerances':{'absolute':1e-9,'relative':1e-9,'integrality':1e-9}}
    expected_lp = {'schema_version':1,'preconditioner':{'ruiz_passes':10,'pock_chambolle_alpha':1.0},
        'iteration_limit':50000,'check_interval':200,'power_iterations':20,
        'restart':{'sufficient':0.2,'necessary':0.8,'artificial':0.36},
        'primal_weight':{'proportional':0.5,'integral':0.0,'derivative':0.0}}
    if value['solve']!=expected_solve or value['lp_settings']!=expected_lp:
        raise ValueError('solve/LP settings differ from ADR-0014')
    groups, ids, hashes, generators, manifests = {}, set(), {}, {}, []
    for reference in value['manifests']:
        manifest = validate('manifest', read_json(checked_reference(ROOT, reference)))
        manifests.append(manifest)
        for item in manifest['instances']:
            if item['id'] in ids: raise ValueError('duplicate instance identity')
            ids.add(item['id'])
            partition = manifest['partition']
            for mapping, key in [(groups,item['group']), (hashes,item['model']['sha256'])]:
                if key in mapping and mapping[key] != partition: raise ValueError('related-instance partition leakage')
                mapping[key] = partition
            generator_key=(item['generator']['name'],item['generator']['seed'])
            if item['family']!='taillard_diagnostic':
                if generator_key in generators and generators[generator_key]!=partition:
                    raise ValueError('generator seed crosses partitions')
                generators[generator_key]=partition
            if item['family'] == 'taillard_diagnostic' and partition != 'development':
                raise ValueError('inspected Taillard data must remain development')
            if item['bytes'] > 16 * 1024 * 1024: raise ValueError('model byte limit exceeded')
            if materialized:
                model_path = local(ROOT, item['model']['path'])
                if model_path.stat().st_size != item['bytes']: raise ValueError('model size mismatch')
                checked_reference(ROOT, item['model'])
                if item['witness'] is not None: checked_reference(ROOT, item['witness'])
    if {m['partition'] for m in manifests} != {'development','validation','held_out'}:
        raise ValueError('all three frozen partitions are required')
    if value['configurations'] != [{'id':b,'backend':b} for b in ['highs','host-lp','cuda-lp']]:
        raise ValueError('baseline grid differs')
    return value, manifests

def ordered(configurations, seed, instance, repetition):
    return sorted(configurations, key=lambda c: digest(f'{seed}:{instance}:{repetition}:{c["id"]}'.encode()))

class Ledger:
    """One exclusive campaign writer, durable reservations, conservative recovery."""
    def __init__(self, directory, campaign_hash, allocations=None, slice_seconds=900):
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'ledger.jsonl'
        self.campaign_hash = campaign_hash
        self.allocations = allocations or PHASES
        self.slice_ns = slice_seconds * NS
        self.lock = None; self.events = []

    def __enter__(self):
        self.lock = (self.directory / 'campaign.lock').open('a+b')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._load()
            for reservation in list(self.pending().values()):
                self._append('recover', reservation, reservation['reserved_ns'])
            return self
        except BaseException:
            self.lock.close(); raise

    def __exit__(self, *_):
        fcntl.flock(self.lock, fcntl.LOCK_UN); self.lock.close()

    def bind_output(self, output):
        """A different output directory cannot create a fresh budget for this identity."""
        binding={'campaign_sha256':self.campaign_hash,'output_path':str(Path(output).resolve())}
        path=self.directory/'output.json'
        if path.exists() and read_json(path)!=binding:
            raise ValueError('campaign already bound to another output directory; budget cannot reset')
        if not path.exists():write_json(path,binding)

    def _load(self):
        if not self.path.exists(): return
        data = self.path.read_bytes()
        if data and not data.endswith(b'\n'):
            split = data.rfind(b'\n') + 1
            evidence = self.directory / f'torn-{time.time_ns()}.bin'
            evidence.write_bytes(data[split:])
            # A reservation was fsynced before a job could start. A torn last
            # settlement therefore leaves that reservation conservatively charged.
            with self.path.open('r+b') as stream:
                stream.truncate(split); stream.flush(); os.fsync(stream.fileno())
            data = data[:split]
        self.events = []
        for line in data.splitlines():
            # Use the same strict parser as artifact validation, without a temporary file.
            event = strict_loads(line)
            validate('ledger', event)
            if event['campaign_sha256'] != self.campaign_hash or event['sequence'] != len(self.events):
                raise ValueError('ledger identity/sequence mismatch')
            self.events.append(event)
        self.pending()  # validates event relationships before recovery writes

    def pending(self):
        active, seen = {}, set()
        for event in self.events:
            key = event['reservation_id']
            if event['kind'] == 'reserve':
                if key in seen or event['charged_ns'] != 0: raise ValueError('duplicate/invalid reservation')
                seen.add(key); active[key] = event
            else:
                original = active.pop(key, None)
                if original is None or any(event[k] != original[k] for k in ['trial_id','resource','phase','reserved_ns']):
                    raise ValueError('unmatched ledger settlement')
                if event['kind'] == 'recover' and event['charged_ns'] != event['reserved_ns']:
                    raise ValueError('undercharged crash reservation')
        return active

    def totals(self, resource='gpu', phase=None):
        total = sum(e['charged_ns'] for e in self.events if e['resource'] == resource
                    and (phase is None or e['phase'] == phase))
        return total + sum(e['reserved_ns'] for e in self.pending().values()
                    if e['resource'] == resource and (phase is None or e['phase'] == phase))

    def attempted(self):
        return {e['trial_id'] for e in self.events if e['kind'] == 'reserve'}

    def reserve(self, trial_id, seconds, resource='gpu', phase='baseline'):
        ns = round(seconds * NS)
        if ns <= 0 or trial_id in self.attempted(): raise ValueError('invalid/duplicate trial reservation')
        if phase not in self.allocations: raise ValueError('unknown budget phase')
        if resource == 'gpu' and (self.totals() + ns > min(28800 * NS, self.slice_ns)
                or self.totals(phase=phase) + ns > self.allocations[phase] * NS):
            raise ValueError('GPU budget exhausted')
        original = dict(reservation_id=trial_id, trial_id=trial_id, resource=resource,
                        phase=phase, reserved_ns=ns)
        return self._append('reserve', original, 0)

    def settle(self, reservation, actual_ns):
        if reservation['reservation_id'] not in self.pending(): raise ValueError('reservation already settled')
        return self._append('settle', reservation, max(0, actual_ns))

    def _append(self, kind, original, charged):
        event = {k: original[k] for k in ['reservation_id','trial_id','resource','phase','reserved_ns']}
        event.update(schema_version=1, campaign_sha256=self.campaign_hash,
                     sequence=len(self.events), kind=kind, charged_ns=charged)
        validate('ledger', event)
        with self.path.open('ab') as stream:
            stream.write(encoded(event)); stream.flush(); os.fsync(stream.fileno())
        self.events.append(event)
        return event

def strict_loads(data):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value: raise ValueError('duplicate JSON key: ' + key)
            value[key] = item
        return value
    def nonfinite(value): raise ValueError('nonfinite JSON value: ' + value)
    import math
    def floating(value):
        parsed = float(value)
        if not math.isfinite(parsed): nonfinite(value)
        return parsed
    return json.loads(data, object_pairs_hook=unique, parse_constant=nonfinite, parse_float=floating)
