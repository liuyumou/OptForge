"""Final findings, exact preservation, portable evidence and independent closure."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from lp_mixed2_fp4_common import ROOT,BASE,BINARY,BASELINE,CPU_CAPS,GPU_CAPS,NS,load,put,ref,require
from lp_mixed2_fp4_budget import accounting,admission_open
from lp_mixed2_fp4_analysis import ANALYSIS,ARCHIVE,archive_files,verify as replay
DATA=ROOT/'docs/benchmarks/data'
ACCEPTANCE=DATA/'mixed2-fp4-acceptance-v1.json'
ACCOUNTING=DATA/'mixed2-fp4-accounting-v1.json'
ALLOWED={'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md'}

def report():
    a=load(ANALYSIS);d=load(DATA/'mixed2-fp4-diagnosis-v1.json')
    supported=[r['family'] for r in a['rows'] if r['tier']=='certified-1e-9' and r['speedup']['lower']>1]
    regressed=[r['family'] for r in a['rows'] if r['tier']=='certified-1e-9' and r['speedup']['upper']<1]
    lines=['# MIXED2 FP4 tensor implementation and larger-scale evaluation','',
        'Implemented the tensor-core approach in an isolated research executor under',
        '[SPEC-0038](../specifications/SPEC-0038-mixed2-fp4.md) and',
        '[ADR-0071](../decisions/ADR-0071-mixed2-fp4.md). FP4 computes matrix increments;',
        'persistent state, original-matrix references, recovery and final authority',
        'remain high precision. Public solver defaults are unchanged.','',
        f"Available strict pairs with descriptive intervals above parity: {', '.join(supported) or 'none'}.",
        f"Available strict pairs with descriptive intervals below parity: {', '.join(regressed) or 'none'}.",
        'Retain native for small workloads; this does not support a broad FP4 replacement.','',
        f"The planned 32-block confirmation is **incomplete**. It retains **{a['sessions']} complete sessions / {a['solves']} retained solve responses**:",
        f"**{a['certificates']} original-model certificates and {a['refusals']} intentional refusals**.",
        f"There are {a['completed_session_solves']} solves in completed sessions and {a['partial_session_responses']} retained response files from an interrupted session whose teardown did not complete.",
        'Block 26 of 32 was stopped for a lost coordinator heartbeat. The 25 prior and',
        'six untouched later blocks completed; the failed block was never retried.',
        'Its eight completed sessions and six further retained response files remain visible;',
        'The six response files are complete and independently rechecked, but there is',
        'no receipt proving their original delivery fsync/EOF boundary completed. The',
        'raw machine ledger uses the term durable for retained files; it must not be',
        'interpreted as a completed original delivery-time measurement.',
        '23 later sessions in that failed block were not executed. The full frozen',
        'coverage requirement fails, so no confirmation, retention or adoption pass is claimed.',
        'The study includes sixteen families, both 1e-7 and 1e-9 tiers, and dense1024/2048',
        'full solves. Dense2048 has 16 times as many coefficients as dense512.',
        'The coupled large cases add a fixed 0.5 cyclic coupling and require longer',
        'trajectories. Known primal/dual construction forms these models but never',
        'initializes the solver. These constructed workloads do not establish',
        'performance on arbitrary production LPs.','',
        '## Complete prepared performance','',
        'Table entries use every available complete pair (31 or 32 per family); each session has three',
        'solves at each tier. Native uses 32-update windows; FP4 x2 uses 16-update',
        'original-reference windows. Both use fixed maximum-200 audits, cached initial',
        'observations and the same improved independent checker. Every output is',
        'durable before its complete-time boundary. Setup, preparation, EOF, destruction',
        'and log durability are additionally charged in measured six-solve sessions.',
        'The session bookkeeping JSON is outside the delivered-solution boundary.','',
        '| Family | Tier | Pairs | Native ms | FP4 ms | Descriptive paired speedup [interval] | Saved ms | Native / FP4 updates |',
        '| --- | --- | ---: | ---: | ---: | --- | ---: | --- |']
    for r in a['rows']:
        v=r['speedup'];lines.append(f"| {r['family']} | {r['tier'].replace('certified-','')} | {r['speedup']['n']} | {r['native_ms']:.3f} | {r['fp4_ms']:.3f} | {v['median']:.3f} [{v['lower']:.3f}, {v['upper']:.3f}] | {r['saved_ms']['median']:.3f} | {r['native_work']} / {r['fp4_work']} |")
    lines += ['',
        'Ratios are formed from the two within-session medians in each block, then',
        'summarized across available pairs. Marginal table medians need not divide to the paired',
        'ratio. Exact binomial order-statistic intervals use Bonferroni coverage over',
        '32 family/tier ratios and 32 paired absolute savings (joint nominal >=95% only',
        'under the statistical assumptions). Missingness is not proven independent of',
        'cost. These are descriptive conditional intervals, not a successful frozen',
        'confirmation or a correction for the interrupted block.',
        'They assume independent session-level blocks; the shared GPU and temporal',
        'conditions limit that assumption. Within-session repeats are not independent',
        'samples. Planned order was exactly balanced 16/16; the incomplete block breaks',
        'that balance for some families. No cell, refusal or outlier is silently',
        'discarded and no scientific block is retried. Missing cells, first-16 sensitivity, pair-order',
        'splits and every block value remain in the machine analysis. The provisional',
        '1.10x target is not used to veto diagnostic evidence or claim adoption.','',
        '## GPU work and lifecycle value','',
        '| Strict dense family | Native GPU ms | FP4 GPU ms | Paired GPU speedup | Extra setup+teardown ms | Forecast break-even solves | Measured six-solve session ratio |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in a['rows']:
        if r['tier']=='certified-1e-9' and r['family'].startswith('dense-'):
            lines.append(f"| {r['family']} | {r['native_gpu_ms']:.3f} | {r['fp4_gpu_ms']:.3f} | {r['gpu_speedup']['median']:.3f} | {r['extra_lifecycle_ms']:.3f} | {r['forecast_break_even_solves']} | {r['six_solve_session_speedup']['median']:.3f} |")
    lines += ['',
        'GPU values are enclosing window events, including launches and host gaps,',
        'not isolated tensor instruction throughput. Break-even divides median extra',
        'setup/destruction by median per-solve savings, rounded upward. It is a',
        'constant-cost amortization forecast, not a measured cold-solve result or a',
        'guarantee for long sessions. Repeats reset the same model and initial state;',
        'they do not measure changing right-hand sides or model streams. A useful',
        'production reuse workload is unvalidated. The six-solve ratio is measured and includes both',
        'tiers. Small shapes and short sessions can lose even where dense prepared',
        'arithmetic wins; no universal preset or timing-selected route is selected.','',
        '## Retained diagnosis and optimizations','',
        'The first admitted FP64-reconstruction implementation lost at every measured',
        'shape. Strict dense2048 complete medians were 104.154 ms native, 189.208 ms',
        'x2 and 181.135 ms x4; GPU events were 17.801 / 37.895 / 93.926 ms. X2 needed',
        '232 updates and two assessments while the controls needed 200 and one.',
        'All original development records and failed versions remain preserved.','',
        'FP32 temporary reconstruction with an explicit outward rounding bound cut',
        'tensor cost. FP32 vector proposals retain FP64 residual accounting; outward',
        'FP32 maxima and cooperative warp gathering reduce guard overhead. Original',
        'references and persistent arithmetic remain FP64. Independent row/column',
        'parallelism, exact SHA-256 and bounded magnitude-ordered FastTwoSum improve',
        'both controls while preserving the original checker bits and reduction tree.','',
        'The two-block window study showed x2/16 avoids the extra generic-dense',
        'assessment observed at x2/32. The audit pilot then cached the immutable',
        'initial observation and retained 200-update audits instead of shortening to',
        '32 near convergence. Coupled1024 FP4 fell from about 172 to 80 ms, while',
        'physical work increased from 720 to 800; native received the same changes.',
        'This is a measured check-frequency tradeoff, not a relaxed final tolerance.','',
        '| Strict family / lane | Coarse timers ms | Timers removed ms | Median paired overhead ratio | Four observed ratios |',
        '| --- | ---: | ---: | ---: | --- |']
    for r in d['timing_ablation']['rows']:
        lines.append(f"| {r['family']} / {r['lane']} | {r['timed_ms']:.3f} | {r['minimal_ms']:.3f} | {r['timed_over_minimal']:.3f} | {', '.join(f'{v:.3f}' for v in r['ratios'])} |")
    lines += ['',
        f"The separate timer ablation preserves all {d['timing_ablation']['exact_pairs']} paired numerical transcripts",
        '(endpoints, certificates, audits, checkpoints, recovery and physical work).',
        'Only coarse phase clocks and run-window CUDA events are removed. Actual',
        'stream synchronization, readbacks and deadline clocks remain. Four blocks',
        'give descriptive disturbance evidence; variability prevents assigning every',
        'difference to timers or treating phase spans as exact causal attribution.',
        'The frozen confirmation executable is unchanged by this ablation.','',
        'The two 180-cell product studies retain both directions, both FP4 component',
        'counts and guarded/unguarded ablations. Guard-free products are read-only',
        'diagnostics and never enter a solver. Product events divide 128 launches and',
        'retain host launch gaps; vector preparation, allocation and readback are',
        'separate. All values and source identities are in the diagnostic archive.',
        'An independent exact dyadic oracle checks all 95232 retained FP4 product outputs',
        'against original coefficients and all 47616 native outputs against the original',
        'eight-warp multiply/add tree, including the largest 2048 grids. These component',
        'studies cannot substitute for complete certified solves.','',
        '## Numerical authority and limitations','',
        'Normal E2M1 components exclude subnormal codes 1/9. The admitted unscaled',
        '32-term component dots are exactly representable quarter-integer FP32 sums.',
        'The bounded codec and scale range prevent temporary overflow/underflow;',
        'FP32 reconstruction error, vector residuals, matrix representation error and',
        'FP64 reference/addition errors enter conservative outward local bounds.',
        'Those bounds are local product enclosures, not a global trajectory proof.',
        'Guard/progress failure restores the exact FP64 checkpoint and promotes',
        'x2 to x4 to permanent native; physical work is never rolled back.',
        f"Confirmation recovery counts: `{a['recoveries']}`. All recoveries and refusals remain visible.",
        'Cancellation/deadlines precede certificate authority. The independent CPU',
        'checker uses the original model at the requested tier, never FP4 data.',
        '[NVIDIA PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/) and',
        '[Ogita, Rump and Oishi (2005)](https://www.tuhh.de/ti3/paper/rump/OgRuOi05.pdf)',
        'document the MMA arithmetic interface and error-free addition transformation.',
        'Hardware assumptions remain explicit, tested and specific to this image.','',
        'Build v1 failed on a CUDA helper name (1440 CPU seconds); build v2 failed on',
        'a debug interface signature (960 CPU seconds). Device v1 hit the inherited',
        '128 MiB checker input cap on the 225 MiB dense2048 model (720 CPU / 180 GPU',
        'seconds). The new explicit 384 MiB cap passed CPU admission before CUDA.',
        'These failures, source versions and full charges remain preserved.','',
        'One development all-process racecheck run exited 11 without delivering its',
        'certificate, reporting zero hazards; its full 960 CPU / 240 GPU reservation is',
        'charged. Eight prospectively ordered old/new-image',
        'probes did not reproduce it; its cause remains unassigned. Later admission',
        'scopes instrumentation to the root CUDA executor. The separate checker has',
        'CUDA visibility disabled and independent CPU admission. Four new scoped',
        'passes do not prove the earlier exit fixed. This remains a reliability',
        'limitation and prevents a production-readiness claim.','',
        'A separate CPU product oracle was stopped after a missed coordinator heartbeat',
        'after checking dimensions through 512. Its full 960 CPU-second reservation',
        'is retained. A new cooperative three-CPU validation launcher keeps the same',
        'supervisor and limits; this is CPU acceptance, not a scientific timing retry.',
        'The scheduling cause is unassigned. The same supervisor reason later stopped',
        'scientific block 26, preserving its full 720 CPU / 180 GPU seconds. All',
        'remaining untouched blocks retain the original image, source, settings and',
        'order; the failed block stays incomplete and is never regraded.','',
        'Further useful work is representative sparse/batched production workloads,',
        'remaining exact checker cost, setup amortization, and investigation of that',
        'unexplained exit. No follow-on allocation, public default, GPUP-8 completion,',
        'TENSOR2 pass or GPUP-9 release is implied. Historical results stay exact.','',
        '## Reproduction and acceptance','',
        '`python3 tools/lp_mixed2_fp4_analysis.py verify` reproduces every confirmation',
        'available cell, explicit missing-cell ledger and all descriptive summaries',
        'without CUDA or the original artifacts tree. Replay verifies stored response',
        'bytes, coverage, work/cost arithmetic and summaries; original-model serial',
        'recertification is the separate endpoint/audit acceptance described below.',
        'Use `bash tools/check_mixed2_fp4_cpu.sh` for isolated CPU acceptance.',
        '[Analysis](data/mixed2-fp4-analysis-v1.json),',
        '[original confirmation responses](data/mixed2-fp4-records-v1.json),',
        '[diagnosis](data/mixed2-fp4-diagnosis-v1.json),',
        '[acceptance](data/mixed2-fp4-acceptance-v1.json) and',
        '[allocation accounting](data/mixed2-fp4-accounting-v1.json) retain the evidence.',
        'The independent envelope is 160000 CPU / 24000 GPU seconds, four CPU slots,',
        '16 GiB sampled RSS and 12 GiB device buffers with one pinned shared lease.',
        'The original supervisor is unchanged. All failed reservations are fully charged;',
        'there is no historical budget transfer. Commit locally only.']
    product_lines=['', '## Guarded product diagnosis', '', '| Generic dimension / forward product | Original guard x2 μs | Optimized guard x2 μs | Optimized native μs | Native / FP4 product ratio |', '| --- | ---: | ---: | ---: | ---: |']
    old_products={r['family']:r for r in d['products']['products-v1']['rows'] if r['lane']=='fp4x2' and r['guarded'] and not r['transpose']}
    final_products={(r['family'],r['lane']):r for r in d['products']['products-v2']['rows'] if r['guarded'] and not r['transpose']}
    for family in sorted(old_products,key=lambda x:int(x.rsplit('-',1)[1])):
        fp=final_products[family,'fp4x2']['product_us'];native=final_products[family,'native']['product_us']
        product_lines.append(f"| {family} | {old_products[family]['product_us']:.3f} | {fp:.3f} | {native:.3f} | {native/fp:.3f} |")
    product_lines += ['', 'These are component diagnostics with fixed nonzero operands. The two versions', 'were measured at different times, so the before/after difference includes shared', 'environment variability; the contemporary native control is the stronger comparison.', 'Both directions and all guarded/unguarded block values remain in the diagnosis.']
    lines += product_lines
    if ACCEPTANCE.exists() and load(ACCEPTANCE).get('status')=='passed':
        x=load(ACCEPTANCE);lines += ['',f"Final acceptance: {x['rust_tests']} repository Rust / {x['python_tests']} Python tests; 27 isolated Rust tests; 204 original CPU admission assessments and {x['endpoint_assessments']} distinct original serial endpoint/audit reassessments. The current device suite has 130 cases and 2304 rational outputs; four scoped sanitizers each have 97 cases / 2304 outputs. All 22 process/configuration cases pass. Portable replay passes; {x['historical_files']} historical files and all older backlog entries remain exact."]
    if ACCOUNTING.exists() and load(ACCOUNTING).get('status')=='closed':
        x=load(ACCOUNTING);lines += ['',f"Allocation closed at {x['cpu_seconds']:.9f} CPU / {x['gpu_seconds']:.9f} GPU seconds, including 128 closing CPU seconds. {x['failed_jobs']} failed reservations and exact sources/logs are preserved; all cleanup is empty.", '', '[Portable development, models, admissions and sources](data/mixed2-fp4-evidence-v1.json), [complete resource receipts](data/mixed2-fp4-resources-v1.json.gz).']
    (ROOT/'docs/benchmarks/lp-mixed2-fp4.md').write_text('\n'.join(lines)+'\n')

def historical():
    h=load(BASE/'history.json');preserved=[]
    for path,sha in h['files'].items():
        if path not in ALLOWED:require(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,'historical file changed: '+path);preserved.append(path)
    for path in ('AGENTS.md','state/active-task.md','docs/plans/gpu-lp-precision-roadmap.md'):
        old=subprocess.check_output(['git','show',BASELINE+':'+path]).decode();body=old.split('\n',1)[1];require(body in (ROOT/path).read_text(),'old handoff changed: '+path)
    old=subprocess.check_output(['git','show',BASELINE+':state/backlog.yaml']).decode();now=(ROOT/'state/backlog.yaml').read_text();require(now.replace(re.search(r'^  - id: GPUP-MIXED2-FP4\n.*?(?=^  - id: )',now,re.M|re.S)[0],'',1)==old,'old backlog changed')
    tasks=lambda s:dict((m.group(1),m.group(0)) for m in re.finditer(r'^  - id: ([^\n]+)\n.*?(?=^  - id: |\Z)',s,re.M|re.S))
    new=tasks(now);parents={k:[p.strip() for p in re.search(r'depends_on: \[([^]]*)\]',v)[1].split(',') if p.strip()] for k,v in new.items()}
    visited=set()
    def visit(k,active):
        require(k in new and k not in active,'dependency cycle/missing')
        if k in visited:return
        for parent in parents[k]:visit(parent,active|{k})
        visited.add(k)
    for k in new:visit(k,set())
    return dict(baseline=BASELINE,preserved=preserved,allowed=sorted(ALLOWED),prior_text_exact=True,historical_tasks_exact=True,dependency_tasks=len(new))

def publish(path,value):
    if path.exists():
        require(load(path)==dict(status='pending'),'completed receipt overwrite')
        draft=BASE/'draft-receipts'/path.name;draft.parent.mkdir(exist_ok=True);draft.write_bytes(path.read_bytes())
        from lp_cpu_admission import atomic_json
        atomic_json(path,value)
    else:put(path,value)

def drafts():
    for path in (ACCEPTANCE,ACCOUNTING):put(path,dict(status='pending'))
    report()

def verify():
    replay();h=historical();native=BASE/'resources/native-v2';log=Path(str(native)+'.resource.json.log').read_text();rust=sum(int(n) for n in re.findall(r'test result: ok\. (\d+) passed;',log));require(rust==638 and 'Ran 700 tests' in log,'full coverage');require('committed run records re-executed and verified: passed' in log,'native replay')
    for job in ('native-v2','isolated-v1','endpoints-v1','product-oracle-v2','processes-v1','device-v6','memcheck-v5','racecheck-v5','initcheck-v5','synccheck-v5'):
        require(load(BASE/'resources'/(job+'.settlement.json'))['status']=='passed','acceptance job failed: '+job)
    for p in (BASE/'resources').glob('*.settlement.json'):
        s=load(p);r=load(ROOT/s['resource']['path']);require(not s['overrun'] and r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup/overrun')
    with tempfile.TemporaryDirectory(prefix='mixed2-fp4-portable-') as temp:
        dest=Path(temp);(dest/'tools').mkdir()
        for p in (ROOT/'tools').glob('*.py'):shutil.copy2(p,dest/'tools'/p.name)
        for p in [ANALYSIS,*archive_files()]:
            target=dest/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        subprocess.run([sys.executable,'-B','tools/lp_mixed2_fp4_analysis.py','verify'],cwd=dest,check=True);require(not (dest/'artifacts').exists(),'portable artifact dependency')
    for cmd in ([sys.executable,'tools/validate_artifacts.py'],[sys.executable,'tools/build_docs.py'],['git','diff','--check']):subprocess.run(cmd,check=True,cwd=ROOT)
    put(DATA/'mixed2-fp4-history-v1.json',h)
    publish(ACCEPTANCE,dict(status='passed',scientific_confirmation=load(ANALYSIS)['status'],retention_pass=False,binary=ref(BINARY),image=ref(BASE/'build-v8/mixed.cubin'),analysis=ref(ANALYSIS),archive=ref(ARCHIVE),history=ref(DATA/'mixed2-fp4-history-v1.json'),rust_tests=rust,python_tests=700,isolated_rust_tests=27,endpoint_assessments=load(BASE/'endpoints-v1/result.json')['endpoints'],historical_files=len(h['preserved']),portable_replay=True,cleanup_empty=True,native=ref(Path(str(native)+'.settlement.json'))))
    report();print(dict(status='passed',historical_files=len(h['preserved'])))

def close():
    admission_open();require(load(ACCEPTANCE)['status']=='passed','acceptance required');require(load(BASE/'resources/final-acceptance-v1.settlement.json')['status']=='passed','final settlement')
    cpu,gpu=accounting();cpu['cleanup']+=128*NS
    require(all(cpu[k]<=v*NS for k,v in CPU_CAPS.items()) and all(gpu[k]<=v*NS for k,v in GPU_CAPS.items()),'allocation exceeded')
    receipts=[]
    for p in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(p);stem=str(p).replace('.settlement.json','');r=load(stem+'.resource.json');require(not s['overrun'] and r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup/overrun')
        receipts.append(dict(binding=ref(p),settlement=s,reservation=load(stem+'.reservation.json'),resource=r,log=Path(stem+'.resource.json.log').read_text()))
    raw=DATA/'mixed2-fp4-resources-v1.json.gz'
    with raw.open('xb') as f:f.write(gzip.compress(json.dumps(dict(receipts=receipts,resource_files={str(p.relative_to(BASE)):p.read_text() for p in sorted((BASE/'resources').iterdir()) if p.is_file()}),sort_keys=True,separators=(',',':')).encode(),mtime=0))
    archive=DATA/'mixed2-fp4-evidence-v1.json'
    require(load(BASE/'resources/evidence-v1.settlement.json')['status']=='passed','evidence packaging')
    require(load(BASE/'resources/evidence-check-v1.settlement.json')['status']=='passed','evidence verification')
    value=dict(status='closed',cpu_caps_seconds=CPU_CAPS,gpu_caps_seconds=GPU_CAPS,cpu_ns=cpu,gpu_ns=gpu,cpu_seconds=sum(cpu.values())/NS,gpu_seconds=sum(gpu.values())/NS,closing_administration_cpu_seconds=128,failed_jobs=sum(r['settlement']['status']!='passed' for r in receipts),failed_reservations=[r['binding'] for r in receipts if r['settlement']['status']!='passed'],full_receipts=ref(raw),evidence=ref(archive),evidence_verification=ref(DATA/'mixed2-fp4-evidence-check-v1.json'),historical_transfers=0,cleanup_empty=True)
    publish(ACCOUNTING,value);put(BASE/'CLOSED.json',dict(accounting=ref(ACCOUNTING)));report();print(value)

def evidence():
    archive=BASE/'packaging-v2/mixed2-fp4-evidence-v1.tar.gz';paths=[p for p in BASE.rglob('*') if p.is_file() and not p.is_symlink() and not p.relative_to(BASE).parts[0].startswith('confirmation-b') and p.suffix!='.lock' and 'resources' not in p.relative_to(BASE).parts and not (p.parent.name=='packaging-v1' and p.suffix=='.gz')]
    # Earlier model files retain their original portable paths and exact bytes.
    paths+= [ROOT/r['path'] for r in load(BASE/'models/manifest-v2.json')['models'].values()]
    archive.parent.mkdir(exist_ok=True)
    with tarfile.open(archive,'x:gz',compresslevel=6) as tar:
        for p in sorted(set(paths)):tar.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
    parts=[]
    with archive.open('rb') as source:
        i=0
        while blob:=source.read(48<<20):
            path=DATA/f'mixed2-fp4-evidence-v1.part{i:02d}'
            with path.open('xb') as out:out.write(blob)
            parts.append(dict(**ref(path),bytes=len(blob)));i+=1
    index=DATA/'mixed2-fp4-evidence-v1.json'
    put(index,dict(format='concatenated-tar-gzip-v1',sha256=ref(archive)['sha256'],bytes=archive.stat().st_size,parts=parts))
    print(dict(archive=ref(index),files=len(set(paths))),flush=True)


def check_evidence():
    index=DATA/'mixed2-fp4-evidence-v1.json';manifest=load(index);digest=hashlib.sha256();size=0
    for r in manifest['parts']:
        blob=(ROOT/r['path']).read_bytes();require(len(blob)==r['bytes'] and hashlib.sha256(blob).hexdigest()==r['sha256'],'evidence part');digest.update(blob);size+=len(blob)
    require(size==manifest['bytes'] and digest.hexdigest()==manifest['sha256'],'evidence sequence')
    archive=BASE/'packaging-v2/mixed2-fp4-evidence-v1.tar.gz';count=0
    with tarfile.open(archive,'r|gz') as tar:
        for m in tar:
            require(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts,'unsafe evidence member')
            p=(ROOT/m.name).resolve();require(p.is_relative_to(ROOT),'evidence path escape')
            require(hashlib.sha256(tar.extractfile(m).read()).digest()==hashlib.sha256(p.read_bytes()).digest(),'evidence content: '+m.name);count+=1
    put(DATA/'mixed2-fp4-evidence-check-v1.json',dict(status='passed',index=ref(index),files=count,original_bytes_exact=True))
    print(dict(status='passed',files=count),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['report','drafts','verify','evidence','check_evidence','close']);a=p.parse_args();globals()[a.action]()
