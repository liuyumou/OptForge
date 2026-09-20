"""Frozen ADR-0019 precision and COPT development study; original campaign authority."""
import argparse,hashlib,os,shutil,subprocess
from pathlib import Path
from benchmark_lp import prepare_execution,provenance,recover_intents,run_trial,schedule
from benchmark_lp_tuned import require_executable,reference_identity
from lp_protocol import ROOT,Ledger,NS,campaign,checked_reference,file_hash,read_json,validate,write_json
CONFIG=ROOT/'benchmarks/configs/lp-precision-v4.json'
OUTPUT=ROOT/'artifacts/gpup5-fp32-v1'
PRIOR_EVENTS=1902
PRIOR_HASH='35b58ef0b0d58637288801bac2bdaa32b65b97b42b429debcffc615768c7c543'

def require_prior_history(path):
    prefix=b''.join(path.read_bytes().splitlines(keepends=True)[:PRIOR_EVENTS])
    if hashlib.sha256(prefix).hexdigest()!=PRIOR_HASH:raise ValueError('pre-GPUP-5 ledger prefix differs')

def protocol(path=CONFIG,materialized=True):
    value=validate('campaign',read_json(path));base,manifests=campaign(checked_reference(ROOT,value['budget_authority']),materialized)
    for key in base.keys()-{'id','schema_version','configurations','slice_gpu_seconds'}:
        if value[key]!=base[key]:raise ValueError('GPUP-5 changed frozen '+key)
    if value['cumulative_gpu_ns']!=value['prior_gpu_ns']+value['additional_gpu_seconds']*NS:raise ValueError('precision allowance differs')
    if materialized:
        checked_reference(ROOT,value['reference_binary']);checked_reference(ROOT,value['reference_code_object'])
    return value,base,manifests

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--campaign',type=Path,default=CONFIG);p.add_argument('--binary',type=Path,default=ROOT/'target/release/optimizer');p.add_argument('--output',type=Path,default=OUTPUT);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    value,base,manifests=protocol(a.campaign);jobs=list(schedule(value,manifests))
    if a.dry_run:print(len(jobs),'planned attempts; 3600 additional GPU seconds; screening phase');return
    binary=a.binary.resolve();directory=a.output.resolve();native=provenance(binary,value['device']);code=ROOT/'target/native/cuda'
    for filename,key in [('lp_pdhg_tuned.cubin','code_object_sha256'),('lp_pdhg_precision.cubin','precision_code_object_sha256'),('schedule_eval.cubin','session_code_object_sha256')]:
        if file_hash(code/filename)!=value[key]:raise ValueError('provisioned code differs: '+filename)
    copt=ROOT/'artifacts/gpup5-copt/venv/lib/python3.11/site-packages/coptpy'
    for filename,key in [('libcopt_python.so','copt_library_sha256'),('coptcore.so','copt_binding_sha256')]:
        if file_hash(copt/filename)!=value[key]:raise ValueError('COPT identity differs')
    receipt=read_json(ROOT/'target/lp-native-gate.json')
    if native['build_profile']!='release' or not receipt.get('native') or receipt.get('source_tree_sha256')!=native['source_tree_sha256']:raise ValueError('full native gate required on exact source')
    ref=reference_identity(value);require_executable(binary);require_executable(checked_reference(ROOT,value['reference_binary']))
    native.update(copt_library_sha256=None,copt_binding_sha256=None)
    old={**native,**{k:ref[k] for k in ['source_tree_sha256','binary_sha256','code_object_sha256']},'revision':subprocess.check_output(['git','rev-parse',value['reference_revision']],cwd=ROOT,text=True).strip(),'dirty':False}
    identities={}
    for c in value['configurations']:
        item=dict(old if c['binary']=='reference' else native)
        item['code_object_sha256']=value['precision_code_object_sha256'] if 'precision' in c else value['code_object_sha256'] if c['backend']=='cuda-lp-tuned' else item['code_object_sha256'] if c['binary']=='reference' else None
        if c['backend'].startswith('copt-'):item.update(copt_library_sha256=value['copt_library_sha256'],copt_binding_sha256=value['copt_binding_sha256'])
        identities[c['id']]=item
    ledger_directory=ROOT/'artifacts/lp-campaign-ledgers'/base['id'];require_prior_history(ledger_directory/'ledger.jsonl')
    with Ledger(ledger_directory,value['budget_authority']['sha256'],base['phase_gpu_seconds'],cumulative_ns=value['cumulative_gpu_ns']) as ledger:
        if read_json(ledger_directory/'output.json')['output_path']!=str(ROOT/'artifacts/gpup-baseline-v1'):raise ValueError('original output binding differs')
        if ledger.totals()<value['prior_gpu_ns']:raise ValueError('lost campaign consumption')
        prepare_execution(directory,native)
        for source in [binary,code/'lp_pdhg_tuned.cubin',code/'lp_pdhg_precision.cubin']:
            destination=directory/source.name
            if destination.exists() and file_hash(destination)!=file_hash(source):raise ValueError('archived executable differs')
            if not destination.exists():shutil.copy2(source,destination)
        frozen=directory/'campaign.json'
        if frozen.exists() and read_json(frozen)!=value:raise ValueError('resume protocol differs')
        write_json(frozen,value);write_json(directory/'configuration-executions.json',identities)
        write_json(directory/'budget-binding.json',dict(ledger_directory=str(ledger_directory.relative_to(ROOT)),prior_gpu_ns=value['prior_gpu_ns'],cumulative_gpu_ns=value['cumulative_gpu_ns'],protocol_sha256=file_hash(a.campaign)))
        write_json(directory/'solve.json',value['solve']);write_json(directory/'lp-settings.json',value['lp_settings']);recover_intents(directory,ledger.attempted())
        try:
            for job in jobs:
                if job[0] in ledger.attempted():continue
                reference=job[2]['binary']=='reference';executable=checked_reference(ROOT,value['reference_binary']) if reference else binary
                code_dir=checked_reference(ROOT,value['reference_code_object']).parent if reference else code
                run_trial(value,*job,executable,directory,ledger,identities[job[2]['id']],file_hash(a.campaign),code_directory=code_dir)
        finally:shutil.copyfile(ledger.path,directory/'ledger.jsonl')
if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as e:raise SystemExit(str(e))
