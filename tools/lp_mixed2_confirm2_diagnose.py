"""Bind the prospective resource-policy tradeoff and retain every observed delay."""
import argparse
from lp_mixed2_confirm2_common import BASE, ROOT, load, put, ref, require


def admission():
    old=(ROOT/'tools/lp_confirmation_supervisor.py').read_text()
    source=ROOT/'tools/lp_confirmation2_supervisor.py'; new=source.read_text()
    # Invert the entire deliberately small policy/metadata diff. Anything else,
    # including cleanup, death detection, wall budgets or RSS checks, refuses.
    replacements=[
        ('SPEC-0041 supervision: finite prospective limit and explicit 100 ms observations.',
         'SPEC-0040 isolated supervision: distinguish sampling from guardian observation.'),
        ('ADVISORY_GAP_NS = 100_000_000\n',''),
        ('peak_threads=0, peak_sum_process_hwm_bytes=0,','peak_threads=0,'),
        ("                  timing_exceedances=[], advisory_gap_ns=ADVISORY_GAP_NS, hard_gap_ns=request['max_gap_ns'],\n",''),
        ("            if gap > ADVISORY_GAP_NS:\n                result['timing_exceedances'].append(['sample_start_gap',last,gap])\n",''),
        ("            result['peak_sum_process_hwm_bytes'] = max(result['peak_sum_process_hwm_bytes'],observation['sum_process_hwm_bytes'])\n",''),
        ("            if sample_work > ADVISORY_GAP_NS:\n                result['timing_exceedances'].append(['sample_work',now,sample_work])\n",''),
        ('        self.advisory_exceedances = []\n',''),
        ('            if gap > ADVISORY_GAP_NS:self.advisory_exceedances.append([self.last,sent,gap])\n',''),
        ('recent_samples=self.recent,\n                    advisory_gap_ns=ADVISORY_GAP_NS,advisory_exceedances=self.advisory_exceedances)',
         'recent_samples=self.recent)'),
        ("    if request.get('max_gap_ns') not in (100_000_000,1_000_000_000):\n        raise AdmissionError('unsupported_sampling_policy')\n",''),
        ('cooperative_process_supervision_v4','cooperative_process_supervision_v3'),
        ("    parser.add_argument('--max-gap-ms',type=int,choices=[100,1000],default=100)\n",''),
        ("args['max_gap_ns'] = args.pop('max_gap_ms') * 1_000_000", "args['max_gap_ns'] = 100_000_000")]
    for before,after in replacements:
        require(new.count(before)==1,'policy diff ambiguous or missing: '+repr(before));new=new.replace(before,after)
    require(new==old,'resource enforcement changed beyond declared policy/metadata')
    contracts=BASE/'resources/supervisor-contracts-v1.settlement.json'
    require(load(contracts)['status']=='passed','supervision contracts')
    log=(BASE/'resources/supervisor-contracts-v1.resource.json.log').read_text()
    require('Ran 39 tests' in log and '\nOK\n' in log,'contract coverage')
    observations=[]
    for name in ('phase-trace-boundary-v1','cpu-timing-v1','cpu-timing-v2'):
        prefix=BASE/'resources'/name
        require(load(str(prefix)+'.settlement.json')['status']=='passed','diagnostic failed')
        observations.append(dict(name=name,resource=ref(str(prefix)+'.resource.json'),
            phases=ref(str(prefix)+'.resource.json.phases.json')))
    put(BASE/'supervisor-admission-v2.json',dict(status='passed',source=ref(source),
        previous_source=ref(ROOT/'tools/lp_confirmation_supervisor.py'),
        whole_source_exact_after_declared_policy_metadata_removal=True,
        contracts=ref(contracts),contract_count=39,observations=observations,
        hard_limit_ns=1000000000,advisory_limit_ns=100000000,target_wait_ns=5000000,
        authority='User explicitly permits changing or waiving an inappropriate 100 ms limit.',
        policy='Finite maximum tolerated observation delay; not a numerical tolerance or inferred scheduling guarantee.',
        memory_tradeoff='A longer maximum observation gap can miss longer transient RSS peaks. Sampled RSS is not a hard enclosure at either bound. Keep the 16 GiB observed stop, per-process high-water observations, fixed model/buffer bounds and independent cleanup/death/deadline checks.',
        history_regraded=False,hard_memory_enclosure=False,historical_cause_established=False,
        production_availability_established=False,
        findings=[
            'An injected 150 ms scan is admitted under the prospective one-second policy and recorded as a real delay.',
            'Both fixed CPU experiment-library probes pass all 72 tests; neither reproduces an actual interval above 100 ms.',
            'The second probe has a 97.715046 ms sample-start gap and an 81.685364 ms scan with 6.488537 ms process CPU.',
            'Shared cgroup throttling counters increase by ten events / 4.516513 seconds during that probe; these aggregate associations do not identify the cause of a particular interval.',
            'A one-second bound leaves operational margin while preserving a finite, fault-tested refusal. It is a policy choice, not a guarantee derived from two probes.',
            'All subsequent scientific jobs omit the diagnostic phase tracer. Every 100 ms exceedance and all elapsed costs remain visible.',
            'Require fresh native acceptance and three full-size operational pilots before freezing the scientific cohort.'
        ],references=[
            'docs/decisions/ADR-0044-tensor-cost-continuation.md',
            'https://www.man7.org/linux/man-pages/man2/select.2.html',
            'https://www.kernel.org/doc/html/v5.19/admin-guide/cgroup-v2.html']))
    print('39 contracts and exact policy-only supervisor diff admitted',flush=True)


def final():
    rows=[]
    for i in range(32):
        p=BASE/'resources'/f'confirmation-b{i:02d}.resource.json';r=load(p)
        s=load(BASE/'resources'/f'confirmation-b{i:02d}.settlement.json')
        folder=BASE/f'confirmation-b{i:02d}';sessions=list(folder.glob('*.session.json'))
        responses=list(folder.glob('*-r[0-9][0-9].json'))
        rows.append(dict(block=i,status=s['status'],reason=r['result']['reason'],sessions=len(sessions),responses=len(responses),
            cpu_ns=s['cpu_ns'],gpu_ns=s['gpu_ns'],sample_gap_ns=r['result'].get('max_sample_gap_ns'),
            sample_work_ns=r['result'].get('max_sample_work_ns'),
            peak_rss_bytes=r['result'].get('peak_rss_bytes'),
            peak_sum_process_hwm_bytes=r['result'].get('peak_sum_process_hwm_bytes'),
            timing_exceedances=r['result'].get('timing_exceedances',[]),
            observation=r['guardian_observation'],resource=ref(p),
            environment_start=load(folder/'manifest.json')['environment'] if (folder/'manifest.json').exists() else None,
            environment_end=load(folder/'result.json')['environment'] if (folder/'result.json').exists() else None))
    put(ROOT/'docs/benchmarks/data/mixed2-confirm2-diagnosis-v1.json',dict(status='recorded',blocks=rows,
        admission=ref(BASE/'supervisor-admission-v2.json'),historical_cause_established=False,
        hard_limit_ns=1000000000,advisory_limit_ns=100000000,
        max_sample_gap_ns=max((r['sample_gap_ns'] or 0) for r in rows),
        max_sample_work_ns=max((r['sample_work_ns'] or 0) for r in rows),
        max_guardian_gap_ns=max(r['observation']['max_loop_gap_ns'] for r in rows),
        max_delivery_lag_ns=max(r['observation']['max_delivery_lag_ns'] for r in rows),
        all_retained_responses=sum(r['responses'] for r in rows),
        limitations=['Shared host and shared device; success does not prove universal availability.',
                    'A one-second maximum observation delay does not provide continuous resource enclosure.',
                    'Coarse environment associations are descriptive, not causal; no block is excluded.']))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['admission','final']);globals()[p.parse_args().action]()
