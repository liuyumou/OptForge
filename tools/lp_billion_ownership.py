"""Additive audit of retained GPU memory ownership; never changes old receipts."""
import json
from lp_billion_common import BASE, put, ref, load
from lp_billion_idle import UNATTRIBUTED_LIMIT


def audit():
    rows=[]
    for path in sorted((BASE/'resources').glob('*.reservation.json')):
        reservation=load(path)
        if not reservation['gpu']:
            continue
        identity=path.name.removesuffix('.reservation.json')
        trace=path.with_name(identity+'.resource.json.capacity.jsonl')
        samples=[json.loads(line)['gpu'] for line in trace.read_text().splitlines()
                 if 'gpu' in json.loads(line)] if trace.exists() else []
        idle=reservation.get('idle') or []
        residual=[s['used']-sum(s['processes'].values()) for s in idle+samples]
        row=dict(id=identity,reservation=ref(path),trace=ref(trace) if trace.exists() else None,
                 idle_samples=len(idle),supervised_samples=len(samples),
                 min_unattributed_bytes=min(residual) if residual else None,
                 max_unattributed_bytes=max(residual) if residual else None,
                 samples_above_bound=sum(v>UNATTRIBUTED_LIMIT for v in residual),
                 fixed_allowance_bytes=UNATTRIBUTED_LIMIT)
        if row['samples_above_bound']:
            row['status']='timing_ineligible_ownership_uncertain'
            put(path.with_name(identity+'.ownership-disposition.json'),dict(row,
                settlement=ref(path.with_name(identity+'.settlement.json')),
                numerical_results_retained=True,retry_authorized=False))
        else:
            row['status']='no_additional_exclusion'
        rows.append(row)
    put(BASE/'ownership-audit-v1.json',dict(status='audited',rows=rows,
        limitation='Retrospective sampled telemetry cannot establish absence of all unlisted activity.'))
    print({'gpu_reservations':len(rows),'additional_exclusions':[r['id'] for r in rows if r['samples_above_bound']]},flush=True)


if __name__=='__main__':
    audit()
