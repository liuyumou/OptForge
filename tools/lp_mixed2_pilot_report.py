"""Durable pilot findings, portable acceptance, preservation and independent closure."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from lp_mixed2_pilot_common import ROOT,BASE,BINARY,IMAGE,BASELINE,CPU_CAPS,GPU_CAPS,NS,load,put,ref,require
from lp_mixed2_pilot_budget import accounting,admission_open
from lp_mixed2_pilot_analysis import DATA,OUTPUT,ARCHIVE,verify as replay
ACCEPTANCE=DATA/'mixed2-pilot-acceptance-v1.json'
ACCOUNTING=DATA/'mixed2-pilot-accounting-v1.json'
ALLOWED={'AGENTS.md','state/active-task.md','state/backlog.yaml','docs/plans/gpu-lp-precision-roadmap.md','CHANGELOG.md','state/known-failures.md'}


def report():
    a=load(OUTPUT)
    lines=['# MIXED2 prepared attribution and GPU storage pilot','',
        'The bounded pilot completes under [SPEC-0037](../specifications/SPEC-0037-mixed2-pilot.md)',
        'and [ADR-0070](../decisions/ADR-0070-mixed2-pilot.md). The 1.10x target is now',
        'a provisional adoption criterion requiring workload-value and sample-size',
        'justification before later confirmation. A useful, safe diagnostic pilot does',
        'not require an assumed 1.10x win. All historical criteria and results remain exact.','',
        '**Do not integrate this product/guard implementation into a mixed solver.**',
        'FP32 storage is approximately tied at dense128/256 and loses at dense512',
        '(0.876x native product throughput). Including the dense conservative guard',
        'gives only 0.350–0.429x native product throughput across the measured shapes.',
        'This negative result does not depend on choosing 1.10x instead of parity.',
        'Separately, profiling inflates dense complete time by 7.7–9.2x; the actual',
        'uninstrumented matrix fraction remains inconclusive. Both findings are retained.','',
        '## Prepared native attribution','',
        'All 192 prepared sessions / 576 solves complete across twelve families at the',
        'strict 1e-9 tier: 528 independently checked certificates and 48 intentional',
        'unbounded-direction refusals. Every endpoint, audit, certificate, checkpoint,',
        'recovery and unit of physical work matches the retained original, including',
        'signed zeros. Both variants use the same checker, batching and setup overlap.','',
        '| Family | Control complete ms | Control GPU ms | Profile complete / control | Instrumented matrix union ms | Instrumented outer event ms |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in a['prepared']:
        lines.append(f"| {r['family']} | {r['control_ms']['median']:.3f} | {r['control_gpu_ms']['median']:.3f} | {r['profile_over_control']['median']:.3f}x | {r['profile_matrix_ms']['median']:.3f} | {r['profile_outer_event_ms']['median']:.3f} |")
    lines += ['',
        'Each entry is the median of eight block values; within a session complete',
        'and event costs are means of all three fresh solves. Profile matrix costs',
        'are interval unions across concurrently active CTAs, divided by three solves.',
        'The machine record retains all eight values, ranges, setup, teardown and',
        'separate CUDA kernel events/CTA unions. Zeros on sparse nativefast paths mean',
        '**unattributed**, not free matrix work. Instrumentation adds per-launch events,',
        'timestamp stores, readback and durable diagnostic logging. Its measured',
        'disturbance prevents interpreting these matrix durations as exact durations',
        'of the uninstrumented control. No subtraction claims to remove that bias.',
        'Compiler resource reports show 39 registers and 2048 bytes shared memory',
        'for both native kernels, with no spills. That observation does not rule out',
        'instruction/scheduling perturbation. Both product kernels use 40 registers',
        'and 2048 bytes shared memory; the guard uses 40 registers and 4096 bytes.',
        'The control is this new package’s wrapper around retained native kernels;',
        'its timings are not interchangeable with historical DELIVERY4 samples.','',
        'The device global timer is a target-specific facility intended for NVIDIA',
        'tools; its semantics are not a portable timing guarantee.',
        '[PTX documentation](https://docs.nvidia.com/cuda/parallel-thread-execution/index.html#special-registers-globaltimer-globaltimer-lo-globaltimer-hi).',
        'The product timer probes retain every timestamp. Their minimum positive',
        'read-to-read spacing is 32 ns in every family/direction summary; this is',
        'an observed spacing, not a guaranteed hardware resolution.',
        'Software spans omit scheduling outside their first/last CTA and are not',
        'interchangeable with enclosing CUDA events or complete delivery.','',
        '## FP32 storage products and conservative guard','',
        'The independent 192-cell product cohort uses original unscaled matrices,',
        'both directions, fixed generic nonzero vectors and 128 launches per cell.',
        'FP64 and FP32 storage use identical FP64 FMA/reduction schedules. These',
        'product kernels differ from the retained solver’s separate multiply/add',
        'schedule; this microprobe is not a drop-in solver comparison.','',
        '| Family / direction | FP64 μs | FP32 μs | Guard μs | FP64 / FP32 | FP64 / (FP32 + guard) |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for r in a['products']:
        lines.append(f"| {r['family']} / {'transpose' if r['transpose'] else 'A'} | {r['fp64_us']['median']:.3f} | {r['fp32_us']['median']:.3f} | {r['guard_us']['median']:.3f} | {r['product_speed_ratio']['median']:.3f}x | {r['guarded_speed_ratio']['median']:.3f}x |")
    lines += ['',
        'Costs divide the measured stream-batch event by 128; host launch gaps remain',
        'inside that boundary. Marginal medians do not add; ratios are formed within',
        'each block first. These are descriptive observations, not simultaneous',
        'confidence bounds, statistical power or retained solver speedups.','',
        'The guard encloses representation error plus FP64 FMA/tree rounding and',
        'subnormal allowances using upward arithmetic. Independent rational original',
        f"dots check {a['guarded_outputs']} study outputs; independent rational FMA",
        'schedule replay checks both product outputs, including padding. Admission',
        'also covers FP32 subnormals, binary64 underflow, cancellation and edge shapes.',
        'There is no approximate final certificate or FP32 iterative state.','',
        '| Family / direction | All representations μs | FP32 allocation/upload μs | Error allocation/upload μs | Output readback μs |',
        '| --- | ---: | ---: | ---: | ---: |']
    for r in a['products']:
        lines.append(f"| {r['family']} / {'transpose' if r['transpose'] else 'A'} | {r['representation_us']['median']:.1f} | {r['fp32_upload_us']['median']:.1f} | {r['error_upload_us']['median']:.1f} | {r['download_us']['median']:.1f} |")
    lines += ['',
        'Representation timing constructs FP64, FP32 and error arrays together;',
        'the incremental CPU packing cost versus an existing native representation',
        'is not identified. CPU oracle time is measured separately and excluded from',
        'that representation span. Transfer spans include allocation and synchronization.',
        'With retained FP64 coefficients, both-direction FP32 storage plus a dense',
        'FP64 error array raises coefficient-buffer storage to 2.5 times native alone.',
        'These costs must be amortized explicitly; 128 launches are not 128 solves.',
        'The machine record includes 1/128/4096-product scenarios with and without',
        'per-product host readback. They charge all measured representation work and',
        'FP32/error allocation/upload once, and product plus guard on every call.',
        'That is a conservative assignment of packing cost, not an identified',
        'incremental cost. The resident case excludes an unimplemented device policy.',
        'These are conditional product scenarios, not LP-solver forecasts.','',
        '## Implications and limits','',
        'Whole-event 2x/removal forecasts remain optimistic sensitivity cases in the',
        '[machine analysis](data/mixed2-pilot-analysis-v1.json). They assume unchanged',
        'work and zero added cost; actual matrix-only complete benefit is not identified',
        'by disturbed software profiling. Prepared sessions are appropriate for further',
        'cost questions; the historical 1.010266x ideal cold upper bound remains exact.',
        'Separate lifecycle forecasts amortize measured setup/teardown over 1, 3 and',
        '100 native solves while hypothetically halving all GPU event time. They keep',
        'the zero-added-cost assumption explicit and do not identify matrix-only gains.',
        'The prior measured context costs and unresolved outer latency remain in the',
        '[MIXED2 CPU report](lp-mixed2.md) and [DELIVERY4 report](lp-delivery4.md).','',
        'Useful mixed windows, convergence, work amplification, rollback/correction',
        'cost and final full-solver performance remain unmeasured. Eight ordered blocks',
        'on a shared device do not establish independent production performance.',
        'No family is removed, no public default is selected and GPUP-8 stays incomplete.',
        'A later numerical solver study needs its own cost case, fixed useful-work',
        'criteria, resource manifest and workload-value/sample-size justification.',
        'Priorities from this pilot are a less intrusive attribution method and a',
        'cheaper guard/representation design with a measured component benefit.',
        'Cached coefficient-error norms with vector norms are a possible cheaper but',
        'looser enclosure to investigate, not an admitted implementation or speed claim.',
        'No full-solver confirmation is justified by these product results.','',
        '## Reproduction and acceptance','',
        '`python3 -B tools/lp_mixed2_pilot_analysis.py verify` reproduces all cells,',
        'numeric checks and summaries from the [portable archive](data/mixed2-pilot-records-v1.json.gz).',
        'Replay requires Python and repository validation dependencies, but no CUDA,',
        'executable or original artifacts tree. Admission evidence and exact source',
        'bindings are in [acceptance](data/mixed2-pilot-acceptance-v1.json).','',
        'The new image passes memcheck, racecheck, initcheck and synccheck, with',
        'nonzero error exits enforced. These are scoped admission runs, not a guarantee',
        'for untested inputs. [Compute Sanitizer documentation](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html).',
        'The repository gate passes 638 Rust / 694 Python tests, native replay, dependency,',
        'artifact, documentation and smoke checks. The isolated crate passes 30 Rust',
        'tests; 204 fresh CPU assessments reproduce 102 retained serial endpoints,',
        '48 representation comparisons and 21 process/configuration cases.','',
        'The independent allocation is 48000 CPU / 2400 GPU seconds, with four CPUs,',
        '16 GiB sampled RSS, a pinned shared GPU lease and the unchanged supervisor.',
        'All failed reservations, source versions and cleanup are retained in',
        '[accounting](data/mixed2-pilot-accounting-v1.json). No historical budget transfer,',
        'scientific retry, public default, follow-on solver allocation or GPUP-9 release.',
        'Three development failures retain full charges: an ambiguous Rust buffer',
        'element type (1440 CPU seconds), the expected pre-CUDA missing-model exit',
        'misclassified as a missing sanitizer summary (600 CPU / 150 GPU seconds),',
        'and a reporting-script bracket typo (360 CPU seconds). Corrected versions',
        'pass. The sanitizer exception is exact and limited to that pre-CUDA refusal;',
        'it does not waive any executed kernel check. No scientific cell was retried.',
        'Commit locally only.']
    if ACCOUNTING.exists() and load(ACCOUNTING).get('status')=='closed':
        c=load(ACCOUNTING);lines+=['',f"Closed charge: **{c['cpu_seconds']:.9f} CPU / {c['gpu_seconds']:.9f} GPU seconds**, including 128 closing CPU seconds; {c['failed_jobs']} failed reservations retained. All cleanup is empty."]
    if ACCEPTANCE.exists() and load(ACCEPTANCE).get('status')=='passed':
        lines += ['',f"Final preservation: {load(ACCEPTANCE)['historical_files']} historical files and all prior backlog entries remain exact; isolated portable replay passed."]
    (ROOT/'docs/benchmarks/lp-mixed2-pilot.md').write_text('\n'.join(lines)+'\n')


def history():
    preserved=[]
    for item in subprocess.check_output(['git','ls-tree','-rz','--full-tree',BASELINE],cwd=ROOT).split(b'\0'):
        if not item:continue
        metadata,name=item.split(b'\t',1);mode,kind,blob=metadata.split();name=name.decode()
        if name in ALLOWED:continue
        require(kind==b'blob','historical gitlink')
        raw=os.readlink(ROOT/name).encode() if mode==b'120000' else (ROOT/name).read_bytes()
        digest=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest();require(digest==blob.decode(),'historical change: '+name);preserved.append(dict(path=name,git_blob=digest))
    for name in ('AGENTS.md','state/active-task.md','CHANGELOG.md','state/known-failures.md','docs/plans/gpu-lp-precision-roadmap.md'):
        old=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT).decode().split('\n\n',1)[1]
        require((ROOT/name).read_text().endswith(old),'older text changed '+name)
    def tasks(text):
        starts=list(re.finditer(r'^  - id: (\S+)\s*$',text,re.M));return {m[1]:text[m.start():starts[i+1].start() if i+1<len(starts) else len(text)] for i,m in enumerate(starts)}
    old=tasks(subprocess.check_output(['git','show',BASELINE+':state/backlog.yaml'],cwd=ROOT).decode());new=tasks((ROOT/'state/backlog.yaml').read_text())
    require(set(new)==set(old)|{'GPUP-MIXED2-PILOT'},'unexpected task roster')
    for name in old:require(old[name]==new[name],'historical backlog changed '+name)
    require('    status: complete\n' in new['GPUP-MIXED2-PILOT'],'pilot incomplete')
    parents={name:[v.strip() for v in re.search(r'^    depends_on: \[([^]\n]*)\]',text,re.M)[1].split(',') if v.strip()] for name,text in new.items()}
    visited=set()
    def visit(name,active):
        require(name in new and name not in active,'missing dependency or cycle')
        if name in visited:return
        for parent in parents[name]:visit(parent,active|{name})
        visited.add(name)
    for name in new:visit(name,set())
    for name in parents['GPUP-MIXED2-PILOT']:require('    status: complete\n' in new[name],'pilot dependency incomplete')
    return dict(baseline=BASELINE,preserved=preserved,allowed=sorted(ALLOWED),historical_tasks_exact=True,prior_text_exact=True,dependency_tasks=len(new))


def evidence():
    files={}
    for dirname in ('cpu-v1','device-v1','memcheck-v1','memcheck-v2','racecheck-v1','initcheck-v1','synccheck-v1'):
        for p in sorted((BASE/dirname).rglob('*')):
            if p.is_file():files[str(p.relative_to(BASE))]=p.read_text()
    path=DATA/'mixed2-pilot-admission-v1.json.gz'
    with path.open('xb') as f:f.write(gzip.compress(json.dumps(files,sort_keys=True,separators=(',',':')).encode(),mtime=0))
    for path in (ACCEPTANCE,ACCOUNTING):
        if not path.exists():put(path,dict(status='pending'))
    report()


def publish(path,value):
    if path.exists():
        require(load(path)==dict(status='pending'),'completed receipt overwrite')
        dest=BASE/'draft-receipts'/path.name;dest.parent.mkdir(exist_ok=True)
        with dest.open('xb') as f:f.write(path.read_bytes())
        from lp_cpu_admission import atomic_json
        atomic_json(path,value)
    else:put(path,value)


def verify():
    replay();h=history()
    native=load(BASE/'resources/cpu-native-v1.settlement.json');require(native['status']=='passed','native gate')
    log=(BASE/'resources/cpu-native-v1.resource.json.log').read_text()
    rust=sum(int(v) for v in re.findall(r'test result: ok\. (\d+) passed;',log));require(rust==638 and 'Ran 694 tests' in log,'full coverage')
    require('committed run records re-executed and verified: passed' in log,'native replay')
    for name in ('device','memcheck','racecheck','initcheck','synccheck'):
        version='-v2' if name=='memcheck' else '-v1'
        require(load(BASE/(name+version+'/result.json'))['status']=='passed','device admission')
        require(load(BASE/'resources'/(name+version+'.settlement.json'))['status']=='passed','device settlement')
    with tempfile.TemporaryDirectory(prefix='gpup-mixed2-pilot-portable-') as directory:
        dest=Path(directory);(dest/'tools').mkdir()
        for p in (ROOT/'tools').glob('*.py'):shutil.copyfile(p,dest/'tools'/p.name)
        for p in (ARCHIVE,OUTPUT):
            target=dest/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        subprocess.run([sys.executable,'-B','tools/lp_mixed2_pilot_analysis.py','verify'],cwd=dest,check=True)
        require(not (dest/'artifacts').exists(),'portable replay accessed artifacts')
    for path in (BASE/'resources').glob('*.settlement.json'):
        s=load(path);require(not s['overrun'],'overrun');r=load(ROOT/s['resource']['path']);require(r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup')
    for command in ([sys.executable,'tools/validate_artifacts.py'],[sys.executable,'tools/build_docs.py'],['git','diff','--check']):subprocess.run(command,cwd=ROOT,check=True)
    put(DATA/'mixed2-pilot-history-v1.json',h)
    publish(ACCEPTANCE,dict(status='passed',analysis=ref(OUTPUT),archive=ref(ARCHIVE),admission=ref(DATA/'mixed2-pilot-admission-v1.json.gz'),history=ref(DATA/'mixed2-pilot-history-v1.json'),native=ref(BASE/'resources/cpu-native-v1.settlement.json'),dependencies=load(BASE/'dependencies-v1.json'),rust_tests=638,python_tests=694,isolated_rust_tests=30,historical_files=len(h['preserved']),portable_replay=True,cleanup_empty=True,binary=ref(BINARY),image=ref(IMAGE)))
    print(dict(status='passed',historical_files=len(h['preserved'])),flush=True)


def close():
    admission_open();require(load(ACCEPTANCE)['status']=='passed','acceptance required')
    require(load(BASE/'resources/final-acceptance-v1.settlement.json')['status']=='passed','final settlement')
    cpu,gpu=accounting();cpu['cleanup']+=128*NS
    require(all(cpu[k]<=v*NS for k,v in CPU_CAPS.items()) and all(gpu[k]<=v*NS for k,v in GPU_CAPS.items()),'allocation exceeded')
    receipts=[]
    for path in sorted((BASE/'resources').glob('*.settlement.json')):
        s=load(path);stem=str(path).replace('.settlement.json','');r=load(stem+'.resource.json');require(not s['overrun'] and r['guardian_cleanup']['empty'] and r['result']['cleanup']['empty'],'cleanup/overrun')
        receipts.append(dict(binding=ref(path),settlement=s,reservation=load(stem+'.reservation.json'),resource=r,log=Path(stem+'.resource.json.log').read_text()))
    sources={str(p.relative_to(BASE)):p.read_text() for p in sorted((BASE/'sources').rglob('*')) if p.is_file()}
    sources.update({p.name:p.read_text() for p in BASE.iterdir() if p.suffix in ('.py','.sh')})
    binary_archive=BASE/'binaries'/ref(BINARY)['sha256'];binary_archive.parent.mkdir(exist_ok=True)
    with binary_archive.open('xb') as stream:stream.write(BINARY.read_bytes())
    require(ref(binary_archive)['sha256']==ref(BINARY)['sha256'],'binary archive mismatch')
    raw=DATA/'mixed2-pilot-resources-v1.json.gz'
    with raw.open('xb') as f:f.write(gzip.compress(json.dumps(dict(receipts=receipts,development_sources=sources),sort_keys=True,separators=(',',':')).encode(),mtime=0))
    value=dict(status='closed',cpu_caps_seconds=CPU_CAPS,gpu_caps_seconds=GPU_CAPS,cpu_ns=cpu,gpu_ns=gpu,cpu_seconds=sum(cpu.values())/NS,gpu_seconds=sum(gpu.values())/NS,closing_administration_cpu_seconds=128,failed_jobs=sum(r['settlement']['status']!='passed' for r in receipts),failed_reservations=[r['binding'] for r in receipts if r['settlement']['status']!='passed'],full_receipts_and_sources=ref(raw),binary_archive=ref(binary_archive),image=ref(IMAGE),historical_transfers=0,cleanup_empty=True)
    publish(ACCOUNTING,value);put(BASE/'CLOSED.json',dict(accounting=ref(ACCOUNTING)));report();print(value,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['evidence','verify','close','report']);a=p.parse_args();globals()[a.action]()
