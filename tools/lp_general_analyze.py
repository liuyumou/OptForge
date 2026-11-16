"""Loss-preserving descriptive analysis, including interrupted/missing cells."""
import argparse
import statistics
from lp_general_common import ROOT,BASE,load,put,ref,require

def run(identity):
    out=BASE/identity;frozen=load(out/'freeze.json');rows=[];missing=[];resources={}
    for p in (BASE/'resources').glob('*.reservation.json'):
        reservation=load(p);command=reservation['command']
        if identity not in command or '--index' not in command:continue
        i=int(command[command.index('--index')+1]);require(i not in resources,'duplicate model resource job')
        settlement=p.with_name(p.name.replace('.reservation.json','.settlement.json'))
        r=load(settlement) if settlement.exists() else {}
        resources[i]=dict(reservation=ref(p),settlement=ref(settlement) if settlement.exists() else None,
            eligible=r.get('status')=='passed' and not r.get('overrun',True) and bool(r.get('resource')))
    for cell in frozen['cells']:
        p=out/f'm{cell["model_index"]:02d}'/(cell['id']+'.cell.json')
        if not p.exists():
            missing.append(dict(**cell,reason='no complete cell receipt; interrupted or unexecuted',resource=resources.get(cell['model_index'])))
            continue
        r=load(p)
        require(all(r[k]==v for k,v in cell.items()),'cell differs from freeze')
        r['resource_eligible']=resources.get(cell['model_index'],{}).get('eligible',False)
        rows.append(r)
    formats={}
    for format in ['native','fp32','fp4x1','fp4x2']:
        rs=[r for r in rows if r['settings']['format']==format]
        qualified=[r for r in rs if r['resource_eligible']]
        formats[format]=dict(cells=len(rs),planned_cells=sum(c['settings']['format']==format for c in frozen['cells']),
            resource_eligible_cells=len(qualified),certified=sum(r.get('certified',False) for r in rs),
            accepted=[sum(r.get('accepted',[0]*4)[j] for r in rs) for j in range(4)],
            attempted=[sum(r.get('attempted',[0]*4)[j] for r in rs) for j in range(4)],
            complete_median_ms=statistics.median(r['complete_ns']/1e6 for r in qualified) if qualified else None,
            timing_scope='all resource-eligible observed outcomes, including limits; conditional on coverage, not time-to-certified-solution')
    groups=[];comparisons=[]
    for i in sorted({r['model_index'] for r in frozen['cells']}):
        for tier in [1e-7,1e-9]:
            rs={r['settings']['format']:r for r in rows if r['model_index']==i and r['settings']['tolerance']==tier}
            example=next((r for r in rows if r['model_index']==i),{})
            family=next(c['family'] for c in frozen['cells'] if c['model_index']==i)
            group=dict(model_index=i,family=family,tolerance=tier,
                columns=example.get('columns'),rows=example.get('rows'),nonzeros=example.get('nonzeros'),formats={})
            for format in ['native','fp32','fp4x1','fp4x2']:
                r=rs.get(format)
                if r is None:
                    group['formats'][format]=dict(status='missing',certified=False,resource_eligible=False)
                    if format!='native':comparisons.append(dict(model_index=i,family=family,tolerance=tier,format=format,
                        eligible=False,reason='missing cell',ratio=None,savings_ms=None,accepted_fp4_fraction=None,accepted_fp4_nonzeros=None))
                    continue
                response=load(ROOT/r['response']['path']) if r['process_returncode']==0 else None
                group['formats'][format]=dict(certified=r.get('certified',False),status=r.get('status',r['error']),
                    resource_eligible=r['resource_eligible'],
                    complete_ms=r['complete_ns']/1e6,accepted=r.get('accepted'),physical=r.get('physical'),
                    certificate=response['certificate'] if response else None,
                    cost_ms={k:v/1e6 for k,v in r.get('cost_ns',{}).items()},
                    unassigned_internal_ms=r.get('unassigned_internal_ns',0)/1e6,outer_ms=r.get('outer_ns',0)/1e6)
                if format!='native':
                    native=rs.get('native',{})
                    eligible=bool(r.get('certified') and native.get('certified') and r['resource_eligible'] and native.get('resource_eligible'))
                    comparisons.append(dict(model_index=i,family=r['family'],tolerance=tier,format=format,eligible=eligible,
                        ratio=rs['native']['complete_ns']/r['complete_ns'] if eligible else None,
                        savings_ms=(rs['native']['complete_ns']-r['complete_ns'])/1e6 if eligible else None,
                        accepted_fp4_fraction=sum(r.get('accepted',[0]*4)[2:])/max(1,r.get('logical',0)),
                        accepted_fp4_nonzeros=sum(r.get('accepted_matvec_nonzeros',[0]*4)[2:])))
            groups.append(group)
    result=dict(kind='general-development-descriptive-analysis',status='incomplete' if missing else 'complete',
        cells=len(rows),planned_cells=len(frozen['cells']),missing=missing,resource_eligible_cells=sum(r['resource_eligible'] for r in rows),
        resources=resources,formats=formats,groups=groups,
        comparisons=comparisons,freeze=ref(out/'freeze.json'),scientific_confirmation=False,
        conclusion='No value/adoption test: one timing per cell; failures and missing cells stay visible. Missingness may be informative.')
    put(out/'analysis.json',result)
    print(dict(cells=len(rows),formats=formats,certified_comparisons=sum(r['eligible'] for r in comparisons)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);a=p.parse_args();run(a.id)
