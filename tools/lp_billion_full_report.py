"""Report every full-roster outcome and exclusive cost without success filtering."""
import argparse,json,statistics
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require,NS
from lp_billion_budget import accounting
from lp_billion_full_run import MANIFEST,LANES,FAMILIES
from lp_billion_timing import process_ledger

def validate_audit_binding(response_ref, model_ref, checker_ref, response, audit, project):
    require(audit['response']==response_ref,'independent audit response identity')
    if project or response['has_solution']:
        require(audit['status']=='passed' and audit['model']==model_ref and audit['checker']==checker_ref,'strict original model/checker identity')
        require(audit['results'] and all(q['model_sha256']==model_ref['sha256'] and q['tolerance']==1e-9 for q in audit['results']),'strict original-model tolerance in every proof')
        accepted=audit['results'][0]['accepted']
        require(audit['strict_endpoint_accepted']==accepted,'final endpoint proof classification')
        from lp_billion_full_audit_v2 import certification_status
        require(audit['certified']==certification_status(response,project,accepted),'retained solver/deadline certificate classification')
    else:
        require(audit['status']=='no_endpoint' and not audit['certified'] and audit['checks']==0,'vendor has no endpoint or proof')


def vendor_ledger(response, measured, final_check_ns):
    profile=response['profile']
    require(sum(profile['exclusive_ns'].values())==profile['total_ns']<=measured['process_ns'],'vendor profile coverage')
    require(measured['process_ns']+measured['response_transport_ns']==measured['fresh_process_ns'],'vendor process coverage')
    costs=dict(profile['exclusive_ns'],process_imports_serialization_cleanup=measured['process_ns']-profile['total_ns'],response_transport=measured['response_transport_ns'])
    if 'process_cost_ledger' in measured:
        require(measured['process_cost_ledger']['exclusive_ns']==costs,'retained vendor ledger agrees with raw intervals')
    costs['independent_final_check']=final_check_ns
    total=measured['fresh_process_ns']+final_check_ns
    require(sum(costs.values())==total,'exact vendor complete cost coverage')
    return dict(total_ns=total,exclusive_ns=costs)


def vendor_timing_eligible(response):
    """Retain errors as outcomes, without ranking a failed API call as faster."""
    return response['solve_called'] and response['solve_returncode']==0


def record(c):
    row=dict(id=c['id'],family=c['family'],lane=c['lane'],status=c['status'],capacity=c['memory'])
    if c['status']!='pending':return row
    path=BASE/'resources'/(c['id']+'.settlement.json');s=load(path);row['settlement']=ref(path)
    disposition=path.with_name(path.name.replace('.settlement.json','.cleanup-disposition.json'))
    if disposition.exists():row['supplemental_cleanup']=ref(disposition)
    response=BASE/c['id']/'response.json';measured=BASE/c['id']/'result.json';audit_path=BASE/(c['id']+'-full-audit/result.json')
    audit=load(audit_path);row['audit']=ref(audit_path)
    audit_settlement=BASE/'resources'/(c['id']+'-full-audit.settlement.json')
    audit_status=load(audit_settlement)
    require(audit_status['status']=='passed' and audit_status['cleanup_empty'] and not audit_status['overrun'],'successful settled independent audit')
    audit_resource=load(resolve(audit_status['resource']))
    row['independent_audit_sampled_aggregate_peak_rss_bytes']=audit_resource['result'].get('peak_rss_bytes')
    row['audit_settlement']=ref(audit_settlement)
    telemetry=BASE/'resources'/(c['id']+'.resource.json.capacity.jsonl')
    if telemetry.exists():
        from lp_billion_copt_readiness import gpu_peak
        row['sampled_peak_owned_device_bytes']=gpu_peak(telemetry);row['device_telemetry']=ref(telemetry)
    process_path=BASE/c['id']/'process.json'
    if process_path.exists():
        process=load(process_path);row['process_evidence']=ref(process_path)
        row['solver_child_hwm_bytes']=process['child_rusage_hwm_bytes'] if process['child_rusage_scope_is_single_solver'] else None
        row['owned_child_timed_out']=process['timed_out']
        row['observed_solver_child_elapsed_ns']=process['elapsed_ns']
    resource=load(resolve(s['resource']));row['sampled_aggregate_peak_rss_bytes']=resource['result'].get('peak_rss_bytes')
    row['reservation_active_elapsed_ns']=resource.get('active_elapsed_ns')
    vendor_log=BASE/c['id']/'response.copt.log'
    if vendor_log.exists():row['vendor_log']=ref(vendor_log)
    if not response.exists():return dict(row,status='missing_response',timing_eligible=False,certified=False)
    r=load(response);project=c['lane'] in LANES[:3];row.update(response=ref(response),status=r['status'],certified=bool(audit.get('certified')),strict_endpoint_accepted=bool(audit.get('strict_endpoint_accepted',audit.get('certified'))),timing_eligible=s['status']=='passed' and s['cleanup_empty'] and not s['overrun'] and measured.exists())
    validate_audit_binding(ref(response),c['model'],ref(BASE/'image-v1/executor'),r,audit,project)
    row['final_check_ns']=audit.get('final_check_ns',0);row['offline_audit_ns']=audit.get('offline_audit_ns',0)
    if project:
        exclusive=r['solver_profile']['exclusive_ns']
        row['original_input_validation_and_transpose_ns']=r['input_ns']
        row['solver_preparation_ns']=sum(exclusive[k] for k in ['preparation_engine','preparation_operator','preparation_packing','preparation_control'])
        row['observed_upfront_ns']=r['input_ns']+row['solver_preparation_ns']+exclusive['device_setup']
        row.update(logical=r['logical'],physical=r['physical'],accepted=r['accepted'],accepted_product_work=r['accepted_product_work'],
            accepted_fp4_share=r['accepted_product_work'][1]/r['accepted_product_work'][3] if r['accepted_product_work'][3] else 0.,
            device_bytes_upper=r['device_bytes_upper'],preparation_detail_ns=r.get('preparation_detail_ns'),gpu_preparation=r.get('gpu_preparation'),
            cost_ns=r['cost_ns'],solver_profile=r['solver_profile'],solver_wall_ns=r['elapsed_ns'])
    else:
        row['timing_eligible'] = row['timing_eligible'] and vendor_timing_eligible(r)
        row.update(has_solution=r['has_solution'],gpu_confirmed=r['gpu_confirmed'],requested=r['requested'],executed=r['executed'],
            native=r['native'],vendor_host_memory=r['host_memory'],solve_returncode=r['solve_returncode'],vendor_profile=r['profile'],solver_wall_ns=r['solver_wall_ns'])
    row['requested_solver_wall_ns']=600*NS;row['requested_wall_exceeded']=row['solver_wall_ns']>600*NS
    if row['timing_eligible']:
        m=load(measured);require(m['response']==ref(response),'measured response identity')
        row.update(fresh_process_ns=m['fresh_process_ns'],process_ns=m['process_ns'],response_transport_ns=m['response_transport_ns'])
        if project:ledger=process_ledger(r,m,row['final_check_ns'])
        else:
            ledger=vendor_ledger(r,m,row['final_check_ns'])
        row['complete_ns']=ledger['total_ns'];row['complete_cost_ledger']=ledger
    return row

def main(output):
    f=load(MANIFEST);require((MANIFEST.parent/'completed.json').exists(),'every supported cell attempted and audited')
    rows=[record(c) for c in f['cells']];comparisons=[]
    for family in FAMILIES:
        lanes={r['lane']:r for r in rows if r['family']==family}
        for baseline in ['native','fp32','copt-cpu-auto','copt-gpu-pdlp']:
            a,b=lanes[baseline],lanes['fp4x2'];eligible=a.get('timing_eligible',False) and b.get('timing_eligible',False)
            certified=eligible and a.get('certified',False) and b.get('certified',False)
            comparisons.append(dict(family=family,baseline=baseline,candidate='fp4x2',both_timing_eligible=eligible,both_strict_certified=certified,
                baseline_over_fp4_complete_ratio=a['complete_ns']/b['complete_ns'] if eligible else None,
                certified_solve_speedup=a['complete_ns']/b['complete_ns'] if certified else None,
                same_accepted_update_count=a.get('logical')==b.get('logical') if baseline in ['native','fp32'] and eligible else None,
                meaning='Descriptive bounded-run ratio; only jointly certified endpoints support certified-solve timing.'))
    cpu,gpu=accounting();put(output,dict(status='complete_development_roster',freeze=ref(MANIFEST),cells=rows,comparisons=comparisons,
        source=ref(__file__),original_nonzeros_per_model=1_000_000_000,total_cells=30,iterations=f['iterations'],
        attempted=sum(c['status']=='pending' for c in f['cells']),unsupported=sum(c['status']!='pending' for c in f['cells']),
        available_responses=sum('response' in r for r in rows),eligible_timings=sum(r.get('timing_eligible',False) for r in rows),
        strictly_certified=sum(r.get('certified',False) for r in rows),accounting_snapshot_cpu_ns=sum(cpu.values()),accounting_snapshot_gpu_ns=sum(gpu.values()),
        accounting_snapshot_includes_current_reservation=True,confirmation=False,public_adoption=False,
        limitations=['One rotated repetition per supported cell; retain all family/lane capacity refusals.',
                    'Common requested solver allowance is 600 s; vendor calls and mandatory final checks can exceed it. Actual elapsed costs are reported.',
                    'COPT internal preprocessing/execution is opaque; adapter preparation is not total vendor preparation.',
                    'For project lanes input_hash_validation includes chunk reading/hashing/decoding, canonical validation and construction of the original CSR-to-CSC transpose; it is not pure disk I/O.',
                    'GPU device-advance wall time is not kernel-active time.',
                    'Uncertified limit endpoints do not establish certified-solve benefit.']))
    print(dict(cells=30,attempted=sum(c['status']=='pending' for c in f['cells']),certified=sum(r.get('certified',False) for r in rows)),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();main(a.output)
