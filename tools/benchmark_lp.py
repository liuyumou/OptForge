"""Bounded LP-only baseline campaign. See ADR-0014; this is not the C10 runner."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from lp_protocol import (ROOT, NS, Ledger, campaign, checked_reference, digest, encoded,
                         file_hash, ordered, read_json, validate, write_json)

CAMPAIGN=ROOT/'benchmarks/configs/lp-campaign-v1.json'

def command_text(args, timeout=10):
    try:
        run=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=timeout,check=True)
        return run.stdout.strip() or 'unavailable: empty output'
    except (OSError,subprocess.SubprocessError) as error:
        return 'unavailable: '+str(error)

def source_identity():
    files=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).split(b'\0')
    pieces=[]
    for name in sorted(set(files)):
        if not name: continue
        path=ROOT/os.fsdecode(name)
        pieces.extend([name,b'\0',path.read_bytes() if path.is_file() else b'<absent>',b'\0'])
    return digest(b''.join(pieces))

def telemetry(device):
    return command_text(['nvidia-smi','--id='+device,
        '--query-gpu=uuid,name,driver_version,temperature.gpu,power.draw,clocks.sm,memory.used,utilization.gpu',
        '--format=csv,noheader,nounits'],3)

def quiet_device(device):
    from lp_activity import wait_quiet
    return wait_quiet(device)


def provenance(binary, device):
    code=Path(os.environ.get('AI_OPTIMIZER_CUDA_DIR',ROOT/'target/native/cuda'))/'lp_pdhg.cubin'
    native=ROOT/'target/native/highs-1.11.0/install/lib/libhighs.a'
    if not native.is_file(): raise ValueError('pinned native HiGHS archive is required')
    return {'revision':command_text(['git','rev-parse','HEAD']),
        'dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)),
        'source_tree_sha256':source_identity(),'binary_sha256':file_hash(binary),
        'code_object_sha256':file_hash(code) if code.is_file() else None,
        'highs_library_sha256':file_hash(native),'rustc':command_text(['rustc','--version']),
        'cargo':command_text(['cargo','--version']),'os':command_text(['uname','-sr']),
        'cpu':command_text(['lscpu']), 'cpu_affinity':[min(os.sched_getaffinity(0))],
        'build_profile':'release' if binary.parent.name=='release' else 'debug',
        'device':device,'telemetry_before':'unavailable: not sampled yet',
        'telemetry_after':'unavailable: not sampled yet'}

def schedule(value, manifests):
    selected=next(m for m in manifests if m['partition']==value['partition'])
    for mode,count in [('timing',value['repetitions']),('profile',value['profile_repetitions'])]:
        for instance in selected['instances']:
            for repetition in range(count):
                for order,configuration in enumerate(ordered(value['configurations'],value['order_seed'],instance['id'],repetition)):
                    identity=f'{mode}-{instance["id"]}-{repetition}-{configuration["id"]}'
                    yield identity,instance,configuration,repetition,order,mode

def reference(directory,path):
    path=Path(path)
    return {'path':str(path.relative_to(directory)),'sha256':file_hash(path)} if path.is_file() else None

def recover_intents(directory, attempts):
    for intent in directory.glob('*.intent.json'):
        trial=read_json(intent)
        if trial['id'] not in attempts:continue
        destination=directory/(trial['id']+'.trial.json')
        if destination.exists(): continue
        trial['status']='process_failure'; trial['error']='interrupted coordinator; ledger preserves actual or conservative crash charge; partial files retained'
        validate('trial',trial); write_json(destination,trial)

def run_trial(value, identity, instance, configuration, repetition, order, mode,
              binary, directory, ledger, base_provenance):
    gpu=configuration['backend']=='cuda-lp'
    if gpu:
        from lp_activity import ActivityPause
        try:
            activity = quiet_device(value['device'])
        except ActivityPause as error:
            write_json(directory/(identity+'.activity.json'), error.report)
            raise
        write_json(directory/(identity+'.activity.json'), activity)
    before=telemetry(value['device'])
    model=checked_reference(ROOT,instance['model'])
    evidence=directory/(identity+'.endpoint.json')
    config_hash=digest(encoded({'configuration':configuration,'solve':value['solve'],
                               'lp_settings':value['lp_settings'] if configuration['backend']!='highs' else None}))
    trial={'schema_version':1,'id':identity,'campaign_sha256':ledger.campaign_hash,
        'instance_id':instance['id'],'model_sha256':instance['model']['sha256'],
        'config_id':configuration['id'],'config_sha256':config_hash,
        'block':f'{instance["id"]}:{repetition}','repetition':repetition,'order':order,'mode':mode,
        'requested_backend':configuration['backend'],'executed_backend':None,'status':'process_failure',
        'endpoint_class':None,'endpoint':None,'worker':None,'stdout':None,'stderr':None,
        'elapsed_ns':None,'queue_ns':None,'leased_ns':None,'verification_ns':None,'peak_rss_bytes':None,
        'memory_method':'unavailable: worker not completed','limits':value['limits'],
        'provenance':{**base_provenance,'telemetry_before':before},'error':'unfinished trial intent'}
    validate('trial',trial)
    write_json(directory/(identity+'.intent.json'),trial)
    args=[str(binary),'solve','--model',str(model),'--config',str(directory/'solve.json'),
          '--backend',configuration['backend'],'--lp-evidence',str(evidence),
          '--lp-profile','true' if mode=='profile' else 'false',
          '--lp-device-memory-bytes',str(value['limits']['device_buffer_bytes'])]
    if configuration['backend']!='highs': args+=['--lp-settings',str(directory/'lp-settings.json')]
    if gpu: args+=['--device',value['device']]
    request={k:value['limits'][k] for k in ['solve_seconds','cleanup_seconds','host_rss_bytes','poll_ms','output_bytes']}
    request.update(command=args,directory=str(directory),prefix=identity)
    if gpu: request.update(schema_version=2, gpu_admission_seconds=3)
    request_path=directory/(identity+'.request.json');write_json(request_path,request)
    # One second covers the bounded supervisor's setup/lease teardown overhead.
    reservation=ledger.reserve(identity,value['limits']['solve_seconds']+value['limits']['cleanup_seconds']+(4 if gpu else 1),
                               resource='gpu' if gpu else 'cpu')
    worker_args=['bash',str(ROOT/'tools/gpu_job.sh'),value['device'],'--lp-study-request',str(request_path)] if gpu else [sys.executable,str(ROOT/'tools/lp_supervise.py'),'--request',str(request_path)]
    worker=subprocess.Popen(worker_args,pass_fds=(ledger.lock.fileno(),))
    try:
        worker.wait(timeout=322 if gpu else 18)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        worker.send_signal(signal.SIGTERM)
        try: worker.wait(timeout=3)
        except subprocess.TimeoutExpired: worker.kill();worker.wait()
    worker_path=directory/(identity+'.worker.json')
    info=read_json(worker_path) if worker_path.is_file() else None
    if info is None:
        ledger.settle(reservation,reservation['reserved_ns'])
        trial['error']='worker did not return a report; full reservation charged'
    else:
        charge=info['leased_ns'] if gpu else info['elapsed_ns']
        ledger.settle(reservation,charge)
        trial.update(status='process_failure' if info['reason']=='activity_blocked' else info['reason'],elapsed_ns=info['elapsed_ns'],queue_ns=info['queue_ns'],
                     leased_ns=info['leased_ns'],peak_rss_bytes=info['peak_rss_bytes'],memory_method=info['memory_method'],error=None)
        if worker.returncode!=0:
            trial.update(status='process_failure',error=f'worker exit {worker.returncode}')
        if charge>reservation['reserved_ns']:
            trial['error']='worker exceeded reserved bound; fully charged; campaign must stop'
    trial['worker']=reference(directory,worker_path)
    for role in ['stdout','stderr']:trial[role]=reference(directory,directory/(identity+'.'+role))
    verification=time.monotonic_ns()
    if evidence.exists():
        trial['endpoint']=reference(directory,evidence)
        try:
            endpoint=validate('endpoint',read_json(evidence))
            if endpoint['model_sha256']!=instance['model']['sha256'] or endpoint['requested_backend']!=configuration['backend']:
                raise ValueError('endpoint model/backend differs from scheduled trial')
            if endpoint['record']['options']!=value['solve']:
                raise ValueError('endpoint solve configuration differs')
            if endpoint['record']['backend']!='highs' and endpoint['record'].get('lp_settings')!=value['lp_settings']:
                raise ValueError('endpoint LP settings differ')
            verified=subprocess.run([str(binary),'lp-study','verify','--model',str(model),'--evidence',str(evidence)],
                                    capture_output=True,text=True,timeout=12)
            if verified.returncode:raise ValueError('independent verifier rejected endpoint: '+verified.stderr[:1000])
            trial['executed_backend']=endpoint['record']['backend'];trial['endpoint_class']=endpoint['assessment']['classification']
        except Exception as error:
            # Preserve a malformed artifact and its hash; it cannot become a success.
            trial.update(status='invalid_evidence',error=str(error)[:2000])
    elif trial['status']=='completed':trial.update(status='missing_evidence',error='solve produced no complete evidence')
    trial['verification_ns']=time.monotonic_ns()-verification
    trial['provenance']['telemetry_after']=telemetry(value['device'])
    validate('trial',trial);write_json(directory/(identity+'.trial.json'),trial)
    print(f'{identity}: {trial["status"]}/{trial["endpoint_class"]}; GPU charged {ledger.totals()/NS:.3f}s',flush=True)
    if info is None or (info and (info['leased_ns'] if gpu else info['elapsed_ns'])>reservation['reserved_ns']):
        raise ValueError('uncertain/overrun worker; stop after preserving trial')
    if info and info['reason'] == 'activity_blocked':
        raise ValueError('GPU activity appeared under lease; blocked attempt retained; pause study')
    return trial

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,default=CAMPAIGN)
    parser.add_argument('--binary',type=Path,default=ROOT/'target/release/optimizer')
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/gpup-baseline-v1')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    value,manifests=campaign(args.campaign)
    jobs=list(schedule(value,manifests))
    if args.dry_run:
        print(f'{len(jobs)} planned trials; {sum(j[2]["backend"]=="cuda-lp" for j in jobs)} GPU jobs; 900s slice cap');return
    binary=args.binary.resolve();directory=args.output.resolve()
    if not binary.is_file():raise ValueError('build the release optimizer first')
    base=provenance(binary,value['device'])
    receipt_path=ROOT/'target/lp-native-gate.json'
    receipt=read_json(receipt_path) if receipt_path.is_file() else {}
    if receipt.get('native') is not True or receipt.get('source_tree_sha256')!=base['source_tree_sha256']:
        raise ValueError('run the full native tools/check.sh on this source tree before study execution')
    ledger_directory=ROOT/'artifacts/lp-campaign-ledgers'/value['id']
    with Ledger(ledger_directory,file_hash(args.campaign),value['phase_gpu_seconds'],value['slice_gpu_seconds']) as ledger:
        ledger.bind_output(directory)
        prepare_execution(directory,base)
        write_json(directory/'budget-binding.json',{'ledger_directory':str(ledger_directory.relative_to(ROOT))})
        recover_intents(directory,ledger.attempted())
        write_json(directory/'solve.json',value['solve']);write_json(directory/'lp-settings.json',value['lp_settings'])
        try:
            for job in jobs:
                if job[0] in ledger.attempted():continue
                run_trial(value,*job,binary,directory,ledger,base)
        finally:
            # A portable evidence snapshot; the canonical ledger remains the
            # only mutable budget authority, independent of --output.
            if ledger.path.exists():
                import shutil
                shutil.copyfile(ledger.path,directory/'ledger.jsonl')
    print('Study execution complete. Run tools/lp_report.py to verify and report artifacts.')

def prepare_execution(directory, base):
    # Freeze executable/source identities across resume, while allowing recorded
    # thermal observations to change. Archive the exact dirty source for replay.
    directory.mkdir(parents=True,exist_ok=True)
    identity_keys=['source_tree_sha256','binary_sha256','code_object_sha256','highs_library_sha256','device','cpu_affinity','build_profile']
    execution_path=directory/'execution.json'
    if execution_path.exists():
        previous=read_json(execution_path)
        if any(previous[k]!=base[k] for k in identity_keys):
            raise ValueError('resume source/binary/device identity differs; use a recorded protocol revision')
    else:
        import io, tarfile
        source_files=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).split(b'\0')
        with tarfile.open(directory/'source.tar','w') as archive:
            for name in sorted(set(source_files)):
                if not name:continue
                source=ROOT/os.fsdecode(name)
                if not source.is_file():continue
                content=source.read_bytes(); item=tarfile.TarInfo(os.fsdecode(name));item.size=len(content);item.mode=0o644
                archive.addfile(item,io.BytesIO(content))
        from validate_artifacts import schema_snapshot
        write_json(execution_path,{**base,'source_archive_sha256':file_hash(directory/'source.tar'),
                                   'schema_snapshot_sha256':schema_snapshot().sha256})

if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as error:raise SystemExit(str(error))
