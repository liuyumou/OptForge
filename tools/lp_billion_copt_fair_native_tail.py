"""Finish only the four untouched cells within the sealed native setting domain."""
import argparse
import copy
import hashlib
import math
import subprocess
import time
from lp_billion_common import BASE, ROOT, NS, CPU_CAPS, GPU_CAPS, DISK_LIMIT, disk_bytes, load, put, ref, resolve, require
from lp_billion_budget import accounting, run
from lp_billion_prepare_continue import completed, job
from lp_billion_readmission import CPU, GPU
from lp_billion_copt_fair_run import PYTHON
from lp_billion_copt_fair_policy import FAMILIES, timely
from lp_billion_copt_fair_budgeted import budgeted_pair, ORIGINAL
from lp_billion_copt_fair_recovery_v2 import CELL, recovered_record

PREVIOUS = BASE / 'copt-fair-budgeted-v1/freeze.json'
MANIFEST = BASE / 'copt-fair-native-tail-v1/freeze.json'
PROTOCOL = ROOT / 'docs/specifications/SPEC-0046-amendment-87.md'
VALIDATION = 'copt-fair-native-wall-validation-v1'
CONTRACTS = 'copt-fair-native-tail-contracts-v1'
IDLE = 'copt-fair-native-tail-idle-v1'


def corrected(cell):
    value = copy.deepcopy(cell)
    require(value['status'] == 'pending' and value['family'] in ['ill_scaled', 'degenerate'], 'only the untouched two-family tail')
    value.update(wall_seconds=1800., common_solver_wall_seconds=1800)
    if value['lane'] == 'fp4x2': value['request']['settings']['wall_ms'] = 1800000
    require(value['seconds'] == 2700 and value['audit_seconds'] == (4600 if value['lane'] == 'fp4x2' else 900), 'retain outer and audit headroom')
    return value


def envelope():
    c, g = accounting(); cpu = dict(admission=2400, development=50400, reporting=52000, cleanup=480); gpu = dict(development=10800)
    require(all(c[k] + v * NS <= CPU_CAPS[k] * NS for k, v in cpu.items()), 'complete remaining CPU envelope')
    require(all(g[k] + v * NS <= GPU_CAPS[k] * NS for k, v in gpu.items()), 'complete remaining GPU envelope')
    return dict(cpu=cpu, gpu=gpu, remaining_after_cpu_seconds={k:CPU_CAPS[k]-c[k]/NS-v for k,v in cpu.items()},
                remaining_after_gpu_seconds={k:GPU_CAPS[k]-g[k]/NS-v for k,v in gpu.items()})


def native_validation():
    out = BASE / VALIDATION; out.mkdir(exist_ok=False)
    binding = load(BASE / 'image-v11/binding.json'); exe = resolve(binding['executor'])
    fixture = load(BASE / 'generator-admission-v1-coupled_blocks/result.json')
    source = ROOT / 'research/lp-billion-lowbit/src/solve.rs'
    prior = load(BASE / 'gpu-control-settled-checkpoint-v1.json')
    require(ref(source) in prior['numerical_bindings'], 'unchanged sealed native setting validation source')
    settings = dict(format='fp4x2', tolerance=1e-9, iteration_limit=10000, check_interval=500, reference_window=16, equilibrate=True)
    witness = load(resolve(fixture['construction'])); records = []
    for milliseconds in [1800000, 1800001, 2100000]:
        request = dict(settings=dict(settings, wall_ms=milliseconds), endpoint=witness)
        import json
        result = subprocess.run([str(exe),'assess',str(resolve(fixture['model'])),str(BASE)], input=json.dumps(request)+'\n',
                                text=True,capture_output=True,timeout=30)
        put(out / f'{milliseconds}.request.json', request)
        (out / f'{milliseconds}.stdout').write_text(result.stdout); (out / f'{milliseconds}.stderr').write_text(result.stderr)
        if milliseconds == 1800000:
            proof = json.loads(result.stdout); require(result.returncode == 0 and proof['accepted'] and proof['tolerance'] == 1e-9, 'maximum native allowance accepted with strict small-fixture proof')
        else: require(result.returncode == 2 and result.stderr.strip() == 'invalid solver settings' and not result.stdout, 'native rejects unsupported allowance')
        records.append(dict(wall_ms=milliseconds, returncode=result.returncode, request=ref(out/f'{milliseconds}.request.json'),
                            stdout=ref(out/f'{milliseconds}.stdout'), stderr=ref(out/f'{milliseconds}.stderr')))
    put(out/'result.json',dict(status='passed',executor=ref(exe),source=ref(source),fixture=fixture['model'],checks=records,protocol=ref(PROTOCOL)))


def freeze():
    require(completed(CPU) and completed(GPU) and completed(VALIDATION) and completed(CONTRACTS), 'native and harness validation plus exact operational admission')
    require(not MANIFEST.exists(), 'fresh untouched effective manifest')
    old = load(PREVIOUS); resolve(old['resumption_source'])
    untouched = [c['id'] for c in old['cells'] if c['status']=='pending' and not (BASE/'resources'/(c['id']+'.reservation.json')).exists()]
    expected = ['copt-fair-1b-v1-'+family+'-'+lane for family, lane in [('ill_scaled','project'),('ill_scaled','copt'),('degenerate','copt'),('degenerate','project')]]
    require(untouched == expected, 'exact four never-attempted cells')
    value = copy.deepcopy(old); value['cells'] = [corrected(c) if c['id'] in untouched else c for c in value['cells']]
    for before, after in zip(old['cells'],value['cells']):
        expected_cell = corrected(before) if before['id'] in untouched else before
        require(after == expected_cell, 'historical outcomes and all other settings unchanged')
    require(disk_bytes() + (64 << 30) <= DISK_LIMIT, 'per-family input/endpoint storage headroom')
    for item in load(BASE/'gpu-control-settled-checkpoint-v1.json')['numerical_bindings']: resolve(item)
    cohorts = [dict(c,ids=[i for i in c['ids'] if i not in untouched]) for c in old['allowance_cohorts']]
    cohorts.append(dict(name='supported_native_tail',wall_seconds=1800,outer_seconds=2700,ids=untouched))
    value.update(previous_effective_freeze=ref(PREVIOUS),resumption_source=ref(__file__),time_budget_protocol=ref(PROTOCOL),
                 native_wall_validation=ref(BASE/VALIDATION/'result.json'),contracts=ref(BASE/'resources'/(CONTRACTS+'.settlement.json')),
                 untouched=untouched,allowance_cohorts=cohorts,reservation=envelope())
    put(MANIFEST,value);print(dict(untouched=untouched,reservation=value['reservation']),flush=True)


def observation():
    from lp_billion_availability import observe, stable, proof
    out=BASE/IDLE;out.mkdir(exist_ok=False);start=time.monotonic();ready=False
    for i in range(8):
        while time.monotonic()<start+i*60:time.sleep(min(1,start+i*60-time.monotonic()))
        observe(IDLE);paths=sorted((BASE/'availability'/IDLE).glob('*.json'),key=lambda p:int(p.stem))
        ready=stable([load(p) for p in paths],time.monotonic_ns())
        if ready:proof(IDLE);break
    put(out/'result.json',dict(status='observed_idle' if ready else 'idle_gate_not_met',samples=[ref(p) for p in paths],source=ref(__file__)))


def regenerate(family):
    from lp_billion_generate import generate
    from lp_billion_portable import arrays
    original=load(BASE/f'models-1b-{family}-v1/result.json');resolve(original['generator'])
    identity=f'copt-fair-regenerated-1b-{family}-'+('v2' if family=='ill_scaled' else 'v1')
    checked=0;removed=[]
    if family=='ill_scaled':
        failed=BASE/'resources/copt-fair-regenerate-1b-ill_scaled-v1.request.json'
        documents=[load(resolve(original['model'])),load(resolve(original['construction']))]
        chunks={q['sha256']:q['bytes'] for d in documents for a in arrays(d) for q in a['chunks']}
        for sha,size in chunks.items():
            path=BASE/'objects'/(sha+'.bin')
            if not path.exists():continue
            require(not path.is_symlink(),'owned regular content object');data=path.read_bytes();actual=hashlib.sha256(data).hexdigest();checked+=1
            if len(data)!=size or actual!=sha:
                require(path.stat().st_mtime_ns>=failed.stat().st_mtime_ns,'partial write belongs to interrupted regeneration')
                removed.append(dict(expected_sha256=sha,actual_sha256=actual,bytes=len(data),expected_bytes=size));path.unlink()
        put(BASE/'copt-fair-ill-scaled-partial-recovery-v1.json',dict(status='existing_chunks_checked',checked=checked,removed=removed,
            failed_reservation=ref(failed.with_name('copt-fair-regenerate-1b-ill_scaled-v1.reservation.json')),source=ref(__file__)))
    generate(identity,family,original['target'],original['seed']);fresh=load(BASE/identity/'result.json')
    require(fresh['model']['sha256']==original['model']['sha256'] and load(resolve(fresh['model']))==load(resolve(original['model'])), 'exact regenerated original model')
    require(load(resolve(fresh['construction']))==load(resolve(original['construction'])), 'exact separate construction witness for cleanup only')


def execute():
    require(completed(CPU) and completed(GPU) and completed(VALIDATION) and completed(CONTRACTS) and completed(IDLE),'all retained and fresh gates')
    require(load(BASE/IDLE/'result.json')['status']=='observed_idle','fresh sustained idle proof')
    f=load(MANIFEST);resolve(f['resumption_source']);envelope()
    require(not (MANIFEST.parent/'completed.json').exists(),'never repeat completed tail')
    for identity in f['untouched']:require(not (BASE/'resources'/(identity+'.reservation.json')).exists(),'never repeat attempted scientific cell')
    for family in ['ill_scaled','degenerate']:
        gen='copt-fair-regenerate-1b-'+family+('-v2' if family=='ill_scaled' else '-v1')
        job(gen,900,[str(PYTHON),'-B',__file__,'regenerate','--family',family],phase='development',host=32,disk=40)
        for i,c in enumerate(f['cells']):
            if c['id'] not in f['untouched'] or c['family']!=family:continue
            m=c['memory'];disk=c.get('disk_gib',math.ceil(m.get('endpoint_bytes_upper',0)/(1<<30))+1)
            s=run(c['id'],'development',2700,True,[str(PYTHON),'-B',str(resolve(f['source'])),'worker','--manifest',str(MANIFEST),'--index',str(i)],m['host_gib'],m['device_gib'],disk)
            print(dict(cell=c['id'],settlement=s),flush=True);require(s['cleanup_empty'] and not s['overrun'],'cleanup/overrun stops continuation')
            audit=c['id']+'-full-audit';a=run(audit,'reporting',c['audit_seconds'],False,[str(PYTHON),'-B',str(resolve(f['audit'])),str(MANIFEST),str(i)],64,0,math.ceil(8*load(resolve(c['model_result']))['rows']/(1<<30))+1)
            print(dict(audit=audit,settlement=a),flush=True);require(a['status']=='passed','all original-model strict proofs checked')
        job('copt-fair-prune-1b-'+family+'-v1',60,[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),str(PYTHON),'-B',str(ROOT/'tools/lp_billion_copt_fair_run.py'),'cleanup','--scale','1b','--family',family],phase='cleanup',host=8)
    put(MANIFEST.parent/'completed.json',dict(status='all_four_untouched_cells_attempted_and_audited',manifest=ref(MANIFEST)))
    put(ORIGINAL.parent/'completed.json',dict(status='all_admitted_cells_attempted_and_audited',original_freeze=ref(ORIGINAL),effective_freeze=ref(MANIFEST)))
    job('copt-fair-complete-report-v1',180,[str(PYTHON),'-B',str(ROOT/'tools/lp_mixed2_reuse_place.py'),str(PYTHON),'-B',__file__,'report'],phase='reporting',host=8)


def report():
    from lp_billion_full_report import record
    require((MANIFEST.parent/'completed.json').exists(),'completed four-cell tail');f=load(MANIFEST);rows=[]
    cohorts={identity:cohort['name'] for cohort in f['allowance_cohorts'] for identity in cohort['ids']}
    for c in f['cells']:
        r=recovered_record(c) if c['id']==CELL else record(c)
        r.update(timely_strict_certificate=False,requested_solver_wall_ns=int(c['wall_seconds']*NS),outer_reservation_seconds=c['seconds'],allowance_cohort=cohorts[c['id']])
        if r.get('response'):
            response=load(resolve(r['response']));r['timely_strict_certificate']=timely(r,response,c['wall_seconds'])
            r['requested_wall_exceeded']=r['solver_wall_ns']>r['requested_solver_wall_ns']
            r['iteration_safety_limit']=10000 if c['lane']=='fp4x2' else None
            r['iteration_limit_reached']=response.get('logical',0)>=10000 if c['lane']=='fp4x2' else None
            if c['lane']!='fp4x2':r.update(phase_journal=response['phase_journal'],interrupts=response['interrupts'])
        rows.append(r)
    comparisons=[budgeted_pair(next(r for r in rows if r['family']==family and r['lane']=='fp4x2'),next(r for r in rows if r['family']==family and r['lane']=='copt-gpu-pdlp')) for family in FAMILIES]
    path=BASE/'copt-fair-results-v1.json';require(not path.exists(),'fresh final result')
    put(path,dict(status='all_fair_comparison_outcomes_retained',cells=rows,comparisons=comparisons,freeze=ref(MANIFEST),original_freeze=ref(ORIGINAL),source=ref(__file__),strict_original_tolerance=1e-9,
        native_wall_validation=ref(BASE/VALIDATION/'result.json'),idle_admission=ref(BASE/IDLE/'result.json'),
        limitations=['All prior attempted cells retain their original allowances and outcomes.','Coupled project rejects the unsupported requested allowance before solving; it is not retried.',
                    'Tall original cold-proof timing remains unavailable.','Only jointly timely strict pairs with equal allowances support ratios.']))
    from lp_billion_copt_fair_report import main
    main()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['native_validation','freeze','observation','regenerate','execute','report']);p.add_argument('--family');a=p.parse_args()
    if a.action=='regenerate':regenerate(a.family)
    else:globals()[a.action]()
