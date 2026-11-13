"""Retained-record diagnosis; no new numerical execution or cohort regrading."""
import argparse
import json
from collections import Counter
from lp_mixed2_reuse_common import BASE, ROOT, load, put, ref, require
from lp_mixed2_reuse_analysis import DATA, ANALYSIS
from lp_mixed2_reuse_incomplete import collect

TARGET=DATA/'mixed2-reuse-diagnosis-v1.json'


def postfailure_probe():
    name='postfailure-probe-v1';resource=BASE/'resources'/(name+'.resource.json');r=load(resource)
    telemetry=[]
    for path in sorted((BASE/name).glob('phase-*/parent-telemetry.jsonl')):
        first=previous=last=None;count=gap=0
        with path.open() as stream:
            for line in stream:
                row=json.loads(line);count+=1
                if first is None:first=row
                if previous is not None:gap=max(gap,row['time_ns']-previous['time_ns'])
                previous=last=row
        parse=lambda row:dict((k,int(v)) for k,v in (line.split() for line in row['cpu.stat'].splitlines()))
        before,after=parse(first),parse(last)
        telemetry.append(dict(binding=ref(path),samples=count,max_observer_gap_ns=gap,
            cgroup_throttled_periods_delta=after['nr_throttled']-before['nr_throttled'],
            cgroup_throttled_usec_delta=after['throttled_usec']-before['throttled_usec'],
            memory_events_before=first['memory.events'],memory_events_after=last['memory.events']))
    return dict(resource=ref(resource),status=r['status'],reason=r['result']['reason'],
        max_sample_gap_ns=r['result'].get('max_sample_gap_ns'),telemetry=telemetry,
        completed_preparations=load(BASE/name/'result.json')['preparations'] if (BASE/name/'result.json').exists() else None,
        observation='Bounded CPU preparation with external parent telemetry; no internal supervisor wrappers.',
        limits='Nonreproduction does not establish a fix. Cgroup counters cover the shared cgroup; monitor sample gaps are not supervisor heartbeat gaps.')


def run():
    frozen,sessions,records,missing,failures=collect();analysis=load(ANALYSIS)
    completed={r['result']['path'] for s in sessions for r in s['records']}
    partial=[]
    for name in sorted(set(records)-completed):
        r=load(ROOT/name)
        partial.append(dict(response=ref(ROOT/name),certified=r['certified'],model_sha256=r['model_sha256'],
                            physical=r['physical'],lane=r['lane'],tier=r['tier'],
                            completed_delivery_or_teardown=False))
    blocks=[]
    for index in range(frozen['blocks']):
        name=f'confirmation-b{index:02d}';receipt=BASE/'resources'/(name+'.resource.json')
        if index in load(BASE/'confirmation-stop-v1.json')['unattempted_blocks']:
            blocks.append(dict(block=index,status='unattempted',reason='operational-stop',sessions=0,cpu_ns=0,gpu_ns=0))
            continue
        r=load(receipt);s=load(BASE/'resources'/(name+'.settlement.json'));folder=BASE/name
        rows=[x for x in sessions if x['block']==index]
        before=load(folder/'manifest.json').get('environment') if (folder/'manifest.json').exists() else None
        after=load(folder/'result.json').get('environment') if (folder/'result.json').exists() else None
        blocks.append(dict(block=index,status=s['status'],reason=r['result']['reason'],
            sessions=len(rows),active_ns=r['active_elapsed_ns'],cpu_ns=s['cpu_ns'],gpu_ns=s['gpu_ns'],
            max_sample_gap_ns=r['result'].get('max_sample_gap_ns'),
            peak_rss_bytes=r['result'].get('peak_rss_bytes'),resource=ref(receipt),
            environment_before=before,environment_after=after))
    costs=[]
    for row in analysis['rows']:
        if 'summaries' not in row:continue
        for lane,summary in row['summaries'].items():
            total=summary['aggregate_session_ns'];parts=summary['aggregate_cost_ns']
            costs.append(dict(family=row['family'],tier=row['tier'],lane=lane,
                complete_ns=total,parts_ns=parts,shares={k:v/total for k,v in parts.items()},
                hypothetical_remove_iteration_gain=total/(total-parts.get('solver/iteration',0)),
                hypothetical_remove_checker_gain=total/(total-parts.get('solver/checker',0))))
    require(len(completed)==analysis['solves'] and len(sessions)==analysis['sessions'],'diagnosis coverage')
    value=dict(schema_version=1,status=analysis['status'],analysis=ref(ANALYSIS),freeze=ref(BASE/'confirmation-freeze.json'),
        reliability=ref(BASE/'reliability-v1.json'),blocks=blocks,complete_sessions=len(sessions),
        complete_session_responses=len(completed),all_retained_responses=len(records),partial_responses=partial,
        missing_cells=missing,failed_blocks=[r['block'] for r in failures],
        unattempted_blocks=load(BASE/'confirmation-stop-v1.json')['unattempted_blocks'],
        resource_reasons=dict(Counter(r['reason'] for r in blocks)),costs=costs,
        postfailure_cpu_probe=postfailure_probe(),
        limitations=[
            'All frozen blocks and available pairs remain visible. Missingness may be informative; incomplete coverage suppresses every scoped confirmation pass.',
            'Complete-session host clocks form nonoverlapping partitions. GPU events are nested, not additive or isolated tensor throughput.',
            'Removing an entire host phase is a zero-replacement-cost hypothetical bound, not a measured or attainable optimization.',
            'Coarse NVML snapshots bracket each block, not individual sessions; associations do not identify a cause.',
            'Partial response bytes do not prove original delivery durability, EOF or complete-session latency.',
            'The unchanged supervisor enforces its deadline; a heartbeat failure does not itself identify scheduler, I/O or numerical causality.'],
        next_implications=[
            'Resolve and admit process/supervisor availability before a production or further independent confirmation claim.',
            'Use the full measured cost partition to prioritize exact checker and model-preparation work; retain original-model authority.',
            'Evaluate representative application streams and reuse lengths before a default or workload-value claim.'])
    put(TARGET,value);print({k:value[k] for k in ('status','complete_sessions','all_retained_responses','failed_blocks')},flush=True)


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();run()
