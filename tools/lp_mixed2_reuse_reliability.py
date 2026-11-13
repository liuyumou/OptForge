"""Source-bound disposition of CPU/process probes, with unresolved causes explicit."""
import json
from lp_mixed2_reuse_common import BASE, OLD, ROOT, load, put, ref, require


def run():
    rows=[]
    for name in ['cpu-diagnose-four-a','cpu-diagnose-three-a','cpu-diagnose-three-b','cpu-diagnose-four-b',
                 'host-probe-unpinned-v1','host-probe-pinned-v1','models-v2','models-v3','serial-admission-v2','serial-admission-v3']:
        path=BASE/'resources'/(name+'.resource.json');d=load(path)
        row=dict(job=name,resource=ref(path),status=d['status'],reason=d['result']['reason'],
                 max_sample_gap_ns=d['result'].get('max_sample_gap_ns'),
                 peak_rss_bytes=d['result'].get('peak_rss_bytes'),elapsed_ns=d['active_elapsed_ns'])
        trace=path.with_name(path.name+'.telemetry.jsonl')
        if trace.exists():
            rs=[json.loads(x) for x in trace.read_text().splitlines()]
            hs=[x for x in rs if x['kind']=='heartbeat']
            if len(hs)>1:
                a,b=max(zip(hs,hs[1:]),key=lambda pair:pair[1]['begin_ns']-pair[0]['begin_ns'])
                before=list(map(int,a['schedstat'].split()));after=list(map(int,b['schedstat'].split()))
                row['largest_observed_heartbeat_gap']=dict(gap_ns=b['begin_ns']-a['begin_ns'],
                    coordinator_cpu_ns=after[0]-before[0],coordinator_runqueue_wait_ns=after[1]-before[1],
                    begin_ns=a['begin_ns'],end_ns=b['begin_ns'])
            row['telemetry']=ref(trace)
        rows.append(row)
    races=[]
    for name in ['race-all-four-v1','race-application-three-v1','race-all-three-v1','race-application-four-v1']:
        result=load(BASE/name/'result.json')
        require(load(BASE/'resources'/(name+'.settlement.json'))['status']=='passed','race job supervision')
        for r in result['rows']:
            require(r['returncode']==0 and r['certified'],'unresolved fresh process failure blocks timing')
        logs=[ref(p) for p in sorted((BASE/name).glob('*.sanitizer'))]
        require(len(logs)==4,'missing diagnostic sanitizer logs')
        for item in logs:
            require('RACECHECK SUMMARY: 0 hazards' in (ROOT/item['path']).read_text(),'race diagnostic hazards')
        races.append(dict(name=name,result=ref(BASE/name/'result.json'),rows=result['rows'],logs=logs))
    for name in ['device-v2','scenario-large-v2','scenario-invalid-v2','scenario-recovery-v2','serial-admission-v3','processes-v2','resource-pilot-v1']+[
            n+'-v2' for n in ('memcheck','racecheck','initcheck','synccheck')]+[
            'scenario-'+n+'-v3' for n in ('memcheck','racecheck','initcheck','synccheck')]:
        require(load(BASE/name/'result.json')['status']=='passed','current host admission missing: '+name)
    put(BASE/'reliability-v1.json',dict(schema_version=1,proceed_research_confirmation=True,
        cpu_probes=rows,race_probes=races,supervisor=ref(ROOT/'tools/lp_cpu_admission.py'),
        historical_failures=[ref(OLD/'resources'/f'{n}.resource.json') for n in
                             ['confirmation-b25','product-oracle-v1','racecheck-v3']],
        observations=[
            'A fresh CPU-only preparation missed the unchanged 100 ms heartbeat despite three-CPU work placement.',
            'The successful instrumented pinned preparation contains a long gap dominated by coordinator runqueue wait.',
            'Fresh pinned preparation and current device/scenario/scoped sanitizer admission passed.',
            'Sixteen prospectively specified old/current-host process probes cross two sanitizer scopes and two placements.'],
        limitations=[
            'The historical heartbeat causes and two current uninstrumented CPU misses remain unassigned; no scheduling telemetry survives those failed instants.',
            'Long-gap scheduling evidence comes from a successful instrumented run, not the failed instant.',
            'Pinning separates our workers from our controls, not from other host users; it is no availability guarantee.',
            'The historical sanitizer exit 11 did not reproduce; successful probes do not prove a repair.',
            'Application-only sanitizer scope covers the CUDA root process; independent checker admission is CPU-only.',
            'These admissions permit bounded research timing, not production readiness.'],
        primary_placement=ref(ROOT/'tools/lp_mixed2_reuse_place.py'),
        unchanged_max_gap_ns=100000000,production_readiness=False))


if __name__=='__main__':run()
