"""Fair COPT comparison planning and retained startup evidence; no implicit allocation."""
import argparse
import re
import statistics
from pathlib import Path
from lp_billion_common import BASE,ROOT,put,load,ref,resolve,require
from lp_billion_full_report import record
from lp_billion_copt_fair_allocation import worksheet


def diagnostics():
    path=BASE/'copt-diagnostic-64m-v1/freeze.json';f=load(path)
    require((path.parent/'completed.json').exists(),'complete diagnostic roster, including failures')
    rows=[]
    for c in f['cells']:
        row=record(c);row['variant']=c['variant'];row['requested_solver_wall_ns']=int(c['wall_seconds']*1e9)
        if 'response' in row:
            r=load(resolve(row['response']));row['parameters']=r['parameters'];row['phase_journal']=r['phase_journal'];resolve(r['phase_journal'])
            row['timely_strict_certificate']=bool(row['timing_eligible'] and row['certified'] and r['returned_before_deadline'] and r['solver_wall_ns']<=row['requested_solver_wall_ns'])
            row['requested_wall_exceeded']=r['solver_wall_ns']>row['requested_solver_wall_ns']
            row['interrupts']=r['interrupts'];row['solve_returned_ns']=r['solve_returned_ns']
            log=BASE/c['id']/'response.copt.log';row['log']=ref(log)
            first=re.search(r'^\s*0\s+[+-].*?\s+(\d+(?:\.\d+)?)s\s*$',log.read_text(),re.M)
            row['vendor_logged_iteration_zero_seconds']=float(first.group(1)) if first else None
        else:row['timely_strict_certificate']=False
        rows.append(row)
    variants=['instrumented','dualize-off','scale-off','scale-dual-off']
    scores={v:sum(r['timely_strict_certificate'] for r in rows if r['variant']==v) for v in variants}
    best=max(scores.values());eligible=[v for v in variants if scores[v]==best]
    families={r['family'] for r in rows}
    common=sorted(f for f in families if all(any(r['family']==f and r['variant']==v and r['timely_strict_certificate'] for r in rows) for v in eligible))
    costs={v:statistics.median(next(r['complete_ns'] for r in rows if r['variant']==v and r['family']==f) for f in common) for v in eligible} if common else {}
    selected=min(eligible,key=lambda v:(costs.get(v,0),variants.index(v)))
    put(BASE/'copt-diagnostic-results-v1.json',dict(status='all_diagnostic_outcomes_retained',freeze=ref(path),cells=rows,selected_variant=selected,
        timely_strict_certificates=scores,common_certified_families=common,selection_complete_cost_ns=costs,
        selection_rule='Maximize timely strict endpoint coverage; minimize median complete cost on the common certified families. Ties prefer instrumented, dualize-off, scale-off, then both off.',
        limitation='One rotated repetition on three prespecified families; diagnostic tuning is not the final six-family comparison.',source=ref(__file__)))
    for r in rows:
        print(dict(family=r['family'],variant=r['variant'],status=r['status'],strict=r['timely_strict_certificate'],
            iteration_zero_s=r.get('vendor_logged_iteration_zero_seconds'),iterations=r.get('native',{}).get('PDLPIter'),
            process_s=r.get('fresh_process_ns',0)/1e9,complete_s=r.get('complete_ns',0)/1e9),flush=True)
    print(dict(selected=selected,coverage=scores,common_certified=common),flush=True)


def proposal():
    d=worksheet();prior=load(BASE/'gpu-control-settled-checkpoint-v1.json')
    require(all(prior['cpu_by_phase_ns'][k]/1e9+d['cpu'][k]<=v for k,v in d['cpu_caps'].items()),'entire prospective CPU phase allocation')
    require(all(prior['gpu_by_phase_ns'][k]/1e9+d['gpu'][k]<=v for k,v in d['gpu_caps'].items()),'entire prospective GPU phase allocation')
    put(BASE/'copt-fair-reservation-proposal-v1.json',dict(status='prospective_not_authorized',**d,checkpoint=ref(BASE/'gpu-control-settled-checkpoint-v1.json'),
        reserved_total_cpu_seconds=prior['cpu_ns']/1e9+sum(d['cpu'].values()),reserved_total_gpu_seconds=prior['gpu_ns']/1e9+sum(d['gpu'].values()),source=ref(__file__)))
    print('Whole prospective comparison fits proposed totals and every proposed phase cap.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['diagnostics','proposal']);a=parser.parse_args();globals()[a.action]()
