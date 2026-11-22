"""Compact completed billion results and exact per-phase CSV for local review."""
import argparse,csv,io,subprocess,sys
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require
from lp_billion_full_report import main as project_report,record
from lp_billion_timing import PHASES

def main():
    subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/integration','-p','test_lp_billion_full_report.py'],check=True,timeout=60)
    target=BASE/'full-billion-results-v1.json'
    project_report(target);report=load(target)
    extra=BASE/'copt-nopresolve-1b-v1/freeze.json';rows=list(report['cells'])
    supplemental=None
    if extra.exists() and (extra.parent/'completed.json').exists():
        frozen=load(extra);supplemental=dict(freeze=ref(extra),cells=[record(c) for c in frozen['cells']])
        supplemental.update(total_slots=len(frozen['cells']),attempted=sum(c['status']=='pending' for c in frozen['cells']),
            available_responses=sum('response' in r for r in supplemental['cells']),
            eligible_timings=sum(r.get('timing_eligible',False) for r in supplemental['cells']),
            strictly_certified=sum(r.get('certified',False) for r in supplemental['cells']))
        rows+=supplemental['cells']
    comparisons=list(report['comparisons'])
    if supplemental:
        for c in supplemental['cells']:
            for lane in ['native','fp32','fp4x2']:
                p=next(r for r in report['cells'] if r['family']==c['family'] and r['lane']==lane)
                eligible=c.get('timing_eligible',False) and p.get('timing_eligible',False)
                certified=eligible and c.get('certified',False) and p.get('certified',False)
                comparisons.append(dict(family=c['family'],baseline=c['lane'],candidate=lane,both_timing_eligible=eligible,both_strict_certified=certified,
                    baseline_over_candidate_complete_ratio=c['complete_ns']/p['complete_ns'] if eligible else None,
                    certified_solve_speedup=c['complete_ns']/p['complete_ns'] if certified else None,
                    meaning='Separate Presolve=0 GPU variant; uncertified bounded endpoints do not establish certified-solve speedup.'))
    totals=dict(slots=len(rows),attempted=report['attempted']+(supplemental['attempted'] if supplemental else 0),
        available_responses=sum('response' in r for r in rows),strictly_certified=sum(r.get('certified',False) for r in rows))
    compact=dict(report,source_report=ref(target),supplemental=supplemental,all_rosters=totals,comparisons=comparisons,delivery_source=ref(__file__))
    out=ROOT/'docs/benchmarks/lp-billion-full-results.json';put(out,compact)
    phases=sorted({k for r in rows for k in r.get('complete_cost_ledger',{}).get('exclusive_ns',{})})
    output=ROOT/'docs/benchmarks/lp-billion-full-phases.csv'
    with output.open('x',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['family','lane','status','certified','strict_endpoint_accepted','timing_eligible','logical_updates','copt_pdlp_iterations','accepted_fp4_share','solver_process_peak_gib','sampled_aggregate_peak_gib','independent_audit_sampled_peak_gib','sampled_owned_device_peak_gib','owned_child_timed_out','observed_solver_child_seconds','reservation_active_seconds','complete_seconds',*[k+'_seconds' for k in phases]])
        for r in rows:
            costs=r.get('complete_cost_ledger',{}).get('exclusive_ns',{})
            if costs:require(sum(costs.values())==r['complete_ns'],'every exported exclusive phase sums exactly')
            scale=lambda x:None if x is None else x/(1<<30)
            writer.writerow([r['family'],r['lane'],r['status'],r.get('certified',False),r.get('strict_endpoint_accepted',False),r.get('timing_eligible',False),r.get('logical'),r.get('native',{}).get('PDLPIter'),r.get('accepted_fp4_share'),
                scale(r.get('solver_child_hwm_bytes')),scale(r.get('sampled_aggregate_peak_rss_bytes')),scale(r.get('independent_audit_sampled_aggregate_peak_rss_bytes')),scale(r.get('sampled_peak_owned_device_bytes')),r.get('owned_child_timed_out'),r['observed_solver_child_elapsed_ns']/1e9 if r.get('observed_solver_child_elapsed_ns') is not None else None,r['reservation_active_elapsed_ns']/1e9 if r.get('reservation_active_elapsed_ns') is not None else None,r.get('complete_ns',0)/1e9 if costs else None,
                *[costs[k]/1e9 if k in costs else None for k in phases]])
    put(BASE/'full-billion-delivery-v1.json',dict(status='complete',compact=ref(out),phase_csv=ref(output),source=ref(__file__),rows=len(rows),
        actual_billion_responses=sum('response' in r for r in rows),strict_certificates=sum(r.get('certified',False) for r in rows)))
    print(dict(rows=len(rows),compact=str(out),phase_csv=str(output)),flush=True)

if __name__=='__main__':main()
