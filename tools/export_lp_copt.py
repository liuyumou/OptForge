"""Publish compact, hash-bound analysis data without copying raw solver binaries."""
import argparse,csv,gzip,json
from collections import Counter
from pathlib import Path
from lp_protocol import checked_reference,file_hash,read_json,write_json
from lp_cost import validate_profile
from report_lp_copt import check_worker,check_collector_envelope


def export(directory,report_path,output):
    output.mkdir(parents=True,exist_ok=True)
    report=read_json(report_path);resources=[];audit=[];blocks=Counter()
    verified={v['trial']:v for v in report['verification']['receipts']}
    for path in sorted(directory.glob('*.trial.json')):
        trial=read_json(path);worker=read_json(checked_reference(directory,trial['worker'])) if trial['worker'] else {}
        if worker:check_worker(trial,worker)
        if trial['cost']:
            cost=read_json(checked_reference(directory,trial['cost']))
            for observation in cost['observations']:
                raw=read_json(checked_reference(directory,observation['artifact']))
                validate_profile(raw);check_collector_envelope(raw,observation['process'],trial['elapsed_ns'])
        verification=verified.get(trial['id'],{})
        resources.append({k:trial[k] for k in ['id','mode','instance_id','config_id','status','elapsed_ns','queue_ns','leased_ns','peak_rss_bytes','memory_method','verification_ns']}|
            dict(returncode=worker.get('returncode'),reason=worker.get('reason'),final_verification_ns=verification.get('elapsed_ns'),certified=verification.get('certified_latency_eligible',False)))
        audit.append(dict(trial=trial['id'],trial_sha256=file_hash(path),worker_sha256=trial['worker']['sha256'] if trial['worker'] else None))
        blocks[trial['mode']]+=1
    with (output/'copt-resources.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,lineterminator='\n',fieldnames=list(resources[0]));w.writeheader();w.writerows(resources)
    write_json(directory/'final-metadata-audit.json',dict(report_sha256=file_hash(report_path),tools={name:file_hash(Path(__file__).parent/name) for name in ['export_lp_copt.py','report_lp_copt.py','lp_cost.py']},checked=len(audit),trials=audit))
    # The full independently verified analysis retains every scope, native report,
    # per-rung count, uncertainty interval and missing observation. Deterministic
    # compression bounds repository size; it does not alter the JSON payload.
    (output/'copt-analysis.json.gz').write_bytes(gzip.compress(report_path.read_bytes(),mtime=0))
    for name,key in [('copt-overhead','instrumentation_overhead'),('copt-equivalence','observed_profile_equivalence'),('copt-trace-overhead','trace_overhead')]:
        write_json(output/(name+'.json'),dict(report_sha256=file_hash(report_path),observations=report[key]))
    for source,target in [('report.trials.csv','copt-trials.csv'),('report.costs.csv','copt-scopes.csv')]:
        with (directory/source).open(newline='') as src,(output/target).open('w',newline='') as dst:
            csv.writer(dst,lineterminator='\n').writerows(csv.reader(src))
    write_json(output/'copt-summary.json',{k:report[k] for k in ['id','status','planned','attempted','verified_endpoints','certified','initial_certified','outcomes','budget','limitations']}|
        dict(report_sha256=file_hash(report_path),blocks=dict(blocks),primary_certified=sum(r['certified'] for r in report['rows']),initial_primary_certified=sum(r['initial_certified'] for r in report['rows'])))
    print('Published data and validated worker/collector metadata for',len(audit),'trials.')

def catalog(directory,report_path,output,acceptance):
    """Bind published aggregates to archives and retained validation receipts."""
    references=[]
    selected=[directory/name for name in ['campaign.json','execution.json','configuration-executions.json','profiler.json','code-objects.json','report.json','ledger.jsonl','partial-endpoint-catalog.json','final-metadata-audit.json']]
    selected.extend(directory.glob('trace-recovery-*.json'))
    selected.extend(directory.glob('offline-import-*.json'))
    selected.extend(directory/'final-verifier'/name for name in ['execution.json','optimizer','source.tar'])
    selected.extend(acceptance.glob('*.resource.json'))
    selected.extend(acceptance/name for name in ['implementation-acceptance.json','dual-profile-equivalence.json','frozen-integrity-before-final-verifier.json','clean-source-budget.log','clean-source-budget-final.log','native-05.log','native-06.log'])
    for path in selected:
        if path.exists():references.append(dict(path=str(path),sha256=file_hash(path),bytes=path.stat().st_size))
    resource_rows=[dict(path=str(path),**read_json(path)) for path in sorted(acceptance.glob('*.resource.json'))]
    measured=sum(row['user_seconds']+row['system_seconds'] for row in resource_rows)
    study=sum(row['user_seconds']+row['system_seconds'] for row in resource_rows if 'study-run' in row['path'])
    write_json(output/'copt-provenance.json',dict(schema_version=1,id='gpup-copt-comparison-v1',
        report_sha256=file_hash(report_path),retained=references,
        measured=read_json(directory/'execution.json'),configuration_executions=read_json(directory/'configuration-executions.json'),
        final_verifier=read_json(directory/'final-verifier'/'execution.json'),profiler=read_json(directory/'profiler.json'),
        code_objects=read_json(directory/'code-objects.json'),initial_implementation_acceptance=read_json(acceptance/'implementation-acceptance.json'),
        final_native_gate=next((read_json(acceptance/name) for name in ['native-06.resource.json','native-05.resource.json'] if (acceptance/name).exists()),None),
        cpu_resources=resource_rows,measured_cpu_seconds=measured,study_cpu_seconds=study,other_timed_cpu_seconds=measured-study,
        resource_limitation='Timed child user+system CPU only; includes retained failed attempts. Small development commands were not completely sampled. GPU leases and CPU-worker wall are separate report observations.',
        published=[dict(path=path.name,sha256=file_hash(path),bytes=path.stat().st_size) for path in sorted(output.iterdir()) if path.is_file() and path.name!='copt-provenance.json']))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--acceptance',type=Path);p.add_argument('--catalog-only',action='store_true');a=p.parse_args()
    if not a.catalog_only:export(a.directory,a.report,a.output)
    if a.acceptance:catalog(a.directory,a.report,a.output,a.acceptance)
