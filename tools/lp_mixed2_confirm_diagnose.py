"""Retain observer/sampling evidence without attributing historical failed instants."""
import argparse
import ast
from lp_mixed2_confirm_common import BASE, ROOT, load, put, ref, require


def admission():
    old=(ROOT/'tools/lp_cpu_admission.py').read_text()
    new=(ROOT/'tools/lp_confirmation_supervisor.py').read_text()
    functions=lambda s:{n.name:ast.get_source_segment(s,n) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
    a,b=functions(old),functions(new)
    unchanged=[k for k in a if k not in ('run','coordinator')]
    require(all(a[k]==b[k] for k in unchanged),'unintended coordinator/resource change')
    class TimingMetadata(ast.NodeTransformer):
        def visit_Call(self,node):
            self.generic_visit(node)
            if isinstance(node.func,ast.Name) and node.func.id=='dict':
                node.keywords=[k for k in node.keywords if k.arg!='max_sample_work_ns']
            return node
        def visit_Assign(self,node):
            target=node.targets[0]
            if isinstance(target,ast.Name) and target.id=='sample_work':return None
            if isinstance(target,ast.Subscript) and isinstance(target.slice,ast.Constant) and target.slice.value=='max_sample_work_ns':return None
            return self.generic_visit(node)
        def visit_If(self,node):
            if isinstance(node.test,ast.Compare) and isinstance(node.test.left,ast.Name) and node.test.left.id=='sample_work':return None
            return self.generic_visit(node)
        def visit_Expr(self,node):
            call=node.value
            if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=='send' and len(call.args)==2:
                value=call.args[1]
                if isinstance(value,ast.Call) and any(k.arg=='event' and isinstance(k.value,ast.Constant) and k.value.value=='heartbeat' for k in value.keywords):return None
            return self.generic_visit(node)
    normalized=lambda source:ast.dump(TimingMetadata().visit(ast.parse(source)),include_attributes=False)
    require(normalized(a['coordinator'])==normalized(b['coordinator']),'coordinator changed beyond notification and added duration guard')
    contracts=BASE/'resources/supervisor-contracts-v3.settlement.json'
    require(load(contracts)['status']=='passed','supervisor contracts')
    log=(BASE/'resources/supervisor-contracts-v3.resource.json.log').read_text()
    require('Ran 36 tests' in log and '\nOK\n' in log,'contract coverage')
    probe=load(BASE/'guardian-probe-v1/result.json')
    require([r['status'] for r in probe['rows']]==['refused','passed'],'controlled reproduction')
    failure=load(BASE/'resources/native-v1.resource.json')
    native=load(BASE/'resources/native-v5.resource.json')
    require(native['status']=='passed','fresh native admission')
    put(BASE/'supervisor-admission-v1.json',dict(status='passed',original_source=ref(ROOT/'tools/lp_cpu_admission.py'),
        corrected_source=ref(ROOT/'tools/lp_confirmation_supervisor.py'),unchanged_functions=unchanged,
        contracts=ref(contracts),contract_count=36,probe=ref(BASE/'guardian-probe-v1/result.json'),
        notification_boundary=ref(BASE/'boundary-probe-v1/result.json'),coordinator_normalized_ast_exact=True,
        probe_source_scope='development version; final source also covered by delayed-guardian contract',
        native_failures=[ref(BASE/'resources'/f'native-v{i}.resource.json') for i in (1,2,3)],
        native=ref(BASE/'resources/native-v5.resource.json'),
        instrumented_native=ref(BASE/'resources/native-v4.resource.json'),
        native_failure_observation=failure['guardian_observation'],native_observation=native['guardian_observation'],
        native_placement=ref(ROOT/'tools/lp_mixed2_confirm_native_place.py'),
        native_rust_placement=ref(ROOT/'tools/lp_mixed2_confirm_cargo.py'),
        sampling_diagnosis=ref(BASE/'resources/native-sampling-diagnosis-v1.resource.json'),
        allocation_extension=ref(BASE/'native-allocation-extension-v1.json'),
        sample_limit_ns=100000000,historical_cause_established=False,production_availability_established=False,
        findings=['Old guardian checks freshness before receiving valid queued samples.',
          'Corrected guardian drains and validates sample timestamps; stale queued traffic never renews freshness.',
          'Controlled 180 ms observer delay reproduces the old refusal while the sampler remains healthy.',
          'Three native attempts refused notification freshness. None establishes that actual scan cadence exceeded 100 ms.',
          'Controlled valid 60 ms scans reproduce false staleness when their start timestamps are published after scanning.',
          'Sample-start notification removes that ambiguity and an added duration check also covers the terminal scan.',
          'An instrumented three-worker experiment-library diagnostic completed all 72 tests; its timing does not prove a historical cause.',
          'Native acceptance uses three CPUs for Rust and lower-priority workers with four CPUs retained for nested Python resource tests.',
          'Scientific sessions retain the admitted three-worker/fourth-control-CPU placement.']))


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
            peak_rss_bytes=r['result'].get('peak_rss_bytes'),observation=r['guardian_observation'],resource=ref(p),
            environment_start=load(folder/'manifest.json')['environment'] if (folder/'manifest.json').exists() else None,
            environment_end=load(folder/'result.json')['environment'] if (folder/'result.json').exists() else None))
    put(ROOT/'docs/benchmarks/data/mixed2-confirm-diagnosis-v1.json',dict(status='recorded',blocks=rows,
        admission=ref(BASE/'supervisor-admission-v1.json'),historical_cause_established=False,
        max_sample_gap_ns=max((r['sample_gap_ns'] or 0) for r in rows),
        max_sample_work_ns=max((r['sample_work_ns'] or 0) for r in rows),
        max_guardian_gap_ns=max(r['observation']['max_loop_gap_ns'] for r in rows),
        max_delivery_lag_ns=max(r['observation']['max_delivery_lag_ns'] for r in rows),
        all_retained_responses=sum(r['responses'] for r in rows),
        limitations=['Shared host and shared device; successful cohort does not prove universal availability.',
                    'Coarse environment associations are descriptive, not causal and never exclude blocks.']))


def post():
    rows=[]
    for name in ('hash-whole-v1','hash-streaming-v1','cpu-library-observation-v1','cpu-library-observation-v2'):
        prefix=BASE/'resources'/name
        s=load(str(prefix)+'.settlement.json');r=load(str(prefix)+'.resource.json')
        capture=ROOT/(str(prefix.relative_to(ROOT))+'.resource.json.failure-capture.json')
        stack=ROOT/(str(prefix.relative_to(ROOT))+'.resource.json.failure-stack.txt')
        row=dict(name=name,status=s['status'],reason=r['result']['reason'],settlement=ref(str(prefix)+'.settlement.json'),
            resource=ref(str(prefix)+'.resource.json'),elapsed_ns=r['active_elapsed_ns'],
            peak_rss_bytes=r['result'].get('peak_rss_bytes'),sample_gap_ns=r['result'].get('max_sample_gap_ns'),
            sample_work_ns=r['result'].get('max_sample_work_ns'),guardian_observation=r['guardian_observation'],
            capture=load(capture) if capture.exists() else None,stack=stack.read_text() if stack.exists() else None)
        if row['capture'] and 'after_capture' in row['capture']:
            before=row['capture'];after=before['after_capture']
            row['capture_observation_span_ns']=after['time_ns']-before['time_ns']
            row['scheduler_counters_unchanged']=before['fields']['schedstat']==after['fields']['schedstat']
        rows.append(row)
    for version in ('v1','v2'):
        require(load(BASE/f'failure-trace-admission-{version}/result.json')['status']=='passed','post-refusal capture admission')
    put(ROOT/'docs/benchmarks/data/mixed2-confirm-postdiagnosis-v1.json',dict(status='recorded',rows=rows,
        gpu_seconds=0,scientific_retry=False,post_refusal_capture=True,per_sample_trace=False,
        findings=['Both fixed hashing probes validate all 20 original model hashes for 12 rounds.',
          'A CPU-only experiment workload reproduces the progress refusal; GPU execution is not a necessary trigger.',
          'Whole-file versus streaming probes are fixed-order diagnostics, not randomized performance confirmation.',
          'Post-refusal observations occur after the decision and may observe a progressing or descheduled coordinator.',
          'Missing signal-stack output is retained as missing; it does not identify a kernel or scheduler cause.'],
        historical_cause_established=False,production_availability_established=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['admission','final','post']);globals()[p.parse_args().action]()
