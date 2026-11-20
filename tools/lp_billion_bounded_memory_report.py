"""Audit bounded-memory CPU observations and preserve all exclusions and failures."""
from pathlib import Path
from statistics import median
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require,CPU_CAPS,GPU_CAPS
from lp_billion_budget import accounting
from lp_billion_memory_bounds_final import bounded_capacity
from lp_billion_campaign import capacity
from lp_confirmation2_supervisor import same_process


def numerical(name):
    return name.endswith(('.rs','.cu')) or Path(name).name.startswith('Cargo.')


def main():
    before=load(BASE/'image-v8/binding.json');after=load(BASE/'image-v9/binding.json')
    for key in ['cuda','preparation']:
        require(ref(resolve(before[key]))['sha256']==ref(resolve(after[key]))['sha256'],'unchanged CUDA '+key)
    allowed={'research/lp-billion-lowbit/'+p for p in ['src/billion.rs','src/fast_device.rs','src/lib.rs','src/tensor_prepare.rs','tests/contracts.rs']}
    allowed.add('research/lp-tensor-expanded-device/cuda-sys/src/lib.rs')
    old=[];exact=[];changed=[];guards=[]
    for item in load(resolve(before['source_manifest']))['sources']:
        name=item['original']['path']
        if numerical(name):
            resolve(item['retained']);old.append(name);current=ref(ROOT/name)
            if current==item['original']:exact.append(current)
            else:
                require(name in allowed,'unexpected numerical change '+name)
                changed.append(dict(before=item['retained'],after=current))
        if name in ['tools/lp_billion_budget.py','tools/lp_billion_common.py','tools/lp_billion_idle.py',
                    'tools/lp_confirmation2_supervisor.py','tools/lp_confirmation_supervisor.py','tools/lp_mixed2_reuse_place.py']:
            resolve(item['original']);guards.append(item['original'])
    current=[]
    for item in load(BASE/'sources/operational-cpu-v17/manifest.json')['sources']:
        if numerical(item['original']['path']):
            resolve(item['original']);resolve(item['retained']);current.append(item['original'])
    added=[p for p in current if p['path'] not in old]
    require((len(old),len(exact),len(changed),len(current),len(added),len(guards))==(297,291,6,299,2,6),'complete source coverage')
    build=load(BASE/'bounded-memory-diagnostic-v1/result.json')
    require(resolve(build['retained_reference']).read_bytes()==resolve(build['reference_source']).read_bytes(),'exact v8 packing reference')
    resolve(build['executable']);[resolve(i) for i in build['libraries'].values()]
    require(load(BASE/'build-bounded-memory-v1/result.json')['rust_tests']==58,'complete Rust quality')
    gates=[]
    for name in ['bounded-memory-quality-v1','bounded-upload-contracts-v1','bounded-memory-seal-v1',
                 'bounded-memory-diagnostic-build-v1','bounded-memory-freeze-v1','operational-cpu-v16',
                 'bounded-memory-tail-freeze-v1','operational-cpu-v17','bounded-memory-contracts-v2']:
        p=BASE/'resources'/(name+'.settlement.json');s=load(p)
        require(s['status']=='passed' and s['cleanup_empty'] and not s['overrun'] and s['gpu_ns']==0,'complete CPU gate '+name)
        gates.append(ref(p))
    f=load(BASE/'bounded-memory-cpu-v1/freeze.json');cells=[]
    tail=load(BASE/'bounded-memory-cpu-tail-v1.json');tail_ids={c['id'] for c in tail['cells']}
    require(len(tail_ids)==8 and not tail_ids.intersection(c['cell'] for c in tail['attempted']),'disjoint never-attempted tail')
    for c in f['cells']:
        reservation=BASE/'resources'/(c['id']+'.reservation.json')
        if not reservation.exists():
            refusal=BASE/'bounded-memory-cpu-v1'/(c['id']+'.capacity-refusal.json');resolve(ref(refusal))
            cells.append(dict(cell=c['id'],scale=c['scale'],family=c['family'],implementation=c['implementation'],capacity_refusal=ref(refusal),eligible=False));continue
        s_path=BASE/'resources'/(c['id']+'.settlement.json');s=load(s_path);resource=load(resolve(s['resource']))
        require(s['cleanup_empty'] and not s['overrun'] and s['gpu_ns']==0,'complete CPU-only supervision '+c['id'])
        identities=resource['result']['observed_processes']
        require(not any(same_process(i) for i in identities),'no owned diagnostic process survives')
        raw_path=BASE/c['id']/'preparation.stdout';r=load(raw_path)
        m=load(resolve(c['model_result']))
        require(r['status']=='passed' and r['model_sha256']==c['model']['sha256'] and r['nonzeros']==m['nonzeros'] and
                r['tile_count']==m['canonical_tiles'] and not r['lp_solve_executed'] and not r['cuda_context_created'],'original complete CPU response')
        bound=bounded_capacity(m,'fp4x2')
        if c['implementation']=='candidate':require(r['packed_bytes']<=bound['packed_bytes_upper'],'corrected exact final storage bound')
        if s['status']=='passed':
            result=load(BASE/c['id']/'result.json');require(result['raw']==ref(raw_path),'raw result binding');process_ns=result['process_ns']
        else:
            require(c['id']=='bounded-memory-cpu-v1-64m-3-candidate','only retained eight-byte refusal');process_ns=None
        cells.append(dict(cell=c['id'],family=c['family'],scale=c['scale'],implementation=c['implementation'],
            eligible=s['status']=='passed',raw=ref(raw_path),settlement=ref(s_path),source_manifest=load(reservation)['source_manifest'],
            timing_ns={k:r[k] for k in ['input_ns','engine_ns','operator_ns','packing_ns','preparation_ns','fingerprint_ns','process_body_ns']},
            fresh_process_ns=process_ns,hwm_bytes=r['after_drop']['hwm_bytes'],sampled_aggregate_rss_bytes=resource['result']['peak_rss_bytes'],
            memory_stages={k:r[k] for k in ['after_input','after_engine','after_packing','after_drop']},
            packed_bytes=r['packed_bytes'],packed_sha256=r['packed_sha256'],tile_count=r['tile_count'],nonzeros=r['nonzeros'],
            excluded_reason=None if s['status']=='passed' else 'Final host-bound assertion omitted eight bytes; retain raw data and full charge, exclude performance.',
            cleanup_empty=True,all_owned_identities_absent=True))
    pairs=[]
    for key in sorted({(c['scale'],c['family']) for c in cells if c['scale']!='1b'}):
        pair={c['implementation']:c for c in cells if (c['scale'],c['family'])==key}
        a,b=pair['reference'],pair['candidate']
        if 'raw' not in a or 'raw' not in b:continue
        require(a['packed_sha256']==b['packed_sha256'] and a['packed_bytes']==b['packed_bytes'] and a['tile_count']==b['tile_count'],'complete packed-byte pair')
        eligible=a['eligible'] and b['eligible']
        pairs.append(dict(scale=key[0],family=key[1],exact_packed_bytes=True,eligible=eligible,
            reference=a['raw'],candidate=b['raw'],reference_hwm_bytes=a['hwm_bytes'],candidate_hwm_bytes=b['hwm_bytes'],
            hwm_ratio=a['hwm_bytes']/b['hwm_bytes'] if eligible else None,
            packing_ratio=a['timing_ns']['packing_ns']/b['timing_ns']['packing_ns'] if eligible else None,
            preparation_ratio=a['timing_ns']['preparation_ns']/b['timing_ns']['preparation_ns'] if eligible else None))
    failures=[]
    for p in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(p)
        if s['status']!='passed':failures.append(dict(settlement=ref(p),cpu_ns=s['cpu_ns'],gpu_ns=s['gpu_ns']))
    require(len(failures)==22 and sum(f['cpu_ns'] for f in failures)==40_020_000_000_000 and
            sum(f['gpu_ns'] for f in failures)==1_800_000_000_000,'all failures and full charges')
    prospective=[]
    for p in sorted(BASE.glob('models-1b-*/result.json')):
        m=load(p)
        for lane in ['native','fp32','fp4x2']:
            a=capacity(m,lane,True);b=bounded_capacity(m,lane)
            prospective.append(dict(family=m['family'],lane=lane,old_host_with_headroom_gib=a['host_gib']+4,
                new_host_with_headroom_gib=b['host_gib']+4,stages=b,model=ref(p)))
    for kind in ['gpu','memcheck','racecheck','initcheck','synccheck']:
        require(not (BASE/'resources'/('bounded-memory-'+kind+'-v1.reservation.json')).exists(),'GPU admission unattempted')
    cpu,gpu=accounting();plan=load(BASE/'billion-comparison-plan-v1.json')
    require(plan['status']=='prospective_not_frozen' and len(plan['cells'])==30 and plan['billion_solves']==0,'full roster unfrozen')
    result=dict(status='CPU_bounded_memory_validated_GPU_admission_pending',image=ref(BASE/'image-v9/binding.json'),
        capacity_source=ref(ROOT/'tools/lp_billion_memory_bounds_final.py'),original_freeze=ref(BASE/'bounded-memory-cpu-v1/freeze.json'),tail=ref(BASE/'bounded-memory-cpu-tail-v1.json'),
        cells=cells,pairs=pairs,exact_pairs=len(pairs),eligible_pairs=sum(p['eligible'] for p in pairs),
        successful_responses=sum(c['eligible'] for c in cells),raw_responses=sum('raw' in c for c in cells),
        billion_preparation=[c for c in cells if c['scale']=='1b'],billion_LP_solves=0,
        rust_tests=58,upload_boundary_tests=1,supervisor_tests=75,python_contract_tests=42,gates=gates,
        source_bindings=current,unchanged_numerical_bindings=len(exact),changed=changed,added=added,unchanged_guards=guards,
        diagnostic_build=ref(BASE/'bounded-memory-diagnostic-v1/result.json'),failures=failures,prospective_capacity=prospective,
        host_capacity=ref(BASE/'billion-host-availability-v6.json'),cpu_caps=CPU_CAPS,gpu_caps=GPU_CAPS,
        cpu_ns_including_active_reservations=cpu,gpu_ns_including_active_reservations=gpu,allocation_open=True,
        gpu_admission_started=False,comparison=ref(BASE/'billion-comparison-plan-v1.json'),
        previous_capacity_counts=dict(cells=38,responses=37,eligible_timings=35,missing=1),
        previous_CPU_packing_counts=dict(responses=18,eligible_timings=12,excluded=6),portable_replay_claim=False,
        limitations=['CPU-only fresh-process preparation; no GPU/upload or certified solve measurement.',
                    'Single observations; no repeatability claim. Failed coupled64M timing excluded.',
                    'Prospective bounds include unchanged CPU fallback and repaired witnesses; preliminary 60 GiB is superseded.',
                    'VmHWM is per-process high-water RSS; sampled aggregate RSS is not an exact aggregate peak.'])
    put(BASE/'bounded-memory-delivery-v1.json',result)
    compact={k:v for k,v in result.items() if k not in ['source_bindings','cells','prospective_capacity']}
    compact['delivery']=ref(BASE/'bounded-memory-delivery-v1.json')
    compact['capacity_fp4']=[dict(family=c['family'],before_gib=c['old_host_with_headroom_gib'],after_gib=c['new_host_with_headroom_gib'],peak=c['stages']['peak_stage']) for c in prospective if c['lane']=='fp4x2']
    compact['cells']=[{k:v for k,v in c.items() if k not in ['memory_stages','source_manifest']} for c in cells]
    put(ROOT/'docs/benchmarks/lp-billion-bounded-memory-results.json',compact)
    print(dict(status=result['status'],exact_pairs=len(pairs),eligible_pairs=result['eligible_pairs'],sources=len(current)),flush=True)

if __name__=='__main__':main()
