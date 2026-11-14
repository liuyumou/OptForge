"""MIXED2 durable findings, portable replay, exact history and CPU closure."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from lp_mixed2_common import ROOT, BASE, BASELINE, BINARY, CPU_CAPS, NS, load, put, ref, require
from lp_mixed2_budget import accounting, admission_open
from lp_mixed2_cost import OUTPUT, analyze, DATA, TARGETS

ALLOWED={'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md','CHANGELOG.md','state/known-failures.md'}
ACCEPTANCE=DATA/'mixed2-acceptance-v1.json'
ACCOUNTING=DATA/'mixed2-accounting-v1.json'


def publish(path,value):
    if path.exists():
        require(load(path)=={'status':'pending'},'refuse completed receipt overwrite')
        archive=BASE/'draft-receipts'/path.name;archive.parent.mkdir(parents=True,exist_ok=True)
        with archive.open('xb') as f:f.write(path.read_bytes())
        from lp_cpu_admission import atomic_json
        atomic_json(path,value)
    else:put(path,value)


def report():
    result=load(OUTPUT);cold,prepared=result['routes']
    lines=['# GPUP-MIXED2 CPU contract and complete-cost admission','',
        'MIXED2 completes its bounded CPU admission with **device work deferred**. The',
        'FP32-matrix/FP64-compute reference and local error/recovery contract are implemented',
        'under [SPEC-0036](../specifications/SPEC-0036-mixed2.md) and',
        '[ADR-0069](../decisions/ADR-0069-mixed2.md). There is no new GPU solver, certified',
        'mixed solve, public preset or measured mixed-precision speedup.','',
        '## Complete-cost decision','',
        'The [machine record](data/mixed2-cost-v1.json) retains 768 selected native cells',
        'and 1536 solves: all twelve families and 32 blocks of strict DELIVERY4 cold',
        'and DELIVERY3 prepared candidate controls. The 1408 retained certificates and',
        '128 intentional refusals are historical native outcomes, not MIXED2 results.',
        'All 145 frozen scenarios per lifecycle remain visible. No scientific cell was rerun.',
        'The original retention decisions are unchanged.','',
        '| Lifecycle | Ideal removal of every GPU event | Hypothetical 2x every GPU event | Disposition |',
        '| --- | --- | --- | --- |']
    for route in result['routes']:
        ideal=route['scenarios'][0]['benefit'];two=next(s['benefit'] for s in route['scenarios'] if s['scenario']['id']=='f1.0-s2.0-w1.0-o0.0')
        lines.append(f"| {route['lifecycle']} | {ideal['median']:.6f}x [{ideal['lower']:.6f}, {ideal['upper']:.6f}] | {two['median']:.6f}x [{two['lower']:.6f}, {two['upper']:.6f}] | {'Insufficient upper bound' if route['lifecycle']=='cold' else 'Attribution and added costs unknown'} |")
    lines += ['',
        'Ratios are medians of block geometric ratios for dense128/256/512. Brackets',
        'are simultaneous binomial median intervals for **assumed transformed retained',
        'costs**, not uncertainty intervals for a measured new candidate. The 1.10x',
        'benefit, eleven family guards per lifecycle and original 1e-9 coverage rules',
        'were fixed before this analysis; all 24 metrics use ranks 7 and 26 of 32.',
        'Block independence and shared-device limitations from the original studies remain.',
        'Each solve is transformed before taking the three-solve prepared session median.',
        'All GPU event time includes non-matrix work, so these are optimistic upper cases.',
        '',
        'Even an ideal arithmetic replacement cannot justify cold execution under the',
        'declared benefit rule. Prepared execution remains plausible only conditionally:',
        'the actual matrix fraction, achievable speed, work amplification and additional',
        'representation/transfer/guard/correction/fallback/checking costs are unknown.',
        'No assumption of zero overhead establishes their safety. A separately funded',
        'matrix-attribution and overhead pilot is required before a solver/device cohort.',
        '',
        '| Prepared family | Median complete delivery (ms) | Median GPU events (ms) | Median extra-cost allowance at 2x events (ms) |',
        '| --- | ---: | ---: | ---: |']
    for row in prepared['summary']:
        if row['family'] in TARGETS:
            lines.append(f"| {row['family']} | {row['complete_median_ms']:.3f} | {row['event_median_ms']:.3f} | {row['extra_allowance_2x_median_ms']:.3f} |")
    lines += ['',
        'Allowances are computed per solve as T/1.10 - (T - G + G/2), then summarized;',
        'they are illustrative individual-family thresholds, not replacements for the',
        'frozen joint target and family guards. Marginal phase medians are not additive.',
        'Prepared setup/teardown is retained separately for every family in the machine',
        'summary; it cannot be silently amortized into a cold-latency claim.',
        '',
        'The retained DELIVERY4 diagnosis remains relevant: dense512 warm host',
        'preparation 110.9 to 53.2 ms and hashing 61.3 to 9.8 ms; profiled context',
        'setup about 222 ms (113 driver initialization, 107 context creation), owned',
        'destruction about 74 ms including 69 ms context destruction. Another 37–38 ms',
        'outside Rust main remains unassigned. These are prior observations from',
        '[DELIVERY4](lp-delivery4.md), not new MIXED2 measurements.',
        '',
        '## Numerical implementation and limits','',
        'The [architecture note](../architecture/lp-mixed2.md) derives the local product',
        'enclosure and explains the isolated CSR representation, FP64 FMA, shared',
        'transpose coefficients, identity scaling and independent original-model authority.',
        'The CPU reference refuses invalid shapes, nonfinite inputs, FP32 range loss',
        'and nonfinite arithmetic/enclosures. It preserves original coefficient bits.',
        'The window reference restores opaque checkpoint bytes, charges attempted work,',
        'requires positive work and primal/dual progress, and promotes permanently to native.',
        '',
        'Eleven Rust tests and ten Python contracts pass. The independent exact-rational',
        'oracle checks 1049 requests and 5121 outputs, separating representation and',
        'FMA rounding errors across generic significands, cancellation, subnormals,',
        'extreme exponents and both directions. Final source-bound oracle evidence is in',
        '[CPU acceptance](data/mixed2-cpu-v2.json). A development review corrected',
        'physical accounting for refused calls after native promotion and bounded sparse',
        'dimensions before transpose-output allocation; development versions and',
        'the earlier passing oracle receipt remain archived. No failed numerical job occurred.',
        '',
        'These tests do not establish a useful mixed solver window, a complete executor',
        'checkpoint, global trajectory error, convergence or an original-model certificate.',
        'The conservative progress rule can promote if one residual is already zero.',
        'There is no GPU subnormal/FTZ admission or sanitizer reuse claim. The prior',
        '[refinement](lp-refinement-gpup-refine.md) and',
        '[resident quantization](lp-quant-resident-gpup7r.md) failures remain design',
        'inputs: zero work and zero useful mixed windows cannot qualify a future solver.',
        '',
        '## Reproduction, acceptance and resources','',
        '`python3 tools/lp_mixed2_cost.py --verify` reproduces every selected sample and',
        'scenario from committed portable archives. A clean temporary copy containing',
        'only tools, the specification and bound input/output records verifies without',
        'the original artifacts tree, CUDA or the reference executable. The isolated',
        'Rust package builds without a toolkit; `tools/check_mixed2_cpu.sh` runs its',
        'CPU gate and rational oracle with a fresh exclusive output receipt.',
        '',
        'Full native gate, exact history and final cleanup: [acceptance](data/mixed2-acceptance-v1.json).',
        'Separate phase charges, all source versions and raw supervisor receipts:',
        '[accounting](data/mixed2-accounting-v1.json). The independent ceiling is 16000',
        'CPU / zero GPU seconds, four slots and 16 GiB sampled RSS. It includes 512',
        'preparation and 128 closing-administration CPU seconds; no historical transfers.',
        'The unchanged supervisor is used for every numerical/analysis/acceptance job.',
        '',
        'The next ready task is GPUP-8-DISPOSITION, a review requiring a separate request.',
        'Readiness is not execution or funding. GPUP-8 remains incomplete, TENSOR2',
        'conditional and GPUP-9 gated. No follow-on allocation, public default, push or',
        'publication follows; the delivery is committed locally.']
    if ACCEPTANCE.exists() and load(ACCEPTANCE).get('status')=='passed':
        a=load(ACCEPTANCE)
        lines += ['',f"Final software acceptance: {a['total_rust_tests']} repository Rust tests, {a['python_tests']} Python tests, 11 isolated Rust tests, full native/replay/artifact/docs/smoke checks. {a['historical_files']} historical files remain exact; prior handoff/changelog/known-limitations text is preserved."]
    if ACCOUNTING.exists() and load(ACCOUNTING).get('status')=='closed':
        a=load(ACCOUNTING)
        lines += ['',f"Allocation closed at **{a['cpu_seconds']:.9f} / 16000 CPU seconds**, **zero GPU**, including closing administration. Failed jobs: {a['failed_jobs']}; all cleanup empty."]
    (ROOT/'docs/benchmarks/lp-mixed2.md').write_text('\n'.join(lines)+'\n')


def package():
    # Immutable final binary and portable CPU evidence; no new solve.
    binary_ref=ref(BINARY);dest=BASE/'binaries'/binary_ref['sha256'];dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as stream:stream.write(BINARY.read_bytes())
    oracle=load(BASE/'oracle-v3.json');require(oracle['binary']==binary_ref,'final binary mismatch')
    put(DATA/'mixed2-cpu-v2.json',dict(oracle=oracle,prior_oracles=[load(BASE/'oracle-v1.json'),load(BASE/'oracle-v2.json')],binary_archive=ref(dest),
        isolated=ref(BASE/'resources/final-cpu-v2.settlement.json'),rust_tests=11,python_tests=10,
        sources={str(p.relative_to(ROOT)):ref(p)['sha256'] for p in sorted((ROOT/'research/lp-mixed2/src').glob('*.rs'))}))
    for path in (ACCEPTANCE,ACCOUNTING):
        if not path.exists():put(path,dict(status='pending'))
        else:require(load(path)=={'status':'pending'},'package after finalized receipt')
    report()


def history():
    preserved=[]
    for item in subprocess.check_output(['git','ls-tree','-rz','--full-tree',BASELINE],cwd=ROOT).split(b'\0'):
        if not item:continue
        metadata,name=item.split(b'\t',1);mode,kind,blob=metadata.split();name=name.decode()
        if name in ALLOWED:continue
        require(kind==b'blob','historical gitlink')
        raw=os.readlink(ROOT/name).encode() if mode==b'120000' else (ROOT/name).read_bytes()
        digest=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(digest==blob.decode(),'historical source changed: '+name);preserved.append(dict(path=name,git_blob=digest))
    for name in ('AGENTS.md','state/active-task.md','CHANGELOG.md','state/known-failures.md'):
        old=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT).decode().split('\n\n',1)[1]
        require((ROOT/name).read_text().endswith(old),'older text modified: '+name)
    def tasks(text):
        starts=list(re.finditer(r'^  - id: (\S+)\s*$',text,re.M))
        result={m.group(1):text[m.start():starts[i+1].start() if i+1<len(starts) else len(text)] for i,m in enumerate(starts)}
        require(len(result)==len(starts),'duplicate task');return result
    old=tasks(subprocess.check_output(['git','show',BASELINE+':state/backlog.yaml'],cwd=ROOT).decode());now=tasks((ROOT/'state/backlog.yaml').read_text())
    require(set(old)==set(now),'backlog roster changed')
    for name in old:
        if name=='GPUP-MIXED2':continue
        if name=='GPUP-8-DISPOSITION':require(now[name]==old[name].replace('status: planned','status: ready'),'disposition changed beyond readiness')
        else:require(old[name]==now[name],'other task changed: '+name)
    require('    status: complete\n' in now['GPUP-MIXED2'],'MIXED2 admission not complete')
    require('next_ready_task: GPUP-8-DISPOSITION\n' in (ROOT/'state/backlog.yaml').read_text(),'next readiness')
    parents={name:re.search(r'^    depends_on: \[([^]\n]*)\]',text,re.M).group(1).split(',') for name,text in now.items()}
    visited=set()
    def visit(name,active):
        require(name in now and name not in active,'dependency cycle or missing task')
        if name in visited:return
        for p in parents[name]:
            if p.strip():visit(p.strip(),active|{name})
        visited.add(name)
    for name in now:visit(name,set())
    for p in parents['GPUP-8-DISPOSITION']:require('    status: complete\n' in now[p.strip()],'next dependency incomplete')
    return dict(baseline=BASELINE,preserved=preserved,allowed=sorted(ALLOWED),prior_text_exact=True,other_backlog_tasks_exact_except_disposition_readiness=True,dependency_tasks=len(now))


def verify():
    require(analyze()==load(OUTPUT),'cost record mismatch')
    h=history();native=load(BASE/'resources/native-gate-v1.settlement.json');require(native['status']=='passed','native gate incomplete')
    isolated=load(BASE/'resources/final-cpu-v2.settlement.json');require(isolated['status']=='passed','isolated gate incomplete')
    log=(BASE/'resources/native-gate-v1.resource.json.log').read_text()
    require('committed run records re-executed and verified: passed' in log,'replay missing')
    counts=re.findall(r'Ran (\d+) tests',log);require(counts and '688' in counts,'Python coverage')
    rust=sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed;',log));require(rust==638,'Rust coverage')
    with tempfile.TemporaryDirectory(prefix='gpup-mixed2-portable-') as directory:
        dest=Path(directory);(dest/'tools').mkdir()
        for p in (ROOT/'tools').glob('*.py'):shutil.copyfile(p,dest/'tools'/p.name)
        record=load(OUTPUT)
        for name in [r['path'] for r in record['inputs']]+['docs/specifications/SPEC-0036-mixed2.md',str(OUTPUT.relative_to(ROOT))]:
            p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
        subprocess.run([sys.executable,'-B','tools/lp_mixed2_cost.py','--verify'],cwd=dest,check=True,capture_output=True,text=True)
        require(not (dest/'artifacts').exists(),'portable replay used artifacts')
    for path in (BASE/'resources').glob('*.settlement.json'):
        s=load(path);require(not s['overrun'],'resource overrun')
        if s['resource']:
            r=load(ROOT/s['resource']['path']);require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup incomplete')
    for command in ([sys.executable,'tools/validate_artifacts.py'],[sys.executable,'tools/build_docs.py'],['git','diff','--check']):subprocess.run(command,cwd=ROOT,check=True)
    put(DATA/'mixed2-history-v1.json',h)
    publish(ACCEPTANCE,dict(status='passed',analysis=ref(OUTPUT),cpu=ref(DATA/'mixed2-cpu-v2.json'),history=ref(DATA/'mixed2-history-v1.json'),
        native=ref(BASE/'resources/native-gate-v1.settlement.json'),total_rust_tests=rust,python_tests=688,isolated_rust_tests=11,
        historical_files=len(h['preserved']),portable_replay=True,all_145_scenarios_each_lifecycle_reproduced=True,
        historical_decisions_unchanged=True,cleanup_empty=True,gpu_seconds=0))
    report();print(dict(status='passed',historical_files=len(h['preserved']),rust=rust,python=688),flush=True)


def close():
    admission_open();require(load(ACCEPTANCE)['status']=='passed','acceptance required')
    require(load(BASE/'resources/final-acceptance-v1.settlement.json')['status']=='passed','final acceptance settlement required')
    cpu,gpu=accounting();cpu['cleanup']+=128*NS
    require(sum(cpu.values())<=16000*NS and all(cpu[k]<=v*NS for k,v in CPU_CAPS.items()) and not gpu,'allocation exceeded')
    receipts=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(path);require(not s['overrun'],'overrun')
        stem=str(path).replace('.settlement.json','');r=load(stem+'.resource.json')
        require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup incomplete')
        receipts.append(dict(binding=ref(path),settlement=s,reservation=load(stem+'.reservation.json'),resource=r,log=Path(stem+'.resource.json.log').read_text()))
    sources={str(p.relative_to(BASE)):p.read_text() for p in sorted((BASE/'sources').rglob('*')) if p.is_file()}
    sources.update({p.name:p.read_text() for p in BASE.iterdir() if p.suffix in ('.py','.sh')})
    value=dict(status='closed',cpu_caps_seconds=CPU_CAPS,cpu_ns=cpu,cpu_seconds=sum(cpu.values())/NS,gpu_seconds=0,
        closing_administration_cpu_seconds=128,failed_jobs=sum(r['settlement']['status']!='passed' for r in receipts),
        receipts=receipts,development_sources=sources,historical_transfers=0,cleanup_empty=True)
    publish(ACCOUNTING,value);put(BASE/'CLOSED.json',dict(accounting=ref(ACCOUNTING)))
    report();print(dict(status='closed',cpu_seconds=value['cpu_seconds'],gpu_seconds=0),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['package','verify','close','report']);a=p.parse_args();globals()[a.action]()
