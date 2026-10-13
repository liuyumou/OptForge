"""Frozen ADR-0036 scalar device validation and descriptive primitive timings.

Uses the existing canonical campaign ledger and supervised shared host lease.
Never retries an attempted identity, launches the refused full-bin kernels, or
promotes a primitive result to a controller/solver performance claim.
"""
import argparse
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import tarfile

import lp_state_admission as admission
import lp_state_review as review
from lp_protocol import ROOT, NS, read_json, write_json, file_hash
from lp_copt_budget import ComparisonLedger, receipt
from lp_expansion_oracle import power2, round_fraction

COHORTS = {
    "v1": ("GPU-dfb2449a-9eff-e868-3597-2c448c9a8e48", 16366,
           "4d083cdb06b4baa38452bb331541fa8874614aeb037f34e40001ce9692ede26b",
           17635432015338, 500, 1100),
    "v2": ("GPU-6721b13a-30f9-83ec-dace-ba2d9738556f", 16368,
           "a97630527900a1a11cfd612bd3f96d55a86c211555bb0adc7de3ab52adebfc96",
           17638434099818, 496, 1096),
}


def select_cohort(name):
    global ID, DEVICE, OUTPUT, PREFIX_EVENTS, PREFIX_HASH, PRIOR_NS, ACCEPT_SECONDS, CAP_SECONDS
    DEVICE, PREFIX_EVENTS, PREFIX_HASH, PRIOR_NS, ACCEPT_SECONDS, CAP_SECONDS = COHORTS[name]
    ID = "gpup-state-device-" + name
    OUTPUT = ROOT / "artifacts" / ID


select_cohort("v2")
SOURCE = ROOT / "tools/diagnostics/lp_state_device_probe.cu"
BINARY = ROOT / "target/release/examples/lp_state_probe"
SENTINEL = [0xa5a5a5a5a5a5a5a5, -777, 13, 0xa5a5a5a5]
ALLOWED = ["state_compact_fma_p48", "state_compact_fma_p64", "state_bench_p48", "state_bench_p64"]
KERNELS = review.KERNELS + ["state_bench_p48", "state_bench_p64"]
PATTERNS = ("increment", "far_tail", "cancellation")
SHAPES = {"chain": (1, 16385, 1), "batch": (65536, 129, 128)}
FROZEN_FILES = {"protocol.json","roster.json","corpus.json","lp_state_probe","device.cubin",
                "compiler.log","resources.txt","instructions.sass","source.tar","execution.json"} | {
    "sources/"+name for name in [SOURCE.name,review.SOURCE.name,admission.SOURCE.name,
        "lp_state_probe.rs","ADR-0036-full-expansion-state-admission.md"]}


def protocol():
    return dict(schema_version=1, id=ID, device=DEVICE, prior_events=PREFIX_EVENTS,
                prior_ledger_sha256=PREFIX_HASH, prior_gpu_ns=PRIOR_NS,
                cumulative_gpu_ns=21602574545061, total_gpu_seconds=28800,
                phase_gpu_seconds=dict(baseline=1800,screening=9500,ablations=7650,repeatability=4450,finalists=9000),
                categories=dict(accept=dict(phase="repeatability",seconds=ACCEPT_SECONDS),
                                timing=dict(phase="screening",seconds=600)),
                combined_cap_seconds=CAP_SECONDS,cpu_cap_seconds=14400,
                shapes={name:list(shape) for name,shape in SHAPES.items()},
                patterns=list(PATTERNS),precisions=[48,64],repetitions=3,
                allocation_cap_bytes=64*1024*1024)


def ledger_for(value):
    # Validate public authority before opening any private campaign artifact.
    if admission.encoded(value) != admission.encoded(protocol()):
        raise ValueError("state device authority differs")
    from lp_exec_budget import protocol as parent_protocol, ledger_for as parent_ledger
    inherited = parent_ledger(parent_protocol())
    prefix = b"".join(inherited.path.read_bytes().splitlines(keepends=True)[:PREFIX_EVENTS])
    if len(prefix.splitlines()) != PREFIX_EVENTS or hashlib.sha256(prefix).hexdigest() != PREFIX_HASH:
        raise ValueError("state device historical prefix differs")
    if sum(json.loads(line)["charged_ns"] for line in prefix.splitlines() if json.loads(line)["resource"] == "gpu") != PRIOR_NS:
        raise ValueError("state device prior consumption differs")
    return ComparisonLedger(inherited.path.parent, inherited.campaign_hash, value)


def corpus():
    # Preserve each original fixture byte and build a separate unsigned wire
    # document so Rust never decodes negative 64-bit magnitudes through f64.
    original = admission.read_document(admission.FIXTURE)
    extra = admission.read_document(review.FIXTURE)
    if admission.encoded(admission.fixture()) != admission.FIXTURE.read_text() or admission.encoded(review.fixture()) != review.FIXTURE.read_text():
        raise ValueError("independent source fixtures differ")
    cases = []
    for case in original["fma_cases"] + extra["cases"]:
        result = case["result"]
        expected = SENTINEL[:3] + [2] if result["infinity_sign"] else admission.wire(result) + [0]
        cases.append(dict(precision=case["precision"],input=case["input"],expected=expected))
    return dict(schema_version=1,identity=ID+"-corpus",cases=cases)


def roster():
    jobs = [dict(id=ID+"-accept-"+gate,category="accept",gate=gate,seconds=seconds,mode="check")
            for gate,seconds in [("oracle",30),("repeat",30),("memcheck",90),("racecheck",90),
                                 ("initcheck",90),("synccheck",90)]]
    # Fixed alternating order across repetitions; no measured-result selection.
    cells = [(p,pattern,shape) for p in (48,64) for pattern in PATTERNS for shape in SHAPES]
    for repetition in range(3):
        for precision,pattern,shape in (cells if repetition%2 == 0 else list(reversed(cells))):
            count,iterations,block = SHAPES[shape]
            jobs.append(dict(id=f"{ID}-timing-p{precision}-{pattern}-{shape}-r{repetition}",category="timing",
                             gate="timing",seconds=10,mode="timing",precision=precision,pattern=pattern,
                             shape=shape,count=count,iterations=iterations,block=block,repetition=repetition))
    return jobs


@lru_cache(maxsize=256)
def expected_benchmark(precision, pattern, iterations, residue):
    one = 1 << (precision-1)
    if pattern == "increment":
        coefficient,exponent = one+residue+iterations, -(precision-1)
    elif pattern == "far_tail":
        coefficient,exponent = (-1 if iterations%2 else 1)*(one+residue), -(precision-1)
    elif pattern == "cancellation":
        coefficient,exponent = (-residue if iterations%2 else one+residue), -(precision-1)
    else:
        raise ValueError("unknown benchmark pattern")
    return admission.wire(round_fraction(coefficient*power2(exponent),(precision,-1022,1023)))+[0]


def launch_plan(job):
    if job["mode"] == "timing":
        return [dict(precision=job["precision"],count=job["count"],block=job["block"],iterations=job["iterations"],
                     pattern=job["pattern"],phase=phase) for phase in ("warmup","measured")]
    launches = []
    for p in (48,64):
        for block in (64,128,256):
            for repeat in range(2):
                launches.append(dict(precision=p,count=3085,block=block,iterations=None,repeat=repeat))
        for count in (0,1,31,32,33,127,128,129):
            launches.append(dict(precision=p,count=count,block=128,iterations=None))
        for pattern in PATTERNS:
            for count,block,iterations in ((1,1,7),(129,128,8)):
                launches.append(dict(precision=p,count=count,block=block,iterations=iterations,pattern=pattern))
    return launches


def request_for(job, frozen):
    fields = {key:job[key] for key in ("precision","count","block","iterations","pattern") if key in job}
    return dict(schema_version=1,identity=ID,attempt=job["id"],mode=job["mode"],device=DEVICE,
                image=str(frozen/"device.cubin"),corpus=str(frozen/"corpus.json"),**fields)


def verify_endpoint(endpoint, job, request, data):
    if admission.encoded(endpoint.get("request")) != admission.encoded(request) or type(endpoint.get("schema_version")) is not int or endpoint["schema_version"] != 1 or endpoint.get("device",{}).get("uuid") != DEVICE:
        raise ValueError("device endpoint identity differs")
    for key in ("context_ns","module_stream_ns","allocation_ns","teardown_ns","process_work_ns"):
        if type(endpoint.get(key)) is not int or endpoint[key] < 0:
            raise ValueError("device endpoint cost field")
    plan = launch_plan(job)
    if len(endpoint.get("launches",[])) != len(plan):
        raise ValueError("device launch roster differs")
    expected_cases = {p:[case["expected"] for case in data["cases"] if case["precision"]==p] for p in (48,64)}
    numerical = []
    for result, expected in zip(endpoint["launches"],plan):
        metadata = {key:result.get(key) for key in ("precision","count","block","iterations","repeat","pattern","phase") if key in result}
        if admission.encoded(metadata) != admission.encoded(expected):
            raise ValueError("device launch parameters differ")
        count,p,iterations = expected["count"],expected["precision"],expected["iterations"]
        kernel = f"state_compact_fma_p{p}" if iterations is None else f"state_bench_p{p}"
        if result.get("kernel") != kernel:
            raise ValueError("device kernel identity differs")
        if iterations is None:
            values = expected_cases[p][:count]
        else:
            values = [expected_benchmark(p,expected["pattern"],iterations,i%17) for i in range(count)]
        actual = result.get("values")
        # Canonical comparison rejects booleans, float-rounded u64s and wrong guards.
        if admission.encoded(actual) != admission.encoded(values+[SENTINEL]):
            raise ValueError("independent device FMA endpoint differs")
        cycles = result.get("cycles")
        if type(cycles) is not list or len(cycles) != count+1 or any(type(n) is not int or n<0 for n in cycles) or cycles[-1] != 0:
            raise ValueError("device cycle receipt differs")
        if (iterations is None and any(cycles)) or (iterations is not None and any(n==0 for n in cycles[:-1])):
            raise ValueError("device cycle scope differs")
        expected_allocation = (3085+1)*76 if job["mode"]=="check" else (count+1)*76
        if type(result.get("allocated_bytes")) is not int or result["allocated_bytes"] != expected_allocation:
            raise ValueError("device allocation accounting differs")
        for key in ("host_prepare_ns","upload_ns","launch_sync_ns","download_ns"):
            if type(result.get(key)) is not int or result[key] < 0:
                raise ValueError("device launch cost field")
        if not result["launch_sync_ns"]:
            raise ValueError("zero measured launch duration")
        numerical.append([metadata,actual])
    return hashlib.sha256(admission.encoded(numerical).encode()).hexdigest()


def freeze():
    from benchmark_lp import source_identity, prepare_execution, provenance
    gate = read_json(ROOT/"target/lp-native-gate.json")
    if gate != dict(native=True,source_tree_sha256=source_identity()):
        raise ValueError("exact-source full native gate required")
    frozen = OUTPUT/"frozen"
    frozen.mkdir(parents=True,exist_ok=False)
    sources = frozen/"sources"; sources.mkdir()
    for path in [SOURCE,review.SOURCE,admission.SOURCE,
                 ROOT/"crates/optimizer-lp-cuda/examples/lp_state_probe.rs",
                 ROOT/"docs/decisions/ADR-0036-full-expansion-state-admission.md"]:
        shutil.copy2(path,sources/path.name)
    write_json(frozen/"protocol.json",protocol()); write_json(frozen/"roster.json",roster())
    write_json(frozen/"corpus.json",corpus()); shutil.copy2(BINARY,frozen/"lp_state_probe")
    nvcc = "/usr/local/cuda/bin/nvcc"; dump = "/usr/local/cuda/bin/cuobjdump"
    command=[nvcc,"--cubin","-std=c++17","-arch=sm_120","-O3","-lineinfo","-fmad=false","-ftz=false",
             "--ptxas-options=-v",str(sources/SOURCE.name),"-o",str(frozen/"device.cubin")]
    compiled=subprocess.run(command,capture_output=True,text=True,timeout=300)
    (frozen/"compiler.log").write_text(compiled.stdout+compiled.stderr); compiled.check_returncode()
    resources=subprocess.check_output([dump,"--dump-resource-usage",str(frozen/"device.cubin")],text=True)
    sass=subprocess.check_output([dump,"--dump-sass",str(frozen/"device.cubin")],text=True)
    (frozen/"resources.txt").write_text(resources); (frozen/"instructions.sass").write_text(sass)
    inventory=admission.resource_audit(resources,compiled.stdout+compiled.stderr,sass,KERNELS)
    for name in ALLOWED:
        if inventory[name]["status"] != "fits_resource_gate":
            raise ValueError("device primitive resource refusal: "+name)
    for name in ALLOWED[2:]:
        instructions=inventory[name]["instruction_counts"]
        if not any(i.startswith("BRA") for i in instructions) or instructions.get("CS2R",0)+instructions.get("S2R",0)<2:
            raise ValueError("dynamic timed loop/clock audit missing")
    base=provenance(frozen/"lp_state_probe",DEVICE)
    base.update(code_object_sha256=file_hash(frozen/"device.cubin"),build_profile="release")
    prepare_execution(frozen,base)
    write_json(frozen/"freeze.json",dict(identity=ID,source_tree_sha256=gate["source_tree_sha256"],
        compiler_command=command,nvcc_version=subprocess.check_output([nvcc,"--version"],text=True),
        native_gate=gate,kernels=inventory,files={str(p.relative_to(frozen)):file_hash(p)
        for p in sorted(frozen.rglob("*")) if p.is_file()}))
    verify_freeze(frozen)
    print("frozen and audited: "+str(frozen))


def verify_freeze(frozen):
    record=read_json(frozen/"freeze.json")
    if set(record)!={"identity","source_tree_sha256","compiler_command","nvcc_version","native_gate","kernels","files"} or type(record["files"]) is not dict or set(record["files"])!=FROZEN_FILES:
        raise ValueError("frozen device inventory differs")
    if record["identity"] != ID or read_json(frozen/"protocol.json") != protocol() or read_json(frozen/"roster.json") != roster():
        raise ValueError("frozen device protocol differs")
    for name,digest in record["files"].items():
        path=Path(name)
        if path.is_absolute() or ".." in path.parts or file_hash(frozen/path)!=digest:
            raise ValueError("frozen device file differs")
    hasher=hashlib.sha256()
    with tarfile.open(frozen/"source.tar") as archive:
        members=archive.getmembers()
        names=[m.name for m in members]
        if names!=sorted(set(names)) or any(not m.isfile() or Path(m.name).is_absolute() or ".." in Path(m.name).parts for m in members):
            raise ValueError("frozen source archive inventory differs")
        for member in members:
            hasher.update(member.name.encode()+b"\0"+archive.extractfile(member).read()+b"\0")
    if hasher.hexdigest()!=record["source_tree_sha256"] or record["native_gate"]!=dict(native=True,source_tree_sha256=record["source_tree_sha256"]):
        raise ValueError("frozen source/native gate binding differs")
    execution=read_json(frozen/"execution.json")
    if execution["source_tree_sha256"]!=record["source_tree_sha256"] or execution["source_archive_sha256"]!=file_hash(frozen/"source.tar") or execution["binary_sha256"]!=file_hash(frozen/"lp_state_probe") or execution["code_object_sha256"]!=file_hash(frozen/"device.cubin") or execution["device"]!=DEVICE:
        raise ValueError("frozen execution binding differs")
    if admission.encoded(read_json(frozen/"corpus.json")) != admission.encoded(corpus()):
        raise ValueError("frozen device independent corpus differs")
    dump="/usr/local/cuda/bin/cuobjdump"
    resources=subprocess.check_output([dump,"--dump-resource-usage",str(frozen/"device.cubin")],text=True)
    sass=subprocess.check_output([dump,"--dump-sass",str(frozen/"device.cubin")],text=True)
    if resources!=(frozen/"resources.txt").read_text() or sass!=(frozen/"instructions.sass").read_text():
        raise ValueError("actual device image audit differs")
    inventory=admission.resource_audit(resources,(frozen/"compiler.log").read_text(),sass,KERNELS)
    if inventory!=record["kernels"] or any(inventory[name]["status"]!="fits_resource_gate" for name in ALLOWED):
        raise ValueError("device resource outcome differs")
    return record


def command_for(job,frozen,request,endpoint):
    command=[str(frozen/"lp_state_probe"),str(request),str(endpoint)]
    if job["gate"] in ("memcheck","racecheck","initcheck","synccheck"):
        command=["/usr/local/cuda/bin/compute-sanitizer","--error-exitcode","99","--tool",job["gate"],*command]
    return command


def sanitizer_ok(stdout, stderr):
    lines=(stdout+"\n"+stderr).splitlines()
    return any(line.strip() in ("========= ERROR SUMMARY: 0 errors",
                               "========= RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)") for line in lines)


REPAIR_FILES={"tools/lp_state_device.py","tests/integration/test_lp_state_device.py",
              "docs/decisions/ADR-0036-full-expansion-state-admission.md","state/active-task.md"}


def archive_sources(path):
    with tarfile.open(path) as archive:
        members=archive.getmembers()
        if any(not m.isfile() or Path(m.name).is_absolute() or ".." in Path(m.name).parts for m in members):
            raise ValueError("repair source archive inventory")
        names=[m.name for m in members]
        if names!=sorted(set(names)):raise ValueError("repair source archive order")
        return {m.name:archive.extractfile(m).read() for m in members}


def verify_continuation():
    directory=OUTPUT/"verification-repair"; record=read_json(directory/"receipt.json")
    for name,digest in record["files"].items():
        if name not in ("source.tar","execution.json") or file_hash(directory/name)!=digest:
            raise ValueError("verification repair archive hash")
    if set(record["files"])!={"source.tar","execution.json"}:raise ValueError("repair inventory")
    original=archive_sources(OUTPUT/"frozen/source.tar"); revised=archive_sources(directory/"source.tar")
    changed=sorted(k for k in original.keys()|revised.keys() if original.get(k)!=revised.get(k))
    if not changed or not set(changed)<=REPAIR_FILES or changed!=record["changed_files"]:
        raise ValueError("repair changed execution sources")
    hasher=hashlib.sha256()
    for name,data in revised.items():hasher.update(name.encode()+b"\0"+data+b"\0")
    execution=read_json(directory/"execution.json"); frozen=read_json(OUTPUT/"frozen/execution.json")
    if hasher.hexdigest()!=execution["source_tree_sha256"] or record["native_gate"]!=dict(native=True,source_tree_sha256=hasher.hexdigest()) or execution["source_archive_sha256"]!=record["files"]["source.tar"]:
        raise ValueError("repair source/native binding")
    if record["original_freeze_sha256"]!=file_hash(OUTPUT/"frozen/freeze.json") or any(execution[k]!=frozen[k] for k in ("binary_sha256","code_object_sha256","device","highs_library_sha256")):
        raise ValueError("repair changed execution identity")
    return hasher.hexdigest()


def result_for(job):
    key=job["id"]; raw=OUTPUT/(key+".result.json"); reviewed=OUTPUT/(key+".reviewed-result.json")
    if not reviewed.exists():return read_json(raw)
    record=read_json(reviewed)
    expected={key+suffix for suffix in (".result.json",".worker.json",".endpoint.json",".stdout",".stderr",".request.json",".supervisor.json")}
    if set(record["files"])!=expected or any(file_hash(OUTPUT/name)!=digest for name,digest in record["files"].items()):
        raise ValueError("reviewed sanitizer receipt binding")
    if record["verification_source_sha256"]!=verify_continuation():raise ValueError("reviewed verifier identity")
    original=read_json(raw); result=record["result"]
    if original["status"]!="failed" or original["error"]!="sanitizer success receipt missing" or result!={**original,"status":"passed","error":None}:
        raise ValueError("reviewed sanitizer classification differs")
    return result


def repair_receipt():
    from benchmark_lp import source_identity,prepare_execution,provenance
    frozen=OUTPUT/"frozen"; verify_freeze(frozen)
    gate=read_json(ROOT/"target/lp-native-gate.json")
    if gate!=dict(native=True,source_tree_sha256=source_identity()):raise ValueError("exact-source repair gate required")
    job=roster()[2];key=job["id"];raw=read_json(OUTPUT/(key+".result.json"))
    worker=read_json(OUTPUT/(key+".worker.json"))
    if raw["status"]!="failed" or raw["error"]!="sanitizer success receipt missing" or worker["reason"]!="completed" or worker["returncode"]!=0:
        raise ValueError("not the retained receipt-only failure")
    numerical=verify_endpoint(read_json(OUTPUT/(key+".endpoint.json")),job,request_for(job,frozen),read_json(frozen/"corpus.json"))
    if numerical!=raw["numerical_sha256"] or not sanitizer_ok((OUTPUT/(key+".stdout")).read_text(),(OUTPUT/(key+".stderr")).read_text()):
        raise ValueError("retained sanitizer evidence does not pass")
    directory=OUTPUT/"verification-repair";directory.mkdir(exist_ok=False)
    base=provenance(frozen/"lp_state_probe",DEVICE)
    base.update(code_object_sha256=file_hash(frozen/"device.cubin"),build_profile="release")
    prepare_execution(directory,base)
    old=archive_sources(frozen/"source.tar");new=archive_sources(directory/"source.tar")
    write_json(directory/"receipt.json",dict(native_gate=gate,original_freeze_sha256=file_hash(frozen/"freeze.json"),
        changed_files=sorted(k for k in old.keys()|new.keys() if old.get(k)!=new.get(k)),
        files={name:file_hash(directory/name) for name in ("source.tar","execution.json")}))
    verified=verify_continuation()
    names=[key+suffix for suffix in (".result.json",".worker.json",".endpoint.json",".stdout",".stderr",".request.json",".supervisor.json")]
    write_json(OUTPUT/(key+".reviewed-result.json"),dict(verification_source_sha256=verified,
        files={name:file_hash(OUTPUT/name) for name in names},result={**raw,"status":"passed","error":None}))
    result_for(job)
    print("retained memcheck receipt reclassified; no execution repeated")


def run_jobs():
    from benchmark_lp import source_identity
    frozen=OUTPUT/"frozen"; identity=verify_freeze(frozen)
    admitted=verify_continuation() if (OUTPUT/"verification-repair/receipt.json").exists() else identity["source_tree_sha256"]
    if source_identity()!=admitted or read_json(ROOT/"target/lp-native-gate.json")!=dict(native=True,source_tree_sha256=admitted):
        raise ValueError("exact frozen source required before device jobs")
    data=read_json(frozen/"corpus.json")
    with ledger_for(protocol()) as ledger:
        for job in roster():
            key=job["id"]; result_path=OUTPUT/(key+".result.json")
            if key in ledger.attempted():
                if not result_path.exists() or result_for(job).get("status")!="passed":
                    raise ValueError("attempt failed/interrupted; no retry: "+key)
                continue
            # Later phases cannot run past a failed earlier admission job.
            for prior in roster()[:roster().index(job)]:
                if result_for(prior)["status"]!="passed":
                    raise ValueError("previous admission/attempt failed")
            request=OUTPUT/(key+".request.json"); endpoint=OUTPUT/(key+".endpoint.json")
            payload=request_for(job,frozen)
            if request.exists() or endpoint.exists(): raise ValueError("existing device request")
            write_json(request,payload)
            command=command_for(job,frozen,request,endpoint)
            supervised=dict(schema_version=2,gpu_admission_seconds=3,command=command,directory=str(OUTPUT),prefix=key,
                solve_seconds=job["seconds"],cleanup_seconds=2,host_rss_bytes=8589934592,poll_ms=10,output_bytes=33554432)
            worker_request=OUTPUT/(key+".supervisor.json"); write_json(worker_request,supervised)
            reservation=ledger.reserve(key,job["seconds"]+6,phase=protocol()["categories"][job["category"]]["phase"])
            print("starting "+key,flush=True)
            process=subprocess.Popen(["bash",str(ROOT/"tools/gpu_job.sh"),DEVICE,"--lp-study-request",str(worker_request)],pass_fds=(ledger.lock.fileno(),))
            try:
                process.wait(timeout=job["seconds"]+310)
            except (subprocess.TimeoutExpired,KeyboardInterrupt):
                process.terminate()
                try: process.wait(timeout=3)
                except subprocess.TimeoutExpired: process.kill();process.wait()
            worker_path=OUTPUT/(key+".worker.json")
            worker=read_json(worker_path) if worker_path.exists() else None
            charged=worker["leased_ns"] if worker else reservation["reserved_ns"]
            ledger.settle(reservation,charged)
            result=dict(job=job,status="failed",charged_ns=charged,numerical_sha256=None,error=None)
            try:
                if not worker or process.returncode or worker["reason"]!="completed" or worker["returncode"]!=0 or charged>reservation["reserved_ns"]:
                    raise ValueError("supervised device execution failed")
                result["numerical_sha256"]=verify_endpoint(read_json(endpoint),job,payload,data)
                if job["gate"] in ("memcheck","racecheck","initcheck","synccheck"):
                    if not sanitizer_ok((OUTPUT/(key+".stdout")).read_text(),(OUTPUT/(key+".stderr")).read_text()):
                        raise ValueError("sanitizer success receipt missing")
                result["status"]="passed"
            except (OSError,ValueError,KeyError,TypeError) as error:
                result["error"]=str(error)
            write_json(result_path,result); write_json(OUTPUT/"budget.json",receipt(ledger))
            shutil.copyfile(ledger.path,OUTPUT/"ledger.jsonl")
            print(key+": "+result["status"]+f"; charged {charged/NS:.9f} s",flush=True)
            if result["status"]!="passed":raise ValueError(result["error"])


def verify_budget(path,budget):
    from lp_protocol import strict_loads, validate
    content=path.read_bytes()
    if not content.endswith(b"\n"):raise ValueError("device ledger is torn")
    prefix=b"".join(content.splitlines(keepends=True)[:PREFIX_EVENTS])
    if len(prefix.splitlines())!=PREFIX_EVENTS or hashlib.sha256(prefix).hexdigest()!=PREFIX_HASH:
        raise ValueError("device ledger prefix differs")
    rows=[strict_loads(line) for line in content.splitlines()]
    campaign=rows[0]["campaign_sha256"];pending={};seen=set()
    for index,event in enumerate(rows):
        validate("ledger",event)
        if event["sequence"]!=index or event["campaign_sha256"]!=campaign:raise ValueError("device ledger sequence/identity differs")
        key=event["reservation_id"]
        if event["kind"]=="reserve":
            if key in seen or event["charged_ns"]!=0:raise ValueError("device ledger duplicate reservation")
            pending[key]=event;seen.add(key)
        else:
            reserved=pending.pop(key,None)
            if reserved is None or any(event[k]!=reserved[k] for k in ("trial_id","resource","phase","reserved_ns")):
                raise ValueError("device ledger unmatched settlement")
            if event["kind"]=="recover" and event["charged_ns"]!=event["reserved_ns"]:raise ValueError("device ledger recovery charge")
    if pending:raise ValueError("device ledger pending reservation")
    categories={c:sum(e["charged_ns"] for e in rows if e["resource"]=="gpu" and e["trial_id"].startswith(ID+"-"+c+"-")) for c in protocol()["categories"]}
    total=sum(e["charged_ns"] for e in rows if e["resource"]=="gpu")
    expected=dict(categories_ns=categories,cpu_ns=0,cumulative_ns=total,ledger_sha256=file_hash(path),events=len(rows))
    if admission.encoded(budget)!=admission.encoded(expected):raise ValueError("device budget receipt differs")
    if total>protocol()["cumulative_gpu_ns"] or sum(categories.values())>protocol()["combined_cap_seconds"]*NS:raise ValueError("device cumulative/task budget exceeded")
    for category,rule in protocol()["categories"].items():
        if categories[category]>rule["seconds"]*NS:raise ValueError("device category budget exceeded")
    for phase,seconds in protocol()["phase_gpu_seconds"].items():
        if sum(e["charged_ns"] for e in rows if e["resource"]=="gpu" and e["phase"]==phase)>seconds*NS:raise ValueError("device phase budget exceeded")
    return rows


def report():
    frozen=OUTPUT/"frozen"; identity=verify_freeze(frozen)
    data=read_json(frozen/"corpus.json"); groups=defaultdict(list); attempts=[]; repeat=[]
    budget=read_json(OUTPUT/"budget.json")
    rows=verify_budget(OUTPUT/"ledger.jsonl",budget)
    for job in roster():
        key=job["id"]; result_path=OUTPUT/(key+".result.json")
        events=[e for e in rows if e["trial_id"]==key]
        if not result_path.exists():
            attempts.append(dict(id=key,status="interrupted" if events else "unexecuted")); continue
        result=result_for(job); request=read_json(OUTPUT/(key+".request.json"))
        supervised=read_json(OUTPUT/(key+".supervisor.json"))
        worker_path=OUTPUT/(key+".worker.json")
        worker=read_json(worker_path) if worker_path.exists() else None
        endpoint_path=OUTPUT/(key+".endpoint.json")
        if request!=request_for(job,frozen) or supervised["command"]!=command_for(job,frozen,OUTPUT/(key+".request.json"),endpoint_path) or supervised["prefix"]!=key or supervised["directory"]!=str(OUTPUT) or supervised["solve_seconds"]!=job["seconds"]:
            raise ValueError("device request/command binding differs")
        phase=protocol()["categories"][job["category"]]["phase"]
        charged=worker["leased_ns"] if worker else (job["seconds"]+6)*NS
        if len(events)!=2 or [e["kind"] for e in events]!=["reserve","settle"] or any(e["phase"]!=phase or e["resource"]!="gpu" or e["reserved_ns"]!=(job["seconds"]+6)*NS for e in events) or events[1]["charged_ns"]!=charged or result["charged_ns"]!=charged:
            raise ValueError("device ledger binding differs")
        item=dict(id=key,status=result["status"],charged_ns=result["charged_ns"],
                  worker_reason=worker["reason"] if worker else "missing_receipt",error=result["error"])
        if result["status"]=="passed":
            if not worker or worker["reason"]!="completed" or worker["returncode"]!=0 or worker["leased_ns"]>(job["seconds"]+6)*NS or worker["activity"]["device"]!=DEVICE:
                raise ValueError("device worker outcome differs")
            endpoint=read_json(endpoint_path)
            numerical=verify_endpoint(endpoint,job,request,data)
            if numerical!=result["numerical_sha256"]:raise ValueError("device numerical identity differs")
            item["numerical_sha256"]=numerical
            if job["mode"]=="check": repeat.append(numerical)
            if job["gate"] in ("memcheck","racecheck","initcheck","synccheck"):
                if not sanitizer_ok((OUTPUT/(key+".stdout")).read_text(),(OUTPUT/(key+".stderr")).read_text()):raise ValueError("sanitizer receipt missing")
            if job["mode"]=="timing":
                measured=endpoint["launches"][1]; operations=job["count"]*job["iterations"]
                item.update(launch_sync_ns=measured["launch_sync_ns"],operations=operations,
                    operations_per_second=operations*NS/measured["launch_sync_ns"],
                    chain_cycles_per_fma=measured["cycles"][0]/job["iterations"] if job["shape"]=="chain" else None,
                    upload_ns=measured["upload_ns"],download_ns=measured["download_ns"],context_ns=endpoint["context_ns"],
                    module_stream_ns=endpoint["module_stream_ns"],allocation_ns=endpoint["allocation_ns"],
                    process_work_ns=endpoint["process_work_ns"],allocated_bytes=measured["allocated_bytes"])
                groups[(job["precision"],job["pattern"],job["shape"])].append(item)
        attempts.append(item)
    if repeat and len(set(repeat))!=1:raise ValueError("fresh/sanitized device repetitions differ")
    summaries=[]
    for (precision,pattern,shape),items in sorted(groups.items()):
        summary=dict(precision=precision,pattern=pattern,shape=shape,repetitions=len(items))
        for metric in ("launch_sync_ns","operations_per_second","context_ns","module_stream_ns","allocation_ns","upload_ns","download_ns","process_work_ns","charged_ns"):
            values=[i[metric] for i in items]
            summary[metric]=dict(median=statistics.median(values),minimum=min(values),maximum=max(values))
        if shape=="chain":
            values=[i["chain_cycles_per_fma"] for i in items]
            summary["chain_cycles_per_fma"]=dict(median=statistics.median(values),minimum=min(values),maximum=max(values))
        summaries.append(summary)
    return dict(schema_version=1,identity=ID,device=DEVICE,source_tree_sha256=identity["source_tree_sha256"],
        freeze_sha256=file_hash(frozen/"freeze.json"),status="complete" if all(a["status"]=="passed" for a in attempts) else "incomplete",
        independent_cases=6170,correctness_attempts=len(repeat),repeatability_equal=bool(repeat),
        timing_attempts=sum(a["id"].startswith(ID+"-timing-") and a["status"]=="passed" for a in attempts),
        budget=budget,kernels={name:identity["kernels"][name] for name in ALLOWED},
        groups=summaries,attempts=attempts,full_controller_accepted=False,solver_performance_claim=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("action",choices=("freeze","run","report","repair-receipt"))
    p.add_argument("--cohort",choices=COHORTS,default="v2");args=p.parse_args()
    select_cohort(args.cohort)
    if args.cohort=="v1" and args.action!="report":
        raise ValueError("historical blocked cohort is verification-only")
    if args.action=="freeze":freeze()
    elif args.action=="run":run_jobs()
    elif args.action=="repair-receipt":repair_receipt()
    else:print(json.dumps(report(),sort_keys=True,indent=2))


if __name__=="__main__":main()
