"""Compact timeline diagnostics; sampled timelines are not uninstrumented latency."""
import argparse
import collections
import sqlite3
import statistics
from pathlib import Path
from lp_general_common import BASE,ROOT,load,put,ref,require
from lp_general_tensor_diagnosis_report import distribution


def report(identity,output):
    root=BASE/identity;f=load(root/'freeze.json');results=[]
    for cell in f['cells']:
        modes={mode:load(root/(cell['id']+'-'+mode)/'response.json') for mode in ['before','trace','after']}
        db=root/(cell['id']+'-trace')/'trace.sqlite';c=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
        kernels=[dict(r) for r in c.execute('SELECT k.*,s.value AS name FROM CUPTI_ACTIVITY_KIND_KERNEL k JOIN StringIds s ON k.shortName=s.id ORDER BY start')]
        mapping=list(c.execute('SELECT DISTINCT gpuId FROM TARGET_INFO_CUDA_DEVICE WHERE cudaId=?',(kernels[0]['deviceId'],)));require(len(mapping)==1,'physical mapping')
        device=dict(c.execute('SELECT * FROM TARGET_INFO_GPU WHERE id=?',(mapping[0]['gpuId'],)).fetchone());require(device['uuid']=='6721b13a-30f9-83ec-dace-ba2d9738556f','pinned UUID')
        groups=collections.defaultdict(list)
        for k in kernels:groups[(k['name'],k['gridX'],k['blockX'])].append(k)
        summaries=[dict(name=n,grid=g,block=b,duration_ns=distribution([r['end']-r['start'] for r in rs]),registers=sorted({r['registersPerThread'] for r in rs}),local_bytes=sorted({r['localMemoryPerThread'] for r in rs})) for (n,g,b),rs in sorted(groups.items())]
        steps=[r for r in kernels if r['name'].startswith(('fast_step_','fast_product_','fast_combined_'))]
        require(len(steps)%5==0,'fixed 500 updates in five windows');width=len(steps)//5;windows=[steps[i:i+width] for i in range(0,len(steps),width)]
        active=sum(r['end']-r['start'] for r in steps);span=sum(w[-1]['end']-w[0]['start'] for w in windows)
        results.append(dict(cell=cell['id'],model_index=cell['model_index'],format=cell['format'],device={k:device[k] for k in ['name','uuid','smCount','maxWarpsPerSm','l2CacheSize']},database=ref(db),kernels=summaries,
            update_kernel_ns=active,update_span_ns=span,inter_kernel_gap_ns=span-active,
            cost_ns={m:r['cost_ns'] for m,r in modes.items()},profiler_execution_ratio={m:modes['trace']['cost_ns']['execution']/modes[m]['cost_ns']['execution'] for m in ['before','after']}))
        c.close()
    put(output,dict(status='passed',freeze=ref(root/'freeze.json'),rows=results,source=ref(__file__),limits='Timeline durations include profiler disturbance; no hardware counters or measured occupancy. Device ordinal verified against physical UUID.'))
    for r in results:print(r['cell'],{k:round(r[k]/1e6,3) for k in ['update_kernel_ns','update_span_ns','inter_kernel_gap_ns']},r['profiler_execution_ratio'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();report(a.id,a.output)
