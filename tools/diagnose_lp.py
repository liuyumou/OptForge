"""ADR-0015 supplementary diagnostics; no baseline trial is modified or repeated."""
import argparse
import cProfile
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
from benchmark_lp import CAMPAIGN, prepare_execution, provenance, quiet_device, telemetry
from lp_protocol import ROOT, NS, Ledger, campaign, file_hash, read_json, validate, write_json

OUTPUT = ROOT / 'artifacts/gpup2-diagnosis-v1'
NSYS = Path('/opt/nvidia/nsight-compute/2025.3.0/host/target-linux-x64/nsys')
JOBS = [('profile-'+name, name, 50000, False) for name in ['small-4','irregular-256','irregular-2048']] + [
    (kind+'-'+name,name,200,kind=='trace') for name in ['small-4','irregular-2048'] for kind in ['short','trace']]
PRIOR_NS = 173_148_261_443


def python_cost():
    from validate_artifacts import validator
    OUTPUT.mkdir(parents=True,exist_ok=True)
    values={kind:read_json(ROOT/path) for kind,path in [
        ('ledger','examples/lp-ledger-v1.synthetic.json'),
        ('endpoint','artifacts/gpup-baseline-v1/profile-gpup-development-irregular-2048-0-cuda-lp.endpoint.json')]}
    result={}
    for kind,value in values.items():
        fresh=[]; reused=[]
        for _ in range(3):
            start=time.perf_counter_ns(); validate(kind,value);fresh.append(time.perf_counter_ns()-start)
        compiled=validator('lp-'+kind+'-v1.schema.json')
        for _ in range(3):
            start=time.perf_counter_ns();compiled.validate(value);reused.append(time.perf_counter_ns()-start)
        # Reuse is a diagnostic counterfactual only; both perform the same validation.
        wrong={**value,'unknown_diagnostic_field':True}
        for check in [lambda x:validate(kind,x),compiled.validate]:
            try:check(wrong)
            except Exception:pass
            else:raise AssertionError('unknown field was accepted')
        result[kind]={'fresh_validator_ns':fresh,'reused_validator_ns':reused}
    profile=cProfile.Profile()
    profile.runcall(validate,'ledger',values['ledger'])
    profile.dump_stats(OUTPUT/'schema.cprofile')
    write_json(OUTPUT/'python-cost.json',result)
    print(json.dumps(result,indent=2))


def gpu():
    value,_=campaign(CAMPAIGN)
    binary=ROOT/'target/release/optimizer'
    base=provenance(binary,value['device'])
    receipt=read_json(ROOT/'target/lp-native-gate.json')
    if not receipt['native'] or receipt['source_tree_sha256']!=base['source_tree_sha256']:
        raise ValueError('full native gate required on the diagnostic source tree')
    if not NSYS.is_file():raise ValueError('frozen Nsight Systems executable unavailable')
    protocol={'id':'gpup2-diagnosis-v1','adr_sha256':file_hash(ROOT/'docs/decisions/ADR-0015-lp-baseline-diagnosis.md'),
        'campaign_sha256':file_hash(CAMPAIGN),'prior_gpu_ns':PRIOR_NS,'cap_ns':120*NS,'jobs':JOBS,
        'nsys':str(NSYS),'nsys_sha256':file_hash(NSYS),
        'nsys_version':subprocess.check_output([str(NSYS),'--version'],text=True).strip()}
    directory=ROOT/'artifacts/lp-campaign-ledgers'/value['id']
    with Ledger(directory,file_hash(CAMPAIGN),value['phase_gpu_seconds'],value['slice_gpu_seconds']) as ledger:
        # The original output binding is intentionally retained. This extension
        # shares its only budget authority and uses separate diagnostic artifacts.
        original=read_json(directory/'output.json')
        if original['output_path']!=str(ROOT/'artifacts/gpup-baseline-v1'):
            raise ValueError('unexpected original campaign binding')
        prepare_execution(OUTPUT,base)
        protocol_path=OUTPUT/'diagnostic-protocol.json'
        if protocol_path.exists() and read_json(protocol_path)!=json.loads(json.dumps(protocol)):
            raise ValueError('diagnostic protocol changed across resume')
        write_json(protocol_path,protocol)
        if ledger.totals()<PRIOR_NS:raise ValueError('prior GPU consumption lost')
        try:
            for label,name,iterations,traced in JOBS:
                identity='gpup2-diagnosis-v1-'+label
                if identity in ledger.attempted():
                    print(identity+': prior attempt retained');continue
                if ledger.totals()-PRIOR_NS+13*NS>120*NS:raise ValueError('diagnostic allowance exhausted')
                quiet_device(value['device'])
                before=telemetry(value['device'])
                model=ROOT/f'artifacts/lp-inputs-v1/gpup-development-{name}.json'
                evidence=OUTPUT/(label+'.endpoint.json')
                settings={**value['lp_settings'],'iteration_limit':iterations}
                write_json(OUTPUT/(label+'.settings.json'),settings)
                write_json(OUTPUT/'solve.json',value['solve'])
                command=[str(binary),'solve','--backend','cuda-lp','--device',value['device'],
                    '--model',str(model),'--config',str(OUTPUT/'solve.json'),
                    '--lp-settings',str(OUTPUT/(label+'.settings.json')),
                    '--lp-evidence',str(evidence),'--lp-profile','true',
                    '--lp-device-memory-bytes',str(value['limits']['device_buffer_bytes'])]
                if traced:
                    command=[str(NSYS),'profile','--trace=cuda','--sample=none','--cpuctxsw=none',
                        '--cuda-event-trace=false','--stats=false','--force-overwrite=false',
                        '--export=sqlite','--output='+str(OUTPUT/label)]+command
                request={k:value['limits'][k] for k in ['solve_seconds','cleanup_seconds','host_rss_bytes','poll_ms','output_bytes']}
                request.update(command=command,directory=str(OUTPUT),prefix=label)
                request_path=OUTPUT/(label+'.request.json');write_json(request_path,request)
                intent={'id':identity,'label':label,'model_sha256':file_hash(model),
                    'settings_sha256':file_hash(OUTPUT/(label+'.settings.json')),
                    'trace':traced,'telemetry_before':before,'command':command}
                write_json(OUTPUT/(label+'.intent.json'),intent)
                reservation=ledger.reserve(identity,13)
                start=time.monotonic_ns()
                worker=subprocess.Popen(['bash',str(ROOT/'tools/gpu_job.sh'),value['device'],
                    '--lp-study-request',str(request_path)],pass_fds=(ledger.lock.fileno(),))
                try:worker.wait(timeout=318)
                except (subprocess.TimeoutExpired,KeyboardInterrupt):
                    worker.terminate()
                    try:worker.wait(timeout=3)
                    except subprocess.TimeoutExpired:worker.kill();worker.wait()
                worker_path=OUTPUT/(label+'.worker.json')
                info=read_json(worker_path) if worker_path.is_file() else None
                charge=info['leased_ns'] if info else reservation['reserved_ns']
                ledger.settle(reservation,charge)
                result={**intent,'supervisor_wall_ns':time.monotonic_ns()-start,'worker':info,
                    'charged_ns':charge,'cumulative_gpu_ns':ledger.totals(),
                    'telemetry_after':telemetry(value['device']),'endpoint_verified':False}
                if evidence.is_file():
                    endpoint=validate('endpoint',read_json(evidence))
                    checked=subprocess.run([str(binary),'lp-study','verify','--model',str(model),
                        '--evidence',str(evidence)],capture_output=True,text=True,timeout=12)
                    result['endpoint_verified']=checked.returncode==0
                    result['endpoint_sha256']=file_hash(evidence)
                    result['assessment']=endpoint['assessment']
                    result['verification_stderr']=checked.stderr[:2000]
                write_json(OUTPUT/(label+'.result.json'),result)
                print(f'{label}: {info}; verified={result["endpoint_verified"]}; cumulative GPU {ledger.totals()/NS:.6f}s',flush=True)
                if info is None or charge>reservation['reserved_ns']:raise ValueError('uncertain/overrun job retained; stop')
        finally:
            (OUTPUT/'ledger.jsonl').write_bytes(ledger.path.read_bytes())
    write_json(OUTPUT/'artifact-hashes.json',{p.name:file_hash(p) for p in sorted(OUTPUT.iterdir())
        if p.is_file() and p.name!='artifact-hashes.json'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gpu',action='store_true',help='explicitly launch the seven frozen leased diagnostics')
    args=parser.parse_args()
    if args.gpu:gpu()
    else:python_cost()
