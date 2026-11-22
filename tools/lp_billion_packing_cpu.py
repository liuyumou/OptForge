"""Source-bound CPU-only packing diagnostics; never starts GPU admission."""
import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require
from lp_billion_prepare_continue import job
from lp_billion_budget import accounting

COHORT='cpu-packing-64m-v1'
BUILD='packing-cpu-build-v1'
SOURCE=ROOT/'research/lp-billion-lowbit/diagnostics/packing.rs'


def build():
    out=BASE/BUILD;out.mkdir()
    require(load(BASE/'resources/packing-quality-v1.settlement.json')['status']=='passed','candidate CPU quality')
    image=load(BASE/'image-v5/binding.json')
    for item in load(resolve(image['source_manifest']))['sources']:
        if item['original']['path'].endswith(('.rs','.cu')) or Path(item['original']['path']).name.startswith('Cargo.'):
            resolve(item['original']);resolve(item['retained'])
    def command(name,args):
        r=subprocess.run(list(map(str,args)),capture_output=True,text=True)
        (out/(name+'.stdout')).write_text(r.stdout);(out/(name+'.stderr')).write_text(r.stderr)
        require(r.returncode==0,'diagnostic '+name+': '+r.stderr[-1500:])
    command('format',['rustfmt','--edition','2024','--check',SOURCE])
    command('library',['cargo','build','--manifest-path','research/lp-billion-lowbit/Cargo.toml','--release','--offline','--lib'])
    deps=BASE/'target/release/deps'
    def library(name):
        paths=list(deps.glob('lib'+name+'-*.rlib'));require(len(paths)==1,'unambiguous linked library '+name);return paths[0]
    linked=library('lp_billion_lowbit');serde=library('serde_json');exe=out/'packing'
    command('compile',['rustc','--edition','2024','-C','opt-level=3','-C','debuginfo=0',
        '--extern','lp_billion_lowbit='+str(linked),'--extern','serde_json='+str(serde),
        '-L','dependency='+str(deps),SOURCE,'-o',exe])
    request=out/'smoke-request.json';put(request,load(BASE/'ladder-64m-v4/freeze.json')['cells'][0]['request'])
    smokes=[]
    for fixture in ['dense','irregular']:
        for order in ['reference-first','candidate-first']:
            name=fixture+'-'+order
            command(name,[exe,BASE/('memory-gpu-v1/'+fixture+'.arrays.json'),BASE,request,order])
            result=json.loads((out/(name+'.stdout')).read_text())
            require(result['exact'] and not result['cuda_context_created'] and not result['lp_solve_executed'],'CPU-only exact smoke')
            smokes.append(ref(out/(name+'.stdout')))
    put(out/'result.json',dict(status='passed',source=ref(SOURCE),library=ref(linked),serde=ref(serde),
        executable=ref(exe),smokes=smokes,image=ref(BASE/'image-v5/binding.json')))


def freeze():
    out=BASE/COHORT
    require(not out.exists(),'fresh CPU diagnostic cohort')
    built=load(BASE/BUILD/'result.json');resolve(built['executable'])
    cells=[]
    for index,previous in enumerate(load(BASE/'ladder-64m-v4/freeze.json')['cells']):
        model=load(resolve(previous['model_result']))
        require(model['nonzeros']==64_000_000,'complete 64 M original input')
        cells.append(dict(id=COHORT+'-'+str(index),family=model['family'],model=previous['model'],
            model_result=previous['model_result'],request=previous['request'],canonical_tiles=model['canonical_tiles'],
            order='reference-first' if index%2==0 else 'candidate-first',seconds=240,host_gib=20,disk_gib=1))
    put(out/'freeze.json',dict(status='frozen',cells=cells,build=ref(BASE/BUILD/'result.json'),
        executable=built['executable'],source=ref(SOURCE),harness=ref(__file__),
        protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-24.md'),
        claim='One CPU-only packing pair per original input; no GPU context, full preparation or solve measurement.'))


def worker(index):
    manifest=load(BASE/COHORT/'freeze.json');cell=manifest['cells'][index]
    exe=resolve(manifest['executable']);model=resolve(cell['model'])
    out=BASE/cell['id'];out.mkdir();request=out/'request.json';put(request,cell['request'])
    started=time.monotonic_ns()
    r=subprocess.run(list(map(str,[exe,model,BASE,request,cell['order']])),capture_output=True,text=True)
    elapsed=time.monotonic_ns()-started
    (out/'stdout.json').write_text(r.stdout);(out/'stderr').write_text(r.stderr)
    require(r.returncode==0,'CPU packing diagnostic failed: '+r.stderr)
    result=json.loads(r.stdout)
    require(result['status']=='passed' and result['exact'] and result['nonzeros']==64_000_000 and
        result['tile_count']==cell['canonical_tiles'] and not result['cuda_context_created'] and not result['lp_solve_executed'],
        'exact full-input CPU packing diagnostic')
    put(out/'result.json',dict(status='passed',family=cell['family'],order=cell['order'],raw=ref(out/'stdout.json'),
        process_ns=elapsed,freeze=ref(BASE/COHORT/'freeze.json')))


def report():
    manifest=BASE/COHORT/'freeze.json';rows=[]
    for cell in load(manifest)['cells']:
        result_path=BASE/cell['id']/'result.json';result=load(result_path);raw=load(resolve(result['raw']))
        settlement_path=BASE/'resources'/(cell['id']+'.settlement.json');settlement=load(settlement_path)
        require(settlement['status']=='passed' and settlement['cleanup_empty'] and not settlement['overrun'] and settlement['gpu_ns']==0,'complete CPU-only supervision')
        resource=load(resolve(settlement['resource']))
        require(raw['exact'] and not raw['cuda_context_created'] and not raw['lp_solve_executed'],'CPU diagnostic boundary')
        rows.append(dict(family=cell['family'],order=cell['order'],nonzeros=raw['nonzeros'],tile_count=raw['tile_count'],
            reference_packing_ns=raw['reference_packing_ns'],candidate_packing_ns=raw['candidate_packing_ns'],
            packing_ratio=raw['reference_packing_ns']/raw['candidate_packing_ns'],input_ns=raw['input_ns'],
            engine_ns=raw['engine_ns'],operator_ns=raw['operator_ns'],process_ns=result['process_ns'],
            peak_rss_bytes=resource['result']['peak_rss_bytes'],exact=True,result=ref(result_path),settlement=ref(settlement_path)))
    from lp_confirmation2_supervisor import same_process
    interruptions=[]
    for name in ['operational-gpu-v11','operational-gpu-v12']:
        path=BASE/'resources'/(name+'.settlement.json');s=load(path);r=load(resolve(s['resource']))
        require(s['status']=='refused' and s['cleanup_empty'] and not s['overrun'] and
            s['cpu_ns']==480_000_000_000 and s['gpu_ns']==120_000_000_000,'retained full operational failure')
        identities={(p['pid'],p['start_ticks']):p for p in r['guardian_cleanup']['killed']+r['result']['cleanup']['killed']}
        require(not any(same_process(p) for p in identities.values()),'owned process still alive')
        interruptions.append(dict(identity=name,settlement=ref(path),reason=r['result']['reason'],
            identities=list(identities.values()),live_identities=0,partial_new_responses=len(list((BASE/name).glob('*-new.stdout.jsonl')))))
    failures=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(path)
        if s['status']!='passed':failures.append(dict(settlement=ref(path),cpu_ns=s['cpu_ns'],gpu_ns=s['gpu_ns']))
    cpu,gpu=accounting()
    put(BASE/'packing-progress-v1.json',dict(status='cpu_stage_measured_gpu_admission_pending',
        image=ref(BASE/'image-v5/binding.json'),quality=ref(BASE/'build-packing-v1/result.json'),
        diagnostic_build=ref(BASE/BUILD/'result.json'),freeze=ref(manifest),cells=rows,
        median_packing_ratio=statistics.median(r['packing_ratio'] for r in rows),
        interrupted_admissions=interruptions,failed_reservations=failures,
        observations=[dict(result=ref(BASE/('packing-idle-v'+str(i)+'/result.json')),
            settlement=ref(BASE/('resources/packing-idle-v'+str(i)+'.settlement.json'))) for i in range(1,4)],
        operational_plan=ref(BASE/'operational-readmissions/v13.json'),
        cpu_admission=ref(BASE/'resources/operational-cpu-v13.settlement.json'),
        cpu_ns_including_active=sum(cpu.values()),gpu_ns_including_active=sum(gpu.values()),
        candidate_gpu_validation_started=False,candidate_scientific_cells_started=0,billion_solves=0,
        strict_certificates_unchanged=True,source=ref(__file__),
        limitation='Single paired CPU packing-stage measurements with alternating order. No measured full-preparation, GPU execution or complete-solve speedup.'))
    print(dict(status='passed',cells=len(rows),median_packing_ratio=statistics.median(r['packing_ratio'] for r in rows)),flush=True)


def main():
    job(BUILD,120,['bash','tools/lp_general_env.sh','python3','-B',__file__,'build'])
    built=load(BASE/BUILD/'result.json')
    plan_path=BASE/'operational-readmissions/v13.json'
    if not plan_path.exists():
        plan=load(BASE/'operational-readmissions/v12.json')
        plan.update(protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-24.md'),
            cpu_admission_job='operational-cpu-v13',admission_job='operational-gpu-v13',
            supersedes_failed=['operational-gpu-v11','operational-gpu-v12'],
            interrupted_operational_admissions=[ref(BASE/('resources/operational-gpu-v'+str(i)+'.settlement.json')) for i in [11,12]],
            cpu_only_jobs=[COHORT+'-'+str(i) for i in range(6)],cpu_only_sources=[ref(SOURCE),ref(__file__),built['library'],built['executable']])
        put(plan_path,plan)
    job('operational-cpu-v13',120,['bash','-c','set -e\npython3 -B -m unittest discover -s tests/integration -p "test_lp_confirmation*supervisor.py"\npython3 -B -m unittest discover -s tests/integration -p "test_lp_billion*.py"'])
    manifest=BASE/COHORT/'freeze.json'
    if not manifest.exists():freeze()
    for index,cell in enumerate(load(manifest)['cells']):
        job(cell['id'],cell['seconds'],['python3','-B',__file__,'worker','--index',str(index)],
            phase='development',host=cell['host_gib'],disk=cell['disk_gib'])
    job('packing-cpu-report-v1',120,['python3','-B',__file__,'report'],phase='reporting',host=8)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','worker','report','run']);p.add_argument('--index',type=int);a=p.parse_args()
    if a.action=='worker':worker(a.index)
    else:{'build':build,'report':report,'run':main}[a.action]()
