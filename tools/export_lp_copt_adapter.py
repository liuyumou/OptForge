"""Export reviewed SPEC-0019 tables and immutable source/resource provenance."""
import csv
import gzip
import hashlib
from pathlib import Path
import subprocess
import tarfile
from lp_copt_adapter_budget import protocol
from report_lp_copt_adapter import check_measured_source
from lp_protocol import ROOT, file_hash, read_json, write_json


def main():
    value=protocol();source=ROOT/value['output'];output=ROOT/'docs/benchmarks/data/copt-adapter';output.mkdir(parents=True,exist_ok=True)
    report=read_json(source/'report.json')
    write_json(output/'adapter-summary.json',{k:report[k] for k in ['id','planned','attempted','verified','certified_timings','certified_profiles','groups','ratios','equivalence','acceptance','budget','limitations']})
    write_json(output/'adapter-profiles.json',report['profiles'])
    with (output/'adapter-trials.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(report['rows'][0]),lineterminator='\n');writer.writeheader();writer.writerows(report['rows'])
    (output/'adapter-analysis.json.gz').write_bytes(gzip.compress((source/'report.json').read_bytes(),mtime=0))
    measured, corrected = check_measured_source(source)
    old=subprocess.check_output(['git','ls-tree','-r','--name-only',value['baseline_revision']],cwd=ROOT,text=True).splitlines()
    preserved=[n for n in old if n.startswith(('crates/','cuda/','tools/','schemas/','benchmarks/','docs/decisions/')) or n in ['Cargo.toml','Cargo.lock']]
    for n in preserved:
        if (ROOT/n).read_bytes()!=subprocess.check_output(['git','show',value['baseline_revision']+':'+n],cwd=ROOT):raise ValueError('historical code/authority changed: '+n)
    ledger=(source/'ledger.jsonl').read_bytes();prefix=b''.join(ledger.splitlines(keepends=True)[:value['prior_events']])
    if hashlib.sha256(prefix).hexdigest()!=value['prior_ledger_sha256'] or file_hash(source/'ledger.jsonl')!=report['budget']['ledger_sha256']:raise ValueError('ledger prefix differs')
    write_json(output/'adapter-source-ledger-audit.json',dict(status='passed',measured_files=measured,review_corrected_paths=corrected,unchanged_measured_files=len(measured)-len(corrected),review_corrections_sha256=file_hash(output/'adapter-review-corrections.json') if corrected else None,preserved_files=preserved,prior_events=value['prior_events'],prior_ledger_sha256=value['prior_ledger_sha256'],ledger_sha256=report['budget']['ledger_sha256'],events=len(ledger.splitlines())))
    cpu=[dict(path=str(p.relative_to(ROOT)),sha256=file_hash(p),**read_json(p)) for p in sorted((ROOT/value['acceptance_output']).glob('*.cpu.json'))]
    write_json(output/'adapter-resources.json',dict(gpu=report['budget'],cpu_seconds=sum(r['cpu_seconds'] for r in cpu),cpu_cap_seconds=value['cpu_cap_seconds'],cpu_receipts=cpu,note='Metered child CPU; small editing/catalog operations excluded. Ledger CPU reservations are separately visible.'))
    catalog=[]
    for name in [value['baseline_output'],value['output'],value['acceptance_output']]:
        for p in sorted((ROOT/name).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:catalog.append(dict(path=str(p.relative_to(ROOT)),sha256=file_hash(p),bytes=p.stat().st_size))
    for name in ['identity.json','wheels.json']:
        p=ROOT/'artifacts/gpup-copt-adapter-env'/name;catalog.append(dict(path=str(p.relative_to(ROOT)),sha256=file_hash(p),bytes=p.stat().st_size))
    write_json(output/'adapter-provenance.json',dict(schema_version=1,source_report=dict(path=str((source/'report.json').relative_to(ROOT)),sha256=file_hash(source/'report.json')),artifacts=catalog))
    print('Exported',len(catalog),'references;',len(measured),'measured files ('+str(len(corrected))+' declared CPU review corrections) and',len(preserved),'historical authority files unchanged')


if __name__=='__main__':main()
