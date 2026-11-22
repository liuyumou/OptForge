"""Prospective continuation of only unattempted bounded-memory CPU cells."""
import argparse
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,require
from lp_billion_prepare_continue import job
from lp_billion_memory_bounds import bounded_capacity

TAIL=BASE/'bounded-memory-cpu-tail-v1.json'

def freeze():
    original=BASE/'bounded-memory-cpu-v1/freeze.json';f=load(original);cells=[];attempted=[]
    for index,c in enumerate(f['cells']):
        reservation=BASE/'resources'/(c['id']+'.reservation.json')
        if reservation.exists():
            settlement=reservation.with_name(c['id']+'.settlement.json')
            require(settlement.exists(),'all previous attempts settled')
            attempted.append(dict(cell=c['id'],settlement=ref(settlement)));continue
        b=bounded_capacity(load(BASE/c['model_result']['path']),'fp4x2')
        c=dict(c,index=index)
        if c['scale']=='1b':c.update(host_gib=b['CPU_preparation_host_gib'],memory_bound=b)
        require(c['host_gib']>=b['CPU_preparation_host_gib'],'complete preparation reserve')
        cells.append(c)
    require(len(cells)==8 and len(attempted)==7,'original attempted/unattempted partition')
    put(TAIL,dict(status='frozen_unattempted_tail',original=ref(original),cells=cells,attempted=attempted,
        source=ref(__file__),capacity_source=ref(ROOT/'tools/lp_billion_memory_bounds.py'),
        protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-38.md'),billion_LP_solves=0))
    for new,old in [(21,19),(22,20)]:
        plan=load(BASE/f'operational-readmissions/v{old}.json')
        plan.update(protocol=ref(ROOT/'docs/specifications/SPEC-0046-amendment-38.md'),cpu_admission_job='operational-cpu-v17',
                    cpu_only_jobs=[c['id'] for c in cells],deferred_never_started=[])
        plan['cpu_only_sources']=[ref(ROOT/i['path']) if i['namespace']=='repo' else i for i in plan['cpu_only_sources']]
        plan['cpu_only_sources'] += [ref(__file__),ref(TAIL)]
        put(BASE/f'operational-readmissions/v{new}.json',plan)
    print(dict(unattempted_cells=len(cells),billion_host_gib=cells[-1]['host_gib']),flush=True)

def execute():
    for c in load(TAIL)['cells']:
        require(not (BASE/'resources'/(c['id']+'.reservation.json')).exists(),'tail never retries an attempted cell')
        available=int(next(l for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')).split()[1])*1024
        if available<(c['host_gib']+4)*2**30:
            put(BASE/'bounded-memory-cpu-v1'/(c['id']+'.capacity-refusal.json'),dict(status='never_started_capacity_refusal',
                host_available_bytes=available,host_required_bytes=(c['host_gib']+4)*2**30,cell=c['id'],tail=ref(TAIL)))
            continue
        job(c['id'],c['seconds'],['python3','-B',str(ROOT/'tools/lp_billion_bounded_memory.py'),'worker','--index',str(c['index'])],
            phase='development',host=c['host_gib'],disk=1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','execute']);a=p.parse_args();globals()[a.action]()
