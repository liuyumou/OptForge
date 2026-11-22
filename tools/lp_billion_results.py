"""Audit frozen cohorts and report full costs without loading endpoint vectors."""
import argparse
import copy
import statistics
from pathlib import Path
from lp_billion_common import BASE, load, put, ref, resolve, require
from lp_billion_campaign import check


def audit(manifest):
    for cell in load(manifest)['cells']:
        if cell['status'] != 'pending':
            continue
        identity = cell['id']
        response = BASE/identity/'response.json'
        if not response.exists():
            failed=BASE/'resources'/(identity+'.settlement.json')
            require(failed.exists() and load(failed)['status']=='refused', 'unsettled missing response: '+identity)
            print(dict(cell=identity, retained_missing=True, settlement=ref(failed)), flush=True)
            continue
        model = resolve(cell['model'])
        check(identity+'-final-check', response, model, False)
        check(identity+'-audit', response, model, True)
        print(dict(cell=identity, independently_checked=True), flush=True)


def canonical(response):
    # Endpoint references bind every binary64 bit; never materialize billion-scale
    # vectors merely to compare their already-content-addressed identities.
    result={k: copy.deepcopy(v) for k, v in response.items()
            if k not in {'input_ns', 'elapsed_ns', 'cost_ns','gpu_preparation','preparation_detail_ns','solver_profile'}}
    result.get('fast_config',{}).pop('gpu_preparation',None)
    return result


def record(cell):
    result = dict(id=cell['id'], lane=cell['lane'], capacity=cell['memory'])
    original = load(resolve(cell['model_result']))
    result.update(family=original['family'], nonzeros=original['nonzeros'],
                  rows=original['rows'], columns=original['columns'])
    if cell['status'] != 'pending':
        return dict(result, status=cell['status'])
    out = BASE/cell['id']
    if not (out/'result.json').exists():
        failed=BASE/'resources'/(cell['id']+'.settlement.json')
        return dict(result,status='interrupted' if failed.exists() else 'unmeasured',
                    settlement=ref(failed) if failed.exists() else None)
    measured = load(out/'result.json'); r = load(resolve(measured['response']))
    settlement = load(BASE/'resources'/(cell['id']+'.settlement.json'))
    require(settlement['status']=='passed' and settlement['cleanup_empty']
            and not settlement['overrun'], 'eligible timing supervision')
    resource = load(resolve(settlement['resource']))
    disposition_path=BASE/'resources'/(cell['id']+'.ownership-disposition.json')
    disposition=load(disposition_path) if disposition_path.exists() else None
    if disposition:
        require(disposition['settlement']==ref(BASE/'resources'/(cell['id']+'.settlement.json')),
                'ownership disposition binding')
    final = load(out.with_name(out.name+'-final-check')/'result.json')
    audit_result = load(out.with_name(out.name+'-audit')/'result.json')
    require(final['status']==audit_result['status']=='passed', 'independent checking')
    require(final['response']==audit_result['response']==measured['response'], 'checked endpoint binding')
    work=r['accepted_product_work']
    result.update(status=r['status'], certified=r['certified'], logical=r['logical'], physical=r['physical'],
        timing_eligible=disposition is None,
        ownership_disposition=ref(disposition_path) if disposition else None,
        selected_initial_format=r['selected_initial_format'], accepted=r['accepted'], recoveries=len(r['recoveries']),
        accepted_product_work=work, accepted_fp4_share=work[1]/work[3] if work[3] else 0.,
        process_ns=measured['process_ns'], fresh_process_ns=measured['fresh_process_ns'],
        final_check_ns=final['elapsed_ns'], complete_ns=measured['fresh_process_ns']+final['elapsed_ns'],
        input_ns=r['input_ns'], cost_ns=r['cost_ns'], offline_audit_ns=audit_result['elapsed_ns'],
        device_bytes=r['device_bytes_upper'], operator_storage_bytes=r['operator_storage_bytes'],
        packed_bytes=r['packed_bytes'], tile_count=r['tile_count'],
        gpu_preparation=r.get('gpu_preparation'),preparation_detail_ns=r.get('preparation_detail_ns'),
        peak_rss_bytes=resource['result']['peak_rss_bytes'],
        response=measured['response'], resource=settlement['resource'],
        final_check=ref(out.with_name(out.name+'-final-check')/'result.json'),
        audit=ref(out.with_name(out.name+'-audit')/'result.json'))
    if 'solver_profile' in r:
        from lp_billion_timing import process_ledger
        result['complete_cost_ledger']=process_ledger(r,measured,final['elapsed_ns'])
    return result


def summarize(manifest, output):
    cells=[record(c) for c in load(manifest)['cells']]
    put(output, dict(status='reported', freeze=ref(manifest), cells=cells,
        measured=sum('response' in c for c in cells),
        certified=sum(c.get('certified', False) for c in cells)))


def compare(before, after, output, within_reservation=False):
    if not within_reservation and load(after)['image']['path'] in ['image-v4/binding.json','image-v5/binding.json','image-v6/binding.json','image-v7/binding.json']:
        from lp_billion_budget import run
        import sys
        identity='comparison-'+Path(after).parent.name
        result=run(identity,'reporting',600,False,
            [sys.executable,'-B',__file__,'compare',str(before),str(after),str(output),'--within-reservation'],
            host_gib=32,disk_gib=1)
        require(result['status']=='passed','bounded complete comparison')
        return
    a,b=load(before)['cells'],load(after)['cells']
    require(len(a)==len(b),'paired cohort lengths')
    pairs=[]
    for ca,cb in zip(a,b):
        qa,qb=copy.deepcopy(ca['request']),copy.deepcopy(cb['request'])
        qa['fast'].pop('gpu_preparation',None);qb['fast'].pop('gpu_preparation',None)
        qa.pop('profile',None);qb.pop('profile',None)
        require(ca['model']==cb['model'] and qa==qb,'equal input and work settings')
        ra,rb=record(ca),record(cb)
        require(canonical(load(resolve(ra['response'])))==canonical(load(resolve(rb['response']))),
                'complete numerical transcript differs')
        eligible=ra['timing_eligible'] and rb['timing_eligible']
        pairs.append(dict(family=ra['family'], before=ra, after=rb, exact=True, timing_eligible=eligible,
            preparation_ratio=ra['cost_ns']['host_preparation']/rb['cost_ns']['host_preparation'],
            assessment_ratio=ra['cost_ns']['assessment']/rb['cost_ns']['assessment'],
            process_ratio=ra['process_ns']/rb['process_ns'], complete_ratio=ra['complete_ns']/rb['complete_ns']))
    eligible_pairs=[p for p in pairs if p['timing_eligible']]
    for p in pairs:
        if not p['timing_eligible']:
            for key in ['preparation_ratio','assessment_ratio','process_ratio','complete_ratio']:
                p[key]=None
    put(output,dict(status='passed',before=ref(before),after=ref(after),pairs=pairs,
        median_preparation_ratio=statistics.median(p['preparation_ratio'] for p in eligible_pairs) if eligible_pairs else None,
        median_assessment_ratio=statistics.median(p['assessment_ratio'] for p in eligible_pairs) if eligible_pairs else None,
        median_process_ratio=statistics.median(p['process_ratio'] for p in eligible_pairs) if eligible_pairs else None,
        median_complete_ratio=statistics.median(p['complete_ratio'] for p in eligible_pairs) if eligible_pairs else None,
        claim='Descriptive sequential fixed-work comparison; not certified-solve benefit or confirmation.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('audit');a.add_argument('manifest',type=Path)
    s=sub.add_parser('summarize');s.add_argument('manifest',type=Path);s.add_argument('output',type=Path)
    c=sub.add_parser('compare');c.add_argument('before',type=Path);c.add_argument('after',type=Path);c.add_argument('output',type=Path);c.add_argument('--within-reservation',action='store_true')
    args=p.parse_args()
    if args.action=='audit':audit(args.manifest)
    elif args.action=='summarize':summarize(args.manifest,args.output)
    else:compare(args.before,args.after,args.output,args.within_reservation)
