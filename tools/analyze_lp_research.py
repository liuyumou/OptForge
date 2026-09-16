"""Verify and summarize GPUP-5B without changing historical evidence or GPU work."""
import argparse
from collections import Counter, defaultdict
import hashlib
import os
from pathlib import Path
import shutil
import statistics
import subprocess
from benchmark_lp_research import CONFIG,NSYS,jobs,label,protocol
from lp_research_budget import OUTPUT,PRIOR_EVENTS,PRIOR_HASH,PRIOR_NS
from lp_protocol import ROOT,NS,Ledger,checked_reference,file_hash,read_json,strict_loads,validate,write_json
from lp_report import paired_ratio
from analyze_lp_precision_diagnosis import iteration_execution,trace


def decode(directory):
    importer=Path('/opt/nvidia/nsight-compute/2025.3.0/host/linux-desktop-glibc_2_11_3-x64/QdstrmImporter')
    library=Path('/tmp/gpup2-nsys-libs/root/usr/lib/x86_64-linux-gnu')
    env={**os.environ,'LD_LIBRARY_PATH':str(library)}
    records=[]
    for raw in sorted(directory.glob('*.qdstrm')):
        report=raw.with_suffix('.nsys-rep');sqlite=raw.with_suffix('.sqlite')
        commands=[]
        if not report.exists():commands.append([str(importer),'--input-file',str(raw),'--output-file',str(report)])
        if not sqlite.exists():commands.append([str(NSYS),'export','--type=sqlite','--output='+str(sqlite),str(report)])
        for cmd in commands:
            result=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=60)
            records.append(dict(command=cmd,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
            if result.returncode:break
    path=directory/'offline-import.json'
    if records:write_json(path,dict(gpu_work=False,importer_sha256=file_hash(importer),library_path=str(library),libdw_sha256=file_hash(library/'libdw.so.1'),commands=records))


def historical_integrity():
    for name,index in [('gpup5-fp32-v1','artifact-index.json'),('gpup5-diagnosis-v1','artifact-hashes.json')]:
        directory=ROOT/'artifacts'/name;data=read_json(directory/index)
        items=data.items() if isinstance(data,dict) else [(r['path'],r['sha256']) for r in data]
        for path,expected in items:
            if file_hash(directory/path)!=expected:raise ValueError('historical artifact changed: '+str(directory/path))


def inspect(directory=OUTPUT):
    value,base,manifest=protocol();frozen=read_json(directory/'protocol.json');schedule=list(jobs(value,base,manifest))
    if frozen['protocol']!=value or frozen['protocol_sha256']!=file_hash(CONFIG) or frozen['jobs']!=schedule:raise ValueError('frozen schedule differs')
    if file_hash(directory/'source.tar')!=read_json(directory/'execution.json')['source_archive_sha256']:raise ValueError('source archive changed')
    for filename,expected in [('optimizer',frozen['source']['binary_sha256']),('lp_precision_research',frozen['research_binary_sha256']),('lp_pdhg_research.cubin',frozen['code_object_sha256']),('lp_pdhg_tuned.cubin',base['code_object_sha256']),('lp_pdhg_precision.cubin',base['precision_code_object_sha256'])]:
        if file_hash(directory/filename)!=expected:raise ValueError('execution identity changed')
    snapshot=(directory/'ledger.jsonl').read_bytes();prefix=b''.join(snapshot.splitlines(keepends=True)[:PRIOR_EVENTS])
    if hashlib.sha256(prefix).hexdigest()!=PRIOR_HASH:raise ValueError('old ledger prefix changed')
    authority=checked_reference(ROOT,base['budget_authority']);canonical=ROOT/'artifacts/lp-campaign-ledgers'/read_json(authority)['id']/'ledger.jsonl'
    if not snapshot.endswith(b'\n') or not canonical.read_bytes().startswith(snapshot):raise ValueError('ledger snapshot differs')
    ledger=Ledger(directory,file_hash(authority),base['phase_gpu_seconds'],cumulative_ns=value['cumulative_ceiling_ns'])
    ledger.events=[validate('ledger',strict_loads(line)) for line in snapshot.splitlines()]
    if ledger.pending():raise ValueError('unsettled work')
    if any(e['sequence']!=i or e['campaign_sha256']!=file_hash(authority) for i,e in enumerate(ledger.events)):raise ValueError('ledger provenance differs')
    charges={c:sum(e['charged_ns'] for e in ledger.events if e['kind']=='settle' and e['trial_id'].startswith('gpup5b-'+c+'-')) for c in ['study','accept']}
    if charges['study']>900*NS or charges['accept']>300*NS or ledger.totals()>value['cumulative_ceiling_ns'] or ledger.totals()-PRIOR_NS>1200*NS:raise ValueError('budget exceeded')
    rows=[];missing=[];traces=[]
    for job in schedule:
        key=label(job);result_path=directory/(key+'.result.json');endpoint_path=directory/(key+'.endpoint.json')
        if not result_path.exists():missing.append(key);continue
        result=read_json(result_path)
        if result['job']!=job or 'gpup5b-study-'+key not in ledger.attempted():raise ValueError('result differs from admitted plan')
        intent=read_json(directory/(key+'.intent.json'))
        if intent['job']!=job:raise ValueError('intent changed')
        row=dict(id=key,kind=job['kind'],instance=job['instance']['id'],configuration=job['config']['id'],repetition=job['repetition'],worker=result['worker'],verified=False,certified=False,classification='missing_endpoint')
        if endpoint_path.exists():
            if file_hash(endpoint_path)!=result['endpoint_sha256']:raise ValueError('endpoint bytes changed')
            endpoint=read_json(endpoint_path);model=checked_reference(ROOT,job['instance']['model']);c=job['config']
            options=dict(base['solve']);method=dict(base['lp_settings'])
            if job['kind'] in ['short','trace']:options['iteration_limit']=200;method['iteration_limit']=200
            if 'mode' in c:
                request_path=directory/(key+'.research.json');request=read_json(request_path)
                expected=dict(schema_version=1,mode=c['mode'],model_sha256=job['instance']['model']['sha256'],source_tree_sha256=frozen['source']['source_tree_sha256'],executable_sha256=frozen['research_binary_sha256'],code_object_sha256=frozen['code_object_sha256'],device=base['device'],options=options,method=method,profile=job['kind']!='timing',device_buffer_bytes=base['limits']['device_buffer_bytes'])
                if request!=expected or endpoint['witness']['request']!=expected:raise ValueError('research request/provenance changed')
                cmd=[str(directory/'lp_precision_research'),'verify',str(model),str(request_path),str(endpoint_path)]
                w=endpoint['witness'];d=w['diagnostics'];execd=w['execution'];executed=w['executed_device']==base['device'];proposals=w['proposed_steps'];physical=w['physical_steps']
                row.update(status=w['status'],failure=w['failure'],packing_ns=w['packing_ns'],matrix_tail_max=w['matrix_tail_max'],vector_tail_normalized=w['vector_tail_units']*2**-53,operator_bounds=w['operator_bounds'],step=w['step'],vector_splits=w['vector_splits'],fp32_cross_products=w['fp32_cross_products'])
            else:
                validate('endpoint',endpoint);record=endpoint['record'];d=endpoint['diagnostics'];execd=endpoint['execution'];control=endpoint['control'];executed=record['backend']=='cuda-lp-tuned' and endpoint['fallback_reason'] is None
                if record['options']!=options or record['lp_settings']!=method or endpoint['requested_backend']!='cuda-lp-tuned':raise ValueError('legacy control settings differ')
                if record['lp_execution']['settings']!=c['execution']:raise ValueError('execution policy changed')
                if (record.get('lp_precision') or None)!=(c.get('precision') or None):raise ValueError('precision policy changed')
                cmd=[str(directory/'optimizer'),'lp-study','verify','--model',str(model),'--evidence',str(endpoint_path)]
                proposals=control['logical_iterations'] if control else None;physical=control['physical_iterations'] if control else None;row.update(status=record['termination'],failure=endpoint['fallback_reason'])
            check=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
            if check.returncode:raise ValueError('independent verification failed: '+key+': '+check.stderr[:500])
            worker=result['worker'];classification=endpoint['assessment']['classification'];expected_exit=0 if 'mode' in c or row['status']=='optimal' else 1;complete=bool(worker and worker['reason']=='completed' and worker['returncode']==expected_exit)
            row.update(verified=True,process_complete=complete,classification=classification,certified=bool(complete and executed and classification=='certified_success'),proposals=proposals,physical_steps=physical,elapsed_ns=worker['elapsed_ns'] if worker else None,execution_ns=iteration_execution(d['phases_ns']),phases_ns=d['phases_ns'],memory_bytes=d['device_buffer_peak_bytes'],execution=execd,assessment=endpoint['assessment'],kernel_launches=d['kernel_launches'])
            if job['kind']=='trace':
                path=directory/(key+'.sqlite')
                traces.append(dict(id=key,available=path.exists(),observations=trace(path,d['kernel_launches']) if path.exists() else None))
        rows.append(row)
    groups=defaultdict(list)
    for row in rows:groups[(row['kind'],row['instance'],row['configuration'])].append(row)
    summary=[];paired=[];short=[]
    for c in value['configurations']:
        timings=[r for r in rows if r['kind']=='timing' and r['configuration']==c['id']]
        summary.append(dict(configuration=c['id'],planned=36,attempted=len(timings),certified=sum(r['certified'] for r in timings),outcomes=dict(Counter(r['classification'] for r in timings))))
    comparisons=[('tuned-fp64','research-default-fp64'),('precision-fp64','research-default-fp64'),('research-power2-fp64','research-power2-fp32'),('research-factored-fp64','research-factored-fp32'),('research-components2-fp64','research-components2-fp32'),('research-components3-fp64','research-components3-fp32')]
    comparisons += [('research-default-fp64',c['id']) for c in value['configurations'] if 'mode' in c and c['mode']!='default-fp64']
    for instance in manifest['instances']:
        for left,right in comparisons:
            a={r['repetition']:r for r in groups[('timing',instance['id'],left)]};b={r['repetition']:r for r in groups[('timing',instance['id'],right)]}
            pairs=[(r['elapsed_ns'],b[k]['elapsed_ns']) for k,r in a.items() if k in b and r['certified'] and b[k]['certified']]
            paired.append(dict(instance=instance['id'],comparison=left+'/'+right,statistics=paired_ratio(pairs)))
        for c in value['configurations']:
            observed=[r for r in groups[('short',instance['id'],c['id'])] if r['verified'] and r.get('proposals')==200 and r.get('physical_steps')==200 and r['classification'] in ['work_limit','certified_success'] and r.get('process_complete',False)]
            if observed:short.append(dict(instance=instance['id'],configuration=c['id'],repetitions=len(observed),median_execution_ns=statistics.median(r['execution_ns'] for r in observed),median_ns_per_update=statistics.median(r['execution_ns']/200 for r in observed)))
    endpoint_comparisons=[]
    for left,right in [('research-power2-fp64','research-power2-fp32'),('research-factored-fp64','research-factored-fp32'),('research-default-fp64','research-components3-fp64'),('research-components2-fp64','research-components2-fp32'),('research-components3-fp64','research-components3-fp32')]:
        same=total=0
        for job in schedule:
            if job['kind']!='timing' or job['config']['id']!=left:continue
            a=directory/(label(job)+'.endpoint.json');b=directory/(label(job).removesuffix(left)+right+'.endpoint.json')
            if a.exists() and b.exists():
                x=read_json(a)['witness'];y=read_json(b)['witness'];total+=1
                same+=all(x[k]==y[k] for k in ['primal','dual','status','proposed_steps'])
        endpoint_comparisons.append(dict(left=left,right=right,compared=total,identical=same))
    result=dict(analysis_tool_sha256=file_hash(Path(__file__)),analysis_dependencies={name:file_hash(ROOT/'tools'/name) for name in ['lp_report.py','analyze_lp_precision_diagnosis.py','lp_protocol.py']},bootstrap_seed=17002,bootstrap_resamples=10000,endpoint_comparisons=endpoint_comparisons,schema_version=1,planned=840,attempted=len(rows),verified=sum(r['verified'] for r in rows),missing=missing,coverage=summary,paired=paired,short=short,profiles=[r for r in rows if r['kind']=='profile'],traces=traces,rows=rows,study_gpu_ns=charges['study'],acceptance_gpu_ns=charges['accept'],cumulative_gpu_ns=ledger.totals(),ledger_sha256=hashlib.sha256(snapshot).hexdigest(),ledger_events=len(ledger.events),source=frozen['source'],research_binary_sha256=frozen['research_binary_sha256'],code_object_sha256=frozen['code_object_sha256'])
    historical_integrity()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--decode-traces',action='store_true');a=p.parse_args()
    if a.decode_traces:decode(OUTPUT)
    result=inspect();write_json(OUTPUT/'analysis.json',result)
    print('Attempts',result['attempted'],'verified',result['verified'],'missing',len(result['missing']))
    for row in result['coverage']:print(row)
    print('GPU seconds study / acceptance / cumulative:',*[result[k]/NS for k in ['study_gpu_ns','acceptance_gpu_ns','cumulative_gpu_ns']])
if __name__=='__main__':main()
