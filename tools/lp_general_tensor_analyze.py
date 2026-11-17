"""Descriptive Tensor Core development results; missing and failed cells stay visible."""
import argparse
import json
import statistics
from lp_general_common import BASE,ROOT,load,put,ref,require

CAMPAIGNS=['tensor-development-v1','tensor-ablation-v1','tensor-development-v2']

def rows(campaign):
    root=BASE/campaign;f=load(root/'freeze.json');result=[]
    for c in f['cells']:
        directory=root/f'm{c["model_index"]:02d}';raw=directory/(c['id']+'.stdout.jsonl')
        item=dict(id=c['id'],model_index=c['model_index'],family=f['models'][c['model_index']]['family'],format=c['format'],tolerance=c['request']['settings']['tolerance'],retained=raw.exists(),qualified=False)
        if raw.exists():
            r=json.loads(raw.read_text());item.update(response=ref(raw),status=r['status'],certified=r['certified'],physical=r['physical'],logical=r['logical'],accepted_product_work=r['accepted_product_work'],physical_product_work=r['physical_product_work'],reference_product_nnz=r.get('reference_product_nnz'),cost_ns=r['cost_ns'],tile_count=r['tile_count'],selected_initial_format=r.get('selected_initial_format'),nonzeros=r['nonzeros'],rows=r['rows'],columns=r['columns'],packed_bytes=r['packed_bytes'],assessments=len(r['assessments'])+1)
            result_path=directory/'result.json';settlement=BASE/'resources'/f'{campaign}-m{c["model_index"]:02d}.settlement.json'
            if result_path.exists() and settlement.exists():
                settled=load(settlement);item['qualified']=settled['status']=='passed' and not settled['overrun']
                rr=next(x for x in load(result_path)['rows'] if x['cell']['id']==c['id']);require(rr['cell']==c,'frozen cell differs')
                require(ref(ROOT/rr['response']['path'])==rr['response'],'parsed response differs');require(load(ROOT/rr['response']['path'])==r,'raw response differs')
                item['complete_ms']=rr['complete_ms']
        result.append(item)
    return f,result

def analyze(identity):
    out=BASE/identity;out.mkdir(exist_ok=False);campaigns={}
    for name in CAMPAIGNS:
        f,rs=rows(name);lanes={}
        for fmt in sorted({r['format'] for r in rs}):
            planned=[r for r in rs if r['format']==fmt];retained=[r for r in planned if r['retained']];qualified=[r for r in retained if r['qualified']]
            work=[sum(r['accepted_product_work'][i] for r in retained) for i in range(4)]
            lanes[fmt]=dict(planned=len(planned),retained=len(retained),qualified=len(qualified),certified_retained=sum(r['certified'] for r in retained),certified_qualified=sum(r['certified'] for r in qualified),accepted_product_work=work,fp4_fraction=work[1]/work[3] if work[3] else 0,correction_fraction=work[2]/work[3] if work[3] else 0,tensor_attempt_fraction=work[0]/work[3] if work[3] else 0,tensor_attempt_retention=work[1]/work[0] if work[0] else 0)
        pairs=[]
        for r in rs:
            if r['format']=='native':continue
            n=next(x for x in rs if x['model_index']==r['model_index'] and x['tolerance']==r['tolerance'] and x['format']=='native')
            if r['qualified'] and n['qualified'] and r['certified'] and n['certified']:
                pairs.append(dict(model_index=r['model_index'],family=r['family'],tolerance=r['tolerance'],format=r['format'],native_ms=n['complete_ms'],candidate_ms=r['complete_ms'],speedup=n['complete_ms']/r['complete_ms'],native_logical=n['logical'],candidate_logical=r['logical'],fp4_nonzeros=r['accepted_product_work'][1]))
        pair_summary={fmt:dict(pairs=len(v),faster=sum(x['speedup']>1 for x in v),median_speedup=statistics.median(x['speedup'] for x in v)) for fmt in lanes if (v:=[x for x in pairs if x['format']==fmt])}
        for fmt,summary in pair_summary.items():
            active=[r for r in pairs if r['format']==fmt and r['fp4_nonzeros']>0]
            summary['pairs_with_tensor_work']=len(active)
            summary['faster_with_tensor_work']=sum(r['speedup']>1 for r in active)
            summary['median_with_tensor_work']=statistics.median(r['speedup'] for r in active) if active else None
        fp32_pairs=[]
        for r in rs:
            if r['format']!='fp4x4':continue
            p=next(x for x in rs if x['model_index']==r['model_index'] and x['tolerance']==r['tolerance'] and x['format']=='fp32')
            if r['qualified'] and p['qualified'] and r['certified'] and p['certified']:
                fp32_pairs.append(dict(model_index=r['model_index'],tolerance=r['tolerance'],fp32_ms=p['complete_ms'],fp4_ms=r['complete_ms'],speedup=p['complete_ms']/r['complete_ms']))
        comparisons=[]
        if f.get('ablation'):
            for i in range(len(f['models'])):
                group=[r for r in rs if r['model_index']==i];canonical=next(r for r in group if r['format']=='fp4x4')
                for fmt in ['fp4x4-expanded','fp4x4-w4']:
                    r=next(r for r in group if r['format']==fmt)
                    if not(r['qualified'] and canonical['qualified']):continue
                    a=load(ROOT/canonical['response']['path']);b=load(ROOT/r['response']['path'])
                    fields=['primal','dual','certificate','assessments','accepted','attempted','accepted_product_work','physical_product_work','reference_product_nnz','physical','logical','recoveries','restarts','status']
                    same=all(a[k]==b[k] for k in fields)
                    # Deadline timing may intentionally interrupt different physical windows.
                    require(same or a['status']=='deadline' or b['status']=='deadline','layout/launch changed numerical transcript')
                    comparisons.append(dict(model_index=i,variant=fmt,identical_numerical_transcript=same,compact_one_warp_ms=canonical['complete_ms'],variant_ms=r['complete_ms']))
        campaigns[name]=dict(freeze=ref(BASE/name/'freeze.json'),planned=len(rs),retained=sum(r['retained'] for r in rs),qualified=sum(r['qualified'] for r in rs),missing=[r['id'] for r in rs if not r['retained']],lanes=lanes,certified_pairs=pairs,pair_summary=pair_summary,fp4_vs_fp32_certified_pairs=fp32_pairs,layout_launch_comparisons=comparisons,rows=rs)
        print(name,{k:campaigns[name][k] for k in ['planned','retained','qualified','pair_summary']},flush=True)
    result=dict(schema_version=1,status='descriptive-development',campaigns=campaigns,limitations=['One observation per model/format/tier; no inferential value or adoption pass.','Only jointly certified complete supervised cells enter solve-time ratios; all planned cells remain in coverage.','Four normal FP4 components use sixteen logical coefficient bits per orientation plus scales, indices, original FP64 data and guards.','Native selection for zero-tile operators contributes zero FP4 work.','Prior failed campaign is retained without retry or eligible timing.'])
    put(out/'result.json',result)
    put(ROOT/'docs/benchmarks/lp-general-tensor-results.json',result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--id',required=True);a=p.parse_args();analyze(a.id)
