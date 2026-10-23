"""CPU-only PR source bridge and fresh verification of both quantization studies.

This reader uses frozen requests and workers. It never opens the execution
ledger for writing, admits a GPU job, or reuses old admission for a new binary.
The original live-source execution gates deliberately continue to fail closed.
"""
import argparse
import concurrent.futures as cf
import difflib
import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

from benchmark_lp import reference
from lp_protocol import ROOT, checked_reference, file_hash, read_json, write_json
from lp_quant_report_output import DIRECTORY, report_output

BASE = '8be2138151c4a10681a936c1eaa8a84547332814'
LEDGER = ROOT / 'artifacts/lp-campaign-ledgers/gpup-baseline-v1/ledger.jsonl'
LEDGER_SHA = '930de6771ab9bfbcb855bd05a07a58f6700aa1ade36bca09346790a94e7ff035'
RECEIPT = ROOT / 'docs/benchmarks/data/quant-resident/pr-review-source.json'
CHANGED = {
    'crates/optimizer-lp/src/quant.rs',
    'crates/optimizer-lp/src/quant_resident.rs',
    'crates/optimizer-lp/tests/quant.rs',
    'crates/optimizer-lp/tests/quant_resident.rs',
    'crates/optimizer-experiment/src/lp_quant.rs',
    'crates/optimizer-experiment/src/lp_quant_resident.rs',
    'crates/optimizer-experiment/src/lp_quant_resident_micro.rs',
    'tools/report_lp_quant.py',
    'tools/report_lp_quant_resident.py',
    'tests/integration/test_lp_quant_resident.py',
}
ADDED = {'tools/lp_quant_pr_review.py', 'tools/lp_quant_report_output.py',
         'tests/integration/test_lp_quant_pr_review.py'}


def section(data, start, end=None):
    start = data.index(start.encode())
    return data[start:] if end is None else data[start:data.index(end.encode(), start)]


def before_sources():
    archive = DIRECTORY / 'before-source.tar'
    with tarfile.open(archive) as source:
        members = source.getmembers()
        names = [m.name for m in members]
        if len(names) != len(set(names)) or any(
                Path(m.name).is_absolute() or '..' in Path(m.name).parts
                or not (m.isfile() or m.isdir()) for m in members):
            raise ValueError('PR source archive layout')
        return {m.name: source.extractfile(m).read() for m in members if m.isfile()}


def source_bridge(create=False):
    old = before_sources()
    names = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    sources = {name:(ROOT/name).read_bytes() for name in names
               if name.startswith(('crates/','cuda/','tools/','tests/','schemas/','benchmarks/'))}
    changed = {p for p in old if p in sources and old[p] != sources[p]}
    added = set(sources) - set(old)
    removed = {p for p in old if p.startswith(('crates/', 'cuda/', 'tools/', 'tests/',
                                              'schemas/', 'benchmarks/'))} - set(sources)
    if changed != CHANGED or added != ADDED or removed:
        raise ValueError('undeclared PR execution/test source changes: ' +
                         str((changed ^ CHANGED, added ^ ADDED, removed)))
    for name, data in old.items():
        if name.startswith('docs/benchmarks/data/') or name in {
                'docs/benchmarks/lp-quantization-gpup7.md',
                'docs/benchmarks/lp-quant-resident-gpup7r.md', 'Cargo.toml', 'Cargo.lock'}:
            if (ROOT / name).read_bytes() != data:
                raise ValueError('historical evidence/dependency changed: ' + name)
    proofs = []
    scopes = [
        ('crates/optimizer-lp/src/quant.rs', 'pub const ID:', '#[derive(Clone, Debug)]\npub struct Tile'),
        ('crates/optimizer-lp/src/quant.rs', '        let _cost = optimizer_core::lp_cost::scope("quant_pack_metadata_norm")', '        Ok(Self'),
        ('crates/optimizer-lp/src/quant.rs', '    pub fn groups(', '#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]'),
        ('crates/optimizer-lp/src/quant.rs', 'pub trait Oracle', None),
        ('crates/optimizer-lp/src/quant_resident.rs', '        let _cost = optimizer_core::lp_cost::scope("resident_pack_metadata_norm")', '        Ok(Self'),
        ('crates/optimizer-lp/src/quant_resident.rs', '    pub fn generation(', 'pub struct Window'),
        ('crates/optimizer-lp/src/quant_resident.rs', 'pub struct HostOracle;', None),
        ('crates/optimizer-experiment/src/lp_quant.rs', 'pub fn execute(', '#[cfg(test)]'),
        ('crates/optimizer-experiment/src/lp_quant_resident.rs', 'pub fn execute(', '#[cfg(test)]'),
    ]
    for name, start, end in scopes:
        before, after = section(old[name], start, end), section(sources[name], start, end)
        if before != after:
            raise ValueError('measured arithmetic/controller/authority body changed: ' + name + start)
        proofs.append(dict(path=name, start=start, end=end, sha256=hashlib.sha256(after).hexdigest()))
    micro = 'crates/optimizer-experiment/src/lp_quant_resident_micro.rs'
    after = sources[micro]
    for indent in [b'        ', b'    ']:
        line = indent + b'optimizer_lp::quant::admit_shape(&p).map_err(invalid)?;\n'
        if after.count(line) != 1:
            # Four spaces also occur within the eight-space line; anchor lines.
            if len([x for x in after.splitlines(keepends=True) if x == line]) != 1:
                raise ValueError('micro shape precondition scope')
        after = after.replace(line, b'', 1)
    # The other micro changes only reject noncanonical JSON input shapes.
    if section(after,'pub fn execute(') != section(old[micro],'pub fn execute('):
        raise ValueError('micro execution body changed beyond shape admission')
    start,end='        let e = Engine::new(&p, r.request.method);','pub fn execute('
    if section(after,start,end) != section(old[micro],start,end):
        raise ValueError('micro differential verification arithmetic changed')
    if file_hash(LEDGER) != LEDGER_SHA or len(LEDGER.read_bytes().splitlines()) != 17132:
        raise ValueError('PR added GPU work or changed history')
    files = [dict(path=name, before_sha256=hashlib.sha256(old[name]).hexdigest(),
                  reviewed_sha256=hashlib.sha256(sources[name]).hexdigest())
             for name in sorted(CHANGED)]
    exact = [dict(path=name, sha256=hashlib.sha256(data).hexdigest())
             for name, data in sorted(sources.items()) if name not in CHANGED | ADDED]
    result = dict(identity='gpup-quant-pr-review-v1', gpu_seconds=0,
                  new_device_acceptance=False, base_commit=BASE,
                  before_archive=reference(ROOT, DIRECTORY / 'before-source.tar'),
                  files=files, added=[dict(path=p, sha256=file_hash(ROOT/p)) for p in sorted(ADDED)],
                  unchanged_sources=exact, unchanged_bodies=proofs,
                  ledger_events=17132, ledger_sha256=LEDGER_SHA)
    if create:
        for f in files:
            name = f['path'];dest = DIRECTORY / 'source' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.with_suffix(dest.suffix + '.before').write_bytes(old[name])
            dest.with_suffix(dest.suffix + '.diff').write_text(''.join(difflib.unified_diff(
                old[name].decode().splitlines(keepends=True), sources[name].decode().splitlines(keepends=True),
                fromfile=name + ' (pre-PR)', tofile=name + ' (reviewed)')))
        write_json(RECEIPT, result)
    elif read_json(RECEIPT) != result:
        raise ValueError('PR source bridge does not bind this checkout')
    return result


def roster():
    tasks, studies = [], []
    for family, cohorts, expected in [('quant', ['cpu-admission', 'final-admission'], 182),
            ('quant-resident', ['cpu-admission', 'final-admission', 'accepted-admission'], 313)]:
        module = __import__('benchmark_lp_' + family.replace('-', '_'))
        reader = __import__('report_lp_' + family.replace('-', '_'))
        v = read_json(ROOT / ('benchmarks/configs/lp-' + family + '-v1.json'))
        from validate_artifacts import validator
        validator('lp-' + family + '-study-v1.schema.json').validate(v)
        d = ROOT / v['output'];identity = reader.archive(v, d)
        report = read_json(ROOT / ('docs/benchmarks/data/' + family + '/report.json'))
        events, charges, cumulative = reader.ledger(v, d / 'ledger.jsonl')
        if (charges != report['categories_ns'] or cumulative != report['cumulative_gpu_ns']
                or len(events) != report['ledger_events'] or file_hash(d/'ledger.jsonl') != report['ledger_sha256']):
            raise ValueError('historical report accounting differs')
        models = {i['model']['sha256']: checked_reference(ROOT, i['model'])
                  for i in module.instances(v).values()}
        family_tasks, profiles = [], []
        for job in module.jobs(v):
            key = job['id'];trial_path = d / (key + '.trial.json')
            if not trial_path.exists():
                if any(e['trial_id'] == key for e in events):raise ValueError('missing attempted trial')
                continue
            trial = read_json(trial_path)
            if trial['job'] != job or trial['id'] != key:raise ValueError('trial roster binding')
            if trial['status'] == 'cpu_admission_refusal':
                if trial['charged_ns'] or any(e['trial_id'] == key for e in events):raise ValueError('charged CPU refusal')
                continue
            request, docs = module.prepare_inputs(v, job, d, identity)
            if (read_json(d/(key+'.request.json')) != request or trial['artifacts'] != module.refs(d,key)
                    or trial['campaign_sha256'] != file_hash(ROOT/('benchmarks/configs/lp-'+family+'-v1.json'))
                    or trial['source_tree_sha256'] != identity['source_tree_sha256']
                    or trial['request_sha256'] != file_hash(d/(key+'.request.json'))):
                raise ValueError('frozen trial request/source/artifact binding')
            for name, value in docs.items():
                if read_json(d/name) != value:raise ValueError('frozen nested request changed')
            worker = read_json(d/(key+'.worker.json')) if trial['artifacts']['worker'] else None
            tx = [e for e in events if e['trial_id'] == key]
            reservation = (module.effective(v,job)[2] + 6) * 10**9
            if (len(tx) != 2 or tx[0]['kind'] != 'reserve' or tx[1]['kind'] not in ['settle','recover']
                    or any(t['reserved_ns'] != reservation or t['phase'] != v['categories'][job['category']]['phase'] for t in tx)
                    or tx[1]['charged_ns'] != trial['charged_ns']
                    or tx[1]['charged_ns'] != (worker['leased_ns'] if worker and tx[1]['kind']=='settle' else reservation)
                    or worker and (worker['activity']['device'] != v['device'] or worker['leased_ns'] > reservation)):
                raise ValueError('trial physical accounting')
            ep = d/(key+'.endpoint.json')
            if ep.exists():
                e = read_json(ep)
                if 'outcome' in e:
                    suffix = '.resident-request.json' if family == 'quant-resident' else '.quant-request.json'
                    family_tasks.append((family, 'study', ep, d/(key+suffix), models[e['request']['model_sha256']]))
                else:family_tasks.append(('control', family, ep, None, checked_reference(ROOT,job['instance']['model'])))
                if job['kind'] == 'profile':
                    shaped = e if 'outcome' in e else reader.endpoint_shape(ep,'compact-v1')
                    profiles.append(dict(id=key, eligible=reader.profile_eligible(shaped,v['profile_work'],True,trial,worker)))
        acceptance = ROOT / v['acceptance_output'] / 'project' / 'acceptance.json'
        a = read_json(acceptance)
        if a['status'] != 'passed' or len(a['rows']) != (29 if family=='quant-resident' else 18):
            raise ValueError('incomplete preserved fixed-work acceptance')
        for row in a['rows']:
            ep = checked_reference(ROOT,row['endpoint']);rp = ep.with_name(ep.name.replace('.endpoint.json','.request.json'))
            r = read_json(rp);model = models[r['model_sha256']]
            for name, endpoint in [('acceptance',ep),('replay',checked_reference(ROOT,row['replay']))]:
                family_tasks.append((family,name,endpoint,rp,model))
        for cohort in cohorts:
            base = ROOT/('artifacts/gpup-'+family+'-v1')/cohort;a = read_json(base/'admission.json')
            if 'source_archive' in a:checked_reference(ROOT,a['source_archive'])
            elif (family,cohort) != ('quant','cpu-admission'):raise ValueError('missing CPU source archive')
            if file_hash(base/('lp_precision_'+family.replace('-','_'))) != a['executable_sha256']:
                raise ValueError('CPU cohort executable changed')
            for row in a['rows']:
                if 'endpoint' in row:
                    ep = checked_reference(ROOT,row['endpoint']);rp = ep.with_name('request.json');r = read_json(rp)
                    if r['source_tree_sha256'] != a['source_tree_sha256'] or r['executable_sha256'] != a['executable_sha256']:
                        raise ValueError('CPU cohort request binding')
                    family_tasks.append((family,cohort,ep,rp,models[r['model_sha256']]))
        if len(family_tasks) != expected:raise ValueError('retained LP endpoint roster: '+str((family,len(family_tasks))))
        tasks.extend(family_tasks)
        studies.append(dict(family=family, original_report=reference(ROOT,ROOT/('docs/benchmarks/data/'+family+'/report.json')),
                            lp_endpoints=expected, profiles=profiles, certified_timings=report['certified_timings'],
                            task_gpu_ns=report['task_gpu_ns'],cumulative_gpu_ns=cumulative))
    v = read_json(ROOT/'benchmarks/configs/lp-quant-resident-v1.json');d = ROOT/v['output']
    model = checked_reference(ROOT,__import__('benchmark_lp_quant_resident').instances(v)['gpup-extension-irregular-32768']['model'])
    for ep in sorted((d/'micro').glob('*.endpoint.json')):
        tasks.append(('micro','quant-resident',ep,ep.with_name(ep.name.replace('.endpoint.','.request.')),model))
    if len(tasks) != 516:raise ValueError('retained endpoint total differs')
    return tasks,studies


def verify_endpoints():
    source_bridge();tasks, studies = roster();start = time.monotonic()
    directory = DIRECTORY/'verification-final';directory.mkdir(exist_ok=False)
    binaries = {}
    for family in ['quant','quant-resident']:
        name = 'lp_precision_'+family.replace('-','_');dest = directory/name
        shutil.copy2(ROOT/'target/release/examples'/name,dest);binaries[family] = dest
    shutil.copy2(ROOT/'target/release/optimizer',directory/'optimizer')
    # The first CPU-only resident cohort predates the required first-certification
    # field. Preserve its exact schema/payload and verifier instead of silently
    # normalizing or re-signing historical evidence for the rebuilt executable.
    historical = directory/'resident-initial-cpu-verifier'
    original = ROOT/'artifacts/gpup-quant-resident-v1/cpu-admission/lp_precision_quant_resident'
    shutil.copy2(original,historical)
    def verify(task):
        family,kind,ep,rp,model = task
        if family == 'control':
            command = [str(directory/'optimizer'),'lp-study','verify','--model',str(model),
                       '--model-byte-limit',str(128<<20),'--evidence',str(ep)]
        else:
            binary = historical if (family,kind)==('quant-resident','cpu-admission') else binaries['quant-resident' if family == 'micro' else family]
            command = [str(binary),'micro-verify' if family == 'micro' else 'verify',str(model),str(rp)]
            if family == 'micro':command.append(str(ep.parent.parent/'micro-vectors.json'))
            command.append(str(ep))
        r = subprocess.run(command,capture_output=True,text=True,timeout=240)
        stem = str(ep.relative_to(ROOT)).replace('/','_')
        (directory/(stem+'.stdout')).write_text(r.stdout);(directory/(stem+'.stderr')).write_text(r.stderr)
        if r.returncode:raise ValueError('fresh verifier rejected '+str(ep)+' '+r.stderr[:1500])
        return dict(family=family,kind=kind,endpoint=reference(ROOT,ep),returncode=r.returncode,
                    verifier='original-initial-cpu' if (family,kind)==('quant-resident','cpu-admission') else 'rebuilt')
    with cf.ThreadPoolExecutor(max_workers=4) as pool:rows = list(pool.map(verify,tasks))
    if file_hash(LEDGER) != LEDGER_SHA:raise ValueError('GPU ledger changed during CPU verification')
    result = dict(identity='gpup-quant-pr-verification-v1',status='passed',gpu_seconds=0,
                  new_device_acceptance=False,source_bridge=reference(ROOT,RECEIPT),studies=studies,
                  lp_endpoints=495,micro_endpoints=21,elapsed_seconds=time.monotonic()-start,
                  rebuilt_lp_endpoints=423,historical_initial_cpu_endpoints=72,
                  binaries={k:reference(ROOT,v) for k,v in binaries.items()},
                  historical_initial_cpu_verifier=reference(ROOT,historical),
                  control_verifier=reference(ROOT,directory/'optimizer'),rows=rows,
                  ledger_events=17132,ledger_sha256=LEDGER_SHA)
    write_json(report_output(kind='verified-final'),result)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['bridge','verify'])
    args=parser.parse_args()
    if args.action == 'bridge':source_bridge(create=True);print('CPU-only PR source bridge bound')
    else:
        result=verify_endpoints();print({k:result[k] for k in ['status','lp_endpoints','micro_endpoints','gpu_seconds','elapsed_seconds']})


if __name__ == '__main__':main()
