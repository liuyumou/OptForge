"""Frozen ADR-0017 FP64 execution ablations using the original campaign ledger."""
import argparse,hashlib,os,shutil,subprocess,tarfile
from pathlib import Path
from benchmark_lp import prepare_execution,provenance,recover_intents,run_trial,schedule
from lp_protocol import ROOT,NS,Ledger,campaign,checked_reference,file_hash,read_json,validate,write_json
CONFIG=ROOT/'benchmarks/configs/lp-tuned-v3.json'
OUTPUT=ROOT/'artifacts/gpup4-tuned-fp64-v1'
CORRECTION=ROOT/'benchmarks/configs/lp-tuned-correction-v3.json'
PRIOR_EVENTS=622
PRIOR_LEDGER_SHA256='49ea15fc24a24fcabb4e677d6a684ea8a8d0d6c5fc1d1a52dba7b098c827a8f3'

def require_prior_history(path):
    prefix=b''.join(path.read_bytes().splitlines(keepends=True)[:PRIOR_EVENTS])
    if hashlib.sha256(prefix).hexdigest()!=PRIOR_LEDGER_SHA256:
        raise ValueError('pre-GPUP-4 ledger history differs')

def require_executable(path):
    if not path.is_file() or not os.access(path,os.X_OK):
        raise ValueError('study executable is not executable: '+str(path))

def protocol(path=CONFIG,materialized=True):
    value=validate('campaign',read_json(path))
    baseline,manifests=campaign(checked_reference(ROOT,value['budget_authority']),materialized)
    for key in baseline.keys()-{'id','schema_version','configurations'}:
        if value[key]!=baseline[key]:raise ValueError('tuned study changed frozen '+key)
    if materialized:
        checked_reference(ROOT,value['reference_binary']);checked_reference(ROOT,value['reference_code_object'])
    if value['id']=='gpup4-tuned-fp64-correction-v1':
        original=read_json(CONFIG)
        if {**value,'id':original['id']}!=original:
            raise ValueError('correction must preserve the original study protocol')
    if value['cumulative_gpu_ns']!=value['prior_gpu_ns']+value['additional_gpu_seconds']*NS:
        raise ValueError('tuned allowance differs')
    return value,baseline,manifests

def reference_identity(value):
    directory=checked_reference(ROOT,value['reference_binary']).parent
    info=read_json(directory/'identity.json')
    archive=directory/'source.tar'
    expected=subprocess.check_output(['git','archive','--format=tar',value['reference_revision']],cwd=ROOT)
    if hashlib.sha256(expected).hexdigest()!=file_hash(archive) or file_hash(archive)!=info['source_archive_sha256']:
        raise ValueError('reference source archive differs')
    digest=hashlib.sha256()
    with tarfile.open(archive) as source:
        for item in sorted((m for m in source.getmembers() if m.isfile()),key=lambda m:m.name):
            digest.update(item.name.encode()+b'\0'+source.extractfile(item).read()+b'\0')
    if digest.hexdigest()!=info['source_tree_sha256']:raise ValueError('reference source identity differs')
    if info['binary_sha256']!=value['reference_binary']['sha256'] or info['code_object_sha256']!=value['reference_code_object']['sha256']:
        raise ValueError('reference binary/kernel identity differs')
    if file_hash(directory/'schedule_eval.cubin')!=value['session_code_object_sha256']:
        raise ValueError('reference session code object differs')
    return info

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,default=CONFIG)
    parser.add_argument('--binary',type=Path,default=ROOT/'target/release/optimizer')
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    value,baseline,manifests=protocol(args.campaign)
    jobs=list(schedule(value,manifests))
    if args.dry_run:
        print(f'{len(jobs)} attempts; {sum(j[2]["backend"]!="host-lp" for j in jobs)} GPU; 900 additional seconds');return
    binary=args.binary.resolve();directory=args.output.resolve();base=provenance(binary,value['device'])
    tuned=ROOT/'target/native/cuda/lp_pdhg_tuned.cubin'
    if file_hash(tuned)!=value['code_object_sha256']:raise ValueError('tuned code object differs')
    if file_hash(tuned.parent/'schedule_eval.cubin')!=value['session_code_object_sha256']:
        raise ValueError('session code object differs')
    base['code_object_sha256']=value['code_object_sha256']
    receipt=read_json(ROOT/'target/lp-native-gate.json')
    if base['build_profile']!='release' or not receipt.get('native') or receipt.get('source_tree_sha256')!=base['source_tree_sha256']:
        raise ValueError('full native gate required on this exact release source')
    ref=reference_identity(value)
    require_executable(binary)
    require_executable(checked_reference(ROOT,value['reference_binary']))
    old={**base,**{k:ref[k] for k in ['source_tree_sha256','binary_sha256','code_object_sha256']},
         'revision':subprocess.check_output(['git','rev-parse',value['reference_revision']],cwd=ROOT,text=True).strip(),'dirty':False}
    host={**base,'code_object_sha256':None}
    identities={c['id']:old if c['binary']=='reference' else host if c['backend']=='host-lp' else base for c in value['configurations']}
    ledger_directory=ROOT/'artifacts/lp-campaign-ledgers'/baseline['id']
    require_prior_history(ledger_directory/'ledger.jsonl')
    with Ledger(ledger_directory,value['budget_authority']['sha256'],baseline['phase_gpu_seconds'],
                cumulative_ns=value['cumulative_gpu_ns']) as ledger:
        if read_json(ledger_directory/'output.json')['output_path']!=str(ROOT/'artifacts/gpup-baseline-v1'):
            raise ValueError('original output binding changed')
        if ledger.totals()<value['prior_gpu_ns']:raise ValueError('lost prior consumption')
        prepare_execution(directory,base)
        for source,name in [(binary,'optimizer'),(tuned,'lp_pdhg_tuned.cubin')]:
            destination=directory/name
            if destination.exists() and file_hash(destination)!=file_hash(source):raise ValueError('archived executable/code object differs')
            if not destination.exists():shutil.copy2(source,destination)
        protocol_path=directory/'campaign.json'
        if protocol_path.exists() and read_json(protocol_path)!=value:raise ValueError('resume protocol differs')
        write_json(protocol_path,value)
        write_json(directory/'configuration-executions.json',identities)
        write_json(directory/'reference-execution.json',{**old,'source_archive_sha256':ref['source_archive_sha256']})
        write_json(directory/'budget-binding.json',{'ledger_directory':str(ledger_directory.relative_to(ROOT)),
            'prior_gpu_ns':value['prior_gpu_ns'],'cumulative_gpu_ns':value['cumulative_gpu_ns'],'protocol_sha256':file_hash(args.campaign)})
        write_json(directory/'solve.json',value['solve']);write_json(directory/'lp-settings.json',value['lp_settings'])
        recover_intents(directory,ledger.attempted())
        try:
            for job in jobs:
                if job[0] in ledger.attempted():continue
                reference=job[2]['binary']=='reference'
                executable=checked_reference(ROOT,value['reference_binary']) if reference else binary
                code=checked_reference(ROOT,value['reference_code_object']).parent if reference else tuned.parent
                run_trial(value,*job,executable,directory,ledger,identities[job[2]['id']],file_hash(args.campaign),code_directory=code)
        finally:
            if ledger.path.exists():shutil.copyfile(ledger.path,directory/'ledger.jsonl')
    print('Tuned execution study complete; run tools/report_lp_tuned.py')
if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as e:raise SystemExit(str(e))
