"""Frozen GPUP-6 fresh-single policy comparisons, with legacy controls and no held-out data."""
import argparse
import shutil
from pathlib import Path
from benchmark_lp import prepare_execution, provenance, recover_intents, run_trial
from lp_protocol import ROOT, NS, checked_reference, file_hash, ordered, read_json, write_json
from lp_adaptive_budget import CONFIG, ledger_for, protocol


def jobs(value):
    manifest=read_json(checked_reference(ROOT,next(m for m in value['manifests'] if 'development' in m['path'])))
    instances={i['id']:i for i in manifest['instances']};configs={c['id']:c for c in value['configurations']}
    for block in value['blocks']:
        for name in block['instances']:
            instance=instances[name]
            for repeat in range(block['repetitions']):
                for order,config in enumerate(ordered([configs[c] for c in block['configurations']],value['order_seed'],name,repeat)):
                    key=f'{value["id"]}-study-{block["id"]}-{block["mode"]}-{name}-{repeat}-{config["id"]}'
                    yield key,instance,config,repeat,order,block['mode']


def code_images(directory):
    """Hash every discovery/execution prerequisite before opening the ledger."""
    return {name:file_hash(directory/name) for name in (
        "schedule_eval.cubin", "lp_pdhg.cubin", "lp_pdhg_tuned.cubin", "lp_pdhg_precision.cubin")}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--campaign',type=Path,default=CONFIG);p.add_argument('--binary',type=Path,default=ROOT/'target/release/optimizer');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    value=protocol(a.campaign);schedule=list(jobs(value))
    if len(schedule)!=value['planned_attempts'] or len({j[0] for j in schedule})!=len(schedule):raise ValueError('adaptive schedule count/identity differs')
    if a.dry_run:print(f'{len(schedule)} planned attempts; 5400 ablation seconds; 900 separate acceptance seconds');return
    binary=a.binary.resolve();directory=ROOT/value['output'];native=provenance(binary,value['device'])
    receipt=read_json(ROOT/'target/lp-native-gate.json')
    if native['build_profile']!='release' or not receipt.get('native') or receipt['source_tree_sha256']!=native['source_tree_sha256']:raise ValueError('exact-source release build and full native gate required')
    code=ROOT/'target/native/cuda'
    images=code_images(code)
    original=read_json(ROOT/'benchmarks/configs/lp-precision-v4.json')
    if images['lp_pdhg_precision.cubin']!=original['precision_code_object_sha256'] or images['lp_pdhg_tuned.cubin']!=original['code_object_sha256']:raise ValueError('legacy precision/tuned code object changed')
    # v4 provenance explicitly names absent optional external controls.
    native.update(copt_library_sha256=None,copt_binding_sha256=None)
    identities={}
    for c in value['configurations']:
        name='lp_pdhg_precision.cubin' if 'adaptive' in c or 'precision' in c else 'lp_pdhg_tuned.cubin' if c['backend']=='cuda-lp-tuned' else 'lp_pdhg.cubin'
        identities[c['id']]={**native,'code_object_sha256':images[name] if c['backend'].startswith('cuda-') else None}
    with ledger_for(value) as ledger:
        prepare_execution(directory,native)
        for source in [binary,*[code/name for name in images]]:
            dest=directory/source.name
            if dest.exists() and file_hash(dest)!=file_hash(source):raise ValueError('archived executable differs')
            if not dest.exists():shutil.copy2(source,dest)
        for name,data in [('campaign.json',value),('code-objects.json',images),('configuration-executions.json',identities),('solve.json',value['solve']),('lp-settings.json',value['lp_settings']),('budget-binding.json',dict(ledger_directory=str(ledger.directory.relative_to(ROOT)) if hasattr(ledger,'directory') else str(ledger.path.parent.relative_to(ROOT))))]:
            path=directory/name
            if path.exists() and read_json(path)!=data:raise ValueError('frozen adaptive input differs: '+name)
            write_json(path,data)
        recover_intents(directory,ledger.attempted())
        try:
            for job in schedule:
                if job[0] in ledger.attempted():continue
                try:run_trial(value,*job,binary,directory,ledger,identities[job[2]['id']],file_hash(a.campaign),code_directory=directory)
                except ValueError as error:
                    if 'budget exhausted' in str(error).lower():print(str(error),flush=True);break
                    raise
        finally:
            shutil.copyfile(ledger.path,directory/'ledger.jsonl')
            write_json(directory/'budget.json',dict(study_ns=ledger.usage('study'),acceptance_ns=ledger.usage('accept'),cumulative_ns=ledger.totals(),ledger_sha256=file_hash(ledger.path)))
        print('study seconds',ledger.usage('study')/NS,'acceptance',ledger.usage('accept')/NS,'cumulative',ledger.totals()/NS)

if __name__=='__main__':main()
