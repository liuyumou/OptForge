"""Compact, loss-preserving scale summaries. Timed failures never become wins."""
import argparse
import json
import statistics
from pathlib import Path
from lp_general_common import BASE,ROOT,put,load,ref,require
from lp_general_budget import accounting
from lp_general_scale_evidence import read as read_response

def campaign(identity):
    root=BASE/identity;f=load(root/'freeze.json');rows=[];missing=[];matched=[];raw_only=[]
    for c in f['cells']:
        p=root/f'm{c["model_index"]:02d}'/(c['id']+'.cell.json')
        if not p.exists():
            missing.append(c['id']);raw=p.with_name(p.name.replace('.cell.json','.response.json'))
            if raw.exists():raw_only.append(dict(cell=c['id'],response=ref(raw),bytes=raw.stat().st_size))
            continue
        r=load(p);settlement=BASE/'resources'/f'{identity}-m{c["model_index"]:02d}.settlement.json'
        s=load(settlement) if settlement.exists() else None
        audit_ok=True;deferred=None
        if r.get('audit_pending'):
            ap=p.parent/'history-audit/result.json';sp=BASE/'resources'/f'{identity}-m{c["model_index"]:02d}-audit.settlement.json'
            audit_ok=ap.exists() and sp.exists() and load(ap)['status']=='passed' and load(sp)['status']=='passed'
            if audit_ok:deferred=next(a for a in load(ap)['rows'] if a['cell']==c['id'])
        m=f['models'][c['model_index']];work=r['accepted_product_work'];cost=r['cost_ns']
        row=dict(id=c['id'],model_index=c['model_index'],family=m['family'],target=m.get('target'),seed=m.get('seed'),lane=c['lane'],tolerance=c['tolerance'],repeat=c['repeat'],
            status=r['status'],certified=r['certified'],supervised=bool(s and s['status']=='passed' and audit_ok),history_audit_passed=audit_ok,logical=r['logical'],physical=r['physical'],
            primary_seconds=r['complete_ns']/1e9,process_seconds=r['process_ns']/1e9,independent_seconds=r['independent_ns']/1e9,
            audit_seconds=(deferred['audit_ns'] if deferred else r.get('audit_ns',0))/1e9,cost_seconds={k:v/1e9 for k,v in cost.items()},accepted_product_work=work,
            fp4_share=work[1]/work[3] if work and work[3] else 0,tiles=r['tile_count'],selected_initial_format=r['selected_initial_format'],
            gpu_confirmed=r['gpu_confirmed'],cell=ref(p),response=r['response'],resource=ref(settlement) if s else None,
            certificate=r['certificate'],nonzeros=r['nonzeros'])
        rows.append(row)
    # Pair only within the same frozen model, tier and repetition.
    keyed={(r['model_index'],r['tolerance'],r['repeat'],r['lane']):r for r in rows}
    comparisons=[]
    for r in rows:
        if r['lane'] not in ['fp4x2','fp4x2-split']:continue
        for control in ['native','fp32','copt-cpu-auto','copt-gpu-pdlp','copt-gpu-tight']:
            a=keyed.get((r['model_index'],r['tolerance'],r['repeat'],control))
            if a is None:continue
            eligible=r['supervised'] and a['supervised'] and r['certified'] and a['certified']
            comparisons.append(dict(model_index=r['model_index'],repeat=r['repeat'],tolerance=r['tolerance'],candidate=r['lane'],control=control,
                jointly_certified=eligible,ratio=a['primary_seconds']/r['primary_seconds'] if eligible else None,
                candidate_fp4_share=r['fp4_share'],has_actual_fp4=r['fp4_share']>0))
    if f['mode']=='pilot':
        prefix='old-' if any(r['lane']=='old-native' for r in rows) else 'previous-'
        for r in rows:
            if r['lane'] not in ['native','fp32','fp4x2']:continue
            a=keyed.get((r['model_index'],r['tolerance'],r['repeat'],prefix+r['lane']))
            if a is None:continue
            x,y=read_response(ROOT/a['response']['path']),read_response(ROOT/r['response']['path'])
            keys=['primal','dual','certificate','assessments','logical','physical','accepted','attempted','recoveries','accepted_product_work','physical_product_work']
            exact=all(json.dumps(x[k],sort_keys=True)==json.dumps(y[k],sort_keys=True) for k in keys)
            same_work=x['logical']==y['logical'] and x['physical']==y['physical']
            if same_work:require(exact,'matched version arithmetic differs at equal work')
            else:require('deadline' in [x['status'],y['status']],'unexplained work difference in host-only pilot')
            matched.append(dict(model_index=r['model_index'],lane=r['lane'],repeat=r['repeat'],exact=exact,equal_work=same_work,supervised=r['supervised'] and a['supervised'],status_same=x['status']==y['status'],
                primary_ratio=a['primary_seconds']/r['primary_seconds'],process_ratio=a['process_seconds']/r['process_seconds'],
                preparation_ratio=a['cost_seconds']['host_preparation']/r['cost_seconds']['host_preparation'],
                before_primary_seconds=a['primary_seconds'],after_primary_seconds=r['primary_seconds']))
    summaries=[]
    for lane in sorted({c['lane'] for c in f['cells']}):
        selected=[r for r in rows if r['lane']==lane];valid=[r for r in selected if r['supervised']]
        work=[sum(r['accepted_product_work'][i] for r in valid if r['accepted_product_work']) for i in range(4)]
        summaries.append(dict(lane=lane,planned=sum(c['lane']==lane for c in f['cells']),responses=len(selected),supervised=len(valid),certified=sum(r['certified'] for r in valid),
            statuses={str(k):sum(r['status']==k for r in selected) for k in sorted({r['status'] for r in selected},key=str)},
            accepted_product_work=work,fp4_share=work[1]/work[3] if work[3] else 0))
    return dict(identity=identity,freeze=ref(root/'freeze.json'),mode=f['mode'],planned=len(f['cells']),responses=len(rows),missing=missing,
        continuation_of=f.get('continuation_of'),excluded_attempted=f.get('excluded_attempted',[]),unsupported_models=f.get('unsupported_models',[]),rows=rows,raw_only=raw_only,comparisons=comparisons,matched=matched,summaries=summaries,
        timing_scope='v1 and interrupted v2 include historical endpoint auditing in complete cost; v3 and later separate final-certificate primary time and historical auditing. Compare versions only within the same frozen campaign.')

def report(identities,output,compact=None):
    results=[campaign(x) for x in identities];cpu,gpu=accounting();failures=[]
    for p in sorted((BASE/'resources').glob('scale-*.settlement.json')):
        s=load(p)
        if s['status']!='passed':failures.append(dict(settlement=ref(p),**s))
    data=dict(status='development-results',campaigns=results,failures=failures,cpu_seconds={k:v/1e9 for k,v in cpu.items()},gpu_seconds={k:v/1e9 for k,v in gpu.items()},
        inventory=ref(BASE/'scale-inventory-v2/result.json'),earlier_inventory=ref(BASE/'scale-inventory-v1/result.json'),
        claim='Descriptive development; no confirmation, no unsuccessful-solve speedup, and no FP4 credit for zero-FP4 work. Our research process includes intermediate-trajectory serialization/transport; COPT returns a final endpoint. Archive compression and historical checking are separated in final campaigns.',source=ref(__file__))
    put(output,data)
    if compact:
        columns=['id','model_index','lane','tolerance','repeat','status','certified','supervised','primary_seconds','independent_seconds','audit_seconds','logical','physical','fp4_share','nonzeros','cost_seconds']
        campaigns=[]
        for c in results:
            campaigns.append({**{k:v for k,v in c.items() if k not in ['rows','comparisons']},'cell_columns':columns,'cells':[[r.get(k) for k in columns] for r in c['rows']]})
        put(compact,{**{k:v for k,v in data.items() if k!='campaigns'},'full_local_results':ref(output),'campaigns':campaigns,
            'format_note':'Column-oriented compact cells preserve every observed result. Full original certificates, per-cell bindings and all pair comparisons are in the bound local results and portable archive.'})
    for r in results:
        print(r['identity'],r['responses'],'/',r['planned'],[(s['lane'],s['certified']) for s in r['summaries']],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ids',nargs='+',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--compact-output',type=Path);a=p.parse_args();report(a.ids,a.output,a.compact_output)
