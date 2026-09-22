"""Verify and summarize the frozen GPUP-THROUGHPUT repeated-solve study (SPEC-0014, protocol v3) without changing historical evidence or GPU work.

Amortized repeated-solve throughput is a separately labeled endpoint: it is
never substituted for, tabulated as, or merged into one latency table with
fresh-process single-solve latency, and every comparison of the two is titled
as separate endpoints (SPEC-0014 requirements 1-4, ADR-0013). Bitwise identity
of batch solves against fresh single solves of the same materialized model is
verified from the retained evidence alone and reported as counts, never
asserted (requirements 15-17).
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import statistics
import struct
import subprocess
from pathlib import Path
from benchmark_lp_throughput import (CONFIG,BATCH_KINDS,FRESH_KINDS,REPEAT_KINDS,VARIANT_KINDS,
                                     jobs,label,protocol,request_for,research_batch_request_for,
                                     batch_request_for,settings_for,SINGLE_VARIANT_KIND,verify_control_model)
from lp_research_budget import Study,category_usage
from lp_protocol import ROOT,NS,Ledger,checked_reference,file_hash,read_json,strict_loads,validate,write_json
from lp_report import paired_ratio
from analyze_lp_research import historical_integrity

FRESH_ENDPOINT='fresh-process single-solve latency (primary endpoint, SPEC-0013 requirements 10-13)'
AMORTIZED_ENDPOINT='amortized repeated-solve throughput (separate endpoint, SPEC-0014 requirement 2)'
SEPARATE_TITLE='separate endpoints: amortized per-solve time is never single-solve latency'
SETUP_PHASES=['device_context','module_load','preconditioning','research_preparation','invariant_allocation_upload']
SOLVE_PHASES=['variant_rebind','engine_rebind','bound_upload']
# The variant indices block G solves fresh; batch-variant solves with these
# indices are the only variant solves with a fresh partner (ADR-0023 grid).
FRESH_VARIANT_INDICES=(0,7)
# Coverage rows iterate exactly the planner's kind universe (FRESH/BATCH are tuples).
COVERAGE_KINDS=tuple(list(FRESH_KINDS)+['fresh-variant']+list(REPEAT_KINDS)+list(VARIANT_KINDS[:2]))


def tuned_bits(endpoint):
    """The requirement-15 identity of one tuned per-solve lp-endpoint-v3 record:
    primal and dual bits, logical iteration and restart counts, termination
    status and launch count."""
    record=endpoint['record'];control=endpoint['control']
    return dict(primal=record.get('candidate'),dual=endpoint['diagnostics']['dual'],status=record['termination'],
                logical_iterations=control['logical_iterations'],restarts=control['restarts'],
                kernel_launches=control['device_kernel_launches'])


def research_bits(evidence):
    """The requirement-15 identity of one research-v2 per-solve record."""
    w=evidence['witness'];d=w['diagnostics']
    return dict(primal=w['primal'],dual=w['dual'],status=w['status'],
                logical_iterations=w['proposed_steps'],restarts=d['restarts'],
                kernel_launches=d['kernel_launches'])


def bitwise_key(value):
    """Preserve binary64 encodings recursively, including the sign of zero.

    Non-floating identity fields keep their types; counts and IDs are never
    rounded through float conversion. The key is used only for comparison.
    """
    if type(value) is float:return ('f64',struct.pack('>d',value))
    if type(value) is dict:return ('object',tuple((k,bitwise_key(v)) for k,v in sorted(value.items())))
    if type(value) is list:return ('array',tuple(bitwise_key(v) for v in value))
    return (type(value).__name__,value)


def identity_count(pairs):
    """(compared, identical) over (fresh bits, batch solve bits) pairs: counts, never asserted."""
    return dict(compared=len(pairs),identical=sum(1 for a,b in pairs if bitwise_key(a)==bitwise_key(b)))


def cross_mode_bits(bits):
    """The numerical fields of a requirement-15 identity for a cross-mode
    comparison: fused-fp64 runs two launches per proposal where intguard-fp64
    runs six, so trajectories that agree bitwise still differ in
    kernel_launches by construction (mirrors analyze_lp_research.py's
    primal/dual/status/proposed_steps endpoint comparison)."""
    return {k:v for k,v in bits.items() if k!='kernel_launches'}


def amortized(elapsed_ns,solves):
    """The separately labeled amortized endpoint: batch elapsed / N and its reciprocal throughput."""
    if type(solves) is not int or solves<1 or type(elapsed_ns) is not int or elapsed_ns<=0:
        raise ValueError('invalid batch elapsed/solve count')
    per=elapsed_ns/solves
    return dict(batch_elapsed_ns=elapsed_ns,solves=solves,per_solve_ns=per,solves_per_second=NS/per)


def tuned_exit_code(termination):
    """crates/optimizer-cli/src/solve.rs::exit_code, mirrored exactly."""
    if termination in ('optimal','infeasible','unbounded','unbounded_or_infeasible'):return 0
    if termination=='interrupted':return 130
    if termination in ('feasible','time_limit','iteration_limit','node_limit'):return 1
    return 2


def expected_batch_exit(config,solves):
    """The batch command's worst per-solve exit code from the recorded per-solve outcomes."""
    if 'mode' in config:return 0
    worst=0
    for solve in solves:
        if solve['termination'] is not None:code=tuned_exit_code(solve['termination'])
        elif solve['status']=='failed':code=2
        elif solve['status']=='not_attempted':code={'cancelled':130,'batch_time_limit':1}.get(solve['reason'],2)
        else:code=2
        worst=max(worst,code)
    return worst


def check_endpoint_separation(result):
    """Requirements 1-4: amortized throughput appears only as its own labeled endpoint."""
    expected={'fresh':FRESH_ENDPOINT,'amortized':AMORTIZED_ENDPOINT,'comparison':SEPARATE_TITLE}
    if result.get('endpoint_labeling')!=expected:raise ValueError('endpoint labeling changed')
    fresh={row['id'] for row in result['fresh_single_solve_latency']}
    amortized_ids={row['id'] for row in result['amortized_repeated_solve_throughput']}
    if fresh&amortized_ids:raise ValueError('fresh and amortized rows share one latency table')
    for row in result['paired_amortized_vs_fresh']:
        if row.get('title')!=SEPARATE_TITLE or row.get('endpoints')!='separate':
            raise ValueError('an amortized/fresh comparison is not titled as separate endpoints')


def solve_file(directory,index):
    path=directory/('solve-%03d.json'%index)
    return read_json(path) if path.exists() else None


def inspect(directory=None,config=CONFIG):
    value,base,manifest=protocol(config);study=Study.from_protocol(value);directory=directory or study.output
    frozen=read_json(directory/'protocol.json');schedule=list(jobs(value,base,manifest))
    if frozen['protocol']!=value or frozen['protocol_sha256']!=file_hash(config) or frozen['jobs']!=schedule:raise ValueError('frozen schedule differs')
    if file_hash(directory/'source.tar')!=read_json(directory/'execution.json')['source_archive_sha256']:raise ValueError('source archive changed')
    for filename,expected in [('optimizer',frozen['source']['binary_sha256']),('lp_precision_research',frozen['research_binary_sha256']),('lp_pdhg_research.cubin',frozen['code_object_sha256']),('lp_pdhg_tuned.cubin',base['code_object_sha256']),('lp_pdhg_precision.cubin',base['precision_code_object_sha256'])]:
        if file_hash(directory/filename)!=expected:raise ValueError('execution identity changed')
    snapshot=(directory/'ledger.jsonl').read_bytes();prefix=b''.join(snapshot.splitlines(keepends=True)[:study.prior_events])
    if hashlib.sha256(prefix).hexdigest()!=study.prior_hash:raise ValueError('old ledger prefix changed')
    authority=checked_reference(ROOT,base['budget_authority']);canonical=ROOT/'artifacts/lp-campaign-ledgers'/read_json(authority)['id']/'ledger.jsonl'
    if not snapshot.endswith(b'\n') or not canonical.read_bytes().startswith(snapshot):raise ValueError('ledger snapshot differs')
    ledger=Ledger(directory,file_hash(authority),base['phase_gpu_seconds'],cumulative_ns=value['cumulative_ceiling_ns'])
    ledger.events=[validate('ledger',strict_loads(line)) for line in snapshot.splitlines()]
    if ledger.pending():raise ValueError('unsettled work')
    if any(e['sequence']!=i or e['campaign_sha256']!=file_hash(authority) for i,e in enumerate(ledger.events)):raise ValueError('ledger provenance differs')
    charges={c:sum(e['charged_ns'] for e in ledger.events if e['kind']=='settle' and e['trial_id'].startswith(study.prefix+'-'+c+'-')) for c in ['study','accept']}
    if charges['study']>study.study_cap_seconds*NS or charges['accept']>study.acceptance_cap_seconds*NS or ledger.totals()>value['cumulative_ceiling_ns'] or ledger.totals()-study.prior_ns>study.combined_cap_seconds*NS:raise ValueError('budget exceeded')
    rows=[];missing=[]
    for job in schedule:
        key=label(job);result_path=directory/(key+'.result.json')
        if not result_path.exists():missing.append(key);continue
        result=read_json(result_path)
        if result['job']!=job or study.prefix+'-study-'+key not in ledger.attempted():raise ValueError('result differs from admitted plan')
        intent=read_json(directory/(key+'.intent.json'))
        if intent['job']!=job:raise ValueError('intent changed')
        c=job['config'];research='mode' in c;batch=job['kind'] in BATCH_KINDS
        row=dict(id=key,kind=job['kind'],instance=job['instance']['id'],configuration=c['id'],tier=job['tier'],
                 repetition=job['repeat'],size=job['size'],variant=job['variant'],worker=result['worker'],verified=False,certified=False)
        options,method,_,batch_ms=settings_for(job,base,value)
        model=(verify_control_model(job,value,directory,directory/'optimizer') if job['kind']==SINGLE_VARIANT_KIND
               else checked_reference(ROOT,job['instance']['model']))
        evidence=directory/(key+'.batch') if batch else directory/(key+'.endpoint.json')
        endpoint_path=evidence/'batch.json' if batch else evidence
        if endpoint_path.exists():
            if file_hash(endpoint_path)!=result['endpoint_sha256']:raise ValueError('endpoint bytes changed')
            timeout=120 if job['size'] is None else 120+60*job['size']
            if research:
                request_path=directory/(key+'.research.json');request=read_json(request_path)
                expected=(research_batch_request_for(job,base,value,frozen['source']['source_tree_sha256'],file_hash(model),frozen['research_binary_sha256'],frozen['code_object_sha256'])
                          if batch else request_for(job,base,value,frozen['source']['source_tree_sha256'],file_hash(model),frozen['research_binary_sha256'],frozen['code_object_sha256']))
                if request!=expected:raise ValueError('research request changed')
                cmd=[str(directory/'lp_precision_research'),'verify-batch' if batch else 'verify',str(model),str(request_path),str(evidence)]
            else:
                for suffix,data in [('options',options),('method',method),('execution',c['execution'])]:
                    if read_json(directory/(key+'.'+suffix+'.json'))!=data:raise ValueError('tuned study document changed: '+suffix)
                if batch:
                    batch_path=directory/(key+'.batch.json')
                    if read_json(batch_path)!=batch_request_for(job,value,batch_ms):raise ValueError('batch request changed')
                    cmd=[str(directory/'optimizer'),'lp-study','verify-batch','--model',str(model),'--batch',str(batch_path),'--evidence',str(evidence)]
                else:
                    endpoint=validate('endpoint',read_json(endpoint_path))
                    record=endpoint['record']
                    if record['options']!=options or record['lp_settings']!=method or endpoint['requested_backend']!='cuda-lp-tuned':raise ValueError('legacy control settings differ')
                    if record['lp_execution']['settings']!=c['execution']:raise ValueError('execution policy changed')
                    cmd=[str(directory/'optimizer'),'lp-study','verify','--model',str(model),'--evidence',str(endpoint_path)]
            check=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
            if check.returncode:raise ValueError('independent verification failed: '+key+': '+check.stderr[:500])
            worker=result['worker']
            if batch:
                record=read_json(endpoint_path)
                setup=record['setup']['phases_ns']
                if any(name not in SETUP_PHASES for name in setup):raise ValueError('unknown batch setup phase')
                entries=record['solves'];solves=[]
                for entry in entries:
                    if any(name not in SOLVE_PHASES for name in entry['session_phases_ns']):raise ValueError('unknown batch session phase')
                    per=solve_file(evidence,entry['index'])
                    one=dict(index=entry['index'],status=entry['status'],reason=entry['reason'],classification=None,termination=None,
                             solve_elapsed_ns=entry.get('solve_elapsed_ns'),session_phases_ns=entry['session_phases_ns'],bits=None,certified=False,executed=False)
                    if per is not None:
                        if research:
                            one.update(classification=per['assessment']['classification'],termination=None,bits=research_bits(per),
                                       executed=per['witness']['executed_device']==base['device'])
                        else:
                            one.update(classification=per['assessment']['classification'],termination=per['record']['termination'],bits=tuned_bits(per),
                                       executed=per['record']['backend']=='cuda-lp-tuned' and per['fallback_reason'] is None)
                        one['certified']=one['executed'] and one['classification']=='certified_success'
                    solves.append(one)
                expected_exit=expected_batch_exit(c,solves)
                complete=bool(worker and worker['reason']=='completed' and worker['returncode']==expected_exit)
                row.update(verified=True,process_complete=complete,setup_ns=setup,solves=solves,
                           certified=bool(complete and solves and all(one['certified'] for one in solves)),
                           elapsed_ns=worker['elapsed_ns'] if worker else None,
                           outcomes=dict(Counter(one['status'] for one in solves)))
            else:
                if research:
                    endpoint=read_json(endpoint_path);w=endpoint['witness']
                    if w['request']!=request:raise ValueError('research witness provenance changed')
                    row.update(status=w['status'],bits=research_bits(endpoint),executed=w['executed_device']==base['device'],
                               proposals=w['proposed_steps'],physical_steps=w['physical_steps'])
                    classification=endpoint['assessment']['classification'];expected_exit=0
                else:
                    endpoint=validate('endpoint',read_json(endpoint_path));control=endpoint['control']
                    row.update(status=endpoint['record']['termination'],bits=tuned_bits(endpoint),
                               executed=endpoint['record']['backend']=='cuda-lp-tuned' and endpoint['fallback_reason'] is None,
                               proposals=control['logical_iterations'] if control else None,
                               physical_steps=control['physical_iterations'] if control else None)
                    classification=endpoint['assessment']['classification'];expected_exit=0 if row['status']=='optimal' else 1
                complete=bool(worker and worker['reason']=='completed' and worker['returncode']==expected_exit)
                row.update(verified=True,process_complete=complete,classification=classification,
                           certified=bool(complete and row['executed'] and classification=='certified_success'),
                           elapsed_ns=worker['elapsed_ns'] if worker else None)
        rows.append(row)
    # Bitwise identity against fresh solves (requirements 15-17): repeat batch
    # solves pair with the same repetition's fresh single of the base model;
    # variant batch solves 0 and 7 pair with block G's fresh materialized solve.
    fresh_pair={(r['kind'],r['instance'],r['configuration'],r['tier'],r['repetition']):r for r in rows
                if r['kind'] in FRESH_KINDS and r.get('bits') is not None}
    variant_pair={(r['instance'],r['configuration'],r['tier'],r['variant']):r for r in rows
                  if r['kind']=='fresh-variant' and r.get('solves') and r['solves'][0]['bits'] is not None}
    batch_pair={(r['kind'],r['instance'],r['configuration'],r['tier'],r['repetition'],r['size']):r for r in rows
                if r['kind'] in BATCH_KINDS and r['kind']!='fresh-variant'}
    identity=[]
    for row in rows:
        if row['kind'] not in BATCH_KINDS or row['kind']=='fresh-variant' or not row.get('solves'):continue
        pairs=[]
        if row['kind'] in REPEAT_KINDS:
            partner=fresh_pair.get((('fresh-short' if row['kind']=='batch-repeat-short' else 'fresh'),row['instance'],row['configuration'],row['tier'],row['repetition']))
            if partner is not None:
                pairs=[(partner['bits'],one['bits']) for one in row['solves'] if one['bits'] is not None]
        else:
            for one in row['solves']:
                if one['index'] in FRESH_VARIANT_INDICES and one['bits'] is not None:
                    partner=variant_pair.get((row['instance'],row['configuration'],row['tier'],one['index']))
                    if partner is not None:pairs.append((partner['solves'][0]['bits'],one['bits']))
        if pairs:identity.append(dict(id=row['id'],partner='fresh-single-solve' if row['kind'] in REPEAT_KINDS else 'historical-n1-session',**identity_count(pairs)))
    # Cross-mode check: both admitted research modes are independently
    # bitwise-identical to the FP64 control (GPUP-5C), so their batch solves of
    # one materialized model agree numerically; measured as counts over the
    # numerical fields, never asserted. Launch counts differ by construction.
    cross=defaultdict(list)
    for row in rows:
        if row['kind'] in BATCH_KINDS and row['kind']!='fresh-variant' and row['configuration']=='research-fused-fp64' and row.get('solves'):
            other=batch_pair.get((row['kind'],row['instance'],'research-intguard-fp64',row['tier'],row['repetition'],row['size']))
            if other and other.get('solves'):
                cross[row['kind']].append(identity_count([(cross_mode_bits(a['bits']),cross_mode_bits(b['bits'])) for a,b in zip(row['solves'],other['solves']) if a['bits'] is not None and b['bits'] is not None]))
    cross_counts=[dict(kind=kind,compared=sum(c['compared'] for c in counts),identical=sum(c['identical'] for c in counts)) for kind,counts in sorted(cross.items())]
    # Timing rows describe complete batches only: every solve has its record.
    # Partial batches (cancellation, batch time limit, poisoning) stay visible
    # in coverage and per-row outcomes.
    def complete_batch(r):
        return r['verified'] and r.get('process_complete') and r['elapsed_ns'] and all(one['classification'] is not None for one in r['solves'])
    fresh_rows=[row for row in rows if row['kind'] in FRESH_KINDS]
    batch_rows=[row for row in rows if row['kind'] in BATCH_KINDS and row['kind']!='fresh-variant']
    fresh_table=[]
    groups=defaultdict(list)
    for row in fresh_rows:groups[(row['kind'],row['instance'],row['configuration'],row['tier'],row['variant'])].append(row)
    for (kind,instance,configuration,tier,variant),group in sorted(groups.items()):
        usable=[r for r in group if r['verified'] and r.get('process_complete') and r.get('executed')]
        fresh_table.append(dict(id=kind+'/'+instance+'/'+configuration+('' if variant is None else '/v'+str(variant)),kind=kind,instance=instance,configuration=configuration,tier=tier,variant=variant,
                                planned=len(group),verified=len([r for r in group if r['verified']]),
                                certified=len([r for r in group if r['certified']]),
                                median_elapsed_ns=statistics.median(r['elapsed_ns'] for r in usable) if usable else None,
                                outcomes=dict(Counter(r.get('classification','missing_endpoint') for r in group))))
    amortized_table=[];paired=[]
    groups=defaultdict(list)
    for row in batch_rows:groups[(row['kind'],row['instance'],row['configuration'],row['tier'],row['size'])].append(row)
    for (kind,instance,configuration,tier,size),group in sorted(groups.items()):
        usable=[r for r in group if complete_batch(r)]
        setup={name:statistics.median(r['setup_ns'].get(name,0) for r in usable) for name in SETUP_PHASES} if usable else None
        session={name:statistics.median(sum(one['session_phases_ns'].get(name,0) for one in r['solves'])/len(r['solves']) for r in usable) for name in SOLVE_PHASES} if usable else None
        values=[amortized(r['elapsed_ns'],len(r['solves'])) for r in usable]
        per_row=[statistics.median(times) for times in [[one['solve_elapsed_ns'] for one in r['solves'] if one['solve_elapsed_ns'] is not None] for r in usable] if times]
        amortized_table.append(dict(id='%s/%s/%s/n%d'%(kind,instance,configuration,size),kind=kind,instance=instance,configuration=configuration,tier=tier,size=size,
                                    batches=len(usable),planned=len(group),certified=len([r for r in group if r['certified']]),
                                    median_batch_elapsed_ns=statistics.median(r['elapsed_ns'] for r in usable) if usable else None,
                                    median_amortized_per_solve_ns=statistics.median(v['per_solve_ns'] for v in values) if values else None,
                                    median_solves_per_second=statistics.median(v['solves_per_second'] for v in values) if values else None,
                                    setup_ns=setup,per_solve_session_ns=session,
                                    median_solve_elapsed_ns=statistics.median(per_row) if per_row else None))
        if kind in REPEAT_KINDS:
            fresh_kind='fresh-short' if kind=='batch-repeat-short' else 'fresh'
            pairs=[]
            for r in usable:
                partner=fresh_pair.get((fresh_kind,instance,configuration,tier,r['repetition']))
                if partner is not None and partner.get('process_complete') and partner.get('executed') and partner['elapsed_ns']:
                    pairs.append((partner['elapsed_ns'],r['elapsed_ns']/len(r['solves'])))
            paired.append(dict(id='%s/%s/n%d'%(instance,configuration,size),instance=instance,configuration=configuration,tier=tier,size=size,
                               title=SEPARATE_TITLE,endpoints='separate',fresh_endpoint=FRESH_ENDPOINT,amortized_endpoint=AMORTIZED_ENDPOINT,
                               comparison='fresh single-solve latency / amortized per-solve time',statistics=paired_ratio(pairs)))
    planned_by=Counter((j['kind'],j['config']['id']) for j in schedule)
    coverage=[]
    for kind in COVERAGE_KINDS:
        for c in sorted({j['config']['id'] for j in schedule if j['kind']==kind}):
            cells=[r for r in rows if r['kind']==kind and r['configuration']==c]
            coverage.append(dict(kind=kind,configuration=c,planned=planned_by[(kind,c)],
                                 attempted=len(cells),verified=sum(r['verified'] for r in cells),certified=sum(r['certified'] for r in cells)))
    def public(row):
        out={k:v for k,v in row.items() if k!='bits'}
        if 'solves' in out:out['solves']=[{k:v for k,v in one.items() if k!='bits'} for one in out['solves']]
        return out
    result=dict(analysis_tool_sha256=file_hash(Path(__file__)),analysis_dependencies={name:file_hash(ROOT/'tools'/name) for name in ['benchmark_lp_throughput.py','lp_report.py','lp_protocol.py','lp_research_budget.py','analyze_lp_research.py']},
                bootstrap_seed=17002,bootstrap_resamples=10000,schema_version=1,planned=value['planned_attempts'],attempted=len(rows),
                verified=sum(r['verified'] for r in rows),missing=missing,
                endpoint_labeling={'fresh':FRESH_ENDPOINT,'amortized':AMORTIZED_ENDPOINT,'comparison':SEPARATE_TITLE},
                identity=identity,identity_by_partner={partner:{field:sum(i[field] for i in identity if i['partner']==partner) for field in ['compared','identical']} for partner in sorted({i['partner'] for i in identity})},identity_totals=dict(compared=sum(i['compared'] for i in identity),identical=sum(i['identical'] for i in identity)),
                cross_mode_identity=cross_counts,
                fresh_single_solve_latency=fresh_table,amortized_repeated_solve_throughput=amortized_table,paired_amortized_vs_fresh=paired,
                coverage=coverage,rows=[public(r) for r in rows],
                study_gpu_ns=charges['study'],acceptance_gpu_ns=charges['accept'],cumulative_gpu_ns=ledger.totals(),
                ledger_sha256=hashlib.sha256(snapshot).hexdigest(),ledger_events=len(ledger.events),
                source=frozen['source'],research_binary_sha256=frozen['research_binary_sha256'],code_object_sha256=frozen['code_object_sha256'])
    check_endpoint_separation(result)
    historical_integrity()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--protocol',type=Path,default=CONFIG);p.add_argument('--output',type=Path);a=p.parse_args()
    study=Study.from_protocol(read_json(a.protocol))
    destination=a.output or study.output/'analysis.json'
    if destination.exists():raise ValueError('refusing to overwrite analysis; choose a new --output')
    result=inspect(study.output,a.protocol);write_json(destination,result)
    print('Attempts',result['attempted'],'verified',result['verified'],'missing',len(result['missing']))
    print('Bitwise identity',result['identity_totals'])
    for row in result['coverage']:print(row)
    print('GPU seconds study / acceptance / cumulative:',*[result[k]/NS for k in ['study_gpu_ns','acceptance_gpu_ns','cumulative_gpu_ns']])
if __name__=='__main__':main()
