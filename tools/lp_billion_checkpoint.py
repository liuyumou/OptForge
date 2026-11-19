"""Compact, source-bound progress checkpoint; construction is never a solve result."""
import argparse
import subprocess
from pathlib import Path
from lp_billion_common import BASE,ROOT,load,put,ref,resolve,require,CPU_CAPS,GPU_CAPS,disk_bytes
from lp_billion_budget import accounting
from lp_billion_generate import FAMILIES

ORIGIN='53d7879c128d886cbac260c5c9238a9cdb9a0703'


def checkpoint(identity):
    require(identity and Path(identity).name==identity and identity not in ['.','..'],'checkpoint identity')
    changed=subprocess.check_output(['git','diff','--name-only','--diff-filter=MDRT','-z',ORIGIN],cwd=ROOT).decode().split('\0')
    require(set(changed)-{''} <= {'AGENTS.md','state/active-task.md'},'protected tracked files changed')
    for name in ['AGENTS.md','state/active-task.md']:
        old=subprocess.check_output(['git','show',ORIGIN+':'+name],cwd=ROOT).decode()
        tail=old if name=='AGENTS.md' else old.split('\n',2)[2]
        require((ROOT/name).read_text().endswith(tail),'historical handoff changed')
    quality=load(BASE/'sources/array-quality-v6/manifest.json')
    bindings=0
    for item in quality['sources']:
        path=Path(item['original']['path'])
        if path.suffix in ['.rs','.cu'] or path.name.startswith('Cargo.'):
            resolve(item['original']);resolve(item['retained']);bindings+=1
    built=load(BASE/'build-prepare-v3/result.json');resolve(built['cuda']);resolve(built['cuda_source'])
    images=[]
    for version in [1,2]:
        p=BASE/f'image-v{version}/binding.json';binding=load(p)
        for name in ['executor','legacy','cuda']:resolve(binding[name])
        images.append(ref(p))
    inputs=[]
    for family in FAMILIES:
        path=BASE/f'models-1b-{family}-v1/result.json';model=load(path)
        proof=path.with_name('construction-check.json');certificate=load(proof)
        require(model['nonzeros']==1_000_000_000 and certificate['accepted'] and certificate['model']==model['model'],'complete original construction')
        resource=BASE/'resources'/f'generate-1b-{family}-v1.settlement.json';settlement=load(resource)
        require(settlement['status']=='passed' and settlement['cleanup_empty'] and not settlement['overrun'],'construction supervision')
        inputs.append(dict(family=family,rows=model['rows'],columns=model['columns'],nonzeros=model['nonzeros'],
            canonical_tiles=model['canonical_tiles'],covered_nnz=model['covered_nnz'],
            model=ref(path),construction_check=ref(proof),resource=ref(resource)))
    cells=[]
    from lp_billion_portable import arrays
    for path in sorted(BASE.glob('ladder-*/freeze.json')):
        for cell in load(path)['cells']:
            row=dict(id=cell['id'],freeze=ref(path),status=cell['status'])
            output=BASE/cell['id']/'response.json'
            settlement=BASE/'resources'/(cell['id']+'.settlement.json')
            if output.exists():
                response=load(output);final=output.parent.with_name(output.parent.name+'-final-check')/'result.json'
                audit=output.parent.with_name(output.parent.name+'-audit')/'result.json'
                require(load(final)['status']==load(audit)['status']=='passed','independent endpoint checking')
                require(load(final)['response']==load(audit)['response']==ref(output),'endpoint audit bindings')
                chunks={c['sha256']:c['bytes'] for a in arrays(response) for c in a['chunks']}
                reservation=load(settlement.with_name(cell['id']+'.reservation.json'))
                require(sum(chunks.values())<=reservation['disk_bytes'],'actual endpoint payload exceeds original disk reservation')
                excluded=settlement.with_name(cell['id']+'.ownership-disposition.json')
                row.update(status=response['status'],certified=response['certified'],response=ref(output),final=ref(final),audit=ref(audit),
                    unique_endpoint_payload_bytes=sum(chunks.values()),
                    repaired_dual_assessments=sum('certificate_dual_array' in e['certificate'] for e in [*response['assessments'],response]),
                    timing_eligible=load(settlement)['status']=='passed' and not excluded.exists(),
                    ownership_disposition=ref(excluded) if excluded.exists() else None)
            else:row['status']='missing' if settlement.exists() else cell['status']
            if settlement.exists():row['settlement']=ref(settlement)
            cells.append(row)
    failed=[]
    for p in sorted((BASE/'resources').glob('*.settlement.json')):
        if load(p)['status']!='passed':failed.append(dict(receipt=ref(p),**load(p)))
    cpu,gpu=accounting()
    gates={name:(ref(p) if (p:=BASE/'resources'/(name+'.settlement.json')).exists() else None)
           for name in ['operational-gpu-v8','array-gpu-v3','array-memcheck-v3','array-racecheck-v3','array-initcheck-v3','array-synccheck-v3']}
    admitted=all(p and load(resolve(p))['status']=='passed' for p in gates.values())
    result=dict(status='gpu_preparation_admitted' if admitted else 'awaiting_gpu_preparation_admission',
        origin_commit=ORIGIN,protected_tracked_files_exact=True,historical_handoffs_exact=True,
        current_numerical_source_bindings=bindings,host_quality=ref(BASE/'build-prepare-v3/result.json'),
        cpu_contracts=ref(BASE/'resources/preparation-harness-cpu-v2.settlement.json'),images=images,
        billion_inputs=inputs,billion_solve_measurements=sum(load(p).get('nonzeros')==1_000_000_000 for p in BASE.glob('*/response.json')),capacity_cells=cells,
        gpu_preparation_gates=gates,failed_reservations=failed,
        cpu_caps=CPU_CAPS,gpu_caps=GPU_CAPS,cpu_ns_including_active_reservations=cpu,gpu_ns_including_active_reservations=gpu,
        evidence_payload_bytes=disk_bytes(),allocation_open=not (BASE/'CLOSED.json').exists(),
        operational_plan=ref(BASE/'operational-readmissions/v8.json'),
        protocols=[ref(p) for p in sorted((ROOT/'docs/specifications').glob('SPEC-0046*.md'))],
        limitation='Construction certificates establish ready inputs, not LP solves. GPU preparation has no measured benefit before device admission and experiments.')
    put(BASE/(identity+'.json'),result)
    print(dict(status=result['status'],inputs=len(inputs),measured_capacity=sum('response' in c for c in cells),
        eligible_timings=sum(c.get('timing_eligible',False) for c in cells),missing=sum(c['status']=='missing' for c in cells),
        failed_reservations=len(failed),numerical_source_bindings=bindings),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);a=p.parse_args();checkpoint(a.id)
