"""Frozen ADR-0016 supplementary study; the original campaign remains budget authority."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tarfile
from benchmark_lp import prepare_execution, provenance, recover_intents, run_trial, schedule
from lp_protocol import ROOT, NS, Ledger, campaign, checked_reference, file_hash, read_json, validate, write_json

CONFIG=ROOT/'benchmarks/configs/lp-matched-v2.json'
OUTPUT=ROOT/'artifacts/gpup3-matched-fp64-v1'


def protocol(path=CONFIG, materialized=True):
    value=validate('campaign',read_json(path))
    base_path=checked_reference(ROOT,value['budget_authority'])
    baseline,manifests=campaign(base_path,materialized)
    for key in baseline.keys()-{'id','schema_version','configurations'}:
        if value[key]!=baseline[key]:raise ValueError('supplementary study changed frozen '+key)
    if materialized:checked_reference(ROOT,value['reference_binary'])
    return value,baseline,manifests


def reference_source():
    archive=ROOT/'artifacts/gpup3-reference/source.tar'
    expected=__import__('subprocess').check_output(['git','rev-parse','e415918'],cwd=ROOT,text=True).strip()
    # Verify archive members against the named immutable Git tree, then hash the
    # identical name/NUL/bytes/NUL representation used by source_identity().
    import subprocess
    canonical=subprocess.check_output(['git','archive','--format=tar',expected],cwd=ROOT)
    if hashlib.sha256(canonical).hexdigest()!=file_hash(archive):raise ValueError('reference source archive differs')
    digest=hashlib.sha256()
    with tarfile.open(archive) as source:
        for item in sorted((m for m in source.getmembers() if m.isfile()),key=lambda m:m.name):
            digest.update(item.name.encode()+b'\0'+source.extractfile(item).read()+b'\0')
    return expected,digest.hexdigest(),file_hash(archive)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path,default=CONFIG)
    parser.add_argument('--binary',type=Path,default=ROOT/'target/release/optimizer')
    parser.add_argument('--output',type=Path,default=OUTPUT)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    value,baseline,manifests=protocol(args.campaign)
    jobs=list(schedule(value,manifests))
    if args.dry_run:
        print(f'{len(jobs)} attempts; {sum(j[2]["backend"]!="host-lp" for j in jobs)} GPU; 600 additional seconds')
        return
    binary=args.binary.resolve(); directory=args.output.resolve()
    base=provenance(binary,value['device']); receipt=read_json(ROOT/'target/lp-native-gate.json')
    if base['code_object_sha256']!=value['code_object_sha256']:raise ValueError('reference/current GPU code object differs')
    if base['build_profile']!='release':raise ValueError('comparative measurements require a release build')
    if not receipt.get('native') or receipt.get('source_tree_sha256')!=base['source_tree_sha256']:
        raise ValueError('full native gate required on this exact source')
    reference=checked_reference(ROOT,value['reference_binary'])
    revision,source_hash,archive_hash=reference_source()
    old={**base,'revision':revision,'dirty':False,'source_tree_sha256':source_hash,
         'binary_sha256':file_hash(reference),'build_profile':'release'}
    ledger_directory=ROOT/'artifacts/lp-campaign-ledgers'/baseline['id']
    with Ledger(ledger_directory,value['budget_authority']['sha256'],baseline['phase_gpu_seconds'],baseline['slice_gpu_seconds']) as ledger:
        if read_json(ledger_directory/'output.json')['output_path']!=str(ROOT/'artifacts/gpup-baseline-v1'):
            raise ValueError('original campaign binding changed')
        if ledger.totals()<value['prior_gpu_ns']:raise ValueError('lost prior campaign consumption')
        prepare_execution(directory,base)
        protocol_path=directory/'campaign.json'
        if protocol_path.exists() and read_json(protocol_path)!=value:raise ValueError('resume protocol differs')
        write_json(protocol_path,value)
        write_json(directory/'reference-execution.json',{**old,'source_archive_sha256':archive_hash})
        write_json(directory/'budget-binding.json',{'ledger_directory':str(ledger_directory.relative_to(ROOT))})
        write_json(directory/'solve.json',value['solve']);write_json(directory/'lp-settings.json',value['lp_settings'])
        recover_intents(directory,ledger.attempted())
        try:
            for job in jobs:
                if job[0] in ledger.attempted():continue
                if job[2]['backend']!='host-lp' and ledger.totals()-value['prior_gpu_ns']+16*NS>value['additional_gpu_seconds']*NS:
                    raise ValueError('supplementary GPU allowance exhausted; retain interim evidence')
                is_reference=job[2]['binary']=='reference'
                run_trial(value,*job,reference if is_reference else binary,directory,ledger,
                          old if is_reference else base,protocol_hash=file_hash(args.campaign))
        finally:
            if ledger.path.exists():shutil.copyfile(ledger.path,directory/'ledger.jsonl')
    print('Supplementary execution complete; run tools/report_lp_matched.py')

if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as error:raise SystemExit(str(error))
